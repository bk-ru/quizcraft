"""Core domain models for QuizCraft foundation and provider contracts."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from backend.app.core.modes import GenerationMode


@dataclass(frozen=True, slots=True)
class Explanation:
    """Explanation attached to a generated question."""

    text: str


@dataclass(frozen=True, slots=True)
class Option:
    """Answer option for a quiz question."""

    option_id: str
    text: str


@dataclass(frozen=True, slots=True)
class Question:
    """Quiz question with selectable options."""

    question_id: str
    prompt: str
    options: tuple[Option, ...]
    correct_option_index: int
    explanation: Explanation | None = None


@dataclass(frozen=True, slots=True)
class Quiz:
    """Persisted quiz aggregate."""

    quiz_id: str
    document_id: str
    title: str
    version: int
    last_edited_at: str
    questions: tuple[Question, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the quiz into a JSON-compatible dictionary."""

        return {
            "quiz_id": self.quiz_id,
            "document_id": self.document_id,
            "title": self.title,
            "version": self.version,
            "last_edited_at": self.last_edited_at,
            "questions": [
                {
                    "question_id": question.question_id,
                    "prompt": question.prompt,
                    "options": [
                        {"option_id": option.option_id, "text": option.text}
                        for option in question.options
                    ],
                    "correct_option_index": question.correct_option_index,
                    "explanation": None
                    if question.explanation is None
                    else {"text": question.explanation.text},
                }
                for question in self.questions
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Quiz":
        """Deserialize a quiz from a JSON-compatible dictionary."""

        return cls(
            quiz_id=payload["quiz_id"],
            document_id=payload["document_id"],
            title=payload["title"],
            version=payload["version"],
            last_edited_at=payload["last_edited_at"],
            questions=tuple(
                Question(
                    question_id=question_payload["question_id"],
                    prompt=question_payload["prompt"],
                    options=tuple(
                        Option(
                            option_id=option_payload["option_id"],
                            text=option_payload["text"],
                        )
                        for option_payload in question_payload["options"]
                    ),
                    correct_option_index=question_payload["correct_option_index"],
                    explanation=None
                    if question_payload["explanation"] is None
                    else Explanation(text=question_payload["explanation"]["text"]),
                )
                for question_payload in payload["questions"]
            ),
        )


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Request metadata for quiz generation."""

    question_count: int
    language: str
    difficulty: str
    quiz_type: str
    generation_mode: GenerationMode


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Successful generation result and its metadata."""

    quiz: Quiz
    request: GenerationRequest
    model_name: str
    prompt_version: str


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """Stored document payload used by later generation stages."""

    document_id: str
    filename: str
    media_type: str
    file_size_bytes: int
    normalized_text: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the document into a JSON-compatible dictionary."""

        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "media_type": self.media_type,
            "file_size_bytes": self.file_size_bytes,
            "normalized_text": self.normalized_text,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DocumentRecord":
        """Deserialize a document record from a JSON-compatible dictionary."""

        return cls(
            document_id=payload["document_id"],
            filename=payload["filename"],
            media_type=payload["media_type"],
            file_size_bytes=payload["file_size_bytes"],
            normalized_text=payload["normalized_text"],
            metadata=dict(payload["metadata"]),
        )


@dataclass(frozen=True, slots=True)
class ProviderHealthStatus:
    """Provider availability status returned by later healthcheck operations."""

    status: str
    message: str


@dataclass(frozen=True, slots=True)
class StructuredGenerationRequest:
    """Provider-facing request for structured JSON generation."""

    system_prompt: str
    user_prompt: str
    schema_name: str
    schema: dict[str, Any]
    inference_parameters: dict[str, Any] = field(default_factory=dict)
    model_name: str | None = None


@dataclass(frozen=True, slots=True)
class StructuredGenerationResponse:
    """Provider-facing structured generation result."""

    model_name: str
    content: dict[str, Any]
    raw_response: dict[str, Any]


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    """Provider-facing embeddings request reserved for later stages."""

    texts: tuple[str, ...]
    model_name: str | None = None


@dataclass(frozen=True, slots=True)
class EmbeddingResponse:
    """Provider-facing embeddings result reserved for later stages."""

    model_name: str
    vectors: tuple[tuple[float, ...], ...]
