from django.contrib import admin

from lms import models


class LessonSlideInline(admin.TabularInline):
    model = models.LessonSlide
    extra = 0


class TestChoiceInline(admin.TabularInline):
    model = models.TestChoice
    extra = 0


class TestQuestionInline(admin.TabularInline):
    model = models.TestQuestion
    extra = 0


@admin.register(models.CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "company_id", "status", "is_active")
    list_filter = ("status", "is_active")
    search_fields = ("name",)


@admin.register(models.Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "category_id", "status", "company_id")
    list_filter = ("status", "difficulty")
    search_fields = ("title", "code")


@admin.register(models.CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course_id", "sort_order", "is_active")
    list_filter = ("is_active",)


@admin.register(models.Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "module_id", "type", "sort_order", "is_active")
    list_filter = ("type", "is_active")
    inlines = [LessonSlideInline]


@admin.register(models.LessonSlide)
class LessonSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "sort_order")


@admin.register(models.ChapterTest)
class ChapterTestAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "is_compulsory", "pass_score", "is_active")
    inlines = [TestQuestionInline]


@admin.register(models.TestQuestion)
class TestQuestionAdmin(admin.ModelAdmin):
    list_display = ("prompt", "test", "question_type", "points", "sort_order")
    inlines = [TestChoiceInline]


admin.site.register(models.TestChoice)
admin.site.register(models.CourseEnrollment)
admin.site.register(models.LessonProgress)
admin.site.register(models.TestAttempt)
