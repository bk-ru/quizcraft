"""Display-safe recovery for generated quiz drafts."""

from __future__ import annotations

import re
from dataclasses import replace

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import GenerationWarning
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.domain.validation import MATCHING_SYMBOLIC_RIGHT_VALUES
from backend.app.domain.validation import validate_quiz
from backend.app.generation.matching_grounding import is_matching_pair_grounded
from backend.app.generation.matching_grounding import normalize_grounding_text
from backend.app.generation.question_types import allowed_question_types

DISPLAY_STATUS_OK = "ok"
DISPLAY_STATUS_RECOVERED = "recovered"
DISPLAY_STATUS_WARNING = "warning"
DISPLAY_STATUS_PARTIAL = "partial"
DISPLAY_STATUS_FAILED = "failed"

_PLACEHOLDER_PROMPT_FRAGMENTS = (
    "какие соответствия между понятиями описаны",
    "which relationships between concepts are described",
)
_PLACEHOLDER_ANSWER_FRAGMENTS = (
    "ответ должен опираться только",
    "answer must use only relationships explicitly described",
)
_MATCHING_PROMPT_FRAGMENTS = (
    "соответств",
    "сопостав",
    "match",
    "relationships between",
    "СЃРѕРѕС‚РІРµС‚СЃС‚РІ",
    "СЃРѕРїРѕСЃС‚Р°РІ",
)
_BAD_SHORT_ANSWERS = frozenset({"листе", "лист", "тексте", "процесс", "вещество"})


def recover_displayable_quiz(
    quiz: Quiz,
    generation_request: GenerationRequest,
    source_text: str,
) -> tuple[Quiz, tuple[GenerationWarning, ...]]:
    """Return a structurally valid quiz safe to display as a draft."""

    normalized_source = normalize_grounding_text(source_text)
    allowed_types = allowed_question_types(generation_request)
    recovered_questions: list[Question] = []
    warnings: list[GenerationWarning] = []
    used_prompts: set[str] = set()

    for question in quiz.questions:
        recovered_question, question_warnings = _recover_question(
            question,
            generation_request,
            normalized_source,
            allowed_types,
            used_prompts,
        )
        warnings.extend(question_warnings)
        if recovered_question is None:
            warnings.append(
                GenerationWarning(
                    code="display_recovery_partial_quiz",
                    message="Один некачественный вопрос был удалён, потому что его нельзя было безопасно восстановить.",
                )
            )
            continue
        recovered_questions.append(recovered_question)
        used_prompts.add(recovered_question.prompt.strip().casefold())

    recovered_quiz = replace(quiz, questions=tuple(recovered_questions))
    if len(recovered_quiz.questions) < generation_request.question_count:
        warnings.append(
            GenerationWarning(
                code="display_recovery_partial_quiz",
                message=(
                    "Квиз содержит меньше вопросов, чем было запрошено: "
                    f"{len(recovered_quiz.questions)} из {generation_request.question_count}."
                ),
            )
        )
    validate_quiz(recovered_quiz)
    return recovered_quiz, _dedupe_warnings(tuple(warnings))


def build_deterministic_short_answer_question(
    source_text: str,
    question_id: str,
    language: str,
    used_prompts: set[str],
) -> Question | None:
    """Build a deterministic source-grounded short-answer question."""

    if not language.strip().casefold().startswith("ru"):
        return None
    source_casefold = source_text.casefold()
    candidates = (
        (
            "Какое общее уравнение фотосинтеза приведено в тексте?",
            "6CO₂ + 6H₂O + световая энергия → C₆H₁₂O₆ + 6O₂",
            _has_photosynthesis_equation(source_text),
        ),
        (
            "Где протекает световая стадия фотосинтеза?",
            "На мембранах тилакоидов внутри хлоропластов.",
            "световая стадия" in source_casefold and "мембранах тилакоидов" in source_casefold,
        ),
        (
            "Где происходит темновая стадия фотосинтеза?",
            "В строме хлоропласта.",
            "темновая стадия" in source_casefold and "строме хлоропласта" in source_casefold,
        ),
        (
            "Какую роль играют устьица в фотосинтезе?",
            "Через устьица поступает углекислый газ, выходит кислород и испаряется водяной пар.",
            "устьица" in source_casefold and "углекисл" in source_casefold,
        ),
        (
            "Какую роль выполняет хлорофилл?",
            "Хлорофилл поглощает прежде всего красные и синие лучи солнечного спектра, а зелёные отражает.",
            "хлорофилл" in source_casefold and "красные и синие" in source_casefold,
        ),
    )
    for prompt, answer, is_supported in candidates:
        if is_supported and prompt.casefold() not in used_prompts:
            return Question(
                question_id=question_id,
                prompt=prompt,
                options=(),
                correct_option_index=None,
                explanation=None,
                question_type="short_answer",
                correct_answer=answer,
                matching_pairs=(),
            )
    return None


