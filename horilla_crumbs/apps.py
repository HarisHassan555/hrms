from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HorillaCrumbsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_crumbs"
    verbose_name = _("Breadcrumbs")
