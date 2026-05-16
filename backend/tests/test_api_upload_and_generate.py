from __future__ import annotations

import asyncio
import json
import threading
import time

from fastapi.testclient import TestClient

from backend.app.core.config import AppConfig
from backend.app.domain.errors import LLMTimeoutError
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.llm.registry import ProviderName
from backend.app.main import create_app
from backend.app.storage.documents import FileSystemDocumentRepository


class StubProvider:
    """Test double провайдера для API-потоков загрузки и генерации."""

    def __init__(
        self,
        responses: list[StructuredGenerationResponse] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self._error = error
        self.requests: list[StructuredGenerationRequest] = []

    def healthcheck(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(status="available", message="LM Studio is available")

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        if not self._responses:
            raise AssertionError("provider was called more times than expected")
        return self._responses.pop(0)

    def embed(self, request):
        raise AssertionError("embed should not be called in upload or generate API tests")


class SlowProvider(StubProvider):
    def __init__(self, responses: list[StructuredGenerationResponse], delay_seconds: float = 0.8) -> None:
        super().__init__(responses=responses)
        self.delay_seconds = delay_seconds
        self.started = threading.Event()

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        self.started.set()
        time.sleep(self.delay_seconds)
        return super().generate_structured(request)


def build_config(max_document_chars: int = 50_000, max_file_size_mb: int = 10) -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        max_file_size_mb=max_file_size_mb,
        max_document_chars=max_document_chars,
        log_format="%(levelname)s:%(message)s",
    )


def build_disabled_lm_studio_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        log_format="%(levelname)s:%(message)s",
        providers_enabled=(ProviderName.OLLAMA,),
        default_provider=ProviderName.LM_STUDIO,
    )


def build_generation_payload() -> dict[str, object]:
    return {
        "question_count": 2,
        "language": "ru",
        "difficulty": "medium",
        "quiz_type": "single_choice",
        "generation_mode": "direct",
    }


def build_provider_response() -> StructuredGenerationResponse:
    return StructuredGenerationResponse(
        model_name="local-model",
        content={
            "quiz_id": "quiz-generated",
            "document_id": "ignored-by-normalizer",
            "title": "Generated quiz",
            "version": 1,
            "last_edited_at": "2026-04-18T12:00:00Z",
            "questions": [
                {
                    "question_id": "q-1",
                    "prompt": "Question 1?",
                    "options": [
                        {"option_id": "opt-1", "text": "Option A"},
                        {"option_id": "opt-2", "text": "Option B"},
                    ],
                    "correct_option_index": 0,
                    "explanation": {"text": "Explanation 1."},
                },
                {
                    "question_id": "q-2",
                    "prompt": "Question 2?",
                    "options": [
                        {"option_id": "opt-1", "text": "Option A"},
                        {"option_id": "opt-2", "text": "Option B"},
                    ],
                    "correct_option_index": 0,
                    "explanation": {"text": "Explanation 2."},
                },
            ],
        },
        raw_response={"id": "resp-1", "choices": [{"index": 0}]},
    )


def build_partial_provider_response() -> StructuredGenerationResponse:
    response = build_provider_response()
    content = dict(response.content)
    content["questions"] = list(content["questions"])[:1]
    return StructuredGenerationResponse(
        model_name=response.model_name,
        content=content,
        raw_response={"id": "resp-partial", "choices": [{"index": 0}]},
    )


def upload_document(client: TestClient) -> str:
    response = client.post(
        "/documents",
        content=b"First fact.\nSecond fact.",
        headers={"X-Filename": "lecture.txt", "Content-Type": "text/plain"},
    )
    assert response.status_code == 201
    return response.json()["document_id"]


def upload_russian_document(client: TestClient) -> str:
    response = client.post(
        "/documents",
        content="Первый факт.\nВторой факт.".encode("utf-8"),
        headers={"X-Filename": "lecture.txt", "Content-Type": "text/plain"},
    )
    assert response.status_code == 201
    return response.json()["document_id"]


