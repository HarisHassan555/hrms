"""Replace the short onboarding portal mail template with the full detailed body."""

from django.db import migrations

ONBOARDING_PORTAL_TEMPLATE_TITLE = (
    "[Onboarding] Complete Profile Portal — Login & Details"
)

# Keep in sync with base.mail_template_catalog.onboarding_complete_profile_portal_template_body
ONBOARDING_PORTAL_TEMPLATE_BODY = (
    '<div style="font-family: \'Segoe UI\', Arial, sans-serif; background-color: #f4f6f9; padding: 24px;">'
    '<div style="max-width: 640px; margin: auto; background: #ffffff; border-radius: 12px; padding: 28px; '
    'box-shadow: 0 4px 14px rgba(0,0,0,0.08); border: 1px solid #eceff3;">'
    '<h2 style="margin: 0 0 18px 0; color: #1f2937; font-size: 22px;">'
    "Onboarding Portal — Complete Profile Details"
    "</h2>"
    '<p style="font-size: 14px; color: #374151; line-height: 1.7; margin: 0 0 14px 0;">'
    "Hi {{instance.get_full_name}},</p>"
    '<p style="font-size: 14px; color: #374151; line-height: 1.7; margin: 0 0 16px 0;">'
    "Congratulations on your selection. Use the onboarding portal below to complete your "
    "employee profile, upload required documents, and finish onboarding tasks before you join "
    "<strong>{{instance.get_company}}</strong> as "
    "<strong>{{instance.get_job_position}}</strong>.</p>"
    '<div style="margin: 18px 0; padding: 16px; background: #f9fafb; border-left: 4px solid hsl(8, 77%, 56%); border-radius: 8px;">'
    '<p style="margin: 0 0 8px 0; font-size: 14px; color: #111827;">'
    "<strong>Portal link:</strong> "
    "{% if portal %}"
    '<a href="{{ portal }}" target="_blank" style="color: hsl(8, 77%, 56%); text-decoration: none;">{{ portal }}</a>'
    "{% else %}"
    '<a href="{{ request.scheme }}://{{ request.get_host }}{{ instance.get_onboarding_portal_path }}" '
    'target="_blank" style="color: hsl(8, 77%, 56%); text-decoration: none;">'
    "{{ request.scheme }}://{{ request.get_host }}{{ instance.get_onboarding_portal_path }}"
    "</a>{% endif %}</p>"
    '<p style="margin: 0 0 8px 0; font-size: 14px; color: #111827;">'
    "<strong>Email (for your account):</strong> {{instance.email}}</p>"
    '<p style="margin: 0 0 8px 0; font-size: 14px; color: #111827;">'
    "<strong>Mobile number:</strong> {{instance.mobile}}</p>"
    '<p style="margin: 0; font-size: 14px; color: #111827;">'
    "<strong>How to access:</strong> Open the personal link above. You will create your "
    "password on first visit — this is not the recruitment candidate portal.</p>"
    "</div>"
    '<p style="font-size: 13px; color: #6b7280; margin: 0 0 18px 0;">'
    "For security, please keep this onboarding link private and do not forward it.</p>"
    '<hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">'
    '<p style="font-size: 13px; color: #6b7280; margin: 0;">Regards,</p>'
    '<p style="font-size: 13px; color: #111827; margin: 6px 0 0 0;">'
    "<strong>{{self.get_full_name}} | {{self.get_department}} | {{self.get_company}}</strong></p>"
    "</div></div>"
)


def refresh_onboarding_portal_mail_template_body(apps, schema_editor):
    HorillaMailTemplate = apps.get_model("base", "HorillaMailTemplate")
    HorillaMailTemplate.objects.filter(title=ONBOARDING_PORTAL_TEMPLATE_TITLE).update(
        body=ONBOARDING_PORTAL_TEMPLATE_BODY
    )
    if not HorillaMailTemplate.objects.filter(
        title=ONBOARDING_PORTAL_TEMPLATE_TITLE
    ).exists():
        HorillaMailTemplate.objects.create(
            title=ONBOARDING_PORTAL_TEMPLATE_TITLE,
            body=ONBOARDING_PORTAL_TEMPLATE_BODY,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0018_rename_portal_mail_template_titles"),
    ]

    operations = [
        migrations.RunPython(
            refresh_onboarding_portal_mail_template_body,
            migrations.RunPython.noop,
        ),
    ]
