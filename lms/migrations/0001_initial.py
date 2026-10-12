# Generated manually for LMS MVP (Horilla / Django)

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("base", "0017_alter_announcement_table_and_more"),
        ("employee", "0009_alter_actiontype_table_alter_bonuspoint_table_and_more"),
        ("horilla_audit", "0004_alter_accountblockunblock_table_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseCategory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, null=True, verbose_name="Created At"
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Is Active")),
                ("name", models.CharField(max_length=150, verbose_name="Name")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="Description"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("inactive", "Inactive")],
                        default="active",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "company_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lms_course_categories",
                        to="base.company",
                        verbose_name="Company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_modified_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Modified By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Course category",
                "verbose_name_plural": "Course categories",
            },
        ),
        migrations.CreateModel(
            name="Course",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, null=True, verbose_name="Created At"
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Is Active")),
                ("title", models.CharField(max_length=255, verbose_name="Title")),
                (
                    "code",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="Code"
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="Description"),
                ),
                (
                    "thumbnail",
                    models.CharField(
                        blank=True, max_length=500, null=True, verbose_name="Thumbnail"
                    ),
                ),
                (
                    "difficulty",
                    models.CharField(
                        choices=[
                            ("beginner", "Beginner"),
                            ("intermediate", "Intermediate"),
                            ("advanced", "Advanced"),
                        ],
                        default="beginner",
                        max_length=20,
                        verbose_name="Difficulty",
                    ),
                ),
                (
                    "duration_minutes",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="Duration (minutes)"
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("published", "Published"),
                            ("archived", "Archived"),
                        ],
                        default="draft",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "published_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Published at"
                    ),
                ),
                (
                    "category_id",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="courses",
                        to="lms.coursecategory",
                        verbose_name="Category",
                    ),
                ),
                (
                    "company_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lms_courses",
                        to="base.company",
                        verbose_name="Company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_modified_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Modified By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Course",
                "verbose_name_plural": "Courses",
            },
        ),
        migrations.CreateModel(
            name="CourseModule",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, null=True, verbose_name="Created At"
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Is Active")),
                ("title", models.CharField(max_length=255, verbose_name="Title")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="Description"),
                ),
                (
                    "sort_order",
                    models.PositiveIntegerField(default=0, verbose_name="Sort order"),
                ),
                (
                    "course_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="modules",
                        to="lms.course",
                        verbose_name="Course",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_modified_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Modified By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Course module",
                "verbose_name_plural": "Course modules",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="Lesson",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, null=True, verbose_name="Created At"
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Is Active")),
                ("title", models.CharField(max_length=255, verbose_name="Title")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="Description"),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("video", "Video"),
                            ("pdf", "PDF"),
                            ("text", "Text"),
                        ],
                        max_length=10,
                        verbose_name="Type",
                    ),
                ),
                (
                    "content",
                    models.TextField(blank=True, null=True, verbose_name="Content"),
                ),
                (
                    "file_path",
                    models.CharField(
                        blank=True, max_length=500, null=True, verbose_name="File path"
                    ),
                ),
                (
                    "video_url",
                    models.CharField(
                        blank=True, max_length=500, null=True, verbose_name="Video URL"
                    ),
                ),
                (
                    "duration_minutes",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="Duration (minutes)"
                    ),
                ),
                (
                    "sort_order",
                    models.PositiveIntegerField(default=0, verbose_name="Sort order"),
                ),
                (
                    "module_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lessons",
                        to="lms.coursemodule",
                        verbose_name="Module",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_modified_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Modified By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lesson",
                "verbose_name_plural": "Lessons",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="CourseEnrollment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "assigned_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Assigned at"
                    ),
                ),
                (
                    "due_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Due at"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("assigned", "Assigned"),
                            ("in_progress", "In progress"),
                            ("completed", "Completed"),
                            ("overdue", "Overdue"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="assigned",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "progress_percentage",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(100),
                        ],
                        verbose_name="Progress %",
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Started at"
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Completed at"
                    ),
                ),
                (
                    "last_accessed_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Last accessed at"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                (
                    "assigned_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lms_assignments_made",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Assigned by",
                    ),
                ),
                (
                    "company_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lms_course_enrollments",
                        to="base.company",
                        verbose_name="Company",
                    ),
                ),
                (
                    "course_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="enrollments",
                        to="lms.course",
                        verbose_name="Course",
                    ),
                ),
                (
                    "employee_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lms_course_enrollments",
                        to="employee.employee",
                        verbose_name="Employee",
                    ),
                ),
            ],
            options={
                "verbose_name": "Course enrollment",
                "verbose_name_plural": "Course enrollments",
            },
        ),
        migrations.CreateModel(
            name="LessonProgress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("not_started", "Not started"),
                            ("in_progress", "In progress"),
                            ("completed", "Completed"),
                        ],
                        default="not_started",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "progress_percentage",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(100),
                        ],
                        verbose_name="Progress %",
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Started at"
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Completed at"
                    ),
                ),
                (
                    "last_position",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=10,
                        null=True,
                        verbose_name="Last position",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                (
                    "enrollment_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lesson_progress",
                        to="lms.courseenrollment",
                        verbose_name="Enrollment",
                    ),
                ),
                (
                    "lesson_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="progress_records",
                        to="lms.lesson",
                        verbose_name="Lesson",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lesson progress",
                "verbose_name_plural": "Lesson progress records",
            },
        ),
        migrations.AddIndex(
            model_name="coursecategory",
            index=models.Index(fields=["company_id"], name="lms_coursecat_company_idx"),
        ),
        migrations.AddIndex(
            model_name="coursecategory",
            index=models.Index(fields=["status"], name="lms_coursecat_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="coursecategory",
            constraint=models.UniqueConstraint(
                fields=("company_id", "name"),
                name="lms_unique_category_name_per_company",
            ),
        ),
        migrations.AddIndex(
            model_name="course",
            index=models.Index(fields=["company_id"], name="lms_course_company_idx"),
        ),
        migrations.AddIndex(
            model_name="course",
            index=models.Index(fields=["category_id"], name="lms_course_category_idx"),
        ),
        migrations.AddIndex(
            model_name="course",
            index=models.Index(fields=["status"], name="lms_course_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="course",
            constraint=models.UniqueConstraint(
                condition=models.Q(("code__isnull", False))
                & ~models.Q(("code", "")),
                fields=("company_id", "code"),
                name="lms_unique_course_code_per_company",
            ),
        ),
        migrations.AddIndex(
            model_name="coursemodule",
            index=models.Index(fields=["course_id"], name="lms_module_course_idx"),
        ),
        migrations.AddIndex(
            model_name="lesson",
            index=models.Index(fields=["module_id"], name="lms_lesson_module_idx"),
        ),
        migrations.AddIndex(
            model_name="courseenrollment",
            index=models.Index(fields=["company_id"], name="lms_enroll_company_idx"),
        ),
        migrations.AddIndex(
            model_name="courseenrollment",
            index=models.Index(fields=["course_id"], name="lms_enroll_course_idx"),
        ),
        migrations.AddIndex(
            model_name="courseenrollment",
            index=models.Index(fields=["employee_id"], name="lms_enroll_employee_idx"),
        ),
        migrations.AddIndex(
            model_name="courseenrollment",
            index=models.Index(fields=["status"], name="lms_enroll_status_idx"),
        ),
        migrations.AddIndex(
            model_name="courseenrollment",
            index=models.Index(
                fields=["company_id", "employee_id", "status"],
                name="lms_enroll_co_emp_status_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="courseenrollment",
            constraint=models.UniqueConstraint(
                fields=("company_id", "course_id", "employee_id"),
                name="lms_unique_enrollment_per_employee_course",
            ),
        ),
        migrations.AddIndex(
            model_name="lessonprogress",
            index=models.Index(
                fields=["enrollment_id"], name="lms_lprog_enrollment_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="lessonprogress",
            index=models.Index(fields=["lesson_id"], name="lms_lprog_lesson_idx"),
        ),
        migrations.AddConstraint(
            model_name="lessonprogress",
            constraint=models.UniqueConstraint(
                fields=("enrollment_id", "lesson_id"),
                name="lms_unique_lesson_progress_per_enrollment",
            ),
        ),
    ]
