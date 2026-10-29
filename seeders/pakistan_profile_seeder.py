"""
Complete every active employee profile for DSG Pakistan companies.

Fills shifts, bank details, personal gaps, contracts, leave balances,
allowances/perks, and bonus points so profiles look fully set up.
"""

from __future__ import annotations

from datetime import date, time, timedelta

from django.db import transaction
from django.utils import timezone

from base.models import (
    Company,
    EmployeeShift,
    EmployeeShiftDay,
    EmployeeShiftSchedule,
)
from employee.models import (
    BonusPoint,
    Employee,
    EmployeeBankDetails,
    EmployeeType,
    EmployeeWorkInformation,
    WorkType,
)
from leave.models import AvailableLeave, LeaveType
from payroll.models.models import Allowance, Contract

from .utils import SeederResult, record, set_m2m, upsert

SHIFT_DAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

PAK_BANKS = (
    "HBL",
    "Meezan Bank",
    "UBL",
    "Bank Alfalah",
    "MCB",
    "JazzCash Wallet",
)

PERKS = (
    ("Housing Allowance", 25000, True),
    ("Transport Allowance", 10000, False),
    ("Medical Allowance", 8000, False),
    ("Internet / WFH Stipend", 5000, False),
    ("Meal Allowance", 6000, False),
)

LEAVE_BALANCES = (
    ("Annual Leave", 14, 3),
    ("Casual Leave", 10, 2),
    ("Sick Leave", 8, 1),
)


def _ensure_shift_for_company(company: Company, result: SeederResult) -> EmployeeShift:
    days = {}
    for day in SHIFT_DAYS:
        shift_day, status = upsert(EmployeeShiftDay, {"day": day})
        set_m2m(shift_day, "company_id", [company])
        record(result, status, "Shift day", f"{day} @ {company}")
        days[day] = shift_day

    shift, status = upsert(
        EmployeeShift,
        {"employee_shift": "Regular Day"},
        {"weekly_full_time": "40:00", "full_time": "08:00"},
    )
    set_m2m(shift, "company_id", [company])
    record(result, status, "Shift", f"{shift} @ {company}")

    for day_name in SHIFT_DAYS[:5]:
        schedule, status = upsert(
            EmployeeShiftSchedule,
            {"shift_id": shift, "day": days[day_name]},
            {
                "minimum_working_hour": "08:00",
                "start_time": time(9, 0),
                "end_time": time(18, 0),
                "is_night_shift": False,
            },
        )
        set_m2m(schedule, "company_id", [company])
        record(result, status, "Shift schedule", f"{day_name} @ {company}")
    return shift


def _complete_personal(employee: Employee, company: Company | None, index: int, result):
    changed = False
    city = (company.city if company else None) or employee.city or "Karachi"
    state = (company.state if company else None) or employee.state or "Sindh"
    defaults = {
        "country": employee.country or "Pakistan",
        "state": employee.state or state,
        "city": employee.city or city,
        "address": employee.address or f"{city}, Pakistan",
        "zip": employee.zip or ("75350" if city == "Karachi" else "54000"),
        "dob": employee.dob or date(1990 + (index % 10), (index % 12) + 1, (index % 27) + 1),
        "qualification": employee.qualification or "Bachelor's Degree",
        "experience": employee.experience if employee.experience is not None else (index % 12) + 1,
        "marital_status": employee.marital_status or ("married" if index % 2 else "single"),
        "children": employee.children if employee.children is not None else (1 if index % 2 else 0),
        "emergency_contact": employee.emergency_contact
        or f"0301{(1000000 + index):07d}"[:15],
        "emergency_contact_name": employee.emergency_contact_name
        or (f"{employee.employee_first_name} Kin"[:20]),
        "emergency_contact_relation": employee.emergency_contact_relation or "Sibling",
        "badge_id": employee.badge_id or f"EMP-{employee.pk:04d}",
        "phone": employee.phone or f"0300{(1000000 + index):07d}"[:15],
        "gender": employee.gender or "male",
    }
    for field, value in defaults.items():
        if getattr(employee, field) != value:
            setattr(employee, field, value)
            changed = True
    if changed:
        employee.save()
        record(result, "updated", "Personal profile", employee)
    else:
        record(result, "existing", "Personal profile", employee)


