"""Вспомогательные средства структурированного логирования событий pipeline генерации."""

from __future__ import annotations

import logging

from backend.app.generation.live_journal import record_generation_pipeline_event
from backend.app.generation.status import GenerationPipelineEvent


def log_generation_pipeline_event(logger: logging.Logger, event: GenerationPipelineEvent) -> None:
    """Выпустить одно структурированное событие pipeline генерации."""

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
    record_generation_pipeline_event(event)
