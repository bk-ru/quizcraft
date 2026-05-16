from __future__ import annotations

import pytest

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import DocumentTooLargeForGenerationError
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.generation.orchestrator import DirectGenerationOrchestrator
from backend.app.generation.quality import GenerationQualityChecker
from backend.app.generation.request_builder import DirectGenerationRequestBuilder
from backend.app.prompts.registry import PromptRegistry
from backend.app.storage.documents import FileSystemDocumentRepository
from backend.app.storage.generation_results import FileSystemGenerationResultRepository
from backend.app.storage.quizzes import FileSystemQuizRepository


class StubProvider:
    """Детерминированный test double провайдера для потоков orchestrator."""

    def __init__(self, responses: list[StructuredGenerationResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[StructuredGenerationRequest] = []

    def healthcheck(self) -> ProviderHealthStatus:
        raise AssertionError("healthcheck should not be called in orchestrator tests")

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("provider was called more times than expected")
        return self._responses.pop(0)

    def embed(self, request):
        raise AssertionError("embed should not be called in orchestrator tests")


def build_document() -> DocumentRecord:
    return DocumentRecord(
        document_id="doc-1",
        filename="lecture.txt",
        media_type="text/plain",
        file_size_bytes=128,
        normalized_text="First source fact.\nSecond source fact.\nThird source fact.",
        metadata={"text_length": 56},
    )


def build_generation_request(question_count: int = 2) -> GenerationRequest:
    return GenerationRequest(
        question_count=question_count,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice",
        generation_mode=GenerationMode.DIRECT,
    )


def build_multi_type_generation_request(question_count: int = 6) -> GenerationRequest:
    return GenerationRequest(
        question_count=question_count,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice",
        generation_mode=GenerationMode.DIRECT,
        quiz_types=("single_choice", "true_false", "fill_blank", "short_answer", "matching"),
    )


def build_matching_only_generation_request(question_count: int = 1) -> GenerationRequest:
    return GenerationRequest(
        question_count=question_count,
        language="ru",
        difficulty="medium",
        quiz_type="matching",
        generation_mode=GenerationMode.DIRECT,
        quiz_types=("matching",),
    )


def build_payload(question_count: int = 2) -> dict[str, object]:
    questions = [
        {
            "question_id": f"q-{index + 1}",
            "prompt": f"Question {index + 1}?",
            "options": [
                {"option_id": "opt-1", "text": "Option A"},
                {"option_id": "opt-2", "text": "Option B"},
            ],
            "correct_option_index": 0,
            "explanation": {"text": f"Explanation {index + 1}."},
        }
        for index in range(question_count)
    ]
    return {
        "quiz_id": "quiz-generated",
        "document_id": "doc-1",
        "title": "Generated quiz",
        "version": 1,
        "last_edited_at": "2026-04-18T12:00:00Z",
        "questions": questions,
    }


def build_photosynthesis_document() -> DocumentRecord:
    text = (
        "Фотосинтез происходит в хлоропластах растений. Хлорофилл поглощает световую энергию. "
        "Световая стадия протекает на мембранах тилакоидов и требует света. "
        "Темновая стадия, или цикл Кальвина, происходит в строме хлоропласта и использует АТФ и НАДФН. "
        "Вода служит источником электронов и выделяет кислород. "
        "Углекислый газ используется для синтеза глюкозы. "
        "АТФ запасает энергию, а НАДФН переносит восстановительные эквиваленты."
    )
    return DocumentRecord(
        document_id="doc-1",
        filename="photosynthesis.txt",
        media_type="text/plain",
        file_size_bytes=len(text.encode("utf-8")),
        normalized_text=text,
        metadata={"text_length": len(text)},
    )


def build_photosynthesis_types_document() -> DocumentRecord:
    text = (
        "Кислородный фотосинтез характерен для высших растений и водорослей. "
        "Бескислородный фотосинтез встречается у некоторых бактерий. "
        "Световая стадия протекает на мембранах тилакоидов. "
        "Темновая стадия происходит в строме хлоропласта. "
        "Фотолиз воды приводит к образованию кислорода. "
        "Цикл Кальвина превращает углекислый газ в углеводы."
    )
    return DocumentRecord(
        document_id="doc-1",
        filename="photosynthesis-types.txt",
        media_type="text/plain",
        file_size_bytes=len(text.encode("utf-8")),
        normalized_text=text,
        metadata={"text_length": len(text)},
    )


def build_matching_pairs(count: int) -> list[dict[str, str]]:
    pairs = [
        {"left": "Световая стадия", "right": "Протекает на мембранах тилакоидов"},
        {"left": "Темновая стадия", "right": "Использует АТФ и НАДФН"},
        {"left": "Хлорофилл", "right": "Поглощает световую энергию"},
        {"left": "Вода", "right": "Источник электронов и кислорода"},
    ]
    return pairs[:count]


def build_bad_photosynthesis_type_matching_payload(*, question_count: int = 6) -> dict[str, object]:
    payload = build_payload(question_count=question_count)
    questions = list(payload["questions"])
    questions[-1] = {
        "question_id": "q-bad-matching",
        "question_type": "matching",
        "prompt": "Соотнесите тип фотосинтеза с группой организмов.",
        "options": [
            {"option_id": "A", "text": "Кислородный фотосинтез"},
            {"option_id": "B", "text": "Бескислородный фотосинтез"},
        ],
        "correct_option_index": None,
        "correct_answer": None,
        "matching_pairs": [
            {"left": "Высшие растения и водоросли", "right": "A"},
            {"left": "Некоторые бактерии", "right": "B"},
            {"left": "Цианобактерии (сине-зелёные водоросли)", "right": "A"},
            {"left": "Хемосинтезирующие бактерии", "right": "B"},
        ],
        "explanation": {"text": "Типы фотосинтеза сопоставлены с организмами."},
    }
    payload["questions"] = questions
    return payload


def build_grounded_photosynthesis_matching_payload(*, question_count: int = 6) -> dict[str, object]:
    payload = build_payload(question_count=question_count)
    questions = list(payload["questions"])
    questions[-1] = {
        "question_id": "q-good-matching",
        "question_type": "matching",
        "prompt": "Соотнесите понятия фотосинтеза с описаниями из текста.",
        "options": [],
        "correct_option_index": None,
        "correct_answer": None,
        "matching_pairs": [
            {"left": "Световая стадия", "right": "протекает на мембранах тилакоидов"},
            {"left": "Темновая стадия", "right": "происходит в строме хлоропласта"},
            {"left": "Фотолиз воды", "right": "приводит к образованию кислорода"},
            {"left": "Цикл Кальвина", "right": "превращает углекислый газ в углеводы"},
        ],
        "explanation": {"text": "Все пары явно указаны в тексте."},
    }
    payload["questions"] = questions
    return payload


def build_ungrounded_full_text_matching_payload(*, question_count: int = 1) -> dict[str, object]:
    payload = build_payload(question_count=question_count)
    questions = list(payload["questions"])
    questions[-1] = {
        "question_id": "q-ungrounded-matching",
        "question_type": "matching",
        "prompt": "Соотнесите тип фотосинтеза с группой организмов.",
        "options": [],
        "correct_option_index": None,
        "correct_answer": None,
        "matching_pairs": [
            {"left": "Высшие растения и водоросли", "right": "Кислородный фотосинтез"},
            {"left": "Некоторые бактерии", "right": "Бескислородный фотосинтез"},
            {"left": "Цианобактерии", "right": "Кислородный фотосинтез"},
            {"left": "Хемосинтезирующие бактерии", "right": "Бескислородный фотосинтез"},
        ],
        "explanation": {"text": "Типы фотосинтеза сопоставлены с организмами."},
    }
    payload["questions"] = questions
    return payload


def build_payload_with_matching_pair_count(pair_count: int, *, question_count: int = 6) -> dict[str, object]:
    payload = build_payload(question_count=question_count)
    questions = list(payload["questions"])
    questions[-1] = {
        "question_id": "q-matching",
        "question_type": "matching",
        "prompt": "Установите соответствие между объектами фотосинтеза и их ролью.",
        "options": [],
        "correct_option_index": None,
        "correct_answer": None,
        "matching_pairs": build_matching_pairs(pair_count),
        "explanation": {"text": "Соответствия взяты из описания фотосинтеза."},
    }
    payload["questions"] = questions
    return payload


def build_response(
    payload: dict[str, object],
    *,
    model_name: str = "local-model",
    response_id: str = "resp-1",
) -> StructuredGenerationResponse:
    return StructuredGenerationResponse(
        model_name=model_name,
        content=payload,
        raw_response={"id": response_id, "choices": [{"index": 0}]},
    )


def build_orchestrator(
    tmp_path,
    provider: StubProvider,
    *,
    max_document_chars: int | None = None,
    llm_repair_max_prompt_chars: int = 9_000,
) -> tuple[
    DirectGenerationOrchestrator,
    FileSystemDocumentRepository,
    FileSystemGenerationResultRepository,
]:
    document_repository = FileSystemDocumentRepository(tmp_path)
    quiz_repository = FileSystemQuizRepository(tmp_path)
    result_repository = FileSystemGenerationResultRepository(tmp_path)
    orchestrator = DirectGenerationOrchestrator(
        document_repository=document_repository,
        quiz_repository=quiz_repository,
        generation_result_repository=result_repository,
        request_builder=DirectGenerationRequestBuilder(prompt_registry=PromptRegistry),
        provider=provider,
        quality_checker=GenerationQualityChecker(),
        max_document_chars=max_document_chars,
        llm_repair_max_prompt_chars=llm_repair_max_prompt_chars,
    )
    return orchestrator, document_repository, result_repository


def test_direct_generation_orchestrator_persists_generation_result_on_success(tmp_path) -> None:
    provider = StubProvider([build_response(build_payload())])
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    result = orchestrator.generate("doc-1", build_generation_request())
    persisted = result_repository.get(result.quiz.quiz_id)

    assert result.prompt_version == "direct-v1"
    assert result.model_name == "local-model"
    assert result.quiz.version == 1
    assert result.quiz.last_edited_at.endswith("Z")
    assert persisted == result
    assert len(provider.requests) == 1


def test_direct_generation_orchestrator_uses_unique_server_quiz_id_for_repeated_provider_ids(tmp_path) -> None:
    provider = StubProvider(
        [
            build_response(build_payload(), response_id="resp-1"),
            build_response(build_payload(), response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    first_result = orchestrator.generate("doc-1", build_generation_request())
    second_result = orchestrator.generate("doc-1", build_generation_request())

    assert first_result.quiz.quiz_id.startswith("quiz-")
    assert second_result.quiz.quiz_id.startswith("quiz-")
    assert first_result.quiz.quiz_id != second_result.quiz.quiz_id
    assert first_result.quiz.quiz_id != "quiz-generated"
    assert second_result.quiz.quiz_id != "quiz-generated"
    assert result_repository.get(first_result.quiz.quiz_id) == first_result
    assert result_repository.get(second_result.quiz.quiz_id) == second_result


def test_direct_generation_orchestrator_uses_repair_prompt_after_quality_failure(tmp_path) -> None:
    provider = StubProvider(
        [
            build_response(build_payload(question_count=1), response_id="resp-1"),
            build_response(build_payload(question_count=2), response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    result = orchestrator.generate("doc-1", build_generation_request(question_count=2))

    assert result.prompt_version == "repair-v1"
    assert len(provider.requests) == 2
    assert "question count" in provider.requests[1].user_prompt
    assert "Original generation settings" in provider.requests[1].user_prompt
    assert "Allowed question type: single_choice" in provider.requests[1].user_prompt
    assert "Every question MUST use question_type=single_choice" in provider.requests[1].user_prompt
    assert "If the invalid JSON has fewer questions than requested" in provider.requests[1].user_prompt
    assert "Add new grounded questions from the source document/context" in provider.requests[1].user_prompt
    assert "\"questions\"" in provider.requests[1].user_prompt


def test_direct_generation_matching_error_uses_fallback_before_repair(tmp_path) -> None:
    provider = StubProvider(
        [
            build_response(build_payload_with_matching_pair_count(2), response_id="resp-1"),
        ]
    )
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_document())

    result = orchestrator.generate("doc-1", build_multi_type_generation_request())

    assert len(provider.requests) == 1
    assert result.prompt_version == "direct-v1"
    matching_question = result.quiz.questions[-1]
    assert matching_question.question_type == "short_answer"
    assert matching_question.matching_pairs == ()


def test_direct_generation_fallback_converts_invalid_matching_to_short_answer_after_failed_repair(tmp_path) -> None:
    provider = StubProvider(
        [
            build_response(build_payload_with_matching_pair_count(2), response_id="resp-1"),
            build_response(build_payload_with_matching_pair_count(2), response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_document())

    result = orchestrator.generate("doc-1", build_multi_type_generation_request())

    fallback_question = result.quiz.questions[-1]
    assert result.prompt_version == "direct-v1"
    assert fallback_question.question_type == "short_answer"
    assert fallback_question.matching_pairs == ()
    assert fallback_question.correct_answer is not None
    assert "Световая стадия" in fallback_question.correct_answer
    assert result_repository.get(result.quiz.quiz_id) == result


def test_direct_generation_matching_only_pair_count_failure_returns_partial_result_warning(tmp_path) -> None:
    invalid_payload = build_payload_with_matching_pair_count(2, question_count=1)
    provider = StubProvider(
        [
            build_response(invalid_payload, response_id="resp-1"),
            build_response(dict(invalid_payload), response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_document())

    result = orchestrator.generate("doc-1", build_matching_only_generation_request())

    assert len(result.quiz.questions) == 1
    assert result.quiz.questions[0].question_type == "matching"
    assert result.warnings
    assert "модель вернула 2 пары, нужно минимум 4" in result.warnings[0].message
    assert "недостаточно информации" not in result.warnings[0].message


def test_direct_generation_matching_only_ungrounded_failure_returns_partial_result_warning(tmp_path) -> None:
    invalid_payload = build_ungrounded_full_text_matching_payload()
    provider = StubProvider(
        [
            build_response(invalid_payload, response_id="resp-1"),
            build_response(dict(invalid_payload), response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_types_document())

    result = orchestrator.generate("doc-1", build_matching_only_generation_request())

    assert len(result.quiz.questions) == 1
    assert result.quiz.questions[0].question_type == "matching"
    assert result.warnings[0].message == (
        "Квиз показан с предупреждением: "
        "Вопрос на соответствие не прошёл проверку: пары должны быть явно основаны на тексте документа."
    )


def test_direct_generation_uses_repair_before_fallback_for_ungrounded_matching(tmp_path) -> None:
    provider = StubProvider(
        [
            build_response(build_ungrounded_full_text_matching_payload(question_count=5), response_id="resp-1"),
            build_response(build_grounded_photosynthesis_matching_payload(question_count=5), response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_types_document())

    result = orchestrator.generate("doc-1", build_multi_type_generation_request(question_count=5))

    assert len(provider.requests) == 2
    assert result.prompt_version == "repair-v1"
    assert result.warnings
    matching_question = result.quiz.questions[-1]
    assert matching_question.question_type == "matching"
    assert len(matching_question.matching_pairs) == 4
    assert "Source document/context:" in provider.requests[1].user_prompt
    assert result_repository.get(result.quiz.quiz_id) == result


def test_direct_generation_matching_with_options_uses_fallback_before_repair(tmp_path) -> None:
    provider = StubProvider(
        [
            build_response(build_bad_photosynthesis_type_matching_payload(), response_id="resp-1"),
        ]
    )
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_types_document())

    result = orchestrator.generate("doc-1", build_multi_type_generation_request())

    assert len(provider.requests) == 1
    matching_question = result.quiz.questions[-1]
    assert matching_question.question_type == "short_answer"
    assert matching_question.matching_pairs == ()


def test_direct_generation_fallback_does_not_save_ungrounded_matching_after_failed_repair(tmp_path) -> None:
    bad_payload = build_bad_photosynthesis_type_matching_payload()
    provider = StubProvider(
        [
            build_response(bad_payload, response_id="resp-1"),
            build_response(dict(bad_payload), response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_types_document())

    result = orchestrator.generate("doc-1", build_multi_type_generation_request())

    fallback_question = result.quiz.questions[-1]
    serialized = str(result.quiz.to_dict())
    assert fallback_question.question_type == "short_answer"
    assert fallback_question.matching_pairs == ()
    assert "Установите соответствие" not in fallback_question.prompt
    assert "Цианобактерии" not in serialized
    assert "Хемосинтезирующие бактерии" not in serialized
    assert result_repository.get(result.quiz.quiz_id) == result


def test_direct_generation_orchestrator_persists_partial_result_with_warning_after_repair_is_exhausted(tmp_path) -> None:
    invalid_payload = build_payload(question_count=1)
    provider = StubProvider(
        [
            build_response(invalid_payload, response_id="resp-1"),
            build_response(dict(invalid_payload), response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    result = orchestrator.generate("doc-1", build_generation_request(question_count=2))

    assert len(provider.requests) == 2
    assert len(result.quiz.questions) == 1
    assert result.warnings
    assert result.warnings[0].code == "generation_quality_error"
    assert "Модель вернула 1 вопрос вместо запрошенных 2" in result.warnings[0].message
    assert "уменьшите количество вопросов" in result.warnings[0].recommendations[0]
    assert result_repository.get(result.quiz.quiz_id) == result


def test_direct_generation_orchestrator_trims_extra_generated_questions(tmp_path) -> None:
    provider = StubProvider([build_response(build_payload(question_count=6), response_id="resp-1")])
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(
        DocumentRecord(
            document_id="doc-1",
            filename="photosynthesis.txt",
            media_type="text/plain",
            file_size_bytes=256,
            normalized_text=(
                "\u0424\u043e\u0442\u043e\u0441\u0438\u043d\u0442\u0435\u0437 \u043f\u0440\u0435\u043e\u0431\u0440\u0430\u0437\u0443\u0435\u0442 "
                "\u0441\u0432\u0435\u0442 \u0432 \u0445\u0438\u043c\u0438\u0447\u0435\u0441\u043a\u0443\u044e "
                "\u044d\u043d\u0435\u0440\u0433\u0438\u044e."
            ),
            metadata={"text_length": 53},
        )
    )

    result = orchestrator.generate("doc-1", build_generation_request(question_count=5))
    persisted = result_repository.get(result.quiz.quiz_id)

    assert len(provider.requests) == 1
    assert len(result.quiz.questions) == 5
    assert len(persisted.quiz.questions) == 5


def test_direct_generation_orchestrator_preserves_russian_quiz_fields(tmp_path) -> None:
    provider = StubProvider(
        [
            build_response(
                {
                    "quiz_id": "quiz-ru",
                    "document_id": "ignored-by-normalizer",
                    "title": "Квиз по документу",
                    "version": 1,
                    "last_edited_at": "2026-04-18T12:00:00Z",
                    "questions": [
                        {
                            "question_id": "q-1",
                            "prompt": "Что говорится в первом факте?",
                            "options": [
                                {"option_id": "opt-1", "text": "Первый факт"},
                                {"option_id": "opt-2", "text": "Второй факт"},
                            ],
                            "correct_option_index": 0,
                            "explanation": {"text": "Первый факт указан в документе."},
                        },
                        {
                            "question_id": "q-2",
                            "prompt": "Сколько фактов перечислено?",
                            "options": [
                                {"option_id": "opt-1", "text": "Два"},
                                {"option_id": "opt-2", "text": "Пять"},
                            ],
                            "correct_option_index": 0,
                            "explanation": {"text": "В документе два факта."},
                        },
                    ],
                }
            )
        ]
    )
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(
        DocumentRecord(
            document_id="doc-1",
            filename="lecture.txt",
            media_type="text/plain",
            file_size_bytes=64,
            normalized_text="Первый факт.\nВторой факт.",
            metadata={"text_length": 25},
        )
    )

    result = orchestrator.generate("doc-1", build_generation_request(question_count=2))
    persisted = result_repository.get(result.quiz.quiz_id)

    assert result.quiz.title == "Квиз по документу"
    assert result.quiz.questions[0].prompt == "Что говорится в первом факте?"
    assert result.quiz.questions[0].options[0].text == "Первый факт"
    assert result.quiz.questions[0].explanation is not None
    assert result.quiz.questions[0].explanation.text == "Первый факт указан в документе."
    assert persisted == result


def test_direct_generation_orchestrator_rejects_documents_exceeding_max_chars(tmp_path) -> None:
    provider = StubProvider([])
    orchestrator, document_repository, _ = build_orchestrator(
        tmp_path, provider, max_document_chars=20
    )
    document_repository.save(
        DocumentRecord(
            document_id="doc-big",
            filename="lecture.txt",
            media_type="text/plain",
            file_size_bytes=128,
            normalized_text="Очень длинный русский документ для проверки лимита.",
            metadata={"text_length": 50},
        )
    )

    with pytest.raises(DocumentTooLargeForGenerationError) as error_info:
        orchestrator.generate("doc-big", build_generation_request())

    assert error_info.value.code == "document_too_large_for_generation"
    assert "doc-big" in error_info.value.message
    assert provider.requests == []


def test_direct_generation_orchestrator_accepts_document_within_limit(tmp_path) -> None:
    provider = StubProvider([build_response(build_payload())])
    orchestrator, document_repository, _ = build_orchestrator(
        tmp_path, provider, max_document_chars=10_000
    )
    document_repository.save(build_document())

    result = orchestrator.generate("doc-1", build_generation_request())

    assert result.quiz.quiz_id.startswith("quiz-")
    assert result.quiz.quiz_id != "quiz-generated"
    assert len(provider.requests) == 1


def test_direct_generation_grounded_matching_passes_without_repair(tmp_path) -> None:
    provider = StubProvider(
        [build_response(build_grounded_photosynthesis_matching_payload(), response_id="resp-1")]
    )
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_types_document())

    result = orchestrator.generate("doc-1", build_multi_type_generation_request())

    matching_question = result.quiz.questions[-1]
    assert result.prompt_version == "direct-v1"
    assert len(provider.requests) == 1
    assert matching_question.question_type == "matching"
    assert matching_question.options == ()
    assert len(matching_question.matching_pairs) == 4
    assert all(pair.right not in {"A", "B", "1", "2"} for pair in matching_question.matching_pairs)
    assert result_repository.get(result.quiz.quiz_id) == result


def test_direct_generation_orchestrator_rejects_non_positive_document_limit(tmp_path) -> None:
    with pytest.raises(ValueError, match="max_document_chars"):
        build_orchestrator(tmp_path, StubProvider([]), max_document_chars=0)


def _build_short_repair_payload(*, question_count: int = 1) -> dict[str, object]:
    questions = [
        {
            "question_id": "q-repair-1",
            "prompt": "Что такое фотосинтез?",
            "options": [
                {"option_id": "opt-1", "text": "Процесс"},
                {"option_id": "opt-2", "text": "Вещество"},
            ],
            "correct_option_index": 0,
            "explanation": {"text": "Фотосинтез — это процесс."},
        }
    ][:question_count]
    return {
        "quiz_id": "quiz-repair",
        "document_id": "doc-1",
        "title": "Repaired quiz",
        "version": 1,
        "last_edited_at": "2026-04-18T12:00:00Z",
        "questions": questions,
    }


def test_repair_returns_too_few_questions_fallback_from_original(tmp_path) -> None:
    bad_payload = build_bad_photosynthesis_type_matching_payload()
    short_repair_payload = _build_short_repair_payload(question_count=1)
    provider = StubProvider(
        [
            build_response(bad_payload, response_id="resp-1"),
            build_response(short_repair_payload, response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_types_document())

    result = orchestrator.generate("doc-1", build_multi_type_generation_request())

    assert len(result.quiz.questions) == 6
    fallback_question = result.quiz.questions[-1]
    assert fallback_question.question_type == "short_answer"
    serialized = str(result.quiz.to_dict())
    assert "Цианобактерии" not in serialized
    assert "Хемосинтезирующие бактерии" not in serialized
    assert result_repository.get(result.quiz.quiz_id) == result


def test_matching_error_fallback_preserves_question_count(tmp_path) -> None:
    bad_payload = build_bad_photosynthesis_type_matching_payload()
    provider = StubProvider(
        [
            build_response(bad_payload, response_id="resp-1"),
        ]
    )
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_types_document())

    result = orchestrator.generate("doc-1", build_multi_type_generation_request())

    assert len(result.quiz.questions) == 6
    matching_question = result.quiz.questions[-1]
    assert matching_question.question_type == "short_answer"
    assert matching_question.matching_pairs == ()
    assert result_repository.get(result.quiz.quiz_id) == result


def test_fallback_from_original_quiz_preserves_other_questions(tmp_path) -> None:
    bad_payload = build_bad_photosynthesis_type_matching_payload()
    short_repair_payload = _build_short_repair_payload(question_count=1)
    provider = StubProvider(
        [
            build_response(bad_payload, response_id="resp-1"),
            build_response(short_repair_payload, response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_types_document())

    result = orchestrator.generate("doc-1", build_multi_type_generation_request())

    non_matching_questions = result.quiz.questions[:-1]
    assert all(q.question_type != "matching" for q in non_matching_questions)
    assert len(non_matching_questions) == 5


def test_good_photosynthesis_matching_passes_quality_check(tmp_path) -> None:
    good_payload = build_grounded_photosynthesis_matching_payload()
    provider = StubProvider(
        [build_response(good_payload, response_id="resp-1")]
    )
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_types_document())

    result = orchestrator.generate("doc-1", build_multi_type_generation_request())

    matching_question = result.quiz.questions[-1]
    assert matching_question.question_type == "matching"
    assert matching_question.options == ()
    assert len(matching_question.matching_pairs) == 4


def test_ungrounded_external_terms_still_rejected_or_fallbacked(tmp_path) -> None:
    bad_payload = build_bad_photosynthesis_type_matching_payload()
    short_repair_payload = _build_short_repair_payload(question_count=1)
    provider = StubProvider(
        [
            build_response(bad_payload, response_id="resp-1"),
            build_response(short_repair_payload, response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_types_document())

    result = orchestrator.generate("doc-1", build_multi_type_generation_request())

    serialized = str(result.quiz.to_dict())
    assert "Цианобактерии" not in serialized
    assert "Хемосинтезирующие бактерии" not in serialized


def test_matching_error_fallback_priority_no_llm_call(tmp_path) -> None:
    bad_payload = build_bad_photosynthesis_type_matching_payload()
    provider = StubProvider(
        [
            build_response(bad_payload, response_id="resp-1"),
        ]
    )
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_photosynthesis_types_document())

    result = orchestrator.generate("doc-1", build_multi_type_generation_request())

    assert len(provider.requests) == 1
    assert result.prompt_version == "direct-v1"
    fallback_question = result.quiz.questions[-1]
    assert fallback_question.question_type == "short_answer"


def test_prompt_budget_guard_returns_partial_result_warning_when_repair_is_too_large(tmp_path) -> None:
    invalid_payload = build_payload(question_count=1)
    provider = StubProvider(
        [
            build_response(invalid_payload, response_id="resp-1"),
            build_response(build_payload(), response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, _ = build_orchestrator(
        tmp_path, provider, llm_repair_max_prompt_chars=10
    )
    document_repository.save(build_document())

    result = orchestrator.generate("doc-1", build_generation_request())

    assert len(provider.requests) == 1
    assert len(result.quiz.questions) == 1
    assert result.warnings


def test_non_matching_error_still_uses_repair_within_budget(tmp_path) -> None:
    bad_payload = build_payload(question_count=1)
    good_payload = build_payload()
    provider = StubProvider(
        [
            build_response(bad_payload, response_id="resp-1"),
            build_response(good_payload, response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    result = orchestrator.generate("doc-1", build_generation_request())

    assert len(provider.requests) == 2
    assert result.prompt_version == "repair-v1"
    assert len(result.quiz.questions) == 2
    assert result_repository.get(result.quiz.quiz_id) == result
