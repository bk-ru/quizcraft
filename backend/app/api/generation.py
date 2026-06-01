"""Endpoint прямой генерации для HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi import Query
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.app.api.runtime import get_generation_cancellation_registry
from backend.app.api.runtime import get_generation_dispatcher
from backend.app.api.runtime import get_generation_event_store
from backend.app.api.runtime import get_generation_settings_repository
from backend.app.api.schemas import GenerationRequestBody
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import GenerationResult
from backend.app.domain.models import GenerationSettings
from backend.app.generation.live_journal import bind_generation_journal
from backend.app.generation.cancellation import bind_generation_cancellation
from backend.app.generation.live_journal import GenerationEventStore
from backend.app.generation.profiles import GenerationProfileResolver
from backend.app.generation.status import GenerationPipelineEvent
from backend.app.generation.status import GenerationPipelineStep
from backend.app.generation.status import GenerationRunStatus


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

    @app.post("/generation/runs/{request_id}/cancel")
    async def cancel_generation_run(
        request: Request,
        request_id: str,
    ) -> JSONResponse:
        registry = get_generation_cancellation_registry(request.app)
        outcome = registry.cancel(request_id)
        if outcome is None:
            raise RepositoryNotFoundError("generation_run", request_id)
        if outcome.accepted:
            _append_cancelled_generation_event(
                get_generation_event_store(request.app),
                request_id=request_id,
                document_id=outcome.document_id,
            )
        return JSONResponse(
            status_code=202 if outcome.accepted else 200,
            content=outcome.to_dict(),
        )

    @app.post("/documents/{document_id}/generate")
    async def generate_quiz(
        request: Request,
        document_id: str,
        payload: GenerationRequestBody,
    ) -> dict[str, Any]:
        registry = get_generation_cancellation_registry(request.app)
        cancellation_token = registry.start_run(
            request.state.correlation_id,
            document_id=document_id,
        )
        event_store = get_generation_event_store(request.app)
        event_store.reset_run(request.state.correlation_id)
        if cancellation_token.is_cancelled:
            _append_cancelled_generation_event(
                event_store,
                request_id=request.state.correlation_id,
                document_id=document_id,
            )
        try:
            with (
                bind_generation_journal(request.state.correlation_id, event_store),
                bind_generation_cancellation(cancellation_token),
            ):
                cancellation_token.raise_if_cancelled()
                settings_repository = get_generation_settings_repository(request.app)
                settings = payload.to_settings(defaults=_load_saved_settings(settings_repository))
                profile = GenerationProfileResolver(request.app.state.config).resolve(
                    model_name=settings.model_name,
                    profile_name=settings.profile_name,
                )
                dispatcher = get_generation_dispatcher(request.app)
                inference_parameters = dict(profile.inference_parameters)
                inference_parameters.update(payload.inference_parameter_overrides())
                generation_request = settings.to_generation_request(
                    model_name=profile.model_name,
                    profile_name=profile.profile_name,
                    inference_parameters=inference_parameters,
                )
                cancellation_token.raise_if_cancelled()
                result = await run_in_threadpool(
                    dispatcher.dispatch,
                    document_id,
                    generation_request,
                    cancellation_token,
                )
                cancellation_token.raise_if_cancelled()
            settings_repository.save(settings)
            return _serialize_generation_result(result, request.state.correlation_id)
        finally:
            registry.finish(
                cancellation_token,
                GenerationRunStatus.FAILED,
            )


def _append_cancelled_generation_event(
    event_store: GenerationEventStore,
    *,
    request_id: str,
    document_id: str,
) -> None:
    """Добавить terminal event принятой пользователем отмены."""

    event_store.append(
        request_id,
        GenerationPipelineEvent(
            status=GenerationRunStatus.CANCELLED,
            step=GenerationPipelineStep.CANCEL,
            document_id=document_id,
        ),
    )


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
        "warnings": [warning.to_dict() for warning in result.warnings],
        "quality_status": result.quality_status,
        "request_id": request_id,
    }