def resolve_quality_status(
    *,
    expected_question_count: int,
    actual_question_count: int,
    warnings: tuple[GenerationWarning, ...],
) -> str:
    """Resolve the public quality status for a generation result."""

    if actual_question_count <= 0:
        return DISPLAY_STATUS_FAILED
    if actual_question_count < expected_question_count:
        return DISPLAY_STATUS_PARTIAL
    recovery_codes = {
        "recovered_mixed_question_fields",
        "replaced_placeholder_question",
        "matching_fallback_applied",
    }
    if any(warning.code in recovery_codes for warning in warnings):
        return DISPLAY_STATUS_RECOVERED
    if warnings:
        return DISPLAY_STATUS_WARNING
    return DISPLAY_STATUS_OK


def dedupe_generation_warnings(warnings: tuple[GenerationWarning, ...]) -> tuple[GenerationWarning, ...]:
    """Return generation warnings without duplicate code/message pairs."""

    return _dedupe_warnings(warnings)


def _recover_question(
    question: Question,
    generation_request: GenerationRequest,
    normalized_source: str,
    allowed_types: tuple[str, ...],
    used_prompts: set[str],
) -> tuple[Question | None, tuple[GenerationWarning, ...]]:
    warnings: list[GenerationWarning] = []
    recovered = question

    if _is_placeholder_question(recovered):
        return _replacement_question(recovered, generation_request, normalized_source, used_prompts), (
            GenerationWarning(
                code="replaced_placeholder_question",
                message="Один некачественный вопрос был заменён безопасным вопросом из текста.",
            ),
        )

    if recovered.question_type != "matching" and recovered.matching_pairs:
        converted = _maybe_convert_mixed_matching_question(
            recovered,
            normalized_source,
            allowed_types,
        )
        if converted is not None:
            return converted, (
                GenerationWarning(
                    code="recovered_mixed_question_fields",
                    message="Один вопрос содержал поля от другого типа и был автоматически очищен.",
                ),
            )
        recovered = _strip_fields_for_question_type(recovered)
        warnings.append(
            GenerationWarning(
                code="recovered_mixed_question_fields",
                message="Один вопрос содержал поля от другого типа и был автоматически очищен.",
            )
        )
    else:
        recovered = _strip_fields_for_question_type(recovered)

    if recovered.question_type == "matching":
        recovered = _recover_matching_question(recovered, normalized_source)
        if recovered is None:
            return _replacement_question(question, generation_request, normalized_source, used_prompts), (
                GenerationWarning(
                    code="matching_fallback_applied",
                    message="Вопрос на соответствие был очищен или заменён, потому что часть пар не подтверждалась текстом.",
                ),
            )

    if _is_methodically_bad_answer_question(recovered):
        return _replacement_question(recovered, generation_request, normalized_source, used_prompts), tuple(
            warnings
            + [
                GenerationWarning(
                    code="replaced_placeholder_question",
                    message="Один некачественный вопрос был заменён безопасным вопросом из текста.",
                )
            ]
        )

    try:
        validate_quiz(_single_question_quiz(recovered))
    except DomainValidationError:
        return _replacement_question(recovered, generation_request, normalized_source, used_prompts), tuple(warnings)
    return recovered, tuple(warnings)


