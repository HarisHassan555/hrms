"""
Populate recruitment for DSG Technologies / DSG Business Solutions.

Creates published job posts with skills, candidates across pipeline stages,
onboarding for hired candidates, and converts a subset into employees.

Password for converted employees: ``1212``
"""

from __future__ import annotations

from datetime import date, time, timedelta

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from base.models import Company, Department, JobPosition, JobRole
from employee.models import Employee, EmployeeType, EmployeeWorkInformation, WorkType
from horilla_auth.models import HorillaUser
from onboarding.models import (
    CandidateStage,
    CandidateTask,
    OnboardingPortal,
    OnboardingStage,
    OnboardingTask,
)
from recruitment.models import (
    Candidate,
    CandidateRating,
    InterviewSchedule,
    Recruitment,
    RejectedCandidate,
    RejectReason,
    Skill,
    Stage,
    StageNote,
)

from .utils import SeederResult, record, set_m2m, upsert

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
PASSWORD = "1212"
CANDIDATE_DOMAIN = "apply.dsg.pk"

RECRUIT_STAGES = (
    ("Applied", "applied", 0),
    ("Screening", "initial", 1),
    ("Skills Assessment", "test", 2),
    ("Interview", "interview", 3),
    ("Offer / Hired", "hired", 4),
    ("Not Selected", "cancelled", 5),
)

ONBOARD_STAGES = (
    ("Welcome / Initial", 0, False),
    ("Documentation", 1, False),
    ("IT Setup", 2, False),
    ("Orientation", 3, False),
    ("First Week Complete", 4, True),
)

ONBOARD_TASKS = {
    "Welcome / Initial": (
        ("Send welcome email", True),
        ("Assign onboarding buddy", True),
        ("Share company handbook", True),
    ),
    "Documentation": (
        ("Collect CNIC and bank details", True),
        ("Sign employment contract", True),
        ("Complete tax declaration", True),
    ),
    "IT Setup": (
        ("Provision laptop and accounts", True),
        ("Grant system access", True),
        ("Complete security training", True),
    ),
    "Orientation": (
        ("Attend HR orientation", True),
        ("Meet reporting manager", True),
        ("Tour office / tools walkthrough", True),
    ),
    "First Week Complete": (
        ("30-day goals agreed", True),
        ("First-week feedback collected", True),
    ),
}

