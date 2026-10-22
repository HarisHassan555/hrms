"""
Seed 20 portal-style employees with the Admin company role, work info, and shift.

Runs prerequisite master data (organization, work/employee types, attendance shifts,
leave types) then creates users the same way as the Qarshi seeder.

Default password: ``DemoHRMS123!`` (override with ``ADMIN_TEAM_SEED_PASSWORD``).
Emails: ``admin.team01@demo.hrms`` … ``admin.team20@demo.hrms``
"""

from __future__ import annotations

import os
from datetime import date

from django.contrib.auth.models import Group
from django.db import transaction

from base.models import (
    Company,
    CompanyGroupAssignment,
    Department,
    EmployeeShift,
    JobPosition,
    JobRole,
)
from employee.models import Employee, EmployeeType, EmployeeWorkInformation, WorkType

from horilla_auth.models import HorillaUser

from . import attendance_seeder, employee_seeder, leave_seeder, organization_seeder
from .organization_seeder import get_seed_companies
from .utils import SeederResult, record, set_m2m, upsert

EMPLOYEE_COUNT = 20
EMAIL_DOMAIN = "demo.hrms"
GROUP_NAME = "Admin"
DEFAULT_PASSWORD = os.environ.get("ADMIN_TEAM_SEED_PASSWORD", "DemoHRMS123!")
BADGE_PREFIX = "ADM"

DEPARTMENT_NAME = "Administration"
JOB_POSITION_NAME = "Administrator"
JOB_ROLE_NAME = "System Administrator"

# Deterministic demo names (20 rows)
_PEOPLE = [
    ("Amina", "Khan"),
    ("Bilal", "Ahmed"),
    ("Carla", "Nguyen"),
    ("Daniel", "Okafor"),
    ("Elena", "Petrova"),
    ("Farhan", "Siddiqui"),
    ("Grace", "Mbeki"),
    ("Hassan", "Rahman"),
    ("Isabella", "Costa"),
    ("James", "Wilson"),
    ("Keiko", "Tanaka"),
    ("Liam", "Murphy"),
    ("Maya", "Sharma"),
    ("Noah", "Fischer"),
    ("Olivia", "Brown"),
    ("Priya", "Nair"),
    ("Quinn", "Anderson"),
    ("Ravi", "Patel"),
    ("Sofia", "Martinez"),
    ("Thomas", "Lee"),
]


def _email_for_index(index: int) -> str:
    return f"admin.team{index:02d}@{EMAIL_DOMAIN}"


def _badge_for_index(index: int) -> str:
    return f"{BADGE_PREFIX}-{index:03d}"


def _phone_for_index(index: int) -> str:
    return f"+92300{index:07d}"


def _resolve_org(company: Company, result: SeederResult) -> tuple[Department, JobPosition, JobRole]:
    department = Department.objects.filter(department=DEPARTMENT_NAME).order_by("pk").first()
    if not department:
        department, status = upsert(Department, {"department": DEPARTMENT_NAME})
        set_m2m(department, "company_id", [company])
        record(result, status, "Department", department)

    job_position = JobPosition.objects.filter(
        department_id=department, job_position=JOB_POSITION_NAME
    ).order_by("pk").first()
    if not job_position:
        job_position, status = upsert(
            JobPosition,
            {"department_id": department, "job_position": JOB_POSITION_NAME},
        )
        set_m2m(job_position, "company_id", [company])
        record(result, status, "Job Position", job_position)

    job_role = JobRole.objects.filter(
        job_position_id=job_position, job_role=JOB_ROLE_NAME
    ).order_by("pk").first()
    if not job_role:
        job_role, status = upsert(
            JobRole,
            {"job_position_id": job_position, "job_role": JOB_ROLE_NAME},
        )
        set_m2m(job_role, "company_id", [company])
        record(result, status, "Job Role", job_role)

    return department, job_position, job_role


def _work_type_and_employee_type(company: Company) -> tuple[WorkType, EmployeeType]:
    work_type = WorkType.objects.filter(work_type="Onsite").order_by("pk").first()
    employee_type = EmployeeType.objects.filter(employee_type="Full Time").order_by("pk").first()
    if not work_type or not employee_type:
        employee_seeder.seed()
        work_type = WorkType.objects.filter(work_type="Onsite").order_by("pk").first()
        employee_type = EmployeeType.objects.filter(employee_type="Full Time").order_by("pk").first()
    if work_type:
        set_m2m(work_type, "company_id", [company])
    if employee_type:
        set_m2m(employee_type, "company_id", [company])
    return work_type, employee_type


def _general_shift(company: Company) -> EmployeeShift | None:
    shift = EmployeeShift.objects.filter(employee_shift="General Shift").order_by("pk").first()
    if shift:
        set_m2m(shift, "company_id", [company])
    return shift


