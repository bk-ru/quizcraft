"""Structured logging helpers for generation pipeline events."""

from __future__ import annotations

import logging

from backend.app.generation.status import GenerationPipelineEvent


def log_generation_pipeline_event(logger: logging.Logger, event: GenerationPipelineEvent) -> None:
    """Emit one structured generation pipeline event."""

    logger.info(
        "Generation pipeline step status=%s step=%s document_id=%s",
        event.status.value,
        event.step.value,
        event.document_id,
        extra={
            "generation_event": "pipeline_step",
            **event.to_log_extra(),
        },
    )
