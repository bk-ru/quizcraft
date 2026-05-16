"""Regression tests for LM Studio context overflow fix and matching fallback strategy."""

from __future__ import annotations

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import MatchingPair
from backend.app.domain.models import Option
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.core.modes import GenerationMode
from backend.app.generation.matching_fallback import (
    REPAIR_SOURCE_TEXT_MAX_CHARS,
    build_repair_source_excerpt,
    estimate_repair_prompt_chars,
    fallback_invalid_matching_questions,
    is_matching_error,
    _extract_matching_terms,
)
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


def _make_quiz_with_matching_question(
    pairs: list[tuple[str, str]],
    *,
    options: tuple[Option, ...] = (),
    correct_option_index: int | None = None,
    correct_answer: str | None = None,
) -> Quiz:
    matching_pairs = tuple(MatchingPair(left=left, right=right) for left, right in pairs)
    question = Question(
        question_id="q-match",
        prompt="Соотнесите понятия",
        options=options,
        correct_option_index=correct_option_index,
        explanation=None,
        question_type="matching",
        correct_answer=correct_answer,
        matching_pairs=matching_pairs,
    )
    return Quiz(
        quiz_id="quiz-test",
        document_id="doc-test",
        title="Test Quiz",
        version=1,
        last_edited_at="2024-01-01T00:00:00Z",
        questions=(question,),
    )


def _multi_type_request() -> GenerationRequest:
    return GenerationRequest(
        question_count=1,
        language="ru",
        difficulty="medium",
        quiz_type="matching",
        generation_mode=GenerationMode.DIRECT,
        quiz_types=("single_choice", "short_answer", "matching"),
    )


class TestMatchingFallbackKeepsMatchingWhenFourGroundedPairsRemain:
    def test_removes_one_ungrounded_keeps_matching(self) -> None:
        source = (
            "Фотосинтез — процесс преобразования энергии.\n\n"
            "Световая стадия протекает на мембранах тилакоидов.\n\n"
            "Темновая стадия происходит в строме хлоропласта.\n\n"
            "Хлорофилл поглощает свет.\n\n"
            "Фотолиз воды расщепляет молекулы воды."
        )
        pairs = [
            ("Световая стадия", "протекает на мембранах тилакоидов"),
            ("Темновая стадия", "происходит в строме хлоропласта"),
            ("Хлорофилл", "поглощает свет"),
            ("Фотолиз воды", "расщепляет молекулы воды"),
            ("Цианобактерии", "фотосинтезируют без хлоропластов"),
        ]
        quiz = _make_quiz_with_matching_question(pairs)
        result = fallback_invalid_matching_questions(quiz, _multi_type_request(), source_text=source)
        assert result is not None
        fallback_quiz, actions = result
        fallback_q = fallback_quiz.questions[0]
        assert fallback_q.question_type == "matching"
        assert len(fallback_q.matching_pairs) == 4
        assert fallback_q.options == ()
        assert fallback_q.correct_option_index is None
        assert fallback_q.correct_answer is None
        assert actions[0].action == "cleaned_matching"
        assert actions[0].original_pair_count == 5
        assert actions[0].grounded_pair_count == 4
        assert actions[0].removed_pair_count == 1
        assert actions[0].final_question_type == "matching"


class TestMatchingFallbackDoesNotReclassifyMatching:
    def test_three_grounded_pairs_do_not_become_short_answer(self) -> None:
        source = (
            "Световая стадия фотосинтеза протекает на мембранах тилакоидов.\n\n"
            "Темновая стадия происходит в строме хлоропласта.\n\n"
            "Фотосинтез высших растений сопровождается выделением кислорода."
        )
        pairs = [
            ("Световая стадия фотосинтеза", "протекает на мембранах тилакоидов"),
            ("Темновая стадия", "происходит в строме хлоропласта"),
            ("Фотосинтез высших растений", "сопровождается выделением кислорода"),
        ]
        quiz = _make_quiz_with_matching_question(pairs)
        result = fallback_invalid_matching_questions(quiz, _multi_type_request(), source_text=source)
        assert result is None


    def test_single_grounded_pair_does_not_become_short_answer(self) -> None:
        source = "Световая стадия фотосинтеза — фотолиз воды и образование АТФ/НАДФН."
        pairs = [
            ("Световая стадия", "Фотолиз воды и образование АТФ/НАДФН"),
        ]
        quiz = _make_quiz_with_matching_question(pairs)
        result = fallback_invalid_matching_questions(quiz, _multi_type_request(), source_text=source)
        assert result is None


