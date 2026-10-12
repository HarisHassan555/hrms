"""
Modern helpdesk dashboard views — KPI summary + ApexCharts.

Accessible at /helpdesk/dashboard/modern/ alongside the existing pipeline view.
"""

import calendar
from datetime import date, timedelta

from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from horilla.decorators import login_required, permission_required


def _parse_period(request):
    """Return the current calendar month's bounds (first day to last day).

    The dashboard always shows the current month; GET params are ignored,
    so the range rolls forward on its own when the month changes.
    """
    today = timezone.now().date()
    from_date = today.replace(day=1)
    to_date = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    return from_date, to_date


@login_required
@permission_required("helpdesk.view_ticket")
def helpdesk_dashboard_view(request):
    """Render the modern helpdesk dashboard page."""
    return render(request, "helpdesk/dashboard.html")


def _period_tickets(request):
    """Active tickets created in the current calendar month."""
    from helpdesk.models import Ticket

    from_date, to_date = _parse_period(request)
    return Ticket.objects.filter(
        is_active=True,
        created_date__gte=from_date,
        created_date__lte=to_date,
    )


def _resolved_this_month(request):
    """Active tickets resolved in the current calendar month (by resolved_date).

    Kept separate from `_period_tickets` (scoped by created_date) -- "resolved
    this month" is about when a ticket was actually resolved, not when it
    happened to be created.
    """
    from helpdesk.models import Ticket

    from_date, to_date = _parse_period(request)
    return Ticket.objects.filter(
        is_active=True,
        status="resolved",
        resolved_date__gte=from_date,
        resolved_date__lte=to_date,
    )


@login_required
@permission_required("helpdesk.view_ticket")
def helpdesk_kpi_data(request):
    """Return helpdesk KPI summary data as JSON, scoped to the current month.

    Ticket-volume/status KPIs reflect tickets created this month
    (created_date). Resolution KPIs reflect tickets resolved this month
    (resolved_date) -- not the created-this-month cohort's current status,
    which would conflate "created this month" with "resolved this month".
    Overdue and pending-claims are live, current-state counts, independent
    of month, same reasoning as the asset dashboard's "expiring soon" /
    "return requests" tiles (there's no "became overdue on" or "claim
    raised on" date field to scope them by).
    """
    from helpdesk.models import ClaimRequest

    from_date, to_date = _parse_period(request)
    period_tickets = _period_tickets(request)
    resolved_this_month = _resolved_this_month(request)

    total_tickets = period_tickets.count()
    new_tickets = period_tickets.filter(status="new").count()
    in_progress = period_tickets.filter(status="in_progress").count()
    on_hold = period_tickets.filter(status="on_hold").count()
    canceled = period_tickets.filter(status="canceled").count()
    open_tickets = period_tickets.filter(
        status__in=["new", "in_progress", "on_hold"]
    ).count()

    period_resolved = resolved_this_month.count()
    resolution_rate = (
        round((period_resolved / total_tickets * 100), 1) if total_tickets > 0 else 0
    )

    # Overdue -- live, current-state count (past deadline as of today); a
    # ticket created last month is just as overdue today as one created
    # this month, so this intentionally ignores the month bounds above.
    overdue = _overdue_count()

    # Pending claims -- live, current-state count.
    pending_claims = ClaimRequest.objects.filter(
        is_approved=False,
        is_rejected=False,
    ).count()

    # Avg resolution time (days between created_date and resolved_date) for
    # tickets resolved this month.
    avg_resolution = None
    avg_resolution_count = 0
    try:
        total_days = 0
        count = 0
        for t in resolved_this_month.filter(created_date__isnull=False):
            delta = (t.resolved_date - t.created_date).days
            if delta >= 0:
                total_days += delta
                count += 1
        avg_resolution = round(total_days / count, 1) if count > 0 else None
        avg_resolution_count = count
    except Exception:
        pass

    return JsonResponse(
        {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "new_tickets": new_tickets,
            "in_progress": in_progress,
            "on_hold": on_hold,
            "resolved": period_resolved,
            "canceled": canceled,
            "resolution_rate": resolution_rate,
            "period_resolved": period_resolved,
            "overdue": overdue,
            "pending_claims": pending_claims,
            "avg_resolution_days": avg_resolution,
            "avg_resolution_count": avg_resolution_count,
            "period_from_date": from_date.isoformat(),
            "period_to_date": to_date.isoformat(),
        }
    )


def _overdue_count():
    """Tickets currently past their deadline and still open -- a live count."""
    from helpdesk.models import Ticket

    today = date.today()
    return Ticket.objects.filter(
        is_active=True,
        deadline__lt=today,
        status__in=["new", "in_progress", "on_hold"],
    ).count()


