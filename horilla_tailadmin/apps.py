from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HorillaTailadminConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_tailadmin"
    verbose_name = _("TailAdmin vendor")

    def ready(self):
        from horilla_tailadmin import conf

        conf.log_vendor_status()
