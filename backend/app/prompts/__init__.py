"""Versioned prompt definitions for generation workflows."""

from backend.app.prompts.registry import DIRECT_GENERATION_PROMPT_KEY
from backend.app.prompts.registry import PromptDefinition
from backend.app.prompts.registry import PromptRegistry

__all__ = [
    "DIRECT_GENERATION_PROMPT_KEY",
    "PromptDefinition",
    "PromptRegistry",
]