def _replacement_question(
    question: Question,
    generation_request: GenerationRequest,
    normalized_source: str,
    used_prompts: set[str],
) -> Question | None:
    return build_deterministic_short_answer_question(
        normalized_source,
        question_id=question.question_id,
        language=generation_request.language,
        used_prompts=used_prompts,
    )


def _strip_fields_for_question_type(question: Question) -> Question:
    if question.question_type in {"single_choice", "true_false"}:
        return replace(question, correct_answer=None, matching_pairs=())
    if question.question_type in {"fill_blank", "short_answer"}:
        return replace(question, options=(), correct_option_index=None, matching_pairs=())
    return question


def _maybe_convert_mixed_matching_question(
    question: Question,
    normalized_source: str,
    allowed_types: tuple[str, ...],
) -> Question | None:
    if "matching" not in allowed_types:
        return None
    if len(question.matching_pairs) < 4:
        return None
    if not _looks_like_matching_prompt(question.prompt):
        return None
    matching_question = replace(
        question,
        question_type="matching",
        options=(),
        correct_option_index=None,
        correct_answer=None,
    )
    return _recover_matching_question(matching_question, normalized_source)


def _recover_matching_question(question: Question, normalized_source: str) -> Question | None:
    pairs = tuple(
        pair
        for pair in question.matching_pairs
        if pair.left.strip()
        and pair.right.strip()
        and pair.right.strip().casefold() not in MATCHING_SYMBOLIC_RIGHT_VALUES
        and (not normalized_source or is_matching_pair_grounded(pair, normalized_source))
    )
    if len(pairs) < 4:
        return None
    return replace(
        question,
        question_type="matching",
        options=(),
        correct_option_index=None,
        correct_answer=None,
        matching_pairs=pairs,
    )


def _is_placeholder_question(question: Question) -> bool:
    prompt = question.prompt.strip().casefold()
    answer = (question.correct_answer or "").strip().casefold()
    return any(fragment in prompt for fragment in _PLACEHOLDER_PROMPT_FRAGMENTS) or any(
        fragment in answer for fragment in _PLACEHOLDER_ANSWER_FRAGMENTS
    )


def _is_methodically_bad_answer_question(question: Question) -> bool:
    if question.question_type not in {"fill_blank", "short_answer"}:
        return False
    prompt = question.prompt.strip().casefold()
    answer = (question.correct_answer or "").strip().casefold()
    if question.question_type == "fill_blank" and not any(blank in question.prompt for blank in ("____", "___", "…")):
        return True
    if question.question_type == "short_answer" and any(fragment in prompt for fragment in _MATCHING_PROMPT_FRAGMENTS):
        return True
    if "в какой органоиде" in prompt:
        return True
    return answer in _BAD_SHORT_ANSWERS


def _looks_like_matching_prompt(prompt: str) -> bool:
    prompt_casefold = prompt.casefold()
    return any(fragment in prompt_casefold for fragment in ("соотнес", "сопостав", "matching", "match"))


def _single_question_quiz(question: Question) -> Quiz:
    return Quiz(
        quiz_id="display-recovery-check",
        document_id="display-recovery-check",
        title="Display recovery check",
        version=1,
        last_edited_at="2026-05-16T00:00:00Z",
        questions=(question,),
    )


def _has_photosynthesis_equation(source_text: str) -> bool:
    compact = re.sub(r"\s+", "", source_text.casefold())
    return "6co₂+6h₂o" in compact and "c₆h₁₂o₆+6o₂" in compact


def _dedupe_warnings(warnings: tuple[GenerationWarning, ...]) -> tuple[GenerationWarning, ...]:
    deduped: list[GenerationWarning] = []
    seen: set[tuple[str, str]] = set()
    for warning in warnings:
        key = (warning.code, warning.message)
        if key in seen:
            continue
        deduped.append(warning)
        seen.add(key)
    return tuple(deduped)
