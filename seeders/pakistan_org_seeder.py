"""
Seed a Pakistani organization with two companies, org charts, and history.

Organization brand: DataSphere Global
  1) DSG Technologies — Karachi (HQ, product & engineering)
  2) DSG Business Solutions — Lahore (sales, finance, shared services)

Default password for seeded logins: ``DemoHRMS123!``
(override with env ``PAKISTAN_ORG_SEED_PASSWORD``).

Idempotent. Safe to re-run.
"""

from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

from base.models import Company, CompanyGroupAssignment, Department, JobPosition, JobRole
from employee.models import Employee, EmployeeType, EmployeeWorkInformation, WorkType
from horilla_auth.models import HorillaUser

from .utils import SeederResult, record, set_m2m, upsert

DEFAULT_PASSWORD = os.environ.get("PAKISTAN_ORG_SEED_PASSWORD", "1212")
EMAIL_DOMAIN = "dsg.pk"

COMPANIES = (
    {
        "key": "tech",
        "company": "DSG Technologies",
        "address": "Plot 12, Shahrah-e-Faisal, Karachi",
        "country": "Pakistan",
        "state": "Sindh",
        "city": "Karachi",
        "zip": "75350",
        "hq": True,
    },
    {
        "key": "services",
        "company": "DSG Business Solutions",
        "address": "Office 408, Gulberg III, Lahore",
        "country": "Pakistan",
        "state": "Punjab",
        "city": "Lahore",
        "zip": "54660",
        "hq": False,
    },
)

# Department -> positions -> roles (shared catalog, company-scoped via M2M)
ORG_SETUP = {
    "Executive Office": {
        "Chief Executive Officer": ("Chief Executive",),
        "Managing Director": ("Business Lead",),
    },
    "Human Resources": {
        "HR Manager": ("People Operations",),
        "Talent Acquisition Specialist": ("Recruiter",),
        "HR Generalist": ("HR Operations",),
    },
    "Engineering": {
        "Engineering Manager": ("Engineering Lead",),
        "Senior Software Engineer": ("Backend Engineer",),
        "Software Engineer": ("Full Stack Engineer",),
        "Frontend Engineer": ("UI Engineer",),
        "QA Engineer": ("Quality Analyst",),
        "DevOps Engineer": ("Site Reliability",),
    },
    "Information Technology": {
        "IT Manager": ("IT Operations",),
        "IT Support Specialist": ("Desktop Support",),
    },
    "Sales": {
        "Sales Manager": ("Sales Lead",),
        "Account Executive": ("Enterprise Sales",),
        "Sales Development Representative": ("Outbound Sales",),
    },
    "Finance": {
        "Finance Manager": ("Financial Controller",),
        "Accountant": ("Accounts Payable",),
    },
    "Operations": {
        "Operations Manager": ("Office Operations",),
        "Office Coordinator": ("Administration",),
    },
}

