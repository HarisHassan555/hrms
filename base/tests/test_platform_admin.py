from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from base.platform_admin import is_platform_superuser


class PlatformSuperuserTests(TestCase):
    def test_django_superuser(self):
        user = get_user_model()(username="root", is_superuser=True)
        self.assertTrue(is_platform_superuser(user))

    @override_settings(PLATFORM_SUPERUSER_EMAILS=["owner@dsg.example"])
    def test_allowlisted_email(self):
        user = get_user_model()(
            username="owner",
            email="owner@dsg.example",
            is_superuser=False,
        )
        self.assertTrue(is_platform_superuser(user))

    @override_settings(PLATFORM_SUPERUSER_EMAILS=["owner@dsg.example"])
    def test_tenant_admin_not_platform(self):
        user = get_user_model()(
            username="tenant",
            email="admin@tenant.example",
            is_superuser=False,
        )
        self.assertFalse(is_platform_superuser(user))
