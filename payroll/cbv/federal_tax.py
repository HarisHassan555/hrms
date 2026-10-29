"""
This page handles the cbv methods for federal tax
"""

import math
from typing import Any

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.methods import paginator_qry
from base.models import Holidays
from horilla_views.cbv_methods import (
    hx_request_required,
    login_required,
    permission_required,
)
from horilla_views.generic.cbv.pipeline import Pipeline
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)
from payroll.filters import FilingStatusFilter, TaxBracketFilter
from payroll.forms.tax_forms import FilingStatusForm, TaxBracketForm
from payroll.models.models import FilingStatus
from payroll.models.tax_models import TaxBracket


def get_or_create_default_filing_status():
    """
    Ensure at least one filing-status group exists so tax slabs can be created.
    """
    filing = FilingStatus.objects.order_by("id").first()
    if filing:
        return filing
    return FilingStatus.objects.create(
        filing_status="Income Tax",
        based_on="basic_pay",
        use_py=False,
        description="",
    )


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.change_filingstatus"), name="dispatch")
class FederalTaxFormView(HorillaFormView):
    """
    Update filing-status group name only (create uses TaxBracketCreateForm).
    """

    form_class = FilingStatusForm
    model = FilingStatus
    new_display_title = _("Update Filing Status")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Filing Status")
        return context

    def form_valid(self, form: FilingStatusForm) -> HttpResponse:
        if form.is_valid():
            form.save()
            messages.success(self.request, _("Filing Status Updated Successfully"))
            return self.HttpResponse("<script>location.reload();</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.view_filingstatus"), name="dispatch")
