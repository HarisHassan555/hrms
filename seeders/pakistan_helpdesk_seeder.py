"""
Populate Helpdesk / Tickets for DSG Technologies.

Creates ticket types, department managers, tags, FAQs, and sample tickets
covering My / Suggested / All visibility for employee vs manager flows.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.db import transaction

from base.models import Company, Department, Tags
from employee.models import Employee
from helpdesk.models import (
    ClaimRequest,
    DepartmentManager,
    FAQ,
    FAQCategory,
    Ticket,
    TicketType,
)

from .utils import SeederResult, record, set_m2m, upsert

TODAY = date.today()


def _emp(email: str) -> Employee:
    return Employee.objects.get(email=email)


def _dept(name: str) -> Department:
    return Department.objects.get(department=name)


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
    hamza = _emp("hamza.sheikh@dsg.pk")
    nadia = _emp("nadia.rahman@dsg.pk")
    rabia = _emp("rabia.yousaf@dsg.pk")
    sana = _emp("sana.iqbal@dsg.pk")
    farah = _emp("farah.aziz@dsg.pk")

    eng = _dept("Engineering")
    it = _dept("Information Technology")
    hr = _dept("Human Resources")

    # Ticket types
    type_defs = (
        ("IT Hardware Support", "service_request", "ITH"),
        ("HR Policy Query", "service_request", "HRQ"),
        ("Access / Account Request", "service_request", "ACC"),
        ("General Complaint", "complaint", "CMP"),
        ("Improvement Suggestion", "suggestion", "SUG"),
    )
    types = {}
    for title, ttype, prefix in type_defs:
        tt, st = upsert(
            TicketType,
            {"title": title},
            {"type": ttype, "prefix": prefix, "company_id": company},
        )
        record(result, st, "TicketType", tt)
        types[title] = tt

    # Department managers
    for mgr, dept in ((zain, eng), (hamza, it), (nadia, hr)):
        dm, st = upsert(
            DepartmentManager,
            {"manager": mgr, "department": dept},
            {"company_id": company},
        )
        record(result, st, "DepartmentManager", f"{mgr.get_full_name()} → {dept}")

    # Tags
    tag_objs = []
    for color, title in (("#4F46E5", "Urgent"), ("#0EA5E9", "Access"), ("#16A34A", "Resolved-OK")):
        tag, st = upsert(Tags, {"title": title}, {"color": color})
        record(result, st, "Tag", tag)
        tag_objs.append(tag)

    # FAQ
    cat, st = upsert(FAQCategory, {"title": "IT & Access"}, {})
    record(result, st, "FAQCategory", cat)
    for q, a in (
        ("How do I reset my VPN password?", "Use the IT self-service portal or raise an Access ticket."),
        ("Who approves laptop replacements?", "Your reporting manager, then IT Hardware Support."),
    ):
        faq, st = upsert(FAQ, {"question": q, "category": cat}, {"answer": a})
        record(result, st, "FAQ", faq)
        set_m2m(faq, "tags", [tag_objs[1]])

    # Tickets
    tickets = (
        {
            "title": "Laptop charger replacement",
            "employee_id": ali,
            "ticket_type": types["IT Hardware Support"],
            "description": "Charger sparking — need replacement ASAP.",
            "priority": "high",
            "assigning_type": "department",
            "raised_on": str(it.pk),
            "status": "new",
            "deadline": TODAY + timedelta(days=3),
            "assignees": [hamza],
            "tags": [tag_objs[0]],
        },
        {
            "title": "Leave policy clarification",
            "employee_id": fatima,
            "ticket_type": types["HR Policy Query"],
            "description": "Confirm carry-forward rules for annual leave.",
            "priority": "medium",
            "assigning_type": "department",
            "raised_on": str(hr.pk),
            "status": "in_progress",
            "deadline": TODAY + timedelta(days=7),
            "assignees": [nadia],
            "tags": [],
        },
        {
            "title": "Staging VPN access",
            "employee_id": ali,
            "ticket_type": types["Access / Account Request"],
            "description": "Need staging VPN for Client Portal work.",
            "priority": "medium",
            "assigning_type": "individual",
            "raised_on": str(rabia.pk),
            "status": "on_hold",
            "deadline": TODAY + timedelta(days=5),
            "assignees": [rabia],
            "tags": [tag_objs[1]],
        },
        {
            "title": "Noise in open bay",
            "employee_id": sana,
            "ticket_type": types["General Complaint"],
            "description": "Construction noise near Engineering bay.",
            "priority": "low",
            "assigning_type": "department",
            "raised_on": str(eng.pk),
            "status": "new",
            "deadline": TODAY + timedelta(days=10),
            "assignees": [],
            "tags": [],
        },
        {
            "title": "Dark mode for ESS",
            "employee_id": farah,
            "ticket_type": types["Improvement Suggestion"],
            "description": "Please consider ESS dark mode option.",
            "priority": "low",
            "assigning_type": "department",
            "raised_on": str(eng.pk),
            "status": "resolved",
            "deadline": TODAY - timedelta(days=1),
            "assignees": [zain],
            "tags": [tag_objs[2]],
        },
    )

    created_tickets = []
    for spec in tickets:
        assignees = spec.pop("assignees")
        tags = spec.pop("tags")
        title = spec.pop("title")
        ticket, st = upsert(Ticket, {"title": title}, spec)
        record(result, st, "Ticket", ticket)
        if assignees:
            set_m2m(ticket, "assigned_to", assignees)
        if tags:
            set_m2m(ticket, "tags", tags)
        created_tickets.append(ticket)

    # Claim request on Engineering complaint (unassigned) by Zain
    eng_ticket = next((t for t in created_tickets if t.title == "Noise in open bay"), None)
    if eng_ticket:
        cr, st = upsert(
            ClaimRequest,
            {"ticket_id": eng_ticket, "employee_id": zain},
            {"is_approved": False, "is_rejected": False},
        )
        record(result, st, "ClaimRequest", f"{zain.get_full_name()} → {eng_ticket.title}")

    record(
        result,
        "existing",
        "Summary",
        (
            f"{TicketType.objects.count()} types, "
            f"{Ticket.objects.count()} tickets, "
            f"{DepartmentManager.objects.count()} dept managers"
        ),
    )
    return result
