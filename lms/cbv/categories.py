"""Course category CRUD (Horilla CBV)."""

from typing import Any

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)
from lms.filters import CourseCategoryFilter
from lms.forms import CourseCategoryForm
from lms.models import CourseCategory


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("lms.view_coursecategory"), name="dispatch")
class CourseCategoryListView(HorillaListView):
    model = CourseCategory
    filter_class = CourseCategoryFilter
    show_toggle_form = False

    columns = [
        (_("Name"), "name"),
        (_("Status"), "get_status_display"),
        (_("Description"), "description_col"),
    ]

    header_attrs = {
        "action": """ style="width:200px !important" """,
    }

    row_attrs = """
        id="lmsCategoryTr{get_delete_instance}"
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("lms-category-list")
        self.actions = []
        if self.request.user.has_perm("lms.change_coursecategory"):
            self.actions.append(
                {
                    "action": _("Edit"),
                    "icon": "create-outline",
                    "attrs": """
                        class="oh-btn oh-btn--light-bkg oh-btn--sq-sm"
                        hx-get='{get_update_url}?instance_ids={ordered_ids}'
                        hx-target="#genericModalBody"
                        data-toggle="oh-modal-toggle"
                        data-target="#genericModal"
                    """,
                }
            )
        if self.request.user.has_perm("lms.delete_coursecategory"):
            self.actions.append(
                {
                    "action": _("Delete"),
                    "icon": "trash-outline",
                    "attrs": """
                        class="oh-btn oh-btn--danger oh-btn--sq-sm"
                        hx-get="{get_delete_url}?model=lms.coursecategory&pk={pk}"
                        data-toggle="oh-modal-toggle"
                        data-target="#deleteConfirmation"
                        hx-target="#deleteConfirmationBody"
                    """,
                }
            )


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("lms.view_coursecategory"), name="dispatch")
class CourseCategoryNavView(HorillaNavView):
    template_name = "generic/inline_nav.html"
    nav_title = _("Course categories")
    search_swap_target = "#lmsCategoryListContainer"
    filter_instance = CourseCategoryFilter()
    modern_filter = True

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("lms-category-list")
        if self.request.user.has_perm("lms.add_coursecategory"):
            self.create_attrs = f"""
                onclick="event.stopPropagation();"
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-target="#genericModalBody"
                hx-get="{reverse('lms-category-create')}"
            """


@method_decorator(login_required, name="dispatch")
class CourseCategoryFormView(HorillaFormView):
    model = CourseCategory
    form_class = CourseCategoryForm
    new_display_title = _("Create category")

    def dispatch(self, request, *args, **kwargs):
        if kwargs.get("pk"):
            if not (
                request.user.has_perm("lms.change_coursecategory")
                or request.user.is_superuser
            ):
                raise PermissionDenied
        elif not (
            request.user.has_perm("lms.add_coursecategory")
            or request.user.is_superuser
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update category")
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update category")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: CourseCategoryForm) -> HttpResponse:
        if form.instance.pk:
            messages.success(self.request, _("Category updated successfully."))
        else:
            messages.success(self.request, _("Category created successfully."))
        form.save()
        return self.HttpResponse()
