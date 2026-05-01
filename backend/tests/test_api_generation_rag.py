from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.core.config import AppConfig
from backend.app.domain.models import EmbeddingRequest
from backend.app.domain.models import EmbeddingResponse
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.generation.mode_selector import DEFAULT_RAG_THRESHOLD_CHARS
from backend.app.main import create_app


class StubRagApiProvider:
    """Provider stub that handles both embed and generate_structured calls."""

    def __init__(
        self,
        *,
        structured_responses: list[StructuredGenerationResponse],
        embedding_dimension: int = 4,
        embedding_model_name: str = "rag-embed",
    ) -> None:
        self._structured_responses = list(structured_responses)
        self._embedding_dimension = embedding_dimension
        self._embedding_model_name = embedding_model_name
        self.embedding_requests: list[EmbeddingRequest] = []
        self.structured_requests: list[StructuredGenerationRequest] = []

    def healthcheck(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(status="available", message="LM Studio is available")

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        self.embedding_requests.append(request)
        vectors = tuple(
            self._encode_text(text, position) for position, text in enumerate(request.texts)
        )
        return EmbeddingResponse(model_name=self._embedding_model_name, vectors=vectors)

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        self.structured_requests.append(request)
        if not self._structured_responses:
            raise AssertionError("provider was called more times than expected")
        return self._structured_responses.pop(0)

    def _encode_text(self, text: str, position: int) -> tuple[float, ...]:
        if "Москва" in text:
            return self._make_vector(0)
        if "Санкт-Петербург" in text or "Питер" in text:
            return self._make_vector(1)
        if "Кемерово" in text:
            return self._make_vector(2)
        return self._make_vector(min(position, self._embedding_dimension - 1))

    def _make_vector(self, hot_index: int) -> tuple[float, ...]:
        return tuple(1.0 if index == hot_index else 0.0 for index in range(self._embedding_dimension))


def build_config(max_document_chars: int = 50_000) -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        max_document_chars=max_document_chars,
        log_format="%(levelname)s:%(message)s",
    )


def build_russian_quiz_response(*, question_count: int = 2) -> StructuredGenerationResponse:
    questions = [
        {
            "question_id": f"q-{index + 1}",
            "prompt": f"Вопрос про Москву номер {index + 1}?",
            "options": [
                {"option_id": "opt-1", "text": "Москва"},
                {"option_id": "opt-2", "text": "Санкт-Петербург"},
            ],
            "correct_option_index": 0,
            "explanation": {"text": "Столицей России является Москва."},
        }
        for index in range(question_count)
    ]
    return StructuredGenerationResponse(
        model_name="local-model",
        content={
            "quiz_id": "quiz-rag-generated",
            "document_id": "ignored-by-normalizer",
            "title": "Квиз про Россию",
            "version": 1,
            "last_edited_at": "2026-04-25T20:00:00Z",
            "questions": questions,
        },
        raw_response={"id": "rag-resp-1", "choices": [{"index": 0}]},
    )


def upload_short_russian_document(client: TestClient) -> str:
    text = (
        "Москва — столица России и крупнейший по численности населения город страны.\n"
        "Санкт-Петербург — северная столица, культурный центр на Неве.\n"
        "Кемерово — административный центр Кузбасса, расположен в Сибири."
    )
    response = client.post(
        "/documents",
        content=text.encode("utf-8"),
        headers={"X-Filename": "russia.txt", "Content-Type": "text/plain"},
    )
    assert response.status_code == 201
    return response.json()["document_id"]


def upload_long_russian_document(client: TestClient, *, target_length: int) -> str:
    sentence = "Москва — столица России и крупнейший по численности населения город страны. "
    repetitions = (target_length // len(sentence)) + 1
    text = (sentence * repetitions)[:target_length]
    response = client.post(
        "/documents",
        content=text.encode("utf-8"),
        headers={"X-Filename": "long-russia.txt", "Content-Type": "text/plain"},
    )
    assert response.status_code == 201
    return response.json()["document_id"]


def build_rag_payload(*, generation_mode: str = "rag", question_count: int = 2) -> dict[str, object]:
    return {
        "question_count": question_count,
        "language": "ru",
        "difficulty": "medium",
        "quiz_type": "single_choice",
        "generation_mode": generation_mode,
    }


def test_rag_generation_endpoint_returns_rag_prompt_version_for_explicit_rag_mode(tmp_path) -> None:
    provider = StubRagApiProvider(structured_responses=[build_russian_quiz_response()])
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_short_russian_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_rag_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["prompt_version"] == "rag-v1"
    assert payload["model_name"] == "local-model"
    assert payload["quiz"]["document_id"] == document_id
    assert payload["quiz"]["title"] == "Квиз про Россию"
    assert payload["quiz"]["questions"][0]["options"][0]["text"] == "Москва"


def test_rag_generation_endpoint_calls_embed_for_chunks_and_query(tmp_path) -> None:
    provider = StubRagApiProvider(structured_responses=[build_russian_quiz_response()])
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_short_russian_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_rag_payload())

    assert response.status_code == 200
    assert len(provider.embedding_requests) == 2
    chunks_request = provider.embedding_requests[0]
    query_request = provider.embedding_requests[1]
    assert len(chunks_request.texts) >= 1
    assert all("Москва" in text or "Санкт-Петербург" in text or "Кемерово" in text for text in chunks_request.texts)
    assert query_request.texts == ("Создай 2 вопросов на языке ru, сложность medium, тип single_choice, опираясь только на содержание документа.",)


