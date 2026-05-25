"""Pydantic-схемы запросов и ответов для HTTP API."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from backend.app.core.modes import GenerationMode
from backend.app.domain.enums import Difficulty
from backend.app.domain.enums import Language
from backend.app.domain.enums import QuizType
from backend.app.domain.models import Explanation
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import GenerationSettings
from backend.app.domain.models import MatchingPair
from backend.app.domain.models import Option
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz


class _StrictModel(BaseModel):
    """Базовая модель, отклоняющая лишние поля и удаляющая пробелы по краям строк."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GenerationRequestBody(_StrictModel):
    """Тело запроса для прямой генерации квиза."""

    question_count: int | None = Field(
        default=None,
        strict=True,
        gt=0,
        description="Number of quiz questions to generate",
    )
    language: Language | None = None
    difficulty: Difficulty | None = None
    quiz_type: QuizType | None = None
    quiz_types: list[QuizType] | None = Field(default=None, min_length=1)
    generation_mode: GenerationMode | None = None
    model_name: str | None = Field(default=None, min_length=1)
    profile_name: str | None = Field(default=None, min_length=1)
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)

    def to_settings(self, defaults: GenerationSettings | None = None) -> GenerationSettings:
        """Преобразовать частичное тело запроса в полные настройки генерации."""

        overrides = self.to_settings_overrides()
        if defaults is not None:
            return defaults.merge(overrides)
        return GenerationSettings.from_dict(overrides)

    def to_settings_overrides(self) -> dict[str, Any]:
        """Вернуть только явно переданные значения настроек."""

        values = {
            "question_count": self.question_count,
            "language": None if self.language is None else self.language.value,
            "difficulty": None if self.difficulty is None else self.difficulty.value,
            "quiz_type": self._resolved_quiz_type(),
            "generation_mode": None if self.generation_mode is None else self.generation_mode.value,
            "model_name": self.model_name,
            "profile_name": self.profile_name,
        }
        return {key: value for key, value in values.items() if value is not None}

    def _resolved_quiz_type(self) -> str | None:
        """Вернуть legacy-строку quiz_type, полученную из явных значений."""

        if self.quiz_types:
            return ",".join(item.value for item in self.quiz_types)
        if self.quiz_type is not None:
            return self.quiz_type.value
        return None

    def inference_parameter_overrides(self) -> dict[str, Any]:
        """Return request-time model parameters passed directly in the request."""

        if self.temperature is None:
            return {}
        return {"temperature": self.temperature}

    def to_domain(
        self,
        *,
        model_name: str | None = None,
        profile_name: str | None = None,
        inference_parameters: dict[str, Any] | None = None,
    ) -> GenerationRequest:
        """Преобразовать валидированное тело в доменный запрос генерации."""

        settings = self.to_settings()
        resolved_inference_parameters = {} if inference_parameters is None else dict(inference_parameters)
        if self.temperature is not None:
            resolved_inference_parameters["temperature"] = self.temperature
        return settings.to_generation_request(
            model_name=model_name,
            profile_name=profile_name,
            inference_parameters=resolved_inference_parameters,
        )


class GenerationSettingsBody(_StrictModel):
    """Тело запроса для сохраняемых настроек генерации."""

    question_count: int = Field(strict=True, gt=0)
    language: Language
    difficulty: Difficulty
    quiz_type: QuizType
    quiz_types: list[QuizType] | None = Field(default=None, min_length=1)
    generation_mode: GenerationMode
    model_name: str | None = Field(default=None, min_length=1)
    profile_name: str | None = Field(default=None, min_length=1)

    def to_settings(self) -> GenerationSettings:
        """Преобразовать валидированный payload в сохраняемые настройки генерации."""

        return GenerationSettings(
            question_count=self.question_count,
            language=self.language.value,
            difficulty=self.difficulty.value,
            quiz_type=",".join(item.value for item in self.quiz_types) if self.quiz_types else self.quiz_type.value,
            generation_mode=self.generation_mode,
            model_name=self.model_name,
            profile_name=self.profile_name,
        )


class LMStudioConnectionBody(_StrictModel):
    """Runtime-настройка сетевого адреса LM Studio."""

    host: str = Field(min_length=1, max_length=253)
    port: int = Field(strict=True, ge=1, le=65535)

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        host = value.strip()
        if "://" in host or any(separator in host for separator in ("/", "\\", "?", "#", "@", ":")):
            raise ValueError("host must be a bare IP address or DNS name without scheme, path, or port")
        if not re.fullmatch(r"[A-Za-z0-9.-]+", host):
            raise ValueError("host must contain only letters, digits, dots, and hyphens")
        if host.startswith((".", "-")) or host.endswith((".", "-")) or ".." in host:
            raise ValueError("host must be a valid IP address or DNS name")
        return host

    def to_base_url(self) -> str:
        return f"http://{self.host}:{self.port}/v1"


class ExplanationPayload(_StrictModel):
    """Payload пояснения к вопросу квиза."""

    text: str = Field(min_length=1)

    def to_domain(self) -> Explanation:
        return Explanation(text=self.text)


