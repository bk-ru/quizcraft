from __future__ import annotations

from backend.app.domain.models import Explanation
from backend.app.domain.models import MatchingPair
from backend.app.domain.models import Option
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.export.markdown_exporter import QuizMarkdownExporter


def build_quiz_with_all_types() -> Quiz:
    """Build a quiz containing all question types with Cyrillic text."""

    return Quiz(
        quiz_id="quiz-ru-moscow-2026",
        document_id="doc-ru-cyrillic",
        title="Тест по истории Москвы",
        version=1,
        last_edited_at="2026-05-03T19:30:00.000000Z",
        questions=(
            Question(
                question_id="q-1",
                prompt="Когда был основан Московский Кремль?",
                question_type="single_choice",
                options=(
                    Option(option_id="a", text="XII век"),
                    Option(option_id="b", text="XIV век"),
                    Option(option_id="c", text="XVI век"),
                ),
                correct_option_index=1,
                explanation=Explanation(text="Кремль был основан в XIV веке при князе Дмитрии Донском."),
            ),
            Question(
                question_id="q-2",
                prompt="Москва — столица России.",
                question_type="true_false",
                options=(
                    Option(option_id="a", text="Верно"),
                    Option(option_id="b", text="Неверно"),
                ),
                correct_option_index=0,
                explanation=Explanation(text="Москва официально стала столицей России в XV веке."),
            ),
            Question(
                question_id="q-3",
                prompt="Красная площадь расположена рядом с ___.",
                question_type="fill_blank",
                correct_answer="Кремлём",
                explanation=Explanation(text="Красная площадь находится у северо-восточной стены Кремля."),
            ),
            Question(
                question_id="q-4",
                prompt="Какой метрополитен открылся первым в СССР?",
                question_type="short_answer",
                correct_answer="Московский метрополитен",
            ),
            Question(
                question_id="q-5",
                prompt="Сопоставьте достопримечательности с их районами:",
                question_type="matching",
                matching_pairs=(
                    MatchingPair(left="Красная площадь", right="Тверской район"),
                    MatchingPair(left="Кремль", right="Тверской район"),
                    MatchingPair(left="ВДНХ", right="Северо-Восточный округ"),
                ),
            ),
        ),
    )


def test_markdown_exporter_builds_utf8_file_with_all_types() -> None:
    """Export quiz with all question types and verify UTF-8 Cyrillic preservation."""

    exporter = QuizMarkdownExporter()
    quiz = build_quiz_with_all_types()

    result = exporter.export(quiz)

    assert result.filename == "quiz-ru-moscow-2026.md"
    assert result.media_type == "text/markdown; charset=utf-8"

    content = result.content_bytes.decode("utf-8")

    assert "# Тест по истории Москвы" in content
    assert "**ID квиза:** `quiz-ru-moscow-2026`" in content

    assert "### Вопрос 1" in content
    assert "Когда был основан Московский Кремль?" in content
    assert "A. XII век" in content
    assert "B. XIV век" in content
    assert "C. XVI век" in content

    assert "### Вопрос 2" in content
    assert "Москва — столица России." in content
    assert "A. Верно" in content
    assert "B. Неверно" in content

    assert "### Вопрос 3" in content
    assert "Красная площадь расположена рядом с ___." in content
    assert "**Правильный ответ:** Кремлём" in content

    assert "### Вопрос 4" in content
    assert "Какой метрополитен открылся первым в СССР?" in content

    assert "### Вопрос 5" in content
    assert "| Левая колонка | Правая колонка |" in content
    assert "| Красная площадь | Тверской район |" in content

    assert "## Ответы" in content
    assert "**1.**" in content
    assert "**2.**" in content

    assert "XIV век" in content
    assert "Московский метрополитен" in content
    assert "Красная площадь → Тверской район" in content


def test_markdown_exporter_preserves_cyrillic_in_answer_key() -> None:
    """Verify answer section preserves Cyrillic text correctly."""

    exporter = QuizMarkdownExporter()
    quiz = build_quiz_with_all_types()

    result = exporter.export(quiz)
    content = result.content_bytes.decode("utf-8")

    lines = content.split("\n")
    answer_section_started = False
    answer_lines: list[str] = []

    for line in lines:
        if "## Ответы" in line:
            answer_section_started = True
            continue
        if answer_section_started and line.strip():
            answer_lines.append(line)

    assert any("Кремлём" in line for line in answer_lines)
    assert any("Московский метрополитен" in line for line in answer_lines)
    assert any("Красная площадь → Тверской район" in line for line in answer_lines)


def test_markdown_exporter_deterministic_output() -> None:
    """Same quiz produces identical output on repeated exports."""

    exporter = QuizMarkdownExporter()
    quiz = build_quiz_with_all_types()

    first = exporter.export(quiz)
    second = exporter.export(quiz)

    assert first.content_bytes == second.content_bytes
    assert first.filename == second.filename
    assert first.media_type == second.media_type


def test_markdown_exporter_escapes_special_characters() -> None:
    """Markdown special chars in question text are escaped."""

    quiz = Quiz(
        quiz_id="quiz-escapes",
        document_id="doc-1",
        title="Test *with* special_chars",
        version=1,
        last_edited_at="2026-05-03T19:30:00.000000Z",
        questions=(
            Question(
                question_id="q-1",
                prompt="What is 2 * 2? [hint: think!]",
                question_type="short_answer",
                correct_answer="4",
            ),
        ),
    )

    exporter = QuizMarkdownExporter()
    result = exporter.export(quiz)
    content = result.content_bytes.decode("utf-8")

    assert "\\*" in content or "2 \\* 2" in content
