"""Apply the original request's outcome once a pipeline finishes.

Leave approval still updates the leave balance. Asset approval does not pick
a physical asset here; the last approver allocates it on the existing form.
"""

from __future__ import annotations

from dynamic_pipeline.services import PipelineError


def apply_approval(run) -> None:
    target = _target(run)
    if target is None:
        return
    code = run.process.code
    if code == "leave_request":
        _approve_leave(target)
    elif code == "asset_request":
        _set_asset_status(target, "Approved")


def apply_rejection(run, reason: str = "") -> None:
    target = _target(run)
    if target is None:
        return
    code = run.process.code
    if code == "leave_request":
        _reject_leave(target, reason)
    elif code == "asset_request":
        _set_asset_status(target, "Rejected")


def _target(run):
    model = run.content_type.model_class()
    if model is None:
        return None
    return model.objects.filter(pk=run.object_id).first()


def _approve_leave(leave_request) -> None:
    if leave_request.status == "approved":
        return
    from leave.models import AvailableLeave

    try:
        available = AvailableLeave.objects.get(
            leave_type_id=leave_request.leave_type_id,
            employee_id=leave_request.employee_id,
        )
    except AvailableLeave.DoesNotExist as exc:
        raise PipelineError(
            "No available leave record found for this employee and leave type."
        ) from exc
    total = available.available_days + available.carryforward_days
    if total < leave_request.requested_days:
        raise PipelineError("Not enough leave balance to approve this request.")
    if leave_request.requested_days > available.carryforward_days:
        taken = leave_request.requested_days - available.carryforward_days
        leave_request.approved_carryforward_days = available.carryforward_days
        available.carryforward_days = 0
        available.available_days = available.available_days - taken
        leave_request.approved_available_days = taken
    else:
        available.carryforward_days = (
            available.carryforward_days - leave_request.requested_days
        )
        leave_request.approved_carryforward_days = leave_request.requested_days
    leave_request.status = "approved"
    leave_request.save()
    available.save()


def _reject_leave(leave_request, reason: str) -> None:
    if leave_request.status == "rejected":
        return
    if reason:
        leave_request.reject_reason = reason[:255]
    leave_request.status = "rejected"
    leave_request.save()


def _set_asset_status(asset_request, status: str) -> None:
    if asset_request.asset_request_status == status:
        return
    asset_request.asset_request_status = status
    asset_request.save(update_fields=["asset_request_status"])