def _future_contract_end(joining: date) -> date:
    """Keep contracts active — end date must be after today."""
    today = timezone.localdate()
    candidate = joining + timedelta(days=365 * 3)
    if candidate <= today:
        return today + timedelta(days=365 * 2)
    return candidate


def _complete_work_info(work_info: EmployeeWorkInformation, shift: EmployeeShift, result):
    changed = False
    salary = work_info.basic_salary or 150000
    joining = work_info.date_joining or (timezone.localdate() - timedelta(days=365))
    end_date = work_info.contract_end_date
    if end_date is None or end_date <= timezone.localdate():
        end_date = _future_contract_end(joining)
    updates = {
        "shift_id": shift,
        "basic_salary": salary,
        "salary_hour": work_info.salary_hour or max(int(salary / 176), 500),
        "date_joining": joining,
        "contract_end_date": end_date,
        "location": work_info.location
        or (
            f"{work_info.company_id.city} Office"
            if work_info.company_id_id
            else "Pakistan Office"
        ),
        "email": work_info.email or getattr(work_info.employee_id, "email", None),
        "mobile": work_info.mobile or getattr(work_info.employee_id, "phone", None),
        "experience": work_info.experience
        if work_info.experience
        else max((timezone.localdate() - joining).days / 365.0, 0.5),
    }
    if not work_info.work_type_id_id:
        wt, _ = upsert(WorkType, {"work_type": "Onsite"})
        if work_info.company_id_id:
            set_m2m(wt, "company_id", [work_info.company_id])
        updates["work_type_id"] = wt
    if not work_info.employee_type_id_id:
        et, _ = upsert(EmployeeType, {"employee_type": "Full Time"})
        if work_info.company_id_id:
            set_m2m(et, "company_id", [work_info.company_id])
        updates["employee_type_id"] = et

    for field, value in updates.items():
        if getattr(work_info, field) != value:
            setattr(work_info, field, value)
            changed = True
    if changed:
        work_info.save()
        record(result, "updated", "Work info", work_info.employee_id)
    else:
        record(result, "existing", "Work info", work_info.employee_id)


def _ensure_bank(employee: Employee, company: Company | None, index: int, result):
    bank_name = PAK_BANKS[index % len(PAK_BANKS)]
    city = (company.city if company else None) or employee.city or "Karachi"
    defaults = {
        "bank_name": bank_name,
        "account_number": f"PK{employee.pk:02d}{100000000000 + employee.pk * 17}",
        "branch": f"{city} Main Branch",
        "address": f"{city}, Pakistan",
        "country": "Pakistan",
        "state": (company.state if company else None) or employee.state or "Sindh",
        "city": city,
        "any_other_code1": f"IBAN-{employee.pk:04d}",
    }
    bank = EmployeeBankDetails.objects.filter(employee_id=employee).first()
    if bank is None:
        bank = EmployeeBankDetails(employee_id=employee, **defaults)
        bank.save()
        record(result, "created", "Bank details", employee)
    else:
        changed = False
        for field, value in defaults.items():
            if not getattr(bank, field):
                setattr(bank, field, value)
                changed = True
        if changed:
            bank.save()
            record(result, "updated", "Bank details", employee)
        else:
            record(result, "existing", "Bank details", employee)


def _ensure_contract(employee: Employee, work_info: EmployeeWorkInformation, result):
    salary = float(work_info.basic_salary or 150000)
    joining = work_info.date_joining or timezone.localdate()
    end_date = work_info.contract_end_date
    if end_date is None or end_date <= timezone.localdate():
        end_date = _future_contract_end(joining)
    title = (
        f"{work_info.job_position_id} Contract"
        if work_info.job_position_id_id
        else f"{employee} Contract"
    )
    contract = (
        Contract.objects.filter(employee_id=employee, contract_status="active")
        .order_by("pk")
        .first()
        or Contract.objects.filter(employee_id=employee).order_by("pk").first()
    )
    defaults = {
        "contract_name": title[:250],
        "contract_start_date": joining,
        "contract_end_date": end_date,
        "wage_type": "monthly",
        "pay_frequency": "monthly",
        "wage": salary,
        "contract_status": "active",
    }
    if contract is None:
        contract = Contract(employee_id=employee, **defaults)
        contract.save()
        record(result, "created", "Contract", employee)
    else:
        changed = False
        for field, value in defaults.items():
            if getattr(contract, field) != value:
                setattr(contract, field, value)
                changed = True
        if changed:
            contract.save()
            record(result, "updated", "Contract", employee)
        else:
            record(result, "existing", "Contract", employee)


