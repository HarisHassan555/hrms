"""
Repair or create the candidate rejection notice mail automation.

Usage:
    python manage.py configure_candidate_reject_automation
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from horilla_automations.migrations.0006_configure_candidate_reject_automation import (
    MAIL_DETAILS,
    MAIL_TO,
    MODEL_PATH,
    TEMPLATE_TITLE,
    _refresh_automation_signals,
    configure_candidate_reject_automation,
)


class Command(BaseCommand):
    help = (
        "Configure the candidate rejection mail automation "
        "(RejectedCandidate on create, email to candidate)."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        from django.apps import apps as django_apps

        configure_candidate_reject_automation(django_apps, None)
        _refresh_automation_signals()

        from base.models import HorillaMailTemplate
        from horilla_automations.models import MailAutomation

        auto = MailAutomation.objects.filter(
            model=MODEL_PATH, trigger="on_create"
        ).first()
        tmpl = HorillaMailTemplate.objects.filter(title=TEMPLATE_TITLE).first()

        self.stdout.write(
            self.style.SUCCESS("Candidate rejection automation configured.")
        )
        if auto:
            self.stdout.write(
                f"  Automation: {auto.title} (id={auto.pk}, active={auto.is_active})"
            )
            self.stdout.write(f"  Model: {auto.model}")
            self.stdout.write(f"  Trigger: {auto.trigger}")
            self.stdout.write(f"  Mail to: {auto.mail_to}")
            self.stdout.write(f"  Mail details: {auto.mail_details}")
        if tmpl:
            self.stdout.write(f"  Template: {tmpl.title} (id={tmpl.pk})")
        self.stdout.write(
            "\nTest: reject a candidate in Recruitment (Reject action). "
            "Requires a working mail server under Settings → Email."
        )
        self.stdout.write(f"  Expected mail_to: {MAIL_TO}")
        self.stdout.write(f"  Expected mail_details: {MAIL_DETAILS}")
