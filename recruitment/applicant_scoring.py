"""
Rank career-page applicants in the Applied stage by resume skill match.

Only candidates with source=application in stage_type=applied are included.
"""

import ast
import json
import logging
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional

from django.db.models import QuerySet

logger = logging.getLogger(__name__)

try:
    import pymupdf
except ImportError:  # pragma: no cover
    pymupdf = None

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None


def extract_words_from_pdf(pdf_file) -> str:
    """Extract lowercased text from a resume PDF file field."""
    if not pdf_file or not pymupdf:
        return ""
    try:
        path = getattr(pdf_file, "path", None)
        if not path:
            return ""
        pdf_document = pymupdf.open(path)
        text_chunks = []
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text_chunks.append(page.get_text())
        pdf_document.close()
        return "\n".join(text_chunks).lower()
    except Exception as exc:
        logger.debug("Resume text extraction failed: %s", exc)
        return ""


def skill_match_count(text: str, skills: Iterable[str], threshold: int = 85) -> int:
    if not text or not fuzz:
        return 0
    text = text.lower()
    return sum(
        fuzz.partial_ratio(skill.lower(), text) >= threshold for skill in skills if skill
    )


def normalize_answer_dict(answer_json: Any) -> dict:
    if not answer_json:
        return {}
    if isinstance(answer_json, dict):
        return answer_json
    if isinstance(answer_json, str):
        try:
            return json.loads(answer_json)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(answer_json)
            except (ValueError, SyntaxError):
                return {}
    return {}


def answer_values_for_question(
    answer_dict: dict, question_text: str, question_type: str
) -> List[str]:
    """Resolve stored survey JSON keys to a flat list of answer strings."""
    prefixes = [
        "",
        "rating_",
        "percentage_",
        "date_",
        "multiple_choices_",
        "file_",
    ]
    raw = None
    for prefix in prefixes:
        key = f"{prefix}{question_text}" if prefix else question_text
        if key in answer_dict:
            raw = answer_dict[key]
            break
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(v) for v in raw if v is not None and str(v).strip()]
    return [str(raw)] if str(raw).strip() else []


def _split_preferred(preferred: str) -> List[str]:
    return [part.strip() for part in preferred.split(", ") if part.strip()]


def score_question_answer(question, answer_values: List[str]) -> Optional[float]:
    """
    Return 0.0–1.0 for one question, or None if question is not used in scoring.
    """
    preferred = (question.preferred_answers or "").strip()
    if not preferred:
        return None

    answers = [a.strip() for a in answer_values if str(a).strip()]
    qtype = question.type

    if qtype in ("options", "checkbox"):
        if not answers:
            return 0.0
        answer = answers[0].lower()
        preferred_list = [p.lower() for p in _split_preferred(preferred)]
        return 1.0 if answer in preferred_list else 0.0

    if qtype == "multiple":
        preferred_set = {p.lower() for p in _split_preferred(preferred)}
        selected = {a.lower() for a in answers}
        if not preferred_set:
            return None
        return len(preferred_set & selected) / len(preferred_set)

    if qtype in ("text", "textarea"):
        keywords = [k.strip().lower() for k in preferred.split("|") if k.strip()]
        blob = " ".join(a.lower() for a in answers)
        if not keywords:
            return None
        hits = sum(1 for keyword in keywords if keyword in blob)
        return hits / len(keywords)

    if qtype in ("number", "percentage", "rating"):
        try:
            value = float(answers[0]) if answers else None
        except (ValueError, IndexError, TypeError):
            return 0.0
        if value is None:
            return 0.0
        spec = preferred.strip()
        try:
            if spec.startswith(">="):
                return 1.0 if value >= float(spec[2:].strip()) else 0.0
            if spec.startswith("<="):
                return 1.0 if value <= float(spec[2:].strip()) else 0.0
            if spec.startswith(">"):
                return 1.0 if value > float(spec[1:].strip()) else 0.0
            if spec.startswith("<"):
                return 1.0 if value < float(spec[1:].strip()) else 0.0
            if "-" in spec:
                low, high = spec.split("-", 1)
                lo, hi = float(low.strip()), float(high.strip())
                return 1.0 if lo <= value <= hi else 0.0
            target = float(spec)
            return 1.0 if value == target else 0.0
        except ValueError:
            return 0.0

    return None


