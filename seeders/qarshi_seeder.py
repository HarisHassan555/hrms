"""
Seed Qarshi Industries — org structure, four demo users, and company-scoped roles.

Default password for all seeded accounts: ``QarshiHRMS123!``
(override with env ``QARSHI_SEED_PASSWORD``).

Users:
  - Company administrator (Admin role @ Qarshi)
  - HR Department manager
  - IT Department manager
  - Shared HR/IT staff employee (reports to HR manager)
"""

from __future__ import annotations

import os
from datetime import date

from django.contrib.auth.models import Group
from django.db import transaction

from base.models import Company, CompanyGroupAssignment, Department, JobPosition, JobRole
from employee.models import Employee, EmployeeType, EmployeeWorkInformation, WorkType
from horilla_auth.models import HorillaUser

from .utils import SeederResult, record, set_m2m, upsert

COMPANY_NAME = "Qarshi Industries"
DEFAULT_PASSWORD = os.environ.get("QARSHI_SEED_PASSWORD", "QarshiHRMS123!")

DEPARTMENTS = (
    "HR Department",
    "IT Department",
)

JOB_SETUP = (
    ("HR Department", "Company Administrator", ("Administrator",)),
    ("HR Department", "HR Manager", ("HR Manager",)),
    ("HR Department", "HR & IT Coordinator", ("Coordinator",)),
    ("IT Department", "IT Manager", ("IT Manager",)),
    ("IT Department", "IT Support Specialist", ("Support",)),
)

PEOPLE = (
    {
        "email": "qarshi.admin@qarshi-industries.com",
        "first_name": "Ayesha",
        "last_name": "Qarshi",
        "phone": "03001234501",
        "badge_id": "QAR-001",
        "department": "HR Department",
        "job_position": "Company Administrator",
        "job_role": "Administrator",
        "reporting_manager_email": None,
        "group_name": "Admin",
    },
    {
        "email": "hr.manager@qarshi-industries.com",
        "first_name": "Bilal",
        "last_name": "Hussain",
        "phone": "03001234502",
        "badge_id": "QAR-002",
        "department": "HR Department",
        "job_position": "HR Manager",
        "job_role": "HR Manager",
        "reporting_manager_email": "qarshi.admin@qarshi-industries.com",
        "group_name": "HR Manager",
    },
    {
        "email": "it.manager@qarshi-industries.com",
        "first_name": "Sana",
        "last_name": "Malik",
        "phone": "03001234503",
        "badge_id": "QAR-003",
        "department": "IT Department",
        "job_position": "IT Manager",
        "job_role": "IT Manager",
        "reporting_manager_email": "qarshi.admin@qarshi-industries.com",
        "group_name": "HR Manager",
    },
    {
        "email": "staff.shared@qarshi-industries.com",
        "first_name": "Usman",
        "last_name": "Khan",
        "phone": "03001234504",
        "badge_id": "QAR-004",
        "department": "HR Department",
        "job_position": "HR & IT Coordinator",
        "job_role": "Coordinator",
        "reporting_manager_email": "hr.manager@qarshi-industries.com",
        "group_name": None,
    },
)


def _ensure_company() -> tuple[Company, str]:
    company, status = upsert(
        Company,
        {"company": COMPANY_NAME},
        {
            "address": "Lahore, Pakistan",
            "country": "Pakistan",
            "state": "Punjab",
            "city": "Lahore",
            "zip": "54000",
            "hq": not Company.objects.filter(hq=True).exclude(company=COMPANY_NAME).exists(),
        },
    )
    return company, status


def _ensure_master_data(company: Company, result: SeederResult) -> tuple[WorkType, EmployeeType]:
    work_type, wt_status = upsert(WorkType, {"work_type": "Onsite"})
    if set_m2m(work_type, "company_id", [company]) == "updated" and wt_status == "existing":
        wt_status = "updated"
    record(result, wt_status, "Work Type", work_type)

    employee_type, et_status = upsert(EmployeeType, {"employee_type": "Full Time"})
    if set_m2m(employee_type, "company_id", [company]) == "updated" and et_status == "existing":
        et_status = "updated"
    record(result, et_status, "Employee Type", employee_type)
    return work_type, employee_type


