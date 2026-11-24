"""Configure pipelines and act on the current step."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from base.models import Company
from dynamic_pipeline.finalizers import apply_approval, apply_rejection
from dynamic_pipeline.models import (
    MAX_STEPS,
    Pipeline,
    PipelineRun,
    PipelineStep,
    Process,
    StepAssignee,
)
from dynamic_pipeline.services import (
    PipelineError,
    approval_would_finish,
    decide,
    replace_pipeline,
    runs_for_actor,
    user_can_act,
)
from employee.models import Employee
from horilla.horilla_middlewares import get_selected_company


def _can_configure(user) -> bool:
    return user.is_superuser or user.has_perm("dynamic_pipeline.change_pipeline")


def _selected_company():
    raw = get_selected_company()
    if raw in (None, "", "all"):
        return None
    return Company.objects.filter(pk=raw).first()


def _company_from_request(request):
    selected = _selected_company()
    if selected is not None:
        return selected
    posted = request.POST.get("company") or request.GET.get("company")
    if posted:
        return Company.objects.filter(pk=posted).first()
    return None


def _employee_label(employee: Employee) -> str:
    badge = employee.badge_id or ""
    name = f"{employee.employee_first_name} {employee.employee_last_name}".strip()
    return f"{name} ({badge})" if badge else name


@login_required
def pipeline_list(request):
    if not _can_configure(request.user):
        messages.error(request, _("You do not have permission to configure pipelines."))
        return redirect("pipeline-approvals")
    company = _company_from_request(request)
    processes = list(Process.objects.filter(is_active=True))
    pipelines = Pipeline.objects.filter(is_active=True).select_related(
        "process", "company"
    )
    if company is not None:
        pipelines = pipelines.filter(company=company)
    by_process = {}
    for pipeline in pipelines.prefetch_related("steps"):
        by_process.setdefault(pipeline.process_id, []).append(pipeline)
    rows = []
    for process in processes:
        attached = by_process.get(process.id, [])
        rows.append(
            {
                "process": process,
                "pipelines": attached,
                "step_count": attached[0].steps.count() if len(attached) == 1 else None,
            }
        )
    return render(
        request,
        "dynamic_pipeline/list.html",
        {
            "rows": rows,
            "company": company,
            "companies": Company.objects.all().order_by("company"),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def pipeline_edit(request, code):
    if not _can_configure(request.user):
        messages.error(request, _("You do not have permission to configure pipelines."))
        return redirect("pipeline-approvals")
    process = get_object_or_404(Process, code=code, is_active=True)
    company = _company_from_request(request)
    if request.method == "POST":
        if company is None:
            messages.error(request, _("Choose a company before saving a pipeline."))
        else:
            try:
                replace_pipeline(
                    company,
                    process,
                    _steps_from_post(request),
                    name=request.POST.get("name", ""),
                )
            except (PipelineError, ValidationError) as exc:
                messages.error(request, exc.messages[0] if getattr(exc, "messages", None) else str(exc))
            else:
                messages.success(request, _("Pipeline saved."))
                url = reverse("pipeline-edit", kwargs={"code": process.code})
                return redirect(f"{url}?company={company.pk}")
    pipeline = None
    if company is not None:
        pipeline = (
            Pipeline.objects.filter(process=process, company=company, is_active=True)
            .prefetch_related("steps__assignees__employee", "steps__assignees__role")
            .first()
        )
    return render(
        request,
        "dynamic_pipeline/edit.html",
        {
            "process": process,
            "company": company,
            "companies": Company.objects.all().order_by("company"),
            "pipeline": pipeline,
            "steps": list(pipeline.steps.all()) if pipeline else [],
            "employees": list(
                Employee.objects.all().order_by(
                    "employee_first_name", "employee_last_name"
                )
            ),
            "roles": list(Group.objects.all().order_by("name")),
            "max_steps": MAX_STEPS,
            "employee_label": _employee_label,
        },
    )


def _steps_from_post(request) -> list[dict]:
    names = request.POST.getlist("step_name")
    modes = request.POST.getlist("step_mode")
    kinds = request.POST.getlist("assignee_kind")
    employees = request.POST.getlist("assignee_employee")
    roles = request.POST.getlist("assignee_role")
    indexes = request.POST.getlist("assignee_step")
    if not (len(kinds) == len(employees) == len(roles) == len(indexes)):
        raise PipelineError(_("Approver rows were incomplete. Save the pipeline again."))
    grouped: dict[int, list] = {}
    for kind, employee_id, role_id, index in zip(kinds, employees, roles, indexes):
        if not kind:
            continue
        try:
            step_index = int(index)
        except ValueError as exc:
            raise PipelineError(_("Approver rows were incomplete.")) from exc
        payload = {"kind": kind, "employee_id": None, "role_id": None}
        if kind == StepAssignee.EMPLOYEE:
            if not employee_id:
                raise PipelineError(_("Choose an employee for each employee approver."))
            payload["employee_id"] = int(employee_id)
        elif kind == StepAssignee.ROLE:
            if not role_id:
                raise PipelineError(_("Choose a role for each role approver."))
            payload["role_id"] = int(role_id)
        elif kind != StepAssignee.REPORTING_MANAGER:
            raise PipelineError(_("Unknown approver type."))
        grouped.setdefault(step_index, []).append(payload)
    steps = []
    for position, name in enumerate(names):
        mode = modes[position] if position < len(modes) else PipelineStep.OR
        steps.append(
            {
                "name": name.strip(),
                "mode": mode,
                "assignees": grouped.get(position, []),
            }
        )
    return [step for step in steps if step["name"] or step["assignees"]]


@login_required
@require_http_methods(["POST"])
def pipeline_clear(request, code):
    if not _can_configure(request.user):
        messages.error(request, _("You do not have permission to configure pipelines."))
        return redirect("pipeline-approvals")
    process = get_object_or_404(Process, code=code)
    company = _company_from_request(request)
    if company is None:
        messages.error(request, _("Choose a company first."))
        return redirect("pipeline-list")
    Pipeline.objects.filter(process=process, company=company, is_active=True).update(
        is_active=False
    )
    messages.success(
        request,
        _("Pipeline removed. New requests use the original approval flow."),
    )
    return redirect("pipeline-list")


@login_required
def approval_inbox(request):
    runs = runs_for_actor(request.user)
    cards = []
    for run in runs:
        cards.append(
            {
                "run": run,
                "slots": [
                    slot
                    for slot in run.slots.all()
                    if slot.sequence == run.current_sequence
                ],
                "would_finish": approval_would_finish(run, request.user),
                "target_url": _target_url(run),
            }
        )
    return render(
        request,
        "dynamic_pipeline/inbox.html",
        {"cards": cards},
    )


def _target_url(run: PipelineRun) -> str:
    if run.process.code == "leave_request":
        return f"/leave/request-view?id={run.object_id}"
    if run.process.code == "asset_request":
        return reverse("asset-request-allocation-view")
    return ""


@login_required
@require_http_methods(["POST"])
def approval_decide(request, run_id):
    run = get_object_or_404(
        PipelineRun.objects.select_related("process", "requester"),
        pk=run_id,
        status=PipelineRun.PENDING,
    )
    decision = request.POST.get("decision")
    comment = request.POST.get("comment", "")
    if (
        decision == "approved"
        and run.process.code == "asset_request"
        and approval_would_finish(run, request.user)
    ):
        return redirect("asset-request-approve", req_id=run.object_id)
    if not user_can_act(run, request.user):
        messages.error(request, _("You cannot act on the current step."))
        return redirect("pipeline-approvals")
    try:
        updated = decide(run, request.user, decision, comment)
        if updated.status == PipelineRun.APPROVED:
            apply_approval(updated)
            messages.success(request, _("Request approved."))
        elif updated.status == PipelineRun.REJECTED:
            apply_rejection(updated, comment)
            messages.success(request, _("Request rejected."))
        else:
            messages.success(
                request,
                _(
                    "Approval recorded. The request stays open until every required step is complete."
                ),
            )
    except PipelineError as exc:
        messages.error(request, str(exc))
    return redirect("pipeline-approvals")
