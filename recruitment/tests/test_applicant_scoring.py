"""Unit tests for applicant scoring helpers."""

from types import SimpleNamespace
from unittest import TestCase

from recruitment.applicant_scoring import (
    answer_values_for_question,
    score_question_answer,
    skill_match_count,
)


class ApplicantScoringTests(TestCase):
    def test_skill_match_count_fuzzy(self):
        text = "experienced in python django and postgresql databases"
        skills = ["Python", "Django", "Java"]
        self.assertEqual(skill_match_count(text, skills), 2)

    def test_score_options_match(self):
        question = SimpleNamespace(
            type="options",
            preferred_answers="Senior, Lead",
        )
        self.assertEqual(score_question_answer(question, ["Senior"]), 1.0)
        self.assertEqual(score_question_answer(question, ["Junior"]), 0.0)

    def test_score_text_keywords(self):
        question = SimpleNamespace(
            type="textarea",
            preferred_answers="kubernetes|aws|microservices",
        )
        self.assertEqual(
            score_question_answer(question, ["We run on AWS with microservices"]),
            2 / 3,
        )

    def test_score_rating_range(self):
        question = SimpleNamespace(type="rating", preferred_answers="4-5")
        self.assertEqual(score_question_answer(question, ["5"]), 1.0)
        self.assertEqual(score_question_answer(question, ["2"]), 0.0)

    def test_answer_values_rating_prefix(self):
        data = {"rating_Experience": ["4"]}
        values = answer_values_for_question(data, "Experience", "rating")
        self.assertEqual(values, ["4"])
