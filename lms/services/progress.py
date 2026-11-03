"""Enrollment progress, chapter gating, and test scoring."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from lms.models import (
    ChapterTest,
    CourseEnrollment,
    CourseModule,
    EnrollmentStatus,
    Lesson,
    LessonProgress,
    LessonProgressStatus,
    LessonType,
    TestAttempt,
)

# Video lessons must reach this watch % before "Mark complete" is allowed.
VIDEO_WATCH_COMPLETE_THRESHOLD = Decimal("95")


def _active_modules(course):
    return list(
        CourseModule.objects.filter(course_id=course, is_active=True).order_by(
            "sort_order", "id"
        )
    )


def _active_lessons(module):
    return list(
        Lesson.objects.filter(module_id=module, is_active=True).order_by(
            "sort_order", "id"
        )
    )


def _active_test(module):
    try:
        test = module.chapter_test
    except ChapterTest.DoesNotExist:
        return None
    if not test.is_active:
        return None
    return test


def required_units_for_course(course):
    """
    Return ordered required units for progress:
    ('lesson', lesson) and ('test', chapter_test) when compulsory.
    """
    units = []
    for module in _active_modules(course):
        for lesson in _active_lessons(module):
            units.append(("lesson", lesson))
        test = _active_test(module)
        if test and test.is_compulsory:
            units.append(("test", test))
    return units


def player_sequence_for_course(course):
    """
    Ordered player navigation items matching the outline:
    lessons in each chapter, then that chapter's test when present.
    """
    items = []
    for module in _active_modules(course):
        for lesson in _active_lessons(module):
            items.append(("lesson", lesson))
        test = _active_test(module)
        if test:
            items.append(("test", test))
    return items


def next_player_item_after(course, kind, current):
    """Return ('lesson'|'test', obj) for the next player item, or (None, None)."""
    items = player_sequence_for_course(course)
    for index, (item_kind, obj) in enumerate(items):
        if item_kind == kind and obj.pk == current.pk:
            if index + 1 < len(items):
                return items[index + 1]
            return (None, None)
    return (None, None)


def next_player_item_after_lesson(course, lesson):
    return next_player_item_after(course, "lesson", lesson)


def next_player_item_after_test(course, test):
    """After a chapter test, typically the first lesson of the next chapter."""
    return next_player_item_after(course, "test", test)


def lesson_completed(enrollment, lesson):
    return LessonProgress.objects.filter(
        enrollment_id=enrollment,
        lesson_id=lesson,
        status=LessonProgressStatus.COMPLETED,
    ).exists()


def test_passed(enrollment, test):
    return TestAttempt.objects.filter(
        enrollment=enrollment, test=test, passed=True
    ).exists()


def chapter_content_complete(enrollment, module):
    lessons = _active_lessons(module)
    if not lessons:
        return True
    return all(lesson_completed(enrollment, lesson) for lesson in lessons)


def chapter_requirements_met(enrollment, module):
    if not chapter_content_complete(enrollment, module):
        return False
    test = _active_test(module)
    if test and test.is_compulsory:
        return test_passed(enrollment, test)
    return True


def is_chapter_unlocked(enrollment, module):
    modules = _active_modules(enrollment.course_id)
    for previous in modules:
        if previous.pk == module.pk:
            return True
        if not chapter_requirements_met(enrollment, previous):
            return False
    return False


def touch_enrollment(enrollment):
    enrollment.last_accessed_at = timezone.now()
    if enrollment.started_at is None:
        enrollment.started_at = timezone.now()
    if enrollment.status == EnrollmentStatus.ASSIGNED:
        enrollment.status = EnrollmentStatus.IN_PROGRESS
    enrollment.save(
        update_fields=["last_accessed_at", "started_at", "status", "updated_at"]
    )


def get_lesson_progress(enrollment, lesson):
    return LessonProgress.objects.filter(
        enrollment_id=enrollment, lesson_id=lesson
    ).first()


def video_watch_requirement_met(enrollment, lesson) -> bool:
    """True when a video lesson has been watched far enough to allow completion."""
    if lesson.type != LessonType.VIDEO:
        return True
    progress = get_lesson_progress(enrollment, lesson)
    if progress is None:
        return False
    if progress.status == LessonProgressStatus.COMPLETED:
        return True
    return progress.progress_percentage >= VIDEO_WATCH_COMPLETE_THRESHOLD


@transaction.atomic
def record_video_watch_progress(enrollment, lesson, percentage, position=None):
    """
    Persist YouTube watch progress for a video lesson.
    Does not mark the lesson complete — that remains an explicit learner action
    after the watch threshold is met.
    """
    if lesson.type != LessonType.VIDEO:
        return None

    now = timezone.now()
    try:
        pct = Decimal(str(percentage)).quantize(Decimal("0.01"))
    except Exception:
        pct = Decimal("0")
    pct = max(Decimal("0"), min(Decimal("100"), pct))

    progress, _created = LessonProgress.objects.get_or_create(
        enrollment_id=enrollment,
        lesson_id=lesson,
        defaults={
            "status": LessonProgressStatus.IN_PROGRESS,
            "progress_percentage": pct,
            "started_at": now,
            "last_position": position,
        },
    )
    if progress.status == LessonProgressStatus.COMPLETED:
        return progress

    dirty = False
    if progress.started_at is None:
        progress.started_at = now
        dirty = True
    if progress.status == LessonProgressStatus.NOT_STARTED:
        progress.status = LessonProgressStatus.IN_PROGRESS
        dirty = True
    if pct > progress.progress_percentage:
        progress.progress_percentage = pct
        dirty = True
    if position is not None:
        try:
            pos = Decimal(str(position)).quantize(Decimal("0.01"))
        except Exception:
            pos = None
        if pos is not None and (
            progress.last_position is None or pos > progress.last_position
        ):
            progress.last_position = pos
            dirty = True
    if dirty:
        progress.save()
    touch_enrollment(enrollment)
    return progress


@transaction.atomic
def mark_lesson_complete(enrollment, lesson):
    if lesson.type == LessonType.VIDEO and not video_watch_requirement_met(
        enrollment, lesson
    ):
        raise ValidationError(
            _("Watch the full video before marking this lesson complete.")
        )

    now = timezone.now()
    progress, _created = LessonProgress.objects.get_or_create(
        enrollment_id=enrollment,
        lesson_id=lesson,
        defaults={
            "status": LessonProgressStatus.COMPLETED,
            "progress_percentage": Decimal("100"),
            "started_at": now,
            "completed_at": now,
        },
    )
    if progress.status != LessonProgressStatus.COMPLETED:
        if progress.started_at is None:
            progress.started_at = now
        progress.status = LessonProgressStatus.COMPLETED
        progress.progress_percentage = Decimal("100")
        progress.completed_at = now
        progress.save()
    touch_enrollment(enrollment)
    return recalculate_enrollment_progress(enrollment)


@transaction.atomic
def submit_test_attempt(enrollment, test, answers: dict) -> TestAttempt:
    """
    ``answers`` maps question_id (str/int) -> choice_id (int).
    """
    questions = list(
        test.questions.filter(is_active=True)
        .prefetch_related("choices")
        .order_by("sort_order", "id")
    )
    total_points = sum(q.points for q in questions) or 1
    earned = 0
    normalized = {}
    for question in questions:
        raw = answers.get(str(question.pk), answers.get(question.pk))
        try:
            choice_id = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            choice_id = None
        normalized[str(question.pk)] = choice_id
        if choice_id is None:
            continue
        choice = next(
            (c for c in question.choices.all() if c.pk == choice_id and c.is_active),
            None,
        )
        if choice and choice.is_correct:
            earned += question.points

    score = (Decimal(earned) / Decimal(total_points)) * Decimal("100")
    score = score.quantize(Decimal("0.01"))
    passed = True
    if test.is_compulsory:
        passed = score >= Decimal(test.pass_score)
    else:
        # Optional tests still record pass if score meets threshold when set.
        passed = score >= Decimal(test.pass_score or 0)

    attempt = TestAttempt.objects.create(
        enrollment=enrollment,
        test=test,
        score_percent=score,
        passed=passed,
        answers=normalized,
        completed_at=timezone.now(),
    )
    touch_enrollment(enrollment)
    recalculate_enrollment_progress(enrollment)
    return attempt


@transaction.atomic
def recalculate_enrollment_progress(enrollment: CourseEnrollment):
    units = required_units_for_course(enrollment.course_id)
    total = len(units)
    completed = 0
    for kind, obj in units:
        if kind == "lesson" and lesson_completed(enrollment, obj):
            completed += 1
        elif kind == "test" and test_passed(enrollment, obj):
            completed += 1

    if total:
        pct = (Decimal(completed) / Decimal(total)) * Decimal("100")
    else:
        pct = Decimal("100") if enrollment.status != EnrollmentStatus.CANCELLED else Decimal("0")
    pct = pct.quantize(Decimal("0.01"))

    enrollment.progress_percentage = pct
    now = timezone.now()

    if enrollment.status != EnrollmentStatus.CANCELLED:
        if total and completed >= total:
            enrollment.status = EnrollmentStatus.COMPLETED
            if enrollment.completed_at is None:
                enrollment.completed_at = now
        else:
            enrollment.completed_at = None
            if enrollment.is_overdue():
                enrollment.status = EnrollmentStatus.OVERDUE
            elif enrollment.started_at or completed:
                enrollment.status = EnrollmentStatus.IN_PROGRESS
            else:
                enrollment.status = EnrollmentStatus.ASSIGNED

    enrollment.save(
        update_fields=[
            "progress_percentage",
            "status",
            "completed_at",
            "updated_at",
        ]
    )
    return enrollment


def build_player_outline(enrollment):
    """Chapter list with lock/completion flags for the learner player."""
    outline = []
    for module in _active_modules(enrollment.course_id):
        lessons = _active_lessons(module)
        test = _active_test(module)
        unlocked = is_chapter_unlocked(enrollment, module)
        lesson_rows = [
            {
                "lesson": lesson,
                "completed": lesson_completed(enrollment, lesson),
            }
            for lesson in lessons
        ]
        best_attempt = None
        if test:
            best_attempt = (
                TestAttempt.objects.filter(enrollment=enrollment, test=test)
                .order_by("-passed", "-score_percent", "-id")
                .first()
            )
        outline.append(
            {
                "module": module,
                "unlocked": unlocked,
                "content_complete": chapter_content_complete(enrollment, module),
                "requirements_met": chapter_requirements_met(enrollment, module),
                "lessons": lesson_rows,
                "test": test,
                "test_passed": bool(test and test_passed(enrollment, test)),
                "best_attempt": best_attempt,
            }
        )
    return outline