# company_name, title, job_position, vacancy, skills, manager_emails, description, candidates
# candidate tuple: name, stage_type, source, referral, gender, rating, start_onboard, convert
JOBS = (
    {
        "company": "DSG Technologies",
        "title": "Backend Engineer (Python/Django)",
        "job_position": "Software Engineer",
        "vacancy": 3,
        "skills": ("Python", "Django", "Postgresql", "Rest apis", "Docker"),
        "managers": ("zain.abbas@dsg.pk", "omar.siddiqui@dsg.pk", "nadia.rahman@dsg.pk"),
        "description": (
            "<p>Build and maintain DSG HR platform services. You will design APIs, "
            "optimize queries, and ship reliable Django features with the product team.</p>"
            "<ul><li>3+ years Python</li><li>Strong Django / REST experience</li>"
            "<li>Familiarity with PostgreSQL and Docker</li></ul>"
        ),
        "candidates": (
            ("Amina Shah", "applied", "application", "company_career_site", "female", None, False, False),
            ("Hassan Jamil", "applied", "application", "job_board", "male", None, False, False),
            ("Noor Fatima", "initial", "application", "employee_referral", "female", 3.5, False, False),
            ("Danish Rauf", "test", "software", None, "male", 4.0, False, False),
            ("Leila Rahman", "interview", "application", "linkedin", "female", 4.5, False, False),
            ("Adeel Khan", "hired", "application", "company_career_site", "male", 5.0, True, True),
            ("Saba Nadeem", "hired", "software", "employee_referral", "female", 4.5, True, False),
            ("Farhan Mir", "cancelled", "application", "job_board", "male", 2.0, False, False),
        ),
    },
    {
        "company": "DSG Technologies",
        "title": "Frontend Engineer (React)",
        "job_position": "Frontend Engineer",
        "vacancy": 2,
        "skills": ("Javascript", "React", "Css", "Typescript", "Accessibility"),
        "managers": ("zain.abbas@dsg.pk", "omar.siddiqui@dsg.pk"),
        "description": (
            "<p>Own DSG product UI. Work with design on a clean SaaS interface, "
            "component libraries, and accessible React experiences.</p>"
        ),
        "candidates": (
            ("Zainab Iftikhar", "applied", "application", "company_career_site", "female", None, False, False),
            ("Taha Rizvi", "applied", "application", "job_board", "male", None, False, False),
            ("Hira Nasir", "initial", "application", "social_media", "female", 3.5, False, False),
            ("Owais Jafri", "test", "software", None, "male", 4.0, False, False),
            ("Sundus Bari", "interview", "application", "employee_referral", "female", 4.5, False, False),
            ("Muneeb Aslam", "hired", "application", "company_career_site", "male", 5.0, True, True),
            ("Areeba Zahid", "hired", "software", "job_board", "female", 4.5, True, False),
            ("Faisal Qadir", "cancelled", "application", "social_media", "male", 2.0, False, False),
        ),
    },
    {
        "company": "DSG Technologies",
        "title": "DevOps Engineer",
        "job_position": "DevOps Engineer",
        "vacancy": 1,
        "skills": ("Aws", "Docker", "Kubernetes", "Ci/cd", "Linux"),
        "managers": ("zain.abbas@dsg.pk", "hamza.sheikh@dsg.pk"),
        "description": (
            "<p>Own CI/CD, cloud reliability, and production operations for DSG "
            "platforms hosted in Pakistan and the Gulf.</p>"
        ),
        "candidates": (
            ("Saifullah Khan", "applied", "application", "job_board", "male", None, False, False),
            ("Mahira Sohail", "initial", "application", "company_career_site", "female", 3.5, False, False),
            ("Umer Durrani", "interview", "software", "recruiter_headhunter", "male", 4.5, False, False),
            ("Hammad Iqbal", "hired", "application", "employee_referral", "male", 5.0, True, True),
            ("Kiran Batool", "cancelled", "application", "social_media", "female", None, False, False),
        ),
    },
    {
        "company": "DSG Business Solutions",
        "title": "Account Executive - Enterprise",
        "job_position": "Account Executive",
        "vacancy": 2,
        "skills": ("Negotiation", "Crm", "B2b sales", "Presentation"),
        "managers": ("maham.javed@dsg.pk", "ayesha.kamal@dsg.pk", "bilal.hassan@dsg.pk"),
        "description": (
            "<p>Quota-carrying Account Executive for Lahore enterprise accounts. "
            "You will run demos, negotiate contracts, and expand existing customers.</p>"
        ),
        "candidates": (
            ("Rida Anwar", "applied", "application", "social_media", "female", None, False, False),
            ("Shahzaib Ali", "test", "application", "job_board", "male", 3.5, False, False),
            ("Hina Qazi", "interview", "software", "recruiter_headhunter", "female", 4.0, False, False),
            ("Waleed Asif", "hired", "application", "employee_referral", "male", 4.5, True, True),
            ("Iqra Naseer", "cancelled", "application", "company_career_site", "female", 2.5, False, False),
        ),
    },
    {
        "company": "DSG Business Solutions",
        "title": "HR Business Partner",
        "job_position": "HR Generalist",
        "vacancy": 1,
        "skills": ("Employee relations", "Hr analytics", "Communication", "Onboarding"),
        "managers": ("ayesha.kamal@dsg.pk", "bilal.hassan@dsg.pk"),
        "description": (
            "<p>HR Business Partner for Sales and Finance in Lahore. Support "
            "performance cycles, onboarding, and employee relations.</p>"
        ),
        "candidates": (
            ("Komal Saeed", "applied", "application", "social_media", "female", None, False, False),
            ("Yasir Mehmood", "initial", "application", "job_board", "male", 3.0, False, False),
            ("Anam Bukhari", "interview", "application", "employee_referral", "female", 4.5, False, False),
            ("Sarah Hussain", "hired", "application", "company_career_site", "female", 5.0, True, True),
            ("Noman Iftikhar", "cancelled", "software", None, "male", None, False, False),
        ),
    },
)


def _employee_by_email(email: str) -> Employee | None:
    return Employee.objects.filter(email=email).first()


def _candidate_email(name: str, job_title: str) -> str:
    slug = name.lower().replace(" ", ".")
    job_slug = "".join(ch for ch in job_title.lower() if ch.isalnum())[:18]
    return f"{slug}.{job_slug}@{CANDIDATE_DOMAIN}"


