"""
Ensure a mail automation sends when a candidate is marked rejected.

Seeds or updates the rejection notice template and wires an on-create
RejectedCandidate automation (candidate email, no filter rows).
"""

from django.db import migrations

TEMPLATE_TITLE = "Candidate application rejection"
ALT_TEMPLATE_TITLES = ("Application Status - Not Selected",)
AUTOMATION_METHOD_TITLE = "candidate_reject"
MODEL_PATH = "recruitment.models.RejectedCandidate"
MAIL_TO = str(["candidate_id__get_email"])
MAIL_DETAILS = "candidate_id__pk"
MAIL_BODY = """<p>Hi {{ instance.name }},</p>
<p>Thank you for your interest in <strong>{{ instance.recruitment_id.title }}</strong> and for applying for <strong>{{ instance.job_position_id }}</strong>.</p>
<p>After careful consideration, we will not be moving forward with your application at this time.</p>
{% if instance.rejected_candidate.description %}
<p><strong>Note from our team:</strong> {{ instance.rejected_candidate.description }}</p>
{% endif %}
{% if instance.rejected_candidate.reject_reason_id.all %}
<p><strong>Reason:</strong></p>
<ul>
{% for reason in instance.rejected_candidate.reject_reason_id.all %}
<li>{{ reason }}</li>
{% endfor %}
</ul>
{% endif %}
<p>We encourage you to apply for future roles that match your experience.</p>
<p>Best regards,<br>HR Team</p>"""


def _refresh_automation_signals():
    try:
        from horilla_automations.signals import REFRESH_METHODS

        start = REFRESH_METHODS.get("start_connection")
        if start:
            start()
    except Exception:
        pass


def _find_rejection_automations(MailAutomation):
    from django.db.models import Q

    automations = list(
        MailAutomation.objects.filter(
            Q(title__icontains="candidate reject")
            | Q(method_title=AUTOMATION_METHOD_TITLE)
            | Q(title__icontains="application status update")
        )
    )
    if automations:
        return automations
    return list(
        MailAutomation.objects.filter(model=MODEL_PATH, trigger="on_create")
    )


def configure_candidate_reject_automation(apps, schema_editor):
    if not apps.is_installed("recruitment"):
        return

    HorillaMailTemplate = apps.get_model("base", "HorillaMailTemplate")
    MailAutomation = apps.get_model("horilla_automations", "MailAutomation")

    template = HorillaMailTemplate.objects.filter(title=TEMPLATE_TITLE).first()
    if template is None:
        for alt_title in ALT_TEMPLATE_TITLES:
            template = HorillaMailTemplate.objects.filter(title=alt_title).first()
            if template:
                break
    if template is None:
        template = HorillaMailTemplate.objects.create(
            title=TEMPLATE_TITLE,
            body=MAIL_BODY,
        )
    else:
        HorillaMailTemplate.objects.filter(pk=template.pk).update(
            title=TEMPLATE_TITLE,
            body=MAIL_BODY,
        )
        template = HorillaMailTemplate.objects.filter(pk=template.pk).first()

    automations = _find_rejection_automations(MailAutomation)
    subject_title = (
        "Update on your application - "
        "{{ instance.candidate_id.recruitment_id.title }}"
    )

    for auto in automations:
        auto.title = subject_title
        auto.model = MODEL_PATH
        auto.trigger = "on_create"
        auto.mail_to = MAIL_TO
        auto.mail_details = MAIL_DETAILS
        auto.delivery_channel = "email"
        auto.is_active = True
        auto.condition_querystring = ""
        auto.condition = ""
        auto.mail_template_id = template.pk
        if not auto.method_title:
            auto.method_title = AUTOMATION_METHOD_TITLE
        auto.save()

    if not automations:
        MailAutomation.objects.create(
            title=subject_title,
            method_title=AUTOMATION_METHOD_TITLE,
            model=MODEL_PATH,
            trigger="on_create",
            mail_to=MAIL_TO,
            mail_details=MAIL_DETAILS,
            mail_template_id=template.pk,
            delivery_channel="email",
            is_active=True,
            condition_querystring="",
            condition="",
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("horilla_automations", "0005_configure_candidate_apply_automation"),
    ]

    operations = [
        migrations.RunPython(configure_candidate_reject_automation, noop_reverse),
        migrations.RunPython(
            lambda apps, schema: _refresh_automation_signals(), noop_reverse
        ),
    ]