# People for DSG Technologies (Karachi)
TECH_PEOPLE = (
    {
        "email": f"kamran.shah@{EMAIL_DOMAIN}",
        "first_name": "Kamran",
        "last_name": "Shah",
        "phone": "03001110100",
        "badge_id": "TECH-100",
        "gender": "male",
        "dob": date(1979, 5, 11),
        "department": "Executive Office",
        "job_position": "Chief Executive Officer",
        "job_role": "Chief Executive",
        "manager_email": None,
        "salary": 650000,
        "experience": 22,
        "qualification": "MBA Strategy",
        "marital_status": "married",
        "joining": date(2016, 1, 4),
        "group_name": "Admin",
    },
    {
        "email": f"nadia.rahman@{EMAIL_DOMAIN}",
        "first_name": "Nadia",
        "last_name": "Rahman",
        "phone": "03001110101",
        "badge_id": "TECH-101",
        "gender": "female",
        "dob": date(1988, 3, 14),
        "department": "Human Resources",
        "job_position": "HR Manager",
        "job_role": "People Operations",
        "manager_email": f"kamran.shah@{EMAIL_DOMAIN}",
        "salary": 280000,
        "experience": 12,
        "qualification": "MBA Human Resources",
        "marital_status": "married",
        "joining": date(2019, 4, 1),
        "group_name": "HR Manager",
    },
    {
        "email": f"omar.siddiqui@{EMAIL_DOMAIN}",
        "first_name": "Omar",
        "last_name": "Siddiqui",
        "phone": "03001110102",
        "badge_id": "TECH-102",
        "gender": "male",
        "dob": date(1992, 7, 22),
        "department": "Human Resources",
        "job_position": "Talent Acquisition Specialist",
        "job_role": "Recruiter",
        "manager_email": f"nadia.rahman@{EMAIL_DOMAIN}",
        "salary": 165000,
        "experience": 7,
        "qualification": "BS Psychology",
        "marital_status": "single",
        "joining": date(2021, 6, 15),
        "group_name": None,
    },
    {
        "email": f"hira.malik@{EMAIL_DOMAIN}",
        "first_name": "Hira",
        "last_name": "Malik",
        "phone": "03001110103",
        "badge_id": "TECH-103",
        "gender": "female",
        "dob": date(1995, 11, 2),
        "department": "Human Resources",
        "job_position": "HR Generalist",
        "job_role": "HR Operations",
        "manager_email": f"nadia.rahman@{EMAIL_DOMAIN}",
        "salary": 140000,
        "experience": 5,
        "qualification": "BBA",
        "marital_status": "married",
        "joining": date(2022, 1, 10),
        "group_name": None,
    },
    {
        "email": f"zain.abbas@{EMAIL_DOMAIN}",
        "first_name": "Zain",
        "last_name": "Abbas",
        "phone": "03001110104",
        "badge_id": "TECH-104",
        "gender": "male",
        "dob": date(1986, 1, 19),
        "department": "Engineering",
        "job_position": "Engineering Manager",
        "job_role": "Engineering Lead",
        "manager_email": f"kamran.shah@{EMAIL_DOMAIN}",
        "salary": 420000,
        "experience": 14,
        "qualification": "MS Computer Science",
        "marital_status": "married",
        "joining": date(2018, 9, 3),
        "group_name": "Manager",
    },
    {
        "email": f"fatima.noor@{EMAIL_DOMAIN}",
        "first_name": "Fatima",
        "last_name": "Noor",
        "phone": "03001110105",
        "badge_id": "TECH-105",
        "gender": "female",
        "dob": date(1993, 5, 8),
        "department": "Engineering",
        "job_position": "Senior Software Engineer",
        "job_role": "Backend Engineer",
        "manager_email": f"zain.abbas@{EMAIL_DOMAIN}",
        "salary": 310000,
        "experience": 9,
        "qualification": "BS Software Engineering",
        "marital_status": "single",
        "joining": date(2020, 2, 17),
        "group_name": None,
    },
    {
        "email": f"ali.raza@{EMAIL_DOMAIN}",
        "first_name": "Ali",
        "last_name": "Raza",
        "phone": "03001110106",
        "badge_id": "TECH-106",
        "gender": "male",
        "dob": date(1996, 8, 30),
        "department": "Engineering",
        "job_position": "Software Engineer",
        "job_role": "Full Stack Engineer",
        "manager_email": f"zain.abbas@{EMAIL_DOMAIN}",
        "salary": 210000,
        "experience": 4,
        "qualification": "BS Computer Science",
        "marital_status": "single",
        "joining": date(2023, 3, 6),
        "group_name": None,
    },
    {
        "email": f"sana.iqbal@{EMAIL_DOMAIN}",
        "first_name": "Sana",
        "last_name": "Iqbal",
        "phone": "03001110107",
        "badge_id": "TECH-107",
        "gender": "female",
        "dob": date(1994, 12, 12),
        "department": "Engineering",
        "job_position": "QA Engineer",
        "job_role": "Quality Analyst",
        "manager_email": f"zain.abbas@{EMAIL_DOMAIN}",
        "salary": 175000,
        "experience": 6,
        "qualification": "BS Information Technology",
        "marital_status": "married",
        "joining": date(2021, 11, 1),
        "group_name": None,
    },
    {
        "email": f"rehan.malik@{EMAIL_DOMAIN}",
        "first_name": "Rehan",
        "last_name": "Malik",
        "phone": "03001110108",
        "badge_id": "TECH-108",
        "gender": "male",
        "dob": date(1991, 2, 8),
        "department": "Engineering",
        "job_position": "DevOps Engineer",
        "job_role": "Site Reliability",
        "manager_email": f"zain.abbas@{EMAIL_DOMAIN}",
        "salary": 240000,
        "experience": 8,
        "qualification": "BS Information Systems",
        "marital_status": "married",
        "joining": date(2022, 3, 21),
        "group_name": None,
    },
    {
        "email": f"farah.aziz@{EMAIL_DOMAIN}",
        "first_name": "Farah",
        "last_name": "Aziz",
        "phone": "03001110109",
        "badge_id": "TECH-109",
        "gender": "female",
        "dob": date(1995, 9, 14),
        "department": "Engineering",
        "job_position": "Frontend Engineer",
        "job_role": "UI Engineer",
        "manager_email": f"zain.abbas@{EMAIL_DOMAIN}",
        "salary": 205000,
        "experience": 5,
        "qualification": "BS Computer Science",
        "marital_status": "single",
        "joining": date(2023, 6, 12),
        "group_name": None,
    },
    {
        "email": f"hamza.sheikh@{EMAIL_DOMAIN}",
        "first_name": "Hamza",
        "last_name": "Sheikh",
        "phone": "03001110110",
        "badge_id": "TECH-110",
        "gender": "male",
        "dob": date(1991, 10, 21),
        "department": "Information Technology",
        "job_position": "IT Manager",
        "job_role": "IT Operations",
        "manager_email": f"kamran.shah@{EMAIL_DOMAIN}",
        "salary": 260000,
        "experience": 10,
        "qualification": "BS Computer Networks",
        "marital_status": "married",
        "joining": date(2020, 7, 13),
        "group_name": "Manager",
    },
    {
        "email": f"rabia.yousaf@{EMAIL_DOMAIN}",
        "first_name": "Rabia",
        "last_name": "Yousaf",
        "phone": "03001110111",
        "badge_id": "TECH-111",
        "gender": "female",
        "dob": date(1999, 1, 9),
        "department": "Information Technology",
        "job_position": "IT Support Specialist",
        "job_role": "Desktop Support",
        "manager_email": f"hamza.sheikh@{EMAIL_DOMAIN}",
        "salary": 110000,
        "experience": 2,
        "qualification": "Diploma in IT",
        "marital_status": "single",
        "joining": date(2024, 9, 2),
        "group_name": None,
    },
)

