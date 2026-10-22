from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from base.models import CompanyGroupAssignment
from employee.models import Employee, EmployeeWorkInformation
from horilla_auth.models import HorillaUser

from seeders.admin_team_seeder import EMAIL_DOMAIN, EMPLOYEE_COUNT, GROUP_NAME


class AdminTeamSeederTests(TestCase):
    def call_admin_team_seed(self):
        out = StringIO()
        call_command("seed_data", "--module", "admin_team", stdout=out)
        return out.getvalue()

    def test_creates_twenty_admin_employees(self):
        self.call_admin_team_seed()
        emails = [f"admin.team{i:02d}@{EMAIL_DOMAIN}" for i in range(1, EMPLOYEE_COUNT + 1)]
        self.assertEqual(Employee.objects.filter(email__in=emails).count(), EMPLOYEE_COUNT)
        user = HorillaUser.objects.get(username=emails[0])
        company = EmployeeWorkInformation.objects.get(employee_id__email=emails[0]).company_id
        self.assertTrue(
            CompanyGroupAssignment.objects.filter(
                user=user, company=company, group__name=GROUP_NAME
            ).exists()
        )
        work_info = EmployeeWorkInformation.objects.get(employee_id__email=emails[1])
        self.assertIsNotNone(work_info.shift_id)
        self.assertEqual(work_info.shift_id.employee_shift, "General Shift")

    def test_admin_team_seed_is_idempotent(self):
        self.call_admin_team_seed()
        count = Employee.objects.filter(email__endswith=f"@{EMAIL_DOMAIN}").count()
        self.call_admin_team_seed()
        self.assertEqual(
            count,
            Employee.objects.filter(email__endswith=f"@{EMAIL_DOMAIN}").count(),
        )
