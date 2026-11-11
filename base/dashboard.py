"""
Modern dashboard views — KPI summary + ApexCharts.

Accessible at /dashboard/modern/ alongside the existing dashboard.
"""

import calendar
import json
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods


def _safe_url(url_name):
    """Reverse a URL name; return '#' if the URL is not registered."""
    try:
        return reverse(url_name)
    except Exception:
        return "#"


# ---------------------------------------------------------------------------
# Setup checklist helpers
# ---------------------------------------------------------------------------


def _is_setup_admin(request):
    """
    True for superusers, staff, and any user who can manage HR setup entities.
    Regular employees (no management perms) are excluded — they can't complete
    setup steps and should not see setup prompts.
    """
    user = request.user
    if user.is_superuser or user.is_staff:
        return True
    return user.has_perm("base.add_department") or user.has_perm("base.add_company")


def _resolve_checklist_company(request):
    """
    Return the integer PK of the company currently active for this request.

    Priority:
      1. The company stored in the ContextVar by the middleware
      2. The first company in the DB (fresh install with no session yet)
      3. None  (no company exists — the "Company" step is the first to do)
    """
    from horilla.horilla_middlewares import get_selected_company

    company_id = get_selected_company()
    if company_id and company_id != "all":
        try:
            return int(company_id)
        except (TypeError, ValueError):
            pass

    # "all" or None → fall back to first company in the DB
    from base.models import Company

    first = Company.objects.first()
    return first.pk if first else None


def _exists_for_company(ModelClass, company_id):
    """
    Return True if at least one record of ModelClass is visible for the given
    company.  Mirrors HorillaCompanyManager: a record is visible when it is
    explicitly assigned to this company OR has no company assignment at all
    (meaning it is shared across all companies — common for lookup tables like
    WorkType, EmployeeType, EmployeeShift whose M2M company_id may be empty).
    """
    try:
        filter_path = ModelClass.objects.get_company_filter_path()
        if not filter_path:
            return False
        null_path = f"{filter_path}__isnull"
        return (
            ModelClass.objects.entire()
            .filter(Q(**{filter_path: company_id}) | Q(**{null_path: True}))
            .exists()
        )
    except Exception:
        return False


def _get_setup_checklist_context(request):
    """
    Builds the context for the onboarding setup checklist banner.

    Returns ``{"show_setup_checklist": False}`` when:
      • the user is not an admin/manager (regular employees skip it)
      • the user has already dismissed the banner for the active company
      • all 8 steps are complete for the active company

    In DEBUG mode only, ``?preview_checklist=1`` forces the banner visible
    with every step shown as incomplete — useful for testing on populated DBs
    without deleting any data.
    """
    from django.conf import settings

    from base.models import (
        Company,
        Department,
        DynamicEmailConfiguration,
        EmployeeShift,
        EmployeeShiftSchedule,
        JobPosition,
        SetupChecklistDismissal,
        WorkType,
    )

    # 1. Permission gate — only show to admins / managers
    if not _is_setup_admin(request):
        return {"show_setup_checklist": False}

    preview_mode = settings.DEBUG and request.GET.get("preview_checklist") == "1"

    # 2. Resolve the company we're scoping the checklist to
    company_pk = _resolve_checklist_company(request)

    # 3. Check per-user, per-company dismissal
    if not preview_mode:
        dismissed = SetupChecklistDismissal.objects.filter(
            user=request.user, company_id=company_pk
        ).exists()
        if dismissed:
            return {"show_setup_checklist": False}

    # 4. Build steps — each checks live DB scoped to the active company
    def _has_company():
        # Company itself is the root tenant object; any company existing is enough.
        try:
            return Company.objects.exists()
        except Exception:
            return False

    def _has_employees():
        try:
            from employee.models import Employee

            return _exists_for_company(Employee, company_pk)
        except Exception:
            return False

    def _has_mail_server():
        try:
            return DynamicEmailConfiguration.objects.filter(
                is_primary=True, host__isnull=False
            ).exists()
        except Exception:
            return False

    steps = [
        {
            "key": "company",
            "title": _("Company"),
            "description": _("Add your company profile — name, logo and timezone."),
            "url": _safe_url("company-view"),
            "done": _has_company(),
        },
        {
            "key": "department",
            "title": _("Departments"),
            "description": _("Create the departments your employees will belong to."),
            "url": _safe_url("department-view"),
            "done": (
                _exists_for_company(Department, company_pk) if company_pk else False
            ),
        },
        {
            "key": "job_position",
            "title": _("Job Positions"),
            "description": _("Define named roles within each department."),
            "url": _safe_url("job-position-view"),
            "done": (
                _exists_for_company(JobPosition, company_pk) if company_pk else False
            ),
        },
        {
            "key": "shift",
            "title": _("Shift"),
            "description": _("Define working schedules — Morning, Evening, Night."),
            "url": _safe_url("employee-shift-view"),
            "done": (
                _exists_for_company(EmployeeShift, company_pk) if company_pk else False
            ),
        },
        {
            "key": "shift_schedule",
            "title": _("Shift Schedule"),
            "description": _("Set day-wise timings for each shift."),
            "url": _safe_url("employee-shift-schedule-view"),
            "done": (
                _exists_for_company(EmployeeShiftSchedule, company_pk)
                if company_pk
                else False
            ),
        },
        {
            "key": "work_type",
            "title": _("Work Type"),
            "description": _("Set engagement types — Full Time, Part Time, Contract."),
            "url": _safe_url("work-type-view"),
            "done": _exists_for_company(WorkType, company_pk) if company_pk else False,
        },
        {
            "key": "mail_server",
            "title": _("Mail Server"),
            "description": _(
                "Configure an outgoing mail server so DSG can send emails."
            ),
            "url": _safe_url("mail-server-conf"),
            "done": _has_mail_server(),
        },
        {
            "key": "first_employee",
            "title": _("First Employee"),
            "description": _("Add your first employee to bring everything together."),
            "url": _safe_url("employee-view-new"),
            "done": _has_employees() if company_pk else False,
        },
    ]

    # 5. Preview mode overrides all done flags to False
    if preview_mode:
        for s in steps:
            s["done"] = False

    completed = sum(1 for s in steps if s["done"])
    total = len(steps)

    # Auto-hide once all steps are complete (no dismiss record needed)
    if not preview_mode and completed == total:
        return {"show_setup_checklist": False}

    # 6. Precompute connector-line state for the template.
    for i, step in enumerate(steps):
        step["left_line_active"] = (i > 0) and steps[i - 1]["done"]
        step["right_line_active"] = step["done"] and (i < total - 1)

    next_step = next((s for s in steps if not s["done"]), None)
    progress_pct = int(completed / total * 100)

    return {
        "show_setup_checklist": True,
        "setup_steps": steps,
        "setup_completed": completed,
        "setup_total": total,
        "setup_next_step": next_step,
        "setup_progress_pct": progress_pct,
        "setup_dismiss_url": _safe_url("dashboard-dismiss-setup-checklist"),
        "setup_company_pk": company_pk,
    }


def _parse_period(request):
    """Parse from_date and to_date from GET params. Defaults to current month."""
    today = date.today()
    from_str = request.GET.get("from_date")
    to_str = request.GET.get("to_date")
    try:
        from_date = date.fromisoformat(from_str) if from_str else today.replace(day=1)
    except (ValueError, TypeError):
        from_date = today.replace(day=1)
    try:
        to_date = date.fromisoformat(to_str) if to_str else today
    except (ValueError, TypeError):
        to_date = today
    return from_date, to_date


def _current_month_bounds():
    """Return (first_day, last_day) of the current calendar month.

    Always derived from ``date.today()`` -- never cached -- so every chart
    that calls this rolls over to the new month on its own, with no stored
    "current period" to go stale.
    """
    today = date.today()
    _, last_day_num = calendar.monthrange(today.year, today.month)
    return today.replace(day=1), today.replace(day=last_day_num)


def _is_manager(user):
    """Return True if user is a reporting manager for at least one active employee."""
    try:
        from employee.models import EmployeeWorkInformation

        emp = getattr(user, "employee_get", None)
        if not emp:
            return False
        return EmployeeWorkInformation.objects.filter(reporting_manager_id=emp).exists()
    except Exception:
        return False


def _leave_request_list_qs(request):
    """Same rows request-view lists: subordinates ∪ multi-level approval queue."""
    from base.methods import filtersubordinates
    from leave.methods import filter_conditional_leave_request
    from leave.models import LeaveRequest

    data = LeaveRequest.objects.all()
    conditional_ids = filter_conditional_leave_request(request).values_list(
        "id", flat=True
    )
    return (
        filtersubordinates(request, data, "leave.view_leaverequest")
        | data.filter(id__in=conditional_ids)
    ).distinct()


def _today_leave_qs(request, today, status="approved"):
    return (
        _leave_request_list_qs(request)
        .filter(status=status, start_date__lte=today)
        .filter(Q(end_date__gte=today) | Q(end_date__isnull=True, start_date=today))
    )


def _scoped_active_employee_ids(request):
    """
    Return employee PKs visible on the analytics dashboard.

    ``None`` = org-wide (HR / leadership).

    Managers always see the **nested** reporting tree (direct reports and their
    reports, recursively) — matching org-chart visibility: a manager of
    managers sees the full subtree. Self is excluded; KPIs are about the team.
    """
    from base.dashboard_roles import resolve_home_role

    user = request.user
    if user.is_superuser or user.is_staff:
        return None

    role = resolve_home_role(request)
    if role in ("hr", "leadership"):
        return None

    try:
        from base.methods import get_subordinate_employee_ids

        # Always nested on /dashboard so senior managers see the full subtree
        # regardless of the global NESTED_SUBORDINATE_VISIBILITY flag.
        sub_ids = get_subordinate_employee_ids(request, nested=True)
        return list(set(sub_ids))
    except Exception:
        return []


def _scoped_today_leave_qs(request, today, status="approved"):
    """Leave rows for today, clipped to dashboard employee scope when team-scoped."""
    scoped_ids = _scoped_active_employee_ids(request)
    if scoped_ids is None:
        return _today_leave_qs(request, today, status=status)

    from leave.models import LeaveRequest

    return (
        LeaveRequest.objects.filter(
            status=status,
            start_date__lte=today,
            employee_id__in=scoped_ids,
        )
        .filter(Q(end_date__gte=today) | Q(end_date__isnull=True, start_date=today))
        .distinct()
    )


def _scoped_leave_overlap_qs(request, start, end, status="approved"):
    """Leave overlapping ``[start, end]``, clipped to dashboard employee scope."""
    from leave.models import LeaveRequest

    scoped_ids = _scoped_active_employee_ids(request)
    qs = LeaveRequest.objects.filter(status=status, start_date__lte=end).filter(
        Q(end_date__gte=start) | Q(end_date__isnull=True, start_date__gte=start)
    )
    if scoped_ids is not None:
        qs = qs.filter(employee_id__in=scoped_ids)
    return qs.distinct()


def _team_coverage_next_days(request, emp_ids, days=7):
    """Unique coverage KPIs for managers: upcoming leave + peak concurrent day."""
    today = date.today()
    end = today + timedelta(days=days - 1)
    upcoming_people = 0
    peak_on_leave = 0
    peak_date = None
    try:
        rows = list(
            _scoped_leave_overlap_qs(request, today, end, status="approved").values(
                "employee_id", "start_date", "end_date"
            )
        )
        upcoming_people = len({r["employee_id"] for r in rows})
        team_size = max(1, len(emp_ids) if emp_ids is not None else upcoming_people)
        for offset in range(days):
            day = today + timedelta(days=offset)
            on_leave = 0
            for r in rows:
                start = r["start_date"]
                end_d = r["end_date"] or r["start_date"]
                if start <= day <= end_d:
                    on_leave += 1
            if on_leave > peak_on_leave:
                peak_on_leave = on_leave
                peak_date = day
        peak_pct = round((peak_on_leave / team_size) * 100, 1) if team_size else 0
    except Exception:
        return {
            "upcoming_leave_7d": 0,
            "peak_on_leave_7d": 0,
            "peak_leave_date": None,
            "peak_leave_pct": 0,
        }
    return {
        "upcoming_leave_7d": upcoming_people,
        "peak_on_leave_7d": peak_on_leave,
        "peak_leave_date": peak_date.isoformat() if peak_date else None,
        "peak_leave_pct": peak_pct,
    }