# People for DSG Business Solutions (Lahore)
SERVICES_PEOPLE = (
    {
        "email": f"bilal.hassan@{EMAIL_DOMAIN}",
        "first_name": "Bilal",
        "last_name": "Hassan",
        "phone": "03002220100",
        "badge_id": "SVC-200",
        "gender": "male",
        "dob": date(1985, 4, 4),
        "department": "Executive Office",
        "job_position": "Managing Director",
        "job_role": "Business Lead",
        "manager_email": None,
        "salary": 520000,
        "experience": 16,
        "qualification": "MBA Marketing",
        "marital_status": "married",
        "joining": date(2017, 8, 12),
        "group_name": "Admin",
    },
    {
        "email": f"ayesha.kamal@{EMAIL_DOMAIN}",
        "first_name": "Ayesha",
        "last_name": "Kamal",
        "phone": "03002220101",
        "badge_id": "SVC-201",
        "gender": "female",
        "dob": date(1990, 2, 27),
        "department": "Human Resources",
        "job_position": "HR Manager",
        "job_role": "People Operations",
        "manager_email": f"bilal.hassan@{EMAIL_DOMAIN}",
        "salary": 250000,
        "experience": 10,
        "qualification": "MS HRM",
        "marital_status": "married",
        "joining": date(2019, 1, 8),
        "group_name": "HR Manager",
    },
    {
        "email": f"usman.ali@{EMAIL_DOMAIN}",
        "first_name": "Usman",
        "last_name": "Ali",
        "phone": "03002220102",
        "badge_id": "SVC-202",
        "gender": "male",
        "dob": date(1992, 12, 1),
        "department": "Human Resources",
        "job_position": "HR Generalist",
        "job_role": "HR Operations",
        "manager_email": f"ayesha.kamal@{EMAIL_DOMAIN}",
        "salary": 132000,
        "experience": 6,
        "qualification": "MA Human Resource Management",
        "marital_status": "married",
        "joining": date(2022, 5, 16),
        "group_name": None,
    },
    {
        "email": f"maham.javed@{EMAIL_DOMAIN}",
        "first_name": "Maham",
        "last_name": "Javed",
        "phone": "03002220103",
        "badge_id": "SVC-203",
        "gender": "female",
        "dob": date(1996, 4, 25),
        "department": "Sales",
        "job_position": "Sales Manager",
        "job_role": "Sales Lead",
        "manager_email": f"bilal.hassan@{EMAIL_DOMAIN}",
        "salary": 275000,
        "experience": 8,
        "qualification": "BS Business Administration",
        "marital_status": "single",
        "joining": date(2020, 10, 9),
        "group_name": "Manager",
    },
    {
        "email": f"haroon.saeed@{EMAIL_DOMAIN}",
        "first_name": "Haroon",
        "last_name": "Saeed",
        "phone": "03002220104",
        "badge_id": "SVC-204",
        "gender": "male",
        "dob": date(1994, 6, 16),
        "department": "Sales",
        "job_position": "Account Executive",
        "job_role": "Enterprise Sales",
        "manager_email": f"maham.javed@{EMAIL_DOMAIN}",
        "salary": 170000,
        "experience": 5,
        "qualification": "MBA Marketing",
        "marital_status": "married",
        "joining": date(2023, 1, 16),
        "group_name": None,
    },
    {
        "email": f"kashif.anwar@{EMAIL_DOMAIN}",
        "first_name": "Kashif",
        "last_name": "Anwar",
        "phone": "03002220105",
        "badge_id": "SVC-205",
        "gender": "male",
        "dob": date(1997, 1, 23),
        "department": "Sales",
        "job_position": "Sales Development Representative",
        "job_role": "Outbound Sales",
        "manager_email": f"maham.javed@{EMAIL_DOMAIN}",
        "salary": 120000,
        "experience": 2,
        "qualification": "BBA",
        "marital_status": "single",
        "joining": date(2024, 7, 1),
        "group_name": None,
    },
    {
        "email": f"imran.qureshi@{EMAIL_DOMAIN}",
        "first_name": "Imran",
        "last_name": "Qureshi",
        "phone": "03002220106",
        "badge_id": "SVC-206",
        "gender": "male",
        "dob": date(1987, 9, 16),
        "department": "Finance",
        "job_position": "Finance Manager",
        "job_role": "Financial Controller",
        "manager_email": f"bilal.hassan@{EMAIL_DOMAIN}",
        "salary": 340000,
        "experience": 13,
        "qualification": "ACCA",
        "marital_status": "married",
        "joining": date(2017, 5, 22),
        "group_name": "Manager",
    },
    {
        "email": f"mehwish.tariq@{EMAIL_DOMAIN}",
        "first_name": "Mehwish",
        "last_name": "Tariq",
        "phone": "03002220107",
        "badge_id": "SVC-207",
        "gender": "female",
        "dob": date(1998, 6, 5),
        "department": "Finance",
        "job_position": "Accountant",
        "job_role": "Accounts Payable",
        "manager_email": f"imran.qureshi@{EMAIL_DOMAIN}",
        "salary": 125000,
        "experience": 3,
        "qualification": "B.Com",
        "marital_status": "single",
        "joining": date(2024, 4, 1),
        "group_name": None,
    },
    {
        "email": f"nida.parveen@{EMAIL_DOMAIN}",
        "first_name": "Nida",
        "last_name": "Parveen",
        "phone": "03002220108",
        "badge_id": "SVC-208",
        "gender": "female",
        "dob": date(1996, 10, 3),
        "department": "Finance",
        "job_position": "Accountant",
        "job_role": "Accounts Payable",
        "manager_email": f"imran.qureshi@{EMAIL_DOMAIN}",
        "salary": 118000,
        "experience": 4,
        "qualification": "ACCA Affiliate",
        "marital_status": "single",
        "joining": date(2023, 9, 4),
        "group_name": None,
    },
    {
        "email": f"saad.farooq@{EMAIL_DOMAIN}",
        "first_name": "Saad",
        "last_name": "Farooq",
        "phone": "03002220109",
        "badge_id": "SVC-209",
        "gender": "male",
        "dob": date(1990, 3, 3),
        "department": "Operations",
        "job_position": "Operations Manager",
        "job_role": "Office Operations",
        "manager_email": f"bilal.hassan@{EMAIL_DOMAIN}",
        "salary": 230000,
        "experience": 9,
        "qualification": "MBA Operations",
        "marital_status": "married",
        "joining": date(2021, 2, 1),
        "group_name": "Manager",
    },
    {
        "email": f"zara.ahmed@{EMAIL_DOMAIN}",
        "first_name": "Zara",
        "last_name": "Ahmed",
        "phone": "03002220110",
        "badge_id": "SVC-210",
        "gender": "female",
        "dob": date(2000, 8, 18),
        "department": "Operations",
        "job_position": "Office Coordinator",
        "job_role": "Administration",
        "manager_email": f"saad.farooq@{EMAIL_DOMAIN}",
        "salary": 95000,
        "experience": 2,
        "qualification": "BA English",
        "marital_status": "single",
        "joining": date(2025, 1, 6),
        "group_name": None,
    },
    {
        "email": f"lubna.sheikh@{EMAIL_DOMAIN}",
        "first_name": "Lubna",
        "last_name": "Sheikh",
        "phone": "03002220111",
        "badge_id": "SVC-211",
        "gender": "female",
        "dob": date(1993, 11, 29),
        "department": "Sales",
        "job_position": "Account Executive",
        "job_role": "Enterprise Sales",
        "manager_email": f"maham.javed@{EMAIL_DOMAIN}",
        "salary": 165000,
        "experience": 6,
        "qualification": "MBA",
        "marital_status": "married",
        "joining": date(2022, 4, 5),
        "group_name": None,
    },
)


