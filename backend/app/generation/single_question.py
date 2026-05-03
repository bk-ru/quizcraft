"""Targeted single-question regeneration orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from typing import Any
from typing import Callable

from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.domain.normalization import normalize_question_output
from backend.app.domain.validation import validate_quiz
from backend.app.generation.request_builder import SingleQuestionRegenerationRequestBuilder


@dataclass(frozen=True, slots=True)
class SingleQuestionRegenerationResult:
    """Successful targeted question regeneration result."""

    quiz: Quiz
    regenerated_question: Question
    model_name: str
    prompt_version: str


class SingleQuestionRegenerationOrchestrator:
    """Regenerate one question inside an existing persisted quiz."""

    def __init__(
        self,
        *,
        document_repository,
        quiz_repository,
        request_builder: SingleQuestionRegenerationRequestBuilder,
        provider,
        normalizer: Callable[[dict[str, Any]], Question] = normalize_question_output,
    ) -> None:
        self._document_repository = document_repository
        self._quiz_repository = quiz_repository
        self._request_builder = request_builder
        self._provider = provider
        self._normalizer = normalizer

    def regenerate(
        self,
        *,
        quiz_id: str,
        question_id: str,
        generation_request: GenerationRequest,
        instructions: str | None,
    ) -> SingleQuestionRegenerationResult:
        """Regenerate and persist exactly one question in a quiz."""

        quiz = self._quiz_repository.get(quiz_id)
        target_question = _get_quiz_question(quiz, question_id)
        document = self._document_repository.get(quiz.document_id)
        provider_request = self._request_builder.build(
            document=document,
            quiz=quiz,
            target_question=target_question,
            generation_request=generation_request,
            instructions=instructions,
        )
        response = self._provider.generate_structured(provider_request)
        normalized = self._normalizer(response.content)
        replacement_question = replace(
            normalized,
            question_id=target_question.question_id,
            correct_option_index=(
                normalized.correct_option_index
                if normalized.correct_option_index is not None
                else target_question.correct_option_index
            ),
        )
        updated_quiz = replace(
            quiz,
            questions=tuple(
                replacement_question if question.question_id == question_id else question
                for question in quiz.questions
            ),
        )
        validate_quiz(updated_quiz)
        persisted_quiz = self._quiz_repository.save(updated_quiz)
        persisted_question = _get_quiz_question(persisted_quiz, question_id)
        return SingleQuestionRegenerationResult(
            quiz=persisted_quiz,
            regenerated_question=persisted_question,
            model_name=response.model_name,
            prompt_version=self._request_builder.prompt_version(),
        )


def _get_quiz_question(quiz: Quiz, question_id: str) -> Question:
    """Return one question from a quiz or raise a controlled not-found error."""

    for question in quiz.questions:
        if question.question_id == question_id:
            return question
    raise RepositoryNotFoundError("question", question_id)
