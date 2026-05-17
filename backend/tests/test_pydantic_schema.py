"""Regression tests for Pydantic v2 quiz schema validation.

Covers strict field validation per question type and API shape preservation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.domain.pydantic_models import (
    FillBlankQuestion,
    MatchingQuestion,
    QuizPayload,
    SingleChoiceQuestion,
)
from backend.app.domain.normalization import normalize_quiz_output


class TestFillBlankRejectsMatchingPairs:
    """Regression: fill_blank with matching_pairs must be rejected."""

    def test_fill_blank_with_matching_pairs_fails(self) -> None:
        """fill_blank should reject payload with matching_pairs field."""
        with pytest.raises(ValidationError) as exc_info:
            FillBlankQuestion.model_validate({
                "questionId": "q1",
                "questionType": "fill_blank",
                "prompt": "Заполните пропуск",
                "correctAnswer": "ответ",
                "matchingPairs": [{"left": "A", "right": "B"}],
            })
        assert "matchingPairs" in str(exc_info.value) or "extra_forbidden" in str(exc_info.value)


class TestMatchingRequiresFourPairs:
    """Regression: matching with fewer than 4 pairs must be rejected."""

    def test_matching_with_three_pairs_fails(self) -> None:
        """matching requires at least 4 pairs."""
        with pytest.raises(ValidationError) as exc_info:
            MatchingQuestion.model_validate({
                "questionId": "q1",
                "questionType": "matching",
                "prompt": "Соотнесите",
                "matchingPairs": [
                    {"left": "A1", "right": "B1"},
                    {"left": "A2", "right": "B2"},
                    {"left": "A3", "right": "B3"},
                ],
            })
        assert "matchingPairs" in str(exc_info.value)

    def test_matching_with_symbolic_right_fails(self) -> None:
        """matching pairs with symbolic right values (A/B/C/D) must be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MatchingQuestion.model_validate({
                "questionId": "q1",
                "questionType": "matching",
                "prompt": "Соотнесите",
                "matchingPairs": [
                    {"left": "A1", "right": "a"},
                    {"left": "A2", "right": "B2"},
                    {"left": "A3", "right": "B3"},
                    {"left": "A4", "right": "B4"},
                ],
            })
        assert "matching pair right must contain full text" in str(exc_info.value)


class TestSingleChoiceRequiresOptions:
    """Regression: single_choice without options or correct_option_index fails."""

    def test_single_choice_without_options_fails(self) -> None:
        """single_choice requires at least 2 options."""
        with pytest.raises(ValidationError) as exc_info:
            SingleChoiceQuestion.model_validate({
                "questionId": "q1",
                "questionType": "single_choice",
                "prompt": "Выберите",
                "options": [],
                "correctOptionIndex": 0,
            })
        assert "options" in str(exc_info.value)

    def test_single_choice_with_correct_answer_fails(self) -> None:
        """single_choice must not have correct_answer field."""
        with pytest.raises(ValidationError) as exc_info:
            SingleChoiceQuestion.model_validate({
                "questionId": "q1",
                "questionType": "single_choice",
                "prompt": "Выберите",
                "options": [
                    {"optionId": "o1", "text": "Вариант 1"},
                    {"optionId": "o2", "text": "Вариант 2"},
                ],
                "correctOptionIndex": 0,
                "correctAnswer": "Вариант 1",
            })
        # correctAnswer should be None for single_choice
        assert "correctAnswer" in str(exc_info.value) or "extra_forbidden" in str(exc_info.value)


class TestApiShapePreservation:
    """Regression: valid quiz must serialize to same API shape."""

    def test_valid_quiz_roundtrips_through_normalization(self) -> None:
        """QuizPayload validation + normalization preserves API shape."""
        raw_quiz = {
            "quiz_id": "quiz-test",
            "document_id": "doc-test",
            "title": "Тестовый квиз",
            "version": 1,
            "last_edited_at": "2024-01-01T00:00:00Z",
            "questions": [
                {
                    "question_id": "q1",
                    "question_type": "single_choice",
                    "prompt": "Какой вариант?",
                    "options": [
                        {"option_id": "o1", "text": "Первый"},
                        {"option_id": "o2", "text": "Второй"},
                    ],
                    "correct_option_index": 0,
                    "explanation": None,
                },
                {
                    "question_id": "q2",
                    "question_type": "matching",
                    "prompt": "Соотнесите",
                    "matching_pairs": [
                        {"left": "Понятие 1", "right": "Определение 1"},
                        {"left": "Понятие 2", "right": "Определение 2"},
                        {"left": "Понятие 3", "right": "Определение 3"},
                        {"left": "Понятие 4", "right": "Определение 4"},
                    ],
                    "explanation": {"text": "Пояснение"},
                },
            ],
        }

        # Should normalize without errors
        domain_quiz = normalize_quiz_output(raw_quiz)

        # Verify structure preserved
        assert domain_quiz.quiz_id == "quiz-test"
        assert domain_quiz.title == "Тестовый квиз"
        assert len(domain_quiz.questions) == 2

        # First question is single_choice
        q1 = domain_quiz.questions[0]
        assert q1.question_type == "single_choice"
        assert q1.correct_option_index == 0
        assert len(q1.options) == 2

        # Second question is matching with 4 pairs
        q2 = domain_quiz.questions[1]
        assert q2.question_type == "matching"
        assert len(q2.matching_pairs) == 4

    def test_russian_cyrillic_preserved(self) -> None:
        """Russian/Cyrillic text preserved through validation."""
        raw_quiz = {
            "quiz_id": "quiz-russian",
            "document_id": "doc-russian",
            "title": "Квиз на русском языке",
            "version": 1,
            "last_edited_at": "2024-01-01T00:00:00Z",
            "questions": [
                {
                    "question_id": "q1",
                    "question_type": "short_answer",
                    "prompt": "Что такое фотосинтез?",
                    "correct_answer": "Процесс превращения углекислого газа и воды в глюкозу и кислород",
                },
            ],
        }

        domain_quiz = normalize_quiz_output(raw_quiz)

        # Cyrillic text preserved
        assert "русском" in domain_quiz.title
        assert "фотосинтез" in domain_quiz.questions[0].prompt
        assert "глюкозу" in domain_quiz.questions[0].correct_answer


class TestQuestionTypeDiscriminator:
    """Regression: discriminated union must route to correct question type."""

    def test_unknown_question_type_fails(self) -> None:
        """Unknown question_type must be rejected by discriminator."""
        with pytest.raises(ValidationError) as exc_info:
            QuizPayload.model_validate({
                "quizId": "quiz-test",
                "documentId": "doc-test",
                "title": "Test",
                "version": 1,
                "lastEditedAt": "2024-01-01T00:00:00Z",
                "questions": [
                    {
                        "questionId": "q1",
                        "questionType": "unknown_type",
                        "prompt": "Question?",
                    },
                ],
            })
        assert "discriminator" in str(exc_info.value) or "questionType" in str(exc_info.value)
