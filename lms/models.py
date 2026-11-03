"""
LMS models — categories, courses, chapters, lessons, tests, enrollments, progress.
"""

import re
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company
from employee.models import Employee
from horilla.models import HorillaModel

User = settings.AUTH_USER_MODEL


def _lesson_slide_upload(instance, filename):
    return f"lms/lesson_slides/{instance.lesson_id or 'new'}/{filename}"


def normalize_video_embed_url(url: str) -> str:
    """
    Convert common YouTube share/watch links into iframe-ready embed URLs.
    Leaves already-valid embed URLs and non-YouTube URLs unchanged.
    """
    raw = (url or "").strip()
    if not raw:
        return raw

    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower().replace("www.", "")
    path = parsed.path or ""

    video_id = None
    if host in {"youtu.be"}:
        video_id = path.strip("/").split("/")[0] or None
    elif host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        if path.startswith("/embed/"):
            embed_id = path.strip("/").split("/")[-1]
            if embed_id:
                return f"https://www.youtube.com/embed/{embed_id}"
            return raw
        parts = [p for p in path.split("/") if p]
        if parts and parts[0] in {"shorts", "live", "v"} and len(parts) >= 2:
            video_id = parts[1]
        elif path.startswith("/watch") or "v=" in (parsed.query or ""):
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        if not video_id:
            match = re.search(r"/(?:live|v)/([A-Za-z0-9_-]{6,})", path)
            if match:
                video_id = match.group(1)

    if video_id:
        video_id = video_id.split("?")[0].split("&")[0]
        return f"https://www.youtube.com/embed/{video_id}"

    return raw


def extract_youtube_video_id(url: str) -> str | None:
    """Return the YouTube video id from a watch/share/embed URL, if present."""
    embed = normalize_video_embed_url(url or "")
    if not embed:
        return None
    parsed = urlparse(embed)
    host = (parsed.netloc or "").lower().replace("www.", "")
    path = (parsed.path or "").strip("/")
    if host in {"youtube.com", "m.youtube.com", "youtube-nocookie.com"} and path.startswith(
        "embed/"
    ):
        video_id = path.split("/", 1)[1].split("/")[0]
        return video_id or None
    if host == "youtu.be":
        return path.split("/")[0] or None
    return None


class CourseCategoryStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")


class CourseDifficulty(models.TextChoices):
    BEGINNER = "beginner", _("Beginner")
    INTERMEDIATE = "intermediate", _("Intermediate")
    ADVANCED = "advanced", _("Advanced")


class CourseStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")
    ARCHIVED = "archived", _("Archived")


class LessonType(models.TextChoices):
    VIDEO = "video", _("Video")
    PDF = "pdf", _("PDF")
    TEXT = "text", _("Text")
    SLIDESHOW = "slideshow", _("Slideshow")


class EnrollmentStatus(models.TextChoices):
    ASSIGNED = "assigned", _("Enrolled")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    OVERDUE = "overdue", _("Overdue")
    CANCELLED = "cancelled", _("Cancelled")


class EnrollmentSource(models.TextChoices):
    ASSIGNED = "assigned", _("Assigned")
    SELF = "self", _("Self-enrolled")


class LessonProgressStatus(models.TextChoices):
    NOT_STARTED = "not_started", _("Not started")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")


class QuestionType(models.TextChoices):
    MCQ = "mcq", _("Multiple choice")
    TRUE_FALSE = "true_false", _("True / False")


