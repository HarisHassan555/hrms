"""Point portal mail links at http://192.168.168.31:8000 instead of localhost."""

from django.db import migrations


def refresh_portal_mail_base_url(apps, schema_editor):
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
        ("base", "0022_onboarding_portal_mail_use_portal_var"),
    ]

    operations = [
        migrations.RunPython(
            refresh_portal_mail_base_url, migrations.RunPython.noop
        ),
    ]