def _mtd_attendance_stats(emp_ids, today=None):
    """Month-to-date attendance rate and late incidents (scoped employee ids)."""
    today = today or date.today()
    first = today.replace(day=1)
    mtd_rate = 0.0
    late_mtd = 0
    present_days = 0
    try:
        from attendance.models import Attendance, AttendanceLateComeEarlyOut

        if not emp_ids:
            return {"mtd_attendance_rate": 0.0, "late_mtd": 0, "present_days_mtd": 0}

        present_days = (
            Attendance.objects.filter(
                employee_id__in=emp_ids,
                attendance_date__gte=first,
                attendance_date__lte=today,
            )
            .values("employee_id", "attendance_date")
            .distinct()
            .count()
        )
        # Expected person-days ≈ active headcount × weekdays so far (simple).
        weekdays = sum(
            1
            for i in range((today - first).days + 1)
            if (first + timedelta(days=i)).weekday() < 5
        )
        expected = max(1, len(emp_ids) * weekdays)
        mtd_rate = round((present_days / expected) * 100, 1)
        late_mtd = (
            AttendanceLateComeEarlyOut.objects.filter(
                type="late_come",
                attendance_id__attendance_date__gte=first,
                attendance_id__attendance_date__lte=today,
                employee_id__in=emp_ids,
            )
            .values("employee_id")
            .distinct()
            .count()
        )
    except Exception:
        pass
    return {
        "mtd_attendance_rate": mtd_rate,
        "late_mtd": late_mtd,
        "present_days_mtd": present_days,
    }


def _scoped_employee_queryset(request, *, active_only=True):
    """Employees clipped to the dashboard reporting scope (nested subordinates)."""
    from employee.models import Employee

    qs = Employee.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    scoped_ids = _scoped_active_employee_ids(request)
    if scoped_ids is not None:
        qs = qs.filter(id__in=scoped_ids)
    return qs, scoped_ids


def _is_team_scoped(request):
    """True when analytics must stay inside the user's subordinate tree."""
    return _scoped_active_employee_ids(request) is not None


def _company_scope_context(request) -> dict:
    """Active company label for KPI / header chrome."""
    selected = request.session.get("selected_company")
    if not selected or selected == "all":
        return {
            "dashboard_company_label": str(_("All companies")),
            "dashboard_company_is_all": True,
        }
    try:
        from base.models import Company

        company = Company.objects.filter(id=int(selected)).only("company").first()
        label = company.company if company else str(_("Company"))
    except Exception:
        label = str(_("Company"))
    return {
        "dashboard_company_label": label,
        "dashboard_company_is_all": False,
    }


@login_required
def main_dashboard_view(request):
    """Render the modern analytics dashboard (manager/HR/leadership).

    Employees (ESS home) cannot access analytics; middleware redirects them.
    """
    from django.apps import apps
    from django.shortcuts import redirect

    from base.dashboard_roles import (
        can_access_analytics_dashboard,
        resolve_home_role,
        role_default_prefs,
    )

    if not can_access_analytics_dashboard(request):
        return redirect("ess-dashboard")

    home_role = resolve_home_role(request)

    enabled_timerunner = True
    get_forecasted_at_work = None

    if apps.is_installed("attendance"):
        try:
            from base.context_processors import timerunner_enabled

            enabled_timerunner = timerunner_enabled(request)["enabled_timerunner"]
        except Exception:
            pass

        try:
            get_forecasted_at_work = request.user.employee_get.get_forecasted_at_work()
        except Exception:
            pass

    # Load saved chart preferences from DB for the current employee
    employee_chart_prefs = "[]"
    try:
        from base.models import DashboardEmployeeCharts

        emp = request.user.employee_get
        obj = DashboardEmployeeCharts.objects.filter(employee=emp).first()
        if obj and obj.charts is not None:
            normalized = _normalize_dashboard_chart_prefs(obj.charts)
            # Persist migration when legacy string-list prefs are detected
            if obj.charts and isinstance(obj.charts, list) and obj.charts != normalized:
                if obj.charts and isinstance(obj.charts[0], str):
                    obj.charts = normalized
                    obj.save(update_fields=["charts"])
            employee_chart_prefs = json.dumps(normalized)
    except Exception:
        pass

    context = {
        "enabled_timerunner": enabled_timerunner,
        "get_forecasted_at_work": get_forecasted_at_work,
        "employee_chart_prefs": employee_chart_prefs,
        "home_role": home_role,
        "role_default_prefs": json.dumps(role_default_prefs(home_role)),
    }
    context.update(_company_scope_context(request))
    context.update(_get_setup_checklist_context(request))
    return render(request, "dashboard.html", context)


def _normalize_dashboard_chart_prefs(charts):
    """
    Modern prefs are ``[{id, visible}, ...]``.
    Legacy FAB prefs stored excluded chart id strings — incompatible with the
    modern dashboard; treat those as empty (all charts visible by default).

    Cards listed in ``FORCE_HIDDEN_DUPLICATES`` stay force-hidden so saved
    prefs cannot resurface duplicate KPI tiles.
    """
    from base.dashboard_roles import FORCE_HIDDEN_DUPLICATES

    if not charts or not isinstance(charts, list):
        return []
    if isinstance(charts[0], str):
        return []
    force_hidden = set(FORCE_HIDDEN_DUPLICATES)
    clean = []
    for item in charts:
        if isinstance(item, dict) and item.get("id"):
            cid = item["id"]
            visible = False if cid in force_hidden else item.get("visible", True)
            clean.append({"id": cid, "visible": visible})
    return clean


@login_required
@require_http_methods(["POST"])
def dismiss_setup_checklist(request):
    """
    HTMX endpoint — records per-user, per-company dismissal and returns empty
    HTML so the banner is removed via outerHTML swap.
    Only admins can dismiss (non-admins never see the banner anyway).
    """
    from base.models import SetupChecklistDismissal

    if _is_setup_admin(request):
        company_pk = _resolve_checklist_company(request)
        SetupChecklistDismissal.objects.get_or_create(
            user=request.user,
            company_id=company_pk,
        )
    return HttpResponse("")


@login_required
def dashboard_kpi_data(request):
    """Return KPI summary data as JSON."""
    from employee.models import Employee

    from_date, to_date = _parse_period(request)
    today = to_date
    real_today = date.today()
    first_of_month = from_date
    scoped_ids = _scoped_active_employee_ids(request)

    emp_qs = Employee.objects.filter(is_active=True)
    if scoped_ids is not None:
        emp_qs = emp_qs.filter(id__in=scoped_ids)
    total_employees = emp_qs.count()

    new_joiners = 0
    try:
        from employee.models import EmployeeWorkInformation

        join_qs = EmployeeWorkInformation.objects.filter(
            date_joining__gte=first_of_month,
            date_joining__lte=today,
        )
        if scoped_ids is not None:
            join_qs = join_qs.filter(employee_id__in=scoped_ids)
        new_joiners = join_qs.count()
    except Exception:
        pass

    # Distinct employees, not leave requests — an employee with two
    # overlapping approved leave records must still count once.
    on_leave_employee_ids = set()
    half_day_today = 0
    try:
        leave_qs = _scoped_today_leave_qs(request, real_today, status="approved")
        on_leave_employee_ids = set(
            leave_qs.values_list("employee_id", flat=True).distinct()
        )
        # Half day only counts when today itself is the broken-down boundary
        # date — a multi-day leave's middle days are always full days
        # regardless of how its start/end boundaries are split.
        half_day_today = (
            leave_qs.filter(
                Q(
                    start_date=real_today,
                    start_date_breakdown__in=["first_half", "second_half"],
                )
                | Q(
                    end_date=real_today,
                    end_date_breakdown__in=["first_half", "second_half"],
                )
            )
            .values("employee_id")
            .distinct()
            .count()
        )
    except Exception:
        pass
    on_leave = len(on_leave_employee_ids)

    present_today = 0
    present_by_work_type = []
    try:
        from attendance.models import Attendance

        present_qs = Attendance.objects.filter(
            attendance_date=real_today, employee_id__in=emp_qs
        )
        present_today = present_qs.values("employee_id").distinct().count()
        present_by_work_type = list(
            present_qs.values("work_type_id__work_type")
            .annotate(count=Count("employee_id", distinct=True))
            .order_by("-count")
        )
        present_by_work_type = [
            {
                "label": row["work_type_id__work_type"] or _("Unspecified"),
                "count": row["count"],
            }
            for row in present_by_work_type
        ]
    except Exception:
        pass

    late_today = 0
    early_out_today = 0
    try:
        from attendance.models import AttendanceLateComeEarlyOut

        late_today = (
            AttendanceLateComeEarlyOut.objects.filter(
                type="late_come",
                attendance_id__attendance_date=real_today,
                employee_id__in=emp_qs,
            )
            .values("employee_id")
            .distinct()
            .count()
        )
        early_out_today = (
            AttendanceLateComeEarlyOut.objects.filter(
                type="early_out",
                attendance_id__attendance_date=real_today,
                employee_id__in=emp_qs,
            )
            .values("employee_id")
            .distinct()
            .count()
        )
    except Exception:
        pass

    # Expected = active employees not on approved leave (excludes leave from
    # the denominator so "absent" is not inflated by people who should be out).
    expected_today = max(0, total_employees - on_leave)
    # "Offline" is deliberately the exact remainder of the other two top-row
    # cards, not the Attendance dashboard's shift-aware "missing punches"
    # definition (which excludes employees with no shift assigned or whose
    # shift hasn't started yet) -- Present Today + Offline + On Leave must
    # always add up to Total Employees for these three cards to read
    # correctly together. The Attendance dashboard's own Offline card is a
    # different, more granular metric and isn't held to this identity.
    not_checked_in = max(0, total_employees - present_today - on_leave)
    expected_to_check_in = not_checked_in
    # Keep absent_today as an alias for not_checked_in for API compatibility.
    absent_today = not_checked_in
    attendance_rate = (
        round((present_today / expected_today * 100), 1) if expected_today > 0 else 0
    )

    pending_leaves = 0
    try:
        pending_leaves = _scoped_today_leave_qs(
            request, real_today, status="requested"
        ).count()
    except Exception:
        pass

    open_recruitments = 0
    try:
        from recruitment.models import Recruitment

        # Org-wide recruitment counts are for HR/leadership only. Team-scoped
        # managers must not see company hiring totals as their team KPI.
        if not _is_team_scoped(request) and (
            request.user.has_perm("recruitment.view_recruitment")
            or request.user.is_superuser
        ):
            open_recruitments = Recruitment.objects.filter(
                is_active=True, closed=False
            ).count()
    except Exception:
        pass

    # Direct reports only (for chip context); KPIs use nested subtree above.
    direct_reports = 0
    try:
        from base.methods import get_subordinate_employee_ids

        direct_reports = len(get_subordinate_employee_ids(request, nested=False))
    except Exception:
        pass

    emp_id_list = list(emp_qs.values_list("id", flat=True))
    coverage = _team_coverage_next_days(request, emp_id_list, days=7)
    mtd = _mtd_attendance_stats(emp_id_list, real_today)

    return JsonResponse(
        {
            "total_employees": total_employees,
            "direct_reports": direct_reports,
            "present_today": present_today,
            "present_by_work_type": present_by_work_type,
            "absent_today": absent_today,
            "expected_today": expected_today,
            "not_checked_in": not_checked_in,
            "expected_to_check_in": expected_to_check_in,
            "attendance_rate": attendance_rate,
            "on_leave": on_leave,
            "half_day_today": half_day_today,
            "late_today": late_today,
            "early_out_today": early_out_today,
            "pending_leaves": pending_leaves,
            "new_joiners": new_joiners,
            "open_recruitments": open_recruitments,
            "upcoming_leave_7d": coverage["upcoming_leave_7d"],
            "peak_on_leave_7d": coverage["peak_on_leave_7d"],
            "peak_leave_date": coverage["peak_leave_date"],
            "peak_leave_pct": coverage["peak_leave_pct"],
            "mtd_attendance_rate": mtd["mtd_attendance_rate"],
            "late_mtd": mtd["late_mtd"],
            "date": today.isoformat(),
            "is_team_scoped": scoped_ids is not None,
        }
    )


