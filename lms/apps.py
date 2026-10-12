from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class LmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "lms"
    verbose_name = _("Learning")

    def ready(self):
        # URLs are mounted in horilla.urls (same pattern as employee/).
        settings.APPS.append("lms")
        settings.APP_URLS.append("lms.urls")
        super().ready()
