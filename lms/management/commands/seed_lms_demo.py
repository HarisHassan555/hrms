"""Seed a realistic Learning catalog with courses, slides, videos, and quizzes."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from base.models import Company
from employee.models import Employee
from lms.models import (
    ChapterTest,
    Course,
    CourseCategory,
    CourseCategoryStatus,
    CourseEnrollment,
    CourseModule,
    CourseStatus,
    EnrollmentSource,
    EnrollmentStatus,
    Lesson,
    LessonSlide,
    LessonType,
    QuestionType,
    TestChoice,
    TestQuestion,
)


def _ensure_category(company, name, description):
    category, _ = CourseCategory.objects.get_or_create(
        company_id=company,
        name=name,
        defaults={
            "description": description,
            "status": CourseCategoryStatus.ACTIVE,
        },
    )
    if category.status != CourseCategoryStatus.ACTIVE:
        category.status = CourseCategoryStatus.ACTIVE
        category.is_active = True
        category.save(update_fields=["status", "is_active", "updated_at"])
    return category


def _ensure_course(company, category, *, code, title, description, difficulty, allow_self_enroll=True):
    course, created = Course.objects.get_or_create(
        company_id=company,
        code=code,
        defaults={
            "category_id": category,
            "title": title,
            "description": description,
            "difficulty": difficulty,
            "status": CourseStatus.PUBLISHED,
            "published_at": timezone.now(),
            "allow_self_enroll": allow_self_enroll,
        },
    )
    course.category_id = category
    course.title = title
    course.description = description
    course.difficulty = difficulty
    course.status = CourseStatus.PUBLISHED
    course.allow_self_enroll = allow_self_enroll
    course.is_active = True
    if not course.published_at:
        course.published_at = timezone.now()
    course.save()
    return course, created


def _wipe_course_content(course):
    CourseModule.objects.filter(course_id=course).delete()


def _chapter(course, title, description, sort_order):
    return CourseModule.objects.create(
        course_id=course,
        title=title,
        description=description,
        sort_order=sort_order,
    )


def _text(module, title, content, sort_order):
    return Lesson.objects.create(
        module_id=module,
        title=title,
        type=LessonType.TEXT,
        content=content,
        sort_order=sort_order,
    )


def _video(module, title, video_url, sort_order, description=""):
    return Lesson.objects.create(
        module_id=module,
        title=title,
        type=LessonType.VIDEO,
        video_url=video_url,
        description=description,
        sort_order=sort_order,
    )


def _slideshow(module, title, slides, sort_order):
    lesson = Lesson.objects.create(
        module_id=module,
        title=title,
        type=LessonType.SLIDESHOW,
        sort_order=sort_order,
    )
    for idx, slide in enumerate(slides):
        LessonSlide.objects.create(
            lesson=lesson,
            sort_order=idx,
            title=slide["title"],
            body=slide["body"],
        )
    return lesson


def _test(module, title, pass_score, questions, compulsory=True):
    test = ChapterTest.objects.create(
        module=module,
        title=title,
        is_compulsory=compulsory,
        pass_score=pass_score,
    )
    for q_idx, question in enumerate(questions, start=1):
        q = TestQuestion.objects.create(
            test=test,
            prompt=question["prompt"],
            question_type=question["type"],
            sort_order=q_idx,
            points=question.get("points", 1),
        )
        for c_idx, choice in enumerate(question["choices"]):
            TestChoice.objects.create(
                question=q,
                label=choice["label"],
                is_correct=choice.get("correct", False),
                sort_order=c_idx,
            )
    return test


def _build_onboarding(company, category):
    course, _ = _ensure_course(
        company,
        category,
        code="ONB-101",
        title="New Hire Onboarding Essentials",
        description=(
            "Your first week at the company: culture, tools, security basics, "
            "and how to get productive fast. Includes short videos, slides, and a knowledge check."
        ),
        difficulty="beginner",
        allow_self_enroll=True,
    )
    _wipe_course_content(course)

    ch1 = _chapter(
        course,
        "Welcome & culture",
        "How we work together and what good looks like.",
        1,
    )
    _text(
        ch1,
        "Welcome aboard",
        (
            "Welcome to the team.\n\n"
            "This course walks you through the essentials for your first 30 days:\n"
            "• How we communicate and make decisions\n"
            "• Core workplace expectations\n"
            "• Security habits everyone follows\n"
            "• Where to go when you need help\n\n"
            "Complete each lesson, then take the chapter quiz to unlock the next section."
        ),
        1,
    )
    _slideshow(
        ch1,
        "Our working principles",
        [
            {
                "title": "Customers first",
                "body": (
                    "Every decision should improve the customer outcome.\n"
                    "If something is unclear, ask: does this reduce friction for the people we serve?"
                ),
            },
            {
                "title": "Own the outcome",
                "body": (
                    "We prefer clear ownership over committee fog.\n"
                    "If you take a task, drive it to a decision or a handoff — don’t leave it idle."
                ),
            },
            {
                "title": "Communicate early",
                "body": (
                    "Surprises are expensive.\n"
                    "Share blockers within 24 hours, write decisions down, and keep your manager in the loop."
                ),
            },
            {
                "title": "Respect the craft",
                "body": (
                    "Quality compounds.\n"
                    "Review your own work before asking for review. Leave the codebase, ticket, or document better than you found it."
                ),
            },
        ],
        2,
    )
    _video(
        ch1,
        "How great teams onboard",
        "https://www.youtube.com/embed/ZXsQAXx_ao0",
        3,
        description="Short motivational clip — watch fullscreen, then continue.",
    )
    _test(
        ch1,
        "Culture check",
        70,
        [
            {
                "prompt": "What should you do when you hit a blocker that may delay delivery?",
                "type": QuestionType.MCQ,
                "choices": [
                    {"label": "Wait until the weekly status meeting", "correct": False},
                    {"label": "Raise it early (within about 24 hours) with context and options", "correct": True},
                    {"label": "Only tell teammates if they ask", "correct": False},
                    {"label": "Ignore it and hope it resolves itself", "correct": False},
                ],
            },
            {
                "prompt": "“Own the outcome” means leaving work idle until someone else notices.",
                "type": QuestionType.TRUE_FALSE,
                "choices": [
                    {"label": "True", "correct": False},
                    {"label": "False", "correct": True},
                ],
            },
            {
                "prompt": "Which question best reflects a customers-first mindset?",
                "type": QuestionType.MCQ,
                "choices": [
                    {"label": "Will this impress leadership in a slide deck?", "correct": False},
                    {"label": "Does this reduce friction for the people we serve?", "correct": True},
                    {"label": "Can we ship without documentation?", "correct": False},
                    {"label": "Is this the easiest change for our team?", "correct": False},
                ],
            },
        ],
    )

    ch2 = _chapter(
        course,
        "Security & workplace basics",
        "Protect company and customer data from day one.",
        2,
    )
    _slideshow(
        ch2,
        "Security habits that matter",
        [
            {
                "title": "Never share credentials",
                "body": (
                    "Do not share passwords, OTP codes, or session links.\n"
                    "Use the approved password manager and enable MFA on every work account."
                ),
            },
            {
                "title": "Think before you click",
                "body": (
                    "Phishing often looks urgent and official.\n"
                    "Hover links, verify the sender domain, and report suspicious mail instead of engaging."
                ),
            },
            {
                "title": "Least privilege",
                "body": (
                    "Only request access you need for your role.\n"
                    "If you change teams, ask IT to review access you no longer require."
                ),
            },
            {
                "title": "Public spaces",
                "body": (
                    "Lock your screen when you step away.\n"
                    "Avoid discussing confidential customer or payroll details in open areas or on speakerphone."
                ),
            },
        ],
        1,
    )
    _text(
        ch2,
        "When something feels wrong",
        (
            "If you suspect a security incident:\n\n"
            "1. Stop interacting with the suspicious message or device\n"
            "2. Capture what you can (screenshot, sender, time)\n"
            "3. Contact IT / Security immediately\n"
            "4. Do not delete evidence until advised\n\n"
            "Reporting quickly is always the right move — even if it turns out to be a false alarm."
        ),
        2,
    )
    _test(
        ch2,
        "Security quiz",
        80,
        [
            {
                "prompt": "A colleague asks you to text your MFA code because they are locked out of a shared mailbox. What should you do?",
                "type": QuestionType.MCQ,
                "choices": [
                    {"label": "Send the code once, then change your password", "correct": False},
                    {"label": "Refuse and direct them to IT / the approved recovery process", "correct": True},
                    {"label": "Post the code in the team chat so anyone can help", "correct": False},
                    {"label": "Email the code to their personal Gmail", "correct": False},
                ],
            },
            {
                "prompt": "You should enable MFA on work accounts whenever it is available.",
                "type": QuestionType.TRUE_FALSE,
                "choices": [
                    {"label": "True", "correct": True},
                    {"label": "False", "correct": False},
                ],
            },
            {
                "prompt": "Which is the best first response to a suspected phishing email?",
                "type": QuestionType.MCQ,
                "choices": [
                    {"label": "Click the link to see if the site looks real", "correct": False},
                    {"label": "Forward it to customers as a warning", "correct": False},
                    {"label": "Report it to IT/Security and avoid interacting with links", "correct": True},
                    {"label": "Reply asking the sender to confirm identity", "correct": False},
                ],
            },
            {
                "prompt": "Leaving your unlocked laptop in a meeting room is acceptable if you will return in five minutes.",
                "type": QuestionType.TRUE_FALSE,
                "choices": [
                    {"label": "True", "correct": False},
                    {"label": "False", "correct": True},
                ],
            },
        ],
    )

    ch3 = _chapter(
        course,
        "Getting productive",
        "Systems, support channels, and your first deliverables.",
        3,
    )
    _text(
        ch3,
        "Where to get help",
        (
            "Use the right channel:\n\n"
            "• Manager — priorities, expectations, career questions\n"
            "• Helpdesk — access, devices, software issues\n"
            "• HR — policies, leave, payroll inquiries\n"
            "• Team chat — day-to-day collaboration\n\n"
            "Write clear requests: what you need, why, and by when."
        ),
        1,
    )
    _video(
        ch3,
        "Working with focus",
        "https://www.youtube.com/embed/WUVCmkf5xAQ",
        2,
        description="Optional perspective on deep work — watch fullscreen if helpful.",
    )
    return course


def _build_harassment(company, category):
    course, _ = _ensure_course(
        company,
        category,
        code="CMP-201",
        title="Respectful Workplace & Anti-Harassment",
        description=(
            "Mandatory compliance training on respectful conduct, recognizing harassment, "
            "and how to report concerns safely. Assignment-only for audit tracking."
        ),
        difficulty="beginner",
        allow_self_enroll=False,
    )
    _wipe_course_content(course)

    ch1 = _chapter(course, "Standards of conduct", "What respectful behavior looks like day to day.", 1)
    _slideshow(
        ch1,
        "Respect in practice",
        [
            {
                "title": "What we expect",
                "body": (
                    "Everyone deserves a workplace free from harassment and discrimination.\n"
                    "This includes interactions in the office, on video calls, in chat, and at work events."
                ),
            },
            {
                "title": "Harassment is about impact",
                "body": (
                    "Intent matters for coaching, but impact matters for safety.\n"
                    "If behavior creates a hostile environment, it must be addressed — jokes and banter are not exemptions."
                ),
            },
            {
                "title": "Protected characteristics",
                "body": (
                    "Do not target people based on race, religion, gender, age, disability, "
                    "national origin, or other protected attributes under applicable law and company policy."
                ),
            },
            {
                "title": "Digital workplaces count",
                "body": (
                    "Emojis, memes, DMs, and off-channel chats are still workplace communication.\n"
                    "If you would not say it in a meeting with leadership present, reconsider sending it."
                ),
            },
        ],
        1,
    )
    _text(
        ch1,
        "Examples that cross the line",
        (
            "Examples of unacceptable behavior include:\n\n"
            "• Unwelcome comments about appearance or personal life\n"
            "• Repeated invitations after someone has declined\n"
            "• Displaying or circulating offensive material\n"
            "• Retaliating against someone who raises a concern\n\n"
            "When unsure, pause and ask yourself whether a reasonable person could find the behavior unwelcome."
        ),
        2,
    )
    _test(
        ch1,
        "Conduct knowledge check",
        80,
        [
            {
                "prompt": "A teammate keeps sending flirtatious messages after being asked to stop. This can be harassment even if they claim it was “just a joke.”",
                "type": QuestionType.TRUE_FALSE,
                "choices": [
                    {"label": "True", "correct": True},
                    {"label": "False", "correct": False},
                ],
            },
            {
                "prompt": "Which channel is still covered by respectful workplace expectations?",
                "type": QuestionType.MCQ,
                "choices": [
                    {"label": "Only formal email", "correct": False},
                    {"label": "Only in-person conversations", "correct": False},
                    {"label": "Chat, video calls, email, and work events", "correct": True},
                    {"label": "Only conversations with managers", "correct": False},
                ],
            },
            {
                "prompt": "Retaliating against someone for reporting a concern is prohibited.",
                "type": QuestionType.TRUE_FALSE,
                "choices": [
                    {"label": "True", "correct": True},
                    {"label": "False", "correct": False},
                ],
            },
        ],
    )

    ch2 = _chapter(course, "Reporting & support", "How to raise concerns and what happens next.", 2)
    _slideshow(
        ch2,
        "How to report",
        [
            {
                "title": "You have options",
                "body": (
                    "Report to your manager, HR, or the confidential reporting channel listed in policy.\n"
                    "If your manager is involved, escalate to HR or another leader."
                ),
            },
            {
                "title": "What to share",
                "body": (
                    "Dates, people involved, what was said or done, and any screenshots or witnesses help the review.\n"
                    "You do not need a perfect case file to speak up."
                ),
            },
            {
                "title": "Confidentiality & fairness",
                "body": (
                    "Reports are handled as confidentially as practical.\n"
                    "Investigations aim to be fair to all parties and based on facts, not rumors."
                ),
            },
        ],
        1,
    )
    _test(
        ch2,
        "Reporting quiz",
        75,
        [
            {
                "prompt": "If your manager is the person whose behavior concerns you, you should still only report to that manager.",
                "type": QuestionType.TRUE_FALSE,
                "choices": [
                    {"label": "True", "correct": False},
                    {"label": "False", "correct": True},
                ],
            },
            {
                "prompt": "What should you include when reporting if available?",
                "type": QuestionType.MCQ,
                "choices": [
                    {"label": "Only the names of people you dislike", "correct": False},
                    {"label": "Dates, description of events, and any evidence or witnesses", "correct": True},
                    {"label": "Anonymous social media posts about the team", "correct": False},
                    {"label": "Nothing — HR will discover everything automatically", "correct": False},
                ],
            },
        ],
    )
    return course


def _build_leadership(company, category):
    course, _ = _ensure_course(
        company,
        category,
        code="LDR-310",
        title="People Leadership Foundations",
        description=(
            "For new managers: one-on-ones, feedback, coaching, and running effective team rituals. "
            "Blend of frameworks, video, and a practical quiz."
        ),
        difficulty="intermediate",
        allow_self_enroll=True,
    )
    _wipe_course_content(course)

    ch1 = _chapter(course, "The manager’s job", "Shift from individual contributor to multiplier.", 1)
    _text(
        ch1,
        "From doing to enabling",
        (
            "As a manager, your output is the team’s outcomes.\n\n"
            "Priorities:\n"
            "1. Clarity — goals, owners, deadlines\n"
            "2. Coaching — help people grow capability\n"
            "3. Climate — psychological safety and accountability\n"
            "4. Calibration — fair performance conversations\n\n"
            "You will still do some individual work, but protecting team focus is now your craft."
        ),
        1,
    )
    _slideshow(
        ch1,
        "Weekly leadership cadence",
        [
            {
                "title": "1:1s are non-negotiable",
                "body": (
                    "Hold recurring 1:1s. Agenda belongs to the report first.\n"
                    "Cover wellbeing, priorities, blockers, and career — not only task status."
                ),
            },
            {
                "title": "Feedback within the week",
                "body": (
                    "Give specific, timely feedback while the example is fresh.\n"
                    "Separate appreciation, coaching, and evaluation so the message is clear."
                ),
            },
            {
                "title": "Meetings with purpose",
                "body": (
                    "Every meeting needs an owner, outcome, and agenda.\n"
                    "Cancel rituals that do not produce decisions or shared understanding."
                ),
            },
        ],
        2,
    )
    _video(
        ch1,
        "Leadership mindset",
        "https://www.youtube.com/embed/fLQnP87XI0s",
        3,
    )
    _test(
        ch1,
        "Manager foundations quiz",
        70,
        [
            {
                "prompt": "In a healthy 1:1, whose agenda should usually come first?",
                "type": QuestionType.MCQ,
                "choices": [
                    {"label": "The manager’s status checklist only", "correct": False},
                    {"label": "The direct report’s topics, with space for manager input", "correct": True},
                    {"label": "HR’s annual form", "correct": False},
                    {"label": "Whatever is trending in company chat", "correct": False},
                ],
            },
            {
                "prompt": "Effective feedback is specific and timely.",
                "type": QuestionType.TRUE_FALSE,
                "choices": [
                    {"label": "True", "correct": True},
                    {"label": "False", "correct": False},
                ],
            },
            {
                "prompt": "A meeting without a clear outcome or agenda should usually be:",
                "type": QuestionType.MCQ,
                "choices": [
                    {"label": "Extended so people can brainstorm freely forever", "correct": False},
                    {"label": "Kept on the calendar for culture reasons", "correct": False},
                    {"label": "Restructured or canceled", "correct": True},
                    {"label": "Moved to a larger audience", "correct": False},
                ],
            },
        ],
    )

    ch2 = _chapter(course, "Coaching conversations", "Help people improve without taking the work back.", 2)
    _slideshow(
        ch2,
        "Grow capability",
        [
            {
                "title": "Ask before telling",
                "body": (
                    "Start with curiosity: What have you tried? What options do you see?\n"
                    "Advice lands better after the other person has reasoned aloud."
                ),
            },
            {
                "title": "Delegate outcomes, not chores",
                "body": (
                    "Define the result, constraints, and check-in points.\n"
                    "Avoid hover-managing every keystroke — agree on milestones instead."
                ),
            },
            {
                "title": "Document decisions",
                "body": (
                    "Write down expectations after important coaching moments.\n"
                    "Shared notes prevent “I thought you meant…” surprises later."
                ),
            },
        ],
        1,
    )
    _test(
        ch2,
        "Coaching quiz",
        70,
        [
            {
                "prompt": "The best first move when a report is stuck is often to ask what they have already tried.",
                "type": QuestionType.TRUE_FALSE,
                "choices": [
                    {"label": "True", "correct": True},
                    {"label": "False", "correct": False},
                ],
            },
            {
                "prompt": "Delegating effectively usually means:",
                "type": QuestionType.MCQ,
                "choices": [
                    {"label": "Assigning tasks with no context so people “figure it out”", "correct": False},
                    {"label": "Defining the outcome, constraints, and check-ins", "correct": True},
                    {"label": "Doing the work yourself after assigning it", "correct": False},
                    {"label": "Only delegating work you dislike", "correct": False},
                ],
            },
        ],
    )
    return course


def _build_data_privacy(company, category):
    course, _ = _ensure_course(
        company,
        category,
        code="SEC-220",
        title="Data Privacy for Everyday Work",
        description=(
            "Practical privacy habits for HR, sales, and operations: personal data handling, "
            "sharing rules, and breach response basics."
        ),
        difficulty="intermediate",
        allow_self_enroll=True,
    )
    _wipe_course_content(course)

    ch1 = _chapter(course, "Personal data basics", "What counts as personal data and why it matters.", 1)
    _slideshow(
        ch1,
        "Know the data you touch",
        [
            {
                "title": "Personal data is everywhere",
                "body": (
                    "Names, emails, phone numbers, ID documents, payroll details, "
                    "and performance notes can all be personal data."
                ),
            },
            {
                "title": "Use only what you need",
                "body": (
                    "Collect and share the minimum required for the task.\n"
                    "Do not copy employee files into personal drives “for convenience.”"
                ),
            },
            {
                "title": "Share with purpose",
                "body": (
                    "Before forwarding a spreadsheet, ask: who needs this, for what, and for how long?\n"
                    "Prefer role-based access over email attachments when possible."
                ),
            },
        ],
        1,
    )
    _video(
        ch1,
        "Privacy in plain language",
        "https://www.youtube.com/embed/aOE2kcjafyE",
        2,
    )
    _test(
        ch1,
        "Privacy fundamentals",
        75,
        [
            {
                "prompt": "An employee’s personal mobile number in an HR spreadsheet is personal data.",
                "type": QuestionType.TRUE_FALSE,
                "choices": [
                    {"label": "True", "correct": True},
                    {"label": "False", "correct": False},
                ],
            },
            {
                "prompt": "Which practice best matches “minimum necessary” data use?",
                "type": QuestionType.MCQ,
                "choices": [
                    {"label": "Export the entire employee database to answer one question", "correct": False},
                    {"label": "Share only the fields required for the specific task", "correct": True},
                    {"label": "Post payroll files in a public channel for transparency", "correct": False},
                    {"label": "Email raw ID scans to your personal account for backup", "correct": False},
                ],
            },
            {
                "prompt": "Preferring role-based system access over emailing spreadsheets generally reduces privacy risk.",
                "type": QuestionType.TRUE_FALSE,
                "choices": [
                    {"label": "True", "correct": True},
                    {"label": "False", "correct": False},
                ],
            },
        ],
    )

    ch2 = _chapter(course, "Incidents & vendors", "What to do when data may have been exposed.", 2)
    _text(
        ch2,
        "If you suspect a privacy incident",
        (
            "Examples: email sent to the wrong person, lost laptop, misconfigured share link.\n\n"
            "1. Contain — stop further sharing if you can\n"
            "2. Notify IT/Security/Privacy immediately\n"
            "3. Preserve details — who, what, when\n"
            "4. Do not attempt a quiet fix that hides the issue\n\n"
            "Early reporting protects people and the company."
        ),
        1,
    )
    _test(
        ch2,
        "Incident response quiz",
        80,
        [
            {
                "prompt": "You accidentally emailed a candidate list to the wrong external address. What should you do first?",
                "type": QuestionType.MCQ,
                "choices": [
                    {"label": "Delete your sent folder and hope nobody notices", "correct": False},
                    {"label": "Contain if possible and notify IT/Security/Privacy right away", "correct": True},
                    {"label": "Wait a week to see if anyone replies", "correct": False},
                    {"label": "Ask the recipient to keep it confidential and take no other action", "correct": False},
                ],
            },
            {
                "prompt": "Quietly fixing a privacy mistake without reporting it is acceptable if no customer complained.",
                "type": QuestionType.TRUE_FALSE,
                "choices": [
                    {"label": "True", "correct": False},
                    {"label": "False", "correct": True},
                ],
            },
        ],
    )
    return course


class Command(BaseCommand):
    help = "Seed realistic LMS categories, courses, fullscreen media lessons, and quizzes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--enroll-count",
            type=int,
            default=8,
            help="How many active employees to assign demo courses to (default 8).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        company = Company.objects.filter(is_active=True).order_by("id").first()
        if not company:
            self.stderr.write("No company found; aborting.")
            return

        onboarding = _ensure_category(
            company,
            "Onboarding",
            "First-week essentials for every new hire.",
        )
        compliance = _ensure_category(
            company,
            "Compliance",
            "Required workplace and regulatory training.",
        )
        leadership = _ensure_category(
            company,
            "Leadership",
            "Manager and people-leadership skills.",
        )
        security = _ensure_category(
            company,
            "Security & Privacy",
            "Protecting company and personal data.",
        )

        courses = [
            _build_onboarding(company, onboarding),
            _build_harassment(company, compliance),
            _build_leadership(company, leadership),
            _build_data_privacy(company, security),
        ]

        User = get_user_model()
        assigner = User.objects.filter(is_superuser=True).first() or User.objects.first()
        enrolled = 0
        enroll_count = max(0, options["enroll_count"])
        if assigner and enroll_count:
            employees = list(Employee.objects.filter(is_active=True)[:enroll_count])
            due = timezone.now() + timedelta(days=21)
            for course in courses:
                # Compliance course is assignment-only; assign everyone in sample.
                # Others: assign half for a mixed catalog feel.
                targets = employees if course.code == "CMP-201" else employees[: max(1, len(employees) // 2)]
                for employee in targets:
                    _, was_created = CourseEnrollment.objects.get_or_create(
                        company_id=company,
                        course_id=course,
                        employee_id=employee,
                        defaults={
                            "assigned_by": assigner,
                            "due_at": due if course.code == "CMP-201" else None,
                            "status": EnrollmentStatus.ASSIGNED,
                            "source": EnrollmentSource.ASSIGNED,
                            "notes": "Demo assignment from seed_lms_demo",
                        },
                    )
                    if was_created:
                        enrolled += 1

        lesson_total = Lesson.objects.filter(module_id__course_id__in=courses).count()
        self.stdout.write(
            self.style.SUCCESS(
                "LMS demo catalog ready: "
                f"{len(courses)} courses, {lesson_total} lessons, "
                f"{enrolled} new enrollments."
            )
        )
        for course in courses:
            self.stdout.write(f"  • {course.code} — {course.title}")
