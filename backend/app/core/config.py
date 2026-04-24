"""Runtime configuration for the QuizCraft backend."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from types import MappingProxyType
from typing import Any
from typing import Mapping

from backend.app.domain.errors import ConfigurationError

logger = logging.getLogger(__name__)

DEFAULT_GENERATION_PROFILE_NAME = "balanced"


def load_env_file(path: str | os.PathLike[str], override: bool = False) -> dict[str, str]:
    """Load KEY=VALUE pairs from a dotenv-style file into the process environment.

    Lines beginning with ``#`` and blank lines are ignored. Values may be optionally
    wrapped in single or double quotes. Existing environment variables are preserved
    by default so that real shell values override the file.
    """

    env_path = Path(path)
    if not env_path.is_file():
        return {}

    loaded: dict[str, str] = {}
    for line_number, raw_line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            logger.warning("Ignoring malformed line %s in %s", line_number, env_path)
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if override or key not in os.environ:
            os.environ[key] = value
        loaded[key] = value
    return loaded


@dataclass(frozen=True, slots=True)
class GenerationProfile:
    """Named generation profile with provider-facing parameters."""

    name: str
    model_name: str | None = None
    inference_parameters: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))


def _default_generation_profiles() -> Mapping[str, GenerationProfile]:
    """Return the built-in generation profile registry."""

    return MappingProxyType(
        {
            "fast": GenerationProfile(
                name="fast",
                inference_parameters=MappingProxyType({"temperature": 0.1}),
            ),
            "balanced": GenerationProfile(
                name="balanced",
                inference_parameters=MappingProxyType({}),
            ),
            "strict": GenerationProfile(
                name="strict",
                inference_parameters=MappingProxyType({"temperature": 0.0}),
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Validated backend configuration loaded from environment variables."""

    lm_studio_base_url: str
    lm_studio_model: str
    request_timeout: int = 30
    max_file_size_mb: int = 10
    max_document_chars: int = 50_000
    log_level: str = "INFO"
    log_format: str = "%(asctime)s %(levelname)s %(name)s %(message)s"
    allowed_models: tuple[str, ...] = ()
    generation_profiles: Mapping[str, GenerationProfile] = field(default_factory=_default_generation_profiles)
    default_generation_profile: str = DEFAULT_GENERATION_PROFILE_NAME

    def __post_init__(self) -> None:
        """Normalize and validate derived configuration fields."""

        allowed_models = self.allowed_models or (self.lm_studio_model,)
        normalized_allowed_models = tuple(model.strip() for model in allowed_models if model.strip())
        if not normalized_allowed_models:
            raise ConfigurationError("LM_STUDIO_ALLOWED_MODELS must include at least one model")
        if self.lm_studio_model not in normalized_allowed_models:
            raise ConfigurationError("LM_STUDIO_MODEL must be listed in LM_STUDIO_ALLOWED_MODELS")

        normalized_profiles = self._normalize_generation_profiles(self.generation_profiles)
        if self.default_generation_profile not in normalized_profiles:
            raise ConfigurationError("DEFAULT_GENERATION_PROFILE must reference a configured profile")

        for profile in normalized_profiles.values():
            if profile.model_name is not None and profile.model_name not in normalized_allowed_models:
                raise ConfigurationError("generation profile model_name must be listed in LM_STUDIO_ALLOWED_MODELS")

        object.__setattr__(self, "allowed_models", normalized_allowed_models)
        object.__setattr__(self, "generation_profiles", MappingProxyType(dict(normalized_profiles)))

    @staticmethod
    def _load_int(env_name: str, default: str) -> int:
        """Load an integer setting from the environment."""

        try:
            return int(os.getenv(env_name, default))
        except ValueError as error:
            raise ConfigurationError(f"{env_name} must be a valid integer") from error

    @staticmethod
    def _load_allowed_models(default_model: str) -> tuple[str, ...]:
        """Load allowed model names from a comma-separated environment variable."""

        raw_value = os.getenv("LM_STUDIO_ALLOWED_MODELS")
        if raw_value is None:
            return (default_model,)

        models = tuple(part.strip() for part in raw_value.split(",") if part.strip())
        if not models:
            raise ConfigurationError("LM_STUDIO_ALLOWED_MODELS must include at least one model")
        return models

    @staticmethod
    def _load_generation_profiles() -> Mapping[str, GenerationProfile]:
        """Load generation profile definitions from JSON configuration."""

        raw_value = os.getenv("GENERATION_PROFILES")
        if raw_value is None:
            return _default_generation_profiles()

        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError as error:
            raise ConfigurationError("GENERATION_PROFILES must be valid JSON") from error

        if not isinstance(payload, dict):
            raise ConfigurationError("GENERATION_PROFILES must be a JSON object")

        profiles: dict[str, GenerationProfile] = {}
        for raw_name, raw_profile in payload.items():
            if not isinstance(raw_name, str) or not raw_name.strip():
                raise ConfigurationError("generation profile names must be non-empty strings")
            if not isinstance(raw_profile, dict):
                raise ConfigurationError("generation profile definitions must be JSON objects")

            profile_name = raw_name.strip()
            model_name = raw_profile.get("model_name")
            if model_name is not None:
                if not isinstance(model_name, str) or not model_name.strip():
                    raise ConfigurationError("generation profile model_name must be a non-empty string")
                model_name = model_name.strip()

            inference_parameters = raw_profile.get("inference_parameters", {})
            if not isinstance(inference_parameters, dict):
                raise ConfigurationError("generation profile inference_parameters must be a JSON object")

            profiles[profile_name] = GenerationProfile(
                name=profile_name,
                model_name=model_name,
                inference_parameters=MappingProxyType(dict(inference_parameters)),
            )

        if not profiles:
            raise ConfigurationError("GENERATION_PROFILES must include at least one profile")
        return MappingProxyType(profiles)

    @staticmethod
    def _normalize_generation_profiles(
        profiles: Mapping[str, GenerationProfile],
    ) -> dict[str, GenerationProfile]:
        """Normalize profile names and parameter mappings."""

        normalized: dict[str, GenerationProfile] = {}
        for raw_name, profile in profiles.items():
            if not isinstance(profile, GenerationProfile):
                raise ConfigurationError("generation_profiles must contain GenerationProfile values")
            profile_name = raw_name.strip()
            if not profile_name:
                raise ConfigurationError("generation profile names must be non-empty strings")
            if profile.name != profile_name:
                raise ConfigurationError("generation profile mapping keys must match profile names")
            normalized[profile_name] = GenerationProfile(
                name=profile_name,
                model_name=profile.model_name,
                inference_parameters=MappingProxyType(dict(profile.inference_parameters)),
            )
        if not normalized:
            raise ConfigurationError("generation_profiles must include at least one profile")
        return normalized

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Build configuration from process environment variables.

        When ``QUIZCRAFT_ENV_FILE`` points at a readable file its contents are
        loaded into the process environment before variables are read. Otherwise
        a ``.env`` file in the current working directory is used when present.
        Real shell variables always win over file-provided values.
        """

        env_file_path = os.getenv("QUIZCRAFT_ENV_FILE") or ".env"
        load_env_file(env_file_path)

        lm_studio_base_url = os.getenv("LM_STUDIO_BASE_URL")
        if not lm_studio_base_url:
            raise ConfigurationError("LM_STUDIO_BASE_URL is required")

        lm_studio_model = os.getenv("LM_STUDIO_MODEL")
        if not lm_studio_model:
            raise ConfigurationError("LM_STUDIO_MODEL is required")

        request_timeout = cls._load_int("REQUEST_TIMEOUT", "30")
        max_file_size_mb = cls._load_int("MAX_FILE_SIZE_MB", "10")
        max_document_chars = cls._load_int("MAX_DOCUMENT_CHARS", "50000")
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        log_format = os.getenv("LOG_FORMAT", "%(asctime)s %(levelname)s %(name)s %(message)s")
        allowed_models = cls._load_allowed_models(lm_studio_model)
        generation_profiles = cls._load_generation_profiles()
        default_generation_profile = os.getenv(
            "DEFAULT_GENERATION_PROFILE",
            DEFAULT_GENERATION_PROFILE_NAME,
        ).strip()

        if max_document_chars <= 0:
            raise ConfigurationError("MAX_DOCUMENT_CHARS must be positive")

        return cls(
            lm_studio_base_url=lm_studio_base_url,
            lm_studio_model=lm_studio_model,
            request_timeout=request_timeout,
            max_file_size_mb=max_file_size_mb,
            max_document_chars=max_document_chars,
            log_level=log_level,
            log_format=log_format,
            allowed_models=allowed_models,
            generation_profiles=generation_profiles,
            default_generation_profile=default_generation_profile,
        )
