"""
Promote the SaaS platform operator (Data Sphere Global) to Django superuser.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from base.models import Company
from employee.models import Employee
from horilla_auth.models import HorillaUser


class Command(BaseCommand):
    help = (
        "Grant platform superuser to a user (by email) and optionally mark "
        "the owner company as HQ for branding."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            required=True,
            help="Login email of the Data Sphere Global (platform) user",
        )
        parser.add_argument(
            "--company",
            default=None,
            help="Company name to mark as HQ (default: first PLATFORM_OWNER_COMPANY_NAMES)",
        )
        parser.add_argument(
            "--no-hq",
            action="store_true",
            help="Do not update company HQ flag",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        email = (options["email"] or "").strip()
        if not email:
            raise CommandError("--email is required")

        user = (
            HorillaUser.objects.filter(email__iexact=email).first()
            or HorillaUser.objects.filter(username__iexact=email).first()
        )
        if user is None:
            employee = Employee.objects.filter(email__iexact=email).select_related(
                "employee_user_id"
            ).first()
            if employee and employee.employee_user_id:
                user = employee.employee_user_id

        if user is None:
            raise CommandError(f"No user found for email/username: {email}")

        user.is_superuser = True
        user.is_staff = True
        user.save(update_fields=["is_superuser", "is_staff"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Platform superuser enabled for {user.username} ({user.email})"
            )
        )

        if options["no_hq"]:
            return

        from django.conf import settings

        company_name = options["company"]
        if not company_name:
            names = getattr(settings, "PLATFORM_OWNER_COMPANY_NAMES", None) or []
            company_name = names[0] if names else "Data Sphere Global"

        company = Company.objects.filter(company__iexact=company_name.strip()).first()
        if company is None:
            self.stdout.write(
                self.style.WARNING(
                    f'Company "{company_name}" not found — skipped HQ flag'
                )
            )
            return

        if not company.hq:
            company.hq = True
            company.save(update_fields=["hq"])
            self.stdout.write(self.style.SUCCESS(f'Marked "{company.company}" as HQ'))
