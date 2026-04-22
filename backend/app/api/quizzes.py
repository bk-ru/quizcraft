"""Quiz read endpoint for the HTTP API."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import Response

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import Quiz
from backend.app.domain.validation import validate_quiz
from backend.app.export.json_exporter import QuizJsonExporter
from backend.app.storage.quizzes import FileSystemQuizRepository


def register_quiz_routes(app: FastAPI) -> None:
    """Register quiz read routes on the FastAPI app."""

    @app.get("/quizzes/{quiz_id}")
    async def get_quiz(request: Request, quiz_id: str) -> dict[str, Any]:
        quiz = FileSystemQuizRepository(request.app.state.storage_root).get(quiz_id)
        return _serialize_quiz(quiz, request.state.correlation_id)

    @app.get("/quizzes/{quiz_id}/export/json")
    async def export_quiz_json(request: Request, quiz_id: str) -> Response:
        quiz = FileSystemQuizRepository(request.app.state.storage_root).get(quiz_id)
        exported_file = QuizJsonExporter().export(quiz)
        response = Response(content=exported_file.content_bytes, media_type="application/json")
        response.headers["content-disposition"] = f'attachment; filename="{exported_file.filename}"'
        response.headers["content-type"] = exported_file.media_type
        return response

    @app.put("/quizzes/{quiz_id}")
    async def update_quiz(request: Request, quiz_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        repository = FileSystemQuizRepository(request.app.state.storage_root)
        existing_quiz = repository.get(quiz_id)
        updated_quiz = _deserialize_quiz_update(payload, quiz_id, existing_quiz)
        validate_quiz(updated_quiz)
        persisted_quiz = repository.save(updated_quiz)
        return _serialize_quiz(persisted_quiz, request.state.correlation_id)


def _serialize_quiz(quiz: Quiz, request_id: str) -> dict[str, Any]:
    """Serialize a persisted quiz for API responses."""

    return {
        "quiz_id": quiz.quiz_id,
        "quiz": quiz.to_dict(),
        "request_id": request_id,
    }


def _deserialize_quiz_update(payload: dict[str, Any], quiz_id: str, existing_quiz: Quiz) -> Quiz:
    """Deserialize and normalize a quiz update payload."""

    quiz_payload = payload.get("quiz")
    if not isinstance(quiz_payload, dict):
        raise DomainValidationError("quiz payload must be an object")
    payload_quiz_id = quiz_payload.get("quiz_id")
    if payload_quiz_id != quiz_id:
        raise DomainValidationError("quiz_id in payload must match path")
    if quiz_payload.get("document_id") != existing_quiz.document_id:
        raise DomainValidationError("document_id must match the stored quiz")

    try:
        parsed_quiz = Quiz.from_dict(quiz_payload)
    except (KeyError, TypeError) as error:
        raise DomainValidationError("quiz payload is missing required fields") from error

    return replace(
        parsed_quiz,
        quiz_id=existing_quiz.quiz_id,
        document_id=existing_quiz.document_id,
        version=existing_quiz.version,
        last_edited_at=existing_quiz.last_edited_at,
    )
