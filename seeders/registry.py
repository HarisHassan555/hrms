from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable

from . import admin_team_seeder, asset_seeder, attendance_seeder, employee_seeder, leave_seeder
from . import (
    organization_seeder,
    pakistan_attendance_leave_seeder,
    pakistan_helpdesk_seeder,
    pakistan_org_seeder,
    pakistan_payroll_seeder,
    pakistan_pms_seeder,
    pakistan_profile_seeder,
    pakistan_project_seeder,
    pakistan_recruitment_seeder,
    qarshi_seeder,
)
from .utils import SeederResult


SeederCallable = Callable[[], SeederResult]


@dataclass(frozen=True)
class Seeder:
    slug: str
    label: str
    runner: SeederCallable


SEEDERS = OrderedDict(
    (
        (
            "organization",
            Seeder("organization", "Organization", organization_seeder.seed),
        ),
        ("employee", Seeder("employee", "Employee", employee_seeder.seed)),
        ("attendance", Seeder("attendance", "Attendance", attendance_seeder.seed)),
        ("leave", Seeder("leave", "Leave", leave_seeder.seed)),
        ("asset", Seeder("asset", "Asset", asset_seeder.seed)),
        (
            "qarshi",
            Seeder(
                "qarshi",
                "Qarshi Industries (company + 4 users)",
                qarshi_seeder.seed,
            ),
        ),
        (
            "pakistan_org",
            Seeder(
                "pakistan_org",
                "DataSphere Global PK — 2 companies, org charts, history",
                pakistan_org_seeder.seed,
            ),
        ),
        (
            "pakistan_recruitment",
            Seeder(
                "pakistan_recruitment",
                "DSG PK recruitment jobs, candidates, onboarding, conversions",
                pakistan_recruitment_seeder.seed,
            ),
        ),
        (
            "pakistan_profiles",
            Seeder(
                "pakistan_profiles",
                "Complete employee profiles — shifts, bank, contracts, perks",
                pakistan_profile_seeder.seed,
            ),
        ),
        (
            "pakistan_projects",
            Seeder(
                "pakistan_projects",
                "DSG PK projects, tasks, timesheets + visibility scenarios",
                pakistan_project_seeder.seed,
            ),
        ),
        (
            "pakistan_pms",
            Seeder(
                "pakistan_pms",
                "DSG PK performance — OKRs, feedback, meetings, bonus",
                pakistan_pms_seeder.seed,
            ),
        ),
        (
            "pakistan_helpdesk",
            Seeder(
                "pakistan_helpdesk",
                "DSG PK tickets, types, dept managers, FAQs, claims",
                pakistan_helpdesk_seeder.seed,
            ),
        ),
        (
            "pakistan_attendance_leave",
            Seeder(
                "pakistan_attendance_leave",
                "DSG PK attendance history + leave requests & balances",
                pakistan_attendance_leave_seeder.seed,
            ),
        ),
        (
            "pakistan_payroll",
            Seeder(
                "pakistan_payroll",
                "DSG PK payroll master data, PKR, tax, payslips",
                pakistan_payroll_seeder.seed,
            ),
        ),
        (
            "admin_team",
            Seeder(
                "admin_team",
                "20 Admin employees + org, shifts, leave master data",
                admin_team_seeder.seed,
            ),
        ),
    )
)


def get_seeders(module: str | None = None) -> list[Seeder]:
    if module is None:
        return list(SEEDERS.values())
    try:
        return [SEEDERS[module]]
    except KeyError as exc:
        choices = ", ".join(SEEDERS.keys())
        raise ValueError(
            f"Unknown seed module '{module}'. Available modules: {choices}"
        ) from exc