@login_required
def dashboard_attendance_trend(request):
    """Weekly-bucketed attendance trend for the current calendar month.

    Requires attendance view permission, superuser, or reporting-manager status
    (managers without org-wide employee view see team-scoped rates).
    """
    user = request.user
    if not (
        user.is_superuser
        or user.has_perm("attendance.view_attendance")
        or _is_manager(user)
    ):
        return JsonResponse({"no_permission": True})

    today = date.today()
    weeks = []
    scoped_ids = _scoped_active_employee_ids(request)

    # Always the current calendar month -- ignores any from_date/to_date so
    # the trend can't be pinned to a stale period by the shared date picker.
    from_date, to_date = _current_month_bounds()

    try:
        from attendance.models import Attendance
        from employee.models import Employee

        emp_qs = Employee.objects.filter(is_active=True)
        if scoped_ids is not None:
            emp_qs = emp_qs.filter(id__in=scoped_ids)
        total = emp_qs.count()

        bucket_start = from_date - timedelta(days=from_date.weekday())
        last_monday = to_date - timedelta(days=to_date.weekday())
        while bucket_start <= last_monday:
            week_end = min(bucket_start + timedelta(days=6), to_date)
            week_start_q = max(bucket_start, from_date)

            present_qs = Attendance.objects.filter(
                attendance_date__gte=week_start_q,
                attendance_date__lte=week_end,
                employee_id__in=emp_qs,
            )
            present = present_qs.values("employee_id").distinct().count()
            rate = min(100.0, round((present / total * 100), 1)) if total > 0 else 0

            is_current = bucket_start <= today <= bucket_start + timedelta(days=6)
            label = bucket_start.strftime("%b %d") + (" (now)" if is_current else "")
            weeks.append({"week": label, "rate": rate, "present": present})
            bucket_start += timedelta(weeks=1)
    except Exception:
        weeks = [{"week": f"W{i+1}", "rate": 0, "present": 0} for i in range(12)]

    return JsonResponse({"weeks": weeks, "is_team_scoped": scoped_ids is not None})


@login_required
def dashboard_leave_breakdown(request):
    """Leave type breakdown for the current calendar month.

    Requires leave.view_leaverequest permission, superuser, or reporting manager.
    Team-scoped users only see leave inside their subordinate tree.
    """
    user = request.user
    if not (
        user.is_superuser
        or user.has_perm("leave.view_leaverequest")
        or _is_manager(user)
    ):
        return JsonResponse({"no_permission": True})

    # Always the current calendar month -- ignores any from_date/to_date so
    # the breakdown can't be pinned to a stale period by the shared date picker.
    first_of_month, last_of_month = _current_month_bounds()
    today = date.today()
    breakdown = []
    scoped_ids = _scoped_active_employee_ids(request)

    try:
        from django.db.models import Count, Sum

        from leave.models import LeaveRequest

        qs = LeaveRequest.objects.filter(
            start_date__gte=first_of_month,
            start_date__lte=last_of_month,
            status__in=["approved", "requested"],
        )
        if scoped_ids is not None:
            qs = qs.filter(employee_id__in=scoped_ids)
        data = (
            qs.values("leave_type_id__name")
            .annotate(count=Count("id"), total_days=Sum("requested_days"))
            .order_by("-count")[:8]
        )

        for item in data:
            breakdown.append(
                {
                    "type": item["leave_type_id__name"] or _("Unknown"),
                    "count": item["count"],
                    "days": float(item["total_days"] or 0),
                }
            )
    except Exception:
        pass

    return JsonResponse(
        {
            "breakdown": breakdown,
            "month": today.strftime("%B %Y"),
            "is_team_scoped": scoped_ids is not None,
        }
    )


@login_required
def dashboard_department_headcount(request):
    """Department-wise headcount within the dashboard reporting scope."""
    departments = []
    emp_qs, scoped_ids = _scoped_employee_queryset(request)

    try:
        from django.db.models import Count

        data = (
            emp_qs.values("employee_work_info__department_id__department")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        for item in data:
            dept = item["employee_work_info__department_id__department"]
            if dept:
                departments.append({"department": dept, "count": item["count"]})
    except Exception:
        pass

    return JsonResponse(
        {"departments": departments, "is_team_scoped": scoped_ids is not None}
    )


@login_required
def dashboard_gender_split(request):
    """Gender distribution within the dashboard reporting scope."""
    genders = []
    emp_qs, scoped_ids = _scoped_employee_queryset(request)

    try:
        from django.db.models import Count

        data = emp_qs.values("gender").annotate(count=Count("id")).order_by("-count")

        gender_map = {
            "male": _("Male"),
            "female": _("Female"),
            "other": _("Other"),
            "": _("Not Specified"),
        }
        for item in data:
            genders.append(
                {
                    "gender": gender_map.get(
                        item["gender"], item["gender"] or _("Not Specified")
                    ),
                    # The name above is translated, so it cannot be used to look
                    # up a colour or build a filter. Ship the raw field value too.
                    "key": item["gender"] or "",
                    "count": item["count"],
                }
            )
    except Exception:
        pass

    return JsonResponse({"genders": genders, "is_team_scoped": scoped_ids is not None})


@login_required
def dashboard_announcements(request):
    """Active announcements for the current user."""
    from base.models import Announcement

    today = date.today()
    announcements = []

    try:
        from django.db.models import Q

        qs = Announcement.objects.filter(
            Q(expire_date__gte=today) | Q(expire_date__isnull=True),
        ).order_by("-created_at")[:20]

        for ann in qs:
            announcements.append(
                {
                    "id": ann.id,
                    "title": ann.title,
                    "description": (ann.description or "")[:160],
                    "date": (
                        ann.created_at.strftime("%b %d, %Y") if ann.created_at else ""
                    ),
                    "expire_date": (
                        ann.expire_date.strftime("%b %d") if ann.expire_date else None
                    ),
                }
            )
    except Exception:
        pass

    return JsonResponse({"announcements": announcements})


@login_required
def dashboard_announcement_detail(request, pk):
    """Return a single announcement's full details as JSON."""
    from base.models import Announcement, AnnouncementView

    try:
        ann = Announcement.objects.get(pk=pk)
    except Announcement.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    # Track view (field is employee_id, not employee)
    employee = getattr(request.user, "employee_get", None)
    if employee:
        AnnouncementView.objects.get_or_create(
            announcement=ann, user=request.user, defaults={"employee_id": employee}
        )

    attachments = []
    for att in ann.attachments.all():
        try:
            url = att.file.url
            name = att.file.name.split("/")[-1]
            is_image = any(
                url.lower().endswith(ext)
                for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]
            )
            attachments.append({"url": url, "name": name, "is_image": is_image})
        except Exception:
            pass

    departments = [d.department for d in ann.department.all()]
    job_positions = [j.job_position for j in ann.job_position.all()]
    views_count = ann.get_views().count() if hasattr(ann, "get_views") else 0

    return JsonResponse(
        {
            "id": ann.id,
            "title": ann.title,
            "description": ann.description or "",
            "date": (
                ann.created_at.strftime("%B %d, %Y at %I:%M %p")
                if ann.created_at
                else ""
            ),
            "expire_date": (
                ann.expire_date.strftime("%b %d, %Y") if ann.expire_date else None
            ),
            "attachments": attachments,
            "departments": departments,
            "job_positions": job_positions,
            "views_count": views_count,
            "comments_disabled": ann.disable_comments,
        }
    )


@login_required
def dashboard_todays_leave(request):
    """Employees on leave today within the dashboard reporting scope."""
    today = date.today()
    leaves = []

    user = request.user
    is_mgr = _is_manager(user)
    can_view_team = (
        user.is_superuser
        or user.has_perm("leave.view_leaverequest")
        or is_mgr
    )
    scoped_ids = _scoped_active_employee_ids(request)

    try:
        qs = _scoped_today_leave_qs(
            request, today, status="approved"
        ).select_related("employee_id", "leave_type_id")

        if not can_view_team:
            employee = getattr(user, "employee_get", None)
            qs = qs.filter(employee_id=employee) if employee else qs.none()

        qs = qs.order_by("employee_id__employee_first_name")[:20]

        for lr in qs:
            emp = lr.employee_id
            leaves.append(
                {
                    "id": lr.id,
                    "employee_id": emp.id if emp else None,
                    "employee": emp.get_full_name() if emp else "—",
                    "badge_id": getattr(emp, "badge_id", "") or "",
                    "avatar": emp.get_avatar() if emp else None,
                    "leave_type": lr.leave_type_id.name if lr.leave_type_id else "—",
                    "start": lr.start_date.strftime("%b %d"),
                    "end": lr.end_date.strftime("%b %d") if lr.end_date else "—",
                    "days": float(lr.requested_days) if lr.requested_days else 1,
                }
            )
    except Exception:
        pass

    return JsonResponse(
        {
            "leaves": leaves,
            "date": today.isoformat(),
            "is_restricted": not can_view_team or scoped_ids is not None,
            "is_team_scoped": scoped_ids is not None,
        }
    )


@login_required
def dashboard_upcoming_holidays(request):
    """Holidays occurring within the current calendar month.

    ``Holidays.objects`` is a ``HorillaCompanyManager``, so the active
    company (or "All Companies") is already applied automatically -- same
    as every other query on this dashboard -- with no manual session lookup
    needed here.
    """
    today = date.today()
    first_of_month, last_of_month = _current_month_bounds()
    holidays_data = []

    try:
        from django.db.models import Q

        from base.models import Holidays

        qs = Holidays.objects.filter(
            Q(start_date__lte=last_of_month)
            & (
                Q(end_date__gte=first_of_month)
                | Q(end_date__isnull=True, start_date__gte=first_of_month)
            ),
            is_specific=False,
        )

        for h in qs.order_by("start_date")[:10]:
            holidays_data.append(
                {
                    "id": h.pk,
                    "name": h.name,
                    "start_date": h.start_date.strftime("%b %d"),
                    "end_date": h.end_date.strftime("%b %d") if h.end_date else None,
                    "days_away": (h.start_date - today).days,
                }
            )
    except Exception:
        pass

    return JsonResponse({"holidays": holidays_data})


@login_required
def dashboard_birthdays_anniversaries(request):
    """Birthdays and work anniversaries in the current month (reporting scope)."""
    today = date.today()
    birthdays = []
    anniversaries = []
    emp_qs, scoped_ids = _scoped_employee_queryset(request)

    def _this_month_date(month_day_source):
        """Recreate a month/day in the current year, dodging Feb 29 on non-leap years."""
        try:
            return month_day_source.replace(year=today.year)
        except ValueError:
            return date(today.year, month_day_source.month, 28)

    try:
        from employee.models import EmployeeWorkInformation

        # Birthdays — compare month only, so already-celebrated days this
        # month still show alongside ones still to come.
        for emp in emp_qs.filter(dob__month=today.month).exclude(dob__isnull=True):
            this_year_bday = _this_month_date(emp.dob)
            birthdays.append(
                {
                    "id": emp.id,
                    "name": emp.get_full_name(),
                    "avatar": emp.get_avatar(),
                    "date": this_year_bday.strftime("%b %d"),
                    "days_away": (this_year_bday - today).days,
                }
            )

        # Closest to today first (whether already past or still upcoming this
        # month), so the 10-item cap below keeps the most relevant entries.
        birthdays.sort(key=lambda x: abs(x["days_away"]))

        # Work anniversaries — same current-month rule as birthdays.
        ann_qs = EmployeeWorkInformation.objects.filter(
            employee_id__in=emp_qs,
            date_joining__month=today.month,
        ).exclude(date_joining__isnull=True).select_related("employee_id")
        for wi in ann_qs:
            join = wi.date_joining
            this_year_ann = _this_month_date(join)
            years = today.year - join.year
            emp = wi.employee_id
            anniversaries.append(
                {
                    "id": emp.id,
                    "name": emp.get_full_name(),
                    "avatar": emp.get_avatar(),
                    "date": this_year_ann.strftime("%b %d"),
                    "years": years,
                    "days_away": (this_year_ann - today).days,
                }
            )

        anniversaries.sort(key=lambda x: abs(x["days_away"]))
    except Exception:
        pass

    return JsonResponse(
        {
            "birthdays": birthdays[:10],
            "anniversaries": anniversaries[:10],
            "is_team_scoped": scoped_ids is not None,
        }
    )


