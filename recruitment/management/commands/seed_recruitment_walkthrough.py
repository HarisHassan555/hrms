"""
Seed a self-contained recruitment walkthrough case for demos and training.

All records are tagged with title prefix ``WALKTHROUGH:`` so they are easy to
find in the UI and safe to remove with ``--clear``.

Usage:
    python manage.py seed_recruitment_walkthrough
    python manage.py seed_recruitment_walkthrough --clear
"""

from __future__ import annotations

from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.urls import reverse

from base.models import Company, JobPosition
from employee.models import Employee

WALKTHROUGH_TITLE = "WALKTHROUGH: Senior HR Analyst (2026)"
WALKTHROUGH_PREFIX = "WALKTHROUGH:"

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"

EXTRA_STAGES = (
    ("Phone Screen", "initial", 2),
    ("Skills Test", "test", 3),
    ("Panel Interview", "interview", 4),
    ("Offer / Hired", "hired", 5),
    ("Not Selected", "cancelled", 6),
)

MASTER_SKILLS = (
    "HR analytics",
    "Excel reporting",
    "Stakeholder communication",
)

MASTER_REJECT_REASONS = (
    ("Skills gap", "Does not meet minimum technical bar for the role."),
    ("Role filled", "Position closed or another candidate was selected."),
)

CANDIDATES = (
    # name, email_suffix, stage_type, source, referral_source, rating (optional)
    (
        "Aisha Khan",
        "aisha.khan",
        "applied",
        "application",
        "company_career_site",
        None,
    ),
    (
        "Ben Ortiz",
        "ben.ortiz",
        "applied",
        "software",
        None,
        None,
    ),
    (
        "Carla Chen",
        "carla.chen",
        "initial",
        "application",
        "employee_referral",
        3.5,
    ),
    (
        "Dev Patel",
        "dev.patel",
        "test",
        "application",
        "job_board",
        4.0,
    ),
    (
        "Emma Wright",
        "emma.wright",
        "interview",
        "software",
        None,
        5.0,
    ),
    (
        "Frank Ng",
        "frank.ng",
        "cancelled",
        "application",
        "social_media",
        None,
    ),
)


