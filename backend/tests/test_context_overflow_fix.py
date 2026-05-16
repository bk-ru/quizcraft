"""Regression tests for LM Studio context overflow fix."""

from __future__ import annotations

from backend.app.generation.matching_fallback import (
    REPAIR_SOURCE_TEXT_MAX_CHARS,
    build_repair_source_excerpt,
    estimate_repair_prompt_chars,
    is_matching_error,
    _extract_matching_terms,
)
from backend.app.domain.errors import DomainValidationError
from backend.app.llm.lm_studio import _is_context_overflow_error


class TestIsMatchingError:
    def test_groundedness_error(self) -> None:
        error = DomainValidationError(
            "Вопрос на соответствие не прошёл проверку: пары должны быть явно основаны на тексте документа."
        )
        assert is_matching_error(error) is True

    def test_pair_count_error(self) -> None:
        error = DomainValidationError("matching question must have at least four pairs")
        assert is_matching_error(error) is True

    def test_options_error(self) -> None:
        error = DomainValidationError("matching question must not include options")
        assert is_matching_error(error) is True

    def test_non_matching_error(self) -> None:
        error = DomainValidationError("question count does not match")
        assert is_matching_error(error) is False

    def test_russian_groundedness_error(self) -> None:
        error = DomainValidationError(
            "Вопрос на соответствие не прошёл проверку: пары должны быть явно основаны на тексте документа."
        )
        assert is_matching_error(error) is True


class TestContextOverflowDetection:
    def test_n_keep_n_ctx_pattern(self) -> None:
        body = '{"error":{"message":"n_keep: 4160 >= n_ctx: 4096"}}'
        assert _is_context_overflow_error(body) is True

    def test_context_overflow_text(self) -> None:
        body = "context overflow: too many tokens"
        assert _is_context_overflow_error(body) is True

    def test_unrelated_400_error(self) -> None:
        body = '{"error":{"message":"invalid request format"}}'
        assert _is_context_overflow_error(body) is False

    def test_empty_body(self) -> None:
        assert _is_context_overflow_error("") is False


class TestBuildRepairSourceExcerpt:
    def test_extracts_relevant_paragraphs(self) -> None:
        source = (
            "Фотосинтез — процесс преобразования световой энергии.\n\n"
            "Хлорофилл поглощает световую энергию.\n\n"
            "Дыхание — процесс окисления глюкозы."
        )
        payload = {
            "questions": [
                {
                    "question_type": "matching",
                    "matching_pairs": [
                        {"left": "Хлорофилл", "right": "поглощает световую энергию"},
                    ],
                }
            ]
        }
        excerpt = build_repair_source_excerpt(source, payload)
        assert "Хлорофилл" in excerpt
        assert "Дыхание" not in excerpt

    def test_fallback_to_start_when_no_terms_match(self) -> None:
        source = "Первый параграф.\n\nВторой параграф."
        payload = {
            "questions": [
                {
                    "question_type": "matching",
                    "matching_pairs": [
                        {"left": "Несуществующий термин", "right": "Значение"},
                    ],
                }
            ]
        }
        excerpt = build_repair_source_excerpt(source, payload)
        assert excerpt.startswith("Первый")

    def test_respects_max_chars(self) -> None:
        long_para = "Абвгд " * 500
        source = f"{long_para}\n\n{long_para}"
        payload = {
            "questions": [
                {
                    "question_type": "matching",
                    "matching_pairs": [
                        {"left": "Абвгд", "right": "значение"},
                    ],
                }
            ]
        }
        excerpt = build_repair_source_excerpt(source, payload, max_chars=200)
        assert len(excerpt) <= 200

    def test_russian_cyrillic_terms(self) -> None:
        source = (
            "Фотосинтез происходит в хлоропластах.\n\n"
            "Митохондрии отвечают за дыхание."
        )
        payload = {
            "questions": [
                {
                    "question_type": "matching",
                    "matching_pairs": [
                        {"left": "Хлоропласты", "right": "фотосинтез"},
                    ],
                }
            ]
        }
        excerpt = build_repair_source_excerpt(source, payload)
        assert "хлоропласт" in excerpt.casefold()
        assert "Митохондрии" not in excerpt

    def test_no_matching_questions_returns_truncated_source(self) -> None:
        source = "Некоторый текст документа."
        payload = {"questions": [{"question_type": "single_choice"}]}
        excerpt = build_repair_source_excerpt(source, payload)
        assert excerpt == "Некоторый текст документа."


class TestExtractMatchingTerms:
    def test_extracts_left_and_right(self) -> None:
        payload = {
            "questions": [
                {
                    "question_type": "matching",
                    "matching_pairs": [
                        {"left": "Хлорофилл", "right": "зелёный пигмент"},
                        {"left": "Фотосинтез", "right": "преобразование энергии"},
                    ],
                }
            ]
        }
        terms = _extract_matching_terms(payload)
        assert "Хлорофилл" in terms
        assert "зелёный пигмент" in terms
        assert "Фотосинтез" in terms

    def test_skips_non_matching_questions(self) -> None:
        payload = {
            "questions": [
                {"question_type": "single_choice"},
                {
                    "question_type": "matching",
                    "matching_pairs": [{"left": "Термин", "right": "Значение"}],
                },
            ]
        }
        terms = _extract_matching_terms(payload)
        assert terms == ["Термин", "Значение"]


class TestEstimateRepairPromptChars:
    def test_sums_component_lengths(self) -> None:
        result = estimate_repair_prompt_chars(
            system_prompt="system",
            user_prompt="user prompt",
            schema={"type": "object"},
        )
        assert result == len("system") + len("user prompt") + len('{"type": "object"}')


class TestRepairSourceTextMaxChars:
    def test_max_chars_reduced(self) -> None:
        assert REPAIR_SOURCE_TEXT_MAX_CHARS == 2_500
