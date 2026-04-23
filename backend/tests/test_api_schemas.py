from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.api.schemas import GenerationRequestBody
from backend.app.api.schemas import QuizUpdateBody


def test_generation_request_body_accepts_whitelisted_values() -> None:
    body = GenerationRequestBody.model_validate(
        {
            "question_count": 3,
            "language": "ru",
            "difficulty": "medium",
            "quiz_type": "single_choice",
            "generation_mode": "direct",
        }
    )
    request = body.to_domain()
    assert request.question_count == 3
    assert request.language == "ru"
    assert request.difficulty == "medium"
    assert request.quiz_type == "single_choice"


def test_generation_request_body_rejects_non_positive_question_count() -> None:
    with pytest.raises(ValidationError):
        GenerationRequestBody.model_validate(
            {
                "question_count": 0,
                "language": "ru",
                "difficulty": "medium",
                "quiz_type": "single_choice",
                "generation_mode": "direct",
            }
        )


def test_generation_request_body_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        GenerationRequestBody.model_validate(
            {
                "question_count": 3,
                "language": "ru",
                "difficulty": "medium",
                "quiz_type": "single_choice",
                "generation_mode": "direct",
                "max_tokens": 1024,
            }
        )


def test_quiz_update_body_roundtrips_russian_content() -> None:
    payload = {
        "quiz": {
            "quiz_id": "quiz-1",
            "document_id": "doc-1",
            "title": "Русский квиз",
            "version": 1,
            "last_edited_at": "2026-04-18T00:00:00Z",
            "questions": [
                {
                    "question_id": "q-1",
                    "prompt": "Какой город — столица России?",
                    "options": [
                        {"option_id": "opt-1", "text": "Москва"},
                        {"option_id": "opt-2", "text": "Санкт-Петербург"},
                    ],
                    "correct_option_index": 0,
                    "explanation": {"text": "Москва — столица России."},
                }
            ],
        }
    }

    body = QuizUpdateBody.model_validate(payload)
    quiz = body.quiz.to_domain()

    assert quiz.title == "Русский квиз"
    assert quiz.questions[0].prompt == "Какой город — столица России?"
    assert quiz.questions[0].options[0].text == "Москва"
    assert quiz.questions[0].explanation is not None
    assert quiz.questions[0].explanation.text == "Москва — столица России."


def test_quiz_update_body_rejects_empty_questions() -> None:
    with pytest.raises(ValidationError):
        QuizUpdateBody.model_validate(
            {
                "quiz": {
                    "quiz_id": "quiz-1",
                    "document_id": "doc-1",
                    "title": "Русский квиз",
                    "version": 1,
                    "last_edited_at": "2026-04-18T00:00:00Z",
                    "questions": [],
                }
            }
        )


def test_quiz_update_body_rejects_single_option_question() -> None:
    with pytest.raises(ValidationError):
        QuizUpdateBody.model_validate(
            {
                "quiz": {
                    "quiz_id": "quiz-1",
                    "document_id": "doc-1",
                    "title": "Русский квиз",
                    "version": 1,
                    "last_edited_at": "2026-04-18T00:00:00Z",
                    "questions": [
                        {
                            "question_id": "q-1",
                            "prompt": "Какой город — столица России?",
                            "options": [{"option_id": "opt-1", "text": "Москва"}],
                            "correct_option_index": 0,
                            "explanation": None,
                        }
                    ],
                }
            }
        )
