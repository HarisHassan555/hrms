"""
Repair or create the "Candidate apply" acknowledgment mail automation.

Usage:
    python manage.py configure_candidate_apply_automation
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from horilla_automations.migrations.0005_configure_candidate_apply_automation import (
    CONDITION_QUERYSTRING,
    MAIL_BODY,
    MODEL_PATH,
    TEMPLATE_TITLE,
    _refresh_automation_signals,
    configure_candidate_apply_automation,
)


class Command(BaseCommand):
    help = (
        "Configure the Candidate apply mail automation for public job applications "
        "(source=application, on create)."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        from django.apps import apps as django_apps

        configure_candidate_apply_automation(django_apps, None)
        _refresh_automation_signals()

        from base.models import HorillaMailTemplate
        from horilla_automations.models import MailAutomation

        auto = MailAutomation.objects.filter(title__icontains="candidate apply").first()
        if auto is None:
            auto = MailAutomation.objects.filter(method_title="candidate_apply").first()

        tmpl = HorillaMailTemplate.objects.filter(title=TEMPLATE_TITLE).first()

        self.stdout.write(self.style.SUCCESS("Candidate apply automation configured."))
        if auto:
            self.stdout.write(f"  Automation: {auto.title} (id={auto.pk}, active={auto.is_active})")
            self.stdout.write(f"  Model: {auto.model}")
            self.stdout.write(f"  Trigger: {auto.trigger}")
            self.stdout.write(f"  Mail to: {auto.mail_to}")
            self.stdout.write(f"  Mail details: {auto.mail_details}")
            self.stdout.write(f"  Condition: {auto.condition_querystring or '(none — fires on every create)'}")
        if tmpl:
            self.stdout.write(f"  Template: {tmpl.title} (id={tmpl.pk})")
        self.stdout.write(
            "\nTest: submit a career-page application (source=application). "
            "Requires a working mail server under Settings → Email."
        )