class FailingIngestionService:
    def __init__(self) -> None:
        self.calls = 0

    def ingest(self, *, filename: str, media_type: str, content: bytes):
        self.calls += 1
        raise AssertionError("ingestion service should not be called for oversized upload")


async def post_document_asgi(app, *, headers, chunks, forbid_receive: bool = False):
    sent_messages: list[dict[str, object]] = []
    receive_calls = 0

    async def receive():
        nonlocal receive_calls
        receive_calls += 1
        if forbid_receive:
            raise AssertionError("request body should not be read")
        if receive_calls <= len(chunks):
            return {
                "type": "http.request",
                "body": chunks[receive_calls - 1],
                "more_body": receive_calls < len(chunks),
            }
        return {"type": "http.disconnect"}

    async def send(message):
        sent_messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/documents",
        "raw_path": b"/documents",
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)

    status = next(message["status"] for message in sent_messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in sent_messages
        if message["type"] == "http.response.body"
    )
    return int(status), json.loads(body.decode("utf-8")), receive_calls


def test_document_upload_endpoint_persists_valid_file_and_returns_metadata(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/documents",
        content=b"First fact.\nSecond fact.",
        headers={"X-Filename": "lecture.txt", "Content-Type": "text/plain"},
    )

    assert response.status_code == 201
    payload = response.json()
    persisted = FileSystemDocumentRepository(tmp_path).get(payload["document_id"])
    assert payload["filename"] == "lecture.txt"
    assert payload["media_type"] == "text/plain"
    assert payload["file_size_bytes"] == len(b"First fact.\nSecond fact.")
    assert payload["metadata"]["text_length"] == len("First fact.\nSecond fact.")
    assert response.headers["X-Request-ID"] == payload["request_id"]
    assert persisted.document_id == payload["document_id"]


def test_document_upload_endpoint_rejects_invalid_file(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/documents",
        content=b"image",
        headers={"X-Filename": "lecture.png", "Content-Type": "image/png"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "file_validation_error"


def test_document_upload_rejects_content_length_over_limit_without_calling_ingestion(tmp_path) -> None:
    limit = 1024 * 1024
    app = create_app(config=build_config(max_file_size_mb=1), provider=StubProvider(), storage_root=tmp_path)
    service = FailingIngestionService()
    app.state.document_ingestion_service = service

    status, payload, receive_calls = asyncio.run(
        post_document_asgi(
            app,
            headers=[
                (b"host", b"testserver"),
                (b"x-filename", b"lecture.txt"),
                (b"content-type", b"text/plain"),
                (b"content-length", str(limit + 1).encode("ascii")),
            ],
            chunks=[b"body"],
            forbid_receive=True,
        )
    )

    assert status == 413
    assert payload["error"]["code"] == "document_too_large"
    assert receive_calls == 0
    assert service.calls == 0


def test_document_upload_without_content_length_stops_streaming_when_limit_is_exceeded(tmp_path) -> None:
    limit = 1024 * 1024
    app = create_app(config=build_config(max_file_size_mb=1), provider=StubProvider(), storage_root=tmp_path)
    service = FailingIngestionService()
    app.state.document_ingestion_service = service

    status, payload, receive_calls = asyncio.run(
        post_document_asgi(
            app,
            headers=[
                (b"host", b"testserver"),
                (b"x-filename", b"lecture.txt"),
                (b"content-type", b"text/plain"),
            ],
            chunks=[b"a" * limit, b"b", b"c"],
        )
    )

    assert status == 413
    assert payload["error"]["code"] == "document_too_large"
    assert receive_calls == 2
    assert service.calls == 0


def test_document_upload_accepts_file_exactly_at_size_limit(tmp_path) -> None:
    limit = 1024 * 1024
    app = create_app(config=build_config(max_file_size_mb=1), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/documents",
        content=b"a" * limit,
        headers={"X-Filename": "lecture.txt", "Content-Type": "text/plain"},
    )

    assert response.status_code == 201
    assert response.json()["file_size_bytes"] == limit


def test_direct_generation_endpoint_returns_generated_quiz_for_existing_document(tmp_path) -> None:
    provider = StubProvider(responses=[build_provider_response()])
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_generation_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["quiz_id"] == payload["quiz"]["quiz_id"]
    assert payload["quiz"]["document_id"] == document_id
    assert payload["model_name"] == "local-model"
    assert payload["prompt_version"] == "direct-v1"
    assert payload["quality_status"] == "ok"
    assert len(payload["quiz"]["questions"]) == 2
    assert "Question count: 2" in provider.requests[0].user_prompt


def test_direct_generation_endpoint_returns_partial_quiz_with_warning_when_llm_returns_too_few_questions(tmp_path) -> None:
    provider = StubProvider(
        responses=[
            build_partial_provider_response(),
            build_partial_provider_response(),
        ]
    )
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_generation_payload())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["quiz"]["questions"]) == 1
    assert payload["quality_status"] == "partial"
    assert payload["warnings"][0]["code"] == "generation_quality_error"
    assert "Модель вернула 1 вопрос вместо запрошенных 2" in payload["warnings"][0]["message"]
    assert "повторите генерацию" in payload["warnings"][0]["recommendations"][0]


