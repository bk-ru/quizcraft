"""Pydantic request and response schemas for the HTTP API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from backend.app.core.modes import GenerationMode
from backend.app.domain.enums import Difficulty
from backend.app.domain.enums import Language
from backend.app.domain.enums import QuizType
from backend.app.domain.models import Explanation
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import Option
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz


class _StrictModel(BaseModel):
    """Base model rejecting extra fields and stripping string whitespace."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GenerationRequestBody(_StrictModel):
    """Request body for direct quiz generation."""

    question_count: int = Field(gt=0, description="Number of quiz questions to generate")
    language: Language
    difficulty: Difficulty
    quiz_type: QuizType
    generation_mode: GenerationMode

    def to_domain(self) -> GenerationRequest:
        """Convert the validated body into a domain generation request."""

        return GenerationRequest(
            question_count=self.question_count,
            language=self.language.value,
            difficulty=self.difficulty.value,
            quiz_type=self.quiz_type.value,
            generation_mode=self.generation_mode,
        )


class ExplanationPayload(_StrictModel):
    """Quiz question explanation payload."""

    text: str = Field(min_length=1)

    def to_domain(self) -> Explanation:
        return Explanation(text=self.text)


class OptionPayload(_StrictModel):
    """Quiz answer option payload."""

    option_id: str = Field(min_length=1)
    text: str = Field(min_length=1)

    def to_domain(self) -> Option:
        return Option(option_id=self.option_id, text=self.text)


class QuestionPayload(_StrictModel):
    """Quiz question payload."""

    question_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    options: list[OptionPayload] = Field(min_length=2)
    correct_option_index: int = Field(ge=0)
    explanation: ExplanationPayload | None = None

    def to_domain(self) -> Question:
        return Question(
            question_id=self.question_id,
            prompt=self.prompt,
            options=tuple(option.to_domain() for option in self.options),
            correct_option_index=self.correct_option_index,
            explanation=None if self.explanation is None else self.explanation.to_domain(),
        )


class QuizPayload(_StrictModel):
    """Full quiz payload used in update requests."""

    quiz_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    version: int = Field(ge=0)
    last_edited_at: str = ""
    questions: list[QuestionPayload] = Field(min_length=1)

    def to_domain(self) -> Quiz:
        return Quiz(
            quiz_id=self.quiz_id,
            document_id=self.document_id,
            title=self.title,
            version=self.version,
            last_edited_at=self.last_edited_at,
            questions=tuple(question.to_domain() for question in self.questions),
        )


class QuizUpdateBody(_StrictModel):
    """Request body for quiz update."""

    quiz: QuizPayload


def build_validation_error_message(errors: list[dict[str, Any]]) -> str:
    """Render Pydantic validation errors into a single human-readable message."""

    fragments: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.get("loc", ()) if part != "body")
        message = error.get("msg", "invalid value")
        fragments.append(f"{location}: {message}" if location else message)
    return "; ".join(fragments) if fragments else "request payload is invalid"
