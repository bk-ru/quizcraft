"""Endpoint прямой генерации для HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi import Query
from fastapi import Request
from starlette.concurrency import run_in_threadpool

from backend.app.api.runtime import get_generation_dispatcher
from backend.app.api.runtime import get_generation_event_store
from backend.app.api.runtime import get_generation_settings_repository
from backend.app.api.schemas import GenerationRequestBody
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import GenerationResult
from backend.app.domain.models import GenerationSettings
from backend.app.generation.live_journal import bind_generation_journal
from backend.app.generation.profiles import GenerationProfileResolver


def register_generation_routes(app: FastAPI) -> None:
    """Зарегистрировать маршруты генерации в приложении FastAPI."""

    @app.get("/generation/runs/{request_id}/events")
    async def get_generation_events(
        request: Request,
        request_id: str,
        after: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        event_store = get_generation_event_store(request.app)
        events = event_store.list_events(request_id, after=after)
        return {
            "request_id": request_id,
            "events": [event.to_dict() for event in events],
            "next_after": after if not events else events[-1].event_id,
            "complete": event_store.is_complete(request_id),
        }

    @app.post("/documents/{document_id}/generate")
    async def generate_quiz(
        request: Request,
        document_id: str,
        payload: GenerationRequestBody,
    ) -> dict[str, Any]:
        settings_repository = get_generation_settings_repository(request.app)
        settings = payload.to_settings(defaults=_load_saved_settings(settings_repository))
        profile = GenerationProfileResolver(request.app.state.config).resolve(
            model_name=settings.model_name,
            profile_name=settings.profile_name,
        )
        dispatcher = get_generation_dispatcher(request.app)
        generation_request = settings.to_generation_request(
            model_name=profile.model_name,
            profile_name=profile.profile_name,
            inference_parameters=dict(profile.inference_parameters),
        )
        with bind_generation_journal(request.state.correlation_id, get_generation_event_store(request.app)):
            result = await run_in_threadpool(
                dispatcher.dispatch,
                document_id,
                generation_request,
            )
        settings_repository.save(settings)
        return _serialize_generation_result(result, request.state.correlation_id)


def _load_saved_settings(settings_repository) -> GenerationSettings | None:
    """Загрузить сохраненные настройки генерации, если они существуют."""

    try:
        return settings_repository.get()
    except RepositoryNotFoundError:
        return None


def _serialize_generation_result(result: GenerationResult, request_id: str) -> dict[str, Any]:
    """Сериализовать результат генерации для API-ответов."""

    return {
        "quiz_id": result.quiz.quiz_id,
        "quiz": result.quiz.to_dict(),
        "model_name": result.model_name,
        "prompt_version": result.prompt_version,
        "request_id": request_id,
    }
