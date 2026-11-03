"""
Rich attendance and leave demo data for DSG Pakistan companies.

Builds on pakistan_org / pakistan_profiles (employees, shifts, leave types).
Idempotent — safe to re-run.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from base.models import Company, EmployeeShift, EmployeeShiftDay
from employee.models import Employee, EmployeeWorkInformation
from leave.models import (
    AvailableLeave,
    LeaveAllocationRequest,
    LeaveRequest,
    LeaveType,
)

from .utils import SeederResult, record, set_m2m, upsert

DSG_COMPANY_NAMES = ("DSG Technologies", "DSG Business Solutions")
EMAIL_DOMAIN = "dsg.pk"

WORKING_DAYS_TARGET = 30
ATTENDANCE_LOOKBACK_CALENDAR_DAYS = 75

LEAVE_TYPE_NAMES = ("Annual Leave", "Casual Leave", "Sick Leave")

LEAVE_REQUEST_SPECS = (
    {
        "email": f"ali.raza@{EMAIL_DOMAIN}",
        "leave_type": "Casual Leave",
        "start_offset": -5,
        "end_offset": -5,
        "status": "approved",
        "description": "Personal errand — approved casual day.",
    },
    {
        "email": f"fatima.noor@{EMAIL_DOMAIN}",
        "leave_type": "Sick Leave",
        "start_offset": -2,
        "end_offset": -1,
        "status": "approved",
        "description": "Flu — medical rest (2 days).",
    },
    {
        "email": f"sana.iqbal@{EMAIL_DOMAIN}",
        "leave_type": "Annual Leave",
        "start_offset": 10,
        "end_offset": 12,
        "status": "requested",
        "description": "Family wedding travel — pending manager approval.",
    },
    {
        "email": f"zain.abbas@{EMAIL_DOMAIN}",
        "leave_type": "Annual Leave",
        "start_offset": 14,
        "end_offset": 16,
        "status": "approved",
        "description": "Planned annual leave — engineering offsite week.",
    },
    {
        "email": f"rehan.malik@{EMAIL_DOMAIN}",
        "leave_type": "Casual Leave",
        "start_offset": 3,
        "end_offset": 3,
        "status": "requested",
        "description": "Vehicle registration — half-day request (full day demo).",
    },
    {
        "email": f"farah.aziz@{EMAIL_DOMAIN}",
        "leave_type": "Casual Leave",
        "start_offset": 8,
        "end_offset": 8,
        "status": "rejected",
        "description": "Peak release window — kept rejected for demo filters.",
        "reject_reason": "Critical QA milestone — please reschedule.",
    },
    {
        "email": f"hamza.sheikh@{EMAIL_DOMAIN}",
        "leave_type": "Sick Leave",
        "start_offset": -7,
        "end_offset": -7,
        "status": "approved",
        "description": "Doctor appointment — sick leave.",
    },
    {
        "email": f"bilal.hassan@{EMAIL_DOMAIN}",
        "leave_type": "Annual Leave",
        "start_offset": 20,
        "end_offset": 24,
        "status": "requested",
        "description": "Year-end family visit Lahore → Karachi.",
    },
    {
        "email": f"ayesha.kamal@{EMAIL_DOMAIN}",
        "leave_type": "Casual Leave",
        "start_offset": 0,
        "end_offset": 0,
        "status": "approved",
        "description": "On leave today — dashboard on-leave widget.",
    },
    {
        "email": f"usman.ali@{EMAIL_DOMAIN}",
        "leave_type": "Sick Leave",
        "start_offset": 5,
        "end_offset": 5,
        "status": "requested",
        "description": "Dental procedure — pending HR.",
    },
    {
        "email": f"maham.javed@{EMAIL_DOMAIN}",
        "leave_type": "Annual Leave",
        "start_offset": -14,
        "end_offset": -12,
        "status": "approved",
        "description": "Past approved annual block for history reports.",
    },
    {
        "email": f"saad.farooq@{EMAIL_DOMAIN}",
        "leave_type": "Casual Leave",
        "start_offset": 6,
        "end_offset": 6,
        "status": "requested",
        "description": "School parent meeting.",
    },
)


def _dsg_companies() -> list[Company]:
    return list(Company.objects.filter(company__in=DSG_COMPANY_NAMES).order_by("pk"))


def _employee_by_email(email: str) -> Employee | None:
    return (
        Employee.objects.filter(email=email, is_active=True)
        .order_by("pk")
        .first()
    )


def _employees_in_companies(companies: list[Company]) -> list[Employee]:
    if not companies:
        return []
    return list(
        Employee.objects.filter(
            is_active=True,
            employee_work_info__company_id__in=companies,
        )
        .distinct()
        .order_by("pk")
    )


def _shift_for_company(company: Company) -> EmployeeShift:
    shift, _ = upsert(
        EmployeeShift,
        {"employee_shift": "Regular Day"},
        {"weekly_full_time": "40:00", "full_time": "08:00"},
    )
    set_m2m(shift, "company_id", [company])
    return shift


def _shift_day(company: Company, day: date) -> EmployeeShiftDay:
    day_name = day.strftime("%A").lower()
    shift_day, _ = upsert(EmployeeShiftDay, {"day": day_name})
    set_m2m(shift_day, "company_id", [company])
    return shift_day


def _time_to_seconds(value: time) -> int:
    return value.hour * 3600 + value.minute * 60 + value.second


def _hours_label(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}"


def _clock_datetimes(day, clock_in: time, clock_out: time):
    return (
        timezone.make_aware(datetime.combine(day, clock_in)),
        timezone.make_aware(datetime.combine(day, clock_out)),
    )


def _work_info(employee: Employee) -> EmployeeWorkInformation | None:
    return (
        EmployeeWorkInformation.objects.filter(employee_id=employee)
        .select_related("company_id", "shift_id", "work_type_id")
        .first()
    )


def _attendance_pattern(employee_index: int, workday_index: int) -> str:
    return ("present", "late", "overtime", "half_day", "absent", "validate")[
        (employee_index + workday_index) % 6
    ]


def _seed_attendance(companies: list[Company], result: SeederResult) -> None:
    try:
        from attendance.models import (
            Attendance,
            AttendanceActivity,
            AttendanceLateComeEarlyOut,
            WorkRecords,
        )
    except ImportError:
        record(result, "existing", "Attendance skipped", "attendance app unavailable")
        return

    employees = _employees_in_companies(companies)
    if not employees:
        record(result, "existing", "Attendance skipped", "no DSG employees found")
        return

    today = timezone.localdate()
    created_attendance = 0
    created_absences = 0

    for emp_index, employee in enumerate(employees):
        work_info = _work_info(employee)
        if not work_info or not work_info.company_id:
            continue
        company = work_info.company_id
        shift = work_info.shift_id or _shift_for_company(company)
        work_type = work_info.work_type_id
        workdays = 0
        offset = 1

        while workdays < WORKING_DAYS_TARGET and offset <= ATTENDANCE_LOOKBACK_CALENDAR_DAYS:
            day = today - timedelta(days=offset)
            offset += 1
            if day.weekday() >= 5:
                continue

            pattern = _attendance_pattern(emp_index, workdays)
            shift_day = _shift_day(company, day)
            workdays += 1

            if pattern == "absent":
                _, status = upsert(
                    WorkRecords,
                    {"employee_id": employee, "date": day},
                    {
                        "record_name": "Absent",
                        "work_record_type": "ABS",
                        "at_work": "00:00",
                        "min_hour": "08:00",
                        "at_work_second": 0,
                        "min_hour_second": 8 * 3600,
                        "note": "Seeded absence",
                        "message": "Absent",
                        "is_attendance_record": False,
                        "shift_id": shift,
                        "day_percentage": 0.0,
                    },
                )
                if status == "created":
                    created_absences += 1
                continue

            if pattern == "late":
                clock_in, clock_out = time(9, 22), time(18, 5)
                validated, late_types = True, ["late_come"]
            elif pattern == "overtime":
                clock_in, clock_out = time(8, 55), time(20, 15)
                validated, late_types = True, []
            elif pattern == "half_day":
                clock_in, clock_out = time(9, 5), time(13, 10)
                validated, late_types = True, []
            elif pattern == "validate":
                clock_in, clock_out = time(9, 18), time(17, 45)
                validated, late_types = False, []
            else:
                clock_in, clock_out = time(9, 0), time(18, 0)
                validated, late_types = True, []

            worked_seconds = max(_time_to_seconds(clock_out) - _time_to_seconds(clock_in), 0)
            overtime_seconds = max(worked_seconds - 8 * 3600, 0) if pattern == "overtime" else 0
            work_record_type = "FDP" if worked_seconds >= 8 * 3600 else "HDP"
            if pattern == "half_day":
                work_record_type = "HDP"

            attendance, status = upsert(
                Attendance,
                {"employee_id": employee, "attendance_date": day},
                {
                    "shift_id": shift,
                    "work_type_id": work_type,
                    "attendance_day": shift_day,
                    "attendance_clock_in_date": day,
                    "attendance_clock_in": clock_in,
                    "attendance_clock_out_date": day,
                    "attendance_clock_out": clock_out,
                    "minimum_hour": "08:00",
                    "attendance_worked_hour": _hours_label(worked_seconds),
                    "at_work_second": worked_seconds,
                    "attendance_overtime": _hours_label(overtime_seconds),
                    "overtime_second": overtime_seconds,
                    "attendance_overtime_approve": pattern == "overtime" and emp_index % 2 == 0,
                    "attendance_validated": validated,
                    "is_validate_request": pattern == "validate",
                    "is_validate_request_approved": False,
                    "request_type": "update_request" if pattern == "validate" else None,
                    "request_description": (
                        "Seeded attendance correction for manager approval"
                        if pattern == "validate"
                        else None
                    ),
                    "is_holiday": False,
                },
            )
            if status == "created":
                created_attendance += 1

            in_dt, out_dt = _clock_datetimes(day, clock_in, clock_out)
            upsert(
                AttendanceActivity,
                {
                    "employee_id": employee,
                    "attendance_date": day,
                    "clock_in": clock_in,
                },
                {
                    "shift_day": shift_day,
                    "in_datetime": in_dt,
                    "clock_in_date": day,
                    "clock_out_date": day,
                    "out_datetime": out_dt,
                    "clock_out": clock_out,
                },
            )

            upsert(
                WorkRecords,
                {"employee_id": employee, "date": day},
                {
                    "record_name": "Present" if work_record_type == "FDP" else "Half Day Present",
                    "work_record_type": work_record_type,
                    "at_work": _hours_label(worked_seconds),
                    "min_hour": "08:00",
                    "at_work_second": worked_seconds,
                    "min_hour_second": 8 * 3600,
                    "note": f"Seeded {pattern} attendance",
                    "message": "Present" if work_record_type == "FDP" else "Half Day Present",
                    "is_attendance_record": True,
                    "attendance_id": attendance,
                    "shift_id": shift,
                    "day_percentage": 1.0 if work_record_type == "FDP" else 0.5,
                },
            )

            for late_type in late_types:
                upsert(
                    AttendanceLateComeEarlyOut,
                    {"attendance_id": attendance, "type": late_type},
                    {"employee_id": employee},
                )

    record(
        result,
        "created",
        "DSG attendance expanded",
        f"{created_attendance} new attendance rows, {created_absences} absences "
        f"across {len(employees)} employees (~{WORKING_DAYS_TARGET} workdays each)",
    )


def _leave_type(company: Company, name: str) -> LeaveType | None:
    return LeaveType.objects.filter(company_id=company, name=name).order_by("pk").first()


def _ensure_balances(employee: Employee, company: Company, result: SeederResult) -> None:
    specs = (
        ("Annual Leave", 14, 4),
        ("Casual Leave", 10, 2),
        ("Sick Leave", 8, 2),
    )
    for name, total, used in specs:
        leave_type = _leave_type(company, name)
        if leave_type is None:
            continue
        upsert(
            AvailableLeave,
            {"employee_id": employee, "leave_type_id": leave_type},
            {
                "available_days": float(total - used),
                "carryforward_days": 0,
                "total_leave_days": float(total),
            },
        )


def _seed_leave(companies: list[Company], result: SeederResult) -> None:
    employees = _employees_in_companies(companies)
    if not employees:
        record(result, "existing", "Leave skipped", "no DSG employees found")
        return

    today = timezone.localdate()
    for employee in employees:
        work_info = _work_info(employee)
        if work_info and work_info.company_id:
            _ensure_balances(employee, work_info.company_id, result)

    request_count = 0
    for spec in LEAVE_REQUEST_SPECS:
        employee = _employee_by_email(spec["email"])
        if employee is None:
            continue
        work_info = _work_info(employee)
        company = work_info.company_id if work_info else companies[0]
        leave_type = _leave_type(company, spec["leave_type"])
        if leave_type is None:
            continue

        start = today + timedelta(days=spec["start_offset"])
        end = today + timedelta(days=spec["end_offset"])
        leave_request, status = upsert(
            LeaveRequest,
            {
                "employee_id": employee,
                "leave_type_id": leave_type,
                "start_date": start,
            },
            {
                "end_date": end,
                "start_date_breakdown": "full_day",
                "end_date_breakdown": "full_day",
                "description": spec["description"],
                "status": spec["status"],
                "requested_date": today + timedelta(days=min(spec["start_offset"], -1)),
                "created_by": employee,
                "reject_reason": spec.get("reject_reason", ""),
            },
        )
        record(result, status, "Leave request", leave_request)
        if status == "created":
            request_count += 1

    for email, days, alloc_status in (
        (f"nadia.rahman@{EMAIL_DOMAIN}", 2, "requested"),
        (f"omar.siddiqui@{EMAIL_DOMAIN}", 1, "approved"),
        (f"kamran.shah@{EMAIL_DOMAIN}", 3, "requested"),
    ):
        employee = _employee_by_email(email)
        if employee is None:
            continue
        work_info = _work_info(employee)
        company = work_info.company_id if work_info else companies[0]
        sick = _leave_type(company, "Sick Leave")
        annual = _leave_type(company, "Annual Leave")
        leave_type = sick or annual
        if leave_type is None:
            continue
        allocation, status = upsert(
            LeaveAllocationRequest,
            {
                "employee_id": employee,
                "leave_type_id": leave_type,
                "status": alloc_status,
            },
            {
                "requested_days": days,
                "requested_date": today,
                "description": f"Seeded {alloc_status} extra leave allocation.",
                "reject_reason": "",
            },
        )
        record(result, status, "Leave allocation", allocation)

    record(
        result,
        "created",
        "DSG leave scenarios",
        f"{request_count} new leave requests + balances refreshed for {len(employees)} staff",
    )


@transaction.atomic
def seed() -> SeederResult:
    result = SeederResult()
    companies = _dsg_companies()
    if not companies:
        result.add(
            "existing",
            "DSG attendance/leave skipped — run pakistan_org seeder first.",
        )
        return result

    _seed_attendance(companies, result)
    _seed_leave(companies, result)
    return result
