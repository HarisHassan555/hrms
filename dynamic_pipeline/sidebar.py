"""Sidebar entries for dynamic approval pipelines."""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

MENU = _("Pipelines")
IMG_SRC = "images/ui/approve.png"

SUBMENUS = [
    {
        "menu": _("Approval pipelines"),
        "redirect": reverse_lazy("pipeline-list"),
        "accessibility": "dynamic_pipeline.sidebar.configure_accessibility",
    },
    {
        "menu": _("My approvals"),
        "redirect": reverse_lazy("pipeline-approvals"),
    },
]


def configure_accessibility(request, submenu, user_perms, *args, **kwargs):
    user = request.user
    return user.is_superuser or user.has_perm("dynamic_pipeline.change_pipeline")
