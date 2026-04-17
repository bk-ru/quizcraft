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
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Build configuration from process environment variables."""

        lm_studio_base_url = os.getenv("LM_STUDIO_BASE_URL")
        if not lm_studio_base_url:
            raise ConfigurationError("LM_STUDIO_BASE_URL is required")

        lm_studio_model = os.getenv("LM_STUDIO_MODEL")
        if not lm_studio_model:
            raise ConfigurationError("LM_STUDIO_MODEL is required")

        request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        return cls(
            lm_studio_base_url=lm_studio_base_url,
            lm_studio_model=lm_studio_model,
            request_timeout=request_timeout,
            max_file_size_mb=max_file_size_mb,
            log_level=log_level,
        )
