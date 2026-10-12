from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from base.models import Company, CompanyGroupAssignment, Department
from employee.models import Employee, EmployeeWorkInformation
from horilla_auth.models import HorillaUser


class QarshiSeederTests(TestCase):
    def call_qarshi_seed(self):
        out = StringIO()
        call_command("seed_data", "--module", "qarshi", stdout=out)
        return out.getvalue()

    def test_qarshi_seed_creates_company_and_four_users(self):
        self.call_qarshi_seed()

        company = Company.objects.get(company="Qarshi Industries")
        self.assertTrue(
            Department.objects.filter(department="HR Department").exists()
        )
        self.assertTrue(
            Department.objects.filter(department="IT Department").exists()
        )
        self.assertEqual(
            Employee.objects.filter(
                email__endswith="@qarshi-industries.com"
            ).count(),
            4,
        )
        admin = HorillaUser.objects.get(username="qarshi.admin@qarshi-industries.com")
        self.assertTrue(
            CompanyGroupAssignment.objects.filter(
                user=admin, company=company, group__name="Admin"
            ).exists()
        )
        staff = Employee.objects.get(email="staff.shared@qarshi-industries.com")
        work_info = EmployeeWorkInformation.objects.get(employee_id=staff)
        hr_manager = Employee.objects.get(email="hr.manager@qarshi-industries.com")
        self.assertEqual(work_info.reporting_manager_id, hr_manager)

    def test_qarshi_seed_is_idempotent(self):
        self.call_qarshi_seed()
        counts = {
            "companies": Company.objects.filter(company="Qarshi Industries").count(),
            "users": HorillaUser.objects.filter(
                username__endswith="@qarshi-industries.com"
            ).count(),
        }
        self.call_qarshi_seed()
        self.assertEqual(
            counts["companies"],
            Company.objects.filter(company="Qarshi Industries").count(),
        )
        self.assertEqual(
            counts["users"],
            HorillaUser.objects.filter(
                username__endswith="@qarshi-industries.com"
            ).count(),
        )