def survey_questions_for_recruitment(recruitment):
    from recruitment.models import RecruitmentSurvey

    direct = RecruitmentSurvey.objects.filter(recruitment_ids=recruitment)
    via_template = RecruitmentSurvey.objects.filter(
        template_id__in=recruitment.survey_templates.all()
    )
    return (direct | via_template).distinct().order_by("sequence", "pk")


@dataclass
class ApplicantScore:
    candidate_id: int
    candidate_name: str
    candidate_email: str
    stage_label: str
    skill_matches: int
    skill_total: int
    skill_percent: float
    has_resume: bool


def skill_percent_for_candidate(candidate, recruitment) -> tuple[int, int, float]:
    skills = list(recruitment.skills.values_list("title", flat=True))
    if not skills:
        return 0, 0, 0.0
    text = ""
    if candidate.resume:
        text = extract_words_from_pdf(candidate.resume)
    matches = skill_match_count(text, skills)
    return matches, len(skills), round(100.0 * matches / len(skills), 1)


def survey_percent_for_candidate(candidate, recruitment) -> float:
    from recruitment.models import RecruitmentSurveyAnswer

    questions = list(survey_questions_for_recruitment(recruitment))
    scorable = [q for q in questions if (q.preferred_answers or "").strip()]
    if not scorable:
        return 0.0

    answer_row = (
        RecruitmentSurveyAnswer.objects.filter(
            candidate_id=candidate, recruitment_id=recruitment
        ).first()
        or RecruitmentSurveyAnswer.objects.filter(candidate_id=candidate).first()
    )
    answer_dict = normalize_answer_dict(
        answer_row.answer_json if answer_row else None
    )

    weighted_sum = 0.0
    weight_total = 0
    for question in scorable:
        weight = max(int(question.scoring_weight or 1), 1)
        values = answer_values_for_question(
            answer_dict, question.question, question.type
        )
        fraction = score_question_answer(question, values)
        if fraction is None:
            continue
        weighted_sum += fraction * weight
        weight_total += weight

    if weight_total == 0:
        return 0.0
    return round(100.0 * weighted_sum / weight_total, 1)


def combined_percent(skill_pct: float, survey_pct: float, recruitment) -> float:
    skill_w = max(int(getattr(recruitment, "applicant_skill_score_weight", 50) or 0), 0)
    survey_w = max(
        int(getattr(recruitment, "applicant_survey_score_weight", 50) or 0), 0
    )
    skills_defined = recruitment.skills.exists()
    questions = survey_questions_for_recruitment(recruitment).filter(
        preferred_answers__isnull=False
    ).exclude(preferred_answers="")
    survey_defined = questions.exists()

    if skills_defined and survey_defined and (skill_w + survey_w) > 0:
        return round(
            (skill_pct * skill_w + survey_pct * survey_w) / (skill_w + survey_w), 1
        )
    if skills_defined:
        return skill_pct
    if survey_defined:
        return survey_pct
    return 0.0


def applicants_queryset(recruitment) -> QuerySet:
    from recruitment.models import Candidate

    return (
        Candidate.objects.filter(
            recruitment_id=recruitment,
            canceled=False,
            source="application",
            stage_id__stage_type="applied",
        )
        .select_related("stage_id", "job_position_id")
        .order_by("-created_at")
    )


def rank_applicants(recruitment) -> List[ApplicantScore]:
    results: List[ApplicantScore] = []
    for candidate in applicants_queryset(recruitment):
        skill_matches, skill_total, skill_pct = skill_percent_for_candidate(
            candidate, recruitment
        )
        stage = candidate.stage_id
        results.append(
            ApplicantScore(
                candidate_id=candidate.pk,
                candidate_name=candidate.get_full_name(),
                candidate_email=candidate.get_email() or "",
                stage_label=str(stage) if stage else "",
                skill_matches=skill_matches,
                skill_total=skill_total,
                skill_percent=skill_pct,
                has_resume=bool(candidate.resume),
            )
        )
    results.sort(
        key=lambda row: (row.skill_percent, row.skill_matches),
        reverse=True,
    )
    return results
