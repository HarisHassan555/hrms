"""LMS model forms."""

from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.auth_backends import resolve_company_id_for_new_record
from base.forms import ModelForm
from employee.filters import EmployeeFilter
from employee.models import Employee
from horilla import horilla_middlewares
from horilla_widgets.widgets.horilla_multi_select_field import HorillaMultiSelectField
from horilla_widgets.widgets.select_widgets import HorillaMultiSelectWidget
from lms.models import (
    ChapterTest,
    Course,
    CourseCategory,
    CourseCategoryStatus,
    CourseModule,
    CourseStatus,
    Lesson,
    LessonSlide,
    LessonType,
    QuestionType,
    TestChoice,
    TestQuestion,
    normalize_video_embed_url,
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
        "category_id": 6,
        "code": 6,
        "difficulty": 6,
        "status": 6,
        "allow_self_enroll": 6,
        "description": 12,
    }

    class Meta:
        model = Course
        fields = [
            "title",
            "category_id",
            "code",
            "difficulty",
            "status",
            "allow_self_enroll",
            "description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category_id"].queryset = CourseCategory.objects.filter(
            is_active=True,
            status=CourseCategoryStatus.ACTIVE,
        ).order_by("name")
        self.fields["category_id"].required = False
        self.fields["category_id"].empty_label = _("Select category")
        self.fields["category_id"].help_text = _(
            "Group this course under a catalog category."
        )
        self.fields["title"].help_text = _("Name learners will see in the catalog.")
        self.fields["code"].required = False
        self.fields["code"].help_text = _(
            "Optional short ID (for example ONB-101)."
        )
        self.fields["description"].required = False
        self.fields["description"].help_text = _(
            "Shown on the catalog card and course page."
        )
        self.fields["difficulty"].help_text = _("Expected learner level.")
        self.fields["status"].help_text = _(
            "Only Published courses appear in the catalog."
        )
        self.fields["allow_self_enroll"].help_text = _(
            "If on, learners can enroll from the catalog. If off, HR must assign."
        )
        if "description" in self.fields:
            self.fields["description"].widget.attrs.setdefault("rows", 3)

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
            "sort_order",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["video_url"].label = _("Video URL")
        self.fields["video_url"].help_text = _(
            "For Video lessons only. Paste a YouTube link "
            "(youtu.be, watch, or embed) — it is converted for playback automatically."
        )
        self.fields["file_path"].label = _("PDF file URL")
        self.fields["file_path"].help_text = _(
            "For PDF lessons only. Link to a PDF file learners can open in the player. "
            "Leave blank for Video / Text / Slideshow."
        )
        self.fields["content"].label = _("Lesson text")
        self.fields["content"].help_text = _(
            "For Text lessons only. Written body shown in the player. "
            "Leave blank for Video / PDF / Slideshow."
        )
        self.fields["video_url"].required = False
        self.fields["file_path"].required = False
        self.fields["content"].required = False
        self.fields["sort_order"].required = False

    def clean_video_url(self):
        return normalize_video_embed_url(self.cleaned_data.get("video_url") or "")

    def clean(self):
        cleaned = super().clean()
        lesson_type = cleaned.get("type")
        if lesson_type == LessonType.VIDEO and not (cleaned.get("video_url") or "").strip():
            self.add_error("video_url", _("Video URL is required for video lessons."))
        if lesson_type == LessonType.PDF and not (cleaned.get("file_path") or "").strip():
            self.add_error("file_path", _("PDF file URL is required for PDF lessons."))
        if lesson_type == LessonType.TEXT and not (cleaned.get("content") or "").strip():
            self.add_error("content", _("Lesson text is required for text lessons."))
        return cleaned


