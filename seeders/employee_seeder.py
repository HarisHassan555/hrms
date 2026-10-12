from __future__ import annotations

from base.models import EmployeeType, WorkType

from .organization_seeder import get_seed_companies
from .utils import SeederResult, record, set_m2m, upsert


WORK_TYPES = ["Onsite", "Remote", "Hybrid"]
EMPLOYEE_TYPES = ["Full Time", "Part Time", "Contract", "Intern"]


def seed() -> SeederResult:
    result = SeederResult()
    companies = get_seed_companies()

    for name in WORK_TYPES:
        work_type, status = upsert(WorkType, {"work_type": name})
        m2m_status = set_m2m(work_type, "company_id", companies)
        if status == "existing" and m2m_status == "updated":
            status = "updated"
        record(result, status, "Work Type", work_type)

    for name in EMPLOYEE_TYPES:
        employee_type, status = upsert(EmployeeType, {"employee_type": name})
        m2m_status = set_m2m(employee_type, "company_id", companies)
        if status == "existing" and m2m_status == "updated":
            status = "updated"
        record(result, status, "Employee Type", employee_type)

    return result