def _ensure_companies(result: SeederResult) -> dict[str, Company]:
    companies: dict[str, Company] = {}
    # Rebrand existing "My Company" into the HQ if present.
    legacy = Company.objects.filter(company="My Company").first()
    for spec in COMPANIES:
        lookup_name = spec["company"]
        company = Company.objects.filter(company=lookup_name).first()
        if company is None and legacy and spec["key"] == "tech":
            company = legacy
            company.company = lookup_name
        if company is None:
            company = Company.objects.create(
                company=lookup_name,
                address=spec["address"],
                country=spec["country"],
                state=spec["state"],
                city=spec["city"],
                zip=spec["zip"],
                hq=spec["hq"],
            )
            record(result, "created", "Company", company)
        else:
            changed = False
            for field in ("address", "country", "state", "city", "zip", "hq", "company"):
                value = spec[field] if field != "company" else lookup_name
                if getattr(company, field) != value:
                    setattr(company, field, value)
                    changed = True
            if changed:
                company.save()
                record(result, "updated", "Company", company)
            else:
                record(result, "existing", "Company", company)
        if spec["hq"]:
            Company.objects.exclude(pk=company.pk).filter(hq=True).update(hq=False)
        companies[spec["key"]] = company
    return companies


def _ensure_master(company: Company, result: SeederResult):
    work_type, status = upsert(WorkType, {"work_type": "Onsite"})
    if set_m2m(work_type, "company_id", [company]) == "updated" and status == "existing":
        status = "updated"
    record(result, status, "Work Type", f"{work_type} @ {company}")

    employee_type, status = upsert(EmployeeType, {"employee_type": "Full Time"})
    if set_m2m(employee_type, "company_id", [company]) == "updated" and status == "existing":
        status = "updated"
    record(result, status, "Employee Type", f"{employee_type} @ {company}")
    return work_type, employee_type


