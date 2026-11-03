from django.contrib.auth.models import Group
from django.test import TestCase

from base.role_defaults import DEFAULT_EMPLOYEE_GROUP_NAME, SUPER_USER_GROUP_NAME
from base.signals import _sync_default_hrms_groups


class DefaultHrmsGroupsTests(TestCase):
    def test_manager_group_includes_team_modules(self):
        _sync_default_hrms_groups()
        group = Group.objects.get(name="Manager")
        perms = group.permissions.select_related("content_type")
        app_labels = {p.content_type.app_label for p in perms}
        self.assertIn("recruitment", app_labels)
        self.assertIn("employee", app_labels)
        self.assertIn("leave", app_labels)
        self.assertIn("attendance", app_labels)
        self.assertTrue(
            perms.filter(
                content_type__app_label="recruitment", codename="add_recruitment"
            ).exists()
        )

    def test_employee_group_exists_with_self_service_perms(self):
        _sync_default_hrms_groups()
        group = Group.objects.get(name=DEFAULT_EMPLOYEE_GROUP_NAME)
        self.assertTrue(
            group.permissions.filter(
                content_type__app_label="leave", codename="add_leaverequest"
            ).exists()
        )
        self.assertTrue(
            group.permissions.filter(
                content_type__app_label="employee", codename="view_ownprofile"
            ).exists()
        )

    def test_super_user_group_replaces_legacy_boss(self):
        Group.objects.create(name="Boss")
        _sync_default_hrms_groups()
        self.assertFalse(Group.objects.filter(name="Boss").exists())
        self.assertTrue(Group.objects.filter(name=SUPER_USER_GROUP_NAME).exists())
