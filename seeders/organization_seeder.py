from __future__ import annotations

from base.models import Company, Department, JobPosition, JobRole

from .utils import SeederResult, record, set_m2m, upsert


DEFAULT_COMPANY = {
    "company": "Default Company",
    "address": "Default Address",
    "country": "United States",
    "state": "Default State",
    "city": "Default City",
    "zip": "00000",
    "hq": True,
}

DEPARTMENTS = ["Administration", "Human Resources", "Information Technology"]

JOB_POSITIONS = [
    {
        "department": "Administration",
        "job_position": "Administrator",
        "roles": ["System Administrator"],
    },
    {
        "department": "Human Resources",
        "job_position": "HR Manager",
        "roles": ["HR Operations"],
    },
    {
        "department": "Information Technology",
        "job_position": "Software Engineer",
        "roles": ["Backend Engineer", "Frontend Engineer"],
    },
]


def get_seed_companies() -> list[Company]:
    companies = list(Company.objects.order_by("pk"))
    if companies:
        return companies
    company_lookup = {
        "company": DEFAULT_COMPANY["company"],
        "address": DEFAULT_COMPANY["address"],
    }
    company_defaults = {
        key: value
        for key, value in DEFAULT_COMPANY.items()
        if key not in company_lookup
    }
    company, _status = upsert(Company, company_lookup, company_defaults)
    return [company]


def seed() -> SeederResult:
    result = SeederResult()

    had_companies = Company.objects.exists()
    companies = get_seed_companies()
    for company in companies:
        record(result, "existing" if had_companies else "created", "Company", company)

    departments = {}
    for department_name in DEPARTMENTS:
        department, status = upsert(Department, {"department": department_name})
        m2m_status = set_m2m(department, "company_id", companies)
        if status == "existing" and m2m_status == "updated":
            status = "updated"
        record(result, status, "Department", department)
        departments[department_name] = department

    for item in JOB_POSITIONS:
        department = departments[item["department"]]
        job_position, status = upsert(
            JobPosition,
            {
                "department_id": department,
                "job_position": item["job_position"],
            },
        )
        m2m_status = set_m2m(job_position, "company_id", companies)
        if status == "existing" and m2m_status == "updated":
            status = "updated"
        record(result, status, "Job Position", job_position)

        for role_name in item["roles"]:
            job_role, role_status = upsert(
                JobRole,
                {
                    "job_position_id": job_position,
                    "job_role": role_name,
                },
            )
            role_m2m_status = set_m2m(job_role, "company_id", companies)
            if role_status == "existing" and role_m2m_status == "updated":
                role_status = "updated"
            record(result, role_status, "Job Role", job_role)

    return result