def _ensure_user(
    email: str,
    first_name: str,
    last_name: str,
    password: str,
) -> tuple[HorillaUser, str]:
    user = HorillaUser.objects.filter(username=email).first()
    if user:
        return user, "existing"
    user = HorillaUser.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_superuser=False,
        is_staff=False,
    )
    return user, "created"


def _ensure_employee(
    user: HorillaUser,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    badge_id: str,
) -> tuple[Employee, str]:
    employee = Employee.objects.filter(employee_user_id=user).first()
    if employee:
        changed = False
        for field, value in {
            "employee_first_name": first_name,
            "employee_last_name": last_name,
            "email": email,
            "phone": phone,
            "badge_id": badge_id,
            "is_active": True,
            "gender": "male",
            "marital_status": "single",
        }.items():
            if getattr(employee, field) != value:
                setattr(employee, field, value)
                changed = True
        if changed:
            employee.save()
            return employee, "updated"
        return employee, "existing"

    employee = Employee(
        employee_user_id=user,
        employee_first_name=first_name,
        employee_last_name=last_name,
        email=email,
        phone=phone,
        badge_id=badge_id,
        is_active=True,
        gender="male",
        marital_status="single",
    )
    employee.save()
    return employee, "created"


def _ensure_work_info(
    employee: Employee,
    company: Company,
    department: Department,
    job_position: JobPosition,
    job_role: JobRole,
    work_type: WorkType | None,
    employee_type: EmployeeType | None,
    shift: EmployeeShift | None,
    manager: Employee | None,
) -> tuple[EmployeeWorkInformation, str]:
    defaults = {
        "company_id": company,
        "department_id": department,
        "job_position_id": job_position,
        "job_role_id": job_role,
        "work_type_id": work_type,
        "employee_type_id": employee_type,
        "shift_id": shift,
        "reporting_manager_id": manager,
        "date_joining": date.today(),
        "email": employee.email,
        "mobile": employee.phone,
    }
    work_info, created = EmployeeWorkInformation.objects.get_or_create(
        employee_id=employee,
        defaults=defaults,
    )
    if created:
        return work_info, "created"

    changed = False
    for field, value in defaults.items():
        if getattr(work_info, field) != value:
            setattr(work_info, field, value)
            changed = True
    if changed:
        work_info.save()
        return work_info, "updated"
    return work_info, "existing"


def _assign_admin_role(user: HorillaUser, company: Company) -> str:
    group = Group.objects.filter(name=GROUP_NAME).first()
    if not group:
        return "existing"
    _, created = CompanyGroupAssignment.objects.get_or_create(
        user=user,
        company=company,
        group=group,
    )
    CompanyGroupAssignment.sync_user_group_membership(user, group)
    return "created" if created else "existing"


@transaction.atomic
def seed() -> SeederResult:
    result = SeederResult()

    result.extend(organization_seeder.seed())
    result.extend(employee_seeder.seed())
    result.extend(attendance_seeder.seed())
    result.extend(leave_seeder.seed())

    companies = get_seed_companies()
    company = companies[0]
    if not company.hq and not Company.objects.filter(hq=True).exists():
        company.hq = True
        company.save(update_fields=["hq"])

    department, job_position, job_role = _resolve_org(company, result)
    work_type, employee_type = _work_type_and_employee_type(company)
    shift = _general_shift(company)

    employees: list[Employee] = []
    head_manager: Employee | None = None

    for index in range(1, EMPLOYEE_COUNT + 1):
        first_name, last_name = _PEOPLE[index - 1]
        email = _email_for_index(index)
        user, user_status = _ensure_user(
            email, first_name, last_name, DEFAULT_PASSWORD
        )
        record(result, user_status, "User", user)

        employee, emp_status = _ensure_employee(
            user,
            first_name,
            last_name,
            email,
            _phone_for_index(index),
            _badge_for_index(index),
        )
        record(result, emp_status, "Employee", employee)
        employees.append(employee)
        if index == 1:
            head_manager = employee

    for index, employee in enumerate(employees, start=1):
        manager = None if index == 1 else head_manager
        work_info, wi_status = _ensure_work_info(
            employee,
            company,
            department,
            job_position,
            job_role,
            work_type,
            employee_type,
            shift,
            manager,
        )
        record(result, wi_status, "Work Information", work_info)

        role_status = _assign_admin_role(employee.employee_user_id, company)
        record(result, role_status, "Company role", f"{employee.email} -> {GROUP_NAME}")

    result.add(
        "created",
        (
            f"Admin team seed complete: {EMPLOYEE_COUNT} employees with "
            f"'{GROUP_NAME}' role, General Shift, and master data. "
            f"Password: {DEFAULT_PASSWORD}"
        ),
    )
    return result
