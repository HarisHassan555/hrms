from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HorillaViewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_views"
    verbose_name = _("Views")
