"""
LMS admin dashboard metrics (company-scoped via HorillaCompanyManager).
"""

from decimal import Decimal

from django.db.models import Avg, Count, Q
from django.utils import timezone

from lms.models import Course, CourseEnrollment, CourseStatus, EnrollmentStatus


def _active_enrollment_filter():
    return ~Q(status=EnrollmentStatus.CANCELLED)


def _overdue_filter(now):
    return Q(status=EnrollmentStatus.OVERDUE) | (
        Q(due_at__lt=now)
        & Q(status__in=[EnrollmentStatus.ASSIGNED, EnrollmentStatus.IN_PROGRESS])
    )


def get_lms_dashboard_context():
    """
    Return KPI counts and recent enrollments for the current company scope.
    Call from a view after middleware has set company context on the request.
    """
    now = timezone.now()
    active_enrollments = CourseEnrollment.objects.filter(_active_enrollment_filter())

    course_qs = Course.objects.filter(is_active=True)
    total_courses = course_qs.count()
    published_courses = course_qs.filter(status=CourseStatus.PUBLISHED).count()

    enrollment_agg = active_enrollments.aggregate(
        total_assignments=Count("id"),
        learners=Count("employee_id", distinct=True),
        assigned=Count("id", filter=Q(status=EnrollmentStatus.ASSIGNED)),
        in_progress=Count("id", filter=Q(status=EnrollmentStatus.IN_PROGRESS)),
        completed=Count("id", filter=Q(status=EnrollmentStatus.COMPLETED)),
        overdue=Count("id", filter=_overdue_filter(now)),
        avg_progress=Avg("progress_percentage"),
    )

    total_assignments = enrollment_agg["total_assignments"] or 0
    completed = enrollment_agg["completed"] or 0
    if total_assignments:
        completion_rate = (Decimal(completed) / Decimal(total_assignments)) * 100
    else:
        completion_rate = Decimal("0")

    avg_progress = enrollment_agg["avg_progress"]
    if avg_progress is None:
        avg_progress = Decimal("0")

    recent_enrollments = (
        active_enrollments.select_related("employee_id", "course_id")
        .order_by("-assigned_at")[:8]
    )

    return {
        "total_courses": total_courses,
        "published_courses": published_courses,
        "draft_courses": course_qs.filter(status=CourseStatus.DRAFT).count(),
        "total_learners": enrollment_agg["learners"] or 0,
        "assigned_enrollments": enrollment_agg["assigned"] or 0,
        "in_progress_enrollments": enrollment_agg["in_progress"] or 0,
        "completed_enrollments": completed,
        "overdue_enrollments": enrollment_agg["overdue"] or 0,
        "total_assignments": total_assignments,
        "completion_rate": completion_rate.quantize(Decimal("0.1")),
        "avg_progress": avg_progress.quantize(Decimal("0.1")),
        "recent_enrollments": recent_enrollments,
    }
