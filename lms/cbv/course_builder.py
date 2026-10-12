"""Course builder — modules and lessons."""

from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Max, Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required as cbv_login_required
from horilla_views.generic.cbv.views import HorillaFormView
from lms.forms import CourseModuleForm, LessonForm
from lms.models import Course, CourseModule, Lesson


def _builder_reload_response() -> HttpResponse:
    return HttpResponse(
        "<script>"
        "$('.oh-modal--show').removeClass('oh-modal--show');"
        "$('#lmsBuilderReload').click();"
        "$('#reloadMessagesButton').click();"
        "</script>"
    )


def _get_course(course_id):
    return get_object_or_404(Course.objects, pk=course_id)


def _require_change_course(user):
    if not (user.has_perm("lms.change_course") or user.is_superuser):
        raise PermissionDenied


@login_required
@permission_required("lms.view_course")
def course_builder_panel(request, course_id):
    course = _get_course(course_id)
    lesson_qs = Lesson.objects.filter(is_active=True).order_by("sort_order", "id")
    modules = (
        course.modules.filter(is_active=True)
        .prefetch_related(Prefetch("lessons", queryset=lesson_qs))
        .order_by("sort_order", "id")
    )
    for module in modules:
        module.lesson_list = list(module.lessons.all())
    can_edit = request.user.has_perm("lms.change_course") or request.user.is_superuser
    return render(
        request,
        "lms/course_builder_content.html",
        {
            "course": course,
            "modules": modules,
            "can_edit": can_edit,
        },
    )


@method_decorator(cbv_login_required, name="dispatch")
class CourseModuleFormView(HorillaFormView):
    model = CourseModule
    form_class = CourseModuleForm
    new_display_title = _("Add module")

    def dispatch(self, request, *args, **kwargs):
        _get_course(kwargs["course_id"])
        if kwargs.get("pk"):
            _require_change_course(request.user)
        else:
            _require_change_course(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        if not pk:
            return None
        return CourseModule.objects.filter(
            pk=pk,
            course_id_id=self.kwargs["course_id"],
            is_active=True,
        ).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update module")
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update module")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: CourseModuleForm) -> HttpResponse:
        module = form.save(commit=False)
        module.course_id_id = self.kwargs["course_id"]
        if not module.pk and not module.sort_order:
            current_max = (
                CourseModule.objects.filter(course_id_id=self.kwargs["course_id"]).aggregate(
                    Max("sort_order")
                )["sort_order__max"]
                or 0
            )
            module.sort_order = current_max + 1
        module.save()
        if form.instance.pk:
            messages.success(self.request, _("Module updated successfully."))
        else:
            messages.success(self.request, _("Module added successfully."))
        return _builder_reload_response()


@method_decorator(cbv_login_required, name="dispatch")
class LessonFormView(HorillaFormView):
    model = Lesson
    form_class = LessonForm
    new_display_title = _("Add lesson")

    def dispatch(self, request, *args, **kwargs):
        self._module = get_object_or_404(
            CourseModule.objects.select_related("course_id"),
            pk=kwargs["module_id"],
            is_active=True,
        )
        _get_course(self._module.course_id_id)
        _require_change_course(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        if not pk:
            return None
        return Lesson.objects.filter(
            pk=pk,
            module_id_id=self.kwargs["module_id"],
            is_active=True,
        ).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update lesson")
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update lesson")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: LessonForm) -> HttpResponse:
        lesson = form.save(commit=False)
        lesson.module_id = self._module
        if not lesson.pk and not lesson.sort_order:
            current_max = (
                Lesson.objects.filter(module_id=self._module).aggregate(
                    Max("sort_order")
                )["sort_order__max"]
                or 0
            )
            lesson.sort_order = current_max + 1
        lesson.save()
        if form.instance.pk:
            messages.success(self.request, _("Lesson updated successfully."))
        else:
            messages.success(self.request, _("Lesson added successfully."))
        return _builder_reload_response()
