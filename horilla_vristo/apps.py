"""Django app config for Vristo vendor integration."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HorillaVristoConfig(AppConfig):
    """Registers Vristo vendor paths and optional settings hooks."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_vristo"
    verbose_name = _("Vristo theme vendor")

    def ready(self):
        from horilla_vristo import conf

        conf.log_vendor_status()