@login_required
@permission_required("helpdesk.view_ticket")
def helpdesk_status_distribution(request):
    """Ticket count by current status, for tickets created this month."""
    from_date, to_date = _parse_period(request)
    statuses = []
    status_choices = [
        ("new", _("New")),
        ("in_progress", _("In Progress")),
        ("on_hold", _("On Hold")),
        ("resolved", _("Resolved")),
        ("canceled", _("Canceled")),
    ]
    qs = _period_tickets(request)

    for status, label in status_choices:
        count = qs.filter(status=status).count()
        statuses.append({"status": status, "label": label, "count": count})

    return JsonResponse(
        {
            "statuses": statuses,
            "period_from_date": from_date.isoformat(),
            "period_to_date": to_date.isoformat(),
        }
    )


@login_required
@permission_required("helpdesk.view_ticket")
def helpdesk_priority_distribution(request):
    """Ticket count by priority, for tickets created this month."""
    from_date, to_date = _parse_period(request)
    priorities = []
    priority_choices = [
        ("low", _("Low")),
        ("medium", _("Medium")),
        ("high", _("High")),
    ]
    qs = _period_tickets(request)

    for priority, label in priority_choices:
        count = qs.filter(priority=priority).count()
        priorities.append({"priority": priority, "label": label, "count": count})

    return JsonResponse(
        {
            "priorities": priorities,
            "period_from_date": from_date.isoformat(),
            "period_to_date": to_date.isoformat(),
        }
    )


@login_required
@permission_required("helpdesk.view_ticket")
def helpdesk_type_distribution(request):
    """Ticket count by type, for tickets created this month."""
    from_date, to_date = _parse_period(request)
    types = []

    try:
        data = (
            _period_tickets(request)
            .values("ticket_type__id", "ticket_type__title", "ticket_type__type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            title = item["ticket_type__title"]
            if title:
                types.append(
                    {
                        "id": item["ticket_type__id"],
                        "type": title,
                        "category": item["ticket_type__type"] or "",
                        "count": item["count"],
                    }
                )
    except Exception:
        pass

    return JsonResponse(
        {
            "types": types,
            "period_from_date": from_date.isoformat(),
            "period_to_date": to_date.isoformat(),
        }
    )


@login_required
@permission_required("helpdesk.view_ticket")
def helpdesk_monthly_trend(request):
    """Weekly-bucketed created-vs-resolved trend for the current calendar month.

    Bucketed by week (rather than by month) because the dashboard is always
    pinned to a single calendar month -- a month-by-month trend would
    collapse to one bar. Mirrors the same weekly-bucket approach used by
    the main dashboard's attendance trend once it was pinned to the
    current month.
    """
    from helpdesk.models import Ticket

    from_date, to_date = _parse_period(request)
    today = date.today()
    weeks = []

    bucket_start = from_date - timedelta(days=from_date.weekday())
    last_monday = to_date - timedelta(days=to_date.weekday())
    cursor = bucket_start
    while cursor <= last_monday:
        week_end = min(cursor + timedelta(days=6), to_date)
        week_start = max(cursor, from_date)

        created = Ticket.objects.filter(
            is_active=True,
            created_date__gte=week_start,
            created_date__lte=week_end,
        ).count()

        resolved_count = Ticket.objects.filter(
            is_active=True,
            status="resolved",
            resolved_date__gte=week_start,
            resolved_date__lte=week_end,
        ).count()

        is_current = cursor <= today <= cursor + timedelta(days=6)
        label = week_start.strftime("%b %d") + (" (now)" if is_current else "")
        weeks.append(
            {
                "week": label,
                "from_date": week_start.isoformat(),
                "to_date": week_end.isoformat(),
                "created": created,
                "resolved": resolved_count,
            }
        )
        cursor += timedelta(weeks=1)

    return JsonResponse({"weeks": weeks})


@login_required
@permission_required("helpdesk.view_ticket")
def helpdesk_department_breakdown(request):
    """Tickets by department (via employee owner), for tickets created this month."""
    from_date, to_date = _parse_period(request)
    departments = []

    try:
        data = (
            _period_tickets(request)
            .values(
                "employee_id__employee_work_info__department_id",
                "employee_id__employee_work_info__department_id__department",
            )
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            dept = item["employee_id__employee_work_info__department_id__department"]
            dept_id = item["employee_id__employee_work_info__department_id"]
            if dept:
                departments.append(
                    {"id": dept_id, "department": dept, "count": item["count"]}
                )
    except Exception:
        pass

    return JsonResponse(
        {
            "departments": departments,
            "period_from_date": from_date.isoformat(),
            "period_to_date": to_date.isoformat(),
        }
    )


@login_required
@permission_required("helpdesk.view_ticket")
def helpdesk_overdue_tickets(request):
    """Tickets created this month whose deadline has already passed."""
    _from, to_date = _parse_period(request)
    today = date.today()
    cutoff = min(today, to_date)
    tickets = []

    try:
        qs = (
            _period_tickets(request)
            .filter(
                deadline__lt=cutoff,
                status__in=["new", "in_progress", "on_hold"],
            )
            .select_related("employee_id", "ticket_type")
            .order_by("deadline")[:15]
        )

        for t in qs:
            emp = t.employee_id
            days_overdue = (today - t.deadline).days if t.deadline else 0
            tickets.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "ticket_id": (
                        f"{t.ticket_type.prefix}-{t.id}" if t.ticket_type else str(t.id)
                    ),
                    "employee_id": emp.id if emp else None,
                    "employee": emp.get_full_name() if emp else "—",
                    "avatar": emp.get_avatar() if emp else None,
                    "priority": t.priority,
                    "status": t.status,
                    "days_overdue": days_overdue,
                    "deadline": t.deadline.strftime("%b %d") if t.deadline else "—",
                }
            )
    except Exception:
        pass

    return JsonResponse({"tickets": tickets})


@login_required
@permission_required("helpdesk.view_ticket")
def helpdesk_recent_tickets(request):
    """Most recently created tickets within the current month."""
    tickets = []

    try:
        qs = (
            _period_tickets(request)
            .select_related("employee_id", "ticket_type")
            .order_by("-created_date", "-id")[:10]
        )

        for t in qs:
            emp = t.employee_id
            tickets.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "ticket_id": (
                        f"{t.ticket_type.prefix}-{t.id}" if t.ticket_type else str(t.id)
                    ),
                    "employee_id": emp.id if emp else None,
                    "employee": emp.get_full_name() if emp else "—",
                    "avatar": emp.get_avatar() if emp else None,
                    "priority": t.priority,
                    "status": t.status,
                    "type": t.ticket_type.title if t.ticket_type else "—",
                    "date": t.created_date.strftime("%b %d") if t.created_date else "—",
                }
            )
    except Exception:
        pass

    return JsonResponse({"tickets": tickets})


