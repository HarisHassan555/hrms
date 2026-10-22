"""
Ensure the "Candidate apply" mail automation fires for public job applications.

Updates any automation whose title contains "candidate apply", or creates one
if missing. Also seeds a default thank-you mail template when needed.
"""

from django.db import migrations

TEMPLATE_TITLE = "Candidate application thank you"
AUTOMATION_TITLE = "Candidate apply"
MODEL_PATH = "recruitment.models.Candidate"
CONDITION_QUERYSTRING = (
    "automation_multiple_condition=source"
    "&condition=="
    "&automation_multiple_condition=application"
    "&logic=and"
)
MAIL_BODY = """<p>Hi {{ instance.name }},</p>
<p>Thank you for applying for <strong>{{ instance.job_position_id }}</strong>.</p>
<p>We have received your application for <strong>{{ instance.recruitment_id.title }}</strong>. Our team will review your profile and contact you if you are shortlisted for the next stage.</p>
<p>Best regards,<br>HR Team</p>"""


def _refresh_automation_signals():
    try:
        from horilla_automations.signals import REFRESH_METHODS

        start = REFRESH_METHODS.get("start_connection")
        if start:
            start()
    except Exception:
        pass


def configure_candidate_apply_automation(apps, schema_editor):
    if not apps.is_installed("recruitment"):
        return

    HorillaMailTemplate = apps.get_model("base", "HorillaMailTemplate")
    MailAutomation = apps.get_model("horilla_automations", "MailAutomation")

    template = HorillaMailTemplate.objects.filter(title=TEMPLATE_TITLE).first()
    if template is None:
        template = HorillaMailTemplate.objects.create(
            title=TEMPLATE_TITLE,
            body=MAIL_BODY,
        )
    else:
        HorillaMailTemplate.objects.filter(pk=template.pk).update(body=MAIL_BODY)

    automations = list(
        MailAutomation.objects.filter(title__icontains="candidate apply")
    )
    if not automations:
        automations = list(
            MailAutomation.objects.filter(method_title="candidate_apply")
        )

    subject_title = "Thank you for applying - {{ instance.recruitment_id.title }}"

    for auto in automations:
        auto.title = subject_title
        auto.model = MODEL_PATH
        auto.trigger = "on_create"
        auto.mail_to = str(["get_email"])
        auto.mail_details = "pk"
        auto.delivery_channel = "email"
        auto.is_active = True
        auto.condition_querystring = CONDITION_QUERYSTRING
        auto.condition = CONDITION_QUERYSTRING
        if not auto.mail_template_id:
            auto.mail_template_id = template.pk
        auto.save()

    if not automations:
        MailAutomation.objects.create(
            title=subject_title,
            method_title="candidate_apply",
            model=MODEL_PATH,
            trigger="on_create",
            mail_to=str(["get_email"]),
            mail_details="pk",
            mail_template_id=template.pk,
            delivery_channel="email",
            is_active=True,
            condition_querystring=CONDITION_QUERYSTRING,
            condition=CONDITION_QUERYSTRING,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("horilla_automations", "0004_alter_mailautomation_table"),
    ]

    operations = [
        migrations.RunPython(configure_candidate_apply_automation, noop_reverse),
        migrations.RunPython(lambda apps, schema: _refresh_automation_signals(), noop_reverse),
    ]
