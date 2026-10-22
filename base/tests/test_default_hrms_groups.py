from django.contrib.auth.models import Group
from django.test import TestCase

from base.signals import _sync_default_hrms_groups


class DefaultHrmsGroupsTests(TestCase):
    def test_manager_group_is_recruitment_scoped(self):
        _sync_default_hrms_groups()
        group = Group.objects.get(name="Manager")
        perms = group.permissions.select_related("content_type")
        app_labels = {p.content_type.app_label for p in perms}
        self.assertEqual(app_labels, {"employee", "recruitment"})
        self.assertFalse(
            perms.filter(content_type__app_label="recruitment", codename="view_skill").exists()
        )
        self.assertFalse(
            perms.filter(
                content_type__app_label="recruitment", codename="view_rejectreason"
            ).exists()
        )
        self.assertTrue(
            perms.filter(
                content_type__app_label="recruitment", codename="add_recruitment"
            ).exists()
        )
