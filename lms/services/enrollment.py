"""Self-enroll and HR assignment helpers."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from lms.models import (
    Course,
    CourseEnrollment,
    CourseStatus,
    EnrollmentSource,
    EnrollmentStatus,
)


def published_catalog_qs():
    return (
        Course.objects.filter(
            is_active=True,
            status=CourseStatus.PUBLISHED,
        )
        .select_related("category_id")
        .order_by("title")
    )


def get_employee_enrollment(employee, course):
    if not employee or not course:
        return None
    return (
        CourseEnrollment.objects.filter(
            employee_id=employee,
            course_id=course,
        )
        .exclude(status=EnrollmentStatus.CANCELLED)
        .first()
    )


@transaction.atomic
def self_enroll(*, employee, course, user) -> CourseEnrollment:
    if not employee:
        raise PermissionDenied(_("No employee profile linked to this user."))
    if not course.is_in_catalog():
        raise ValidationError(_("This course is not available in the catalog."))
    if not course.allow_self_enroll:
        raise ValidationError(
            _("This course is assignment-only. Ask HR to enroll you.")
        )

    existing = CourseEnrollment.objects.filter(
        company_id=course.company_id,
        course_id=course,
        employee_id=employee,
    ).first()
    if existing:
        if existing.status == EnrollmentStatus.CANCELLED:
            existing.status = EnrollmentStatus.ASSIGNED
            existing.source = EnrollmentSource.SELF
            existing.assigned_by = user
            existing.save(
                update_fields=["status", "source", "assigned_by", "updated_at"]
            )
        return existing

    return CourseEnrollment.objects.create(
        company_id=course.company_id,
        course_id=course,
        employee_id=employee,
        assigned_by=user,
        source=EnrollmentSource.SELF,
        status=EnrollmentStatus.ASSIGNED,
    )


@transaction.atomic
def assign_course(
    *,
    course,
    employees,
    assigned_by,
    company,
    due_at=None,
    notes=None,
):
    created = []
    for employee in employees:
        enrollment, was_created = CourseEnrollment.objects.get_or_create(
            company_id=company,
            course_id=course,
            employee_id=employee,
            defaults={
                "assigned_by": assigned_by,
                "due_at": due_at,
                "notes": notes,
                "status": EnrollmentStatus.ASSIGNED,
                "source": EnrollmentSource.ASSIGNED,
            },
        )
        if not was_created:
            enrollment.due_at = due_at
            enrollment.notes = notes
            enrollment.source = EnrollmentSource.ASSIGNED
            enrollment.assigned_by = assigned_by
            if enrollment.status == EnrollmentStatus.CANCELLED:
                enrollment.status = EnrollmentStatus.ASSIGNED
            enrollment.save(
                update_fields=[
                    "due_at",
                    "notes",
                    "source",
                    "assigned_by",
                    "status",
                    "updated_at",
                ]
            )
        created.append(enrollment)
    return created
