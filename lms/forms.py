"""LMS model forms."""

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.auth_backends import resolve_company_id_for_new_record
from base.forms import ModelForm
from horilla import horilla_middlewares
from lms.models import (
    Course,
    CourseCategory,
    CourseCategoryStatus,
    CourseModule,
    CourseStatus,
    Lesson,
    LessonType,
)


class CourseCategoryForm(ModelForm):
    cols = {
        "name": 12,
        "status": 6,
        "description": 12,
    }

    class Meta:
        model = CourseCategory
        fields = ["name", "description", "status"]

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name:
            return name
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        company_id = resolve_company_id_for_new_record(request)
        qs = CourseCategory.objects.filter(name__iexact=name.strip())
        if company_id:
            qs = qs.filter(company_id_id=company_id)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                _("A category with this name already exists for this company.")
            )
        return name.strip()


class CourseForm(ModelForm):
    cols = {
        "title": 12,
        "code": 6,
        "category_id": 6,
        "status": 6,
        "difficulty": 6,
        "duration_minutes": 6,
        "thumbnail": 12,
        "description": 12,
    }

    class Meta:
        model = Course
        fields = [
            "title",
            "code",
            "category_id",
            "description",
            "thumbnail",
            "difficulty",
            "duration_minutes",
            "status",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category_id"].queryset = CourseCategory.objects.filter(
            is_active=True,
            status=CourseCategoryStatus.ACTIVE,
        )
        self.fields["category_id"].required = False

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip()
        if not code:
            return None
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        company_id = resolve_company_id_for_new_record(request)
        qs = Course.objects.filter(code__iexact=code)
        if company_id:
            qs = qs.filter(company_id_id=company_id)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                _("A course with this code already exists for this company.")
            )
        return code

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.status == CourseStatus.PUBLISHED and not instance.published_at:
            instance.published_at = timezone.now()
        if commit:
            instance.save()
        return instance


class CourseModuleForm(ModelForm):
    cols = {
        "title": 12,
        "sort_order": 4,
        "description": 12,
    }

    class Meta:
        model = CourseModule
        fields = ["title", "description", "sort_order"]


class LessonForm(ModelForm):
    cols = {
        "title": 12,
        "type": 6,
        "sort_order": 6,
        "duration_minutes": 6,
        "video_url": 12,
        "file_path": 12,
        "description": 12,
        "content": 12,
    }

    class Meta:
        model = Lesson
        fields = [
            "title",
            "description",
            "type",
            "video_url",
            "file_path",
            "content",
            "duration_minutes",
            "sort_order",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["video_url"].help_text = _("Required for video lessons.")
        self.fields["file_path"].help_text = _("URL or storage path for PDF lessons.")
        self.fields["content"].help_text = _("Required for text lessons.")
        self.fields["sort_order"].required = False

    def clean(self):
        cleaned = super().clean()
        lesson_type = cleaned.get("type")
        if lesson_type == LessonType.VIDEO and not (cleaned.get("video_url") or "").strip():
            self.add_error("video_url", _("Video URL is required for video lessons."))
        if lesson_type == LessonType.PDF and not (cleaned.get("file_path") or "").strip():
            self.add_error("file_path", _("File path is required for PDF lessons."))
        if lesson_type == LessonType.TEXT and not (cleaned.get("content") or "").strip():
            self.add_error("content", _("Content is required for text lessons."))
        return cleaned
