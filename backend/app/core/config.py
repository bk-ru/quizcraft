"""Runtime configuration for the QuizCraft backend."""

from __future__ import annotations

import os
from dataclasses import dataclass

from backend.app.domain.errors import ConfigurationError


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

    @staticmethod
    def _load_int(env_name: str, default: str) -> int:
        """Load an integer setting from the environment."""

        try:
            return int(os.getenv(env_name, default))
        except ValueError as error:
            raise ConfigurationError(f"{env_name} must be a valid integer") from error

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Build configuration from process environment variables."""

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
        )
