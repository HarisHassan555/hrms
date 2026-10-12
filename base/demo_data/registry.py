"""Module-wise demo data seed registry.

The functions here reuse the existing enterprise demo backfills, but expose
them in smaller module groups so an operator can top up one area without
running a full fixture reload.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from django.apps import apps
from django.conf import settings


SeedResult = dict[str, object]
SeedRunner = Callable[[date, Path], SeedResult]


@dataclass(frozen=True)
class DemoSeedModule:
    slug: str
    label: str
    description: str
    models: tuple[tuple[str, str], ...]
    runner: SeedRunner


def _seed_base(today: date, root: Path) -> SeedResult:
    from base.demo_data.companies import ensure_companies
    from base.demo_data.media import copy_demo_media
    from base.demo_data.modules.announcements import refresh_announcements
    from base.demo_data.modules.date_clamp import clamp_demo_dates
    from base.demo_data.modules.request_windows import backfill_request_windows
    from base.demo_data.org import (
        differentiate_org_taxonomy_by_company,
        standardize_org_taxonomy,
    )
    from base.demo_data.sanitize import sanitize_loaded_records, scrub_side_fixture_files

    result: SeedResult = {}
    result["media"] = copy_demo_media(root)
    result["side_fixtures"] = scrub_side_fixture_files(root)
    result["companies"] = ensure_companies()
    result["org"] = standardize_org_taxonomy()
    result["org_differentiation"] = differentiate_org_taxonomy_by_company()
    result["announcements"] = refresh_announcements(today)
    result["request_windows"] = backfill_request_windows(today)
    result["sanitized"] = sanitize_loaded_records()
    result["date_clamp"] = clamp_demo_dates(today)
    return result


def _seed_employee(today: date, root: Path) -> SeedResult:
    from base.demo_data.modules.employee_features import (
        backfill_employee_feature_coverage,
    )
    from base.demo_data.modules.employee_lifecycle import backfill_employee_lifecycle
    from base.demo_data.modules.employee_work_history import (
        backfill_employee_work_info_history,
    )

    lifecycle = backfill_employee_lifecycle(today, root)
    return {
        "employee_lifecycle": lifecycle,
        "employee_feature_coverage": backfill_employee_feature_coverage(today),
        "employee_work_info_history": backfill_employee_work_info_history(today),
    }


def _seed_attendance(today: date, root: Path) -> SeedResult:
    from base.demo_data.modules.attendance_trend import (
        backfill_attendance_activities,
        backfill_attendance_density,
        backfill_attendance_overtime,
        backfill_attendance_spread,
        backfill_pending_validation_today,
        backfill_zero_coverage_attendance,
        reconcile_attendance_with_leave,
    )

    return {
        "attendance_backfill": backfill_attendance_spread(today),
        "attendance_overtime_backfill": backfill_attendance_overtime(today),
        "attendance_zero_coverage_backfill": backfill_zero_coverage_attendance(today),
        "attendance_density_backfill": backfill_attendance_density(today),
        "attendance_leave_reconcile": reconcile_attendance_with_leave(today),
        "attendance_activities": backfill_attendance_activities(today),
        "attendance_pending_validation": backfill_pending_validation_today(today),
    }


def _seed_leave(today: date, root: Path) -> SeedResult:
    from base.demo_data.modules.leave_trend import (
        backfill_leave_spread,
        backfill_zero_coverage_available_leave,
    )

    return {
        "leave_backfill": backfill_leave_spread(today),
        "leave_zero_coverage_backfill": backfill_zero_coverage_available_leave(today),
    }


def _seed_recruitment(today: date, root: Path) -> SeedResult:
    from base.demo_data.modules.recruitment import seed_recruitment_catalog
    from base.demo_data.modules.recruitment_expansion import (
        backfill_company_recruitment_pipelines,
    )
    from base.demo_data.modules.recruitment_features import (
        backfill_candidate_offer_status,
        backfill_candidate_source,
        backfill_recruitment_job_position,
        backfill_rejected_candidates,
    )

    return {
        "recruitment": seed_recruitment_catalog(),
        "recruitment_company_pipelines": backfill_company_recruitment_pipelines(today),
        "recruitment_rejected_candidates": backfill_rejected_candidates(today),
        "recruitment_candidate_source": backfill_candidate_source(today),
        "recruitment_job_position": backfill_recruitment_job_position(today),
        "recruitment_offer_status": backfill_candidate_offer_status(today),
    }


def _seed_payroll(today: date, root: Path) -> SeedResult:
    from base.demo_data.modules.payroll_features import (
        backfill_payroll_feature_coverage,
    )
    from base.demo_data.modules.payroll_trend import backfill_payroll_coverage

    return {
        "payroll_feature_coverage": backfill_payroll_feature_coverage(today),
        "payroll_coverage_backfill": backfill_payroll_coverage(today),
    }


def _seed_asset(today: date, root: Path) -> SeedResult:
    from base.demo_data.modules.asset_expansion import backfill_company_asset_pools
    from base.demo_data.modules.asset_features import backfill_asset_reports

    return {
        "asset_company_pools": backfill_company_asset_pools(today),
        "asset_reports": backfill_asset_reports(today),
    }


def _seed_project(today: date, root: Path) -> SeedResult:
    from base.demo_data.modules.project_trend import (
        backfill_project_trend,
        reanchor_project_scenarios,
    )

    return {
        "project_backfill": backfill_project_trend(today),
        "project_scenarios_reanchor": reanchor_project_scenarios(today),
    }


def _seed_pms(today: date, root: Path) -> SeedResult:
    from base.demo_data.modules.pms_trend import (
        backfill_pms_coverage,
        backfill_pms_objectives,
    )

    return {
        "pms_coverage_backfill": backfill_pms_coverage(today),
        "pms_backfill": backfill_pms_objectives(today),
    }


def _seed_onboarding(today: date, root: Path) -> SeedResult:
    from base.demo_data.modules.onboarding_trend import backfill_onboarding_pipeline

    return {"onboarding_backfill": backfill_onboarding_pipeline(today)}


def _seed_offboarding(today: date, root: Path) -> SeedResult:
    from base.demo_data.modules.employee_lifecycle import backfill_employee_lifecycle
    from base.demo_data.modules.offboarding_expansion import (
        backfill_company_offboarding_pipelines,
    )
    from base.demo_data.modules.offboarding_trend import backfill_offboarding_letters

    lifecycle = backfill_employee_lifecycle(today, root)
    return {
        "employee_lifecycle": lifecycle,
        "offboarding_backfill": backfill_offboarding_letters(
            today, lifecycle.get("exit_employee_ids")
        ),
        "offboarding_company_pipelines": backfill_company_offboarding_pipelines(today),
    }


def _seed_helpdesk(today: date, root: Path) -> SeedResult:
    from base.demo_data.modules.helpdesk_expansion import (
        backfill_company_helpdesk_lookups,
    )
    from base.demo_data.modules.helpdesk_trend import (
        backfill_helpdesk_tickets,
        reanchor_helpdesk_scenarios,
    )

    return {
        "helpdesk_company_lookups": backfill_company_helpdesk_lookups(today),
        "helpdesk_backfill": backfill_helpdesk_tickets(today),
        "helpdesk_scenarios_reanchor": reanchor_helpdesk_scenarios(today),
    }


DEMO_SEED_MODULES: tuple[DemoSeedModule, ...] = (
    DemoSeedModule(
        "base",
        "Base",
        "Companies, org taxonomy, announcements, shared settings, and cleanup.",
        (("base", "Company"), ("base", "Department"), ("base", "JobPosition")),
        _seed_base,
    ),
    DemoSeedModule(
        "employee",
        "Employee",
        "Employee lifecycle, feature coverage, and work information history.",
        (("employee", "Employee"), ("employee", "EmployeeWorkInformation")),
        _seed_employee,
    ),
    DemoSeedModule(
        "attendance",
        "Attendance",
        "Attendance spread, overtime, activity, and pending validation records.",
        (("attendance", "Attendance"), ("attendance", "AttendanceActivity")),
        _seed_attendance,
    ),
    DemoSeedModule(
        "leave",
        "Leave",
        "Leave requests and available leave coverage.",
        (("leave", "LeaveRequest"), ("leave", "AvailableLeave")),
        _seed_leave,
    ),
    DemoSeedModule(
        "recruitment",
        "Recruitment",
        "Recruitment catalog, pipelines, candidates, sources, and offer status.",
        (("recruitment", "Recruitment"), ("recruitment", "Candidate")),
        _seed_recruitment,
    ),
    DemoSeedModule(
        "payroll",
        "Payroll",
        "Payroll feature coverage and payslip trend records.",
        (("payroll", "Payslip"), ("payroll", "Contract")),
        _seed_payroll,
    ),
    DemoSeedModule(
        "asset",
        "Asset",
        "Asset pools, assignments, requests, and report coverage.",
        (("asset", "Asset"), ("asset", "AssetRequest")),
        _seed_asset,
    ),
    DemoSeedModule(
        "project",
        "Project",
        "Project trend and scenario dates.",
        (("project", "Project"), ("project", "Task")),
        _seed_project,
    ),
    DemoSeedModule(
        "pms",
        "PMS",
        "Objectives, key results, and PMS trend coverage.",
        (("pms", "Objective"), ("pms", "EmployeeObjective")),
        _seed_pms,
    ),
    DemoSeedModule(
        "onboarding",
        "Onboarding",
        "Onboarding pipeline trend coverage.",
        (("onboarding", "OnboardingStage"), ("onboarding", "OnboardingCandidate")),
        _seed_onboarding,
    ),
    DemoSeedModule(
        "offboarding",
        "Offboarding",
        "Exit employees, resignation letters, and offboarding pipelines.",
        (("offboarding", "Offboarding"), ("offboarding", "ResignationLetter")),
        _seed_offboarding,
    ),
    DemoSeedModule(
        "helpdesk",
        "Helpdesk",
        "Helpdesk lookup data, tickets, and trend scenarios.",
        (("helpdesk", "Ticket"), ("helpdesk", "TicketType")),
        _seed_helpdesk,
    ),
)

_MODULES_BY_SLUG = {module.slug: module for module in DEMO_SEED_MODULES}


def get_demo_seed_module(slug: str) -> DemoSeedModule:
    try:
        return _MODULES_BY_SLUG[slug]
    except KeyError as exc:
        raise ValueError(f"Unknown demo seed module: {slug}") from exc


def count_seed_module_rows(module: DemoSeedModule) -> int:
    total = 0
    for app_label, model_name in module.models:
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            continue
        total += model._default_manager.count()
    return total


def module_cards() -> list[dict[str, object]]:
    return [
        {
            "slug": module.slug,
            "label": module.label,
            "description": module.description,
            "rows": count_seed_module_rows(module),
        }
        for module in DEMO_SEED_MODULES
    ]


def run_demo_seed_module(slug: str, *, today: date | None = None) -> SeedResult:
    today = today or date.today()
    root = Path(settings.BASE_DIR) / "load_data"

    if slug == "all":
        return {
            module.slug: module.runner(today, root)
            for module in DEMO_SEED_MODULES
        }

    module = get_demo_seed_module(slug)
    return module.runner(today, root)
