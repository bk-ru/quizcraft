from __future__ import annotations

from backend.app.generation.status import GenerationPipelineEvent
from backend.app.generation.status import GenerationPipelineStep
from backend.app.generation.status import GenerationRunStatus


def test_generation_status_model_exposes_controlled_transitions_and_steps() -> None:
    assert [status.value for status in GenerationRunStatus] == [
        "queued",
        "running",
        "done",
        "failed",
    ]
    assert [step.value for step in GenerationPipelineStep] == [
        "parse",
        "generate",
        "repair",
        "persist",
    ]


def test_generation_pipeline_event_serializes_russian_safe_metadata() -> None:
    event = GenerationPipelineEvent(
        status=GenerationRunStatus.RUNNING,
        step=GenerationPipelineStep.GENERATE,
        document_id="doc-ru-1",
        quiz_id="quiz-ru-1",
        request_summary={"language": "ru", "difficulty": "medium"},
        metadata={"title": "Квиз по русскому документу"},
    )

    assert event.to_dict() == {
        "status": "running",
        "step": "generate",
        "document_id": "doc-ru-1",
        "quiz_id": "quiz-ru-1",
        "request_summary": {"language": "ru", "difficulty": "medium"},
        "metadata": {"title": "Квиз по русскому документу"},
    }
    assert event.to_log_extra() == {
        "generation_status": "running",
        "generation_step": "generate",
        "generation_document_id": "doc-ru-1",
        "generation_quiz_id": "quiz-ru-1",
        "generation_request_summary": {"language": "ru", "difficulty": "medium"},
        "generation_metadata": {"title": "Квиз по русскому документу"},
    }
