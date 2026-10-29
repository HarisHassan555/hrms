"""
Populate Project module for DataSphere Global PK.

Creates projects, stages, tasks, and timesheets that exercise:
- project manager assignment
- task manager / member assignment
- peer isolation (Ali vs Fatima)
- reporting-manager visibility (Zain over Engineering)
- company-wide view_* via Admin (Kamran)

Password for seeded users remains ``1212``.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.db import transaction

from base.models import Company
from employee.models import Employee
from project.models import Project, ProjectStage, Task, TimeSheet

from .utils import SeederResult, record, set_m2m, upsert

TODAY = date.today()


def _emp(email: str) -> Employee:
    return Employee.objects.get(email=email)


def _ensure_stages(result: SeederResult, project: Project) -> dict[str, ProjectStage]:
    """Ensure Todo / In Progress / Done stages exist; Project.save creates Todo."""
    titles = (
        ("Todo", 1, False),
        ("In Progress", 2, False),
        ("Done", 3, True),
    )
    stages: dict[str, ProjectStage] = {}
    for title, sequence, is_end in titles:
        stage, status = upsert(
            ProjectStage,
            {"project": project, "title": title},
            {"sequence": sequence, "is_end_stage": is_end},
        )
        stages[title] = stage
        record(result, status, "Stage", f"{project.title}/{title}")
    return stages


def _task(
    result: SeederResult,
    *,
    project: Project,
    stage: ProjectStage,
    title: str,
    description: str,
    status: str,
    start: date,
    end: date | None,
    hours: str,
    managers: list[Employee],
    members: list[Employee],
) -> Task:
    task, st = upsert(
        Task,
        {"project": project, "title": title},
        {
            "stage": stage,
            "description": description,
            "status": status,
            "start_date": start,
            "end_date": end,
            "allocated_hours": hours,
        },
    )
    record(result, st, "Task", title)
    if managers:
        set_m2m(task, "task_managers", managers)
    if members:
        set_m2m(task, "task_members", members)
    return task


def _timesheet(
    result: SeederResult,
    *,
    project: Project,
    task: Task,
    employee: Employee,
    day: date,
    hours: str,
    status: str,
    description: str,
) -> TimeSheet:
    ts, st = upsert(
        TimeSheet,
        {
            "project_id": project,
            "task_id": task,
            "employee_id": employee,
            "date": day,
        },
        {
            "time_spent": hours,
            "status": status,
            "description": description,
        },
    )
    record(
        result,
        st,
        "Timesheet",
        f"{employee.get_full_name()} {day} / {task.title}",
    )
    return ts


@transaction.atomic
def seed() -> SeederResult:
    result = SeederResult()
    company = Company.objects.filter(company="DSG Technologies").first()
    if not company:
        result.add("existing", "DSG Technologies company missing — run pakistan_org first")
        return result

    zain = _emp("zain.abbas@dsg.pk")
    ali = _emp("ali.raza@dsg.pk")
    fatima = _emp("fatima.noor@dsg.pk")
    farah = _emp("farah.aziz@dsg.pk")
    sana = _emp("sana.iqbal@dsg.pk")
    rehan = _emp("rehan.malik@dsg.pk")
    kamran = _emp("kamran.shah@dsg.pk")
    hamza = _emp("hamza.sheikh@dsg.pk")
    rabia = _emp("rabia.yousaf@dsg.pk")
    saad = _emp("saad.farooq@dsg.pk")
    zara = _emp("zara.ahmed@dsg.pk")

    # --- Project 1: HRMS Platform (Engineering) ---
    p1, st = upsert(
        Project,
        {"title": "DSG HRMS Platform"},
        {
            "status": "in_progress",
            "start_date": TODAY - timedelta(days=45),
            "end_date": TODAY + timedelta(days=90),
            "description": (
                "Core Horilla HRMS product build — payroll, attendance, "
                "recruitment, and employee self-service for DSG Technologies."
            ),
            "company_id": company,
        },
    )
    record(result, st, "Project", p1)
    set_m2m(p1, "managers", [zain, kamran])
    s1 = _ensure_stages(result, p1)

    t_api = _task(
        result,
        project=p1,
        stage=s1["In Progress"],
        title="Payroll API hardening",
        description="Harden payslip PDF generation and payroll calculation endpoints.",
        status="in_progress",
        start=TODAY - timedelta(days=14),
        end=TODAY + timedelta(days=21),
        hours="40:00",
        managers=[zain],
        members=[ali],
    )
    t_ui = _task(
        result,
        project=p1,
        stage=s1["In Progress"],
        title="Employee self-service UI",
        description="Polish employee profile and leave request screens.",
        status="in_progress",
        start=TODAY - timedelta(days=10),
        end=TODAY + timedelta(days=30),
        hours="32:00",
        managers=[zain],
        members=[fatima, farah],
    )
    t_qa = _task(
        result,
        project=p1,
        stage=s1["Todo"],
        title="Regression suite — attendance",
        description="Automate attendance edge cases for shift and overtime.",
        status="to_do",
        start=TODAY,
        end=TODAY + timedelta(days=45),
        hours="24:00",
        managers=[fatima],
        members=[sana],
    )
    t_devops = _task(
        result,
        project=p1,
        stage=s1["Done"],
        title="Staging CI pipeline",
        description="Docker compose CI for staging deploys.",
        status="completed",
        start=TODAY - timedelta(days=40),
        end=TODAY - timedelta(days=5),
        hours="16:00",
        managers=[zain],
        members=[rehan],
    )

    # Ali-only work (Fatima must not see via membership)
    t_ali_private = _task(
        result,
        project=p1,
        stage=s1["In Progress"],
        title="Ali — leave balance cache",
        description="Private backend task assigned only to Ali Raza.",
        status="in_progress",
        start=TODAY - timedelta(days=3),
        end=TODAY + timedelta(days=10),
        hours="12:00",
        managers=[ali],
        members=[ali],
    )
    # Fatima-only work (Ali must not see via membership)
    t_fatima_private = _task(
        result,
        project=p1,
        stage=s1["Todo"],
        title="Fatima — performance review form",
        description="Private frontend task assigned only to Fatima Noor.",
        status="to_do",
        start=TODAY,
        end=TODAY + timedelta(days=14),
        hours="20:00",
        managers=[fatima],
        members=[fatima],
    )

    for day_offset, hours, desc in (
        (1, "04:00", "Payslip PDF edge cases"),
        (2, "06:30", "Contract end-date fix"),
        (5, "03:00", "Leave balance cache spike"),
    ):
        _timesheet(
            result,
            project=p1,
            task=t_api if day_offset != 5 else t_ali_private,
            employee=ali,
            day=TODAY - timedelta(days=day_offset),
            hours=hours,
            status="completed" if day_offset > 2 else "in_Progress",
            description=desc,
        )

    for day_offset, hours, desc in (
        (1, "05:00", "Profile polish"),
        (3, "04:30", "Leave request UX"),
        (4, "02:00", "Performance form wireframe"),
    ):
        _timesheet(
            result,
            project=p1,
            task=t_ui if day_offset != 4 else t_fatima_private,
            employee=fatima,
            day=TODAY - timedelta(days=day_offset),
            hours=hours,
            status="completed" if day_offset > 2 else "in_Progress",
            description=desc,
        )

    _timesheet(
        result,
        project=p1,
        task=t_ui,
        employee=farah,
        day=TODAY - timedelta(days=2),
        hours="07:00",
        status="in_Progress",
        description="React component cleanup",
    )
    _timesheet(
        result,
        project=p1,
        task=t_qa,
        employee=sana,
        day=TODAY - timedelta(days=1),
        hours="03:30",
        status="in_Progress",
        description="Attendance test cases",
    )
    _timesheet(
        result,
        project=p1,
        task=t_devops,
        employee=rehan,
        day=TODAY - timedelta(days=6),
        hours="08:00",
        status="completed",
        description="CI pipeline finalisation",
    )

    # --- Project 2: Client Portal (Engineering + IT) ---
    p2, st = upsert(
        Project,
        {"title": "DSG Client Portal"},
        {
            "status": "new",
            "start_date": TODAY - timedelta(days=7),
            "end_date": TODAY + timedelta(days=120),
            "description": (
                "External client portal for ticket status, invoices, and SLA reporting."
            ),
            "company_id": company,
        },
    )
    record(result, st, "Project", p2)
    set_m2m(p2, "managers", [zain, hamza])
    s2 = _ensure_stages(result, p2)

    t_auth = _task(
        result,
        project=p2,
        stage=s2["Todo"],
        title="SSO / login flow",
        description="OIDC login for client tenants.",
        status="to_do",
        start=TODAY,
        end=TODAY + timedelta(days=40),
        hours="48:00",
        managers=[zain],
        members=[ali, rehan],
    )
    t_infra = _task(
        result,
        project=p2,
        stage=s2["In Progress"],
        title="VPN and access hardening",
        description="IT access controls for portal staging.",
        status="in_progress",
        start=TODAY - timedelta(days=5),
        end=TODAY + timedelta(days=20),
        hours="16:00",
        managers=[hamza],
        members=[rabia],
    )
    _timesheet(
        result,
        project=p2,
        task=t_auth,
        employee=ali,
        day=TODAY - timedelta(days=1),
        hours="02:00",
        status="in_Progress",
        description="OIDC discovery spike",
    )
    _timesheet(
        result,
        project=p2,
        task=t_infra,
        employee=rabia,
        day=TODAY - timedelta(days=1),
        hours="05:00",
        status="in_Progress",
        description="Firewall rules for staging",
    )

    # --- Project 3: Office Relocate (Ops — outside Engineering tree) ---
    p3, st = upsert(
        Project,
        {"title": "Lahore Office Relocate"},
        {
            "status": "on_hold",
            "start_date": TODAY - timedelta(days=20),
            "end_date": TODAY + timedelta(days=60),
            "description": "Facilities move for DSG Lahore operations team.",
            "company_id": company,
        },
    )
    record(result, st, "Project", p3)
    set_m2m(p3, "managers", [saad])
    s3 = _ensure_stages(result, p3)
    t_move = _task(
        result,
        project=p3,
        stage=s3["Todo"],
        title="Vendor shortlist for movers",
        description="Collect quotes from three movers.",
        status="to_do",
        start=TODAY,
        end=TODAY + timedelta(days=25),
        hours="08:00",
        managers=[saad],
        members=[zara],
    )
    _timesheet(
        result,
        project=p3,
        task=t_move,
        employee=zara,
        day=TODAY - timedelta(days=2),
        hours="01:30",
        status="in_Progress",
        description="Called two vendors",
    )

    record(
        result,
        "existing",
        "Summary",
        (
            f"{Project.objects.count()} projects, "
            f"{Task.objects.count()} tasks, "
            f"{TimeSheet.objects.count()} timesheets"
        ),
    )
    return result