def _ensure_stages(recruitment, managers):
    by_type = {}
    for title, stage_type, sequence in RECRUIT_STAGES:
        stage = (
            Stage._base_manager.filter(
                recruitment_id=recruitment, stage_type=stage_type
            ).first()
            or Stage._base_manager.filter(
                recruitment_id=recruitment, stage=title
            ).first()
        )
        if stage is None:
            stage = Stage._base_manager.create(
                recruitment_id=recruitment,
                stage=title,
                stage_type=stage_type,
                sequence=sequence,
            )
        else:
            stage.stage = title
            stage.stage_type = stage_type
            stage.sequence = sequence
            stage.save(update_fields=["stage", "stage_type", "sequence"])
        if managers:
            stage.stage_managers.set(managers)
        by_type[stage_type] = stage
    return by_type


def _ensure_onboard_stages(recruitment, managers):
    by_title = {}
    existing = list(
        OnboardingStage._base_manager.filter(recruitment_id=recruitment).order_by(
            "sequence", "id"
        )
    )
    for index, (title, sequence, is_final) in enumerate(ONBOARD_STAGES):
        if index < len(existing):
            stage = existing[index]
            stage.stage_title = title
            stage.sequence = sequence
            stage.is_final_stage = is_final
            stage.save(update_fields=["stage_title", "sequence", "is_final_stage"])
        else:
            stage = OnboardingStage._base_manager.create(
                recruitment_id=recruitment,
                stage_title=title,
                sequence=sequence,
                is_final_stage=is_final,
            )
        if managers:
            stage.employee_id.set(managers)
        by_title[title] = stage
    return by_title


def _ensure_onboard_tasks(onboard_stages, managers):
    by_stage = {}
    for stage_title, task_defs in ONBOARD_TASKS.items():
        stage = onboard_stages[stage_title]
        tasks = []
        for task_title, required in task_defs:
            task, _ = OnboardingTask._base_manager.get_or_create(
                stage_id=stage,
                task_title=task_title,
                defaults={"is_required": required},
            )
            if managers:
                task.employee_id.set(managers)
            tasks.append(task)
        by_stage[stage_title] = tasks
    return by_stage


def _task_status(current_stage_title: str, task_stage_title: str, index: int) -> str:
    order = [title for title, _, _ in ONBOARD_STAGES]
    current_idx = order.index(current_stage_title)
    task_idx = order.index(task_stage_title)
    if task_idx < current_idx:
        return "done"
    if task_idx == current_idx:
        return "ongoing" if index % 2 else "done"
    return "todo"