def _ensure_org(company: Company, needed_depts: set[str], result: SeederResult) -> dict:
    departments = {}
    positions = {}
    roles = {}
    for dept_name, jobs in ORG_SETUP.items():
        if dept_name not in needed_depts:
            continue
        dept, status = upsert(Department, {"department": dept_name})
        if set_m2m(dept, "company_id", [company]) == "updated" and status == "existing":
            status = "updated"
        record(result, status, "Department", f"{dept} @ {company}")
        departments[dept_name] = dept
        for position_name, role_names in jobs.items():
            job, status = upsert(
                JobPosition,
                {"department_id": dept, "job_position": position_name},
            )
            if set_m2m(job, "company_id", [company]) == "updated" and status == "existing":
                status = "updated"
            record(result, status, "Job Position", f"{job} @ {company}")
            positions[position_name] = job
            for role_name in role_names:
                role, role_status = upsert(
                    JobRole,
                    {"job_position_id": job, "job_role": role_name},
                )
                if (
                    set_m2m(role, "company_id", [company]) == "updated"
                    and role_status == "existing"
                ):
                    role_status = "updated"
                record(result, role_status, "Job Role", f"{role} @ {company}")
                roles[(position_name, role_name)] = role
    return {"departments": departments, "positions": positions, "roles": roles}


