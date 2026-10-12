from __future__ import annotations

from datetime import timedelta

from django.apps import apps
from django.utils import timezone

from base.models import (
    CompanyLeaves,
    Department,
    EmployeeType,
    Holidays,
    JobPosition,
    WorkType,
)
from employee.models import Employee, EmployeeWorkInformation
from leave.models import (
    AvailableLeave,
    EmployeePastLeaveRestrict,
    LeaveAllocationRequest,
    LeaveGeneralSetting,
    LeaveRequest,
    LeaveType,
    RestrictLeave,
)

from .organization_seeder import get_seed_companies
from .utils import SeederResult, record, set_m2m, upsert


WEEKLY_OFF_DAYS = [
    {"based_on_week": None, "based_on_week_day": "5"},
    {"based_on_week": None, "based_on_week_day": "6"},
]

LEAVE_TYPES = [
    {
        "name": "Casual Leave",
        "payment": "paid",
        "payment_type": "paid",
        "count": 1,
        "total_days": 12,
        "limit_leave": True,
        "reset": True,
        "reset_based": "yearly",
        "reset_month": "1",
        "reset_day": "1",
    },
    {
        "name": "Sick Leave",
        "payment": "paid",
        "payment_type": "paid",
        "count": 1,
        "total_days": 10,
        "limit_leave": True,
        "reset": True,
        "reset_based": "yearly",
        "reset_month": "1",
        "reset_day": "1",
        "require_attachment": "yes",
    },
    {
        "name": "Unpaid Leave",
        "payment": "unpaid",
        "payment_type": "unpaid",
        "count": 1,
        "total_days": 1,
        "limit_leave": False,
        "reset": False,
    },
    {
        "name": "Compensatory Leave Type",
        "payment": "paid",
        "payment_type": "paid",
        "count": 1,
        "total_days": 0,
        "limit_leave": False,
        "reset": False,
        "is_compensatory_leave": True,
    },
]


def seed() -> SeederResult:
    result = SeederResult()
    companies = get_seed_companies()

    for item in WEEKLY_OFF_DAYS:
        weekly_off, status = upsert(CompanyLeaves, item)
        m2m_status = set_m2m(weekly_off, "company_id", companies)
        if status == "existing" and m2m_status == "updated":
            status = "updated"
        record(result, status, "Weekly Off Day", weekly_off)

    for company in companies:
        for item in LEAVE_TYPES:
            lookup = {"name": item["name"], "company_id": company}
            defaults = {
                "payment": item.get("payment", "unpaid"),
                "payment_type": item.get("payment_type"),
                "count": item.get("count", 1),
                "period_in": item.get("period_in", "day"),
                "limit_leave": item.get("limit_leave", True),
                "total_days": item.get("total_days", 1),
                "reset": item.get("reset", False),
                "reset_based": item.get("reset_based"),
                "reset_month": item.get("reset_month", ""),
                "reset_day": item.get("reset_day"),
                "carryforward_type": item.get("carryforward_type", "no carryforward"),
                "require_approval": item.get("require_approval", "yes"),
                "require_attachment": item.get("require_attachment", "no"),
                "exclude_company_leave": item.get("exclude_company_leave", "no"),
                "exclude_holiday": item.get("exclude_holiday", "no"),
                "is_compensatory_leave": item.get("is_compensatory_leave", False),
            }
            leave_type, status = upsert(LeaveType, lookup, defaults)
            record(result, status, "Leave Type", leave_type)

        leave_setting, status = upsert(
            LeaveGeneralSetting,
            {"company_id": company},
            {"compensatory_leave": True},
        )
        record(result, status, "Leave General Setting", leave_setting)

        past_leave, status = upsert(
            EmployeePastLeaveRestrict,
            {"company_id": company},
            {"enabled": True},
        )
        record(result, status, "Employee Past Leave Restrict", past_leave)

    seed_sample_leave_flow(result, companies)

    return result


def _primary_employee():
    return Employee.objects.filter(is_active=True).order_by("pk").first()


def _resolve_work_info(employee, companies):
    existing_company_id = (
        EmployeeWorkInformation.objects.filter(employee_id=employee)
        .values_list("company_id", flat=True)
        .first()
    )
    company = next((item for item in companies if item.pk == existing_company_id), None)
    if company is None:
        company = companies[0] if companies else None

    department = Department.objects.filter(company_id=company).order_by("pk").first()
    job_position = (
        JobPosition.objects.filter(department_id=department).order_by("pk").first()
        if department
        else None
    )
    work_type = WorkType.objects.filter(company_id=company).order_by("pk").first()
    employee_type = EmployeeType.objects.filter(company_id=company).order_by("pk").first()

    work_info, _created = EmployeeWorkInformation.objects.get_or_create(
        employee_id=employee
    )
    updates = {
        "company_id": company,
        "department_id": department,
        "job_position_id": job_position,
        "work_type_id": work_type,
        "employee_type_id": employee_type,
    }
    changed = False
    for field_name, value in updates.items():
        if value is not None and getattr(work_info, field_name) != value:
            setattr(work_info, field_name, value)
            changed = True
    if changed:
        work_info.save()

    return work_info


def _leave_type(company, name):
    return LeaveType.objects.filter(company_id=company, name=name).order_by("pk").first()


