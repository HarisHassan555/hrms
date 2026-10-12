"""LMS list filters."""

from django.utils.translation import gettext_lazy as _
from django_filters import CharFilter

from horilla.filters import FilterSet
from lms.models import Course, CourseCategory


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
