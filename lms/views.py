"""
LMS views — catalog, learner experience, admin shells, player.
"""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from lms.models import (
    ChapterTest,
    Course,
    CourseCategory,
    CourseCategoryStatus,
    CourseEnrollment,
    CourseModule,
    EnrollmentStatus,
    Lesson,
    LessonType,
    extract_youtube_video_id,
    normalize_video_embed_url,
)
from lms.services.dashboard import get_lms_dashboard_context
from lms.services.enrollment import (
    get_employee_enrollment,
    published_catalog_qs,
    self_enroll,
)
from lms.services.progress import (
    build_player_outline,
    is_chapter_unlocked,
    lesson_completed,
    mark_lesson_complete,
    next_player_item_after_lesson,
    next_player_item_after_test,
    record_video_watch_progress,
    submit_test_attempt,
    test_passed,
    touch_enrollment,
    video_watch_requirement_met,
)
from lms.services.reports import get_progress_report_context


def _hr_lms_access(user):
    return (
        user.has_perm("lms.view_course")
        or user.has_perm("lms.add_course")
        or user.has_perm("lms.view_coursecategory")
        or user.has_perm("lms.view_courseenrollment")
        or user.is_superuser
    )


def _require_hr(user):
    if not _hr_lms_access(user):
        raise PermissionDenied


def _require_employee(user):
    try:
        if not user.employee_get:
            raise PermissionDenied
    except Exception:
        raise PermissionDenied


def _employee_or_none(user):
    try:
        return user.employee_get
    except Exception:
        return None


def _get_own_enrollment(request, enrollment_id):
    employee = request.user.employee_get
    return get_object_or_404(
        CourseEnrollment.objects.select_related("course_id"),
        pk=enrollment_id,
        employee_id=employee,
    )


def _annotate_catalog(qs):
    return qs.annotate(
        chapters_count=Count(
            "modules",
            filter=Q(modules__is_active=True),
            distinct=True,
        ),
        lessons_count=Count(
            "modules__lessons",
            filter=Q(modules__is_active=True, modules__lessons__is_active=True),
            distinct=True,
        ),
        learners_count=Count(
            "enrollments",
            filter=~Q(enrollments__status=EnrollmentStatus.CANCELLED),
            distinct=True,
        ),
    )


@login_required
def lms_landing(request):
    employee = _employee_or_none(request.user)
    if employee:
        return redirect("lms-catalog")
    if _hr_lms_access(request.user):
        return redirect("lms-dashboard")
    raise PermissionDenied


@login_required
def lms_dashboard(request):
    _require_hr(request.user)
    context = {
        "title": _("Learning Dashboard"),
        **get_lms_dashboard_context(),
    }
    return render(request, "lms/dashboard.html", context)


@login_required
@permission_required("lms.view_course")
def course_builder(request, course_id):
    course = get_object_or_404(Course.objects, pk=course_id)
    can_edit = request.user.has_perm("lms.change_course") or request.user.is_superuser
    return render(
        request,
        "lms/course_builder.html",
        {
            "title": _("Course builder"),
            "course": course,
            "can_edit": can_edit,
        },
    )


@login_required
def lms_courses(request):
    if not (request.user.has_perm("lms.view_course") or request.user.is_superuser):
        raise PermissionDenied
    return render(
        request,
        "lms/courses.html",
        {
            "title": _("Manage courses"),
            "subtitle": _("Create courses, publish to the catalog, and open the builder."),
        },
    )


@login_required
def lms_categories(request):
    if not (
        request.user.has_perm("lms.view_coursecategory") or request.user.is_superuser
    ):
        raise PermissionDenied
    return render(request, "lms/categories.html", {"title": _("Categories")})