@login_required
def dashboard_recruitment_pipeline(request):
    """Recruitment pipeline funnel — candidates aggregated by stage type.

    Org-wide metric: requires recruitment view permission. Hidden for
    team-scoped managers so hiring totals never look like team KPIs.
    """
    user = request.user
    if _is_team_scoped(request) or not (
        user.has_perm("recruitment.view_recruitment") or user.is_superuser
    ):
        response = JsonResponse({"no_permission": True})
        response["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response

    stages = []

    try:
        from django.db.models import Count

        from recruitment.models import Candidate, Recruitment, Stage

        active_recruitments = Recruitment.objects.filter(is_active=True, closed=False)
        total_active = active_recruitments.count()

        # Aggregate by stage_type so duplicate stage names across recruitments collapse
        stage_type_order = [t[0] for t in Stage.stage_types]
        stage_type_labels = {t[0]: str(t[1]) for t in Stage.stage_types}

        data = (
            Candidate.objects.filter(
                # recruitment_id__in=active_recruitments,
                is_active=True,
            )
            .values("stage_id__stage_type")
            .annotate(count=Count("id"))
        )

        # Build ordered dict keyed by stage_type
        totals = {}
        for item in data:
            st = item["stage_id__stage_type"] or ""
            totals[st] = totals.get(st, 0) + item["count"]

        # Output in canonical stage order
        for st in stage_type_order:
            if st in totals:
                stages.append(
                    {
                        "stage": stage_type_labels.get(st, st.capitalize()),
                        "type": st,
                        "count": totals[st],
                    }
                )

        # Summary counts
        total_candidates = Candidate.objects.filter(
            recruitment_id__in=active_recruitments, canceled=False
        ).count()
        hired = Candidate.objects.filter(
            recruitment_id__in=active_recruitments, hired=True
        ).count()
        rejected = Candidate.objects.filter(
            recruitment_id__in=active_recruitments, canceled=True
        ).count()
    except Exception:
        total_active = 0
        total_candidates = 0
        hired = 0
        rejected = 0

    response = JsonResponse(
        {
            "stages": stages,
            "total_active": total_active,
            "total_candidates": total_candidates,
            "hired": hired,
            "rejected": rejected,
        }
    )
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


@login_required
def dashboard_payroll_summary(request):
    """Payroll summary — selected period vs previous period.

    Restricted to payroll operators (staff/superuser or change_payslip), not
    every user who can merely view a payslip — keeps compensation totals off
    the general manager home.
    """
    user = request.user
    is_payroll_operator = user.is_superuser or (
        user.has_perm("payroll.view_payslip")
        and (user.is_staff or user.has_perm("payroll.change_payslip"))
    )
    if not is_payroll_operator:
        return JsonResponse({"no_permission": True})
    from_date, to_date = _parse_period(request)
    today = to_date
    first_of_month = from_date
    # Always use full calendar month boundaries for previous month
    prev_month_end = first_of_month - timedelta(days=1)  # last day of previous month
    prev_month_start = prev_month_end.replace(day=1)  # first day of previous month

    current = {"gross": 0, "deductions": 0, "net": 0, "count": 0}
    previous = {"gross": 0, "deductions": 0, "net": 0, "count": 0}

    try:
        from django.db.models import Sum

        from payroll.models.models import Payslip

        def _aggregate(qs):
            agg = qs.aggregate(
                total_gross=Sum("gross_pay"),
                total_deductions=Sum("deduction"),
                total_net=Sum("net_pay"),
            )
            return {
                "gross": round(float(agg["total_gross"] or 0), 2),
                "deductions": round(float(agg["total_deductions"] or 0), 2),
                "net": round(float(agg["total_net"] or 0), 2),
                "count": qs.count(),
            }

        current_qs = Payslip.objects.filter(
            start_date__gte=first_of_month,
            start_date__lte=today,
            status__in=["confirmed", "paid", "review_ongoing"],
        )
        current = _aggregate(current_qs)

        prev_qs = Payslip.objects.filter(
            start_date__gte=prev_month_start,
            start_date__lte=prev_month_end,
            status__in=["confirmed", "paid"],
        )
        previous = _aggregate(prev_qs)
    except Exception:
        pass

    # Trend calculation
    change_pct = 0
    if previous["net"] > 0:
        change_pct = round(
            ((current["net"] - previous["net"]) / previous["net"]) * 100, 1
        )

    return JsonResponse(
        {
            "current_month": today.strftime("%B %Y"),
            "previous_month": prev_month_start.strftime("%B %Y"),
            "current": current,
            "previous": previous,
            "change_percent": change_pct,
        }
    )


@login_required
def dashboard_pending_approvals(request):
    """Pending items awaiting the logged-in user's approval.

    For users without any approval permission, shows their own pending requests
    (items they submitted that are waiting for approval).
    """
    user = request.user
    pending = {}

    has_leave_perm = user.has_perm("leave.change_leaverequest")
    has_attendance_perm = user.has_perm("attendance.change_validateattendance")
    has_asset_perm = user.has_perm("asset.change_assetrequest")
    has_shift_perm = user.has_perm("base.change_shiftrequest")
    has_wt_perm = user.has_perm("base.change_worktyperequest")
    has_reimb_perm = user.has_perm("payroll.change_reimbursement")
    is_mgr = _is_manager(user)

    can_approve = any(
        [
            has_leave_perm,
            has_attendance_perm,
            has_asset_perm,
            has_shift_perm,
            has_wt_perm,
            has_reimb_perm,
            is_mgr,
        ]
    )
    is_restricted = not can_approve
    employee = getattr(user, "employee_get", None)

    # Leave requests — managers use nested team scope on the dashboard so
    # senior managers see requests from the full reporting subtree.
    try:
        from leave.models import LeaveRequest

        if can_approve:
            scoped_ids = _scoped_active_employee_ids(request)
            if scoped_ids is not None:
                leave_count = LeaveRequest.objects.filter(
                    status="requested", employee_id__in=scoped_ids
                ).count()
            else:
                leave_count = (
                    _leave_request_list_qs(request).filter(status="requested").count()
                )
        else:
            leave_count = (
                LeaveRequest.objects.filter(
                    employee_id=employee, status="requested"
                ).count()
                if employee
                else 0
            )
        pending["leave_requests"] = leave_count
    except Exception:
        pending["leave_requests"] = 0

    # Attendance requests — same queryset as the Requested Attendances tab badge
    try:
        from attendance.cbv.attendance_request import (
            AttendanceRequestListTab,
            _request_tab_badge_count,
        )
        from attendance.models import Attendance

        if can_approve:
            att_count = _request_tab_badge_count(request, AttendanceRequestListTab)
        else:
            att_count = (
                Attendance.objects.filter(
                    employee_id=employee,
                    is_validate_request=True,
                    is_validate_request_approved=False,
                ).count()
                if employee
                else 0
            )
        pending["attendance_requests"] = att_count
    except Exception:
        pending["attendance_requests"] = 0

    # Asset requests
    try:
        from asset.models import AssetRequest
        from base.methods import filtersubordinates

        if can_approve:
            qs = AssetRequest.objects.filter(asset_request_status="Requested")
            asset_count = (
                (
                    filtersubordinates(
                        request,
                        qs,
                        "asset.view_assetrequest",
                        field="requested_employee_id",
                    )
                    | (
                        qs.filter(requested_employee_id=employee)
                        if employee
                        else qs.none()
                    )
                )
                .distinct()
                .count()
            )
        else:
            asset_count = (
                AssetRequest.objects.filter(
                    requested_employee_id=employee,
                    asset_request_status="Requested",
                ).count()
                if employee
                else 0
            )
        pending["asset_requests"] = asset_count
    except Exception:
        pending["asset_requests"] = 0

    # Shift requests
    try:
        from base.methods import filtersubordinates
        from base.models import ShiftRequest

        if can_approve:
            data = ShiftRequest.objects.filter(employee_id__is_active=True)
            shift_count = (
                (
                    filtersubordinates(
                        request,
                        data.filter(reallocate_to__isnull=True),
                        "base.view_shiftrequest",
                    )
                    | (data.filter(employee_id=employee) if employee else data.none())
                )
                .filter(approved=False, canceled=False)
                .distinct()
                .count()
            )
        else:
            shift_count = (
                ShiftRequest.objects.filter(
                    employee_id=employee,
                    approved=False,
                    canceled=False,
                ).count()
                if employee
                else 0
            )
        pending["shift_requests"] = shift_count
    except Exception:
        pending["shift_requests"] = 0

    # Work type requests
    try:
        from base.methods import filtersubordinates
        from base.models import WorkTypeRequest

        if can_approve:
            # WorkRequestListView does not drop inactive employees.
            data = WorkTypeRequest.objects.all()
            wt_count = (
                (
                    filtersubordinates(request, data, "base.view_worktyperequest")
                    | (data.filter(employee_id=employee) if employee else data.none())
                )
                .filter(approved=False, canceled=False)
                .distinct()
                .count()
            )
        else:
            wt_count = (
                WorkTypeRequest.objects.filter(
                    employee_id=employee,
                    approved=False,
                    canceled=False,
                ).count()
                if employee
                else 0
            )
        pending["work_type_requests"] = wt_count
    except Exception:
        pending["work_type_requests"] = 0

    # Reimbursement requests
    try:
        from base.methods import filter_own_records
        from payroll.models.models import Reimbursement

        if can_approve:
            # Match ReimbursementsListView's own scoping
            # (payroll.view_reimbursement) so this count agrees with the
            # destination list.
            qs = Reimbursement.objects.filter(status="requested", type="reimbursement")
            reimb_count = filter_own_records(
                request, qs, "payroll.view_reimbursement"
            ).count()
        else:
            reimb_count = (
                Reimbursement.objects.filter(
                    employee_id=employee, status="requested"
                ).count()
                if employee
                else 0
            )
        pending["reimbursements"] = reimb_count
    except Exception:
        pending["reimbursements"] = 0

    pending["total"] = sum(pending.values())

    return JsonResponse({"pending": pending, "is_restricted": is_restricted})


@login_required
def dashboard_team_pulse(request):
    """Team / subordinate pulse for manager-friendly dashboard tiles.

    Returns presence counts, late arrivals, and a short member roster with
    status for the same employee scope as other analytics KPIs.
    """
    from employee.models import Employee

    today = date.today()
    scoped_ids = _scoped_active_employee_ids(request)
    emp_qs = Employee.objects.filter(is_active=True).select_related(
        "employee_work_info__job_position_id"
    )
    if scoped_ids is not None:
        emp_qs = emp_qs.filter(id__in=scoped_ids)

    # Roster prefers the nested reporting tree for managers; org-wide for HR.
    roster_qs = emp_qs
    try:
        from base.methods import get_subordinate_employee_ids

        sub_ids = get_subordinate_employee_ids(request, nested=True)
        if sub_ids:
            roster_qs = emp_qs.filter(id__in=sub_ids)
    except Exception:
        pass

    team_size = emp_qs.count()
    on_leave_ids = set()
    try:
        on_leave_ids = set(
            _scoped_today_leave_qs(request, today, status="approved")
            .values_list("employee_id", flat=True)
            .distinct()
        )
    except Exception:
        pass

    present_ids = set()
    try:
        from attendance.models import Attendance

        present_ids = set(
            Attendance.objects.filter(
                attendance_date=today, employee_id__in=emp_qs
            )
            .values_list("employee_id", flat=True)
            .distinct()
        )
    except Exception:
        pass

    late_ids = set()
    early_out_ids = set()
    try:
        from attendance.models import AttendanceLateComeEarlyOut

        late_qs = AttendanceLateComeEarlyOut.objects.filter(
            type="late_come",
            attendance_id__attendance_date=today,
            employee_id__in=emp_qs,
        )
        late_ids = set(late_qs.values_list("employee_id", flat=True).distinct())
        early_out_ids = set(
            AttendanceLateComeEarlyOut.objects.filter(
                type="early_out",
                attendance_id__attendance_date=today,
                employee_id__in=emp_qs,
            )
            .values_list("employee_id", flat=True)
            .distinct()
        )
    except Exception:
        pass

    on_leave = len(on_leave_ids & set(emp_qs.values_list("id", flat=True)))
    present = len(present_ids)
    offline = max(0, team_size - present - on_leave)

    members = []
    for emp in roster_qs.order_by("employee_first_name", "employee_last_name")[:14]:
        emp_id = emp.id
        if emp_id in on_leave_ids:
            status = "leave"
        elif emp_id in late_ids:
            status = "late"
        elif emp_id in present_ids:
            status = "present"
        else:
            status = "offline"
        job = ""
        try:
            job = str(emp.get_job_position() or "")
        except Exception:
            job = ""
        members.append(
            {
                "id": emp_id,
                "name": emp.get_full_name(),
                "avatar": emp.get_avatar(),
                "job": job,
                "status": status,
            }
        )

    return JsonResponse(
        {
            "team_size": team_size,
            "present": present,
            "offline": offline,
            "on_leave": on_leave,
            "late_today": len(late_ids),
            "early_out_today": len(early_out_ids),
            "members": members,
            "is_team_scoped": scoped_ids is not None,
        }
    )


@login_required
def dashboard_module_pulse(request):
    """Cross-module KPI packs for the analytics home mosaic.

    Each module returns a small set of manager-useful counts, clipped to the
    nested reporting tree for managers and org-wide for HR/leadership.
    Modules the user cannot access are marked ``available: false``.
    """
    from django.apps import apps

    from employee.models import Employee

    today = date.today()
    first_of_month, last_of_month = _current_month_bounds()
    scoped_ids = _scoped_active_employee_ids(request)
    user = request.user
    is_mgr = _is_manager(user)

    emp_qs = Employee.objects.filter(is_active=True)
    if scoped_ids is not None:
        emp_qs = emp_qs.filter(id__in=scoped_ids)
    emp_ids = list(emp_qs.values_list("id", flat=True))

    def _can(*perms):
        return user.is_superuser or any(user.has_perm(p) for p in perms)

    modules = {}

    # ── Attendance (unique vs hero Present/Absent/On Leave/Late accents) ─
    att_ok = _can("attendance.view_attendance") or is_mgr
    if apps.is_installed("attendance") and att_ok:
        early = pending_val = 0
        ot_hours = 0.0
        mtd = {"mtd_attendance_rate": 0.0, "late_mtd": 0}
        try:
            from attendance.models import (
                Attendance,
                AttendanceLateComeEarlyOut,
                AttendanceOverTime,
            )

            early = (
                AttendanceLateComeEarlyOut.objects.filter(
                    type="early_out",
                    attendance_id__attendance_date=today,
                    employee_id__in=emp_ids,
                )
                .values("employee_id")
                .distinct()
                .count()
            )
            pending_val = Attendance.objects.filter(
                employee_id__in=emp_ids,
                is_validate_request=True,
                is_validate_request_approved=False,
            ).count()
            ot_qs = AttendanceOverTime.objects.filter(
                employee_id__in=emp_ids,
                month=today.strftime("%B").lower(),
                year=str(today.year),
            )
            total_seconds = 0
            for row in ot_qs.only("overtime_second"):
                total_seconds += getattr(row, "overtime_second", 0) or 0
            ot_hours = round(total_seconds / 3600, 1)
            mtd = _mtd_attendance_stats(emp_ids, today)
        except Exception:
            pass
        modules["attendance"] = {
            "available": True,
            "metrics": [
                {
                    "key": "mtd_rate",
                    "label": str(_("MTD attendance %")),
                    "value": mtd.get("mtd_attendance_rate", 0),
                },
                {
                    "key": "late_mtd",
                    "label": str(_("Late (month)")),
                    "value": mtd.get("late_mtd", 0),
                },
                {"key": "early_out", "label": str(_("Early out today")), "value": early},
                {
                    "key": "pending",
                    "label": str(_("Pending validation")),
                    "value": pending_val,
                },
                {
                    "key": "ot_hours",
                    "label": str(_("OT hours (month)")),
                    "value": ot_hours,
                },
            ],
        }
    else:
        modules["attendance"] = {"available": False, "metrics": []}

    # ── Leave (unique vs hero On Leave accent) ─────────────────────────
    leave_ok = _can("leave.view_leaverequest") or is_mgr
    if apps.is_installed("leave") and leave_ok:
        pending = approved_month = rejected_month = 0
        try:
            from leave.models import LeaveRequest

            leave_base = LeaveRequest.objects.filter(employee_id__in=emp_ids)
            pending = leave_base.filter(status="requested").count()
            approved_month = leave_base.filter(
                status="approved",
                start_date__lte=last_of_month,
            ).filter(
                Q(end_date__gte=first_of_month)
                | Q(end_date__isnull=True, start_date__gte=first_of_month)
            ).count()
            rejected_month = leave_base.filter(
                status="cancelled",
                start_date__gte=first_of_month,
                start_date__lte=last_of_month,
            ).count()
            rejected_month += leave_base.filter(
                status="rejected",
                start_date__gte=first_of_month,
                start_date__lte=last_of_month,
            ).count()
        except Exception:
            pass
        # Coverage Next 7 Days (hero) owns upcoming/peak; leave tile stays request ops.
        modules["leave"] = {
            "available": True,
            "metrics": [
                {"key": "pending", "label": str(_("Pending requests")), "value": pending},
                {
                    "key": "approved_month",
                    "label": str(_("Approved (month)")),
                    "value": approved_month,
                },
                {
                    "key": "rejected_month",
                    "label": str(_("Rejected / cancelled")),
                    "value": rejected_month,
                },
            ],
        }
    else:
        modules["leave"] = {"available": False, "metrics": []}

    # ── Recruitment ────────────────────────────────────────────────────
    # Company hiring pipeline is org-wide; keep it off team-scoped manager homes.
    rec_ok = (
        not _is_team_scoped(request)
        and _can("recruitment.view_recruitment", "recruitment.view_candidate")
    )
    if apps.is_installed("recruitment") and rec_ok:
        open_jobs = candidates = hired_month = interviews = 0
        try:
            from recruitment.models import Candidate, Recruitment, Stage

            open_jobs = Recruitment.objects.filter(
                is_active=True, closed=False
            ).count()
            candidates = Candidate.objects.filter(
                is_active=True, hired=False, canceled=False
            ).count()
            hired_month = Candidate.objects.filter(
                hired=True,
                hired_date__gte=first_of_month,
                hired_date__lte=last_of_month,
            ).count()
            interview_stages = Stage.objects.filter(
                stage_type="interview", recruitment_id__closed=False
            )
            interviews = Candidate.objects.filter(
                stage_id__in=interview_stages, is_active=True, canceled=False
            ).count()
        except Exception:
            pass
        modules["recruitment"] = {
            "available": True,
            "metrics": [
                {"key": "open", "label": str(_("Open jobs")), "value": open_jobs},
                {
                    "key": "candidates",
                    "label": str(_("Active candidates")),
                    "value": candidates,
                },
                {
                    "key": "interviews",
                    "label": str(_("In interview")),
                    "value": interviews,
                },
                {
                    "key": "hired_month",
                    "label": str(_("Hired (month)")),
                    "value": hired_month,
                },
            ],
        }
    else:
        modules["recruitment"] = {"available": False, "metrics": []}

    # ── Assets ─────────────────────────────────────────────────────────
    asset_ok = _can("asset.view_asset", "asset.view_assetrequest") or is_mgr
    if apps.is_installed("asset") and asset_ok:
        assigned = requests_pending = return_req = 0
        try:
            from asset.models import AssetAssignment, AssetRequest

            assigned = AssetAssignment.objects.filter(
                assigned_to_employee_id__in=emp_ids,
                return_date__isnull=True,
            ).count()
            requests_pending = AssetRequest.objects.filter(
                requested_employee_id__in=emp_ids,
                asset_request_status="Requested",
            ).count()
            return_req = AssetAssignment.objects.filter(
                assigned_to_employee_id__in=emp_ids,
                return_request=True,
                return_date__isnull=True,
            ).count()
        except Exception:
            pass
        modules["assets"] = {
            "available": True,
            "metrics": [
                {
                    "key": "assigned",
                    "label": str(_("Assets assigned")),
                    "value": assigned,
                },
                {
                    "key": "requests",
                    "label": str(_("Pending requests")),
                    "value": requests_pending,
                },
                {
                    "key": "returns",
                    "label": str(_("Return requests")),
                    "value": return_req,
                },
            ],
        }
    else:
        modules["assets"] = {"available": False, "metrics": []}

    # ── Performance ────────────────────────────────────────────────────
    pms_ok = _can("pms.view_employeeobjective", "pms.view_feedback") or is_mgr
    if apps.is_installed("pms") and pms_ok:
        active_obj = at_risk = behind = feedback_open = 0
        try:
            from pms.models import EmployeeObjective, Feedback

            obj_qs = EmployeeObjective.objects.filter(
                employee_id__in=emp_ids, archive=False
            )
            active_obj = obj_qs.exclude(status="Closed").count()
            at_risk = obj_qs.filter(status="At Risk").count()
            behind = obj_qs.filter(status="Behind").count()
            feedback_open = Feedback.objects.filter(
                employee_id__in=emp_ids
            ).exclude(status="Closed").count()
        except Exception:
            pass
        modules["performance"] = {
            "available": True,
            "metrics": [
                {
                    "key": "active",
                    "label": str(_("Active objectives")),
                    "value": active_obj,
                },
                {"key": "at_risk", "label": str(_("At risk")), "value": at_risk},
                {"key": "behind", "label": str(_("Behind")), "value": behind},
                {
                    "key": "feedback",
                    "label": str(_("Open feedback")),
                    "value": feedback_open,
                },
            ],
        }
    else:
        modules["performance"] = {"available": False, "metrics": []}

    # ── Payroll ────────────────────────────────────────────────────────
    pay_ok = _can("payroll.view_payslip", "payroll.change_payslip") or (
        user.is_staff and _can("payroll.view_payslip")
    )
    if apps.is_installed("payroll") and pay_ok:
        payslips = reimbursements = loans = contracts = 0
        try:
            from payroll.models.models import Contract, LoanAccount, Payslip

            payslips = Payslip.objects.filter(
                start_date__gte=first_of_month,
                start_date__lte=last_of_month,
            ).count()
            if scoped_ids is not None:
                payslips = Payslip.objects.filter(
                    employee_id__in=emp_ids,
                    start_date__gte=first_of_month,
                    start_date__lte=last_of_month,
                ).count()
            contracts = Contract.objects.filter(
                employee_id__in=emp_ids, contract_status="active"
            ).count()
            try:
                loans = LoanAccount.objects.filter(
                    employee_id__in=emp_ids
                ).exclude(settled=True).count()
            except Exception:
                try:
                    loans = LoanAccount.objects.filter(employee_id__in=emp_ids).count()
                except Exception:
                    loans = 0
            try:
                from payroll.models.models import Reimbursement

                reimbursements = Reimbursement.objects.filter(
                    status="requested"
                ).count()
                if scoped_ids is not None:
                    reimbursements = Reimbursement.objects.filter(
                        employee_id__in=emp_ids, status="requested"
                    ).count()
            except Exception:
                reimbursements = 0
        except Exception:
            pass
        modules["payroll"] = {
            "available": True,
            "metrics": [
                {
                    "key": "payslips",
                    "label": str(_("Payslips (month)")),
                    "value": payslips,
                },
                {
                    "key": "contracts",
                    "label": str(_("Active contracts")),
                    "value": contracts,
                },
                {
                    "key": "reimbursements",
                    "label": str(_("Reimbursements")),
                    "value": reimbursements,
                },
                {"key": "loans", "label": str(_("Active loans")), "value": loans},
            ],
        }
    else:
        modules["payroll"] = {"available": False, "metrics": []}

    # ── Workforce ops (offboarding + helpdesk) ─────────────────────────
    off_ok = apps.is_installed("offboarding") and (
        _can("offboarding.view_offboardingemployee") or is_mgr or user.is_superuser
    )
    help_ok = apps.is_installed("helpdesk") and (
        _can("helpdesk.view_ticket") or is_mgr or user.is_superuser
    )
    if off_ok or help_ok:
        exits = resignations = open_tickets = new_tickets = 0
        if off_ok:
            try:
                from offboarding.models import OffboardingEmployee, ResignationLetter

                exits = OffboardingEmployee.objects.filter(
                    employee_id__in=emp_ids
                ).count()
                resignations = ResignationLetter.objects.filter(
                    status="requested", employee_id__in=emp_ids
                ).count()
            except Exception:
                pass
        if help_ok:
            try:
                from helpdesk.models import Ticket

                tq = Ticket.objects.exclude(status__in=["resolved", "canceled"])
                if scoped_ids is not None:
                    # Tickets assigned to / created for scoped employees when possible
                    tq = tq.filter(
                        Q(employee_id__in=emp_ids) | Q(assigned_to__in=emp_ids)
                    )
                open_tickets = tq.count()
                new_tickets = tq.filter(status="new").count()
            except Exception:
                pass
        modules["workforce"] = {
            "available": True,
            "metrics": [
                {
                    "key": "exits",
                    "label": str(_("Offboarding")),
                    "value": exits,
                },
                {
                    "key": "resignations",
                    "label": str(_("Resignations")),
                    "value": resignations,
                },
                {
                    "key": "tickets",
                    "label": str(_("Open tickets")),
                    "value": open_tickets,
                },
                {
                    "key": "new_tickets",
                    "label": str(_("New tickets")),
                    "value": new_tickets,
                },
            ],
        }
    else:
        modules["workforce"] = {"available": False, "metrics": []}

    return JsonResponse(
        {
            "modules": modules,
            "team_size": len(emp_ids),
            "is_team_scoped": scoped_ids is not None,
            "date": today.isoformat(),
        }
    )


@login_required
def dashboard_module_detail(request):
    """Return detail rows for a module KPI click (popup modal payload)."""
    from django.apps import apps

    from employee.models import Employee

    module = (request.GET.get("module") or "").strip()
    metric = (request.GET.get("metric") or "").strip()
    today = date.today()
    first_of_month, last_of_month = _current_month_bounds()
    scoped_ids = _scoped_active_employee_ids(request)

    emp_qs = Employee.objects.filter(is_active=True).select_related(
        "employee_work_info__job_position_id",
        "employee_work_info__department_id",
    )
    if scoped_ids is not None:
        emp_qs = emp_qs.filter(id__in=scoped_ids)
    emp_ids = list(emp_qs.values_list("id", flat=True))

    def rows_for(ids, badge="", badge_tone="slate", meta_fn=None):
        out = []
        id_set = set(ids)
        for emp in emp_qs.filter(id__in=id_set).order_by(
            "employee_first_name", "employee_last_name"
        )[:40]:
            meta = meta_fn(emp) if meta_fn else ""
            try:
                profile = reverse("employee-view-individual", kwargs={"obj_id": emp.id})
            except Exception:
                profile = "#"
            out.append(
                {
                    "id": emp.id,
                    "name": emp.get_full_name(),
                    "avatar": emp.get_avatar(),
                    "job": str(emp.get_job_position() or ""),
                    "department": str(emp.get_department() or ""),
                    "meta": meta,
                    "badge": badge,
                    "badge_tone": badge_tone,
                    "url": profile,
                }
            )
        return out

    title = str(_("Details"))
    subtitle = ""
    rows = []
    view_all = ""

    try:
        if module == "attendance" and apps.is_installed("attendance"):
            from attendance.models import (
                Attendance,
                AttendanceLateComeEarlyOut,
                AttendanceOverTime,
            )

            present_ids = set(
                Attendance.objects.filter(
                    attendance_date=today, employee_id__in=emp_ids
                ).values_list("employee_id", flat=True)
            )
            leave_ids = set(
                _scoped_today_leave_qs(request, today, status="approved").values_list(
                    "employee_id", flat=True
                )
            )
            if metric == "present":
                title = str(_("Present today"))
                rows = rows_for(present_ids, str(_("Present")), "green")
                view_all = (
                    _safe_url("employee-view")
                    + f"?present_on={today.isoformat()}&is_active=True&filter_applied=on"
                )
            elif metric == "absent":
                title = str(_("Absent / not punched"))
                absent_ids = set(emp_ids) - present_ids - leave_ids
                rows = rows_for(absent_ids, str(_("Absent")), "red")
                view_all = (
                    _safe_url("employee-view")
                    + f"?expected_to_check_in={today.isoformat()}&is_active=True&filter_applied=on"
                )
            elif metric == "late":
                title = str(_("Late arrivals"))
                late_ids = set(
                    AttendanceLateComeEarlyOut.objects.filter(
                        type="late_come",
                        attendance_id__attendance_date=today,
                        employee_id__in=emp_ids,
                    ).values_list("employee_id", flat=True)
                )
                rows = rows_for(late_ids, str(_("Late")), "amber")
                view_all = (
                    _safe_url("employee-view")
                    + f"?present_on={today.isoformat()}&attendance_status=late_come&is_active=True&filter_applied=on"
                )
            elif metric == "early_out":
                title = str(_("Early departures"))
                early_ids = set(
                    AttendanceLateComeEarlyOut.objects.filter(
                        type="early_out",
                        attendance_id__attendance_date=today,
                        employee_id__in=emp_ids,
                    ).values_list("employee_id", flat=True)
                )
                rows = rows_for(early_ids, str(_("Early out")), "blue")
            elif metric == "pending":
                title = str(_("Pending attendance validation"))
                pending_ids = set(
                    Attendance.objects.filter(
                        employee_id__in=emp_ids,
                        is_validate_request=True,
                        is_validate_request_approved=False,
                    ).values_list("employee_id", flat=True)
                )
                rows = rows_for(pending_ids, str(_("Pending")), "amber")
                view_all = _safe_url("request-attendance-view") + (
                    "?open_tab=1&is_validate_request_approved=False&filter_applied=1"
                )
            elif metric == "ot_hours":
                title = str(_("Overtime this month"))
                ot_map = {
                    r.employee_id_id: round((r.overtime_second or 0) / 3600, 1)
                    for r in AttendanceOverTime.objects.filter(
                        employee_id__in=emp_ids,
                        month=today.strftime("%B").lower(),
                        year=str(today.year),
                    ).only("employee_id_id", "overtime_second")
                    if (r.overtime_second or 0) > 0
                }
                rows = rows_for(
                    ot_map.keys(),
                    str(_("OT")),
                    "indigo",
                    meta_fn=lambda e: f"{ot_map.get(e.id, 0)} h",
                )
            elif metric == "mtd_rate":
                title = str(_("Month-to-date attendance"))
                first = today.replace(day=1)
                present_ids = set(
                    Attendance.objects.filter(
                        employee_id__in=emp_ids,
                        attendance_date__gte=first,
                        attendance_date__lte=today,
                    ).values_list("employee_id", flat=True)
                )
                rows = rows_for(present_ids, str(_("Attended this month")), "green")
            elif metric == "late_mtd":
                title = str(_("Late arrivals this month"))
                first = today.replace(day=1)
                late_ids = set(
                    AttendanceLateComeEarlyOut.objects.filter(
                        type="late_come",
                        attendance_id__attendance_date__gte=first,
                        attendance_id__attendance_date__lte=today,
                        employee_id__in=emp_ids,
                    ).values_list("employee_id", flat=True)
                )
                rows = rows_for(late_ids, str(_("Late")), "amber")

        elif module == "leave" and apps.is_installed("leave"):
            from leave.models import LeaveRequest

            leave_base = LeaveRequest.objects.filter(employee_id__in=emp_ids)
            if metric == "on_leave":
                title = str(_("On leave today"))
                ids = set(
                    _scoped_today_leave_qs(
                        request, today, status="approved"
                    ).values_list("employee_id", flat=True)
                )
                rows = rows_for(ids, str(_("On leave")), "amber")
                view_all = (
                    _safe_url("request-view")
                    + "?status=approved&today_leave=true&filter_applied=on"
                )
            elif metric in ("upcoming_7d", "peak_7d"):
                end = today + timedelta(days=6)
                title = (
                    str(_("On leave next 7 days"))
                    if metric == "upcoming_7d"
                    else str(_("Peak coverage day (next 7 days)"))
                )
                ids = set(
                    _scoped_leave_overlap_qs(
                        request, today, end, status="approved"
                    ).values_list("employee_id", flat=True)
                )
                rows = rows_for(ids, str(_("Upcoming leave")), "amber")
                view_all = (
                    _safe_url("request-view")
                    + "?status=approved&filter_applied=on"
                )
            elif metric == "pending":
                title = str(_("Pending leave requests"))
                ids = set(
                    leave_base.filter(status="requested").values_list(
                        "employee_id", flat=True
                    )
                )
                rows = rows_for(ids, str(_("Pending")), "amber")
                view_all = (
                    _safe_url("request-view") + "?status=requested&filter_applied=1"
                )
            elif metric == "approved_month":
                title = str(_("Approved leave this month"))
                ids = set(
                    leave_base.filter(status="approved")
                    .filter(
                        Q(end_date__gte=first_of_month)
                        | Q(end_date__isnull=True, start_date__gte=first_of_month)
                    )
                    .filter(start_date__lte=last_of_month)
                    .values_list("employee_id", flat=True)
                )
                rows = rows_for(ids, str(_("Approved")), "green")
            elif metric == "rejected_month":
                title = str(_("Rejected / cancelled leave"))
                ids = set(
                    leave_base.filter(
                        status__in=["cancelled", "rejected"],
                        start_date__gte=first_of_month,
                        start_date__lte=last_of_month,
                    ).values_list("employee_id", flat=True)
                )
                rows = rows_for(ids, str(_("Rejected")), "red")

        elif module == "recruitment" and apps.is_installed("recruitment"):
            if scoped_ids is not None:
                return JsonResponse(
                    {
                        "title": str(_("Recruitment")),
                        "subtitle": str(_("Not available for team-scoped dashboards")),
                        "rows": [],
                        "view_all_url": "",
                    }
                )
            from recruitment.models import Candidate, Recruitment, Stage

            if metric == "open":
                title = str(_("Open recruitments"))
                for rec in Recruitment.objects.filter(
                    is_active=True, closed=False
                ).order_by("-id")[:40]:
                    rows.append(
                        {
                            "id": rec.id,
                            "name": str(rec),
                            "avatar": "",
                            "job": "",
                            "department": "",
                            "meta": "",
                            "badge": str(_("Open")),
                            "badge_tone": "blue",
                            "url": _safe_url("recruitment-pipeline"),
                        }
                    )
                view_all = _safe_url("recruitment-view")
            elif metric in ("candidates", "interviews", "hired_month"):
                qs = Candidate.objects.filter(is_active=True)
                if metric == "candidates":
                    title = str(_("Active candidates"))
                    qs = qs.filter(hired=False, canceled=False)
                    badge, tone = str(_("Candidate")), "indigo"
                elif metric == "interviews":
                    title = str(_("Candidates in interview"))
                    stages = Stage.objects.filter(
                        stage_type="interview", recruitment_id__closed=False
                    )
                    qs = qs.filter(stage_id__in=stages, canceled=False)
                    badge, tone = str(_("Interview")), "amber"
                else:
                    title = str(_("Hired this month"))
                    qs = Candidate.objects.filter(
                        hired=True,
                        hired_date__gte=first_of_month,
                        hired_date__lte=last_of_month,
                    )
                    badge, tone = str(_("Hired")), "green"
                for c in qs.select_related("stage_id", "recruitment_id").order_by(
                    "-id"
                )[:40]:
                    rows.append(
                        {
                            "id": c.id,
                            "name": c.get_full_name()
                            if hasattr(c, "get_full_name")
                            else str(c),
                            "avatar": getattr(c, "get_avatar", lambda: "")(),
                            "job": str(getattr(c, "job_position_id", "") or ""),
                            "department": str(
                                getattr(c, "recruitment_id", "") or ""
                            ),
                            "meta": str(getattr(c, "stage_id", "") or ""),
                            "badge": badge,
                            "badge_tone": tone,
                            "url": _safe_url("candidate-view"),
                        }
                    )
                view_all = _safe_url("candidate-view")

        elif module == "assets" and apps.is_installed("asset"):
            from asset.models import AssetAssignment, AssetRequest

            if metric == "assigned":
                title = str(_("Assets currently assigned"))
                for a in (
                    AssetAssignment.objects.filter(
                        assigned_to_employee_id__in=emp_ids,
                        return_date__isnull=True,
                    )
                    .select_related("assigned_to_employee_id", "asset_id")
                    .order_by("-id")[:40]
                ):
                    emp = a.assigned_to_employee_id
                    try:
                        profile = reverse(
                            "employee-view-individual", kwargs={"obj_id": emp.id}
                        )
                    except Exception:
                        profile = "#"
                    rows.append(
                        {
                            "id": a.id,
                            "name": emp.get_full_name(),
                            "avatar": emp.get_avatar(),
                            "job": str(emp.get_job_position() or ""),
                            "department": str(emp.get_department() or ""),
                            "meta": str(a.asset_id),
                            "badge": str(_("Assigned")),
                            "badge_tone": "blue",
                            "url": profile,
                        }
                    )
            elif metric == "requests":
                title = str(_("Pending asset requests"))
                ids = set(
                    AssetRequest.objects.filter(
                        requested_employee_id__in=emp_ids,
                        asset_request_status="Requested",
                    ).values_list("requested_employee_id", flat=True)
                )
                rows = rows_for(ids, str(_("Requested")), "amber")
                view_all = _safe_url("asset-request-allocation-view") + (
                    "?open_tab=2&asset_request_status=Requested&filter_applied=1"
                )
            elif metric == "returns":
                title = str(_("Asset return requests"))
                ids = set(
                    AssetAssignment.objects.filter(
                        assigned_to_employee_id__in=emp_ids,
                        return_request=True,
                        return_date__isnull=True,
                    ).values_list("assigned_to_employee_id", flat=True)
                )
                rows = rows_for(ids, str(_("Return")), "amber")

        elif module == "performance" and apps.is_installed("pms"):
            from pms.models import EmployeeObjective, Feedback

            if metric in ("active", "at_risk", "behind"):
                status_map = {
                    "active": None,
                    "at_risk": "At Risk",
                    "behind": "Behind",
                }
                title = {
                    "active": str(_("Active objectives")),
                    "at_risk": str(_("Objectives at risk")),
                    "behind": str(_("Objectives behind")),
                }[metric]
                qs = EmployeeObjective.objects.filter(
                    employee_id__in=emp_ids, archive=False
                )
                if status_map[metric]:
                    qs = qs.filter(status=status_map[metric])
                else:
                    qs = qs.exclude(status="Closed")
                tone = {"active": "blue", "at_risk": "red", "behind": "amber"}[metric]
                for obj in qs.select_related("employee_id").order_by("-id")[:40]:
                    emp = obj.employee_id
                    if not emp:
                        continue
                    try:
                        profile = reverse(
                            "employee-view-individual", kwargs={"obj_id": emp.id}
                        )
                    except Exception:
                        profile = "#"
                    rows.append(
                        {
                            "id": obj.id,
                            "name": emp.get_full_name(),
                            "avatar": emp.get_avatar(),
                            "job": str(emp.get_job_position() or ""),
                            "department": str(emp.get_department() or ""),
                            "meta": obj.objective or str(obj.objective_id or ""),
                            "badge": obj.status,
                            "badge_tone": tone,
                            "url": profile,
                        }
                    )
            elif metric == "feedback":
                title = str(_("Open feedback"))
                for fb in (
                    Feedback.objects.filter(employee_id__in=emp_ids)
                    .exclude(status="Closed")
                    .select_related("employee_id")
                    .order_by("-id")[:40]
                ):
                    emp = fb.employee_id
                    if not emp:
                        continue
                    try:
                        profile = reverse(
                            "employee-view-individual", kwargs={"obj_id": emp.id}
                        )
                    except Exception:
                        profile = "#"
                    rows.append(
                        {
                            "id": fb.id,
                            "name": emp.get_full_name(),
                            "avatar": emp.get_avatar(),
                            "job": str(emp.get_job_position() or ""),
                            "department": str(emp.get_department() or ""),
                            "meta": getattr(fb, "review_cycle", "") or "",
                            "badge": fb.status,
                            "badge_tone": "indigo",
                            "url": profile,
                        }
                    )

        elif module == "payroll" and apps.is_installed("payroll"):
            from payroll.models.models import Contract, LoanAccount, Payslip

            if metric == "payslips":
                title = str(_("Payslips this month"))
                qs = Payslip.objects.filter(
                    start_date__gte=first_of_month, start_date__lte=last_of_month
                )
                if scoped_ids is not None:
                    qs = qs.filter(employee_id__in=emp_ids)
                ids = set(qs.values_list("employee_id", flat=True))
                rows = rows_for(ids, str(_("Payslip")), "indigo")
            elif metric == "contracts":
                title = str(_("Active contracts"))
                ids = set(
                    Contract.objects.filter(
                        employee_id__in=emp_ids, contract_status="active"
                    ).values_list("employee_id", flat=True)
                )
                rows = rows_for(ids, str(_("Active")), "green")
            elif metric == "reimbursements":
                title = str(_("Pending reimbursements"))
                try:
                    from payroll.models.models import Reimbursement

                    qs = Reimbursement.objects.filter(status="requested")
                    if scoped_ids is not None:
                        qs = qs.filter(employee_id__in=emp_ids)
                    ids = set(qs.values_list("employee_id", flat=True))
                    rows = rows_for(ids, str(_("Requested")), "amber")
                    view_all = _safe_url("view-reimbursement") + (
                        "?open_tab=1&status=requested&type=reimbursement&filter_applied=1"
                    )
                except Exception:
                    rows = []
            elif metric == "loans":
                title = str(_("Active loans / advances"))
                ids = set(
                    LoanAccount.objects.filter(employee_id__in=emp_ids)
                    .exclude(settled=True)
                    .values_list("employee_id", flat=True)
                )
                rows = rows_for(ids, str(_("Loan")), "amber")

        elif module == "workforce":
            if metric in ("exits", "resignations") and apps.is_installed("offboarding"):
                from offboarding.models import OffboardingEmployee, ResignationLetter

                if metric == "exits":
                    title = str(_("Employees in offboarding"))
                    ids = set(
                        OffboardingEmployee.objects.filter(
                            employee_id__in=emp_ids
                        ).values_list("employee_id", flat=True)
                    )
                    rows = rows_for(ids, str(_("Offboarding")), "amber")
                else:
                    title = str(_("Resignation requests"))
                    ids = set(
                        ResignationLetter.objects.filter(
                            status="requested", employee_id__in=emp_ids
                        ).values_list("employee_id", flat=True)
                    )
                    rows = rows_for(ids, str(_("Requested")), "red")
            elif metric in ("tickets", "new_tickets") and apps.is_installed("helpdesk"):
                from helpdesk.models import Ticket

                title = (
                    str(_("New tickets"))
                    if metric == "new_tickets"
                    else str(_("Open tickets"))
                )
                tq = Ticket.objects.exclude(status__in=["resolved", "canceled"])
                if scoped_ids is not None:
                    tq = tq.filter(
                        Q(employee_id__in=emp_ids) | Q(assigned_to__in=emp_ids)
                    )
                if metric == "new_tickets":
                    tq = tq.filter(status="new")
                for t in tq.select_related("employee_id").order_by("-id")[:40]:
                    emp = t.employee_id
                    rows.append(
                        {
                            "id": t.id,
                            "name": emp.get_full_name() if emp else str(t),
                            "avatar": emp.get_avatar() if emp else "",
                            "job": str(emp.get_job_position() or "") if emp else "",
                            "department": str(emp.get_department() or "")
                            if emp
                            else "",
                            "meta": getattr(t, "title", "") or str(t),
                            "badge": t.get_status_display()
                            if hasattr(t, "get_status_display")
                            else t.status,
                            "badge_tone": "blue"
                            if t.status == "new"
                            else "amber",
                            "url": _safe_url("ticket-view")
                            if _safe_url("ticket-view") != "#"
                            else "#",
                        }
                    )
    except Exception as exc:
        return JsonResponse(
            {
                "title": title,
                "subtitle": str(exc),
                "rows": [],
                "view_all_url": "",
                "error": True,
            }
        )

    subtitle = (
        str(_("%(count)s records") % {"count": len(rows)})
        if rows
        else str(_("No records in scope"))
    )
    return JsonResponse(
        {
            "title": title,
            "subtitle": subtitle,
            "rows": rows,
            "view_all_url": view_all,
            "module": module,
            "metric": metric,
        }
    )


@login_required
@require_http_methods(["POST"])
def save_dashboard_prefs(request):
    """Persist dashboard customisation to DashboardEmployeeCharts model."""
    try:
        from base.models import DashboardEmployeeCharts

        data = json.loads(request.body)
        prefs = data.get("prefs", [])
        clean_prefs = _normalize_dashboard_chart_prefs(prefs)
        emp = request.user.employee_get
        DashboardEmployeeCharts.objects.update_or_create(
            employee=emp, defaults={"charts": clean_prefs}
        )
    except Exception:
        pass
    return JsonResponse({"status": "ok"})


@login_required
def load_dashboard_prefs(request):
    """Return saved dashboard preferences for the current employee."""
    try:
        from base.models import DashboardEmployeeCharts

        emp = request.user.employee_get
        obj = DashboardEmployeeCharts.objects.filter(employee=emp).first()
        prefs = _normalize_dashboard_chart_prefs(obj.charts if obj else [])
        return JsonResponse({"prefs": prefs})
    except Exception:
        return JsonResponse({"prefs": []})


@login_required
def dashboard_turnover(request):
    """Employee turnover — new hires vs exits over the last 6 months ending at selected period.

    Org-wide metric: requires employee view permission (not manager-only).
    Hidden for team-scoped managers so exits outside their tree never appear.
    """
    user = request.user
    if _is_team_scoped(request) or not (
        user.has_perm("employee.view_employee") or user.is_superuser
    ):
        return JsonResponse({"no_permission": True})

    _from_date, to_date = _parse_period(request)
    today = to_date
    months = []
    report_url = ""
    try:
        report_url = reverse("standard-report-detail", args=["turnover-attrition"])
    except Exception:
        report_url = ""

    try:
        from employee.models import Employee, EmployeeWorkInformation
        from report.engine import ReportFilters
        from report.metrics._exits import exits_in_period

        filters = ReportFilters(from_date=today.replace(day=1), to_date=today)

        for i in range(5, -1, -1):
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1
            month_start = today.replace(year=year, month=month, day=1)
            if month_start.month == 12:
                month_end = month_start.replace(
                    year=month_start.year + 1, month=1
                ) - timedelta(days=1)
            else:
                month_end = month_start.replace(
                    month=month_start.month + 1
                ) - timedelta(days=1)

            hires = EmployeeWorkInformation.objects.filter(
                date_joining__gte=month_start,
                date_joining__lte=month_end,
            ).count()
            exits = exits_in_period(filters, from_date=month_start, to_date=month_end)

            months.append(
                {
                    "month": month_start.strftime("%b %Y"),
                    "hires": hires,
                    "exits": exits,
                    "net": hires - exits,
                }
            )

        total_employees = Employee.objects.filter(is_active=True).count()
        total_exits_6m = sum(m["exits"] for m in months)
        turnover_rate = (
            round((total_exits_6m / total_employees * 100), 1)
            if total_employees > 0
            else 0
        )
    except Exception:
        months = [
            {"month": f"M{i+1}", "hires": 0, "exits": 0, "net": 0} for i in range(6)
        ]
        turnover_rate = 0

    return JsonResponse(
        {
            "months": months,
            "turnover_rate_6m": turnover_rate,
            "report_url": report_url,
            "subtitle": str(_("All exits — see Standard Report for detail")),
        }
    )


@login_required
def dashboard_leave_coverage(request):
    """Current-month leave coverage: headcount on approved leave per day + by dept.

    Managers without org-wide employee view see team-scoped counts.
    """
    today = date.today()
    first_of_month, last_of_month = _current_month_bounds()
    scoped_ids = _scoped_active_employee_ids(request)
    days = []
    by_department = []
    active_total = 0

    try:
        from django.db.models import Count

        from employee.models import Employee
        from leave.models import LeaveRequest

        emp_qs = Employee.objects.filter(is_active=True)
        if scoped_ids is not None:
            emp_qs = emp_qs.filter(id__in=scoped_ids)
        active_total = emp_qs.count()
        active_ids = set(emp_qs.values_list("id", flat=True))

        days_in_month = (last_of_month - first_of_month).days + 1
        for offset in range(days_in_month):
            day = first_of_month + timedelta(days=offset)
            leave_qs = LeaveRequest.objects.filter(
                start_date__lte=day,
                status="approved",
            ).filter(Q(end_date__gte=day) | Q(end_date__isnull=True, start_date=day))
            if scoped_ids is not None:
                leave_qs = leave_qs.filter(employee_id__in=scoped_ids)
            on_leave = leave_qs.values("employee_id").distinct().count()
            coverage_pct = (
                round(((active_total - on_leave) / active_total) * 100, 1)
                if active_total > 0
                else 100.0
            )
            days.append(
                {
                    "date": day.isoformat(),
                    "label": day.strftime("%a %d"),
                    "on_leave": on_leave,
                    "available": max(0, active_total - on_leave),
                    "coverage_pct": coverage_pct,
                    "is_today": day == today,
                }
            )

        # Current month: on-leave headcount by department (top 8) -- any
        # employee with an approved leave overlapping the month at all.
        month_leave_ids = set(
            LeaveRequest.objects.filter(
                start_date__lte=last_of_month,
                status="approved",
            )
            .filter(
                Q(end_date__gte=first_of_month)
                | Q(end_date__isnull=True, start_date__gte=first_of_month)
            )
            .values_list("employee_id", flat=True)
            .distinct()
        )
        if scoped_ids is not None:
            month_leave_ids &= active_ids

        if month_leave_ids:
            dept_rows = (
                Employee.objects.filter(id__in=month_leave_ids)
                .values("employee_work_info__department_id__department")
                .annotate(count=Count("id"))
                .order_by("-count")[:8]
            )
            for row in dept_rows:
                name = row["employee_work_info__department_id__department"] or str(
                    _("Unassigned")
                )
                by_department.append({"department": name, "on_leave": row["count"]})
    except Exception:
        days = []
        by_department = []

    return JsonResponse(
        {
            "days": days,
            "by_department": by_department,
            "active_employees": active_total,
            "is_team_scoped": scoped_ids is not None,
        }
    )


# ---------------------------------------------------------------------------
# Phase 5 — thin dashboard/api/* proxies for module chart JSON still used by
# templates/dashboard.html (keeps modern home off raw module URL names).
# ---------------------------------------------------------------------------


def _call_module_json(view_callable, request):
    """Invoke a module chart view; always return JsonResponse-compatible output."""
    try:
        return view_callable(request)
    except Exception as exc:
        return JsonResponse({"error": str(exc), "no_permission": True}, status=500)


def _force_get_params(request, **params):
    """Shallow-copy ``request`` with the given GET params forced in.

    These module chart views (attendance/leave) are shared with their own
    module dashboards, which rely on the view's own default period. Forcing
    params on a copy lets the main dashboard pin them to the current month
    without changing the view's default for those other callers.
    """
    import copy

    forced = copy.copy(request)
    get = request.GET.copy()
    for key, value in params.items():
        get[key] = value
    forced.GET = get
    return forced


@login_required
def dashboard_employee_status(request):
    """Active / inactive headcount within the dashboard reporting scope."""
    emp_qs, scoped_ids = _scoped_employee_queryset(request, active_only=False)
    active = emp_qs.filter(is_active=True).count()
    inactive = emp_qs.filter(is_active=False).count()
    return JsonResponse(
        {
            "dataSet": [
                {
                    "label": str(_("Employees")),
                    "data": [active, inactive],
                }
            ],
            "labels": [str(_("Active")), str(_("In-Active"))],
            "is_team_scoped": scoped_ids is not None,
        }
    )


@login_required
def dashboard_attendance_overview(request):
    """On-time / late / early-out by department for the dashboard scope.

    Managers see their nested reporting tree even without org-wide
    ``attendance.view_attendance``; HR/leadership see company-wide.
    Defaults to the current calendar month (same as the prior module proxy).
    """
    user = request.user
    if not (
        user.is_superuser
        or user.has_perm("attendance.view_attendance")
        or _is_manager(user)
    ):
        return JsonResponse({"no_permission": True})

    first_of_month, last_of_month = _current_month_bounds()
    scoped_ids = _scoped_active_employee_ids(request)
    labels = [
        str(_("On Time")),
        str(_("Late Arrival")),
        str(_("Early Departure")),
    ]
    data_set = []

    try:
        from attendance.models import Attendance, AttendanceLateComeEarlyOut
        from base.models import Department
        from employee.models import Employee

        emp_qs = Employee.objects.filter(is_active=True)
        if scoped_ids is not None:
            emp_qs = emp_qs.filter(id__in=scoped_ids)

        dept_ids = (
            emp_qs.exclude(employee_work_info__department_id__isnull=True)
            .values_list("employee_work_info__department_id", flat=True)
            .distinct()
        )
        for dept in Department.objects.filter(id__in=dept_ids).order_by("department"):
            dept_emp_ids = list(
                emp_qs.filter(employee_work_info__department_id=dept).values_list(
                    "id", flat=True
                )
            )
            if not dept_emp_ids:
                continue
            present = Attendance.objects.filter(
                attendance_date__gte=first_of_month,
                attendance_date__lte=last_of_month,
                employee_id__in=dept_emp_ids,
            ).count()
            late = AttendanceLateComeEarlyOut.objects.filter(
                type="late_come",
                attendance_id__attendance_date__gte=first_of_month,
                attendance_id__attendance_date__lte=last_of_month,
                employee_id__in=dept_emp_ids,
            ).count()
            early = AttendanceLateComeEarlyOut.objects.filter(
                type="early_out",
                attendance_id__attendance_date__gte=first_of_month,
                attendance_id__attendance_date__lte=last_of_month,
                employee_id__in=dept_emp_ids,
            ).count()
            on_time = max(0, present - late)
            if on_time or late or early:
                data_set.append(
                    {
                        "id": dept.pk,
                        "label": dept.department,
                        "data": [on_time, late, early],
                    }
                )
    except Exception:
        data_set = []

    return JsonResponse(
        {
            "dataSet": data_set,
            "labels": labels,
            "message": str(_("No records available at the moment.")),
            "is_team_scoped": scoped_ids is not None,
        }
    )


@login_required
def dashboard_department_overtime(request):
    """Validated overtime hours by department for the dashboard reporting scope."""
    user = request.user
    if not (
        user.is_superuser
        or user.has_perm("attendance.view_attendance")
        or _is_manager(user)
    ):
        return JsonResponse({"no_permission": True})

    first_of_month, last_of_month = _current_month_bounds()
    emp_qs, scoped_ids = _scoped_employee_queryset(request)
    emp_ids = list(emp_qs.values_list("id", flat=True))
    labels = []
    data = []
    department_total = []

    try:
        from attendance.models import Attendance, AttendanceValidationCondition
        from attendance.views.views import strtime_seconds

        min_ot = strtime_seconds("00:00")
        condition = AttendanceValidationCondition.objects.first()
        if condition is not None and condition.minimum_overtime_to_approve is not None:
            min_ot = strtime_seconds(condition.minimum_overtime_to_approve)

        attendances = Attendance.objects.filter(
            attendance_date__gte=first_of_month,
            attendance_date__lte=last_of_month,
            employee_id__in=emp_ids,
            overtime_second__gte=min_ot,
            attendance_validated=True,
            attendance_overtime_approve=True,
        ).select_related("employee_id__employee_work_info__department_id")

        totals = {}
        for att in attendances:
            wi = getattr(att.employee_id, "employee_work_info", None)
            dept = getattr(getattr(wi, "department_id", None), "department", None)
            if not dept:
                continue
            totals[dept] = totals.get(dept, 0.0) + (
                (att.approved_overtime_second or 0) / 3600.0
            )

        for dept, hours in sorted(totals.items(), key=lambda x: -x[1]):
            labels.append(dept)
            data.append(round(hours, 2))
            department_total.append({"department": dept, "ot_hours": round(hours, 2)})
    except Exception:
        labels, data, department_total = [], [], []

    return JsonResponse(
        {
            "dataset": [{"label": "", "data": data}],
            "labels": labels,
            "department_total": department_total,
            "message": str(_("No validated Overtimes were found")),
            "is_team_scoped": scoped_ids is not None,
        }
    )


@login_required
def dashboard_leave_trends(request):
    """Approved leave headcount by day for the current month (reporting scope)."""
    user = request.user
    if not (
        user.is_superuser
        or user.has_perm("leave.view_leaverequest")
        or _is_manager(user)
    ):
        return JsonResponse({"no_permission": True})

    first_of_month, last_of_month = _current_month_bounds()
    scoped_ids = _scoped_active_employee_ids(request)
    labels = []
    data = []

    try:
        from leave.models import LeaveRequest

        leave_qs = LeaveRequest.objects.filter(
            status="approved",
            start_date__lte=last_of_month,
        ).filter(
            Q(end_date__gte=first_of_month)
            | Q(end_date__isnull=True, start_date__gte=first_of_month)
        )
        if scoped_ids is not None:
            leave_qs = leave_qs.filter(employee_id__in=scoped_ids)

        day = first_of_month
        while day <= last_of_month:
            labels.append(day.strftime("%d-%m-%Y"))
            on_leave = (
                leave_qs.filter(start_date__lte=day)
                .filter(Q(end_date__gte=day) | Q(end_date__isnull=True, start_date=day))
                .values("employee_id")
                .distinct()
                .count()
            )
            data.append(on_leave)
            day += timedelta(days=1)
    except Exception:
        labels, data = [], []

    return JsonResponse(
        {
            "labels": labels,
            "data": data,
            "is_team_scoped": scoped_ids is not None,
        }
    )


@login_required
def dashboard_leave_by_department(request):
    """Leave request counts by department for the current month (reporting scope)."""
    user = request.user
    if not (
        user.is_superuser
        or user.has_perm("leave.view_leaverequest")
        or _is_manager(user)
    ):
        return JsonResponse({"no_permission": True})

    first_of_month, last_of_month = _current_month_bounds()
    emp_qs, scoped_ids = _scoped_employee_queryset(request)
    labels = []
    data = []

    try:
        from leave.models import LeaveRequest

        leave_qs = LeaveRequest.objects.filter(
            start_date__gte=first_of_month,
            start_date__lte=last_of_month,
            employee_id__in=emp_qs,
        )
        rows = (
            leave_qs.values("employee_id__employee_work_info__department_id__department")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        for row in rows:
            dept = row["employee_id__employee_work_info__department_id__department"]
            if dept and row["count"]:
                labels.append(dept)
                data.append(row["count"])
    except Exception:
        labels, data = [], []

    return JsonResponse(
        {
            "labels": labels,
            "data": data,
            "is_team_scoped": scoped_ids is not None,
        }
    )


@login_required
def dashboard_department_leave_days(request):
    """Approved leave days by department for the current month (reporting scope)."""
    user = request.user
    if not (
        user.is_superuser
        or user.has_perm("leave.view_leaverequest")
        or _is_manager(user)
    ):
        return JsonResponse({"no_permission": True})

    first_of_month, last_of_month = _current_month_bounds()
    emp_qs, scoped_ids = _scoped_employee_queryset(request)
    labels = []
    values = []

    try:
        from django.db.models import Sum

        from leave.models import LeaveRequest

        leave_qs = LeaveRequest.objects.filter(
            status="approved",
            start_date__month=first_of_month.month,
            start_date__year=first_of_month.year,
            employee_id__in=emp_qs,
        )
        rows = (
            leave_qs.values("employee_id__employee_work_info__department_id__department")
            .annotate(days=Sum("requested_days"))
            .order_by("-days")
        )
        for row in rows:
            dept = row["employee_id__employee_work_info__department_id__department"]
            days = float(row["days"] or 0)
            if dept and days:
                labels.append(dept)
                values.append(days)
    except Exception:
        labels, values = [], []

    return JsonResponse(
        {
            "labels": labels,
            "dataset": [{"label": str(_("Leave days")), "data": values}],
            "is_team_scoped": scoped_ids is not None,
        }
    )


@login_required
def dashboard_hiring_timeline(request):
    """Hiring timeline is org-wide; hide for team-scoped manager homes."""
    if _is_team_scoped(request):
        return JsonResponse({"no_permission": True})
    from recruitment.views.dashboard import dashboard_hiring

    return _call_module_json(dashboard_hiring, request)


@login_required
def dashboard_recruitment_by_stage(request):
    """Stacked-by-recruitment pipeline chart (legacy recruitment-pipeline JSON)."""
    if _is_team_scoped(request):
        return JsonResponse({"no_permission": True})
    from recruitment.views.dashboard import dashboard_pipeline

    return _call_module_json(dashboard_pipeline, request)
