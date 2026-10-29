from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recruitment", "0009_applicant_scoring_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="recruitmentgeneralsetting",
            name="application_acknowledgment_email",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Send a thank-you email automatically when a candidate "
                    "submits the public application form."
                ),
                verbose_name="Application acknowledgment email",
            ),
        ),
    ]
