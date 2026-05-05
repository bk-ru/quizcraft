"""Prompt helpers for requested quiz question types."""

from __future__ import annotations

from backend.app.domain.models import GenerationRequest

QUESTION_TYPE_RULES = {
    "single_choice": (
        "single_choice: set question_type to single_choice, provide exactly four options, "
        "and set correct_option_index to the zero-based index of the correct option."
    ),
    "true_false": (
        "true_false: set question_type to true_false, provide two options, "
        "and set correct_option_index to the zero-based index of the correct option."
    ),
    "fill_blank": (
        "fill_blank: set question_type to fill_blank, omit options, and provide a non-empty correct_answer."
    ),
    "short_answer": (
        "short_answer: set question_type to short_answer, omit options, and provide a non-empty correct_answer."
    ),
    "matching": (
        "matching: set question_type to matching and provide at least four matching_pairs with left and right text."
    ),
}


def allowed_question_types(generation_request: GenerationRequest) -> tuple[str, ...]:
    """Return the explicit question types requested by the caller."""

    return tuple(generation_request.quiz_types or (generation_request.quiz_type,))


def render_question_type_policy(generation_request: GenerationRequest) -> str:
    """Render a strict prompt policy for single-type and multi-type requests."""

    allowed_types = allowed_question_types(generation_request)
    allowed_label = ", ".join(allowed_types)
    if len(allowed_types) == 1:
        return (
            f"Allowed question type: {allowed_label}. Every question MUST use question_type={allowed_label}. "
            "Do not create true_false, fill_blank, short_answer, or matching questions unless that exact type is allowed."
        )
    return (
        f"Allowed question types: {allowed_label}. Every question MUST use only one of these question types. "
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
