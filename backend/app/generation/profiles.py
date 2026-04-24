"""Generation profile and model selection resolution."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any
from typing import Mapping

from backend.app.core.config import AppConfig
from backend.app.domain.errors import GenerationProfileError
from backend.app.domain.errors import ModelSelectionError


@dataclass(frozen=True, slots=True)
class ResolvedGenerationProfile:
    """Resolved request-time generation profile values."""

    profile_name: str
    model_name: str | None
    inference_parameters: Mapping[str, Any]


class GenerationProfileResolver:
    """Resolve generation profile and model selections against runtime configuration."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def resolve(
        self,
        *,
        model_name: str | None,
        profile_name: str | None,
    ) -> ResolvedGenerationProfile:
        """Resolve and validate a request-time model/profile selection."""

        resolved_profile_name = profile_name or self._config.default_generation_profile
        profile = self._config.generation_profiles.get(resolved_profile_name)
        if profile is None:
            raise GenerationProfileError(f"unknown generation profile: {resolved_profile_name}")

        selected_model = model_name or profile.model_name
        if selected_model is not None and selected_model not in self._config.allowed_models:
            raise ModelSelectionError(f"model '{selected_model}' is not allowed")

        return ResolvedGenerationProfile(
            profile_name=resolved_profile_name,
            model_name=selected_model,
            inference_parameters=MappingProxyType(dict(profile.inference_parameters)),
        )
