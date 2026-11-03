"""Assign the Employee role to active users who have no company role yet."""

from django.core.management.base import BaseCommand

from base.role_defaults import ensure_default_employee_role_for_unassigned_users
from base.signals import _sync_default_hrms_groups, _sync_export_permissions


class Command(BaseCommand):
    help = (
        "Sync default group permissions and assign the Employee role to users "
        "who have a linked employee record but no company role assignment."
    )

    def handle(self, *args, **options):
        _sync_export_permissions()
        _sync_default_hrms_groups()
        ensure_default_employee_role_for_unassigned_users()
        self.stdout.write(
            self.style.SUCCESS(
                "Default Employee roles assigned where missing (existing "
                "Admin/Manager/HR roles were not changed)."
            )
        )
