"""Prompt helpers for requested quiz question types."""

from __future__ import annotations

from backend.app.domain.models import GenerationRequest

QUESTION_TYPE_RULES = {
    "single_choice": (
        "single_choice: set question_type to single_choice, provide exactly four options, "
        "and set correct_option_index to the zero-based index of the correct option. "
        "All four options must be the same semantic category, such as all years, all names, "
        "all terms, all places, or all organizations. "
        "Avoid meta-options such as \"not specified\", \"all of the above\", or \"none of the above\". "
        "Do not include correct_answer or matching_pairs."
    ),
    "true_false": (
        "true_false: set question_type to true_false, provide two options, "
        "and set correct_option_index to the zero-based index of the correct option. "
        "The statement must be directly verifiable from the document/context. "
        "Avoid ambiguous or compound statements. "
        "Do not include correct_answer or matching_pairs."
    ),
    "fill_blank": (
        "fill_blank: set question_type to fill_blank, omit options, and provide a non-empty correct_answer. "
        "The blank must replace a short phrase explicitly present in the source. "
        "correct_answer must be the exact missing phrase or the minimal source phrase needed to fill the blank. "
        "Do not include options, correct_option_index, or matching_pairs. "
        "Use a blank-style prompt with a missing word/phrase."
    ),
    "short_answer": (
        "short_answer: set question_type to short_answer, omit options, and provide a non-empty correct_answer. "
        "Ask a specific answerable question. "
        "correct_answer must directly answer the prompt. "
        "Avoid vague prompts like \"What fact is stated in the text?\". "
        "Do not ask for one semantic category while providing an answer from another category. "
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
        "  Use only the source document/context for left and right values.\n"
        "  Prefer one coherent relationship type, such as term→definition, stage→location, process→result, "
        "factor→effect, source→output, organization→role, or field→description.\n"
        "  Do not mix unrelated categories in one matching question.\n"
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
