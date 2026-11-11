from __future__ import annotations

import sys

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from base.demo_data.runner import run_enterprise_demo_seeder
from employee.models import Employee
from seeders import pakistan_attendance_leave_seeder as att_leave
from seeders.utils import SeederResult


class Command(BaseCommand):
    help = (
        "Idempotent operational demo backfill for all active employees "
        "(attendance, leave, dashboards, LMS, optional PK seed modules)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--employee-email",
            default="fariarehman41@gmail.com",
            help="Ensure this login exists and reset password.",
        )
        parser.add_argument(
            "--employee-password",
            default="faria1122",
            help="Password to set for --employee-email.",
        )
        parser.add_argument(
            "--skip-enterprise",
            action="store_true",
            help="Skip run_enterprise_demo_seeder backfills.",
        )

    def handle(self, *args, **options):
        email = (options["employee_email"] or "").strip()
        password = options["employee_password"] or ""
        if email and password:
            if not self._ensure_user(email, password):
                sys.exit(1)

        if not options["skip_enterprise"]:
            self.stdout.write("Running enterprise demo backfills…")
            try:
                summary = run_enterprise_demo_seeder(
                    copy_media=False, scrub_side_files=False
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        "Enterprise backfill: "
                        + ", ".join(sorted(summary.keys()))
                    )
                )
            except Exception as exc:
                self.stdout.write(
                    self.style.WARNING(
                        f"Enterprise backfill stopped early ({exc!s}); "
                        "continuing with module seeders."
                    )
                )

        self.stdout.write("Seeding attendance + leave for all companies…")
        self._seed_attendance_leave_all_companies()

        from django.core.management import call_command

        self.stdout.write("Seeding LMS demo…")
        try:
            call_command("seed_lms_demo", verbosity=1)
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"seed_lms_demo: {exc}"))

        for mod in (
            "pakistan_payroll",
            "pakistan_pms",
            "pakistan_helpdesk",
            "pakistan_projects",
            "pakistan_recruitment",
        ):
            try:
                self.stdout.write(f"seed_data --module {mod}")
                call_command("seed_data", module=mod, verbosity=1)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"{mod}: {exc}"))

        active = Employee.objects.filter(is_active=True).count()
        self.stdout.write(
            self.style.SUCCESS(f"Done. Active employees: {active}")
        )

    def _ensure_user(self, email: str, password: str) -> bool:
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            emp = Employee.objects.filter(
                email__iexact=email, is_active=True
            ).first()
            if not emp:
                self.stderr.write(f"No user or employee for {email}")
                return False
            user = User.objects.filter(employee_get=emp).first()
            if not user:
                self.stderr.write(f"No login user linked to employee {email}")
                return False
        user.set_password(password)
        user.is_active = True
        user.save(update_fields=["password", "is_active"])
        emp = Employee.objects.filter(email__iexact=email, is_active=True).first()
        if emp and emp.employee_user_id_id != user.pk:
            emp.employee_user_id = user
            emp.save(update_fields=["employee_user_id"])
        self.stdout.write(
            self.style.SUCCESS(f"Login ready for {user.email}")
        )
        return True

    @transaction.atomic
    def _seed_attendance_leave_all_companies(self) -> None:
        from base.models import Company

        companies = list(Company.objects.all().order_by("pk"))
        if not companies:
            self.stdout.write(self.style.WARNING("No companies found."))
            return
        result = SeederResult()
        att_leave._seed_attendance(companies, result)
        att_leave._seed_leave(companies, result)
        self.stdout.write(
            f"Attendance/leave: created={result.created}, "
            f"updated={result.updated}, existing={result.existing}"
        )
