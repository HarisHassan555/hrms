"""Resolve approvers and move a request through its pipeline.

Slots are copied when a run starts, so a later edit to the pipeline does not
change a request that is already in flight. A reporting-manager slot stores
the requester's manager at that moment: A's request goes to B, and B's
request goes to C.
"""

from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from dynamic_pipeline.models import (
    MAX_STEPS,
    ApprovalSlot,
    Pipeline,
    PipelineRun,
    PipelineStep,
    Process,
    StepAssignee,
)
from employee.models import Employee


class PipelineError(Exception):
    """The decision cannot be applied."""


def requester_company(employee: Employee):
    work = getattr(employee, "employee_work_info", None)
    return getattr(work, "company_id", None)


def requester_manager(employee: Employee):
    work = getattr(employee, "employee_work_info", None)
    return getattr(work, "reporting_manager_id", None)


def active_pipeline(process_code: str, company) -> Pipeline | None:
    if company is None:
        return None
    return (
        Pipeline.objects.filter(
            process__code=process_code,
            company=company,
            is_active=True,
        )
        .select_related("process", "company")
        .prefetch_related("steps__assignees")
        .first()
    )


def pending_run(process_code: str, target) -> PipelineRun | None:
    content_type = ContentType.objects.get_for_model(target.__class__)
    return (
        PipelineRun.objects.filter(
            process__code=process_code,
            content_type=content_type,
            object_id=target.pk,
            status=PipelineRun.PENDING,
        )
        .select_related("process", "requester", "company")
        .prefetch_related("slots")
        .first()
    )


def start_run_if_configured(process_code: str, target, requester: Employee):
    """Open a run when this company has an active pipeline. Otherwise do nothing."""
    if requester is None or getattr(target, "pk", None) is None:
        return None
    company = requester_company(requester)
    pipeline = active_pipeline(process_code, company)
    if pipeline is None:
        return None
    content_type = ContentType.objects.get_for_model(target.__class__)
    existing = PipelineRun.objects.filter(
        content_type=content_type,
        object_id=target.pk,
        status=PipelineRun.PENDING,
    ).first()
    if existing:
        return existing
    return _open_run(pipeline, target, requester, content_type)


def _open_run(pipeline, target, requester, content_type) -> PipelineRun:
    steps = list(pipeline.steps.all().order_by("sequence"))
    if not steps:
        raise PipelineError(_("A pipeline needs at least one step."))
    if len(steps) > MAX_STEPS:
        raise PipelineError(
            _("A pipeline can have at most %(max)s steps.") % {"max": MAX_STEPS}
        )
    with transaction.atomic():
        run = PipelineRun.objects.create(
            pipeline=pipeline,
            process=pipeline.process,
            company=pipeline.company,
            requester=requester,
            content_type=content_type,
            object_id=target.pk,
            status=PipelineRun.PENDING,
            current_sequence=steps[0].sequence,
        )
        manager = requester_manager(requester)
        for step in steps:
            assignees = list(step.assignees.all())
            if not assignees:
                raise PipelineError(_("Each step needs at least one approver."))
            for assignee in assignees:
                employee = None
                role = None
                if assignee.kind == StepAssignee.EMPLOYEE:
                    employee = assignee.employee
                elif assignee.kind == StepAssignee.ROLE:
                    role = assignee.role
                elif assignee.kind == StepAssignee.REPORTING_MANAGER:
                    employee = manager
                ApprovalSlot.objects.create(
                    run=run,
                    sequence=step.sequence,
                    mode=step.mode,
                    kind=assignee.kind,
                    employee=employee,
                    role=role,
                )
    return run


def _actor(user) -> Employee | None:
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.employee_get
    except Employee.DoesNotExist:
        return None


def slot_is_actionable(slot: ApprovalSlot, user, requester: Employee) -> bool:
    """True when this user may approve or reject this pending slot."""
    actor = _actor(user)
    if actor is None or requester is None or actor.pk == requester.pk:
        return False
    if slot.status != ApprovalSlot.PENDING:
        return False
    if slot.kind in (StepAssignee.EMPLOYEE, StepAssignee.REPORTING_MANAGER):
        return slot.employee_id == actor.pk
    if slot.kind == StepAssignee.ROLE and slot.role_id:
        from base.auth_backends import get_user_groups_for_company

        return get_user_groups_for_company(user, slot.run.company_id).filter(
            pk=slot.role_id
        ).exists()
    return False


def current_slots(run: PipelineRun):
    return [
        slot
        for slot in run.slots.all()
        if slot.sequence == run.current_sequence and slot.status == ApprovalSlot.PENDING
    ]


def approval_would_finish(run: PipelineRun, user) -> bool:
    """True when this user's approval clears the current step and no step remains."""
    pending = current_slots(run)
    actionable = [
        slot for slot in pending if slot_is_actionable(slot, user, run.requester)
    ]
    if not actionable or not pending:
        return False
    mode = pending[0].mode
    if mode == PipelineStep.OR:
        step_clears = True
    else:
        remaining = [slot for slot in pending if slot not in actionable]
        step_clears = not remaining
    if not step_clears:
        return False
    return not any(slot.sequence > run.current_sequence for slot in run.slots.all())


