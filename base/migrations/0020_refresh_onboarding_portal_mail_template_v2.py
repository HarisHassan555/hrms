"""Upgrade onboarding portal mail template to onboarding_portal_url variable."""

from django.db import migrations


def refresh_template(apps, schema_editor):
    from base.mail_template_catalog import (
        ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE,
        onboarding_complete_profile_portal_template_body,
    )

    HorillaMailTemplate = apps.get_model("base", "HorillaMailTemplate")
    body = onboarding_complete_profile_portal_template_body()
    HorillaMailTemplate.objects.filter(
        title=ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE
    ).update(body=body)


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0019_refresh_onboarding_portal_mail_template_body"),
    ]

    operations = [
        migrations.RunPython(refresh_template, migrations.RunPython.noop),
    ]
