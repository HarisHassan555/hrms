"""Start a pipeline run when a configured request is created."""

import logging

from django.db.utils import DatabaseError

logger = logging.getLogger(__name__)


def connect_request_signals() -> None:
    from django.db.models.signals import post_save

    from asset.models import AssetRequest
    from leave.models import LeaveRequest

    post_save.connect(
        _on_leave_saved,
        sender=LeaveRequest,
        dispatch_uid="dynamic_pipeline_leave_request",
    )
    post_save.connect(
        _on_asset_saved,
        sender=AssetRequest,
        dispatch_uid="dynamic_pipeline_asset_request",
    )


def _on_leave_saved(sender, instance, created, raw=False, **kwargs):
    if raw or not created or instance.status != "requested":
        return
    _start("leave_request", instance, instance.employee_id)


def _on_asset_saved(sender, instance, created, raw=False, **kwargs):
    if raw or not created or instance.asset_request_status != "Requested":
        return
    _start("asset_request", instance, instance.requested_employee_id)


def _start(process_code, target, requester) -> None:
    from dynamic_pipeline.services import PipelineError, start_run_if_configured

    try:
        start_run_if_configured(process_code, target, requester)
    except (DatabaseError, PipelineError):
        logger.exception(
            "Skipped pipeline start for %s %s",
            process_code,
            getattr(target, "pk", None),
        )
