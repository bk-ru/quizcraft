from backend.app.core.modes import GenerationMode
from backend.app.domain.models import GenerationRequest
from backend.app.generation.question_types import QUESTION_TYPE_RULES
from backend.app.generation.question_types import render_question_type_policy


def test_matching_question_type_rule_requires_four_or_more_pairs() -> None:
    rule = QUESTION_TYPE_RULES["matching"]

    assert "4 or more pairs" in rule
    assert "Never create a matching question with fewer than 4 pairs" in rule
    assert "term→definition" in rule
    assert "Do not use `options`" in rule
    assert "matching_pairs.right must contain the full matching text" in rule
    assert "Use only the source document/context" in rule
    assert "Prefer one coherent relationship type" in rule


def test_non_matching_question_type_rules_forbid_foreign_fields() -> None:
    assert "Do not include correct_answer or matching_pairs" in QUESTION_TYPE_RULES["single_choice"]
    assert "Avoid negative questions" in QUESTION_TYPE_RULES["single_choice"]
    assert "Prefer asking about directly stated facts" in QUESTION_TYPE_RULES["single_choice"]
    assert "Do not include correct_answer or matching_pairs" in QUESTION_TYPE_RULES["true_false"]
    assert (
        "Do not include options, correct_option_index, or matching_pairs"
        in QUESTION_TYPE_RULES["fill_blank"]
    )
    assert "Use a blank-style prompt with a missing word/phrase" in QUESTION_TYPE_RULES["fill_blank"]
    assert (
        "Do not include options, correct_option_index, or matching_pairs"
        in QUESTION_TYPE_RULES["short_answer"]
    )
    assert "Ask a direct answerable question" in QUESTION_TYPE_RULES["short_answer"]
    assert "источники снимков" in QUESTION_TYPE_RULES["short_answer"]
    assert "типы данных" in QUESTION_TYPE_RULES["short_answer"]


def build_request(question_count: int) -> GenerationRequest:
    return GenerationRequest(
        question_count=question_count,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice,true_false,fill_blank,short_answer,matching",
        generation_mode=GenerationMode.DIRECT,
        quiz_types=("single_choice", "true_false", "fill_blank", "short_answer", "matching"),
    )


def test_multi_type_policy_requires_one_question_per_type_when_counts_match() -> None:
    policy = render_question_type_policy(build_request(question_count=5))

    assert "Return exactly one question for each allowed question type" in policy
    assert "Do not replace an allowed type with a repeated type" in policy
    assert "include exactly one matching question" in policy


def test_multi_type_policy_uses_every_type_before_repeating_when_count_is_larger() -> None:
    policy = render_question_type_policy(build_request(question_count=7))

    assert "Use every allowed question type at least once" in policy
    assert "Then repeat suitable allowed types until exactly 7 questions are returned" in policy


def test_multi_type_policy_prefers_reliable_subset_when_count_is_smaller() -> None:
    policy = render_question_type_policy(build_request(question_count=3))

    assert "Use the most suitable subset of allowed types" in policy
    assert "single_choice, true_false, fill_blank, short_answer, matching" in policy
