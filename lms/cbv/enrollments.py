"""Enrollment list and assign course form."""

from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required as django_login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View

from base.auth_backends import resolve_company_id_for_new_record
from base.models import Company
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaListView, HorillaNavView
from lms.filters import CourseEnrollmentFilter
from lms.forms import CourseAssignForm
from lms.models import Course, CourseEnrollment


def _can_manage_enrollments(user):
    return (
        user.has_perm("lms.view_courseenrollment")
        or user.has_perm("lms.view_course")
        or user.is_superuser
    )


@method_decorator(login_required, name="dispatch")
class EnrollmentListView(HorillaListView):
    model = CourseEnrollment
    filter_class = CourseEnrollmentFilter
    show_toggle_form = False

    def dispatch(self, request, *args, **kwargs):
        if not _can_manage_enrollments(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    columns = [
        (_("Employee"), "employee_id"),
        (_("Course"), "course_id"),
        (_("Source"), "source_badge"),
        (_("Status"), "status_badge"),
        (_("Progress"), "progress_col"),
        (_("Due"), "due_col"),
        (_("Enrolled"), "assigned_at"),
    ]

    header_attrs = {
        "action": """ style="width:120px !important" """,
    }

    row_attrs = """
        id="lmsEnrollmentTr{get_delete_instance}"
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("lms-enrollment-list")
        self.actions = []
        if self.request.user.has_perm("lms.delete_courseenrollment"):
            self.actions.append(
                {
                    "action": _("Delete"),
                    "icon": "trash-outline",
                    "attrs": """
                        class="oh-btn oh-btn--danger oh-btn--sq-sm"
                        hx-get="{get_delete_url}?model=lms.courseenrollment&pk={pk}"
                        data-toggle="oh-modal-toggle"
                        data-target="#deleteConfirmation"
                        hx-target="#deleteConfirmationBody"
                    """,
                }
            )


@method_decorator(login_required, name="dispatch")
class EnrollmentNavView(HorillaNavView):
    template_name = "generic/inline_nav.html"
    nav_title = _("Assignments")
    search_swap_target = "#lmsEnrollmentListContainer"
    filter_instance = CourseEnrollmentFilter()

    def dispatch(self, request, *args, **kwargs):
        if not _can_manage_enrollments(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("lms-enrollment-list")
        self.modern_filter = True
        if (
            self.request.user.has_perm("lms.add_courseenrollment")
            or self.request.user.has_perm("lms.add_course")
            or self.request.user.is_superuser
        ):
            self.create_attrs = f"""
                onclick="event.stopPropagation();"
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-target="#genericModalBody"
                hx-get="{reverse('lms-enrollment-assign')}"
            """


@method_decorator(django_login_required, name="dispatch")
class CourseAssignFormView(View):
    """
    Plain Django View — use django's login_required here.

    Horilla's login_required re-injects request from thread-locals and would
    call get/post with a duplicated request positional argument.
    """

    template_name = "lms/assign_course_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not (
            request.user.has_perm("lms.add_courseenrollment")
            or request.user.has_perm("lms.add_course")
            or request.user.is_superuser
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def _course_from_request(self, request):
        course_id = request.GET.get("course") or request.POST.get("course")
        if course_id and str(course_id).isdigit():
            return Course.objects.filter(
                pk=int(course_id), is_active=True
            ).first()
        return None

    def get(self, request, *args, **kwargs):
        course = self._course_from_request(request)
        form = CourseAssignForm(course=course) if course else CourseAssignForm()
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": _("Assign course"),
                "preselected_course": course,
            },
        )

    def post(self, request, *args, **kwargs):
        course = self._course_from_request(request)
        form = CourseAssignForm(request.POST, course=course)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "title": _("Assign course"),
                    "preselected_course": course,
                },
            )
        company_id = resolve_company_id_for_new_record(request)
        company = None
        if company_id:
            company = Company.objects.filter(pk=company_id).first()
        if company is None:
            company = getattr(form.cleaned_data.get("course"), "company_id", None)
        if not company:
            messages.error(request, _("Unable to resolve company for assignment."))
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "title": _("Assign course"),
                    "preselected_course": course,
                },
            )
        created = form.save(assigned_by=request.user, company=company)
        messages.success(
            request,
            _("%(count)s enrollment(s) saved.") % {"count": len(created)},
        )
        return HttpResponse(
            "<script>"
            "$('.oh-modal--show').removeClass('oh-modal--show');"
            "$('#reloadMessagesButton').click();"
            "htmx.trigger('#lmsEnrollmentListContainer','reload');"
            "window.location.reload();"
            "</script>"
        )
