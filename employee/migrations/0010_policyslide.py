# Generated manually for policy slideshow pages

import django.db.models.deletion
from django.db import migrations, models

import horilla.models


class Migration(migrations.Migration):

    dependencies = [
        ("employee", "0009_alter_actiontype_table_alter_bonuspoint_table_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PolicySlide",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, null=True, verbose_name="Created At"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Is Active"),
                ),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "title",
                    models.CharField(
                        blank=True, max_length=120, verbose_name="Slide title"
                    ),
                ),
                ("body", models.TextField(blank=True, verbose_name="Slide text")),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to=horilla.models.upload_path,
                        verbose_name="Slide image",
                    ),
                ),
                (
                    "policy",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="slides",
                        to="employee.policy",
                    ),
                ),
            ],
            options={
                "verbose_name": "Policy slide",
                "verbose_name_plural": "Policy slides",
                "ordering": ["sort_order", "id"],
            },
        ),
    ]