def _ensure_org(company: Company, result: SeederResult) -> dict:
    departments: dict[str, Department] = {}
    for name in DEPARTMENTS:
        dept, status = upsert(Department, {"department": name})
        if set_m2m(dept, "company_id", [company]) == "updated" and status == "existing":
            status = "updated"
        record(result, status, "Department", dept)
        departments[name] = dept

    positions: dict[tuple[str, str], JobPosition] = {}
    roles: dict[tuple[str, str, str], JobRole] = {}

    for dept_name, position_name, role_names in JOB_SETUP:
        dept = departments[dept_name]
        key = (dept_name, position_name)
        if key not in positions:
            job_position, status = upsert(
                JobPosition,
                {"department_id": dept, "job_position": position_name},
            )
            if set_m2m(job_position, "company_id", [company]) == "updated" and status == "existing":
                status = "updated"
            record(result, status, "Job Position", job_position)
            positions[key] = job_position

        for role_name in role_names:
            role_key = (dept_name, position_name, role_name)
            job_position = positions[key]
            job_role, role_status = upsert(
                JobRole,
                {"job_position_id": job_position, "job_role": role_name},
            )
            if set_m2m(job_role, "company_id", [company]) == "updated" and role_status == "existing":
                role_status = "updated"
            record(result, role_status, "Job Role", job_role)
            roles[role_key] = job_role

    return {"departments": departments, "positions": positions, "roles": roles}


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
    )
    employee.save()
    return employee, "created"


def _ensure_work_info(
    employee: Employee,
    company: Company,
    department: Department,
    job_position: JobPosition,
    job_role: JobRole,
    work_type: WorkType,
    employee_type: EmployeeType,
    manager: Employee | None,
) -> tuple[EmployeeWorkInformation, str]:
    work_info, created = EmployeeWorkInformation.objects.get_or_create(
        employee_id=employee,
        defaults={
            "company_id": company,
            "department_id": department,
            "job_position_id": job_position,
            "job_role_id": job_role,
            "work_type_id": work_type,
            "employee_type_id": employee_type,
            "reporting_manager_id": manager,
            "date_joining": date.today(),
            "email": employee.email,
            "mobile": employee.phone,
        },
    )
    if created:
        return work_info, "created"

    changed = False
    updates = {
        "company_id": company,
        "department_id": department,
        "job_position_id": job_position,
        "job_role_id": job_role,
        "work_type_id": work_type,
        "employee_type_id": employee_type,
        "reporting_manager_id": manager,
        "email": employee.email,
        "mobile": employee.phone,
    }
    for field, value in updates.items():
        if getattr(work_info, field) != value:
            setattr(work_info, field, value)
            changed = True
    if changed:
        work_info.save()
        return work_info, "updated"
    return work_info, "existing"


def _assign_group(user: HorillaUser, company: Company, group_name: str | None) -> str:
    if not group_name:
        return "existing"
    group = Group.objects.filter(name=group_name).first()
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
    company, company_status = _ensure_company()
    record(result, company_status, "Company", company)

    work_type, employee_type = _ensure_master_data(company, result)
    org = _ensure_org(company, result)

    employees_by_email: dict[str, Employee] = {}

    for person in PEOPLE:
        user, user_status = _ensure_user(
            person["email"],
            person["first_name"],
            person["last_name"],
            DEFAULT_PASSWORD,
        )
        record(result, user_status, "User", user)

        employee, emp_status = _ensure_employee(
            user,
            person["first_name"],
            person["last_name"],
            person["email"],
            person["phone"],
            person["badge_id"],
        )
        record(result, emp_status, "Employee", employee)
        employees_by_email[person["email"]] = employee

    for person in PEOPLE:
        employee = employees_by_email[person["email"]]
        manager = None
        if person["reporting_manager_email"]:
            manager = employees_by_email.get(person["reporting_manager_email"])

        dept = org["departments"][person["department"]]
        pos = org["positions"][(person["department"], person["job_position"])]
        role = org["roles"][
            (person["department"], person["job_position"], person["job_role"])
        ]

        work_info, wi_status = _ensure_work_info(
            employee,
            company,
            dept,
            pos,
            role,
            work_type,
            employee_type,
            manager,
        )
        record(result, wi_status, "Work Information", work_info)

        group_status = _assign_group(
            employee.employee_user_id,
            company,
            person["group_name"],
        )
        if person["group_name"]:
            record(
                result,
                group_status,
                "Company role",
                f"{person['email']} -> {person['group_name']}",
            )

    result.add(
        "created",
        f"Qarshi seed complete. Login password for all four users: {DEFAULT_PASSWORD}",
    )
    return result
