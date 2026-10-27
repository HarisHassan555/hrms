"""Recruitment vs onboarding portal mail templates render with correct localhost URLs."""

from django import template
from django.test import RequestFactory, TestCase

from base.methods import sanitize_mail_template_body
from base.mail_template_catalog import (
    HARDCODED_MAIL_BASE_URL,
    ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE,
    RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE,
    build_candidate_mail_template_context,
    build_onboarding_portal_absolute_url,
    ensure_onboarding_complete_profile_portal_mail_template,
    ensure_recruitment_candidate_portal_mail_template,
    onboarding_complete_profile_portal_template_body,
    recruitment_candidate_portal_template_body,
)
from base.models import HorillaMailTemplate
from horilla.testkit import make_company
from horilla.testkit.factories import make_candidate, make_recruitment
from onboarding.models import OnboardingPortal


class _MailSender:
    def get_full_name(self):
        return "HR Sender"

    def get_department(self):
        return "Human Resources"

    def get_company(self):
        return "DSG"


def _render(body: str, context: dict) -> str:
    tpl = template.Template(sanitize_mail_template_body(body))
    return tpl.render(template.Context(context))


class PortalMailTemplateRenderingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/")
        self.request.user = type(
            "U",
            (),
            {"employee_get": _MailSender(), "is_authenticated": True},
        )()
        company = make_company("DSG")
        self.recruitment = make_recruitment(company=company, title="Engineering Hire")
        self.candidate = make_candidate(
            recruitment=self.recruitment,
            email="candidate@example.com",
            name="Haris Hassan",
            hired=True,
        )
        self.candidate.mobile = "5559876543"
        self.candidate.save(update_fields=["mobile"])

    def test_canonical_recruitment_template_body_has_localhost_login(self):
        body = recruitment_candidate_portal_template_body()
        self.assertIn(
            f"{HARDCODED_MAIL_BASE_URL}/recruitment/candidate-login/", body
        )
        self.assertIn("{{instance.email}}", body)
        self.assertIn("{{instance.mobile}}", body)

    def test_canonical_onboarding_template_body_has_localhost_portal_path(self):
        body = onboarding_complete_profile_portal_template_body()
        self.assertIn("get_onboarding_portal_path", body)
        self.assertIn(HARDCODED_MAIL_BASE_URL, body)
        self.assertIn("Onboarding Portal — Complete Profile Details", body)

    def test_ensure_creates_both_templates_in_database(self):
        ensure_recruitment_candidate_portal_mail_template()
        ensure_onboarding_complete_profile_portal_mail_template()
        recruitment = HorillaMailTemplate.objects.get(
            title=RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE
        )
        onboarding = HorillaMailTemplate.objects.get(
            title=ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE
        )
        self.assertIn(
            f"{HARDCODED_MAIL_BASE_URL}/recruitment/candidate-login/",
            recruitment.body,
        )
        self.assertIn("get_onboarding_portal_path", onboarding.body)

    def test_render_recruitment_email_for_candidate(self):
        ensure_recruitment_candidate_portal_mail_template()
        row = HorillaMailTemplate.objects.get(
            title=RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE
        )
        ctx = build_candidate_mail_template_context(self.request, self.candidate)
        ctx["self"] = _MailSender()
        html = _render(row.body, ctx)
        self.assertIn(
            f"{HARDCODED_MAIL_BASE_URL}/recruitment/candidate-login/", html
        )
        self.assertIn("candidate@example.com", html)
        self.assertIn("5559876543", html)
        self.assertIn("Recruitment candidate portal", html)

    def test_render_onboarding_email_includes_portal_token_url(self):
        ensure_onboarding_complete_profile_portal_mail_template()
        OnboardingPortal.objects.create(
            candidate_id=self.candidate, token="abc123def456"
        )
        row = HorillaMailTemplate.objects.get(
            title=ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE
        )
        ctx = build_candidate_mail_template_context(
            self.request, self.candidate, ensure_onboarding_portal=False
        )
        ctx["self"] = _MailSender()
        html = _render(row.body, ctx)
        expected = (
            f"{HARDCODED_MAIL_BASE_URL}/onboarding/user-creation/abc123def456"
        )
        self.assertIn(expected, html)
        self.assertIn("candidate@example.com", html)
        self.assertIn("5559876543", html)
        self.assertIn("Onboarding Portal — Complete Profile Details", html)
        self.assertNotIn("/recruitment/candidate-login/", html)

    def test_build_onboarding_portal_absolute_url_creates_row(self):
        self.assertFalse(
            OnboardingPortal.objects.filter(candidate_id=self.candidate).exists()
        )
        url = build_onboarding_portal_absolute_url(
            self.request, self.candidate, create=True
        )
        self.assertTrue(url.startswith(f"{HARDCODED_MAIL_BASE_URL}/onboarding/user-creation/"))
        self.assertTrue(
            OnboardingPortal.objects.filter(candidate_id=self.candidate).exists()
        )
