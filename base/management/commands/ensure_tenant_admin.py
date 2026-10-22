"""
Grant a tenant HR admin full module access via the default ``Admin`` auth group.

With COMPANY_SCOPED_PERMISSIONS enabled, group permissions only apply when a
``CompanyGroupAssignment`` exists for the selected company — plain ``user.groups``
membership is not enough.
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from base.models import Company, CompanyGroupAssignment
from base.signals import _sync_default_hrms_groups, _sync_export_permissions
from employee.models import Employee
from horilla_auth.models import HorillaUser


class Command(BaseCommand):
    help = (
        "Sync the default Admin group permissions and assign that role to a user "
        "for every active company (or one company). Optionally grant Django superuser."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            help="User login email (case-insensitive)",
        )
        parser.add_argument(
            "--username",
            help="User username (case-insensitive)",
        )
        parser.add_argument(
            "--name",
            help='Full name match on employee, e.g. "Haris Hassan"',
        )
        parser.add_argument(
            "--company",
            help="Assign only for this company name (default: all companies)",
        )
        parser.add_argument(
            "--superuser",
            action="store_true",
            help="Also set is_superuser and is_staff on the user",
        )
        parser.add_argument(
            "--no-superuser",
            action="store_true",
            help="Clear is_superuser (keep tenant Admin role only)",
        )

    def _resolve_user(self, options):
        user = None
        email = (options.get("email") or "").strip()
        username = (options.get("username") or "").strip()
        name = (options.get("name") or "").strip()

        if email:
            user = (
                HorillaUser.objects.filter(email__iexact=email).first()
                or HorillaUser.objects.filter(username__iexact=email).first()
            )
        if user is None and username:
            user = HorillaUser.objects.filter(username__iexact=username).first()
        if user is None and name:
            parts = name.split(None, 1)
            if len(parts) == 2:
                first, last = parts[0], parts[1]
                employee = (
                    Employee.objects.filter(
                        employee_first_name__iexact=first,
                        employee_last_name__iexact=last,
                    )
                    .select_related("employee_user_id")
                    .first()
                )
            else:
                employee = (
                    Employee.objects.filter(employee_first_name__iexact=parts[0])
                    .select_related("employee_user_id")
                    .first()
                )
            if employee and employee.employee_user_id:
                user = employee.employee_user_id

        if user is None:
            raise CommandError(
                "User not found — pass --email, --username, or --name"
            )
        return user

    @transaction.atomic
    def handle(self, *args, **options):
        _sync_export_permissions()
        _sync_default_hrms_groups()

        admin_group = Group.objects.filter(name="Admin").first()
        if not admin_group:
            raise CommandError(
                'Default "Admin" group is missing — run migrate and try again.'
            )

        user = self._resolve_user(options)

        company_filter = (options.get("company") or "").strip()
        if company_filter:
            companies = list(
                Company.objects.filter(company__iexact=company_filter)
            )
        else:
            companies = list(Company.objects.all().order_by("pk"))

        if not companies:
            raise CommandError("No companies found in the database.")

        created = 0
        for company in companies:
            _, was_created = CompanyGroupAssignment.objects.get_or_create(
                user=user,
                company=company,
                group=admin_group,
            )
            if was_created:
                created += 1
            CompanyGroupAssignment.sync_user_group_membership(user, admin_group)

        if options["superuser"]:
            user.is_superuser = True
            user.is_staff = True
            user.save(update_fields=["is_superuser", "is_staff"])
        elif options["no_superuser"]:
            user.is_superuser = False
            user.is_staff = False
            user.save(update_fields=["is_superuser", "is_staff"])

        perm_count = admin_group.permissions.count()
        has_add_employee = user.has_perm("employee.add_employee")

        self.stdout.write(
            self.style.SUCCESS(
                f"User {user.username} ({user.email}): Admin role on "
                f"{len(companies)} company/companies ({created} new assignment(s)); "
                f"Admin group has {perm_count} permission(s); "
                f"employee.add_employee={has_add_employee}; "
                f"is_superuser={user.is_superuser}"
            )
        )