def _ensure_person(person: dict, city: str, state: str, result: SeederResult) -> Employee:
    user = HorillaUser.objects.filter(username=person["email"]).first()
    if user is None:
        user = HorillaUser.objects.create_user(
            username=person["email"],
            email=person["email"],
            password=DEFAULT_PASSWORD,
            first_name=person["first_name"],
            last_name=person["last_name"],
            is_superuser=False,
            is_staff=False,
        )
        record(result, "created", "User", user)
    else:
        user.set_password(DEFAULT_PASSWORD)
        user.first_name = person["first_name"]
        user.last_name = person["last_name"]
        user.email = person["email"]
        user.is_active = True
        user.save()
        record(result, "updated", "User", user)

    employee = Employee.objects.filter(email=person["email"]).first()
    fields = {
        "employee_user_id": user,
        "employee_first_name": person["first_name"],
        "employee_last_name": person["last_name"],
        "phone": person["phone"],
        "badge_id": person["badge_id"],
        "gender": person["gender"],
        "dob": person["dob"],
        "city": city,
        "country": "Pakistan",
        "state": state,
        "address": f"{city}, Pakistan",
        "qualification": person["qualification"],
        "experience": person["experience"],
        "marital_status": person["marital_status"],
        "is_active": True,
    }
    if employee is None:
        employee = Employee(email=person["email"], **fields)
        employee.save()
        record(result, "created", "Employee", employee)
    else:
        for key, value in fields.items():
            setattr(employee, key, value)
        employee.save()
        record(result, "updated", "Employee", employee)
    return employee


def _assign_group(user, company, group_name, result):
    if not group_name:
        return
    group = Group.objects.filter(name=group_name).first()
    if not group:
        record(result, "existing", "Company role skipped", f"{group_name} missing")
        return
    _, created = CompanyGroupAssignment.objects.get_or_create(
        user=user, company=company, group=group
    )
    CompanyGroupAssignment.sync_user_group_membership(user, group)
    record(
        result,
        "created" if created else "existing",
        "Company role",
        f"{user.username} -> {group_name} @ {company}",
    )


def _seed_people(company, people, city, state, org, work_type, employee_type, result):
    by_email = {}
    for person in people:
        by_email[person["email"]] = _ensure_person(person, city, state, result)

    for person in people:
        employee = by_email[person["email"]]
        manager = by_email.get(person["manager_email"]) if person["manager_email"] else None
        work_info, created = EmployeeWorkInformation.objects.get_or_create(
            employee_id=employee
        )
        work_info.company_id = company
        work_info.department_id = org["departments"][person["department"]]
        work_info.job_position_id = org["positions"][person["job_position"]]
        work_info.job_role_id = org["roles"][(person["job_position"], person["job_role"])]
        work_info.work_type_id = work_type
        work_info.employee_type_id = employee_type
        work_info.reporting_manager_id = manager
        work_info.date_joining = person["joining"]
        work_info.email = person["email"]
        work_info.mobile = person["phone"]
        work_info.location = f"{city} Office"
        work_info.basic_salary = person["salary"]
        work_info.experience = float(person["experience"])
        work_info.save()
        record(
            result,
            "created" if created else "updated",
            "Work Information",
            f"{employee} -> {person['job_position']}",
        )
        _assign_group(
            employee.employee_user_id, company, person.get("group_name"), result
        )
    return by_email


