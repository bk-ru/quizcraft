"""Generation pipeline status models."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any


class GenerationRunStatus(str, Enum):
    """Controlled generation status transitions."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class GenerationPipelineStep(str, Enum):
    """Controlled generation pipeline steps."""

    PARSE = "parse"
    GENERATE = "generate"
    REPAIR = "repair"
    PERSIST = "persist"


@dataclass(frozen=True, slots=True)
class GenerationPipelineEvent:
    """Structured status event emitted by the generation pipeline."""

    status: GenerationRunStatus
    step: GenerationPipelineStep
    document_id: str
    quiz_id: str | None = None
    request_summary: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event into a JSON-compatible dictionary."""

        payload: dict[str, Any] = {
            "status": self.status.value,
            "step": self.step.value,
            "document_id": self.document_id,
        }
        if self.quiz_id is not None:
            payload["quiz_id"] = self.quiz_id
        if self.request_summary:
            payload["request_summary"] = self.request_summary
        if self.metadata:
            payload["metadata"] = self.metadata
        if self.error_code is not None:
            payload["error_code"] = self.error_code
        if self.error_message is not None:
            payload["error_message"] = self.error_message
        return payload

    def to_log_extra(self) -> dict[str, Any]:
        """Serialize the event into LogRecord extra fields."""

        payload: dict[str, Any] = {
            "generation_status": self.status.value,
            "generation_step": self.step.value,
            "generation_document_id": self.document_id,
        }
        if self.quiz_id is not None:
            payload["generation_quiz_id"] = self.quiz_id
        if self.request_summary:
            payload["generation_request_summary"] = self.request_summary
        if self.metadata:
            payload["generation_metadata"] = self.metadata
        if self.error_code is not None:
            payload["generation_error_code"] = self.error_code
        if self.error_message is not None:
            payload["generation_error_message"] = self.error_message
        return payload
