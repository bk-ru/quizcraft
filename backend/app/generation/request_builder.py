"""Provider request builder for direct-generation flows."""

from __future__ import annotations

import json

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import UnsupportedGenerationModeError
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.prompts.registry import DIRECT_GENERATION_PROMPT_KEY
from backend.app.prompts.registry import PromptRegistry
from backend.app.prompts.registry import SINGLE_QUESTION_REGENERATION_PROMPT_KEY


class DirectGenerationRequestBuilder:
    """Build provider-facing requests for direct quiz generation."""

    _prompt_keys_by_mode = {
        GenerationMode.DIRECT: DIRECT_GENERATION_PROMPT_KEY,
    }

    def __init__(self, prompt_registry: type[PromptRegistry]) -> None:
        self._prompt_registry = prompt_registry

    def resolve_prompt_key(self, generation_request: GenerationRequest) -> str:
        """Resolve the prompt key for a generation request mode."""

        try:
            return self._prompt_keys_by_mode[generation_request.generation_mode]
        except KeyError as error:
            raise UnsupportedGenerationModeError(
                f"unsupported generation mode: {generation_request.generation_mode}"
            ) from error

    def build(
        self,
        document: DocumentRecord,
        generation_request: GenerationRequest,
    ) -> StructuredGenerationRequest:
        """Build the provider-facing structured generation request."""

        prompt = self._prompt_registry.resolve(self.resolve_prompt_key(generation_request))
        inference_parameters = {
            **prompt.inference_parameters,
            **generation_request.inference_parameters,
        }
        return StructuredGenerationRequest(
            system_prompt=prompt.system_template,
            user_prompt=prompt.user_template.format(
                document_id=document.document_id,
                document_text=document.normalized_text,
                question_count=generation_request.question_count,
                language=generation_request.language,
                difficulty=generation_request.difficulty,
                quiz_type=generation_request.quiz_type,
            ),
            schema_name=prompt.schema_name,
            schema=prompt.schema,
            inference_parameters=inference_parameters,
            model_name=generation_request.model_name,
        )


class SingleQuestionRegenerationRequestBuilder:
    """Build provider-facing requests for targeted question regeneration."""

    def __init__(self, prompt_registry: type[PromptRegistry]) -> None:
        self._prompt_registry = prompt_registry

    def build(
        self,
        *,
        document: DocumentRecord,
        quiz: Quiz,
        target_question: Question,
        generation_request: GenerationRequest,
        instructions: str | None,
    ) -> StructuredGenerationRequest:
        """Build the provider-facing structured request for one question."""

        if generation_request.generation_mode is not GenerationMode.SINGLE_QUESTION_REGEN:
            raise UnsupportedGenerationModeError(
                f"unsupported generation mode: {generation_request.generation_mode}"
            )
        prompt = self._prompt_registry.resolve(SINGLE_QUESTION_REGENERATION_PROMPT_KEY)
        inference_parameters = {
            **prompt.inference_parameters,
            **generation_request.inference_parameters,
        }
        return StructuredGenerationRequest(
            system_prompt=prompt.system_template,
            user_prompt=prompt.user_template.format(
                document_id=document.document_id,
                document_text=document.normalized_text,
                quiz_json=json.dumps(quiz.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
                target_question_json=json.dumps(
                    _serialize_question(target_question),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                language=generation_request.language,
                difficulty=generation_request.difficulty,
                quiz_type=generation_request.quiz_type,
                instructions="нет" if instructions is None else instructions,
            ),
            schema_name=prompt.schema_name,
            schema=prompt.schema,
            inference_parameters=inference_parameters,
            model_name=generation_request.model_name,
        )

    def prompt_version(self) -> str:
        """Return the targeted-regeneration prompt version."""

        return self._prompt_registry.resolve(SINGLE_QUESTION_REGENERATION_PROMPT_KEY).version


def _serialize_question(question: Question) -> dict[str, object]:
    """Serialize one quiz question for prompt context."""

    return {
        "question_id": question.question_id,
        "prompt": question.prompt,
        "options": [
            {
                "option_id": option.option_id,
                "text": option.text,
            }
            for option in question.options
        ],
        "correct_option_index": question.correct_option_index,
        "explanation": None if question.explanation is None else {"text": question.explanation.text},
    }
