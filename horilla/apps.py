"""Django app config for shared Horilla runtime hooks (table prefix, etc.)."""

from django.apps import AppConfig


class HorillaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla"
    verbose_name = "Core"

    def ready(self) -> None:
        # Safety net after all models load (class_prepared handles the normal path).
        from horilla.db_table_prefix import apply_db_table_prefix_to_plain_models

        apply_db_table_prefix_to_plain_models()
