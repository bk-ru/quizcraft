from __future__ import annotations

import csv
import io

from backend.app.domain.models import Explanation
from backend.app.domain.models import MatchingPair
from backend.app.domain.models import Option
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.export.csv_exporter import QuizCsvExporter


def build_quiz_with_cyrillic() -> Quiz:
    """Build a quiz with Cyrillic text covering all CSV-supported question types."""

    return Quiz(
        quiz_id="quiz-ru-csv-2026",
        document_id="doc-ru-cyrillic",
        title="География России",
        version=2,
        last_edited_at="2026-05-03T19:45:00.000000Z",
        questions=(
            Question(
                question_id="q-1",
                prompt="Какой город является столицей России?",
                question_type="single_choice",
                options=(
                    Option(option_id="a", text="Москва"),
                    Option(option_id="b", text="Санкт-Петербург"),
                    Option(option_id="c", text="Казань"),
                    Option(option_id="d", text="Новосибирск"),
                ),
                correct_option_index=0,
                explanation=Explanation(text="Москва — официальная столица России с XV века."),
            ),
            Question(
                question_id="q-2",
                prompt="Волга впадает в Каспийское море.",
                question_type="true_false",
                correct_option_index=0,
                explanation=Explanation(text="Дельта Волги расположена в Каспийском море."),
            ),
            Question(
                question_id="q-3",
                prompt="Назовите самое большое озеро в России:",
                question_type="short_answer",
                correct_answer="Байкал",
            ),
            Question(
                question_id="q-4",
                prompt="Река Обь протекает в ___ части страны.",
                question_type="fill_blank",
                correct_answer="западной",
            ),
            Question(
                question_id="q-5",
                prompt="Сопоставьте города с реками:",
                question_type="matching",
                matching_pairs=(
                    MatchingPair(left="Москва", right="Москва-река"),
                    MatchingPair(left="СПб", right="Нева"),
                ),
            ),
        ),
    )


def test_csv_exporter_builds_google_forms_compatible_file() -> None:
    """Export quiz to CSV and verify Google Forms column structure."""

    exporter = QuizCsvExporter()
    quiz = build_quiz_with_cyrillic()

    result = exporter.export(quiz)

    assert result.filename == "quiz-ru-csv-2026.csv"
    assert result.media_type == "text/csv; charset=utf-8"

    content = result.content_bytes.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    assert len(rows) >= 4

    header = rows[0]
    assert header[0] == "Question"
    assert header[1] == "Question Type"
    assert "Option 1" in header
    assert "Option 10" in header
    assert "Correct Answer" in header
    assert "Points" in header
    assert "Feedback" in header


def test_csv_exporter_preserves_cyrillic_text() -> None:
    """Verify Cyrillic characters are preserved in UTF-8 CSV output."""

    exporter = QuizCsvExporter()
    quiz = build_quiz_with_cyrillic()

    result = exporter.export(quiz)
    content = result.content_bytes.decode("utf-8")

    assert "Москва" in content
    assert "Санкт-Петербург" in content
    assert "Казань" in content
    assert "Байкал" in content
    assert "западной" in content


def test_csv_exporter_single_choice_format() -> None:
    """Verify single_choice question maps to Google Forms Multiple choice."""

    exporter = QuizCsvExporter()
    quiz = build_quiz_with_cyrillic()

    result = exporter.export(quiz)
    content = result.content_bytes.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    data_rows = rows[1:]
    single_choice_row = next(r for r in data_rows if "столицей России" in r[0])

    assert single_choice_row[1] == "Multiple choice"
    assert single_choice_row[2] == "Москва"
    assert single_choice_row[3] == "Санкт-Петербург"
    assert single_choice_row[4] == "Казань"
    assert single_choice_row[5] == "Новосибирск"
    assert single_choice_row[12] == "Москва"


def test_csv_exporter_true_false_format() -> None:
    """Verify true_false question maps to Multiple choice with Верно/Неверно."""

    exporter = QuizCsvExporter()
    quiz = build_quiz_with_cyrillic()

    result = exporter.export(quiz)
    content = result.content_bytes.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    data_rows = rows[1:]
    tf_row = next(r for r in data_rows if "Волга впадает" in r[0])

    assert tf_row[1] == "Multiple choice"
    assert tf_row[2] == "Верно"
    assert tf_row[3] == "Неверно"
    assert tf_row[12] == "Верно"


def test_csv_exporter_short_answer_format() -> None:
    """Verify short_answer question maps to Google Forms Short answer."""

    exporter = QuizCsvExporter()
    quiz = build_quiz_with_cyrillic()

    result = exporter.export(quiz)
    content = result.content_bytes.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    data_rows = rows[1:]
    sa_row = next(r for r in data_rows if "самое большое озеро" in r[0])

    assert sa_row[1] == "Short answer"
    assert sa_row[12] == "Байкал"


def test_csv_exporter_fill_blank_format() -> None:
    """Verify fill_blank question maps to Google Forms Short answer."""

    exporter = QuizCsvExporter()
    quiz = build_quiz_with_cyrillic()

    result = exporter.export(quiz)
    content = result.content_bytes.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    data_rows = rows[1:]
    fb_row = next(r for r in data_rows if "Река Обь" in r[0])

    assert fb_row[1] == "Short answer"
    assert fb_row[12] == "западной"


def test_csv_exporter_skips_matching_questions() -> None:
    """Verify matching questions are skipped (not included in output)."""

    exporter = QuizCsvExporter()
    quiz = build_quiz_with_cyrillic()

    result = exporter.export(quiz)
    content = result.content_bytes.decode("utf-8")

    assert "Сопоставьте города" not in content
    assert "Москва-река" not in content


def test_csv_exporter_includes_explanation_as_feedback() -> None:
    """Verify explanations are included in Feedback column."""

    exporter = QuizCsvExporter()
    quiz = build_quiz_with_cyrillic()

    result = exporter.export(quiz)
    content = result.content_bytes.decode("utf-8")

    assert "Москва — официальная столица" in content
    assert "Дельта Волги" in content


def test_csv_exporter_deterministic_output() -> None:
    """Same quiz produces identical output on repeated exports."""

    exporter = QuizCsvExporter()
    quiz = build_quiz_with_cyrillic()

    first = exporter.export(quiz)
    second = exporter.export(quiz)

    assert first.content_bytes == second.content_bytes
    assert first.filename == second.filename


def test_csv_exporter_handles_more_than_ten_options() -> None:
    """Questions with >10 options are truncated to fit CSV format."""

    many_options = tuple(
        Option(option_id=f"opt-{i}", text=f"Вариант {i}")
        for i in range(1, 15)
    )

    quiz = Quiz(
        quiz_id="quiz-many",
        document_id="doc-1",
        title="Test",
        version=1,
        last_edited_at="2026-05-03T19:45:00.000000Z",
        questions=(
            Question(
                question_id="q-1",
                prompt="Выберите один:",
                question_type="single_choice",
                options=many_options,
                correct_option_index=0,
            ),
        ),
    )

    exporter = QuizCsvExporter()
    result = exporter.export(quiz)
    content = result.content_bytes.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    data_row = rows[1]
    option_cols = data_row[2:12]

    assert all(opt != "" for opt in option_cols)
    assert "Вариант 10" in option_cols[-1]
    assert "Вариант 11" not in data_row