def _ensure_leave(employee: Employee, company: Company | None, result):
    for name, total, used in LEAVE_BALANCES:
        lookup = {"name": name}
        defaults = {
            "payment": "paid",
            "payment_type": "paid",
            "count": 1,
            "total_days": total,
            "limit_leave": True,
            "reset": True,
            "reset_based": "yearly",
            "reset_month": "1",
            "reset_day": "1",
        }
        if company:
            leave_type, status = upsert(
                LeaveType, {**lookup, "company_id": company}, defaults
            )
        else:
            leave_type, status = upsert(LeaveType, lookup, defaults)
        record(result, status, "Leave type", f"{leave_type}")
        bal, created = AvailableLeave.objects.get_or_create(
            employee_id=employee,
            leave_type_id=leave_type,
            defaults={
                "available_days": float(total - used),
                "carryforward_days": 0,
                "total_leave_days": float(total),
            },
        )
        if not created and bal.total_leave_days in (None, 0):
            bal.available_days = float(total - used)
            bal.total_leave_days = float(total)
            bal.save()
            record(result, "updated", "Leave balance", f"{employee} / {name}")
        else:
            record(
                result,
                "created" if created else "existing",
                "Leave balance",
                f"{employee} / {name}",
            )


def _ensure_perks(company: Company, result: SeederResult):
    for title, amount, taxable in PERKS:
        allowance, status = upsert(
            Allowance,
            {"title": title, "company_id": company},
            {
                "include_active_employees": True,
                "is_taxable": taxable,
                "is_fixed": True,
                "is_condition_based": False,
                "amount": float(amount),
                "only_show_under_employee": False,
            },
        )
        record(result, status, "Perk / allowance", f"{title} @ {company}")


def _ensure_bonus(employee: Employee, index: int, result):
    points = 50 + (index % 5) * 10
    bonus, created = BonusPoint.objects.get_or_create(
        employee_id=employee,
        defaults={"points": points, "reason": "Performance & engagement credits"},
    )
    if not created and (bonus.points or 0) < 20:
        bonus.points = points
        bonus.reason = "Performance & engagement credits"
        bonus.save()
        record(result, "updated", "Bonus points", employee)
    else:
        record(result, "created" if created else "existing", "Bonus points", employee)


@transaction.atomic
def seed() -> SeederResult:
    result = SeederResult()
    companies = list(Company.objects.order_by("id"))
    shifts_by_company: dict[int, EmployeeShift] = {}
    for company in companies:
        shifts_by_company[company.pk] = _ensure_shift_for_company(company, result)
        _ensure_perks(company, result)

    default_shift = next(iter(shifts_by_company.values()), None)
    if default_shift is None:
        default_shift, _ = upsert(
            EmployeeShift,
            {"employee_shift": "Regular Day"},
            {"weekly_full_time": "40:00", "full_time": "08:00"},
        )

    employees = list(
        Employee.objects.filter(is_active=True)
        .select_related("employee_work_info", "employee_work_info__company_id")
        .order_by("id")
    )
    for index, employee in enumerate(employees):
        work_info = getattr(employee, "employee_work_info", None)
        if work_info is None:
            work_info = EmployeeWorkInformation.objects.create(employee_id=employee)
            record(result, "created", "Work info shell", employee)
        company = work_info.company_id
        shift = (
            shifts_by_company.get(company.pk, default_shift)
            if company
            else default_shift
        )
        _complete_personal(employee, company, index, result)
        _complete_work_info(work_info, shift, result)
        _ensure_bank(employee, company, index, result)
        _ensure_contract(employee, work_info, result)
        _ensure_leave(employee, company, result)
        _ensure_bonus(employee, index, result)

    result.add(
        "created",
        f"Completed profiles for {len(employees)} active employees "
        "(shifts, bank, contracts, leave, perks, bonus points).",
    )
    return result