class FilingStatusDetailView(HorillaDetailedView):
    """
    detail view for filing status, also registered as the related-object-link
    target for FilingStatus via detail_view_url_name
    """

    model = FilingStatus
    detail_view_url_name = "filing-status-detail-view"
    detail_view_permission = "payroll.view_filingstatus"
    title = _("Filing Status")

    header = {
        "title": "filing_status",
        "subtitle": "",
        "avatar": "",
    }

    cols = {"tax_brackets_col": 12}

    body = [
        (_("Filing Status"), "filing_status"),
        (_("Based On"), "get_based_on_display"),
        (_("Description"), "description"),
        (_("Tax Brackets"), "tax_brackets_col", True),
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
@method_decorator(permission_required("payroll.add_taxbracket"), name="dispatch")
class TaxBracketCreateForm(HorillaFormView):
    """
    Create / edit a tax slab with only:
    Income Exceeds, Does Not Exceed, Tax Rate (%), Fixed Amount.
    """

    model = TaxBracket
    form_class = TaxBracketForm
    new_display_title = _("Create Filing Status")

    def _is_page_create(self) -> bool:
        return "create-filing-status" in (self.request.path or "")

    def dispatch(self, request, *args, **kwargs):
        filing_status_id = kwargs.get("filing_status_id")
        if filing_status_id and not FilingStatus.objects.filter(
            id=filing_status_id
        ).exists():
            messages.error(self.request, "Filing status not found.")
            return redirect("filing-status-view")
        # Page-level Create has no filing_status_id — attach to default group.
        if not kwargs.get("pk") and not filing_status_id:
            filing = get_or_create_default_filing_status()
            self.kwargs["filing_status_id"] = filing.pk
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        filing_status_id = self.kwargs.get("filing_status_id")
        if filing_status_id and not self.kwargs.get("pk"):
            initial["filing_status_id"] = filing_status_id
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            title = (
                _("Update Filing Status")
                if self._is_page_create()
                else _("Update Tax Bracket")
            )
            self.form_class.verbose_name = title
            self.new_display_title = title
        else:
            filing_status_id = self.kwargs.get("filing_status_id")
            filling = FilingStatus.objects.filter(id=filing_status_id).first()
            if not filling:
                filling = get_or_create_default_filing_status()
                self.kwargs["filing_status_id"] = filling.pk
            self.form.fields["filing_status_id"].initial = filling
            context["is_create"] = True
            title = (
                _("Create Filing Status")
                if self._is_page_create()
                else _("Create Tax Bracket")
            )
            self.form_class.verbose_name = title
            self.new_display_title = title

        context["form"] = self.form
        return context

    def form_valid(self, form: TaxBracketForm) -> HttpResponse:
        if form.is_valid():
            max_income = form.cleaned_data.get("max_income")
            if not max_income:
                messages.info(self.request, _("The maximum income will be infinite"))
                form.instance.max_income = math.inf

            filing_status = form.cleaned_data.get("filing_status_id")
            if not filing_status:
                fs_id = self.kwargs.get("filing_status_id")
                if fs_id:
                    form.instance.filing_status_id_id = fs_id
                    filing_status = FilingStatus.objects.filter(id=fs_id).first()

            is_update = bool(form.instance.pk)
            form.save()

            if is_update:
                messages.success(
                    self.request, _("The tax bracket has been updated successfully.")
                )
            else:
                messages.success(
                    self.request, _("The tax bracket was created successfully.")
                )

            # Page Create modal: close + reload. Nested create: refresh brackets.
            if self._is_page_create() or not filing_status:
                return self.HttpResponse("<script>location.reload();</script>")

            context = {
                "filing_status_id": filing_status.id,
                "form_instance": form.instance.pk,
            }
            html = render_to_string("cbv/federal_tax/tax_bracket.html", context)
            return HttpResponse(html)
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.view_taxbracket"), name="dispatch")
class TaxBracketNavView(HorillaNavView):
    """
    Nav view for tax bracket list
    """

    nav_title = _("Filing Status")
    search_swap_target = "#FilingStatusList"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_url = f"{reverse_lazy('filing-status-search')}"
        # Create opens the simple 4-field tax slab form.
        self.create_attrs = f"""
            data-toggle="oh-modal-toggle"
            data-target="#objectCreateModal"
            hx-get="{reverse_lazy('create-filing-status')}"
            hx-target="#objectCreateModalTarget"
        """


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
@method_decorator(permission_required("payroll.view_taxbracket"), name="dispatch")
class FilingStatusPipeline(Pipeline):
    """
    Pipeline class for FilingStatus model.
    """

    model = TaxBracket
    filter_class = TaxBracketFilter
    grouper = "filing_status_id"
    template_name = "cbv/federal_tax/pipeline.html"

    allowed_fields = [
        {
            "field": "filing_status_id",
            "model": FilingStatus,
            "filter": FilingStatusFilter,
            "url": reverse_lazy("filing-status-list"),
            "parameters": [
                "filing_status_id={pk}",
            ],
            "actions": [
                {
                    "action": _("Create"),
                    "attrs": """
                        class="oh-dropdown__link oh-dropdown__link"
                        data-toggle="oh-modal-toggle"
                        data-target="#objectCreateModal"
                        hx-get="{get_create_url}"
                        hx-target="#objectCreateModalTarget"
                    """,
                },
                {
                    "action": _("Edit"),
                    "attrs": """
                        class="oh-dropdown__link oh-dropdown__link"
                        data-toggle="oh-modal-toggle"
                        data-target="#objectCreateModal"
                        hx-get="{get_update_url}"
                        hx-target="#objectCreateModalTarget"
                    """,
                },
                {
                    "action": _("Delete"),
                    "attrs": """
                        class="oh-dropdown__link oh-dropdown__link--danger"
                        data-toggle="oh-modal-toggle"
                        data-target="#deleteConfirmation"
                        hx-get="{get_delete_url}"
                        hx-target="#deleteConfirmationBody"
                    """,
                },
            ],
        }
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pipeline renders every FilingStatus row unconditionally with no
        # paging at all - fine with a handful of filing statuses, but it
        # just keeps growing as more get added. Page it like every other
        # list, keeping the total (not just the current page's count) for
        # the tab badge script at the bottom of pipeline.html.
        all_groups = context["groups"]
        context["groups_total_count"] = all_groups.count()
        context["groups"] = paginator_qry(all_groups, self.request.GET.get("page"))

        # quick_actions.html's pagination widget expects these names.
        context["queryset"] = context["groups"]
        context["search_url"] = reverse("filing-status-search")
        preserved_query = self.request.GET.copy()
        preserved_query.pop("page", None)
        context["pd"] = preserved_query.urlencode()
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
@method_decorator(permission_required("payroll.view_taxbracket"), name="dispatch")
class TaxBracketListView(HorillaListView):
    """
    List view for tax brackets
    """

    model = TaxBracket
    filter_class = TaxBracketFilter
    bulk_select_option = False
    template_name = "cbv/federal_tax/tax_bracket_list.html"

    columns = [
        (_("Income Exceeds"), "min_income"),
        (_("Does Not Exceed"), "get_display_max_income"),
        (_("Tax Rate (%)"), "tax_rate"),
        (_("Fixed Amount"), "fixed_amount"),
    ]

    filter_keys_to_remove = ["filing_status_id"]
    header_attrs = {
        "action": """ style="width:90px !important;" """,
    }
    actions = [
        {
            "action": _("Edit"),
            "icon": "create-outline",
            "attrs": """
                class="oh-btn oh-btn--light-bkg oh-btn--sq-sm"
                data-toggle="oh-modal-toggle"
                data-target="#objectCreateModal"
                hx-get="{get_update_url}"
                hx-target="#objectCreateModalTarget"
            """,
        },
        {
            "action": _("delete"),
            "icon": "trash-outline",
            "attrs": """
                class="oh-btn oh-btn--danger oh-btn--sq-sm"
                data-toggle="oh-modal-toggle"
                data-target="#objectCreateModal"
                hx-get="{get_delete_url}"
                hx-target="#objectCreateModalTarget"
            """,
        },
    ]

    def dispatch(self, request, *args, **kwargs):
        if not request.GET.get("filing_status_id"):
            return HttpResponse()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self, queryset=None, filtered=False, *args, **kwargs):
        queryset = super().get_queryset(queryset, filtered, *args, **kwargs)
        queryset = queryset.filter(
            filing_status_id__pk=self.request.GET.get("filing_status_id")
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filing_status_id = self.request.GET.get("filing_status_id")
        filing_status = FilingStatus.objects.filter(pk=filing_status_id).first()
        context["filing_status"] = filing_status
        return context
