"""Quiz read, update, and export endpoints for the HTTP API."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import Response

from backend.app.api.schemas import QuizUpdateBody
from backend.app.api.schemas import SingleQuestionRegenerationBody
from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import Quiz
from backend.app.domain.models import Question
from backend.app.domain.validation import validate_quiz
from backend.app.export.json_exporter import QuizJsonExporter
from backend.app.storage.quizzes import FileSystemQuizRepository


def register_quiz_routes(app: FastAPI) -> None:
    """Register quiz read, update, and export routes on the FastAPI app."""

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
        target_question = _get_quiz_question(quiz, question_id)
        return {
            "quiz_id": quiz.quiz_id,
            "question_id": target_question.question_id,
            "target_question": _serialize_question(target_question),
            "request": payload.to_contract_dict(),
            "regeneration": {
                "status": "contract_validated",
                "provider_call": False,
                "quiz_mutated": False,
                "prompt_mode": "not_configured",
            },
            "request_id": request.state.correlation_id,
        }


def _serialize_quiz(quiz: Quiz, request_id: str) -> dict[str, Any]:
    """Serialize a persisted quiz for API responses."""

    return {
        "quiz_id": quiz.quiz_id,
        "quiz": quiz.to_dict(),
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