@login_required
def lms_catalog(request):
    employee = _employee_or_none(request.user)
    if not employee and not _hr_lms_access(request.user):
        raise PermissionDenied

    q = (request.GET.get("q") or "").strip()
    category_id = request.GET.get("category") or ""
    difficulty = request.GET.get("difficulty") or ""

    courses = _annotate_catalog(published_catalog_qs())
    if q:
        courses = courses.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(code__icontains=q)
            | Q(category_id__name__icontains=q)
        )
    if category_id.isdigit():
        courses = courses.filter(category_id_id=int(category_id))
    if difficulty:
        courses = courses.filter(difficulty=difficulty)

    enrollment_map = {}
    if employee:
        enrollment_map = {
            e.course_id_id: e
            for e in CourseEnrollment.objects.filter(employee_id=employee)
            .exclude(status=EnrollmentStatus.CANCELLED)
            .select_related("course_id")
        }

    cards = []
    for course in courses:
        enrollment = enrollment_map.get(course.pk)
        cards.append(
            {
                "course": course,
                "enrollment": enrollment,
                "enrolled": bool(enrollment),
            }
        )

    categories = CourseCategory.objects.filter(
        is_active=True, status=CourseCategoryStatus.ACTIVE
    ).order_by("name")

    return render(
        request,
        "lms/catalog.html",
        {
            "title": _("Course catalog"),
            "cards": cards,
            "categories": categories,
            "q": q,
            "selected_category": category_id,
            "selected_difficulty": difficulty,
            "can_assign": _hr_lms_access(request.user),
            "employee": employee,
        },
    )


@login_required
def lms_course_detail(request, pk):
    employee = _employee_or_none(request.user)
    if not employee and not _hr_lms_access(request.user):
        raise PermissionDenied

    course = get_object_or_404(
        _annotate_catalog(published_catalog_qs()),
        pk=pk,
    )
    modules = (
        CourseModule.objects.filter(course_id=course, is_active=True)
        .prefetch_related(
            Prefetch(
                "lessons",
                queryset=Lesson.objects.filter(is_active=True).order_by(
                    "sort_order", "id"
                ),
            )
        )
        .order_by("sort_order", "id")
    )
    syllabus = []
    for module in modules:
        lessons = list(module.lessons.all())
        try:
            test = module.chapter_test if module.chapter_test.is_active else None
        except ChapterTest.DoesNotExist:
            test = None
        syllabus.append({"module": module, "lessons": lessons, "test": test})

    enrollment = get_employee_enrollment(employee, course) if employee else None
    return render(
        request,
        "lms/course_detail.html",
        {
            "title": course.title,
            "course": course,
            "syllabus": syllabus,
            "enrollment": enrollment,
            "employee": employee,
            "can_assign": _hr_lms_access(request.user),
            "can_edit": request.user.has_perm("lms.change_course")
            or request.user.is_superuser,
            "can_self_enroll": bool(
                employee and course.allow_self_enroll and not enrollment
            ),
        },
    )


