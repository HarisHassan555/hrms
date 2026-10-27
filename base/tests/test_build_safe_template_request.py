from django.http import HttpRequest
from django.template import Context, Template
from django.test import SimpleTestCase, override_settings

from base.methods import build_safe_template_request, get_public_site_origin


@override_settings(ALLOWED_HOSTS=["hrms.example.com"])
class BuildSafeTemplateRequestTests(SimpleTestCase):
    def test_scheme_and_host_available_in_mail_templates(self):
        request = HttpRequest()
        request.META["HTTP_HOST"] = "hrms.example.com"
        safe = build_safe_template_request(request)
        rendered = Template(
            "{{ request.scheme }}://{{ request.get_host }}/recruitment/candidate-login/"
        ).render(Context({"request": safe}))
        self.assertEqual(
            rendered, "http://hrms.example.com/recruitment/candidate-login/"
        )

    @override_settings(CSRF_TRUSTED_ORIGINS=["https://public.hrms.example.com"])
    def test_forwarded_host_used_for_public_origin(self):
        request = HttpRequest()
        request.META["HTTP_HOST"] = "localhost:8000"
        request.META["HTTP_X_FORWARDED_HOST"] = "public.hrms.example.com"
        request.META["HTTP_X_FORWARDED_PROTO"] = "https"
        self.assertEqual(
            get_public_site_origin(request), "https://public.hrms.example.com"
        )
