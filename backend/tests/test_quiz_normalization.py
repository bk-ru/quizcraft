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


def test_normalize_quiz_output_preserves_russian_new_question_types() -> None:
    raw_payload = {
        "quiz_id": "quiz-ru",
        "document_id": "doc-ru",
        "title": "Русский квиз",
        "version": 1,
        "last_edited_at": "2026-05-03T09:00:00Z",
        "questions": [
            {
                "question_id": "q-true",
                "question_type": "true_false",
                "prompt": "Байкал — самое глубокое озеро России.",
                "options": [
                    {"option_id": "true", "text": "Истина"},
                    {"option_id": "false", "text": "Ложь"},
                ],
                "correct_option_index": 0,
                "explanation": {"text": "Байкал действительно является самым глубоким озером."},
            },
            {
                "question_id": "q-short",
                "question_type": "short_answer",
                "prompt": "Как называется столица России?",
                "correct_answer": "Москва",
                "explanation": {"text": "Столица России — Москва."},
            },
            {
                "question_id": "q-match",
                "question_type": "matching",
                "prompt": "Сопоставьте города и реки.",
                "matching_pairs": [
                    {"left": "Санкт-Петербург", "right": "Нева"},
                    {"left": "Казань", "right": "Казанка"},
                ],
                "explanation": None,
            },
        ],
    }

    quiz = normalize_quiz_output(raw_payload)

    assert quiz.questions[0].question_type == "true_false"
    assert quiz.questions[0].options[0].text == "Истина"
    assert quiz.questions[1].question_type == "short_answer"
    assert quiz.questions[1].correct_answer == "Москва"
    assert quiz.questions[2].question_type == "matching"
    assert quiz.questions[2].matching_pairs[0].left == "Санкт-Петербург"
    assert quiz.questions[2].matching_pairs[0].right == "Нева"


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


def test_normalize_quiz_output_infers_short_answer_when_single_choice_has_no_options_but_correct_answer() -> None:
    raw_payload = {
        "quiz_id": "quiz-1",
        "document_id": "doc-1",
        "title": "Тест",
        "version": 1,
        "last_edited_at": "2026-04-18T12:00:00Z",
        "questions": [
            {
                "question_id": "q-1",
                "question_type": "single_choice",
                "prompt": "Назовите столицу России.",
                "options": [],
                "correct_answer": "Москва",
            }
        ],
    }

    quiz = normalize_quiz_output(raw_payload)

    assert quiz.questions[0].question_type == "short_answer"
    assert quiz.questions[0].correct_answer == "Москва"
    assert quiz.questions[0].options == ()


def test_normalize_quiz_output_infers_matching_when_single_choice_has_no_options_but_matching_pairs() -> None:
    raw_payload = {
        "quiz_id": "quiz-1",
        "document_id": "doc-1",
        "title": "Тест",
        "version": 1,
        "last_edited_at": "2026-04-18T12:00:00Z",
        "questions": [
            {
                "question_id": "q-1",
                "question_type": "single_choice",
                "prompt": "Установите соответствие.",
                "options": [],
                "matching_pairs": [
                    {"left": "Класс A", "right": "Твёрдые вещества"},
                    {"left": "Класс B", "right": "Жидкие вещества"},
                ],
            }
        ],
    }

    quiz = normalize_quiz_output(raw_payload)

    assert quiz.questions[0].question_type == "matching"
    assert len(quiz.questions[0].matching_pairs) == 2
    assert quiz.questions[0].matching_pairs[0].left == "Класс A"
