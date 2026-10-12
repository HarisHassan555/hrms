from __future__ import annotations

from datetime import datetime, time, timedelta

from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceGeneralSetting,
    AttendanceLateComeEarlyOut,
    AttendanceValidationCondition,
    GraceTime,
    WorkRecords,
)
from base.models import EmployeeShift, EmployeeShiftDay, EmployeeShiftSchedule
from employee.models import Employee, EmployeeWorkInformation
from django.utils import timezone

from .organization_seeder import get_seed_companies
from .utils import SeederResult, record, set_m2m, upsert


SHIFT_DAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

WORK_RECORD_LABELS = {
    "FDP": "Present",
    "HDP": "Half Day Present",
    "ABS": "Absent",
}


def _seconds(value: str) -> int:
    hours, minutes, seconds = [int(part) for part in value.split(":")]
    return hours * 3600 + minutes * 60 + seconds


def seed() -> SeederResult:
    result = SeederResult()
    companies = get_seed_companies()

    existing_default = GraceTime.objects.filter(is_default=True).order_by("pk").first()
    if existing_default:
        grace_lookup = {"pk": existing_default.pk}
        grace_defaults = {
            "allowed_time": "00:15:00",
            "allowed_time_in_secs": _seconds("00:15:00"),
            "allowed_clock_in": True,
            "allowed_clock_out": False,
            "is_default": True,
        }
    else:
        grace_lookup = {"allowed_time": "00:15:00", "is_default": True}
        grace_defaults = {
            "allowed_time_in_secs": _seconds("00:15:00"),
            "allowed_clock_in": True,
            "allowed_clock_out": False,
        }
    grace_time, status = upsert(
        GraceTime,
        grace_lookup,
        grace_defaults,
    )
    m2m_status = set_m2m(grace_time, "company_id", companies)
    if status == "existing" and m2m_status == "updated":
        status = "updated"
    record(result, status, "Grace Time", grace_time)

    days = {}
    for day in SHIFT_DAYS:
        shift_day, status = upsert(EmployeeShiftDay, {"day": day})
        m2m_status = set_m2m(shift_day, "company_id", companies)
        if status == "existing" and m2m_status == "updated":
            status = "updated"
        record(result, status, "Employee Shift Day", shift_day)
        days[day] = shift_day

    shift, status = upsert(
        EmployeeShift,
        {"employee_shift": "General Shift"},
        {
            "weekly_full_time": "40:00",
            "full_time": "200:00",
            "grace_time_id": grace_time,
        },
    )
    m2m_status = set_m2m(shift, "company_id", companies)
    if status == "existing" and m2m_status == "updated":
        status = "updated"
    record(result, status, "Employee Shift", shift)

    for day_name in SHIFT_DAYS[:5]:
        schedule, status = upsert(
            EmployeeShiftSchedule,
            {"shift_id": shift, "day": days[day_name]},
            {
                "minimum_working_hour": "08:00",
                "start_time": time(9, 0),
                "end_time": time(17, 0),
                "is_night_shift": False,
            },
        )
        m2m_status = set_m2m(schedule, "company_id", companies)
        if status == "existing" and m2m_status == "updated":
            status = "updated"
        record(result, status, "Employee Shift Schedule", schedule)

    condition = AttendanceValidationCondition.objects.order_by("pk").first()
    if condition is None:
        condition, status = upsert(
            AttendanceValidationCondition,
            {"validation_at_work": "08:00"},
            {
                "minimum_overtime_to_approve": "00:30",
                "overtime_cutoff": "02:00",
                "auto_approve_ot": False,
            },
        )
    else:
        condition, status = upsert(
            AttendanceValidationCondition,
            {"pk": condition.pk},
            {
                "validation_at_work": "08:00",
                "minimum_overtime_to_approve": "00:30",
                "overtime_cutoff": "02:00",
                "auto_approve_ot": False,
            },
        )
    m2m_status = set_m2m(condition, "company_id", companies)
    if status == "existing" and m2m_status == "updated":
        status = "updated"
    record(result, status, "Attendance Validation Condition", condition)

    for company in companies:
        setting, status = upsert(
            AttendanceGeneralSetting,
            {"company_id": company},
            {"time_runner": True, "enable_check_in": True},
        )
        record(result, status, "Attendance General Setting", setting)

    seed_sample_attendance(result, companies, shift, days)

    return result


def _primary_employee():
    return Employee.objects.filter(is_active=True).order_by("pk").first()