class CourseCategory(HorillaModel):
    company_id = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="lms_course_categories",
        verbose_name=_("Company"),
    )
    name = models.CharField(max_length=150, verbose_name=_("Name"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    status = models.CharField(
        max_length=20,
        choices=CourseCategoryStatus.choices,
        default=CourseCategoryStatus.ACTIVE,
        verbose_name=_("Status"),
    )

    objects = HorillaCompanyManager(related_company_field="company_id")

    class Meta:
        verbose_name = _("Course category")
        verbose_name_plural = _("Course categories")
        constraints = [
            models.UniqueConstraint(
                fields=["company_id", "name"],
                name="lms_unique_category_name_per_company",
            ),
        ]
        indexes = [
            models.Index(fields=["company_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from base.auth_backends import stamp_company_on_create

        stamp_company_on_create(self)
        super().save(*args, **kwargs)

    def description_col(self):
        if not self.description:
            return "—"
        text = self.description.strip()
        return text if len(text) <= 80 else f"{text[:77]}..."

    def get_update_url(self):
        return reverse_lazy("lms-category-update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("generic-delete")

    def get_delete_instance(self):
        return self.pk

    def get_instance_id(self):
        return self.pk


class Course(HorillaModel):
    company_id = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="lms_courses",
        verbose_name=_("Company"),
    )
    category_id = models.ForeignKey(
        CourseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
        verbose_name=_("Category"),
    )
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Code"),
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    difficulty = models.CharField(
        max_length=20,
        choices=CourseDifficulty.choices,
        default=CourseDifficulty.BEGINNER,
        verbose_name=_("Difficulty"),
    )
    status = models.CharField(
        max_length=20,
        choices=CourseStatus.choices,
        default=CourseStatus.DRAFT,
        verbose_name=_("Status"),
    )
    allow_self_enroll = models.BooleanField(
        default=True,
        verbose_name=_("Open enrollment"),
        help_text=_("Learners can enroll themselves from the catalog."),
    )
    published_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Published at"),
    )

    objects = HorillaCompanyManager(related_company_field="company_id")

    class Meta:
        verbose_name = _("Course")
        verbose_name_plural = _("Courses")
        constraints = [
            models.UniqueConstraint(
                fields=["company_id", "code"],
                name="lms_unique_course_code_per_company",
                condition=models.Q(code__isnull=False) & ~models.Q(code=""),
            ),
        ]
        indexes = [
            models.Index(fields=["company_id"]),
            models.Index(fields=["category_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        from base.auth_backends import stamp_company_on_create

        stamp_company_on_create(self)
        super().save(*args, **kwargs)

    def category_col(self):
        if self.category_id:
            return self.category_id.name
        return "—"

    def open_enroll_col(self):
        return _("Yes") if self.allow_self_enroll else _("No")

    def is_in_catalog(self):
        return self.is_active and self.status == CourseStatus.PUBLISHED

    def chapter_count(self):
        return self.modules.filter(is_active=True).count()

    def lesson_count(self):
        return Lesson.objects.filter(
            module_id__course_id=self, module_id__is_active=True, is_active=True
        ).count()

    def get_catalog_url(self):
        return reverse_lazy("lms-course-detail", kwargs={"pk": self.pk})

    def get_builder_url(self):
        return reverse_lazy("lms-course-builder", kwargs={"course_id": self.pk})

    def get_update_url(self):
        return reverse_lazy("lms-course-update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("generic-delete")

    def get_delete_instance(self):
        return self.pk

    def get_instance_id(self):
        return self.pk


class CourseModule(HorillaModel):
    """Chapter within a course (UI label: Chapter)."""

    course_id = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="modules",
        verbose_name=_("Course"),
    )
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("Sort order"))

    class Meta:
        verbose_name = _("Chapter")
        verbose_name_plural = _("Chapters")
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["course_id"]),
        ]

    def __str__(self):
        return self.title

    def get_update_url(self):
        return reverse_lazy(
            "lms-module-update",
            kwargs={"course_id": self.course_id_id, "pk": self.pk},
        )

    def get_delete_url(self):
        return reverse_lazy("generic-delete")

    def get_delete_instance(self):
        return self.pk


class Lesson(HorillaModel):
    module_id = models.ForeignKey(
        CourseModule,
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name=_("Chapter"),
    )
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    type = models.CharField(
        max_length=12,
        choices=LessonType.choices,
        verbose_name=_("Type"),
    )
    content = models.TextField(blank=True, null=True, verbose_name=_("Content"))
    file_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("File path"),
    )
    video_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("Video URL"),
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("Sort order"))

    class Meta:
        verbose_name = _("Lesson")
        verbose_name_plural = _("Lessons")
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["module_id"]),
        ]

    def __str__(self):
        return self.title

    def get_update_url(self):
        return reverse_lazy(
            "lms-lesson-update",
            kwargs={"module_id": self.module_id_id, "pk": self.pk},
        )

    def get_delete_url(self):
        return reverse_lazy("generic-delete")

    def get_delete_instance(self):
        return self.pk

    def type_badge(self):
        return self.get_type_display()

    @property
    def embed_video_url(self):
        return normalize_video_embed_url(self.video_url or "")