class TestMatchingFallbackDoesNotUseCompareWord:
    def test_russian_prompt_no_compare(self) -> None:
        source = "Хлорофилл поглощает свет.\n\nХлоропласты содержат хлорофилл."
        pairs = [
            ("Хлорофилл", "поглощает свет"),
            ("Хлоропласты", "содержат хлорофилл"),
        ]
        quiz = _make_quiz_with_matching_question(pairs)
        result = fallback_invalid_matching_questions(quiz, _multi_type_request(), source_text=source)
        assert result is None

    def test_english_prompt_no_compare(self) -> None:
        source = "Chlorophyll absorbs light. Chloroplasts contain chlorophyll."
        pairs = [
            ("Chlorophyll", "absorbs light"),
            ("Chloroplasts", "contain chlorophyll"),
        ]
        quiz = _make_quiz_with_matching_question(pairs)
        request = GenerationRequest(
            question_count=1, language="en", difficulty="medium",
            quiz_type="matching", generation_mode=GenerationMode.DIRECT,
            quiz_types=("single_choice", "short_answer", "matching"),
        )
        result = fallback_invalid_matching_questions(quiz, request, source_text=source)
        assert result is None


class TestMatchingFallbackWithNoGroundedPairs:
    def test_no_grounded_pairs_does_not_create_placeholder_question(self) -> None:
        source = "Фотосинтез происходит в листьях и связан с хлорофиллом."
        pairs = [
            ("Азот", "поступает через лёгкие"),
            ("Белок", "отражает зелёный свет"),
            ("Митохондрия", "создаёт крахмал"),
            ("Корень", "выделяет кислород ночью"),
        ]
        quiz = _make_quiz_with_matching_question(pairs)

        result = fallback_invalid_matching_questions(quiz, _multi_type_request(), source_text=source)

        assert result is None


class TestMatchingFallbackReplacesSymbolicOptionsAndKeepsMatching:
    def test_symbolic_right_resolved_and_matching_kept(self) -> None:
        source = (
            "Фотосинтез — процесс преобразования энергии.\n\n"
            "Световая стадия протекает на мембранах тилакоидов.\n\n"
            "Темновая стадия происходит в строме хлоропласта.\n\n"
            "Хлорофилл поглощает свет.\n\n"
            "Фотолиз воды расщепляет молекулы воды."
        )
        options = (
            Option(option_id="A", text="протекает на мембранах тилакоидов"),
            Option(option_id="B", text="происходит в строме хлоропласта"),
            Option(option_id="C", text="поглощает свет"),
            Option(option_id="D", text="расщепляет молекулы воды"),
        )
        pairs = [
            ("Световая стадия", "A"),
            ("Темновая стадия", "B"),
            ("Хлорофилл", "C"),
            ("Фотолиз воды", "D"),
        ]
        quiz = _make_quiz_with_matching_question(pairs, options=options)
        result = fallback_invalid_matching_questions(quiz, _multi_type_request(), source_text=source)
        assert result is not None
        fallback_quiz, actions = result
        fallback_q = fallback_quiz.questions[0]
        assert fallback_q.question_type == "matching"
        assert len(fallback_q.matching_pairs) == 4
        assert fallback_q.options == ()
        for pair in fallback_q.matching_pairs:
            assert pair.right not in ("A", "B", "C", "D")
        assert actions[0].action == "cleaned_matching"