@login_required
@require_POST
def lms_self_enroll(request, pk):
    _require_employee(request.user)
    course = get_object_or_404(published_catalog_qs(), pk=pk)
    try:
        enrollment = self_enroll(
            employee=request.user.employee_get,
            course=course,
            user=request.user,
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
        return redirect("lms-course-detail", pk=pk)
    messages.success(request, _("You are enrolled. Start learning when you are ready."))
    return redirect("lms-player", enrollment_id=enrollment.pk)


@login_required
def lms_my_learning(request):
    _require_employee(request.user)
    employee = request.user.employee_get
    enrollments = (
        CourseEnrollment.objects.filter(employee_id=employee)
        .exclude(status=EnrollmentStatus.CANCELLED)
        .select_related("course_id", "course_id__category_id")
        .order_by("-last_accessed_at", "-assigned_at")
    )
    cards = [
        {
            "enrollment": e,
            "overdue": e.is_overdue(),
            "progress": e.progress_percentage,
        }
        for e in enrollments
    ]
    return render(
        request,
        "lms/my_learning.html",
        {
            "title": _("My Learning"),
            "cards": cards,
        },
    )


@login_required
def lms_my_learning_partial(request):
    _require_employee(request.user)
    employee = request.user.employee_get
    enrollments = (
        CourseEnrollment.objects.filter(employee_id=employee)
        .exclude(status=EnrollmentStatus.CANCELLED)
        .select_related("course_id", "course_id__category_id")
        .order_by("-last_accessed_at", "-assigned_at")
    )
    cards = [
        {
            "enrollment": e,
            "overdue": e.is_overdue(),
            "progress": e.progress_percentage,
        }
        for e in enrollments
    ]
    return render(request, "lms/_my_learning_cards.html", {"cards": cards})


@login_required
def lms_enrollments(request):
    _require_hr(request.user)
    return render(
        request,
        "lms/enrollments.html",
        {
            "title": _("Assignments"),
            "subtitle": _(
                "Assign catalog courses to employees with optional deadlines."
            ),
        },
    )


@login_required
def lms_progress_reports(request):
    _require_hr(request.user)
    course_id = request.GET.get("course_id") or None
    employee_id = request.GET.get("employee_id") or None
    context = get_progress_report_context(
        course_id=int(course_id) if course_id else None,
        employee_id=int(employee_id) if employee_id else None,
    )
    context.update(
        {
            "title": _("Progress Reports"),
            "subtitle": _("Completion, scores, and deadline status."),
        }
    )
    return render(request, "lms/progress_reports.html", context)


@login_required
def lms_player(request, enrollment_id):
    _require_employee(request.user)
    enrollment = _get_own_enrollment(request, enrollment_id)
    touch_enrollment(enrollment)
    enrollment.refresh_from_db()
    outline = build_player_outline(enrollment)
    return render(
        request,
        "lms/player.html",
        {
            "title": enrollment.course_id.title,
            "enrollment": enrollment,
            "outline": outline,
            "course": enrollment.course_id,
        },
    )


@login_required
def lms_player_lesson(request, enrollment_id, lesson_id):
    _require_employee(request.user)
    enrollment = _get_own_enrollment(request, enrollment_id)
    lesson = get_object_or_404(
        Lesson.objects.select_related("module_id").prefetch_related("slides"),
        pk=lesson_id,
        module_id__course_id=enrollment.course_id,
        is_active=True,
    )
    if not is_chapter_unlocked(enrollment, lesson.module_id):
        messages.error(
            request, _("This chapter is locked. Complete the previous chapter first.")
        )
        return redirect("lms-player", enrollment_id=enrollment.pk)

    touch_enrollment(enrollment)
    slides = list(lesson.slides.filter(is_active=True).order_by("sort_order", "id"))

    video_embed_url = ""
    youtube_video_id = ""
    video_watch_complete = True
    if lesson.type == LessonType.VIDEO:
        video_embed_url = normalize_video_embed_url(lesson.video_url or "")
        youtube_video_id = extract_youtube_video_id(lesson.video_url or "") or ""
        video_watch_complete = video_watch_requirement_met(enrollment, lesson)
    return render(
        request,
        "lms/player_lesson.html",
        {
            "title": lesson.title,
            "enrollment": enrollment,
            "lesson": lesson,
            "module": lesson.module_id,
            "slides": slides,
            "completed": lesson_completed(enrollment, lesson),
            "outline": build_player_outline(enrollment),
            "course": enrollment.course_id,
            "video_embed_url": video_embed_url,
            "youtube_video_id": youtube_video_id,
            "video_watch_complete": video_watch_complete,
        },
    )


@login_required
@require_POST
def lms_player_video_progress(request, enrollment_id, lesson_id):
    """Record YouTube watch progress so Mark complete can be gated server-side."""
    _require_employee(request.user)
    enrollment = _get_own_enrollment(request, enrollment_id)
    lesson = get_object_or_404(
        Lesson.objects.select_related("module_id"),
        pk=lesson_id,
        module_id__course_id=enrollment.course_id,
        is_active=True,
    )
    if lesson.type != LessonType.VIDEO:
        return JsonResponse({"ok": False, "error": "not_video"}, status=400)
    if not is_chapter_unlocked(enrollment, lesson.module_id):
        raise PermissionDenied

    try:
        payload = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        payload = {}
    percentage = payload.get("percentage", 0)
    position = payload.get("position")
    record_video_watch_progress(enrollment, lesson, percentage, position)
    watch_complete = video_watch_requirement_met(enrollment, lesson)
    return JsonResponse({"ok": True, "watch_complete": watch_complete})


@login_required
@require_POST
def lms_player_complete_lesson(request, enrollment_id, lesson_id):
    _require_employee(request.user)
    enrollment = _get_own_enrollment(request, enrollment_id)
    lesson = get_object_or_404(
        Lesson.objects.select_related("module_id"),
        pk=lesson_id,
        module_id__course_id=enrollment.course_id,
        is_active=True,
    )
    if not is_chapter_unlocked(enrollment, lesson.module_id):
        raise PermissionDenied
    try:
        mark_lesson_complete(enrollment, lesson)
    except ValidationError as exc:
        messages.error(
            request,
            "; ".join(getattr(exc, "messages", None) or [str(exc)]),
        )
        return redirect(
            "lms-player-lesson", enrollment_id=enrollment.pk, lesson_id=lesson.pk
        )
    enrollment.refresh_from_db()
    messages.success(request, _("Lesson marked complete."))

    next_kind, next_obj = next_player_item_after_lesson(enrollment.course_id, lesson)
    if next_kind == "lesson":
        return redirect(
            "lms-player-lesson",
            enrollment_id=enrollment.pk,
            lesson_id=next_obj.pk,
        )
    if next_kind == "test":
        return redirect(
            "lms-player-test",
            enrollment_id=enrollment.pk,
            test_id=next_obj.pk,
        )
    return redirect("lms-player", enrollment_id=enrollment.pk)


@login_required
def lms_player_test(request, enrollment_id, test_id):
    _require_employee(request.user)
    enrollment = _get_own_enrollment(request, enrollment_id)
    test = get_object_or_404(
        ChapterTest.objects.select_related("module").prefetch_related(
            "questions__choices"
        ),
        pk=test_id,
        module__course_id=enrollment.course_id,
        is_active=True,
    )
    if not is_chapter_unlocked(enrollment, test.module):
        messages.error(request, _("This chapter is locked."))
        return redirect("lms-player", enrollment_id=enrollment.pk)

    from lms.services.progress import chapter_content_complete

    if not chapter_content_complete(enrollment, test.module):
        messages.error(
            request, _("Complete all lessons in this chapter before the test.")
        )
        return redirect("lms-player", enrollment_id=enrollment.pk)

    questions = list(
        test.questions.filter(is_active=True).order_by("sort_order", "id")
    )
    for q in questions:
        q.choice_list = list(
            q.choices.filter(is_active=True).order_by("sort_order", "id")
        )

    if request.method == "POST":
        answers = {
            str(question.pk): request.POST.get(f"q_{question.pk}")
            for question in questions
        }
        attempt = submit_test_attempt(enrollment, test, answers)
        enrollment.refresh_from_db()
        if attempt.passed:
            messages.success(
                request,
                _("You scored %(score)s%% and passed.")
                % {"score": attempt.score_percent},
            )
            next_kind, next_obj = next_player_item_after_test(
                enrollment.course_id, test
            )
            if next_kind == "lesson":
                return redirect(
                    "lms-player-lesson",
                    enrollment_id=enrollment.pk,
                    lesson_id=next_obj.pk,
                )
            if next_kind == "test":
                return redirect(
                    "lms-player-test",
                    enrollment_id=enrollment.pk,
                    test_id=next_obj.pk,
                )
            return redirect("lms-player", enrollment_id=enrollment.pk)
        messages.error(
            request,
            _("You scored %(score)s%%. Required: %(pass)s%%.")
            % {"score": attempt.score_percent, "pass": test.pass_score},
        )
        return redirect(
            "lms-player-test",
            enrollment_id=enrollment.pk,
            test_id=test.pk,
        )

    return render(
        request,
        "lms/player_test.html",
        {
            "title": test.title,
            "enrollment": enrollment,
            "test": test,
            "module": test.module,
            "questions": questions,
            "already_passed": test_passed(enrollment, test),
            "outline": build_player_outline(enrollment),
            "course": enrollment.course_id,
        },
    )
