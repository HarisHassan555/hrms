"""Progress report aggregations for LMS."""

from __future__ import annotations

from django.db.models import Avg, Count, Prefetch, Q
from django.utils import timezone

from lms.models import Course, CourseEnrollment, EnrollmentStatus, TestAttempt


def get_progress_report_context(course_id=None, employee_id=None):
    now = timezone.now()
    enrollments = (
        CourseEnrollment.objects.filter(~Q(status=EnrollmentStatus.CANCELLED))
        .select_related("course_id", "employee_id")
        .prefetch_related(
            Prefetch(
                "test_attempts",
                queryset=TestAttempt.objects.select_related("test").order_by(
                    "-passed", "-score_percent", "-id"
                ),
            )
        )
        .order_by("-assigned_at")
    )
    if course_id:
        enrollments = enrollments.filter(course_id_id=course_id)
    if employee_id:
        enrollments = enrollments.filter(employee_id_id=employee_id)

    rows = []
    for enrollment in enrollments[:200]:
        compulsory_scores = []
        for attempt in enrollment.test_attempts.all():
            if attempt.test.is_compulsory:
                compulsory_scores.append(attempt.score_percent)
                break  # best first due to ordering
        overdue = enrollment.is_overdue()
        rows.append(
            {
                "enrollment": enrollment,
                "employee": enrollment.employee_id,
                "course": enrollment.course_id,
                "progress": enrollment.progress_percentage,
                "status": enrollment.status,
                "status_label": enrollment.get_status_display(),
                "due_at": enrollment.due_at,
                "overdue": overdue,
                "compulsory_score": compulsory_scores[0] if compulsory_scores else None,
            }
        )

    by_course = (
        CourseEnrollment.objects.filter(~Q(status=EnrollmentStatus.CANCELLED))
        .values("course_id", "course_id__title")
        .annotate(
            assigned=Count("id"),
            completed=Count("id", filter=Q(status=EnrollmentStatus.COMPLETED)),
            overdue=Count(
                "id",
                filter=Q(status=EnrollmentStatus.OVERDUE)
                | (
                    Q(due_at__lt=now)
                    & Q(
                        status__in=[
                            EnrollmentStatus.ASSIGNED,
                            EnrollmentStatus.IN_PROGRESS,
                        ]
                    )
                ),
            ),
            avg_progress=Avg("progress_percentage"),
        )
        .order_by("course_id__title")
    )

    courses = Course.objects.filter(is_active=True).order_by("title")
    return {
        "rows": rows,
        "by_course": list(by_course),
        "courses": courses,
        "selected_course_id": course_id,
        "selected_employee_id": employee_id,
    }