class Command(BaseCommand):
    help = "Create or remove the recruitment walkthrough demo case in the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete walkthrough recruitments and their candidates.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear()
            return
        self._seed()

    def _clear(self):
        from recruitment.models import Candidate, Recruitment

        recs = Recruitment._base_manager.filter(title__startswith=WALKTHROUGH_PREFIX)
        count = recs.count()
        if not count:
            self.stdout.write(self.style.WARNING("No walkthrough recruitments found."))
            return
        Candidate._base_manager.filter(recruitment_id__in=recs).delete()
        recs.delete()
        self.stdout.write(
            self.style.SUCCESS(f"Removed {count} walkthrough recruitment(s).")
        )

    @transaction.atomic
    def _seed(self):
        from recruitment.models import (
            Candidate,
            CandidateRating,
            Recruitment,
            RecruitmentGeneralSetting,
            RejectReason,
            RejectedCandidate,
            Skill,
            Stage,
        )

        company = Company._base_manager.order_by("id").first()
        if not company:
            raise CommandError(
                "No company found. Create a company under Settings → Organization first."
            )

        job = (
            JobPosition._base_manager.filter(department_id__isnull=False)
            .order_by("id")
            .first()
        )
        if not job:
            job = JobPosition._base_manager.order_by("id").first()
        if not job:
            raise CommandError(
                "No job position found. Add at least one under Settings → Organization → Job Positions."
            )

        managers = list(Employee._base_manager.filter(is_active=True).order_by("id")[:2])
        if not managers:
            raise CommandError("No active employees found to assign as recruitment managers.")

        today = date.today()
        recruitment, created = Recruitment._base_manager.get_or_create(
            title=WALKTHROUGH_TITLE,
            defaults={
                "description": (
                    "<p><strong>Demo case</strong> for end-to-end recruitment: "
                    "public applications, pipeline shortlisting, interviews, and rejection.</p>"
                ),
                "is_event_based": False,
                "closed": False,
                "is_published": True,
                "vacancy": 3,
                "company_id": company,
                "job_position_id": job,
                "start_date": today - timedelta(days=14),
                "end_date": today + timedelta(days=60),
                "optional_profile_image": True,
                "optional_resume": False,
                "publish_in_linkedin": False,
            },
        )
        if not created:
            self.stdout.write(
                self.style.WARNING(
                    "Walkthrough recruitment already exists; refreshing stages and candidates."
                )
            )
            Candidate._base_manager.filter(recruitment_id=recruitment).delete()
            Stage._base_manager.filter(recruitment_id=recruitment).exclude(
                stage_type__in=("applied", "initial")
            ).delete()

        recruitment.recruitment_managers.set(managers)
        recruitment.open_positions.set([job])
        skill_ids = []
        for title in MASTER_SKILLS:
            skill, _ = Skill._base_manager.get_or_create(title=title.capitalize())
            skill_ids.append(skill.pk)
        recruitment.skills.set(skill_ids)

        reject_map = {}
        for title, description in MASTER_REJECT_REASONS:
            reason, _ = RejectReason._base_manager.get_or_create(
                title=title,
                company_id=company,
                defaults={"description": description},
            )
            reject_map[title] = reason

        RecruitmentGeneralSetting._base_manager.update_or_create(
            company_id=company,
            defaults={
                "candidate_self_tracking": True,
                "show_overall_rating": True,
            },
        )

        stage_by_type = {
            s.stage_type: s
            for s in Stage._base_manager.filter(recruitment_id=recruitment)
        }
        for stage_title, stage_type, sequence in EXTRA_STAGES:
            stage, _ = Stage._base_manager.get_or_create(
                recruitment_id=recruitment,
                stage_type=stage_type,
                defaults={"stage": stage_title, "sequence": sequence},
            )
            if stage.sequence != sequence or stage.stage != stage_title:
                stage.stage = stage_title
                stage.sequence = sequence
                stage.save(update_fields=["stage", "sequence"])
            stage.stage_managers.set(managers)
            stage_by_type[stage_type] = stage

        resume_file = ContentFile(MINIMAL_PDF, name="walkthrough-resume.pdf")
        rater = managers[0]

        for name, email_suffix, stage_type, source, referral_source, rating in CANDIDATES:
            stage = stage_by_type.get(stage_type) or stage_by_type["applied"]
            email = f"{email_suffix}.walkthrough@example.com"
            candidate, _ = Candidate._base_manager.update_or_create(
                email=email,
                defaults={
                    "name": name,
                    "recruitment_id": recruitment,
                    "job_position_id": job,
                    "stage_id": stage,
                    "source": source,
                    "referral_source": referral_source,
                    "mobile": "5550100",
                    "hired": stage_type == "hired",
                    "canceled": stage_type == "cancelled",
                },
            )
            if not candidate.resume:
                candidate.resume.save("walkthrough-resume.pdf", resume_file, save=True)

            if rating is not None:
                CandidateRating._base_manager.get_or_create(
                    candidate_id=candidate,
                    employee_id=rater,
                    defaults={"rating": rating},
                )

            if stage_type == "cancelled":
                rejected, _ = RejectedCandidate._base_manager.get_or_create(
                    candidate_id=candidate,
                    defaults={
                        "description": "Not moving forward after skills assessment.",
                    },
                )
                rejected.reject_reason_id.set([reject_map["Skills gap"]])

        app_url = reverse("application-form") + f"?recruitmentId={recruitment.pk}"
        open_jobs = reverse("open-recruitments")
        pipeline = reverse("cbv-pipeline")
        candidates = reverse("candidate-view")

        self.stdout.write(self.style.SUCCESS("Recruitment walkthrough case is ready."))
        self.stdout.write(f"  Company: {company}")
        self.stdout.write(f"  Job position: {job}")
        self.stdout.write(f"  Recruitment id: {recruitment.pk}")
        self.stdout.write(f"  Title: {WALKTHROUGH_TITLE}")
        self.stdout.write("")
        self.stdout.write("Open in the app (after login):")
        self.stdout.write(f"  Job openings (public): {open_jobs}")
        self.stdout.write(f"  Apply link: {app_url}")
        self.stdout.write(f"  Pipeline: {pipeline}")
        self.stdout.write(f"  Candidates list: {candidates}")
        self.stdout.write("")
        self.stdout.write(
            "Filter candidates by recruitment title containing 'WALKTHROUGH'."
        )
