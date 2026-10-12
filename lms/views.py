"""
LMS views — placeholder shells until feature UIs are built.
"""

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from lms.models import Course
from lms.services.dashboard import get_lms_dashboard_context


def _hr_lms_access(user):
    return (
        user.has_perm("lms.view_course")
        or user.has_perm("lms.add_course")
        or user.has_perm("lms.view_coursecategory")
        or user.has_perm("lms.view_courseenrollment")
        or user.is_superuser
    )


def _require_hr(user):
    if not _hr_lms_access(user):
        raise PermissionDenied


def _require_employee(user):
    try:
        if not user.employee_get:
            raise PermissionDenied
    except Exception:
        raise PermissionDenied


@login_required
def lms_landing(request):
    if _hr_lms_access(request.user):
        return redirect("lms-dashboard")
    _require_employee(request.user)
    return redirect("lms-my-learning")


@login_required
def lms_dashboard(request):
    _require_hr(request.user)
    context = {
        "title": _("Learning Dashboard"),
        **get_lms_dashboard_context(),
    }
    return render(request, "lms/dashboard.html", context)


@login_required
@permission_required("lms.view_course")
def course_builder(request, course_id):
    course = get_object_or_404(Course.objects, pk=course_id)
    can_edit = request.user.has_perm("lms.change_course") or request.user.is_superuser
    return render(
        request,
        "lms/course_builder.html",
        {
            "title": _("Course builder"),
            "course": course,
            "can_edit": can_edit,
        },
    )


@login_required
def lms_courses(request):
    if not (
        request.user.has_perm("lms.view_course") or request.user.is_superuser
    ):
        raise PermissionDenied
    return render(request, "lms/courses.html", {"title": _("Courses")})


@login_required
def lms_categories(request):
    if not (
        request.user.has_perm("lms.view_coursecategory")
        or request.user.is_superuser
    ):
        raise PermissionDenied
    return render(request, "lms/categories.html", {"title": _("Course Categories")})


@login_required
def lms_my_learning(request):
    _require_employee(request.user)
    return render(request, "lms/my_learning.html", {"title": _("My Learning")})


@login_required
def lms_enrollments(request):
    _require_hr(request.user)
    return render(request, "lms/enrollments.html", {"title": _("Enrollments")})


@login_required
def lms_progress_reports(request):
    _require_hr(request.user)
    return render(
        request,
        "lms/progress_reports.html",
        {"title": _("Progress Reports")},
    )
