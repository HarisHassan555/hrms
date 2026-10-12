from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HorillaAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_auth"
    verbose_name = _("Horilla Auth")

    def ready(self) -> None:
        from django.contrib.auth import get_user_model

        from horilla.db_table_prefix import apply_db_table_prefix_to_model

        apply_db_table_prefix_to_model(get_user_model())
