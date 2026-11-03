"""
LMS URL configuration.
"""

from django.urls import path

from lms import views
from lms.cbv import categories, course_builder, courses, enrollments

urlpatterns = [
    path("", views.lms_landing, name="lms-index"),
    path("catalog/", views.lms_catalog, name="lms-catalog"),
    path("catalog/<int:pk>/", views.lms_course_detail, name="lms-course-detail"),
    path(
        "catalog/<int:pk>/enroll/",
        views.lms_self_enroll,
        name="lms-self-enroll",
    ),
    path("dashboard/", views.lms_dashboard, name="lms-dashboard"),
    path("courses/", views.lms_courses, name="lms-courses"),
    path("courses/list/", courses.CourseListView.as_view(), name="lms-course-list"),
    path("courses/nav/", courses.CourseNavView.as_view(), name="lms-course-nav"),
    path(
        "courses/create/",
        courses.CourseFormView.as_view(),
        name="lms-course-create",
    ),
    path(
        "courses/<int:pk>/update/",
        courses.CourseFormView.as_view(),
        name="lms-course-update",
    ),
    path(
        "courses/<int:course_id>/builder/",
        views.course_builder,
        name="lms-course-builder",
    ),
    path(
        "courses/<int:course_id>/builder/panel/",
        course_builder.course_builder_panel,
        name="lms-course-builder-panel",
    ),
    path(
        "courses/<int:course_id>/modules/create/",
        course_builder.CourseModuleFormView.as_view(),
        name="lms-module-create",
    ),
    path(
        "courses/<int:course_id>/modules/<int:pk>/update/",
        course_builder.CourseModuleFormView.as_view(),
        name="lms-module-update",
    ),
    path(
        "modules/<int:module_id>/lessons/create/",
        course_builder.LessonFormView.as_view(),
        name="lms-lesson-create",
    ),
    path(
        "modules/<int:module_id>/lessons/<int:pk>/update/",
        course_builder.LessonFormView.as_view(),
        name="lms-lesson-update",
    ),
    path(
        "modules/<int:module_id>/test/",
        course_builder.ChapterTestFormView.as_view(),
        name="lms-chapter-test-edit",
    ),
    path(
        "tests/<int:test_id>/questions/create/",
        course_builder.TestQuestionFormView.as_view(),
        name="lms-test-question-create",
    ),
    path(
        "tests/<int:test_id>/questions/<int:pk>/update/",
        course_builder.TestQuestionFormView.as_view(),
        name="lms-test-question-update",
    ),
    path("categories/", views.lms_categories, name="lms-categories"),
    path(
        "categories/list/",
        categories.CourseCategoryListView.as_view(),
        name="lms-category-list",
    ),
    path(
        "categories/nav/",
        categories.CourseCategoryNavView.as_view(),
        name="lms-category-nav",
    ),
    path(
        "categories/create/",
        categories.CourseCategoryFormView.as_view(),
        name="lms-category-create",
    ),
    path(
        "categories/<int:pk>/update/",
        categories.CourseCategoryFormView.as_view(),
        name="lms-category-update",
    ),
    path("my-learning/", views.lms_my_learning, name="lms-my-learning"),
    path(
        "my-learning/partial/",
        views.lms_my_learning_partial,
        name="lms-my-learning-partial",
    ),
    path("enrollments/", views.lms_enrollments, name="lms-enrollments"),
    path(
        "enrollments/list/",
        enrollments.EnrollmentListView.as_view(),
        name="lms-enrollment-list",
    ),
    path(
        "enrollments/nav/",
        enrollments.EnrollmentNavView.as_view(),
        name="lms-enrollment-nav",
    ),
    path(
        "enrollments/assign/",
        enrollments.CourseAssignFormView.as_view(),
        name="lms-enrollment-assign",
    ),
    path(
        "progress-reports/",
        views.lms_progress_reports,
        name="lms-progress-reports",
    ),
    path(
        "player/<int:enrollment_id>/",
        views.lms_player,
        name="lms-player",
    ),
    path(
        "player/<int:enrollment_id>/lessons/<int:lesson_id>/",
        views.lms_player_lesson,
        name="lms-player-lesson",
    ),
    path(
        "player/<int:enrollment_id>/lessons/<int:lesson_id>/complete/",
        views.lms_player_complete_lesson,
        name="lms-player-complete-lesson",
    ),
    path(
        "player/<int:enrollment_id>/lessons/<int:lesson_id>/video-progress/",
        views.lms_player_video_progress,
        name="lms-player-video-progress",
    ),
    path(
        "player/<int:enrollment_id>/tests/<int:test_id>/",
        views.lms_player_test,
        name="lms-player-test",
    ),
]
