"""Prompt helpers for requested quiz question types."""

from __future__ import annotations

from backend.app.domain.models import GenerationRequest

QUESTION_TYPE_RULES = {
    "single_choice": (
        "single_choice: set question_type to single_choice, provide exactly four options, "
        "and set correct_option_index to the zero-based index of the correct option. "
        "Do not include correct_answer or matching_pairs."
    ),
    "true_false": (
        "true_false: set question_type to true_false, provide two options, "
        "and set correct_option_index to the zero-based index of the correct option. "
        "Do not include correct_answer or matching_pairs."
    ),
    "fill_blank": (
        "fill_blank: set question_type to fill_blank, omit options, and provide a non-empty correct_answer. "
        "Do not include options, correct_option_index, or matching_pairs. "
        "Use a blank-style prompt with a missing word/phrase."
    ),
    "short_answer": (
        "short_answer: set question_type to short_answer, omit options, and provide a non-empty correct_answer. "
        "Do not include options, correct_option_index, or matching_pairs. "
        "Ask a direct answerable question, not a matching/list placeholder."
    ),
    "matching": (
        "matching: set question_type to matching and provide at least four matching_pairs.\n"
        "  For matching questions:\n"
        "  Create a table-style correspondence task, not a comparison or short-answer task.\n"
        "  Do not use `options`.\n"
        "  Do not put option IDs such as \"A\", \"B\", \"1\", \"2\" into matching_pairs.right.\n"
        "  matching_pairs.right must contain the full matching text.\n"
        "  A valid matching question MUST contain 4 or more pairs.\n"
        "  All pairs in one matching question must use one coherent relationship type only.\n"
        "  Each pair must be based on an explicit relationship from the document.\n"
        "  Every left and right value must be directly supported by the source document/context.\n"
        "  Do not introduce entities, organisms, terms, or examples that are not explicitly present in the source document/context.\n"
        "  Good coherent relationship types: term→definition, stage→location, process→result, factor→effect, "
        "substance→role, organoid→function.\n"
        "  Do not mix unrelated categories in one matching question, such as stage→location, gas→source, and product→role together.\n"
        "  Prefer short source-grounded values copied or minimally rephrased from the document.\n"
        "  Example format: Concept A→description copied from the source; "
        "Concept B→role copied from the source; Concept C→result copied from the source; "
        "Concept D→location copied from the source.\n"
        "  Never create a matching question with fewer than 4 pairs.\n"
        "  If you cannot create 4 pairs, do not create a matching question; use another allowed question type."
    ),
}


def allowed_question_types(generation_request: GenerationRequest) -> tuple[str, ...]:
    """Return the explicit question types requested by the caller."""

    return tuple(generation_request.quiz_types or (generation_request.quiz_type,))


def render_question_type_policy(generation_request: GenerationRequest) -> str:
    """Render a strict prompt policy for single-type and multi-type requests."""

    allowed_types = allowed_question_types(generation_request)
    allowed_label = ", ".join(allowed_types)
    exact_count_rule = f"Return exactly {generation_request.question_count} questions."
    if len(allowed_types) == 1:
        return (
            f"{exact_count_rule} Allowed question type: {allowed_label}. "
            f"Every question MUST use question_type={allowed_label}. "
            "Do not create true_false, fill_blank, short_answer, or matching questions unless that exact type is allowed."
        )
    return (
        f"{exact_count_rule} Allowed question types: {allowed_label}. "
        "Every question MUST use only one of these question types. "
        "Do not stop after using each allowed question type once; "
        f"repeat suitable allowed question types until exactly {generation_request.question_count} questions are returned. "
        "Distribute questions across the allowed types when the source content supports them."
    )


def render_question_type_rules(generation_request: GenerationRequest) -> str:
    """Render schema-level rules for the requested question types."""

    rules = [
        QUESTION_TYPE_RULES[question_type]
        for question_type in allowed_question_types(generation_request)
        if question_type in QUESTION_TYPE_RULES
    ]
    return "\n".join(f"- {rule}" for rule in rules)
