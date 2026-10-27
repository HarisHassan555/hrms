"""Use http://localhost:8000 as the mail template base URL for portal links."""

from django.db import migrations


def apply_hardcoded_portal_templates(apps, schema_editor):
    from base.mail_template_catalog import (
        ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE,
        RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE,
        onboarding_complete_profile_portal_template_body,
        recruitment_candidate_portal_template_body,
    )

    HorillaMailTemplate = apps.get_model("base", "HorillaMailTemplate")
    HorillaMailTemplate.objects.filter(
        title=RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE
    ).update(body=recruitment_candidate_portal_template_body())
    HorillaMailTemplate.objects.filter(
        title=ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE
    ).update(body=onboarding_complete_profile_portal_template_body())


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0020_refresh_onboarding_portal_mail_template_v2"),
    ]

    operations = [
        migrations.RunPython(apply_hardcoded_portal_templates, migrations.RunPython.noop),
    ]
