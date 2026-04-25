"""Quiz read, update, and export endpoints for the HTTP API."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import Response

from backend.app.api.runtime import get_generation_settings_repository
from backend.app.api.runtime import get_single_question_regeneration_orchestrator
from backend.app.api.schemas import QuizUpdateBody
from backend.app.api.schemas import SingleQuestionRegenerationBody
from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import GenerationSettings
from backend.app.domain.models import Quiz
from backend.app.domain.models import Question
from backend.app.domain.validation import validate_quiz
from backend.app.export.base import ExportedQuizFile
from backend.app.export.registry import DEFAULT_QUIZ_EXPORT_REGISTRY
from backend.app.generation.profiles import GenerationProfileResolver
from backend.app.generation.single_question import SingleQuestionRegenerationResult
from backend.app.storage.quizzes import FileSystemQuizRepository


def register_quiz_routes(app: FastAPI) -> None:
    """Register quiz read, update, and export routes on the FastAPI app."""

    @app.get("/export/formats")
    async def get_export_formats(request: Request) -> dict[str, Any]:
        return {
            "formats": _serialize_export_formats(),
            "request_id": request.state.correlation_id,
        }

    @app.get("/quizzes/{quiz_id}")
    async def get_quiz(request: Request, quiz_id: str) -> dict[str, Any]:
        quiz = FileSystemQuizRepository(request.app.state.storage_root).get(quiz_id)
        return _serialize_quiz(quiz, request.state.correlation_id)

    @app.get("/quizzes/{quiz_id}/export/json")
    async def export_quiz_json(request: Request, quiz_id: str) -> Response:
        exported_file = _export_persisted_quiz(request.app.state.storage_root, quiz_id, "json")
        return _build_export_response(exported_file)

    @app.get("/quizzes/{quiz_id}/export/{export_format}")
    async def export_quiz(request: Request, quiz_id: str, export_format: str) -> Response:
        exported_file = _export_persisted_quiz(request.app.state.storage_root, quiz_id, export_format)
        return _build_export_response(exported_file)

    @app.put("/quizzes/{quiz_id}")
    async def update_quiz(request: Request, quiz_id: str, payload: QuizUpdateBody) -> dict[str, Any]:
        repository = FileSystemQuizRepository(request.app.state.storage_root)
        existing_quiz = repository.get(quiz_id)
        updated_quiz = _apply_quiz_update(payload, quiz_id, existing_quiz)
        validate_quiz(updated_quiz)
        persisted_quiz = repository.save(updated_quiz)
        return _serialize_quiz(persisted_quiz, request.state.correlation_id)

    @app.post("/quizzes/{quiz_id}/questions/{question_id}/regenerate")
    async def validate_single_question_regeneration_contract(
        request: Request,
        quiz_id: str,
        question_id: str,
        payload: SingleQuestionRegenerationBody,
    ) -> dict[str, Any]:
        repository = FileSystemQuizRepository(request.app.state.storage_root)
        quiz = repository.get(quiz_id)
        _validate_regeneration_boundary(payload, quiz_id, question_id)
        _get_quiz_question(quiz, question_id)
        settings_repository = get_generation_settings_repository(request.app)
        settings = payload.to_generation_settings(defaults=_load_saved_settings(settings_repository))
        profile = GenerationProfileResolver(request.app.state.config).resolve(
            model_name=settings.model_name,
            profile_name=settings.profile_name,
        )
        result = get_single_question_regeneration_orchestrator(request.app).regenerate(
            quiz_id=quiz_id,
            question_id=question_id,
            generation_request=settings.to_generation_request(
                model_name=profile.model_name,
                profile_name=profile.profile_name,
                inference_parameters=dict(profile.inference_parameters),
            ),
            instructions=payload.instructions,
        )
        return _serialize_single_question_regeneration_result(result, request.state.correlation_id)


def _serialize_quiz(quiz: Quiz, request_id: str) -> dict[str, Any]:
    """Serialize a persisted quiz for API responses."""

    return {
        "quiz_id": quiz.quiz_id,
        "quiz": quiz.to_dict(),
        "request_id": request_id,
    }


def _build_export_response(exported_file: ExportedQuizFile) -> Response:
    """Build a file download response for an exported quiz artifact."""

    response = Response(content=exported_file.content_bytes, media_type=exported_file.media_type)
    response.headers["content-disposition"] = f'attachment; filename="{exported_file.filename}"'
    response.headers["content-type"] = exported_file.media_type
    return response


def _export_persisted_quiz(storage_root, quiz_id: str, export_format: str) -> ExportedQuizFile:
    """Export a persisted quiz through the registered exporter for the requested format."""

    exporter = DEFAULT_QUIZ_EXPORT_REGISTRY.get(export_format)
    quiz = FileSystemQuizRepository(storage_root).get(quiz_id)
    return exporter.export(quiz)


def _serialize_export_formats() -> list[dict[str, str]]:
    """Serialize supported export formats for API capability discovery."""

    return [
        {
            "format": export_format,
            "media_type": DEFAULT_QUIZ_EXPORT_REGISTRY.get(export_format).media_type,
        }
        for export_format in DEFAULT_QUIZ_EXPORT_REGISTRY.supported_formats()
    ]


def _serialize_single_question_regeneration_result(
    result: SingleQuestionRegenerationResult,
    request_id: str,
) -> dict[str, Any]:
    """Serialize a targeted regeneration result for API responses."""

    return {
        "quiz_id": result.quiz.quiz_id,
        "question_id": result.regenerated_question.question_id,
        "quiz": result.quiz.to_dict(),
        "regenerated_question": _serialize_question(result.regenerated_question),
        "model_name": result.model_name,
        "prompt_version": result.prompt_version,
        "request_id": request_id,
    }


def _apply_quiz_update(payload: QuizUpdateBody, quiz_id: str, existing_quiz: Quiz) -> Quiz:
    """Build the domain quiz for an update, enforcing path and ownership invariants."""

    if payload.quiz.quiz_id != quiz_id:
        raise DomainValidationError("quiz_id in payload must match path")
    if payload.quiz.document_id != existing_quiz.document_id:
        raise DomainValidationError("document_id must match the stored quiz")

    parsed_quiz = payload.quiz.to_domain()
    return replace(
        parsed_quiz,
        quiz_id=existing_quiz.quiz_id,
        document_id=existing_quiz.document_id,
        version=existing_quiz.version,
        last_edited_at=existing_quiz.last_edited_at,
    )


def _validate_regeneration_boundary(
    payload: SingleQuestionRegenerationBody,
    quiz_id: str,
    question_id: str,
) -> None:
    """Validate optional payload identifiers against the path boundary."""

    if payload.quiz_id is not None and payload.quiz_id != quiz_id:
        raise DomainValidationError("quiz_id in payload must match path")
    if payload.question_id is not None and payload.question_id != question_id:
        raise DomainValidationError("question_id in payload must match path")


def _get_quiz_question(quiz: Quiz, question_id: str) -> Question:
    """Return one question from a quiz or raise a controlled not-found error."""

    for question in quiz.questions:
        if question.question_id == question_id:
            return question
    raise RepositoryNotFoundError("question", question_id)


def _serialize_question(question: Question) -> dict[str, Any]:
    """Serialize one quiz question for API responses."""

    return {
        "question_id": question.question_id,
        "prompt": question.prompt,
        "options": [
            {
                "option_id": option.option_id,
                "text": option.text,
            }
            for option in question.options
        ],
        "correct_option_index": question.correct_option_index,
        "explanation": None if question.explanation is None else {"text": question.explanation.text},
    }


def _load_saved_settings(settings_repository) -> GenerationSettings | None:
    """Load saved generation settings if they exist."""

    try:
        return settings_repository.get()
    except RepositoryNotFoundError:
        return None