class LessonSlide(HorillaModel):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="slides",
        verbose_name=_("Lesson"),
    )
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Sort order"))
    title = models.CharField(
        max_length=120, blank=True, verbose_name=_("Slide title")
    )
    body = models.TextField(blank=True, verbose_name=_("Slide text"))
    image = models.ImageField(
        upload_to=_lesson_slide_upload,
        blank=True,
        null=True,
        verbose_name=_("Slide image"),
    )

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = _("Lesson slide")
        verbose_name_plural = _("Lesson slides")

    def __str__(self):
        label = self.title or _("Slide")
        return f"{label} ({self.lesson_id})"


class ChapterTest(HorillaModel):
    module = models.OneToOneField(
        CourseModule,
        on_delete=models.CASCADE,
        related_name="chapter_test",
        verbose_name=_("Chapter"),
    )
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    is_compulsory = models.BooleanField(
        default=False, verbose_name=_("Compulsory")
    )
    pass_score = models.PositiveSmallIntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Pass score (%)"),
        help_text=_("Minimum score required to unlock the next chapter when compulsory."),
    )

    class Meta:
        verbose_name = _("Chapter test")
        verbose_name_plural = _("Chapter tests")

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.is_compulsory and self.pass_score is None:
            raise ValidationError(
                {"pass_score": _("Pass score is required for compulsory tests.")}
            )

    def get_update_url(self):
        return reverse_lazy(
            "lms-chapter-test-edit",
            kwargs={"module_id": self.module_id},
        )

    def get_delete_url(self):
        return reverse_lazy("generic-delete")

    def get_delete_instance(self):
        return self.pk


class TestQuestion(HorillaModel):
    test = models.ForeignKey(
        ChapterTest,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name=_("Test"),
    )
    prompt = models.TextField(verbose_name=_("Question"))
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
        default=QuestionType.MCQ,
        verbose_name=_("Type"),
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("Sort order"))
    points = models.PositiveSmallIntegerField(default=1, verbose_name=_("Points"))

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = _("Test question")
        verbose_name_plural = _("Test questions")

    def __str__(self):
        return self.prompt[:60]


