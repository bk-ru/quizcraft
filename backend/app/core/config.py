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
from backend.app.llm.registry import ProviderName

logger = logging.getLogger(__name__)

DEFAULT_GENERATION_PROFILE_NAME = "balanced"
DEFAULT_ENABLED_PROVIDERS = (ProviderName.LM_STUDIO,)
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


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
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL
    ollama_model: str | None = None
    ollama_embedding_model: str | None = None
    external_api_base_url: str | None = None
    external_api_key: str | None = None
    external_api_model: str | None = None
    external_api_embedding_model: str | None = None
    request_timeout: int = 300
    max_file_size_mb: int = 10
    max_document_chars: int = 50_000
    log_level: str = "INFO"
    log_format: str = "%(asctime)s %(levelname)s %(name)s %(message)s"
    allowed_models: tuple[str, ...] = ()
    providers_enabled: tuple[ProviderName, ...] = DEFAULT_ENABLED_PROVIDERS
    default_provider: ProviderName | str | None = None
    generation_profiles: Mapping[str, GenerationProfile] = field(default_factory=_default_generation_profiles)
    default_generation_profile: str = DEFAULT_GENERATION_PROFILE_NAME

    def __post_init__(self) -> None:
        """Normalize and validate derived configuration fields."""

        normalized_providers_enabled = self._normalize_providers_enabled(self.providers_enabled)
        if self.default_provider is None:
            normalized_default_provider = normalized_providers_enabled[0]
        else:
            try:
                normalized_default_provider = ProviderName.normalize(self.default_provider)
            except ValueError as error:
                raise ConfigurationError(str(error)) from error

        normalized_lm_studio_model = self.lm_studio_model.strip()
        if not normalized_lm_studio_model:
            raise ConfigurationError("LM_STUDIO_MODEL must be a non-empty string")
        normalized_ollama_base_url = self.ollama_base_url.strip()
        if not normalized_ollama_base_url:
            raise ConfigurationError("OLLAMA_BASE_URL must be a non-empty string")
        normalized_ollama_model = (self.ollama_model or normalized_lm_studio_model).strip()
        if not normalized_ollama_model:
            raise ConfigurationError("OLLAMA_MODEL must be a non-empty string")
        normalized_ollama_embedding_model = (self.ollama_embedding_model or normalized_ollama_model).strip()
        if not normalized_ollama_embedding_model:
            raise ConfigurationError("OLLAMA_EMBEDDING_MODEL must be a non-empty string")
        uses_external_api = (
            ProviderName.EXTERNAL_API in normalized_providers_enabled
            or normalized_default_provider is ProviderName.EXTERNAL_API
        )
        normalized_external_api_base_url = (self.external_api_base_url or "").strip()
        if uses_external_api and not normalized_external_api_base_url:
            raise ConfigurationError("EXTERNAL_API_BASE_URL must be a non-empty string when external_api is configured")
        normalized_external_api_key = (
            self.external_api_key.strip()
            if isinstance(self.external_api_key, str) and self.external_api_key.strip()
            else None
        )
        normalized_external_api_model = (self.external_api_model or "").strip()
        if uses_external_api and not normalized_external_api_model:
            raise ConfigurationError("EXTERNAL_API_MODEL must be a non-empty string when external_api is configured")
        normalized_external_api_embedding_model = (
            self.external_api_embedding_model or normalized_external_api_model
        ).strip()
        if uses_external_api and not normalized_external_api_embedding_model:
            raise ConfigurationError(
                "EXTERNAL_API_EMBEDDING_MODEL must be a non-empty string when external_api is configured"
            )

        default_allowed_models = [normalized_lm_studio_model]
        if ProviderName.OLLAMA in normalized_providers_enabled or normalized_default_provider is ProviderName.OLLAMA:
            default_allowed_models.append(normalized_ollama_model)
        if uses_external_api:
            default_allowed_models.append(normalized_external_api_model)
        allowed_models = self.allowed_models or tuple(dict.fromkeys(default_allowed_models))
        normalized_allowed_models = tuple(model.strip() for model in allowed_models if model.strip())
        if not normalized_allowed_models:
            raise ConfigurationError("LM_STUDIO_ALLOWED_MODELS must include at least one model")
        if normalized_lm_studio_model not in normalized_allowed_models:
            raise ConfigurationError("LM_STUDIO_MODEL must be listed in LM_STUDIO_ALLOWED_MODELS")
        if (
            ProviderName.OLLAMA in normalized_providers_enabled or normalized_default_provider is ProviderName.OLLAMA
        ) and normalized_ollama_model not in normalized_allowed_models:
            raise ConfigurationError("OLLAMA_MODEL must be listed in LM_STUDIO_ALLOWED_MODELS")
        if uses_external_api and normalized_external_api_model not in normalized_allowed_models:
            raise ConfigurationError("EXTERNAL_API_MODEL must be listed in LM_STUDIO_ALLOWED_MODELS")

        normalized_profiles = self._normalize_generation_profiles(self.generation_profiles)
        if self.default_generation_profile not in normalized_profiles:
            raise ConfigurationError("DEFAULT_GENERATION_PROFILE must reference a configured profile")

        for profile in normalized_profiles.values():
            if profile.model_name is not None and profile.model_name not in normalized_allowed_models:
                raise ConfigurationError("generation profile model_name must be listed in LM_STUDIO_ALLOWED_MODELS")

        object.__setattr__(self, "lm_studio_model", normalized_lm_studio_model)
        object.__setattr__(self, "ollama_base_url", normalized_ollama_base_url)
        object.__setattr__(self, "ollama_model", normalized_ollama_model)
        object.__setattr__(self, "ollama_embedding_model", normalized_ollama_embedding_model)
        object.__setattr__(self, "external_api_base_url", normalized_external_api_base_url or None)
        object.__setattr__(self, "external_api_key", normalized_external_api_key)
        object.__setattr__(self, "external_api_model", normalized_external_api_model or None)
        object.__setattr__(
            self,
            "external_api_embedding_model",
            normalized_external_api_embedding_model or None,
        )
        object.__setattr__(self, "allowed_models", normalized_allowed_models)
        object.__setattr__(self, "providers_enabled", normalized_providers_enabled)
        object.__setattr__(self, "default_provider", normalized_default_provider)
        object.__setattr__(self, "generation_profiles", MappingProxyType(dict(normalized_profiles)))

    @property
    def default_model(self) -> str:
        """Return the default generation model for the configured active provider."""

        if self.default_provider is ProviderName.OLLAMA:
            return self.ollama_model or self.lm_studio_model
        if self.default_provider is ProviderName.EXTERNAL_API:
            return self.external_api_model or self.lm_studio_model
        return self.lm_studio_model

    @staticmethod
    def _load_int(env_name: str, default: str) -> int:
        """Load an integer setting from the environment."""

        try:
            return int(os.getenv(env_name, default))
        except ValueError as error:
            raise ConfigurationError(f"{env_name} must be a valid integer") from error

    @staticmethod
    def _load_allowed_models(default_models: tuple[str, ...]) -> tuple[str, ...]:
        """Load allowed model names from a comma-separated environment variable."""

        raw_value = os.getenv("LM_STUDIO_ALLOWED_MODELS")
        if raw_value is None:
            return tuple(dict.fromkeys(model for model in default_models if model.strip()))

        models = tuple(part.strip() for part in raw_value.split(",") if part.strip())
        if not models:
            raise ConfigurationError("LM_STUDIO_ALLOWED_MODELS must include at least one model")
        return models

    @staticmethod
    def _load_providers_enabled() -> tuple[ProviderName, ...]:
        """Load enabled provider names from a comma-separated environment variable."""

        raw_value = os.getenv("PROVIDERS_ENABLED")
        if raw_value is None:
            return DEFAULT_ENABLED_PROVIDERS

        providers = tuple(part.strip() for part in raw_value.split(","))
        if not providers or any(not provider for provider in providers):
            raise ConfigurationError("PROVIDERS_ENABLED must contain non-empty provider names")
        return AppConfig._normalize_providers_enabled(providers)

    @staticmethod
    def _load_default_provider() -> ProviderName | None:
        """Load the default provider name from the environment."""

        raw_value = os.getenv("DEFAULT_PROVIDER")
        if raw_value is None:
            return None
        try:
            return ProviderName.normalize(raw_value)
        except ValueError as error:
            raise ConfigurationError(str(error)) from error

    @staticmethod
    def _normalize_providers_enabled(
        providers_enabled: tuple[ProviderName | str, ...],
    ) -> tuple[ProviderName, ...]:
        """Normalize enabled provider names and reject unsupported values."""

        if not providers_enabled:
            raise ConfigurationError("PROVIDERS_ENABLED must include at least one provider")

        normalized_providers: list[ProviderName] = []
        seen_providers: set[ProviderName] = set()
        for provider_name in providers_enabled:
            try:
                normalized_provider_name = ProviderName.normalize(provider_name)
            except ValueError as error:
                raise ConfigurationError(str(error)) from error
            if normalized_provider_name in seen_providers:
                raise ConfigurationError(f"PROVIDERS_ENABLED contains duplicate provider '{normalized_provider_name.value}'")
            normalized_providers.append(normalized_provider_name)
            seen_providers.add(normalized_provider_name)
        return tuple(normalized_providers)

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

        ollama_base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
        ollama_model = os.getenv("OLLAMA_MODEL", lm_studio_model)
        ollama_embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", ollama_model)
        external_api_base_url = os.getenv("EXTERNAL_API_BASE_URL")
        external_api_key = os.getenv("EXTERNAL_API_API_KEY")
        external_api_model = os.getenv("EXTERNAL_API_MODEL")
        external_api_embedding_model = os.getenv("EXTERNAL_API_EMBEDDING_MODEL", external_api_model or "")
        providers_enabled = cls._load_providers_enabled()
        default_provider = cls._load_default_provider()
        default_allowed_models = [lm_studio_model]
        if ProviderName.OLLAMA in providers_enabled or default_provider is ProviderName.OLLAMA:
            default_allowed_models.append(ollama_model)
        if ProviderName.EXTERNAL_API in providers_enabled or default_provider is ProviderName.EXTERNAL_API:
            if external_api_model:
                default_allowed_models.append(external_api_model)
        request_timeout = cls._load_int("REQUEST_TIMEOUT", "300")
        max_file_size_mb = cls._load_int("MAX_FILE_SIZE_MB", "10")
        max_document_chars = cls._load_int("MAX_DOCUMENT_CHARS", "50000")
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        log_format = os.getenv("LOG_FORMAT", "%(asctime)s %(levelname)s %(name)s %(message)s")
        allowed_models = cls._load_allowed_models(tuple(default_allowed_models))
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
            ollama_base_url=ollama_base_url,
            ollama_model=ollama_model,
            ollama_embedding_model=ollama_embedding_model,
            external_api_base_url=external_api_base_url,
            external_api_key=external_api_key,
            external_api_model=external_api_model,
            external_api_embedding_model=external_api_embedding_model,
            request_timeout=request_timeout,
            max_file_size_mb=max_file_size_mb,
            max_document_chars=max_document_chars,
            log_level=log_level,
            log_format=log_format,
            allowed_models=allowed_models,
            providers_enabled=providers_enabled,
            default_provider=default_provider,
            generation_profiles=generation_profiles,
            default_generation_profile=default_generation_profile,
        )
