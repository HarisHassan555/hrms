"""
Create a demo policy with multiple slideshow pages for Policies & Discipline.
"""

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from base.models import Company
from employee.models import Policy, PolicySlide


SAMPLE_TITLE = "Sample: Workplace Conduct (Slideshow)"


class Command(BaseCommand):
    help = "Create a sample policy with multi-page slideshow for training/demo."

    def handle(self, *args, **options):
        existing = Policy.objects.filter(title=SAMPLE_TITLE).first()
        if existing:
            policy = existing
            if policy.slides.exists():
                self.stdout.write(
                    self.style.WARNING("Sample slideshow policy already exists.")
                )
                self.stdout.write(
                    f"Policy id={policy.pk} — open Policies & Discipline → View Policy."
                )
                return
            policy.body_format = Policy.BodyFormat.SLIDESHOW
            policy.save(update_fields=["body_format"])
            self.stdout.write(
                self.style.WARNING(
                    f"Sample policy id={policy.pk} exists without slides; adding slides."
                )
            )
        else:
            policy = None

        company = Company.objects.filter(hq=True).first() or Company.objects.first()
        if policy is None:
            policy = Policy.objects.create(
                title=SAMPLE_TITLE,
                body_format=Policy.BodyFormat.SLIDESHOW,
                body="",
                is_visible_to_all=True,
            )
            if company:
                policy.company_id.add(company)

        slides = [
            (
                0,
                _("How to use this format"),
                _(
                    "This policy uses multiple pages. Use Previous / Next or the dots "
                    "when viewing. HR chooses Single page or Multiple pages under Policy body "
                    "when creating or editing a policy."
                ),
            ),
            (
                1,
                _("Welcome"),
                _(
                    "This slide deck explains how DSG expects everyone to work together "
                    "respectfully and safely."
                ),
            ),
            (
                2,
                _("Respect & inclusion"),
                _(
                    "Treat colleagues, candidates, and partners with respect. "
                    "Harassment and discrimination are not tolerated."
                ),
            ),
            (
                3,
                _("Reporting concerns"),
                _(
                    "Speak with your manager or HR if you see conduct that violates policy. "
                    "You can also use the helpdesk for confidential questions."
                ),
            ),
        ]
        for order, title, body in slides:
            PolicySlide.objects.create(
                policy=policy,
                sort_order=order,
                title=title,
                body=body,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created sample policy id={policy.pk} with {len(slides)} slides."
            )
        )
        self.stdout.write("Open Employee → Policies & Discipline → Policies tab → View Policy.")
