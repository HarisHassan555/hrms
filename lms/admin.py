from django.contrib import admin

from lms import models

admin.site.register(models.CourseCategory)
admin.site.register(models.Course)
admin.site.register(models.CourseModule)
admin.site.register(models.Lesson)
admin.site.register(models.CourseEnrollment)
admin.site.register(models.LessonProgress)