def test_rag_generation_endpoint_reuses_runtime_cache_and_preserves_cached_russian_context(tmp_path) -> None:
    provider = StubRagApiProvider(
        structured_responses=[
            build_russian_quiz_response(),
            build_russian_quiz_response(),
        ]
    )
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_short_russian_document(client)

    first_response = client.post(f"/documents/{document_id}/generate", json=build_rag_payload())
    cache_files = list((tmp_path / "rag_cache").glob("*.json"))
    second_response = client.post(f"/documents/{document_id}/generate", json=build_rag_payload())

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(cache_files) == 1
    raw_cache_payload = cache_files[0].read_text(encoding="utf-8")
    assert "Москва" in raw_cache_payload
    assert "Санкт-Петербург" in raw_cache_payload
    assert "Рњ" not in raw_cache_payload
    assert len(provider.embedding_requests) == 3
    first_chunk_request = provider.embedding_requests[0]
    first_query_request = provider.embedding_requests[1]
    second_query_request = provider.embedding_requests[2]
    assert len(first_chunk_request.texts) >= 1
    assert len(first_query_request.texts) == 1
    assert len(second_query_request.texts) == 1
    assert first_query_request.texts == second_query_request.texts
    assert len(provider.structured_requests) == 2
    second_structured_request = provider.structured_requests[1]
    assert "Retrieved context" in second_structured_request.user_prompt
    assert "Москва" in second_structured_request.user_prompt
    assert "Санкт-Петербург" in second_structured_request.user_prompt
    second_payload = second_response.json()
    assert second_payload["prompt_version"] == "rag-v1"
    assert second_payload["quiz"]["document_id"] == document_id
    assert second_payload["quiz"]["title"] == "Квиз про Россию"
    assert second_payload["quiz"]["questions"][0]["prompt"] == "Вопрос про Москву номер 1?"


def test_rag_generation_endpoint_passes_retrieved_context_into_structured_request(tmp_path) -> None:
    provider = StubRagApiProvider(structured_responses=[build_russian_quiz_response()])
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_short_russian_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_rag_payload())

    assert response.status_code == 200
    assert len(provider.structured_requests) == 1
    structured_request = provider.structured_requests[0]
    assert "Москва" in structured_request.user_prompt
    assert document_id in structured_request.user_prompt
    assert structured_request.schema_name == "quiz_payload"


def test_direct_request_promotes_to_rag_when_document_exceeds_threshold(tmp_path) -> None:
    provider = StubRagApiProvider(structured_responses=[build_russian_quiz_response()])
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_long_russian_document(client, target_length=DEFAULT_RAG_THRESHOLD_CHARS + 200)

    response = client.post(
        f"/documents/{document_id}/generate",
        json=build_rag_payload(generation_mode="direct"),
    )

    assert response.status_code == 200
    assert response.json()["prompt_version"] == "rag-v1"
    assert len(provider.embedding_requests) == 2


def test_direct_request_below_threshold_skips_rag_path(tmp_path) -> None:
    provider = StubRagApiProvider(structured_responses=[build_russian_quiz_response()])
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_short_russian_document(client)

    response = client.post(
        f"/documents/{document_id}/generate",
        json=build_rag_payload(generation_mode="direct"),
    )

    assert response.status_code == 200
    assert response.json()["prompt_version"] == "direct-v1"
    assert provider.embedding_requests == []


def test_generation_endpoint_rejects_single_question_regen_mode(tmp_path) -> None:
    provider = StubRagApiProvider(structured_responses=[])
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_short_russian_document(client)

    response = client.post(
        f"/documents/{document_id}/generate",
        json=build_rag_payload(generation_mode="single_question_regen"),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "unsupported_generation_mode"
    assert provider.structured_requests == []
    assert provider.embedding_requests == []


def test_rag_generation_endpoint_maps_oversized_document_to_413(tmp_path) -> None:
    provider = StubRagApiProvider(structured_responses=[])
    app = create_app(config=build_config(max_document_chars=10), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_short_russian_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_rag_payload())

    assert response.status_code == 413
    body = response.json()
    assert body["error"]["code"] == "document_too_large_for_generation"
    assert document_id in body["error"]["message"]
    assert provider.structured_requests == []


def test_rag_generation_endpoint_returns_russian_quiz_for_russian_document(tmp_path) -> None:
    provider = StubRagApiProvider(structured_responses=[build_russian_quiz_response(question_count=1)])
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_short_russian_document(client)

    response = client.post(
        f"/documents/{document_id}/generate",
        json=build_rag_payload(question_count=1),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["quiz"]["title"] == "Квиз про Россию"
    assert payload["quiz"]["document_id"] == document_id
    assert payload["quiz"]["questions"][0]["prompt"] == "Вопрос про Москву номер 1?"
    assert payload["quiz"]["questions"][0]["options"][0]["text"] == "Москва"
    assert payload["quiz"]["questions"][0]["explanation"] == {"text": "Столицей России является Москва."}
