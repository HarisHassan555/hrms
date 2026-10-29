"""Ensure portal mail templates / request host proxy use the LAN base URL."""

from django.db import migrations


def refresh_portal_mail_templates(apps, schema_editor):
    from base.mail_template_catalog import (
        ensure_onboarding_complete_profile_portal_mail_template,
        ensure_recruitment_candidate_portal_mail_template,
    )

    ensure_recruitment_candidate_portal_mail_template()
    ensure_onboarding_complete_profile_portal_mail_template()


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0023_mail_portal_base_url_lan"),
    ]

    operations = [
        migrations.RunPython(
            refresh_portal_mail_templates, migrations.RunPython.noop
        ),
    ]
