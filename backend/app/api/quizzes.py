"""Quiz read endpoint for the HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi import Request

from backend.app.domain.models import Quiz
from backend.app.storage.quizzes import FileSystemQuizRepository


def register_quiz_routes(app: FastAPI) -> None:
    """Register quiz read routes on the FastAPI app."""

    @app.get("/quizzes/{quiz_id}")
    async def get_quiz(request: Request, quiz_id: str) -> dict[str, Any]:
        quiz = FileSystemQuizRepository(request.app.state.storage_root).get(quiz_id)
        return _serialize_quiz(quiz, request.state.correlation_id)


def _serialize_quiz(quiz: Quiz, request_id: str) -> dict[str, Any]:
    """Serialize a persisted quiz for API responses."""

    return {
        "quiz_id": quiz.quiz_id,
        "quiz": quiz.to_dict(),
        "request_id": request_id,
    }