class LessonSlideForm(ModelForm):
    class Meta:
        model = LessonSlide
        fields = ["sort_order", "title", "body", "image"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "sort_order": forms.HiddenInput(),
            "title": forms.TextInput(attrs={"placeholder": _("Slide title (optional)")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sort_order"].required = False
        self.fields["image"].required = False
        self.fields["title"].required = False
        self.fields["body"].required = False


def build_lesson_slide_formset(instance=None, data=None, files=None):
    extra = 0
    if not instance or not instance.pk or not instance.slides.exists():
        extra = 1
    factory = inlineformset_factory(
        Lesson,
        LessonSlide,
        form=LessonSlideForm,
        extra=extra,
        can_delete=True,
        min_num=0,
        validate_min=False,
        max_num=40,
    )
    if data is not None:
        return factory(data, files, instance=instance)
    return factory(instance=instance)


class ChapterTestForm(ModelForm):
    cols = {
        "title": 12,
        "is_compulsory": 6,
        "pass_score": 6,
    }

    class Meta:
        model = ChapterTest
        fields = ["title", "is_compulsory", "pass_score"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_compulsory") and cleaned.get("pass_score") is None:
            self.add_error(
                "pass_score", _("Pass score is required for compulsory tests.")
            )
        return cleaned


class TestQuestionForm(ModelForm):
    choice_1 = forms.CharField(required=False, label=_("Choice A"), max_length=500)
    choice_2 = forms.CharField(required=False, label=_("Choice B"), max_length=500)
    choice_3 = forms.CharField(required=False, label=_("Choice C"), max_length=500)
    choice_4 = forms.CharField(required=False, label=_("Choice D"), max_length=500)
    correct_choice = forms.ChoiceField(
        required=False,
        label=_("Correct choice"),
        choices=[
            ("1", _("Choice A")),
            ("2", _("Choice B")),
            ("3", _("Choice C")),
            ("4", _("Choice D")),
        ],
    )
    true_false_answer = forms.ChoiceField(
        required=False,
        label=_("Correct answer"),
        choices=[("true", _("True")), ("false", _("False"))],
        initial="true",
    )

    cols = {
        "prompt": 12,
        "question_type": 6,
        "points": 6,
        "sort_order": 6,
        "true_false_answer": 6,
        "choice_1": 12,
        "choice_2": 12,
        "choice_3": 12,
        "choice_4": 12,
        "correct_choice": 6,
    }

    class Meta:
        model = TestQuestion
        fields = ["prompt", "question_type", "points", "sort_order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sort_order"].required = False
        self.fields["points"].required = False
        self.fields["question_type"].widget.attrs.update(
            {
                "onchange": "if (window.lmsToggleQuestionAnswerFields) { window.lmsToggleQuestionAnswerFields(); }",
            }
        )
        if self.instance.pk and self.instance.question_type == QuestionType.MCQ:
            choices = list(
                self.instance.choices.filter(is_active=True).order_by("sort_order", "id")
            )
            for idx, choice in enumerate(choices[:4], start=1):
                self.fields[f"choice_{idx}"].initial = choice.label
                if choice.is_correct:
                    self.fields["correct_choice"].initial = str(idx)
        elif self.instance.pk and self.instance.question_type == QuestionType.TRUE_FALSE:
            correct = (
                self.instance.choices.filter(is_correct=True, is_active=True)
                .order_by("sort_order")
                .first()
            )
            if correct and correct.label.lower() == "false":
                self.fields["true_false_answer"].initial = "false"

    def clean(self):
        cleaned = super().clean()
        qtype = cleaned.get("question_type")
        if qtype == QuestionType.MCQ:
            labels = [
                (cleaned.get("choice_1") or "").strip(),
                (cleaned.get("choice_2") or "").strip(),
                (cleaned.get("choice_3") or "").strip(),
                (cleaned.get("choice_4") or "").strip(),
            ]
            filled = [label for label in labels if label]
            if len(filled) < 2:
                self.add_error("choice_1", _("Provide at least two choices."))
            correct = cleaned.get("correct_choice") or "1"
            try:
                correct_idx = int(correct) - 1
            except (TypeError, ValueError):
                correct_idx = 0
            if correct_idx < 0 or correct_idx > 3 or not labels[correct_idx]:
                self.add_error(
                    "correct_choice", _("Select a correct choice that has a label.")
                )
        elif qtype == QuestionType.TRUE_FALSE:
            if not cleaned.get("true_false_answer"):
                self.add_error(
                    "true_false_answer", _("Select True or False as the correct answer.")
                )
        return cleaned

    def save_with_choices(self, test):
        question = self.save(commit=False)
        question.test = test
        if not question.points:
            question.points = 1
        question.save()
        question.choices.all().delete()
        if question.question_type == QuestionType.TRUE_FALSE:
            answer = self.cleaned_data.get("true_false_answer") or "true"
            TestChoice.objects.create(
                question=question,
                label=_("True"),
                is_correct=answer == "true",
                sort_order=0,
            )
            TestChoice.objects.create(
                question=question,
                label=_("False"),
                is_correct=answer == "false",
                sort_order=1,
            )
        else:
            labels = [
                (self.cleaned_data.get("choice_1") or "").strip(),
                (self.cleaned_data.get("choice_2") or "").strip(),
                (self.cleaned_data.get("choice_3") or "").strip(),
                (self.cleaned_data.get("choice_4") or "").strip(),
            ]
            correct = self.cleaned_data.get("correct_choice") or "1"
            correct_idx = int(correct) - 1
            order = 0
            for idx, label in enumerate(labels):
                if not label:
                    continue
                TestChoice.objects.create(
                    question=question,
                    label=label,
                    is_correct=idx == correct_idx,
                    sort_order=order,
                )
                order += 1
        return question


class CourseAssignForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.none(),
        label=_("Course"),
    )
    employees = HorillaMultiSelectField(
        queryset=Employee.objects.filter(is_active=True),
        widget=HorillaMultiSelectWidget(
            filter_route_name="employee-widget-filter",
            filter_class=EmployeeFilter,
            filter_instance_context_name="f",
            filter_template_path="employee_filters.html",
            required=True,
        ),
        label=_("Employees"),
        required=True,
    )
    due_at = forms.DateTimeField(
        required=False,
        label=_("Deadline"),
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": "form-control"}
        ),
    )
    notes = forms.CharField(
        required=False,
        label=_("Notes"),
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        initial_course = kwargs.pop("course", None)
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Course.objects.filter(
            is_active=True, status=CourseStatus.PUBLISHED
        ).order_by("title")
        self.fields["employees"].queryset = Employee.objects.filter(is_active=True)
        if initial_course:
            self.fields["course"].initial = initial_course
            self.fields["course"].queryset = Course.objects.filter(
                pk=initial_course.pk
            ) | self.fields["course"].queryset

    def save(self, assigned_by, company):
        from lms.services.enrollment import assign_course

        return assign_course(
            course=self.cleaned_data["course"],
            employees=self.cleaned_data["employees"],
            assigned_by=assigned_by,
            company=company,
            due_at=self.cleaned_data.get("due_at"),
            notes=self.cleaned_data.get("notes") or None,
        )
