from backend.app.generation.question_types import QUESTION_TYPE_RULES


def test_matching_question_type_rule_requires_four_or_more_pairs() -> None:
    rule = QUESTION_TYPE_RULES["matching"]

    assert "4 or more pairs" in rule
    assert "Never create a matching question with fewer than 4 pairs" in rule
    assert "term→definition" in rule
    assert "Do not use `options`" in rule
    assert "matching_pairs.right must contain the full matching text" in rule
    assert "not explicitly present in the source document/context" in rule
