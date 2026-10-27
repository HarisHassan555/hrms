from django.test import TestCase

from base.mail_template_catalog import (
    ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE,
    RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE,
    ensure_onboarding_complete_profile_portal_mail_template,
    ensure_recruitment_candidate_portal_mail_template,
)
from base.models import HorillaMailTemplate


class PortalMailTemplateCatalogTests(TestCase):
    def test_recruitment_template_renames_legacy_title(self):
        HorillaMailTemplate.objects.filter(
            title=RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE
        ).delete()
        legacy = HorillaMailTemplate.objects.create(
            title="Candidate Portal Login",
            body="<p>legacy</p>",
        )
        ensure_recruitment_candidate_portal_mail_template()
        legacy.refresh_from_db()
        self.assertEqual(legacy.title, RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE)
        self.assertFalse(
            HorillaMailTemplate.objects.filter(
                title="Candidate Portal Login"
            ).exists()
        )

    def test_onboarding_template_created_with_distinct_title(self):
        ensure_onboarding_complete_profile_portal_mail_template()
        self.assertTrue(
            HorillaMailTemplate.objects.filter(
                title=ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE
            ).exists()
        )
        self.assertNotEqual(
            RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE,
            ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE,
        )

    def test_onboarding_template_upgrades_legacy_short_body(self):
        legacy, _created = HorillaMailTemplate.objects.get_or_create(
            title=ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE,
            defaults={"body": "<p>placeholder</p>"},
        )
        legacy.body = (
            "<p>Hi {{instance.get_full_name}},</p><p>Short legacy body.</p>"
        )
        legacy.save(update_fields=["body"])
        ensure_onboarding_complete_profile_portal_mail_template()
        legacy.refresh_from_db()
        self.assertIn("Onboarding Portal — Complete Profile Details", legacy.body)
        self.assertIn("get_onboarding_portal_path", legacy.body)
