"""Versioned prompt definitions for generation workflows."""

from backend.app.prompts.registry import DIRECT_GENERATION_PROMPT_KEY
from backend.app.prompts.registry import PromptDefinition
from backend.app.prompts.registry import PromptRegistry
from backend.app.prompts.registry import REPAIR_GENERATION_PROMPT_KEY
from backend.app.prompts.registry import SINGLE_QUESTION_REGENERATION_PROMPT_KEY

__all__ = [
    "DIRECT_GENERATION_PROMPT_KEY",
    "PromptDefinition",
    "PromptRegistry",
    "REPAIR_GENERATION_PROMPT_KEY",
    "SINGLE_QUESTION_REGENERATION_PROMPT_KEY",
]
