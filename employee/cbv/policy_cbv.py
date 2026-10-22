"""
Policy  forms
"""

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from employee.filters import PolicyFilter
from employee.forms import PolicyForm, build_policy_slide_formset
from employee.models import Policy
from horilla.methods import handle_no_permission
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaFormView, HorillaNavView


def _sync_policy_body_from_pages(policy):
    page_count = policy.slides.count()
    policy.body = ""
    if page_count > 1:
        policy.body_format = Policy.BodyFormat.SLIDESHOW
    elif page_count == 1:
        policy.body_format = Policy.BodyFormat.SINGLE
    else:
        policy.body_format = Policy.BodyFormat.SINGLE
    policy.save(update_fields=["body", "body_format"])


@method_decorator(login_required, name="dispatch")
class PolicyFormView(HorillaFormView):
    """
    form view for create policy
    """

    form_class = PolicyForm
    model = Policy
    new_display_title = _("Policy Creation")
    template_name = "policies/policy_form.html"

    def dispatch(self, request, *args, **kwargs):
        is_update = bool(kwargs.get("pk") or request.GET.get("instance_id"))
        perm = (
            "employee.change_policy" if is_update else "employee.add_policy"
        )
        if not request.user.has_perm(perm):
            return handle_no_permission(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Policy Update")
        instance = self.get_queryset()
        if kwargs.get("slide_formset") is not None:
            context["slide_formset"] = kwargs["slide_formset"]
        elif self.request.method == "POST":
            context["slide_formset"] = build_policy_slide_formset(
                instance=instance,
                data=self.request.POST,
                files=self.request.FILES,
            )
        else:
            context["slide_formset"] = build_policy_slide_formset(instance=instance)
        if (
            instance
            and instance.pk
            and not instance.slides.exists()
            and (instance.body or "").strip()
        ):
            context["legacy_policy_body"] = instance.body
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if not form.is_valid():
            return self.form_invalid(form)

        was_update = self.get_queryset() is not None
        save_result = form.save()
        policy = save_result[0] if isinstance(save_result, tuple) else save_result

        slide_formset = build_policy_slide_formset(
            instance=policy,
            data=request.POST,
            files=request.FILES,
        )
        if not slide_formset.is_valid():
            messages.error(
                request,
                _(
                    "Policy was saved but some pages could not be saved. "
                    "Fix the errors and save again."
                ),
            )
            return self.render_to_response(
                self.get_context_data(form=form, slide_formset=slide_formset)
            )
        slide_formset.save()
        if not policy.slides.exists():
            messages.error(
                request,
                _("Add at least one page with text or an image in the policy body."),
            )
            return self.render_to_response(
                self.get_context_data(form=form, slide_formset=slide_formset)
            )
        _sync_policy_body_from_pages(policy)

        message = _("Policy updated") if was_update else _("Policy saved")
        messages.success(request, message)
        return self.HttpResponse(targets_to_reload=["#policyContainerReload"])


@method_decorator(login_required, name="dispatch")
class PoliciesNav(HorillaNavView):
    """
    Policies Nav
    """

    nav_title = _("Policies")
    search_url = reverse_lazy("search-policies")
    search_swap_target = "#policyContainer"
    template_name = "generic/inline_nav.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.request.user.has_perm("employee.add_policy"):
            self.create_attrs = f"""
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-get="{reverse_lazy('create-policy')}"
                hx-target="#genericModalBody"
            """
