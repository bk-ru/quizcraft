"""Backend bootstrap entry point."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.app.core.config import AppConfig


@dataclass(slots=True)
class ApplicationBootstrap:
    """Minimal application container for the backend bootstrap stage."""

    config: AppConfig


def create_app(config: AppConfig | None = None) -> ApplicationBootstrap:
    """Create the minimal application bootstrap container."""

    resolved_config = config or AppConfig.from_env()
    logging.basicConfig(
        level=getattr(logging, resolved_config.log_level, logging.INFO),
        format=resolved_config.log_format,
        force=True,
    )
    return ApplicationBootstrap(config=resolved_config)
