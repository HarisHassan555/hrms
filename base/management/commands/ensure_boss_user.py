"""
Create/sync the Boss role (all permissions) and assign it to a user per company.

Optionally grants Django superuser for platform-level settings and bypass rules.
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from base.management.commands.ensure_tenant_admin import Command as AdminCommand
from base.models import Company, CompanyGroupAssignment
from base.signals import _sync_default_hrms_groups, _sync_export_permissions

BOSS_GROUP_NAME = "Boss"


class Command(BaseCommand):
    help = (
        "Sync the Boss role (full application permissions) and assign it to a user "
        "for every company. Use --superuser for Django superuser (maximum control)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--email", help="User login email (case-insensitive)")
        parser.add_argument("--username", help="User username (case-insensitive)")
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
            help="Also set is_superuser and is_staff (recommended for full control)",
        )
        parser.add_argument(
            "--replace-roles",
            action="store_true",
            help="Remove other company role assignments for this user before assigning Boss",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        _sync_export_permissions()
        _sync_default_hrms_groups()

        boss_group = Group.objects.filter(name=BOSS_GROUP_NAME).first()
        if not boss_group:
            raise CommandError(
                f'"{BOSS_GROUP_NAME}" group is missing — run migrate and try again.'
            )

        resolver = AdminCommand()
        user = resolver._resolve_user(options)

        company_filter = (options.get("company") or "").strip()
        if company_filter:
            companies = list(
                Company.objects.filter(company__iexact=company_filter)
            )
        else:
            companies = list(Company.objects.all().order_by("pk"))

        if not companies:
            raise CommandError("No companies found in the database.")

        if options["replace_roles"]:
            CompanyGroupAssignment.objects.filter(user=user).delete()
            user.groups.clear()

        created = 0
        for company in companies:
            _, was_created = CompanyGroupAssignment.objects.get_or_create(
                user=user,
                company=company,
                group=boss_group,
            )
            if was_created:
                created += 1
            CompanyGroupAssignment.sync_user_group_membership(user, boss_group)

        if options["superuser"]:
            user.is_superuser = True
            user.is_staff = True
            user.save(update_fields=["is_superuser", "is_staff"])

        perm_count = boss_group.permissions.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"User {user.username} ({user.email}): {BOSS_GROUP_NAME} role on "
                f"{len(companies)} company/companies ({created} new assignment(s)); "
                f"{perm_count} permission(s) on role; is_superuser={user.is_superuser}"
            )
        )