class TestChoice(HorillaModel):
    question = models.ForeignKey(
        TestQuestion,
        on_delete=models.CASCADE,
        related_name="choices",
        verbose_name=_("Question"),
    )
    label = models.CharField(max_length=500, verbose_name=_("Choice"))
    is_correct = models.BooleanField(default=False, verbose_name=_("Correct"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("Sort order"))

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = _("Test choice")
        verbose_name_plural = _("Test choices")

    def __str__(self):
        return self.label[:60]


class CourseEnrollment(models.Model):
    company_id = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="lms_course_enrollments",
        verbose_name=_("Company"),
    )
    course_id = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name=_("Course"),
    )
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="lms_course_enrollments",
        verbose_name=_("Employee"),
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="lms_assignments_made",
        verbose_name=_("Assigned by"),
        null=True,
        blank=True,
    )
    source = models.CharField(
        max_length=20,
        choices=EnrollmentSource.choices,
        default=EnrollmentSource.ASSIGNED,
        verbose_name=_("Source"),
    )
    assigned_at = models.DateTimeField(default=timezone.now, verbose_name=_("Enrolled at"))
    due_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Due at"))
    notes = models.TextField(blank=True, null=True, verbose_name=_("Notes"))
    status = models.CharField(
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ASSIGNED,
        verbose_name=_("Status"),
    )
    progress_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Progress %"),
    )
    started_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Started at"))
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Completed at"),
    )
    last_accessed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Last accessed at"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    objects = HorillaCompanyManager(related_company_field="company_id")

    class Meta:
        verbose_name = _("Course enrollment")
        verbose_name_plural = _("Course enrollments")
        constraints = [
            models.UniqueConstraint(
                fields=["company_id", "course_id", "employee_id"],
                name="lms_unique_enrollment_per_employee_course",
            ),
        ]
        indexes = [
            models.Index(fields=["company_id"]),
            models.Index(fields=["course_id"]),
            models.Index(fields=["employee_id"]),
            models.Index(fields=["status"]),
            models.Index(
                fields=["company_id", "employee_id", "status"],
                name="lms_enroll_co_emp_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.employee_id} — {self.course_id}"

    def is_overdue(self):
        if self.status == EnrollmentStatus.COMPLETED:
            return False
        if self.status == EnrollmentStatus.CANCELLED:
            return False
        if not self.due_at:
            return False
        return timezone.now() > self.due_at

    def recalculate_progress(self):
        from lms.services.progress import recalculate_enrollment_progress

        return recalculate_enrollment_progress(self)

    def get_player_url(self):
        return reverse_lazy("lms-player", kwargs={"enrollment_id": self.pk})

    def status_badge(self):
        return self.get_status_display()

    def source_badge(self):
        return self.get_source_display()

    def progress_col(self):
        return f"{self.progress_percentage}%"

    def due_col(self):
        if not self.due_at:
            return "—"
        return timezone.localtime(self.due_at).strftime("%d %b %Y")

    def get_delete_url(self):
        return reverse_lazy("generic-delete")

    def get_delete_instance(self):
        return self.pk


class LessonProgress(models.Model):
    enrollment_id = models.ForeignKey(
        CourseEnrollment,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
        verbose_name=_("Enrollment"),
    )
    lesson_id = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progress_records",
        verbose_name=_("Lesson"),
    )
    status = models.CharField(
        max_length=20,
        choices=LessonProgressStatus.choices,
        default=LessonProgressStatus.NOT_STARTED,
        verbose_name=_("Status"),
    )
    progress_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Progress %"),
    )
    started_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Started at"))
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Completed at"),
    )
    last_position = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name=_("Last position"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("Lesson progress")
        verbose_name_plural = _("Lesson progress records")
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment_id", "lesson_id"],
                name="lms_unique_lesson_progress_per_enrollment",
            ),
        ]
        indexes = [
            models.Index(fields=["enrollment_id"]),
            models.Index(fields=["lesson_id"]),
        ]

    def __str__(self):
        return f"{self.enrollment_id_id} — {self.lesson_id_id}"


class TestAttempt(models.Model):
    enrollment = models.ForeignKey(
        CourseEnrollment,
        on_delete=models.CASCADE,
        related_name="test_attempts",
        verbose_name=_("Enrollment"),
    )
    test = models.ForeignKey(
        ChapterTest,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name=_("Test"),
    )
    score_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Score %"),
    )
    passed = models.BooleanField(default=False, verbose_name=_("Passed"))
    answers = models.JSONField(default=dict, blank=True, verbose_name=_("Answers"))
    started_at = models.DateTimeField(default=timezone.now, verbose_name=_("Started at"))
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Completed at"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        verbose_name = _("Test attempt")
        verbose_name_plural = _("Test attempts")
        ordering = ["-completed_at", "-id"]
        indexes = [
            models.Index(fields=["enrollment", "test"]),
        ]

    def __str__(self):
        return f"{self.enrollment_id} / {self.test_id}: {self.score_percent}%"
