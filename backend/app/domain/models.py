"""Core domain models for QuizCraft foundation and provider contracts."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from backend.app.core.modes import GenerationMode
from backend.app.core.modes import GenerationModeRegistry
from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import GenerationSettingsError


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
class MatchingPair:
    """One left-to-right pair for matching questions."""

    left: str
    right: str


@dataclass(frozen=True, slots=True)
class Question:
    """Quiz question with selectable options."""

    question_id: str
    prompt: str
    options: tuple[Option, ...] = ()
    correct_option_index: int | None = None
    explanation: Explanation | None = None
    question_type: str = "single_choice"
    correct_answer: str | None = None
    matching_pairs: tuple[MatchingPair, ...] = ()


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
                    "question_type": question.question_type,
                    "prompt": question.prompt,
                    "options": [
                        {"option_id": option.option_id, "text": option.text}
                        for option in question.options
                    ],
                    "correct_option_index": question.correct_option_index,
                    "correct_answer": question.correct_answer,
                    "matching_pairs": [
                        {"left": pair.left, "right": pair.right}
                        for pair in question.matching_pairs
                    ],
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
                    question_type=question_payload.get("question_type", "single_choice"),
                    prompt=question_payload["prompt"],
                    options=tuple(
                        Option(
                            option_id=option_payload["option_id"],
                            text=option_payload["text"],
                        )
                        for option_payload in question_payload["options"]
                    ),
                    correct_option_index=question_payload.get("correct_option_index"),
                    correct_answer=question_payload.get("correct_answer"),
                    matching_pairs=tuple(
                        MatchingPair(left=pair_payload["left"], right=pair_payload["right"])
                        for pair_payload in question_payload.get("matching_pairs", ())
                    ),
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
    model_name: str | None = None
    profile_name: str | None = None
    inference_parameters: dict[str, Any] = field(default_factory=dict)
    quiz_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Normalize multi-type request metadata while preserving legacy quiz_type."""

        normalized_types = tuple(
            item.strip()
            for item in (self.quiz_types or tuple(self.quiz_type.split(",")))
            if isinstance(item, str) and item.strip()
        )
        object.__setattr__(self, "quiz_types", normalized_types or (self.quiz_type,))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the generation request into a JSON-compatible dictionary."""

        payload = {
            "question_count": self.question_count,
            "language": self.language,
            "difficulty": self.difficulty,
            "quiz_type": self.quiz_type,
            "quiz_types": list(self.quiz_types),
            "generation_mode": self.generation_mode.value,
        }
        if self.model_name is not None:
            payload["model_name"] = self.model_name
        if self.profile_name is not None:
            payload["profile_name"] = self.profile_name
        if self.inference_parameters:
            payload["inference_parameters"] = dict(self.inference_parameters)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GenerationRequest":
        """Deserialize a generation request from a JSON-compatible dictionary."""

        return cls(
            question_count=payload["question_count"],
            language=payload["language"],
            difficulty=payload["difficulty"],
            quiz_type=payload["quiz_type"],
            generation_mode=GenerationModeRegistry.ensure_supported(payload["generation_mode"]),
            model_name=payload.get("model_name"),
            profile_name=payload.get("profile_name"),
            inference_parameters=dict(payload.get("inference_parameters", {})),
            quiz_types=tuple(payload.get("quiz_types", ())),
        )


@dataclass(frozen=True, slots=True)
class GenerationSettings:
    """Persisted generation defaults for the single-user local backend."""

    question_count: int
    language: str
    difficulty: str
    quiz_type: str
    generation_mode: GenerationMode
    model_name: str | None = None
    profile_name: str | None = None

    def __post_init__(self) -> None:
        """Validate persisted generation settings."""

        if not isinstance(self.question_count, int) or isinstance(self.question_count, bool):
            raise GenerationSettingsError("question_count must be a positive integer")
        if self.question_count <= 0:
            raise GenerationSettingsError("question_count must be a positive integer")
        for field_name in ("language", "difficulty", "quiz_type"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise GenerationSettingsError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
        generation_mode = GenerationModeRegistry.ensure_supported(self.generation_mode)
        object.__setattr__(self, "generation_mode", generation_mode)
        for field_name in ("model_name", "profile_name"):
            value = getattr(self, field_name)
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise GenerationSettingsError(f"{field_name} must be a non-empty string")
                object.__setattr__(self, field_name, value.strip())

    def to_dict(self) -> dict[str, Any]:
        """Serialize generation settings into a JSON-compatible dictionary."""

        payload: dict[str, Any] = {
            "question_count": self.question_count,
            "language": self.language,
            "difficulty": self.difficulty,
            "quiz_type": self.quiz_type,
            "generation_mode": self.generation_mode.value,
        }
        if self.model_name is not None:
            payload["model_name"] = self.model_name
        if self.profile_name is not None:
            payload["profile_name"] = self.profile_name
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GenerationSettings":
        """Deserialize generation settings from a JSON-compatible dictionary."""

        try:
            return cls(
                question_count=payload["question_count"],
                language=payload["language"],
                difficulty=payload["difficulty"],
                quiz_type=payload["quiz_type"],
                generation_mode=GenerationModeRegistry.ensure_supported(payload["generation_mode"]),
                model_name=payload.get("model_name"),
                profile_name=payload.get("profile_name"),
            )
        except KeyError as error:
            raise GenerationSettingsError(f"generation settings missing required field: {error.args[0]}") from error

    def merge(self, overrides: dict[str, Any]) -> "GenerationSettings":
        """Return settings with explicit request values applied."""

        payload = self.to_dict()
        for key, value in overrides.items():
            if value is not None:
                payload[key] = value.value if isinstance(value, GenerationMode) else value
        return GenerationSettings.from_dict(payload)

    def to_generation_request(
        self,
        *,
        model_name: str | None,
        profile_name: str | None,
        inference_parameters: dict[str, Any],
    ) -> GenerationRequest:
        """Convert persisted settings into a resolved generation request."""

        return GenerationRequest(
            question_count=self.question_count,
            language=self.language,
            difficulty=self.difficulty,
            quiz_type=self.quiz_type,
            generation_mode=self.generation_mode,
            model_name=model_name,
            profile_name=profile_name,
            inference_parameters=dict(inference_parameters),
            quiz_types=tuple(item.strip() for item in self.quiz_type.split(",") if item.strip()),
        )


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Successful generation result and its metadata."""

    quiz: Quiz
    request: GenerationRequest
    model_name: str
    prompt_version: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the generation result into a JSON-compatible dictionary."""

        return {
            "quiz": self.quiz.to_dict(),
            "request": self.request.to_dict(),
            "model_name": self.model_name,
            "prompt_version": self.prompt_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GenerationResult":
        """Deserialize a generation result from a JSON-compatible dictionary."""

        return cls(
            quiz=Quiz.from_dict(payload["quiz"]),
            request=GenerationRequest.from_dict(payload["request"]),
            model_name=payload["model_name"],
            prompt_version=payload["prompt_version"],
        )


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
    """Provider-facing embeddings request for one or more texts."""

    texts: tuple[str, ...]
    model_name: str | None = None

    def __post_init__(self) -> None:
        """Validate embeddings request payload."""

        if not isinstance(self.texts, tuple):
            raise DomainValidationError("texts must be a tuple of strings")
        if not self.texts:
            raise DomainValidationError("texts must contain at least one entry")
        for index, text in enumerate(self.texts):
            if not isinstance(text, str):
                raise DomainValidationError(f"texts[{index}] must be a string")
            if not text.strip():
                raise DomainValidationError(f"texts[{index}] must not be empty")
        if self.model_name is not None:
            if not isinstance(self.model_name, str) or not self.model_name.strip():
                raise DomainValidationError("model_name must be a non-empty string")
            object.__setattr__(self, "model_name", self.model_name.strip())


@dataclass(frozen=True, slots=True)
class EmbeddingResponse:
    """Provider-facing embeddings result with one vector per requested text."""

    model_name: str
    vectors: tuple[tuple[float, ...], ...]