@login_required
@permission_required("helpdesk.view_ticket")
def helpdesk_sla_compliance(request):
    """SLA compliance -- tickets resolved this month, on time vs late."""
    from_date, to_date = _parse_period(request)
    resolved_on_time = 0
    resolved_late = 0

    try:
        resolved_with_deadline = _resolved_this_month(request).filter(
            deadline__isnull=False,
        )

        for t in resolved_with_deadline:
            if t.resolved_date <= t.deadline:
                resolved_on_time += 1
            else:
                resolved_late += 1
    except Exception:
        pass

    open_overdue = _overdue_count()

    total_with_deadline = resolved_on_time + resolved_late
    compliance_rate = (
        round((resolved_on_time / total_with_deadline * 100), 1)
        if total_with_deadline > 0
        else 0
    )

    return JsonResponse(
        {
            "compliance_rate": compliance_rate,
            "resolved_on_time": resolved_on_time,
            "resolved_late": resolved_late,
            "open_overdue": open_overdue,
            "total_with_deadline": total_with_deadline,
            "period_from_date": from_date.isoformat(),
            "period_to_date": to_date.isoformat(),
        }
    )


@login_required
@permission_required("helpdesk.view_ticket")
def helpdesk_assignee_workload(request):
    """Open ticket count per assignee, restricted to tickets created this month."""
    from_date, to_date = _parse_period(request)
    assignees = []

    try:
        open_tickets = _period_tickets(request).filter(
            status__in=["new", "in_progress", "on_hold"],
        )

        workload = {}
        for t in open_tickets:
            for emp in t.assigned_to.all():
                if emp.id not in workload:
                    workload[emp.id] = {
                        "id": emp.id,
                        "name": emp.get_full_name(),
                        "avatar": emp.get_avatar(),
                        "count": 0,
                        "high": 0,
                    }
                workload[emp.id]["count"] += 1
                if t.priority == "high":
                    workload[emp.id]["high"] += 1

        assignees = sorted(workload.values(), key=lambda x: x["count"], reverse=True)[
            :10
        ]
    except Exception:
        pass

    return JsonResponse(
        {
            "assignees": assignees,
            "period_from_date": from_date.isoformat(),
            "period_to_date": to_date.isoformat(),
        }
    )
