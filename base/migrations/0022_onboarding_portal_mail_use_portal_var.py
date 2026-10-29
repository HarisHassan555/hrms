"""Point onboarding portal mail template at {{ portal }} (full absolute URL)."""

from django.db import migrations


def refresh_onboarding_portal_template(apps, schema_editor):
    from base.mail_template_catalog import (
        ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE,
        onboarding_complete_profile_portal_template_body,
    )

    HorillaMailTemplate = apps.get_model("base", "HorillaMailTemplate")
    body = onboarding_complete_profile_portal_template_body()
    updated = HorillaMailTemplate.objects.filter(
        title=ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE
    ).update(body=body)
    if not updated:
        HorillaMailTemplate.objects.create(
            title=ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE,
            body=body,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0021_hardcode_localhost_mail_portal_urls"),
    ]

    operations = [
        migrations.RunPython(
            refresh_onboarding_portal_template, migrations.RunPython.noop
        ),
    ]
