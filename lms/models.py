"""
LMS MVP models — catalog, enrollment, and lesson progress.

Integrates with existing HRMS: base.Company, employee.Employee, horilla_auth.HorillaUser.
"""

from django.conf import settings
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


class EnrollmentStatus(models.TextChoices):
    ASSIGNED = "assigned", _("Assigned")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    OVERDUE = "overdue", _("Overdue")
    CANCELLED = "cancelled", _("Cancelled")


class LessonProgressStatus(models.TextChoices):
    NOT_STARTED = "not_started", _("Not started")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")


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
    thumbnail = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("Thumbnail"),
    )
    difficulty = models.CharField(
        max_length=20,
        choices=CourseDifficulty.choices,
        default=CourseDifficulty.BEGINNER,
        verbose_name=_("Difficulty"),
    )
    duration_minutes = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Duration (minutes)"),
    )
    status = models.CharField(
        max_length=20,
        choices=CourseStatus.choices,
        default=CourseStatus.DRAFT,
        verbose_name=_("Status"),
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
        verbose_name = _("Course module")
        verbose_name_plural = _("Course modules")
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
        verbose_name=_("Module"),
    )
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    type = models.CharField(
        max_length=10,
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
    duration_minutes = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Duration (minutes)"),
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
        return reverse_lazy("lms-lesson-update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("generic-delete")

    def get_delete_instance(self):
        return self.pk

    def type_badge(self):
        return self.get_type_display()


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
    )
    assigned_at = models.DateTimeField(default=timezone.now, verbose_name=_("Assigned at"))
    due_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Due at"))
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
