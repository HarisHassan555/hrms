"""LMS list filters."""

from django.utils.translation import gettext_lazy as _
from django_filters import BooleanFilter, CharFilter

from horilla.filters import FilterSet
from lms.models import Course, CourseCategory, CourseEnrollment, EnrollmentStatus


class CourseFilter(FilterSet):
    search = CharFilter(method="search_method", label=_("Search"))

    def search_method(self, queryset, _name, value):
        if not value:
            return queryset
        return (
            queryset.filter(title__icontains=value)
            | queryset.filter(code__icontains=value)
            | queryset.filter(description__icontains=value)
        ).distinct()

    class Meta:
        model = Course
        fields = [
            "search",
            "status",
            "difficulty",
            "category_id",
        ]


class CourseCategoryFilter(FilterSet):
    search = CharFilter(method="search_method", label=_("Search"))

    def search_method(self, queryset, _name, value):
        if not value:
            return queryset
        return (
            queryset.filter(name__icontains=value)
            | queryset.filter(description__icontains=value)
        ).distinct()

    class Meta:
        model = CourseCategory
        fields = ["search", "status"]


class CourseEnrollmentFilter(FilterSet):
    search = CharFilter(method="search_method", label=_("Search"))
    overdue = BooleanFilter(method="overdue_method", label=_("Overdue only"))

    def search_method(self, queryset, _name, value):
        if not value:
            return queryset
        return (
            queryset.filter(course_id__title__icontains=value)
            | queryset.filter(employee_id__employee_first_name__icontains=value)
            | queryset.filter(employee_id__employee_last_name__icontains=value)
            | queryset.filter(employee_id__badge_id__icontains=value)
        ).distinct()

    def overdue_method(self, queryset, _name, value):
        if not value:
            return queryset
        from django.utils import timezone

        now = timezone.now()
        return queryset.filter(due_at__lt=now).exclude(
            status__in=[EnrollmentStatus.COMPLETED, EnrollmentStatus.CANCELLED]
        )

    class Meta:
        model = CourseEnrollment
        fields = [
            "search",
            "course_id",
            "employee_id",
            "status",
            "source",
        ]
