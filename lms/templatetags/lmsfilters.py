from django import template

from lms.models import EnrollmentStatus

register = template.Library()

_ENROLLMENT_BADGE = {
    EnrollmentStatus.ASSIGNED: "md-badge--blue",
    EnrollmentStatus.IN_PROGRESS: "md-badge--amber",
    EnrollmentStatus.COMPLETED: "md-badge--green",
    EnrollmentStatus.OVERDUE: "md-badge--red",
    EnrollmentStatus.CANCELLED: "md-badge--purple",
}


@register.filter
def enrollment_status_badge(status):
    return _ENROLLMENT_BADGE.get(status, "md-badge--blue")