def seed_sample_leave_flow(result: SeederResult, companies) -> None:
    employee = _primary_employee()
    if employee is None:
        result.add("existing", "Leave sample skipped - no active employee found")
        return

    work_info = _resolve_work_info(employee, companies)
    company = work_info.company_id or (companies[0] if companies else None)
    if company is None:
        result.add("existing", "Leave sample skipped - no company found")
        return

    today = timezone.localdate()
    casual_leave = _leave_type(company, "Casual Leave")
    sick_leave = _leave_type(company, "Sick Leave")
    unpaid_leave = _leave_type(company, "Unpaid Leave")
    compensatory_leave = _leave_type(company, "Compensatory Leave Type")
    leave_types = [item for item in [casual_leave, sick_leave, unpaid_leave] if item]

    for leave_type in leave_types:
        available_days = 12 if leave_type == casual_leave else 10
        carryforward_days = 1 if leave_type == casual_leave else 0
        if leave_type == unpaid_leave:
            available_days = 3
            carryforward_days = 0
        available_leave, status = upsert(
            AvailableLeave,
            {"employee_id": employee, "leave_type_id": leave_type},
            {
                "available_days": available_days,
                "carryforward_days": carryforward_days,
                "total_leave_days": available_days + carryforward_days,
                "assigned_date": today.replace(month=1, day=1),
                "reset_date": today.replace(year=today.year + 1, month=1, day=1),
            },
        )
        record(result, status, "Available Leave", available_leave)

    if compensatory_leave:
        available_leave, status = upsert(
            AvailableLeave,
            {"employee_id": employee, "leave_type_id": compensatory_leave},
            {
                "available_days": 1,
                "carryforward_days": 0,
                "total_leave_days": 1,
                "assigned_date": today,
                "reset_date": None,
            },
        )
        record(result, status, "Available Leave", available_leave)

    if casual_leave:
        leave_samples = [
            {
                "start_date": today,
                "end_date": today,
                "status": "approved",
                "description": "Seeded approved leave for dashboard on-leave view.",
            },
            {
                "start_date": today + timedelta(days=1),
                "end_date": today + timedelta(days=1),
                "status": "requested",
                "description": "Seeded pending leave request for approval workflow.",
            },
            {
                "start_date": today + timedelta(days=5),
                "end_date": today + timedelta(days=5),
                "status": "rejected",
                "description": "Seeded rejected leave request for status filters.",
                "reject_reason": "Seeded request kept rejected for demo filters.",
            },
        ]

        for sample in leave_samples:
            leave_request, status = upsert(
                LeaveRequest,
                {
                    "employee_id": employee,
                    "leave_type_id": casual_leave,
                    "start_date": sample["start_date"],
                },
                {
                    "end_date": sample["end_date"],
                    "start_date_breakdown": "full_day",
                    "end_date_breakdown": "full_day",
                    "description": sample["description"],
                    "status": sample["status"],
                    "requested_date": today,
                    "created_by": employee,
                    "reject_reason": sample.get("reject_reason", ""),
                },
            )
            record(result, status, "Leave Request", leave_request)

    allocation_type = sick_leave or casual_leave
    if allocation_type:
        for status_name, requested_days in [("requested", 2), ("approved", 1)]:
            allocation, status = upsert(
                LeaveAllocationRequest,
                {
                    "employee_id": employee,
                    "leave_type_id": allocation_type,
                    "status": status_name,
                },
                {
                    "requested_days": requested_days,
                    "requested_date": today,
                    "description": f"Seeded {status_name} leave allocation request.",
                    "reject_reason": "",
                },
            )
            record(result, status, "Leave Allocation Request", allocation)

    for offset, name in [(10, "Seeded Public Holiday"), (40, "Seeded Optional Holiday")]:
        holiday, status = upsert(
            Holidays,
            {"name": name, "company_id": company},
            {
                "start_date": today + timedelta(days=offset),
                "end_date": today + timedelta(days=offset),
                "recurring": False,
                "is_specific": False,
                "assigning_type": None,
            },
        )
        record(result, status, "Public Holiday", holiday)

    department = work_info.department_id
    if department and casual_leave:
        restricted_leave, status = upsert(
            RestrictLeave,
            {"title": "Seeded Year-End Leave Freeze", "company_id": company},
            {
                "start_date": today + timedelta(days=20),
                "end_date": today + timedelta(days=25),
                "department": department,
                "include_all": False,
                "description": "Seeded restricted leave period for demo filters.",
            },
        )
        m2m_status = set_m2m(restricted_leave, "spesific_leave_types", [casual_leave])
        if status == "existing" and m2m_status == "updated":
            status = "updated"
        record(result, status, "Restricted Leave Period", restricted_leave)

    if apps.is_installed("attendance") and compensatory_leave:
        _seed_compensatory_leave(result, employee, today)


def _seed_compensatory_leave(result: SeederResult, employee, today) -> None:
    from attendance.models import Attendance
    from leave.models import CompensatoryLeaveRequest

    attendance = (
        Attendance.objects.filter(employee_id=employee)
        .order_by("-attendance_date", "-pk")
        .first()
    )
    if attendance is None:
        result.add(
            "existing",
            "Compensatory leave sample skipped - no attendance record found",
        )
        return

    request, status = upsert(
        CompensatoryLeaveRequest,
        {
            "employee_id": employee,
            "requested_date": today,
            "status": "requested",
        },
        {
            "leave_type_id": LeaveType.objects.filter(
                is_compensatory_leave=True
            ).first(),
            "requested_days": 1,
            "description": "Seeded compensatory leave request from attendance overtime.",
            "reject_reason": "",
        },
    )
    m2m_status = set_m2m(request, "attendance_id", [attendance])
    if status == "existing" and m2m_status == "updated":
        status = "updated"
    record(result, status, "Compensatory Leave Request", request)
