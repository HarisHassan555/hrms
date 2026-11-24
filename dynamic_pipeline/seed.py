"""Catalog of request types a company can attach a pipeline to."""

import logging

from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)

PROCESSES = (
    (
        "leave_request",
        "Leave request",
        "Time off requested by an employee.",
    ),
    (
        "leave_allocation",
        "Leave allocation request",
        "A request for additional leave balance.",
    ),
    (
        "attendance_request",
        "Attendance request",
        "A request to regularize attendance.",
    ),
    (
        "overtime_request",
        "Overtime request",
        "Overtime that needs approval.",
    ),
    (
        "shift_request",
        "Shift request",
        "A request to change shift.",
    ),
    (
        "work_type_request",
        "Work type request",
        "A request to change work type.",
    ),
    (
        "asset_request",
        "Asset allocation request",
        "A request to allocate a company asset.",
    ),
    (
        "document_request",
        "Document request",
        "An employee document that needs approval.",
    ),
    (
        "reimbursement",
        "Reimbursement request",
        "A payroll reimbursement request.",
    ),
    (
        "claim_request",
        "Helpdesk claim",
        "A helpdesk claim that needs approval.",
    ),
)


def seed_processes(sender=None, **kwargs) -> None:
    """Insert the fixed process catalog. Safe to run more than once."""
    from dynamic_pipeline.models import Process

    try:
        for code, name, description in PROCESSES:
            Process.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": description},
            )
    except (OperationalError, ProgrammingError):
        logger.debug("dynamic pipeline catalog is not ready yet")
