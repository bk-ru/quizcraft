from backend.app.generation.question_types import QUESTION_TYPE_RULES


def test_matching_question_type_rule_requires_four_or_more_pairs() -> None:
    rule = QUESTION_TYPE_RULES["matching"]

    assert "4 or more pairs" in rule
    assert "Never create a matching question with fewer than 4 pairs" in rule
    assert "term→definition" in rule
    assert "Do not use `options`" in rule
    assert "matching_pairs.right must contain the full matching text" in rule
    assert "not explicitly present in the source document/context" in rule


def test_non_matching_question_type_rules_forbid_foreign_fields() -> None:
    assert "Do not include correct_answer or matching_pairs" in QUESTION_TYPE_RULES["single_choice"]
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
