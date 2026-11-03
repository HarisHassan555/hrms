from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BackupConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_backup"
    verbose_name = _("Backup")

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns

        urlpatterns.append(
            path("backup/", include("horilla_backup.urls")),
        )
        super().ready()
