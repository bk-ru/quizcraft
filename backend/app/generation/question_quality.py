"""Lightweight methodical quality checks for generated questions."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from dataclasses import replace

from backend.app.domain.errors import GenerationQualityError
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz

RECOVERED_QUESTION_PROMPT_WARNING_CODE = "recovered_question_prompt"
RECOVERED_QUESTION_PROMPT_WARNING_MESSAGE = (
    "Один вопрос был автоматически переформулирован для согласованности с ответами."
)
METHODICAL_QUALITY_ERROR_MESSAGE = "generated quiz contains methodically inconsistent question"

_BAD_CHLOROPLAST_PROMPT = "bad_chloroplast_single_choice"
_MIXED_MATCHING_PROMPT = "mixed_matching_prompt"
_CHLOROPLAST_PROMPT = "Какой органоид содержит зелёный пигмент хлорофилл?"
_RU_GENERIC_MATCHING_PROMPT = "Соотнесите понятие и его характеристику:"
_EN_GENERIC_MATCHING_PROMPT = "Match each concept with its description:"

_NARROW_PROMPT_CATEGORY_FRAGMENTS: dict[str, tuple[str, ...]] = {
    "organelle": ("органоид", "organelle"),
    "stage": ("стад", "этап", "stage", "phase"),
    "factor": ("фактор", "factor"),
    "process": ("процесс", "process"),
}
_LEFT_CATEGORY_FRAGMENTS: dict[str, tuple[str, ...]] = {
    "organelle": (
        "хлоропласт",
        "митохондри",
        "ядро",
        "вакуол",
        "рибосом",
        "chloroplast",
        "mitochondri",
        "nucleus",
        "vacuole",
        "ribosome",
    ),
    "stage": ("стад", "этап", "stage", "phase"),
    "factor": (
        "освещ",
        "температур",
        "недостат",
        "концентрац",
        "влажн",
        "минеральн",
        "light",
        "temperature",
        "shortage",
        "concentration",
        "humidity",
    ),
    "process": (
        "фотолиз",
        "синтез",
        "дыхан",
        "испар",
        "поглощ",
        "выдел",
        "process",
        "synthesis",
        "respiration",
        "evaporation",
    ),
    "structure": ("тилакоид", "устьиц", "stoma", "stomata", "thylakoid"),
}


@dataclass(frozen=True, slots=True)
class QuestionQualityIssue:
    """A recoverable or rejectable methodical quality issue."""

    code: str
    message: str


def ensure_methodical_quality(quiz: Quiz) -> None:
    """Raise when a quiz contains a known methodically inconsistent question."""

    issue = next(iter_question_quality_issues(quiz), None)
    if issue is not None:
        raise GenerationQualityError(issue.message)


def iter_question_quality_issues(quiz: Quiz) -> Iterator[QuestionQualityIssue]:
    """Yield known methodical issues for generated questions."""

    for question in quiz.questions:
        issue = find_question_quality_issue(question)
        if issue is not None:
            yield issue


def find_question_quality_issue(question: Question) -> QuestionQualityIssue | None:
    """Return a known methodical issue for one question, if present."""

    if _is_bad_chloroplast_single_choice(question):
        return QuestionQualityIssue(
            code=_BAD_CHLOROPLAST_PROMPT,
            message=METHODICAL_QUALITY_ERROR_MESSAGE,
        )
    if _matching_prompt_needs_generalization(question):
        return QuestionQualityIssue(
            code=_MIXED_MATCHING_PROMPT,
            message=METHODICAL_QUALITY_ERROR_MESSAGE,
        )
    return None


def recover_question_quality(question: Question, language: str) -> tuple[Question, QuestionQualityIssue | None]:
    """Recover known methodical issues without changing answer semantics."""

    issue = find_question_quality_issue(question)
    if issue is None:
        return question, None
    if issue.code == _BAD_CHLOROPLAST_PROMPT:
        return replace(question, prompt=_CHLOROPLAST_PROMPT), issue
    if issue.code == _MIXED_MATCHING_PROMPT:
        return replace(question, prompt=_generic_matching_prompt(language)), issue
    return question, issue


def _is_bad_chloroplast_single_choice(question: Question) -> bool:
    if question.question_type != "single_choice":
        return False
    prompt = _normalize_text(question.prompt)
    if not ("органоид" in prompt and "наход" in prompt and "хлоропласт" in prompt):
        return False
    if question.correct_option_index is None:
        return False
    if question.correct_option_index < 0 or question.correct_option_index >= len(question.options):
        return False
    return "хлоропласт" in _normalize_text(question.options[question.correct_option_index].text)


def _matching_prompt_needs_generalization(question: Question) -> bool:
    if question.question_type != "matching":
        return False
    prompt_category = _prompt_category(question.prompt)
    if prompt_category is None:
        return False
    categories = tuple(
        category
        for category in (_left_value_category(pair.left) for pair in question.matching_pairs)
        if category is not None
    )
    if not categories:
        return False
    known_categories = set(categories)
    return any(category != prompt_category for category in known_categories) and (
        prompt_category in known_categories or len(known_categories) > 1
    )


def _prompt_category(prompt: str) -> str | None:
    normalized = _normalize_text(prompt)
    for category, fragments in _NARROW_PROMPT_CATEGORY_FRAGMENTS.items():
        if any(fragment in normalized for fragment in fragments):
            return category
    return None


def _left_value_category(value: str) -> str | None:
    normalized = _normalize_text(value)
    for category, fragments in _LEFT_CATEGORY_FRAGMENTS.items():
        if any(fragment in normalized for fragment in fragments):
            return category
    return None


def _generic_matching_prompt(language: str) -> str:
    if language.strip().casefold().startswith("ru"):
        return _RU_GENERIC_MATCHING_PROMPT
    return _EN_GENERIC_MATCHING_PROMPT


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().replace("ё", "е").split())
