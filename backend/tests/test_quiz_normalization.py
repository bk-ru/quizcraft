import pytest

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.normalization import normalize_quiz_output
from backend.app.domain.normalization import resolve_readable_quiz_title


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


def test_resolve_readable_quiz_title_preserves_meaningful_llm_title() -> None:
    """If LLM provided a meaningful title, keep it as-is."""

    result = resolve_readable_quiz_title("География России", "document.txt", 5)
    assert result == "География России"


def test_resolve_readable_quiz_title_generates_from_filename() -> None:
    """Generate readable title from filename when LLM returned default."""

    result = resolve_readable_quiz_title("Сгенерированный квиз", "lecture_notes_2026.txt", 10)
    assert result == "lecture notes 2026 — 10 вопросов"


def test_resolve_readable_quiz_title_replaces_generic_model_title_with_filename() -> None:
    """Replace generic model titles with the uploaded Russian filename."""

    result = resolve_readable_quiz_title("quiz_1", "География_России.txt", 7)
    assert result == "География России — 7 вопросов"


def test_resolve_readable_quiz_title_replaces_hyphenated_generic_model_title() -> None:
    """Replace numbered generic model titles with readable document names."""

    result = resolve_readable_quiz_title("quiz-12", "История-Москвы.pdf", 3)
    assert result == "История Москвы — 3 вопроса"


def test_resolve_readable_quiz_title_handles_cyrillic_filename() -> None:
    """Handle Russian filenames correctly."""

    result = resolve_readable_quiz_title("Сгенерированный квиз", "История_Москвы.docx", 5)
    assert result == "История Москвы — 5 вопросов"


def test_resolve_readable_quiz_title_uses_correct_pluralization() -> None:
    """Use correct Russian plural forms for question count."""

    assert resolve_readable_quiz_title("Сгенерированный квиз", "doc.txt", 1) == "doc — 1 вопрос"
    assert resolve_readable_quiz_title("Сгенерированный квиз", "doc.txt", 2) == "doc — 2 вопроса"
    assert resolve_readable_quiz_title("Сгенерированный квиз", "doc.txt", 4) == "doc — 4 вопроса"
    assert resolve_readable_quiz_title("Сгенерированный квиз", "doc.txt", 5) == "doc — 5 вопросов"
    assert resolve_readable_quiz_title("Сгенерированный квиз", "doc.txt", 11) == "doc — 11 вопросов"
    assert resolve_readable_quiz_title("Сгенерированный квиз", "doc.txt", 21) == "doc — 21 вопрос"
    assert resolve_readable_quiz_title("Сгенерированный квиз", "doc.txt", 22) == "doc — 22 вопроса"
    assert resolve_readable_quiz_title("Сгенерированный квиз", "doc.txt", 25) == "doc — 25 вопросов"
    assert resolve_readable_quiz_title("Сгенерированный квиз", "doc.txt", 111) == "doc — 111 вопросов"


def test_resolve_readable_quiz_title_handles_empty_filename() -> None:
    """Fallback to generic name when filename is empty."""

    result = resolve_readable_quiz_title("Сгенерированный квиз", "", 3)
    assert result == "Квиз — 3 вопроса"


def test_resolve_readable_quiz_title_strips_extension() -> None:
    """Remove file extension from filename."""

    result = resolve_readable_quiz_title("Сгенерированный квиз", "report.pdf", 8)
    assert result == "report — 8 вопросов"


def test_resolve_readable_quiz_title_handles_whitespace_only_title() -> None:
    """Treat whitespace-only title as missing and generate from filename."""

    result = resolve_readable_quiz_title("   ", "my_document.txt", 7)
    assert result == "my document — 7 вопросов"
