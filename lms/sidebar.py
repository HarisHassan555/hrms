"""
LMS sidebar — catalog-first Learning navigation.
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

MENU = _("Learning")
IMG_SRC = "images/ui/learning.svg"
ACCESSIBILITY = "lms.sidebar.learning_menu_accessibility"

SUBMENUS = [
    {
        "menu": _("Catalog"),
        "redirect": reverse_lazy("lms-catalog"),
        "accessibility": "lms.sidebar.catalog_accessibility",
        "match_prefixes": [
            "/learning/catalog/",
        ],
    },
    {
        "menu": _("My Learning"),
        "redirect": reverse_lazy("lms-my-learning"),
        "accessibility": "lms.sidebar.my_learning_accessibility",
        "match_prefixes": [
            "/learning/my-learning/",
            "/learning/player/",
        ],
    },
    {
        "menu": _("Dashboard"),
        "redirect": reverse_lazy("lms-dashboard"),
        "accessibility": "lms.sidebar.hr_admin_accessibility",
        "match_prefixes": [
            "/learning/dashboard/",
        ],
    },
    {
        "menu": _("Manage courses"),
        "redirect": reverse_lazy("lms-courses"),
        "accessibility": "lms.sidebar.hr_admin_accessibility",
        "match_prefixes": [
            "/learning/courses/",
        ],
    },
    {
        "menu": _("Categories"),
        "redirect": reverse_lazy("lms-categories"),
        "accessibility": "lms.sidebar.hr_admin_accessibility",
        "match_prefixes": [
            "/learning/categories/",
        ],
    },
    {
        "menu": _("Assignments"),
        "redirect": reverse_lazy("lms-enrollments"),
        "accessibility": "lms.sidebar.hr_admin_accessibility",
        "match_prefixes": [
            "/learning/enrollments/",
        ],
    },
    {
        "menu": _("Progress Reports"),
        "redirect": reverse_lazy("lms-progress-reports"),
        "accessibility": "lms.sidebar.hr_admin_accessibility",
        "match_prefixes": [
            "/learning/progress-reports/",
        ],
    },
]


def learning_menu_accessibility(request, menu, user_perms, *args, **kwargs):
    return hr_admin_accessibility(request, menu, user_perms, *args, **kwargs) or (
        my_learning_accessibility(request, menu, user_perms, *args, **kwargs)
    )


def catalog_accessibility(request, submenu, user_perms, *args, **kwargs):
    return my_learning_accessibility(
        request, submenu, user_perms, *args, **kwargs
    ) or hr_admin_accessibility(request, submenu, user_perms, *args, **kwargs)


def hr_admin_accessibility(request, submenu, user_perms, *args, **kwargs):
    user = request.user
    return (
        user.has_perm("lms.view_course")
        or user.has_perm("lms.add_course")
        or user.has_perm("lms.view_coursecategory")
        or user.has_perm("lms.view_courseenrollment")
        or user.is_superuser
    )


def my_learning_accessibility(request, submenu, user_perms, *args, **kwargs):
    if not request.user.is_authenticated:
        return False
    try:
        return bool(request.user.employee_get)
    except Exception:
        return False