def test_generation_live_journal_exposes_sanitized_pipeline_events(tmp_path) -> None:
    provider = StubProvider(responses=[build_provider_response()])
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)

    response = client.post(
        f"/documents/{document_id}/generate",
        json=build_generation_payload(),
        headers={"X-Request-ID": "run-live-journal-1"},
    )
    events_response = client.get("/generation/runs/run-live-journal-1/events")

    assert response.status_code == 200
    assert events_response.status_code == 200
    payload = events_response.json()
    assert payload["request_id"] == "run-live-journal-1"
    assert payload["complete"] is True
    messages = [event["message"] for event in payload["events"]]
    assert "Загружаем документ и проверяем ограничения." in messages
    assert "Формируем запрос для модели." in messages
    assert "Отправляем запрос провайдеру." in messages
    assert "Провайдер ответил, проверяем структуру результата." in messages
    assert "Проверяем качество квиза." in messages
    assert "Квиз сохранён: 2 вопросов." in messages
    assert all("user_prompt" not in json.dumps(event, ensure_ascii=False) for event in payload["events"])


def test_generation_live_journal_streams_while_provider_request_is_in_flight(tmp_path) -> None:
    provider = SlowProvider(responses=[build_provider_response()])
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)
    response_holder = {}

    def run_generation() -> None:
        response_holder["response"] = client.post(
            f"/documents/{document_id}/generate",
            json=build_generation_payload(),
            headers={"X-Request-ID": "run-live-journal-stream"},
        )

    generation_thread = threading.Thread(target=run_generation)
    generation_thread.start()
    try:
        assert provider.started.wait(timeout=2)
        started_at = time.perf_counter()
        events_response = client.get("/generation/runs/run-live-journal-stream/events")
        elapsed = time.perf_counter() - started_at
    finally:
        generation_thread.join(timeout=3)

    assert not generation_thread.is_alive()
    assert response_holder["response"].status_code == 200
    assert events_response.status_code == 200
    assert elapsed < provider.delay_seconds / 2
    payload = events_response.json()
    assert payload["complete"] is False
    assert any(
        event["step"] == "generate" and event["status"] == "running"
        for event in payload["events"]
    )


