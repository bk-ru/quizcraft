"""Prompt helpers for requested quiz question types."""

from __future__ import annotations

from backend.app.domain.models import GenerationRequest

QUESTION_TYPE_RULES = {
    "single_choice": (
        "single_choice: set question_type to single_choice, provide exactly four options, "
        "and set correct_option_index to the zero-based index of the correct option. "
        "All options must share one semantic category: years, names, terms, places, or organizations. "
        "Avoid meta-options such as \"not specified\", \"all of the above\", or \"none of the above\". "
        "Avoid negative questions such as \"which is NOT mentioned\" unless necessary. "
        "Prefer asking about directly stated facts. "
        "Do not include correct_answer or matching_pairs."
    ),
    "true_false": (
        "true_false: set question_type to true_false. "
        "Provide exactly two options: option 1 must be 'Верно' (or 'Да'), option 2 must be 'Неверно' (or 'Нет'). "
        "The prompt must contain ONE clear statement directly verifiable from the document. "
        "Do NOT provide two different statements in options; options are only for True/False labels. "
        "Set correct_option_index to 0 if the statement is true, or 1 if the statement is false. "
        "Do not include correct_answer or matching_pairs."
    ),
    "fill_blank": (
        "fill_blank: set question_type to fill_blank, omit options, and provide a non-empty correct_answer. "
        "The blank must replace a short phrase explicitly present in the source; "
        "correct_answer must be the exact missing phrase or minimal source phrase. "
        "Do not include options, correct_option_index, or matching_pairs. "
        "Use a blank-style prompt with a missing word/phrase."
    ),
    "short_answer": (
        "short_answer: set question_type to short_answer, omit options, and provide a non-empty correct_answer. "
        "Ask a specific answerable question; correct_answer must directly answer the prompt. "
        "Avoid vague prompts like \"What fact is stated in the text?\". "
        "Do not ask for one semantic category while answering with another. "
        "If the document says \"снимки, полученные со спутников, самолётов и беспилотников\", "
        "ask for \"источники снимков\" or \"платформы получения снимков\", not "
        "\"типы изображений\" or \"типы данных\". "
        "Do not include options, correct_option_index, or matching_pairs. "
        "Ask a direct answerable question, not a matching/list placeholder."
    ),
    "matching": (
        "matching: set question_type to matching and provide 4 or more pairs in matching_pairs. "
        "Create a correspondence task, not comparison or short answer. "
        "Do not use `options`. "
        "Do not put IDs like \"A\", \"B\", \"1\", \"2\" into matching_pairs.right; "
        "matching_pairs.right must contain the full matching text. "
        "Use only the source document/context for left and right values. "
        "Prefer one coherent relationship type, such as term→definition, stage→location, "
        "process→result, factor→effect, or field→description. "
        "Do not mix unrelated categories in one matching question. "
        "Never create a matching question with fewer than 4 pairs. "
        "If matching is required by the selected type policy, create exactly one matching question with 4 or more pairs before repeating any other question type. "
        "If matching is not required by the selected type policy, use another suitable allowed type."
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
            f"{exact_count_rule} Selected question type: {allowed_label}. "
            f"This type is REQUIRED. Every question MUST use question_type={allowed_label}. "
            "Do not create true_false, fill_blank, short_answer, or matching questions unless that exact type is allowed."
        )
    base_policy = (
        f"{exact_count_rule} Selected question types: {allowed_label}. "
        "ALL selected question types are REQUIRED. "
        "Use only these question types. "
    )
    if generation_request.question_count == len(allowed_types):
        return (
            base_policy +
            "Because question_count equals the number of selected types: "
            "Return exactly one question for each selected question type. "
            "Do not omit any selected type. "
            "Do not repeat any type. "
            "Each selected type must appear exactly once."
        )
    if generation_request.question_count > len(allowed_types):
        has_matching = "matching" in allowed_types
        matching_clause = ""
        if has_matching:
            matching_clause = (
                "matching is REQUIRED because it was selected. "
                "Include at least one matching question with 4 or more matching_pairs. "
                "Create the required matching question BEFORE repeating any other selected type. "
            )
        return (
            base_policy +
            "Because question_count is greater than the number of selected types: "
            "Use EVERY selected question type at least once. "
            "Do not omit any selected type. "
            + matching_clause +
            f"Then repeat suitable selected types until exactly {generation_request.question_count} questions are returned. "
            "Prefer repeating types that are easier to ground in the source text."
        )
    return (
        base_policy +
        "Because question_count is less than the number of selected types: "
        "Use the most suitable subset of selected types. "
        "Prefer structurally reliable types in this order: "
        "single_choice, true_false, fill_blank, short_answer, matching."
    )


def render_question_type_rules(generation_request: GenerationRequest) -> str:
    """Render schema-level rules for the requested question types."""

    rules = [
        QUESTION_TYPE_RULES[question_type]
        for question_type in allowed_question_types(generation_request)
        if question_type in QUESTION_TYPE_RULES
    ]
    return "\n".join(f"- {rule}" for rule in rules)
