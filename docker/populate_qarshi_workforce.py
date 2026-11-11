"""
Populate operational demo data for all active employees on production.

Run on server:
  cd /app && python manage.py shell < docker/populate_qarshi_workforce.py
"""

from __future__ import annotations

import sys

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction

from base.demo_data.runner import run_enterprise_demo_seeder
from employee.models import Employee
from seeders import pakistan_attendance_leave_seeder as att_leave
from seeders.utils import SeederResult

TARGET_EMAIL = "fariarehman41@gmail.com"
TARGET_PASSWORD = "faria1122"


def ensure_target_user():
    User = get_user_model()
    user = User.objects.filter(email__iexact=TARGET_EMAIL).first()
    if not user:
        emp = Employee.objects.filter(email__iexact=TARGET_EMAIL, is_active=True).first()
        if not emp:
            print(f"ERROR: No user or employee for {TARGET_EMAIL}", file=sys.stderr)
            return False
        user = User.objects.filter(employee_get=emp).first()
        if not user:
            print(
                f"ERROR: Employee exists but no login user for {TARGET_EMAIL}",
                file=sys.stderr,
            )
            return False
    user.set_password(TARGET_PASSWORD)
    user.is_active = True
    user.save(update_fields=["password", "is_active"])
    emp = Employee.objects.filter(email__iexact=TARGET_EMAIL, is_active=True).first()
    if emp and emp.employee_user_id_id != user.pk:
        emp.employee_user_id = user
        emp.save(update_fields=["employee_user_id"])
    print(f"OK: login ready for {user.email} (employee linked: {bool(emp)})")
    return True


@transaction.atomic
def seed_attendance_leave_all_companies():
    from base.models import Company

    companies = list(Company.objects.all().order_by("pk"))
    if not companies:
        print("WARN: no companies in database")
        return
    result = SeederResult()
    att_leave._seed_attendance(companies, result)
    att_leave._seed_leave(companies, result)
    print(
        f"Attendance/leave seed: created={result.created} updated={result.updated} "
        f"existing={result.existing}"
    )


def main():
    if not ensure_target_user():
        return

    print("Running enterprise demo backfills (all modules, idempotent)…")
    summary = run_enterprise_demo_seeder(copy_media=False, scrub_side_files=False)
    print(f"Enterprise backfill keys: {', '.join(sorted(summary.keys()))}")

    print("Seeding attendance + leave for all companies / employees…")
    seed_attendance_leave_all_companies()

    print("Seeding LMS demo assignments…")
    try:
        call_command("seed_lms_demo", verbosity=1)
    except Exception as exc:
        print(f"WARN: seed_lms_demo: {exc}")

    for mod in (
        "pakistan_payroll",
        "pakistan_pms",
        "pakistan_helpdesk",
        "pakistan_projects",
        "pakistan_recruitment",
    ):
        try:
            print(f"Running seed_data --module {mod} …")
            call_command("seed_data", module=mod, verbosity=1)
        except Exception as exc:
            print(f"WARN: {mod}: {exc}")

    active = Employee.objects.filter(is_active=True).count()
    print(f"Done. Active employees: {active}")


main()
