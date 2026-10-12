"""Tests for DB_TABLE_PREFIX / physical table naming."""

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from base.models import Company, EmployeeShiftDay
from horilla.db_table_prefix import resolve_prefixed_db_table
from horilla_auth.models import HorillaUser, LegacyUser


class DbTablePrefixRulesTests(SimpleTestCase):
    @override_settings(DB_TABLE_PREFIX="dsg_hr_")
    def test_company_table_name_rule(self):
        self.assertEqual(
            resolve_prefixed_db_table("base", "company", "base_company"),
            "dsg_hr_base_company",
        )

    @override_settings(DB_TABLE_PREFIX="dsg_hr_")
    def test_explicit_db_table_unchanged(self):
        self.assertEqual(
            resolve_prefixed_db_table(
                "horilla_auth",
                "legacyuser",
                "auth_user",
                explicit_db_table=True,
            ),
            "auth_user",
        )

    @override_settings(DB_TABLE_PREFIX="dsg_hr_")
    def test_auth_permission_app_excluded(self):
        self.assertEqual(
            resolve_prefixed_db_table("auth", "permission", "auth_permission"),
            "auth_permission",
        )

    @override_settings(DB_TABLE_PREFIX="")
    def test_empty_prefix_keeps_default_name(self):
        self.assertEqual(
            resolve_prefixed_db_table("base", "company", "base_company"),
            "base_company",
        )

    @override_settings(DB_TABLE_PREFIX="dsg_hr_")
    def test_no_double_prefix(self):
        self.assertEqual(
            resolve_prefixed_db_table(
                "base", "company", "dsg_hr_base_company"
            ),
            "dsg_hr_base_company",
        )


class DbTablePrefixStartupTests(SimpleTestCase):
    def test_horilla_model_prefixed_at_class_creation(self):
        prefix = settings.DB_TABLE_PREFIX or ""
        if prefix:
            self.assertEqual(Company._meta.db_table, f"{prefix}base_company")
        else:
            self.assertEqual(Company._meta.db_table, "base_company")

    def test_plain_model_prefixed_in_ready(self):
        prefix = settings.DB_TABLE_PREFIX or ""
        expected = (
            f"{prefix}base_employeeshiftday"
            if prefix
            else "base_employeeshiftday"
        )
        self.assertEqual(EmployeeShiftDay._meta.db_table, expected)

    def test_explicit_meta_db_table_unchanged(self):
        self.assertEqual(LegacyUser._meta.db_table, "auth_user")

    def test_custom_user_model_gets_prefix(self):
        prefix = settings.DB_TABLE_PREFIX or ""
        expected = (
            f"{prefix}horilla_auth_horillauser"
            if prefix
            else "horilla_auth_horillauser"
        )
        self.assertEqual(HorillaUser._meta.db_table, expected)
