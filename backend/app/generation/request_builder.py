"""Provider request builder for direct-generation flows."""

from __future__ import annotations

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import UnsupportedGenerationModeError
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.prompts.registry import DIRECT_GENERATION_PROMPT_KEY
from backend.app.prompts.registry import PromptRegistry


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