def test_direct_generation_endpoint_maps_missing_document_to_not_found(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.post("/documents/doc-missing/generate", json=build_generation_payload())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_direct_generation_endpoint_rejects_unknown_difficulty(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)
    payload = build_generation_payload()
    payload["difficulty"] = "insane"

    response = client.post(f"/documents/{document_id}/generate", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "difficulty" in body["error"]["message"]
    assert "easy" in body["error"]["message"]


def test_direct_generation_endpoint_rejects_unknown_quiz_type(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)
    payload = build_generation_payload()
    payload["quiz_type"] = "multi_choice"

    response = client.post(f"/documents/{document_id}/generate", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "quiz_type" in body["error"]["message"]


def test_direct_generation_endpoint_rejects_unknown_language(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)
    payload = build_generation_payload()
    payload["language"] = "русский"

    response = client.post(f"/documents/{document_id}/generate", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "language" in body["error"]["message"]


def test_direct_generation_endpoint_rejects_coerced_question_count_types(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)
    payload = build_generation_payload()
    payload["question_count"] = True

    response = client.post(f"/documents/{document_id}/generate", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "question_count" in body["error"]["message"]

    payload["question_count"] = "2"
    response = client.post(f"/documents/{document_id}/generate", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "question_count" in body["error"]["message"]


def test_direct_generation_endpoint_maps_oversized_document_to_413(tmp_path) -> None:
    provider = StubProvider()
    app = create_app(config=build_config(max_document_chars=10), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_generation_payload())

    assert response.status_code == 413
    body = response.json()
    assert body["error"]["code"] == "document_too_large_for_generation"
    assert document_id in body["error"]["message"]
    assert provider.requests == []


def test_direct_generation_endpoint_maps_provider_timeout_to_gateway_timeout(tmp_path) -> None:
    provider = StubProvider(error=LLMTimeoutError("LM Studio timed out"))
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_generation_payload())

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "llm_timeout_error"


def test_direct_generation_endpoint_rejects_disabled_provider_without_calling_provider(tmp_path) -> None:
    provider = StubProvider(responses=[build_provider_response()])
    app = create_app(config=build_disabled_lm_studio_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_generation_payload())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "provider_disabled"
    assert "lm_studio" in response.json()["error"]["message"]
    assert provider.requests == []


def test_document_upload_endpoint_preserves_russian_text_in_storage(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/documents",
        content="Первый факт.\nВторой факт.".encode("utf-8"),
        headers={"X-Filename": "lecture.txt", "Content-Type": "text/plain"},
    )

    assert response.status_code == 201
    persisted = FileSystemDocumentRepository(tmp_path).get(response.json()["document_id"])
    assert persisted.normalized_text == "Первый факт.\nВторой факт."


def test_document_upload_endpoint_accepts_russian_filename_query_param(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/documents",
        params={"filename": "тестовый-конспект.txt"},
        content="Первый факт.\nВторой факт.".encode("utf-8"),
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 201
    payload = response.json()
    persisted = FileSystemDocumentRepository(tmp_path).get(payload["document_id"])
    assert payload["filename"] == "тестовый-конспект.txt"
    assert persisted.filename == "тестовый-конспект.txt"
    assert persisted.normalized_text == "Первый факт.\nВторой факт."


def test_direct_generation_endpoint_returns_russian_quiz_for_russian_document(tmp_path) -> None:
    provider = StubProvider(
        responses=[
            StructuredGenerationResponse(
                model_name="local-model",
                content={
                    "quiz_id": "quiz-ru",
                    "document_id": "ignored-by-normalizer",
                    "title": "Русский квиз",
                    "version": 1,
                    "last_edited_at": "2026-04-18T12:00:00Z",
                    "questions": [
                        {
                            "question_id": "q-1",
                            "prompt": "Что указано в документе?",
                            "options": [
                                {"option_id": "opt-1", "text": "Первый факт"},
                                {"option_id": "opt-2", "text": "Третий факт"},
                            ],
                            "correct_option_index": 0,
                            "explanation": {"text": "В документе есть первый факт."},
                        },
                        {
                            "question_id": "q-2",
                            "prompt": "Сколько фактов перечислено?",
                            "options": [
                                {"option_id": "opt-1", "text": "Два"},
                                {"option_id": "opt-2", "text": "Четыре"},
                            ],
                            "correct_option_index": 0,
                            "explanation": {"text": "В документе перечислены два факта."},
                        },
                    ],
                },
                raw_response={"id": "resp-ru-1", "choices": [{"index": 0}]},
            )
        ]
    )
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_generation_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["quiz"]["title"] == "Русский квиз"
    assert payload["quiz"]["document_id"] == document_id
    assert payload["quiz"]["questions"][0]["prompt"] == "Что указано в документе?"
    assert payload["quiz"]["questions"][0]["options"][0]["text"] == "Первый факт"
    assert payload["quiz"]["questions"][0]["explanation"] == {"text": "В документе есть первый факт."}
