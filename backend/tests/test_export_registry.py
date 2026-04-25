from __future__ import annotations

import pytest

from backend.app.api.errors import map_backend_error_to_status_code
from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import UnsupportedExportFormatError
from backend.app.domain.models import Explanation
from backend.app.domain.models import Option
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.export.json_exporter import QuizJsonExporter
from backend.app.export.registry import DEFAULT_QUIZ_EXPORT_REGISTRY
from backend.app.export.registry import QuizExportRegistry


def build_quiz() -> Quiz:
    return Quiz(
        quiz_id="quiz-ru-1",
        document_id="doc-ru-1",
        title="Тренировочный квиз по географии",
        version=3,
        last_edited_at="2026-04-22T12:00:00.000000Z",
        questions=(
            Question(
                question_id="question-1",
                prompt="Какой город является столицей России?",
                options=(
                    Option(option_id="option-1", text="Москва"),
                    Option(option_id="option-2", text="Казань"),
                ),
                correct_option_index=0,
                explanation=Explanation(text="Москва является столицей России."),
            ),
        ),
    )


def test_export_registry_resolves_json_exporter_and_preserves_cyrillic() -> None:
    registry = QuizExportRegistry({" JSON ": QuizJsonExporter()})

    exported_file = registry.export(build_quiz(), "json")

    assert registry.supported_formats() == ("json",)
    assert exported_file.filename == "quiz-ru-1.json"
    assert exported_file.media_type == "application/json; charset=utf-8"
    assert "Тренировочный квиз по географии" in exported_file.content_bytes.decode("utf-8")
    assert "Какой город является столицей России?" in exported_file.content_bytes.decode("utf-8")


def test_default_export_registry_exposes_json_exporter() -> None:
    exported_file = DEFAULT_QUIZ_EXPORT_REGISTRY.export(build_quiz(), "JSON")

    assert DEFAULT_QUIZ_EXPORT_REGISTRY.supported_formats() == ("json",)
    assert exported_file.filename == "quiz-ru-1.json"


def test_export_registry_rejects_unsupported_format_explicitly() -> None:
    registry = QuizExportRegistry({"json": QuizJsonExporter()})

    with pytest.raises(UnsupportedExportFormatError) as error_info:
        registry.get("docx")

    error = error_info.value
    assert error.code == "unsupported_export_format"
    assert error.export_format == "docx"
    assert error.supported_formats == ("json",)
    assert "supported formats: json" in error.message
    assert map_backend_error_to_status_code(error) == 400


def test_export_registry_rejects_invalid_registration() -> None:
    with pytest.raises(DomainValidationError, match="non-empty"):
        QuizExportRegistry({" ": QuizJsonExporter()})

    with pytest.raises(DomainValidationError, match="duplicate"):
        QuizExportRegistry(
            {
                "json": QuizJsonExporter(),
                " JSON ": QuizJsonExporter(),
            }
        )