def user_can_act(run: PipelineRun, user) -> bool:
    return any(
        slot_is_actionable(slot, user, run.requester) for slot in current_slots(run)
    )


def decide(run: PipelineRun, user, decision: str, comment: str = "") -> PipelineRun:
    """Record an approval or rejection on the current step."""
    if decision not in ("approved", "rejected"):
        raise PipelineError(_("Choose approve or reject."))
    if run.status != PipelineRun.PENDING:
        raise PipelineError(_("This request is no longer waiting for approval."))
    actor = _actor(user)
    if actor is None:
        raise PipelineError(_("Only an employee can approve this request."))
    pending = current_slots(run)
    actionable = [
        slot for slot in pending if slot_is_actionable(slot, user, run.requester)
    ]
    if not actionable:
        raise PipelineError(_("You cannot act on the current step."))

    now = timezone.now()
    note = (comment or "")[:255]
    with transaction.atomic():
        locked = PipelineRun.objects.select_for_update().get(pk=run.pk)
        if locked.status != PipelineRun.PENDING:
            raise PipelineError(_("This request is no longer waiting for approval."))
        if decision == "rejected":
            target = actionable[0]
            target.status = ApprovalSlot.REJECTED
            target.acted_by = actor
            target.comment = note
            target.acted_at = now
            target.save(
                update_fields=["status", "acted_by", "comment", "acted_at", "modified_by"]
            )
            locked.slots.filter(status=ApprovalSlot.PENDING).update(
                status=ApprovalSlot.SKIPPED
            )
            locked.status = PipelineRun.REJECTED
            locked.save(update_fields=["status", "modified_by"])
            return locked

        for slot in actionable:
            slot.status = ApprovalSlot.APPROVED
            slot.acted_by = actor
            slot.comment = note
            slot.acted_at = now
            slot.save(
                update_fields=["status", "acted_by", "comment", "acted_at", "modified_by"]
            )
        still_pending = list(
            locked.slots.filter(
                sequence=locked.current_sequence, status=ApprovalSlot.PENDING
            )
        )
        mode = pending[0].mode
        step_clears = mode == PipelineStep.OR or not still_pending
        if mode == PipelineStep.OR and step_clears:
            locked.slots.filter(
                sequence=locked.current_sequence, status=ApprovalSlot.PENDING
            ).update(status=ApprovalSlot.SKIPPED)
        if not step_clears:
            locked.refresh_from_db()
            return locked
        next_sequence = (
            locked.slots.filter(sequence__gt=locked.current_sequence)
            .order_by("sequence")
            .values_list("sequence", flat=True)
            .first()
        )
        if next_sequence is None:
            locked.status = PipelineRun.APPROVED
            locked.save(update_fields=["status", "modified_by"])
        else:
            locked.current_sequence = next_sequence
            locked.save(update_fields=["current_sequence", "modified_by"])
        locked.refresh_from_db()
        return locked


def replace_pipeline(company, process: Process, steps: list[dict], name: str = ""):
    """Replace the company's pipeline for this process. In-flight runs stay as they are."""
    if not steps:
        raise PipelineError(_("Add at least one step."))
    if len(steps) > MAX_STEPS:
        raise PipelineError(
            _("A pipeline can have at most %(max)s steps.") % {"max": MAX_STEPS}
        )
    with transaction.atomic():
        pipeline = (
            Pipeline.objects.filter(process=process, company=company, is_active=True)
            .order_by("-id")
            .first()
        )
        if pipeline is None:
            pipeline = Pipeline.objects.create(
                process=process,
                company=company,
                name=name or process.name,
                is_active=True,
            )
        else:
            pipeline.name = name or process.name
            pipeline.save(update_fields=["name", "modified_by"])
            pipeline.steps.all().delete()
        for index, step_data in enumerate(steps, start=1):
            assignees = step_data.get("assignees") or []
            if not assignees:
                raise PipelineError(
                    _("Step %(number)s needs at least one approver.")
                    % {"number": index}
                )
            mode = step_data.get("mode") or PipelineStep.OR
            if mode not in (PipelineStep.AND, PipelineStep.OR):
                raise PipelineError(_("Choose AND or OR for each step."))
            step = PipelineStep.objects.create(
                pipeline=pipeline,
                sequence=index,
                name=(step_data.get("name") or "")[:120],
                mode=mode,
            )
            seen = set()
            for assignee in assignees:
                kind = assignee.get("kind")
                key = (kind, assignee.get("employee_id"), assignee.get("role_id"))
                if key in seen:
                    continue
                seen.add(key)
                row = StepAssignee(
                    step=step,
                    kind=kind,
                    employee_id=assignee.get("employee_id"),
                    role_id=assignee.get("role_id"),
                )
                row.full_clean()
                row.save()
        return pipeline


def runs_for_actor(user):
    """Pending runs whose current step this user can act on."""
    actor = _actor(user)
    if actor is None:
        return []
    runs = (
        PipelineRun.objects.filter(status=PipelineRun.PENDING)
        .select_related("process", "requester", "company")
        .prefetch_related("slots__employee", "slots__role")
    )
    return [run for run in runs if user_can_act(run, user)]
