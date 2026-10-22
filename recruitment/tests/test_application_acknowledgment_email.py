"""Public apply flow sends a thank-you acknowledgment email."""

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from base.models import Department, JobPosition
from horilla.testkit import make_company
from recruitment.models import Recruitment, RecruitmentGeneralSetting

PDF = b"%PDF-1.4 fake resume bytes"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ApplicationAcknowledgmentEmailTests(TestCase):
    def setUp(self):
        company = make_company("Ack Test Co")
        dept = Department.objects.create(department="HR")
        dept.company_id.add(company)
        self.job = JobPosition.objects.create(
            job_position="Senior HR Analyst", department_id=dept
        )
        self.recruitment = Recruitment.objects.create(
            title="HR Analyst Hiring 2026",
            description="Role description",
            company_id=company,
            job_position_id=self.job,
            vacancy=2,
            is_published=True,
            optional_resume=True,
            optional_profile_image=True,
        )
        self.recruitment.open_positions.add(self.job)

    def test_application_post_sends_acknowledgment_email(self):
        response = self.client.post(
            reverse("application-form") + f"?recruitmentId={self.recruitment.id}",
            {
                "recruitment_id": self.recruitment.id,
                "job_position_id": self.job.id,
                "name": "Jane Applicant",
                "email": "jane.applicant@example.com",
                "mobile": "5551234567",
                "referral_source": "company_career_site",
                "resume": SimpleUploadedFile(
                    "resume.pdf", PDF, content_type="application/pdf"
                ),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn("jane.applicant@example.com", message.to)
        self.assertIn("Senior HR Analyst", message.subject)
        self.assertIn("Jane Applicant", message.body)
        self.assertTrue(message.alternatives)
        html, mime = message.alternatives[0]
        self.assertEqual(mime, "text/html")
        self.assertIn("Jane Applicant", html)
        self.assertIn("Senior HR Analyst", html)

    def test_acknowledgment_skipped_when_setting_disabled(self):
        RecruitmentGeneralSetting.objects.create(
            company_id=self.recruitment.company_id,
            application_acknowledgment_email=False,
        )
        response = self.client.post(
            reverse("application-form") + f"?recruitmentId={self.recruitment.id}",
            {
                "recruitment_id": self.recruitment.id,
                "job_position_id": self.job.id,
                "name": "Jane Applicant",
                "email": "jane.applicant@example.com",
                "mobile": "5551234567",
                "referral_source": "company_career_site",
                "resume": SimpleUploadedFile(
                    "resume.pdf", PDF, content_type="application/pdf"
                ),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