def _seed_contracts(employees_by_email: dict, people, result: SeederResult):
    try:
        from payroll.models.models import Contract
    except Exception:
        record(result, "existing", "Contracts skipped", "payroll unavailable")
        return

    for person in people:
        employee = employees_by_email[person["email"]]
        contract = (
            Contract.objects.filter(employee_id=employee, contract_status="active")
            .order_by("pk")
            .first()
            or Contract.objects.filter(employee_id=employee).order_by("pk").first()
        )
        defaults = {
            "contract_name": f"{person['job_position']} Contract",
            "contract_start_date": person["joining"],
            "wage_type": "monthly",
            "pay_frequency": "monthly",
            "wage": float(person["salary"]),
            "contract_status": "active",
        }
        if contract is None:
            contract = Contract(employee_id=employee, **defaults)
            contract.save()
            record(result, "created", "Contract", contract)
        else:
            changed = False
            for field, value in defaults.items():
                if getattr(contract, field) != value:
                    setattr(contract, field, value)
                    changed = True
            if changed:
                contract.save()
                record(result, "updated", "Contract", contract)
            else:
                record(result, "existing", "Contract", contract)


def _seed_attendance(employees_by_email: dict, company: Company, result: SeederResult):
    try:
        from attendance.models import Attendance, WorkRecords
        from base.models import EmployeeShift, EmployeeShiftDay
    except Exception:
        record(result, "existing", "Attendance skipped", "attendance unavailable")
        return

    shift, _ = upsert(
        EmployeeShift,
        {"employee_shift": "Regular Day"},
        {"weekly_full_time": "40:00", "full_time": "08:00"},
    )
    set_m2m(shift, "company_id", [company])
    today = timezone.localdate()
    count = 0
    for employee in employees_by_email.values():
        for offset in range(1, 11):
            day = today - timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            day_name = day.strftime("%A").lower()
            shift_day, _ = upsert(EmployeeShiftDay, {"day": day_name})
            set_m2m(shift_day, "company_id", [company])
            clock_in = time(9, 0 if count % 3 else 12)
            clock_out = time(18, 0)
            worked = 8 * 3600 if clock_in.minute == 0 else 7 * 3600 + 48 * 60
            attendance, status = upsert(
                Attendance,
                {"employee_id": employee, "attendance_date": day},
                {
                    "shift_id": shift,
                    "attendance_day": shift_day,
                    "attendance_clock_in_date": day,
                    "attendance_clock_in": clock_in,
                    "attendance_clock_out_date": day,
                    "attendance_clock_out": clock_out,
                    "minimum_hour": "08:00",
                    "attendance_worked_hour": "08:00" if clock_in.minute == 0 else "07:48",
                    "at_work_second": worked,
                    "attendance_overtime": "00:00",
                    "attendance_validated": True,
                    "is_holiday": False,
                },
            )
            if status == "created":
                count += 1
            upsert(
                WorkRecords,
                {"employee_id": employee, "date": day},
                {
                    "record_name": "Present",
                    "work_record_type": "FDP",
                    "at_work": "08:00",
                    "min_hour": "08:00",
                    "at_work_second": worked,
                    "min_hour_second": 8 * 3600,
                    "is_attendance_record": True,
                    "attendance_id": attendance,
                    "shift_id": shift,
                    "day_percentage": 1.0,
                },
            )
    record(result, "created", "Attendance days seeded", f"{count} new rows @ {company}")


def _seed_leave_balances(employees_by_email: dict, company: Company, result: SeederResult):
    try:
        from leave.models import AvailableLeave, LeaveType
    except Exception:
        record(result, "existing", "Leave skipped", "leave unavailable")
        return

    leave_specs = (
        ("Annual Leave", 14, 4),
        ("Casual Leave", 10, 2),
        ("Sick Leave", 8, 1),
    )
    for name, total, used in leave_specs:
        leave_type, status = upsert(
            LeaveType,
            {"name": name, "company_id": company},
            {
                "payment": "paid",
                "count": 1,
                "total_days": total,
                "limit_leave": True,
                "reset": True,
                "reset_based": "yearly",
                "reset_month": "1",
                "reset_day": "1",
            },
        )
        record(result, status, "Leave Type", f"{leave_type} @ {company}")
        for employee in employees_by_email.values():
            upsert(
                AvailableLeave,
                {"employee_id": employee, "leave_type_id": leave_type},
                {
                    "available_days": float(total - used),
                    "carryforward_days": 0,
                    "total_leave_days": float(total),
                },
            )


