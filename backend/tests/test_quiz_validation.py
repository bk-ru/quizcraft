from dataclasses import replace

import pytest

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import GenerationQualityError
from backend.app.domain.models import Explanation
from backend.app.domain.models import Option
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.domain.validation import validate_quiz
from backend.app.generation.quality import GenerationQualityChecker


def build_valid_quiz() -> Quiz:
    return Quiz(
        quiz_id="quiz-1",
        document_id="doc-1",
        title="Sample quiz",
        version=1,
        last_edited_at="2026-04-18T12:00:00Z",
        questions=(
            Question(
                question_id="q-1",
                prompt="What is 2 + 2?",
                options=(
                    Option(option_id="opt-1", text="3"),
                    Option(option_id="opt-2", text="4"),
                ),
                correct_option_index=1,
                explanation=Explanation(text="2 + 2 = 4."),
            ),
            Question(
                question_id="q-2",
                prompt="What is the capital of France?",
                options=(
                    Option(option_id="opt-1", text="Paris"),
                    Option(option_id="opt-2", text="Berlin"),
                ),
                correct_option_index=0,
                explanation=None,
            ),
        ),
    )


def test_validate_quiz_rejects_empty_option_text() -> None:
    quiz = build_valid_quiz()
    broken_question = replace(
        quiz.questions[0],
        options=(
            Option(option_id="opt-1", text="3"),
            Option(option_id="opt-2", text=" "),
        ),
    )

    with pytest.raises(DomainValidationError, match="option text"):
        validate_quiz(replace(quiz, questions=(broken_question, quiz.questions[1])))


def test_validate_quiz_rejects_out_of_range_correct_option_index() -> None:
    quiz = build_valid_quiz()
    broken_question = replace(quiz.questions[0], correct_option_index=3)

    with pytest.raises(DomainValidationError, match="out of range"):
        validate_quiz(replace(quiz, questions=(broken_question, quiz.questions[1])))


def test_generation_quality_checker_rejects_question_count_mismatch() -> None:
    quiz = build_valid_quiz()
    checker = GenerationQualityChecker()

    with pytest.raises(GenerationQualityError, match="question count"):
        checker.ensure_quality(quiz, expected_question_count=1)


def test_generation_quality_checker_rejects_duplicate_question_prompts() -> None:
    quiz = build_valid_quiz()
    duplicate_question = replace(quiz.questions[1], prompt="What is 2 + 2?")
    checker = GenerationQualityChecker()

    with pytest.raises(GenerationQualityError, match="duplicate"):
        checker.ensure_quality(
            replace(quiz, questions=(quiz.questions[0], duplicate_question)),
            expected_question_count=2,
        )


def test_generation_quality_checker_accepts_valid_quiz() -> None:
    checker = GenerationQualityChecker()

    checker.ensure_quality(build_valid_quiz(), expected_question_count=2)


def test_generation_quality_checker_accepts_valid_russian_quiz() -> None:
    checker = GenerationQualityChecker()
    russian_quiz = Quiz(
        quiz_id="quiz-ru",
        document_id="doc-ru",
        title="Итоговый квиз",
        version=1,
        last_edited_at="2026-04-18T12:00:00Z",
        questions=(
            Question(
                question_id="q-1",
                prompt="Как называется спутник Земли?",
                options=(
                    Option(option_id="opt-1", text="Луна"),
                    Option(option_id="opt-2", text="Марс"),
                ),
                correct_option_index=0,
                explanation=Explanation(text="Луна — естественный спутник Земли."),
            ),
        ),
    )

    checker.ensure_quality(russian_quiz, expected_question_count=1)
