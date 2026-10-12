from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from asset.models import AssetCategory
from base.models import Company, Department, JobPosition
from leave.models import LeaveType


class SeedDataCommandTests(TestCase):
    def call_seed(self, *args):
        out = StringIO()
        call_command("seed_data", *args, stdout=out)
        return out.getvalue()

    def test_initial_seed_creates_master_records(self):
        self.call_seed()

        self.assertTrue(Company.objects.filter(company="Default Company").exists())
        self.assertTrue(
            Department.objects.filter(department="Human Resources").exists()
        )
        self.assertTrue(
            AssetCategory.objects.filter(asset_category_name="Laptop").exists()
        )
        self.assertTrue(LeaveType.objects.filter(name="Casual Leave").exists())

    def test_seed_is_idempotent(self):
        self.call_seed()
        counts = {
            "companies": Company.objects.count(),
            "departments": Department.objects.count(),
            "asset_categories": AssetCategory.objects.count(),
            "leave_types": LeaveType.objects.count(),
        }

        self.call_seed()

        self.assertEqual(counts["companies"], Company.objects.count())
        self.assertEqual(counts["departments"], Department.objects.count())
        self.assertEqual(counts["asset_categories"], AssetCategory.objects.count())
        self.assertEqual(counts["leave_types"], LeaveType.objects.count())

    def test_seed_updates_canonical_master_values(self):
        self.call_seed("--module", "organization")
        self.call_seed("--module", "asset")

        category = AssetCategory.objects.get(asset_category_name="Laptop")
        category.asset_category_description = "Custom old value"
        category.save()

        self.call_seed("--module", "asset")

        category.refresh_from_db()
        self.assertEqual(
            category.asset_category_description,
            "Portable computers assigned to employees.",
        )

    def test_foreign_keys_point_to_seeded_parent_records(self):
        self.call_seed("--module", "organization")

        department = Department.objects.get(department="Information Technology")
        job_position = JobPosition.objects.get(job_position="Software Engineer")

        self.assertEqual(job_position.department_id, department)

    def test_module_execution_only_runs_requested_module(self):
        self.call_seed("--module", "asset")

        self.assertTrue(
            AssetCategory.objects.filter(asset_category_name="Laptop").exists()
        )
        self.assertFalse(
            Department.objects.filter(department="Human Resources").exists()
        )

    def test_dry_run_rolls_back_changes(self):
        self.call_seed("--dry-run")

        self.assertFalse(Company.objects.filter(company="Default Company").exists())