class OptionPayload(_StrictModel):
    """Payload варианта ответа квиза."""

    option_id: str = Field(min_length=1)
    text: str = Field(min_length=1)

    def to_domain(self) -> Option:
        return Option(option_id=self.option_id, text=self.text)


class MatchingPairPayload(_StrictModel):
    """Payload пары для сопоставления."""

    left: str = Field(min_length=1)
    right: str = Field(min_length=1)

    def to_domain(self) -> MatchingPair:
        return MatchingPair(left=self.left, right=self.right)


class QuestionPayload(_StrictModel):
    """Payload вопроса квиза."""

    question_id: str = Field(min_length=1)
    question_type: QuizType = QuizType.SINGLE_CHOICE
    prompt: str = Field(min_length=1)
    options: list[OptionPayload] = Field(default_factory=list)
    correct_option_index: int | None = Field(default=None, strict=True, ge=0)
    correct_answer: str | None = Field(default=None, min_length=1)
    matching_pairs: list[MatchingPairPayload] = Field(default_factory=list)
    explanation: ExplanationPayload | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "QuestionPayload":
        """Проверить поля, обязательные для каждого типа вопроса."""

        if self.question_type in (QuizType.SINGLE_CHOICE, QuizType.TRUE_FALSE):
            if len(self.options) < 2:
                raise ValueError("choice questions must contain at least two options")
            if self.correct_option_index is None:
                raise ValueError("choice questions must include correct_option_index")
        if self.question_type in (QuizType.FILL_BLANK, QuizType.SHORT_ANSWER) and not self.correct_answer:
            raise ValueError("answer questions must include correct_answer")
        if self.question_type is QuizType.MATCHING and not self.matching_pairs:
            raise ValueError("matching questions must include matching_pairs")
        return self

    def to_domain(self) -> Question:
        return Question(
            question_id=self.question_id,
            question_type=self.question_type.value,
            prompt=self.prompt,
            options=tuple(option.to_domain() for option in self.options),
            correct_option_index=self.correct_option_index,
            correct_answer=self.correct_answer,
            matching_pairs=tuple(pair.to_domain() for pair in self.matching_pairs),
            explanation=None if self.explanation is None else self.explanation.to_domain(),
        )


class QuizPayload(_StrictModel):
    """Полный payload квиза, используемый в запросах обновления."""

    quiz_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    version: int = Field(strict=True, ge=0)
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
    """Тело запроса для обновления квиза."""

    quiz: QuizPayload


class SingleQuestionRegenerationBody(_StrictModel):
    """Тело запроса для API-контракта регенерации одного вопроса."""

    quiz_id: str | None = Field(default=None, strict=True, min_length=1)
    question_id: str | None = Field(default=None, strict=True, min_length=1)
    instructions: str | None = Field(default=None, strict=True, min_length=1, max_length=2000)
    language: Language | None = None
    difficulty: Difficulty | None = None
    quiz_type: QuizType | None = None
    model_name: str | None = Field(default=None, strict=True, min_length=1)
    profile_name: str | None = Field(default=None, strict=True, min_length=1)

    def to_contract_dict(self) -> dict[str, str]:
        """Вернуть явно переданные поля контракта для ответа."""

        values = {
            "quiz_id": self.quiz_id,
            "question_id": self.question_id,
            "instructions": self.instructions,
            "language": None if self.language is None else self.language.value,
            "difficulty": None if self.difficulty is None else self.difficulty.value,
            "quiz_type": None if self.quiz_type is None else self.quiz_type.value,
            "model_name": self.model_name,
            "profile_name": self.profile_name,
        }
        return {key: value for key, value in values.items() if value is not None}

    def to_generation_settings(self, defaults: GenerationSettings | None = None) -> GenerationSettings:
        """Определить настройки регенерации из значений запроса и сохраненных значений по умолчанию."""

        values = _default_single_question_generation_settings()
        if defaults is not None:
            values.update(defaults.to_dict())
        values.update(self.to_contract_dict())
        values["question_count"] = 1
        values["generation_mode"] = GenerationMode.SINGLE_QUESTION_REGEN.value
        values.pop("quiz_id", None)
        values.pop("question_id", None)
        values.pop("instructions", None)
        return GenerationSettings.from_dict(values)


def _default_single_question_generation_settings() -> dict[str, Any]:
    """Вернуть русскоязычные значения по умолчанию для автономной точечной регенерации."""

    return {
        "question_count": 1,
        "language": Language.RU.value,
        "difficulty": Difficulty.MEDIUM.value,
        "quiz_type": QuizType.SINGLE_CHOICE.value,
        "generation_mode": GenerationMode.SINGLE_QUESTION_REGEN.value,
    }


def build_validation_error_message(errors: list[dict[str, Any]]) -> str:
    """Преобразовать ошибки валидации Pydantic в одно человекочитаемое сообщение."""

    fragments: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.get("loc", ()) if part != "body")
        message = error.get("msg", "invalid value")
        fragments.append(f"{location}: {message}" if location else message)
    return "; ".join(fragments) if fragments else "request payload is invalid"
