"""Pydantic v2 models for Quiz schema with discriminated union types.

This module provides strictly-typed question models that enforce correct
field combinations at parse time, replacing manual validation logic.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _to_camel_case(snake: str) -> str:
    """Convert snake_case to camelCase for JSON serialization."""
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class ExplanationPayload(BaseModel):
    """Explanation attached to a question answer."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel_case)

    text: str


class OptionPayload(BaseModel):
    """Single answer option for choice questions."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel_case)

    option_id: str
    text: str


class MatchingPairPayload(BaseModel):
    """Left-right pair for matching questions."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel_case)

    left: str
    right: str


class QuestionBase(BaseModel):
    """Common fields for all question types."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel_case, extra="forbid")

    question_id: str
    question_type: str
    prompt: str
    explanation: ExplanationPayload | None = None

    @field_validator("prompt")
    @classmethod
    def _strip_prompt(cls, v: str) -> str:
        return v.strip()


class SingleChoiceQuestion(QuestionBase):
    """Multiple choice question with single correct answer index."""

    model_config = ConfigDict(extra="forbid")

    question_type: Literal["single_choice"]
    options: list[OptionPayload] = Field(min_length=2)
    correct_option_index: int = Field(ge=0)
    correct_answer: None = None
    matching_pairs: list[MatchingPairPayload] = []

    @model_validator(mode="after")
    def _validate_index_in_range(self) -> SingleChoiceQuestion:
        if self.correct_option_index >= len(self.options):
            raise ValueError("correct_option_index out of range")
        return self

    @field_validator("options")
    @classmethod
    def _validate_unique_options(cls, opts: list[OptionPayload]) -> list[OptionPayload]:
        texts = [o.text.strip().casefold() for o in opts]
        if len(set(texts)) != len(texts):
            raise ValueError("duplicate option texts")
        return opts


class TrueFalseQuestion(QuestionBase):
    """Binary true/false (да/нет) question."""

    model_config = ConfigDict(extra="forbid")

    question_type: Literal["true_false"]
    options: list[OptionPayload] = Field(default_factory=lambda: [
        OptionPayload(option_id="true", text="Да"),
        OptionPayload(option_id="false", text="Нет"),
    ])
    correct_option_index: int = Field(ge=0, le=1)
    correct_answer: None = None
    matching_pairs: list[MatchingPairPayload] = []


class FillBlankQuestion(QuestionBase):
    """Fill-in-the-blank question with correct answer string."""

    model_config = ConfigDict(extra="forbid")

    question_type: Literal["fill_blank"]
    correct_answer: str = Field(min_length=1)
    options: list[OptionPayload] = []
    correct_option_index: None = None


class ShortAnswerQuestion(QuestionBase):
    """Open-ended short answer question."""

    model_config = ConfigDict(extra="forbid")

    question_type: Literal["short_answer"]
    correct_answer: str = Field(min_length=1)
    options: list[OptionPayload] = []
    correct_option_index: None = None


class MatchingQuestion(QuestionBase):
    """Matching pairs question requiring at least 4 pairs."""

    model_config = ConfigDict(extra="forbid")

    question_type: Literal["matching"]
    matching_pairs: list[MatchingPairPayload] = Field(min_length=4)
    options: list[OptionPayload] = []
    correct_option_index: None = None
    correct_answer: None = None

    @field_validator("matching_pairs")
    @classmethod
    def _validate_pairs(cls, pairs: list[MatchingPairPayload]) -> list[MatchingPairPayload]:
        for pair in pairs:
            if not pair.left.strip() or not pair.right.strip():
                raise ValueError("matching pair values must not be empty")
            # Reject symbolic right values (A/B/C/D or 1/2/3/4)
            if pair.right.strip().casefold() in {"a", "b", "c", "d", "1", "2", "3", "4"}:
                raise ValueError("matching pair right must contain full text, not an option id")
        return pairs


# Discriminated union for Question types
QuestionPayload = Annotated[
    SingleChoiceQuestion | TrueFalseQuestion | FillBlankQuestion | ShortAnswerQuestion | MatchingQuestion,
    Field(discriminator="question_type"),
]


class QuizPayload(BaseModel):
    """Top-level Quiz structure for generation output validation."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel_case, extra="forbid")

    quiz_id: str
    document_id: str
    title: str
    version: int = Field(ge=1)
    last_edited_at: str
    questions: list[QuestionPayload] = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def _title_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("quiz title must not be empty")
        return stripped

    @field_validator("questions")
    @classmethod
    def _prompts_not_empty(cls, qs: list[Any]) -> list[Any]:
        for q in qs:
            prompt = getattr(q, "prompt", "")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("question prompt must not be empty")
        return qs


def get_quiz_json_schema() -> dict[str, Any]:
    """Generate JSON Schema for Quiz validation.

    Returns a schema compatible with LLM structured generation.
    """
    return QuizPayload.model_json_schema()


def _explanation_to_domain(exp: ExplanationPayload | None) -> Any:
    """Convert ExplanationPayload to domain Explanation dataclass."""
    from backend.app.domain.models import Explanation

    return Explanation(text=exp.text) if exp else None


def _question_to_domain(q: QuestionPayload) -> Any:
    """Convert QuestionPayload union to domain Question dataclass."""
    from backend.app.domain.models import MatchingPair, Option, Question

    base_fields = {
        "question_id": q.question_id,
        "question_type": q.question_type,
        "prompt": q.prompt,
        "explanation": _explanation_to_domain(q.explanation),
    }

    if isinstance(q, (SingleChoiceQuestion, TrueFalseQuestion)):
        return Question(
            **base_fields,
            options=tuple(Option(option_id=o.option_id, text=o.text) for o in q.options),
            correct_option_index=q.correct_option_index,
            correct_answer=None,
            matching_pairs=(),
        )

    if isinstance(q, (FillBlankQuestion, ShortAnswerQuestion)):
        return Question(
            **base_fields,
            options=(),
            correct_option_index=None,
            correct_answer=q.correct_answer,
            matching_pairs=(),
        )

    if isinstance(q, MatchingQuestion):
        return Question(
            **base_fields,
            options=(),
            correct_option_index=None,
            correct_answer=None,
            matching_pairs=tuple(
                MatchingPair(left=p.left, right=p.right) for p in q.matching_pairs
            ),
        )

    raise ValueError(f"unknown question type: {type(q)}")


def quiz_payload_to_domain(payload: QuizPayload) -> Any:
    """Convert QuizPayload Pydantic model to domain Quiz dataclass.

    Maintains backward compatibility with existing domain models.
    """
    from backend.app.domain.models import Quiz

    return Quiz(
        quiz_id=payload.quiz_id,
        document_id=payload.document_id,
        title=payload.title,
        version=payload.version,
        last_edited_at=payload.last_edited_at,
        questions=tuple(_question_to_domain(q) for q in payload.questions),
    )
