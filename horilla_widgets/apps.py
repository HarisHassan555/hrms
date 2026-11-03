from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HorillaWidgetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_widgets"
    verbose_name = _("Widgets")

    def ready(self):
        from horilla_widgets.widgets.file_widgets import patch_clearable_file_input

        patch_clearable_file_input()
