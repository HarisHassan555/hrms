# Policy body: single page vs slideshow mode

from django.db import migrations, models


def set_slideshow_format(apps, schema_editor):
    Policy = apps.get_model("employee", "Policy")
    PolicySlide = apps.get_model("employee", "PolicySlide")
    for policy_id in (
        PolicySlide.objects.values_list("policy_id", flat=True).distinct()
    ):
        Policy.objects.filter(pk=policy_id).update(body_format="slideshow")


class Migration(migrations.Migration):

    dependencies = [
        ("employee", "0011_policyslide_horilla_audit_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="policy",
            name="body_format",
            field=models.CharField(
                choices=[
                    ("single", "Single page"),
                    ("slideshow", "Multiple pages (slideshow)"),
                ],
                default="single",
                max_length=12,
                verbose_name="Body format",
            ),
        ),
        migrations.AlterField(
            model_name="policy",
            name="body",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(set_slideshow_format, migrations.RunPython.noop),
    ]