def _backfill_history(employees_by_email: dict, result: SeederResult):
    from base.models import JobPosition
    from horilla_views.history_methods import get_diff

    seeded = 0
    for index, employee in enumerate(employees_by_email.values()):
        work_info = EmployeeWorkInformation.objects.filter(employee_id=employee).first()
        if not work_info or get_diff(work_info, "history_set"):
            continue
        original_salary = work_info.basic_salary or 0
        original_job = work_info.job_position_id_id
        starting = max(int(original_salary * 0.75), 1)
        mid = max(int(original_salary * 0.9), starting)
        alt_job = None
        if index % 2 == 0 and work_info.department_id_id:
            alt_job = (
                JobPosition.objects.filter(department_id=work_info.department_id_id)
                .exclude(pk=original_job)
                .order_by("id")
                .values_list("id", flat=True)
                .first()
            )
        work_info.basic_salary = starting
        if alt_job:
            work_info.job_position_id_id = alt_job
        work_info.save()
        work_info.basic_salary = mid
        work_info.save()
        work_info.basic_salary = original_salary
        if alt_job:
            work_info.job_position_id_id = original_job
        work_info.save()
        seeded += 1
    record(result, "created", "Work history backfill", f"{seeded} employees")


def _grant_haris_access(companies: dict[str, Company], result: SeederResult):
    user = HorillaUser.objects.filter(username="haris").first()
    if not user:
        return
    admin_group = Group.objects.filter(name="Admin").first()
    if not admin_group:
        return
    for company in companies.values():
        _, created = CompanyGroupAssignment.objects.get_or_create(
            user=user, company=company, group=admin_group
        )
        CompanyGroupAssignment.sync_user_group_membership(user, admin_group)
        record(
            result,
            "created" if created else "existing",
            "Haris admin access",
            company,
        )
    # Keep Haris work info on HQ tech company if present.
    employee = getattr(user, "employee_get", None)
    if employee:
        work_info = EmployeeWorkInformation.objects.filter(employee_id=employee).first()
        tech = companies.get("tech")
        if work_info and tech:
            work_info.company_id = tech
            work_info.save(update_fields=["company_id"])


@transaction.atomic
def seed() -> SeederResult:
    result = SeederResult()
    companies = _ensure_companies(result)

    tech = companies["tech"]
    services = companies["services"]

    tech_depts = {
        "Executive Office",
        "Human Resources",
        "Engineering",
        "Information Technology",
    }
    services_depts = {
        "Executive Office",
        "Human Resources",
        "Sales",
        "Finance",
        "Operations",
    }

    tech_wt, tech_et = _ensure_master(tech, result)
    svc_wt, svc_et = _ensure_master(services, result)
    tech_org = _ensure_org(tech, tech_depts, result)
    svc_org = _ensure_org(services, services_depts, result)

    tech_people = _seed_people(
        tech, TECH_PEOPLE, "Karachi", "Sindh", tech_org, tech_wt, tech_et, result
    )
    svc_people = _seed_people(
        services,
        SERVICES_PEOPLE,
        "Lahore",
        "Punjab",
        svc_org,
        svc_wt,
        svc_et,
        result,
    )

    _seed_contracts(tech_people, TECH_PEOPLE, result)
    _seed_contracts(svc_people, SERVICES_PEOPLE, result)
    _seed_attendance(tech_people, tech, result)
    _seed_attendance(svc_people, services, result)
    _seed_leave_balances(tech_people, tech, result)
    _seed_leave_balances(svc_people, services, result)
    _backfill_history(tech_people, result)
    _backfill_history(svc_people, result)
    _grant_haris_access(companies, result)

    result.add(
        "created",
        f"Pakistan org ready. Password for seeded users: {DEFAULT_PASSWORD}. "
        f"Companies: {tech.company}, {services.company}.",
    )
    return result
