from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DynamicPipelineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dynamic_pipeline"
    verbose_name = _("Dynamic pipelines")

    def ready(self) -> None:
        from django.db.models.signals import post_migrate

        from dynamic_pipeline.seed import seed_processes
        from dynamic_pipeline.signals import connect_request_signals

        post_migrate.connect(seed_processes, sender=self)
        connect_request_signals()
