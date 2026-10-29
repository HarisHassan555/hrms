"""Recruitment vs onboarding portal mail templates follow the request host."""

from django import template
from django.test import RequestFactory, TestCase, override_settings

from base.methods import sanitize_mail_template_body
from base.mail_template_catalog import (
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


@override_settings(ALLOWED_HOSTS=["localhost", "127.0.0.1", "192.168.168.31", "testserver"])
class PortalMailTemplateRenderingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/", HTTP_HOST="localhost:8000")
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

    def test_canonical_recruitment_template_body_uses_request_host(self):
        body = recruitment_candidate_portal_template_body()
        self.assertIn(
            "{{ request.scheme }}://{{ request.get_host }}/recruitment/candidate-login/",
            body,
        )
        self.assertNotIn("localhost:8000", body)
        self.assertNotIn("192.168.168.31", body)
        self.assertIn("{{instance.email}}", body)
        self.assertIn("{{instance.mobile}}", body)

    def test_canonical_onboarding_template_body_uses_portal_context_var(self):
        body = onboarding_complete_profile_portal_template_body()
        self.assertIn("{{ portal }}", body)
        self.assertNotIn("get_onboarding_portal_path", body)
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
            "{{ request.scheme }}://{{ request.get_host }}/recruitment/candidate-login/",
            recruitment.body,
        )
        self.assertIn("{{ portal }}", onboarding.body)
        self.assertNotIn("get_onboarding_portal_path", onboarding.body)

    def test_render_recruitment_email_follows_localhost(self):
        ensure_recruitment_candidate_portal_mail_template()
        row = HorillaMailTemplate.objects.get(
            title=RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE
        )
        ctx = build_candidate_mail_template_context(self.request, self.candidate)
        ctx["self"] = _MailSender()
        html = _render(row.body, ctx)
        self.assertIn("http://localhost:8000/recruitment/candidate-login/", html)
        self.assertIn("candidate@example.com", html)
        self.assertIn("5559876543", html)
        self.assertIn("Recruitment candidate portal", html)

    def test_render_recruitment_email_follows_lan_host(self):
        ensure_recruitment_candidate_portal_mail_template()
        request = self.factory.get("/", HTTP_HOST="192.168.168.31:8000")
        request.user = self.request.user
        row = HorillaMailTemplate.objects.get(
            title=RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE
        )
        ctx = build_candidate_mail_template_context(request, self.candidate)
        ctx["self"] = _MailSender()
        html = _render(row.body, ctx)
        self.assertIn(
            "http://192.168.168.31:8000/recruitment/candidate-login/", html
        )

    def test_render_onboarding_email_includes_portal_token_url(self):
        ensure_onboarding_complete_profile_portal_mail_template()
        OnboardingPortal.objects.create(
            candidate_id=self.candidate, token="abc123def456"
        )
        row = HorillaMailTemplate.objects.get(
            title=ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE
        )
        ctx = build_candidate_mail_template_context(
            self.request, self.candidate, ensure_onboarding_portal=True
        )
        ctx["self"] = _MailSender()
        html = _render(row.body, ctx)
        expected = "http://localhost:8000/onboarding/user-creation/abc123def456"
        self.assertEqual(ctx["portal"], expected)
        self.assertIn(expected, html)
        self.assertIn(f'href="{expected}"', html)
        self.assertIn("candidate@example.com", html)
        self.assertIn("5559876543", html)
        self.assertIn("Onboarding Portal — Complete Profile Details", html)
        self.assertNotIn("/recruitment/candidate-login/", html)

    def test_render_onboarding_email_follows_lan_host(self):
        ensure_onboarding_complete_profile_portal_mail_template()
        OnboardingPortal.objects.create(
            candidate_id=self.candidate, token="abc123def456"
        )
        request = self.factory.get("/", HTTP_HOST="192.168.168.31:8000")
        request.user = self.request.user
        row = HorillaMailTemplate.objects.get(
            title=ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE
        )
        ctx = build_candidate_mail_template_context(
            request, self.candidate, ensure_onboarding_portal=True
        )
        ctx["self"] = _MailSender()
        html = _render(row.body, ctx)
        expected = (
            "http://192.168.168.31:8000/onboarding/user-creation/abc123def456"
        )
        self.assertEqual(ctx["portal"], expected)
        self.assertIn(expected, html)

    def test_render_creates_portal_and_uses_full_url(self):
        ensure_onboarding_complete_profile_portal_mail_template()
        self.assertFalse(
            OnboardingPortal.objects.filter(candidate_id=self.candidate).exists()
        )
        row = HorillaMailTemplate.objects.get(
            title=ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE
        )
        ctx = build_candidate_mail_template_context(
            self.request, self.candidate, ensure_onboarding_portal=True
        )
        ctx["self"] = _MailSender()
        html = _render(row.body, ctx)
        self.assertTrue(
            ctx["portal"].startswith(
                "http://localhost:8000/onboarding/user-creation/"
            )
        )
        self.assertIn(ctx["portal"], html)
        self.assertIn(f'href="{ctx["portal"]}"', html)
        self.assertIn("/onboarding/user-creation/", html)

    def test_build_onboarding_portal_absolute_url_creates_row(self):
        self.assertFalse(
            OnboardingPortal.objects.filter(candidate_id=self.candidate).exists()
        )
        url = build_onboarding_portal_absolute_url(
            self.request, self.candidate, create=True
        )
        self.assertTrue(
            url.startswith("http://localhost:8000/onboarding/user-creation/")
        )
        self.assertTrue(
            OnboardingPortal.objects.filter(candidate_id=self.candidate).exists()
        )
