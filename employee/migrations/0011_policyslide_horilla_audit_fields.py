# Add HorillaModel audit fields missing from initial PolicySlide migration

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employee", "0010_policyslide"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="policyslide",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
                verbose_name="Created By",
            ),
        ),
        migrations.AddField(
            model_name="policyslide",
            name="modified_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_modified_by",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Modified By",
            ),
        ),
        migrations.AlterModelTable(
            name="policyslide",
            table="dsg_hr_employee_policyslide",
        ),
    ]
