"""
Populate Performance (PMS) for DSG Technologies.

Creates periods, key results, objectives, employee OKRs, question templates,
360 feedback, meetings, and bonus points for manager vs employee scenarios.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from base.models import Company
from employee.models import Employee
from pms.models import (
    AnonymousFeedback,
    EmployeeBonusPoint,
    EmployeeKeyResult,
    EmployeeObjective,
    Feedback,
    KeyResult,
    Meetings,
    Objective,
    Period,
    Question,
    QuestionTemplate,
)

from .utils import SeederResult, record, set_m2m, upsert

TODAY = date.today()


def _emp(email: str) -> Employee:
    return Employee.objects.get(email=email)


@transaction.atomic
def seed() -> SeederResult:
    result = SeederResult()
    company = Company.objects.filter(company="DSG Technologies").first()
    if not company:
        result.add("existing", "DSG Technologies missing — run pakistan_org first")
        return result

    zain = _emp("zain.abbas@dsg.pk")
    ali = _emp("ali.raza@dsg.pk")
    fatima = _emp("fatima.noor@dsg.pk")
    farah = _emp("farah.aziz@dsg.pk")
    sana = _emp("sana.iqbal@dsg.pk")
    kamran = _emp("kamran.shah@dsg.pk")
    nadia = _emp("nadia.rahman@dsg.pk")

    # Periods
    period, st = upsert(
        Period,
        {"period_name": "Q4 2026 Performance Cycle"},
        {
            "start_date": TODAY - timedelta(days=30),
            "end_date": TODAY + timedelta(days=60),
        },
    )
    record(result, st, "Period", period)
    period.company_id.set([company])

    mid_period, st = upsert(
        Period,
        {"period_name": "H2 2026 Mid-Year Review"},
        {
            "start_date": TODAY - timedelta(days=90),
            "end_date": TODAY + timedelta(days=10),
        },
    )
    record(result, st, "Period", mid_period)
    mid_period.company_id.set([company])

    # Key Result templates
    kr_defs = (
        ("Ship payroll PDF reliability", "Reduce payslip PDF failures to under 1%.", "%", 100, 90),
        ("Close critical bugs", "Resolve P0/P1 bugs within SLA.", "#", 20, 60),
        ("Improve leave UX completion", "Raise leave request completion rate.", "%", 100, 45),
        ("QA automation coverage", "Automated regression cases for attendance.", "#", 50, 90),
    )
    krs = {}
    for title, desc, ptype, target, duration in kr_defs:
        kr, st = upsert(
            KeyResult,
            {"title": title},
            {
                "description": desc,
                "progress_type": ptype,
                "target_value": target,
                "duration": duration,
                "company_id": company,
            },
        )
        record(result, st, "KeyResult", kr)
        krs[title] = kr

    # Objective (company OKR) with managers + assignees
    obj, st = upsert(
        Objective,
        {"title": "Engineering Excellence Q4"},
        {
            "description": "Raise product quality and delivery reliability for HRMS.",
            "duration_unit": "months",
            "duration": 3,
            "is_template": False,
            "archive": False,
            "self_employee_progress_update": True,
            "company_id": company,
        },
    )
    record(result, st, "Objective", obj)
    set_m2m(obj, "managers", [zain, kamran])
    set_m2m(obj, "assignees", [ali, fatima, farah, sana])
    set_m2m(
        obj,
        "key_result_id",
        [krs["Ship payroll PDF reliability"], krs["Close critical bugs"], krs["Improve leave UX completion"]],
    )

    obj2, st = upsert(
        Objective,
        {"title": "QA Automation Ramp"},
        {
            "description": "Build regression automation for attendance and leave.",
            "duration_unit": "months",
            "duration": 2,
            "is_template": False,
            "archive": False,
            "self_employee_progress_update": True,
            "company_id": company,
        },
    )
    record(result, st, "Objective", obj2)
    set_m2m(obj2, "managers", [zain])
    set_m2m(obj2, "assignees", [sana, fatima])
    set_m2m(obj2, "key_result_id", [krs["QA automation coverage"]])

    # Template objective (for settings / clone)
    tmpl, st = upsert(
        Objective,
        {"title": "Individual Development Plan Template"},
        {
            "description": "Reusable IDP template for mid-year reviews.",
            "duration_unit": "months",
            "duration": 6,
            "is_template": True,
            "archive": False,
            "company_id": company,
        },
    )
    record(result, st, "Objective template", tmpl)
    set_m2m(tmpl, "managers", [nadia])

    # Employee objectives + key results
    assignments = (
        (ali, obj, "On Track", 40, ("Ship payroll PDF reliability", 55, "On Track")),
        (fatima, obj, "Behind", 25, ("Improve leave UX completion", 30, "Behind")),
        (farah, obj, "Not Started", 0, ("Improve leave UX completion", 0, "Not Started")),
        (sana, obj2, "On Track", 60, ("QA automation coverage", 28, "On Track")),
        (fatima, obj2, "At Risk", 15, ("QA automation coverage", 8, "At Risk")),
    )
    for emp, objective, status, progress, (kr_title, current, kr_status) in assignments:
        eo, st = upsert(
            EmployeeObjective,
            {"employee_id": emp, "objective_id": objective},
            {
                "objective": objective.title,
                "objective_description": objective.description,
                "start_date": TODAY - timedelta(days=20),
                "end_date": TODAY + timedelta(days=70),
                "status": status,
                "progress_percentage": progress,
                "archive": False,
            },
        )
        record(result, st, "EmployeeObjective", f"{emp.get_full_name()} / {objective.title}")
        kr_tpl = krs[kr_title]
        eo.key_result_id.add(kr_tpl)
        ekr, st = upsert(
            EmployeeKeyResult,
            {
                "employee_objective_id": eo,
                "key_result": kr_title,
            },
            {
                "key_result_description": kr_tpl.description,
                "progress_type": kr_tpl.progress_type,
                "status": kr_status,
                "start_value": 0,
                "current_value": current,
                "target_value": kr_tpl.target_value,
                "start_date": TODAY - timedelta(days=20),
                "end_date": TODAY + timedelta(days=70),
                "progress_percentage": int(min(100, (current / max(kr_tpl.target_value, 1)) * 100)),
            },
        )
        record(result, st, "EmployeeKeyResult", f"{emp.get_full_name()} / {kr_title}")

    # Question template + questions
    qt, st = upsert(
        QuestionTemplate,
        {"question_template": "Engineering 360 Review"},
        {},
    )
    record(result, st, "QuestionTemplate", qt)
    qt.company_id.set([company])
    for text, qtype in (
        ("How effectively does this person deliver committed work?", "1"),
        ("Rate collaboration with cross-functional partners.", "2"),
        ("What should this person start / stop / continue?", "1"),
    ):
        q, st = upsert(
            Question,
            {"question": text, "template_id": qt},
            {"question_type": qtype},
        )
        record(result, st, "Question", q)

    meet_qt, st = upsert(
        QuestionTemplate,
        {"question_template": "1:1 Meeting Check-in"},
        {},
    )
    record(result, st, "QuestionTemplate", meet_qt)
    meet_qt.company_id.set([company])
    q_meet, st = upsert(
        Question,
        {"question": "What blockers should we unblock this week?", "template_id": meet_qt},
        {"question_type": "1"},
    )
    record(result, st, "Question", q_meet)

    # 360 Feedback — Ali is subject; Zain manager; Fatima colleague; Farah subordinate-style peer
    fb, st = upsert(
        Feedback,
        {"review_cycle": "Ali Raza — Q4 360"},
        {
            "employee_id": ali,
            "manager_id": zain,
            "question_template_id": qt,
            "status": "On Track",
            "archive": False,
            "start_date": TODAY - timedelta(days=7),
            "end_date": TODAY + timedelta(days=21),
            "cyclic_feedback": False,
        },
    )
    record(result, st, "Feedback", fb)
    set_m2m(fb, "colleague_id", [fatima, farah])
    set_m2m(fb, "subordinate_id", [])
    set_m2m(fb, "others_id", [sana])

    fb2, st = upsert(
        Feedback,
        {"review_cycle": "Fatima Noor — Mid-Year Feedback"},
        {
            "employee_id": fatima,
            "manager_id": zain,
            "question_template_id": qt,
            "status": "Not Started",
            "archive": False,
            "start_date": TODAY,
            "end_date": TODAY + timedelta(days=30),
            "cyclic_feedback": False,
        },
    )
    record(result, st, "Feedback", fb2)
    set_m2m(fb2, "colleague_id", [ali])

    # Anonymous feedback about Ali
    anon, st = upsert(
        AnonymousFeedback,
        {"feedback_subject": "Team collaboration note"},
        {
            "based_on": "employee",
            "employee_id": ali,
            "status": "Not Started",
            "archive": False,
            "feedback_description": "Anonymous note on collaboration during payroll release.",
            "anonymous_feedback_id": "anon01",
        },
    )
    record(result, st, "AnonymousFeedback", anon)

    # Meetings
    meeting_dt = timezone.make_aware(datetime.combine(TODAY + timedelta(days=2), datetime.min.time().replace(hour=15)))
    meet, st = upsert(
        Meetings,
        {"title": "Zain / Ali weekly 1:1"},
        {
            "date": meeting_dt,
            "question_template": meet_qt,
            "response": "",
            "show_response": False,
            "company_id": company,
        },
    )
    record(result, st, "Meeting", meet)
    set_m2m(meet, "manager", [zain])
    set_m2m(meet, "employee_id", [ali])
    set_m2m(meet, "answer_employees", [ali])

    team_meet, st = upsert(
        Meetings,
        {"title": "Engineering standup review"},
        {
            "date": meeting_dt + timedelta(days=1),
            "question_template": None,
            "response": "Discussed OKR progress and QA ramp.",
            "show_response": True,
            "company_id": company,
        },
    )
    record(result, st, "Meeting", team_meet)
    set_m2m(team_meet, "manager", [zain])
    set_m2m(team_meet, "employee_id", [ali, fatima, farah, sana])
    set_m2m(team_meet, "answer_employees", [ali, fatima])

    # Bonus points
    for emp, points, based_on in (
        (ali, 25, "Payslip PDF reliability improvements"),
        (sana, 15, "Attendance regression automation milestone"),
        (fatima, 10, "Leave UX polish"),
    ):
        bp, st = upsert(
            EmployeeBonusPoint,
            {"employee_id": emp, "based_on": based_on},
            {"bonus_point": points},
        )
        record(result, st, "EmployeeBonusPoint", f"{emp.get_full_name()} +{points}")

    record(
        result,
        "existing",
        "Summary",
        (
            f"{Objective.objects.count()} objectives, "
            f"{EmployeeObjective.objects.count()} emp OKRs, "
            f"{Feedback.objects.count()} feedback, "
            f"{Meetings.objects.count()} meetings"
        ),
    )
    return result
