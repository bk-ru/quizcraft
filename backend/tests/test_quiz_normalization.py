import pytest

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.normalization import normalize_quiz_output


def test_normalize_quiz_output_drops_extra_fields_and_canonicalizes_payload() -> None:
    raw_payload = {
        "quiz_id": " quiz-1 ",
        "document_id": " doc-1 ",
        "title": "  Sample quiz  ",
        "version": "1",
        "last_edited_at": " 2026-04-18T12:00:00Z ",
        "questions": [
            {
                "question_id": " q-1 ",
                "prompt": "  What is 2 + 2?  ",
                "correct_option_number": "2",
                "options": [
                    {"option_id": " opt-1 ", "text": " 3 ", "junk": "drop"},
                    {"option_id": " opt-2 ", "text": " 4 "},
                    {"option_id": " opt-3 ", "text": "   "},
                ],
                "explanation": {"text": " Because 2 + 2 = 4. "},
                "unexpected": "drop",
            }
        ],
        "ignored": "drop",
    }

    quiz = normalize_quiz_output(raw_payload)

    assert quiz.quiz_id == "quiz-1"
    assert quiz.document_id == "doc-1"
    assert quiz.title == "Sample quiz"
    assert quiz.version == 1
    assert quiz.last_edited_at == "2026-04-18T12:00:00Z"
    assert len(quiz.questions) == 1
    question = quiz.questions[0]
    assert question.question_id == "q-1"
    assert question.prompt == "What is 2 + 2?"
    assert question.correct_option_index == 1
    assert question.explanation is not None
    assert question.explanation.text == "Because 2 + 2 = 4."
    assert tuple(option.option_id for option in question.options) == ("opt-1", "opt-2")
    assert tuple(option.text for option in question.options) == ("3", "4")


def test_normalize_quiz_output_rejects_non_numeric_answer_index() -> None:
    raw_payload = {
        "quiz_id": "quiz-1",
        "document_id": "doc-1",
        "title": "Sample quiz",
        "version": 1,
        "last_edited_at": "2026-04-18T12:00:00Z",
        "questions": [
            {
                "question_id": "q-1",
                "prompt": "What is 2 + 2?",
                "correct_option_index": "second",
                "options": [
                    {"option_id": "opt-1", "text": "3"},
                    {"option_id": "opt-2", "text": "4"},
                ],
                "explanation": None,
            }
        ],
    }

    with pytest.raises(DomainValidationError, match="correct option"):
        normalize_quiz_output(raw_payload)


def test_normalize_quiz_output_preserves_russian_fields() -> None:
    raw_payload = {
        "quiz_id": " quiz-ru ",
        "document_id": " doc-ru ",
        "title": "  Тренировочный квиз  ",
        "version": "1",
        "last_edited_at": " 2026-04-18T12:00:00Z ",
        "questions": [
            {
                "question_id": " q-1 ",
                "prompt": "  Какой город является столицей России?  ",
                "correct_option_number": "1",
                "options": [
                    {"option_id": " opt-1 ", "text": " Москва "},
                    {"option_id": " opt-2 ", "text": " Санкт-Петербург "},
                ],
                "explanation": {"text": " Потому что Москва — столица России. "},
            }
        ],
    }

    quiz = normalize_quiz_output(raw_payload)

    assert quiz.title == "Тренировочный квиз"
    assert quiz.questions[0].prompt == "Какой город является столицей России?"
    assert tuple(option.text for option in quiz.questions[0].options) == ("Москва", "Санкт-Петербург")
    assert quiz.questions[0].explanation is not None
    assert quiz.questions[0].explanation.text == "Потому что Москва — столица России."


def test_normalize_quiz_output_uses_russian_default_title_when_missing() -> None:
    raw_payload = {
        "quiz_id": "quiz-ru",
        "document_id": "doc-ru",
        "version": 1,
        "last_edited_at": "2026-04-18T12:00:00Z",
        "questions": [
            {
                "question_id": "q-1",
                "prompt": "Что изучает информатика?",
                "correct_option_index": 0,
                "options": [
                    {"option_id": "opt-1", "text": "Информационные процессы"},
                    {"option_id": "opt-2", "text": "Только числа"},
                ],
                "explanation": {"text": "Информатика изучает работу с информацией."},
            }
        ],
    }

    quiz = normalize_quiz_output(raw_payload)

    assert quiz.title == "Сгенерированный квиз"
