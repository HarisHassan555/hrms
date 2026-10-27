"""Rename recruitment vs onboarding portal mail templates to distinct catalog titles."""

from django.db import migrations


def rename_portal_mail_templates(apps, schema_editor):
    HorillaMailTemplate = apps.get_model("base", "HorillaMailTemplate")

    recruitment_canonical = (
        "[Recruitment] Candidate Portal — Login & Track Application"
    )
    recruitment_legacy = (
        "Candidate Portal Login",
        "Candidate Self Tracking Portal Automation",
    )
    onboarding_canonical = (
        "[Onboarding] Complete Profile Portal — Login & Details"
    )

    if not HorillaMailTemplate.objects.filter(title=recruitment_canonical).exists():
        for legacy in recruitment_legacy:
            row = HorillaMailTemplate.objects.filter(title=legacy).first()
            if row is not None:
                row.title = recruitment_canonical
                row.save(update_fields=["title"])
                for other in recruitment_legacy:
                    if other != legacy:
                        HorillaMailTemplate.objects.filter(title=other).delete()
                break

    if not HorillaMailTemplate.objects.filter(title=onboarding_canonical).exists():
        HorillaMailTemplate.objects.create(
            title=onboarding_canonical,
            body=(
                "<p>Hi {{instance.get_full_name}},</p>"
                "<p>Use the onboarding portal link in your email to complete your "
                "employee profile and onboarding tasks.</p>"
            ),
        )


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0017_alter_announcement_table_and_more"),
    ]

    operations = [
        migrations.RunPython(rename_portal_mail_templates, migrations.RunPython.noop),
    ]