def _convert_candidate(
    candidate: Candidate,
    company: Company,
    job: JobPosition,
    manager: Employee | None,
    result: SeederResult,
) -> Employee | None:
    if candidate.converted_employee_id_id:
        return candidate.converted_employee_id

    parts = (candidate.name or "New Hire").split(" ", 1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else "Hire"
    email = candidate.email.replace(CANDIDATE_DOMAIN, "dsg.pk")

    user = HorillaUser.objects.filter(username=email).first()
    if user is None:
        user = HorillaUser.objects.create_user(
            username=email,
            email=email,
            password=PASSWORD,
            first_name=first,
            last_name=last,
        )
    else:
        user.set_password(PASSWORD)
        user.save(update_fields=["password"])

    employee = Employee.objects.filter(email=email).first()
    if employee is None:
        employee = Employee(
            employee_user_id=user,
            email=email,
            employee_first_name=first,
            employee_last_name=last,
            phone=candidate.mobile or "03001110000",
            badge_id=f"HIRE-{candidate.pk}",
            gender=candidate.gender or "male",
            city=candidate.city or company.city,
            country="Pakistan",
            state=company.state,
            address=candidate.address or f"{company.city}, Pakistan",
            is_active=True,
        )
        employee.save()
        record(result, "created", "Converted employee", employee)
    else:
        record(result, "existing", "Converted employee", employee)

    work_type, _ = upsert(WorkType, {"work_type": "Onsite"})
    set_m2m(work_type, "company_id", [company])
    employee_type, _ = upsert(EmployeeType, {"employee_type": "Full Time"})
    set_m2m(employee_type, "company_id", [company])

    # Prefer a role under the hired job position.
    role = JobRole.objects.filter(job_position_id=job).order_by("id").first()
    work_info, _ = EmployeeWorkInformation.objects.get_or_create(employee_id=employee)
    work_info.company_id = company
    work_info.department_id = job.department_id
    work_info.job_position_id = job
    work_info.job_role_id = role
    work_info.work_type_id = work_type
    work_info.employee_type_id = employee_type
    work_info.reporting_manager_id = manager
    work_info.date_joining = candidate.joining_date or timezone.localdate()
    work_info.email = email
    work_info.mobile = candidate.mobile or "03001110000"
    work_info.location = f"{company.city} Office"
    work_info.basic_salary = 180000
    work_info.save()

    candidate.converted_employee_id = employee
    candidate.hired = True
    candidate.start_onboard = True
    candidate.offer_letter_status = "joined"
    candidate.save(
        update_fields=[
            "converted_employee_id",
            "hired",
            "start_onboard",
            "offer_letter_status",
        ]
    )
    return employee


@transaction.atomic
def seed() -> SeederResult:
    result = SeederResult()
    today = timezone.localdate()

    reject_reason, status = upsert(
        RejectReason,
        {"title": "Skills gap"},
        {"description": "Does not meet the technical or role bar."},
    )
    record(result, status, "Reject reason", reject_reason)

    for spec in JOBS:
        company = Company.objects.filter(company=spec["company"]).first()
        if not company:
            record(result, "existing", "Skipped job", f"{spec['title']} (company missing)")
            continue

        job = JobPosition.objects.filter(job_position=spec["job_position"]).first()
        if not job:
            # Create under a sensible department for the company.
            dept_name = {
                "Software Engineer": "Engineering",
                "Frontend Engineer": "Engineering",
                "DevOps Engineer": "Engineering",
                "Account Executive": "Sales",
                "HR Generalist": "Human Resources",
            }.get(spec["job_position"], "Human Resources")
            dept, _ = upsert(Department, {"department": dept_name})
            set_m2m(dept, "company_id", [company])
            job, job_status = upsert(
                JobPosition,
                {"department_id": dept, "job_position": spec["job_position"]},
            )
            set_m2m(job, "company_id", [company])
            record(result, job_status, "Job Position", job)

        managers = [
            emp
            for email in spec["managers"]
            if (emp := _employee_by_email(email)) is not None
        ]
        if not managers:
            managers = list(
                Employee.objects.filter(
                    employee_work_info__company_id=company
                ).order_by("id")[:2]
            )

        recruitment, created = Recruitment._base_manager.get_or_create(
            title=spec["title"],
            defaults={
                "description": spec["description"],
                "is_event_based": False,
                "closed": False,
                "is_published": True,
                "vacancy": spec["vacancy"],
                "company_id": company,
                "job_position_id": job,
                "start_date": today - timedelta(days=18),
                "end_date": today + timedelta(days=40),
                "optional_profile_image": True,
                "optional_resume": False,
                "publish_in_linkedin": False,
            },
        )
        if not created:
            recruitment.description = spec["description"]
            recruitment.vacancy = spec["vacancy"]
            recruitment.closed = False
            recruitment.is_published = True
            recruitment.job_position_id = job
            recruitment.company_id = company
            recruitment.save()
        record(
            result,
            "created" if created else "updated",
            "Recruitment",
            recruitment,
        )

        if managers:
            recruitment.recruitment_managers.set(managers)
        recruitment.open_positions.set([job])

        skills = []
        for title in spec["skills"]:
            skill, skill_status = upsert(Skill, {"title": title})
            skills.append(skill)
            record(result, skill_status, "Skill", skill)
        recruitment.skills.set(skills)

        stage_by_type = _ensure_stages(recruitment, managers)
        onboard_stages = _ensure_onboard_stages(recruitment, managers)
        onboard_tasks = _ensure_onboard_tasks(onboard_stages, managers)

        rater = managers[0] if managers else None
        hired_for_onboard = []

        for (
            name,
            stage_type,
            source,
            referral,
            gender,
            rating,
            start_onboard,
            convert,
        ) in spec["candidates"]:
            email = _candidate_email(name, spec["title"])
            stage = stage_by_type.get(stage_type) or stage_by_type["applied"]
            joining = today + timedelta(days=7) if stage_type == "hired" else None
            hired_on = today - timedelta(days=2) if stage_type == "hired" else None
            city = company.city
            state = company.state

            # referral_source must match model choices; map linkedin -> social_media
            referral_source = {
                "linkedin": "social_media",
                None: None,
            }.get(referral, referral)

            candidate, cand_created = Candidate._base_manager.update_or_create(
                email=email,
                recruitment_id=recruitment,
                defaults={
                    "name": name,
                    "job_position_id": job,
                    "stage_id": stage,
                    "source": source,
                    "referral_source": referral_source,
                    "mobile": "03015550000",
                    "gender": gender,
                    "country": "Pakistan",
                    "state": state,
                    "city": city,
                    "address": f"{city}, Pakistan",
                    "hired": stage_type == "hired",
                    "canceled": stage_type == "cancelled",
                    "start_onboard": bool(start_onboard),
                    "joining_date": joining,
                    "hired_date": hired_on,
                    "offer_letter_status": (
                        "accepted"
                        if stage_type == "hired"
                        else "sent"
                        if stage_type == "interview"
                        else "not_sent"
                    ),
                },
            )
            if not candidate.resume:
                candidate.resume.save(
                    f"{email.split('@')[0]}-resume.pdf",
                    ContentFile(MINIMAL_PDF),
                    save=True,
                )
            record(
                result,
                "created" if cand_created else "updated",
                "Candidate",
                f"{name} @ {stage_type}",
            )

            if rating is not None and rater:
                CandidateRating._base_manager.get_or_create(
                    candidate_id=candidate,
                    employee_id=rater,
                    defaults={"rating": rating},
                )

            if stage_type == "interview" and managers:
                interview, _ = InterviewSchedule._base_manager.get_or_create(
                    candidate_id=candidate,
                    interview_date=today + timedelta(days=2),
                    defaults={
                        "interview_time": time(11, 0),
                        "description": "Panel interview covering role fit and past work.",
                        "completed": False,
                    },
                )
                interview.employee_id.set(managers[:2])
                StageNote._base_manager.get_or_create(
                    candidate_id=candidate,
                    stage_id=stage,
                    description=f"Shortlisted {name} for panel interview.",
                    defaults={"updated_by": rater, "candidate_can_view": False},
                )

            if stage_type == "cancelled":
                rejected, _ = RejectedCandidate._base_manager.get_or_create(
                    candidate_id=candidate,
                    defaults={"description": "Not moving forward after screening."},
                )
                rejected.reject_reason_id.set([reject_reason])

            if stage_type == "hired":
                StageNote._base_manager.get_or_create(
                    candidate_id=candidate,
                    stage_id=stage,
                    description=f"Offer accepted. Joining date {joining}.",
                    defaults={"updated_by": rater, "candidate_can_view": True},
                )
                if start_onboard:
                    hired_for_onboard.append((candidate, convert))

        for index, (candidate, convert) in enumerate(hired_for_onboard):
            stage_titles = list(onboard_stages.keys())
            stage_title = stage_titles[min(index, len(stage_titles) - 1)]
            current_stage = onboard_stages[stage_title]
            CandidateStage._base_manager.update_or_create(
                candidate_id=candidate,
                defaults={
                    "onboarding_stage_id": current_stage,
                    "sequence": current_stage.sequence or 0,
                },
            )
            OnboardingPortal._base_manager.get_or_create(
                candidate_id=candidate,
                defaults={
                    "token": f"dsg-{candidate.pk}-{candidate.email.split('@')[0]}",
                    "used": index == 0,
                    "count": 1 if index == 0 else 0,
                },
            )
            for task_stage_title, tasks in onboard_tasks.items():
                task_stage = onboard_stages[task_stage_title]
                for task in tasks:
                    task.candidates.add(candidate)
                    CandidateTask._base_manager.get_or_create(
                        candidate_id=candidate,
                        onboarding_task_id=task,
                        stage_id=task_stage,
                        defaults={
                            "status": _task_status(stage_title, task_stage_title, index)
                        },
                    )
            record(result, "created", "Onboarding", candidate.name)

            if convert:
                _convert_candidate(
                    candidate,
                    company,
                    job,
                    managers[0] if managers else None,
                    result,
                )

    result.add(
        "created",
        "Recruitment populated: job posts with skills, staged candidates, "
        "onboarding, and converted hires (password 1212).",
    )
    return result
