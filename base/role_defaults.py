"""
Default HRMS role assignment helpers.

New employees receive only the ``Employee`` company role unless an admin
assigns additional groups explicitly.
"""

from __future__ import annotations

from django.contrib.auth.models import Group, Permission

from base.models import Company, CompanyGroupAssignment

DEFAULT_EMPLOYEE_GROUP_NAME = "Employee"
SUPER_USER_GROUP_NAME = "Super User"
LEGACY_BOSS_GROUP_NAME = "Boss"

_EMPLOYEE_PROFILE_CODENAMES = ("view_ownprofile", "change_ownprofile")


def migrate_legacy_boss_group_to_super_user() -> None:
    """Rename or merge the legacy ``Boss`` group into ``Super User``."""
    boss = Group.objects.filter(name=LEGACY_BOSS_GROUP_NAME).first()
    if boss is None:
        return

    super_user = Group.objects.filter(name=SUPER_USER_GROUP_NAME).first()
    if super_user is None:
        boss.name = SUPER_USER_GROUP_NAME
        boss.save(update_fields=["name"])
        return

    if super_user.pk == boss.pk:
        return

    CompanyGroupAssignment.objects.filter(group=boss).update(group=super_user)
    affected_users = list(boss.user_set.all())
    for user in affected_users:
        user.groups.remove(boss)
    boss.delete()
    for user in affected_users:
        CompanyGroupAssignment.sync_user_group_membership(user, super_user)


def attach_employee_profile_permissions_to_group() -> None:
    """Ensure the Employee role includes own-profile permissions."""
    group = Group.objects.filter(name=DEFAULT_EMPLOYEE_GROUP_NAME).first()
    if group is None:
        return
    perms = Permission.objects.filter(
        content_type__app_label="employee",
        codename__in=_EMPLOYEE_PROFILE_CODENAMES,
    )
    if perms.exists():
        group.permissions.add(*perms)


def _resolve_company_for_user(user, company=None):
    if company is not None:
        return company
    try:
        employee = user.employee_get
    except Exception:
        employee = None
    if employee is not None:
        work_info = getattr(employee, "employee_work_info", None)
        if work_info is not None and work_info.company_id_id:
            return work_info.company_id
    return Company.objects.order_by("pk").first()


def assign_default_employee_role(user, *, company=None, replace: bool = False) -> None:
    """
    Assign the ``Employee`` role for ``user`` at ``company``.

    When ``replace`` is True, remove all other groups and company role rows
    first (used only for auto-created login accounts).
    """
    group = Group.objects.filter(name=DEFAULT_EMPLOYEE_GROUP_NAME).first()
    if group is None:
        return

    company = _resolve_company_for_user(user, company)
    if company is None:
        return

    if replace:
        user.groups.clear()
        CompanyGroupAssignment.objects.filter(user=user).delete()

    CompanyGroupAssignment.objects.get_or_create(
        user=user,
        company=company,
        group=group,
    )
    CompanyGroupAssignment.sync_user_group_membership(user, group)

    profile_perms = Permission.objects.filter(
        content_type__app_label="employee",
        codename__in=_EMPLOYEE_PROFILE_CODENAMES,
    )
    user.user_permissions.add(*profile_perms)


def ensure_default_employee_role_for_unassigned_users() -> None:
    """
    Backfill: employees linked to a user with no company role get ``Employee`` only.
    Skips superusers and anyone who already has a role assignment.
    """
    from employee.models import Employee

    group = Group.objects.filter(name=DEFAULT_EMPLOYEE_GROUP_NAME).first()
    if group is None:
        return

    assigned_user_ids = CompanyGroupAssignment.objects.values_list(
        "user_id", flat=True
    ).distinct()

    qs = (
        Employee.objects.filter(
            is_active=True,
            employee_user_id__isnull=False,
        )
        .exclude(employee_user_id__in=assigned_user_ids)
        .exclude(employee_user_id__is_superuser=True)
        .select_related("employee_user_id", "employee_work_info__company_id")
    )

    for employee in qs.iterator():
        user = employee.employee_user_id
        company = None
        if hasattr(employee, "employee_work_info") and employee.employee_work_info:
            company = employee.employee_work_info.company_id
        assign_default_employee_role(user, company=company, replace=True)