def _resolve_work_info(employee, companies, shift):
    from base.models import Department, EmployeeType, WorkType

    company = (
        EmployeeWorkInformation.objects.filter(employee_id=employee)
        .select_related("company_id")
        .values_list("company_id", flat=True)
        .first()
    )
    company_obj = next((item for item in companies if item.pk == company), None)
    if company_obj is None:
        company_obj = companies[0] if companies else None

    department = Department.objects.filter(company_id=company_obj).order_by("pk").first()
    work_type = WorkType.objects.filter(company_id=company_obj).order_by("pk").first()
    employee_type = (
        EmployeeType.objects.filter(company_id=company_obj).order_by("pk").first()
    )

    work_info, _created = EmployeeWorkInformation.objects.get_or_create(
        employee_id=employee
    )
    updates = {
        "company_id": company_obj,
        "department_id": department,
        "shift_id": shift,
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


def _time_to_seconds(value: time) -> int:
    return value.hour * 3600 + value.minute * 60 + value.second


def _duration_seconds(start: time, end: time) -> int:
    return _time_to_seconds(end) - _time_to_seconds(start)


def _hours_label(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}"


def _clock_datetimes(day, clock_in, clock_out):
    return (
        timezone.make_aware(datetime.combine(day, clock_in)),
        timezone.make_aware(datetime.combine(day, clock_out)),
    )


def seed_sample_attendance(result: SeederResult, companies, shift, days) -> None:
    employee = _primary_employee()
    if employee is None:
        result.add("existing", "Attendance sample skipped - no active employee found")
        return

    work_info = _resolve_work_info(employee, companies, shift)
    work_type = work_info.work_type_id
    now = datetime.now()
    today = now.date()
    today_clock_out = time(14, 30)
    if now.time() <= today_clock_out:
        safe_out = now - timedelta(minutes=5)
        today_clock_out = safe_out.time().replace(second=0, microsecond=0)
    today_clock_in = (
        datetime.combine(today, today_clock_out) - timedelta(hours=5)
    ).time()

    samples = [
        {
            "date": today,
            "clock_in": today_clock_in,
            "clock_out": today_clock_out,
            "validated": False,
            "request": False,
            "late_early": ["late_come", "early_out"],
        },
        {
            "date": today - timedelta(days=1),
            "clock_in": time(9, 0),
            "clock_out": time(19, 0),
            "validated": True,
            "request": False,
            "approve_ot": False,
            "late_early": [],
        },
        {
            "date": today - timedelta(days=2),
            "clock_in": time(9, 15),
            "clock_out": time(17, 15),
            "validated": False,
            "request": True,
            "late_early": ["late_come"],
        },
    ]

    for sample in samples:
        attendance_day = days[sample["date"].strftime("%A").lower()]
        worked_seconds = _duration_seconds(sample["clock_in"], sample["clock_out"])
        in_datetime, out_datetime = _clock_datetimes(
            sample["date"], sample["clock_in"], sample["clock_out"]
        )
        attendance, status = upsert(
            Attendance,
            {
                "employee_id": employee,
                "attendance_date": sample["date"],
            },
            {
                "shift_id": shift,
                "work_type_id": work_type,
                "attendance_day": attendance_day,
                "attendance_clock_in_date": sample["date"],
                "attendance_clock_in": sample["clock_in"],
                "attendance_clock_out_date": sample["date"],
                "attendance_clock_out": sample["clock_out"],
                "minimum_hour": "08:00",
                "attendance_worked_hour": _hours_label(worked_seconds),
                "at_work_second": worked_seconds,
                "attendance_validated": sample["validated"],
                "is_validate_request": sample["request"],
                "is_validate_request_approved": False,
                "request_type": "update_request",
                "request_description": (
                    "Seeded attendance correction request"
                    if sample["request"]
                    else None
                ),
                "attendance_overtime_approve": sample.get("approve_ot", False),
            },
        )
        record(result, status, "Attendance", attendance)

        activity, activity_status = upsert(
            AttendanceActivity,
            {
                "employee_id": employee,
                "attendance_date": sample["date"],
                "clock_in": sample["clock_in"],
            },
            {
                "shift_day": attendance_day,
                "in_datetime": in_datetime,
                "clock_in_date": sample["date"],
                "clock_out_date": sample["date"],
                "out_datetime": out_datetime,
                "clock_out": sample["clock_out"],
            },
        )
        record(result, activity_status, "Attendance Activity", activity)

        work_record_type = "FDP" if worked_seconds >= 8 * 3600 else "HDP"
        work_record, work_record_status = upsert(
            WorkRecords,
            {
                "employee_id": employee,
                "date": sample["date"],
            },
            {
                "record_name": WORK_RECORD_LABELS[work_record_type],
                "work_record_type": work_record_type,
                "at_work": _hours_label(worked_seconds),
                "min_hour": "08:00",
                "at_work_second": worked_seconds,
                "min_hour_second": 8 * 3600,
                "note": "Seeded attendance work status",
                "message": WORK_RECORD_LABELS[work_record_type],
                "is_attendance_record": True,
                "attendance_id": attendance,
                "shift_id": shift,
                "day_percentage": 1.0 if work_record_type == "FDP" else 0.5,
            },
        )
        record(result, work_record_status, "Daily Work Status", work_record)

        for late_type in sample["late_early"]:
            late_record, late_status = upsert(
                AttendanceLateComeEarlyOut,
                {
                    "attendance_id": attendance,
                    "type": late_type,
                },
                {"employee_id": employee},
            )
            record(result, late_status, "Late/Early Record", late_record)
