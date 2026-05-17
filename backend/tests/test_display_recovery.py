from dataclasses import replace
from pathlib import Path

from backend.app.core.modes import GenerationMode
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import MatchingPair
from backend.app.domain.models import Option
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.domain.validation import validate_quiz
from backend.app.generation.display_recovery import build_deterministic_short_answer_question
from backend.app.generation.display_recovery import recover_displayable_quiz


PHOTOSYNTHESIS_SOURCE = (
    "Фотосинтез происходит главным образом в листьях. "
    "В клетках листа находятся хлоропласты. "
    "Хлорофилл поглощает прежде всего красные и синие лучи солнечного спектра, а зелёные отражает. "
    "Углекислый газ поступает из воздуха через устьица. Через устьица также выходит кислород и испаряется водяной пар. "
    "Световая стадия протекает на мембранах тилакоидов внутри хлоропластов и требует света. "
    "Темновая стадия, или цикл Кальвина, происходит в строме хлоропласта. "
    "Общее уравнение фотосинтеза часто записывают так: 6CO₂ + 6H₂O + световая энергия → C₆H₁₂O₆ + 6O₂."
)

GENERATION_PRODUCTION_FILES = (
    Path("backend/app/generation/display_recovery.py"),
    Path("backend/app/generation/question_types.py"),
    Path("backend/app/generation/matching_fallback.py"),
)


def build_generation_request(question_count: int = 3) -> GenerationRequest:
    return GenerationRequest(
        question_count=question_count,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice,true_false,fill_blank,short_answer,matching",
        generation_mode=GenerationMode.DIRECT,
        quiz_types=("single_choice", "true_false", "fill_blank", "short_answer", "matching"),
    )


def build_quiz(*questions: Question) -> Quiz:
    return Quiz(
        quiz_id="quiz-display",
        document_id="doc-display",
        title="Квиз по фотосинтезу",
        version=1,
        last_edited_at="2026-05-16T18:00:00Z",
        questions=questions,
    )


def build_valid_choice(question_id: str = "q1") -> Question:
    return Question(
        question_id=question_id,
        prompt="Где у растений главным образом происходит фотосинтез?",
        question_type="single_choice",
        options=(
            Option(option_id="0", text="В корнях"),
            Option(option_id="1", text="В листьях"),
        ),
        correct_option_index=1,
    )


def test_generation_recovery_has_no_domain_specific_fallback_text() -> None:
    forbidden_fragments = (
        "общее уравнение фотосинтеза",
        "световая стадия фотосинтеза",
        "темновая стадия фотосинтеза",
        "хлоропласт",
        "тилакоид",
        "строма",
        "устьица",
        "хлорофилл",
        "углекислый газ",
    )
    production_source = "\n".join(path.read_text(encoding="utf-8").casefold() for path in GENERATION_PRODUCTION_FILES)

    assert all(fragment not in production_source for fragment in forbidden_fragments)


def build_grounded_pairs() -> tuple[MatchingPair, ...]:
    return (
        MatchingPair(left="Световая стадия", right="протекает на мембранах тилакоидов"),
        MatchingPair(left="Темновая стадия", right="происходит в строме хлоропласта"),
        MatchingPair(left="Устьица", right="через устьица выходит кислород"),
        MatchingPair(left="Хлорофилл", right="поглощает красные и синие лучи"),
    )


def test_display_recovery_strips_or_replaces_mixed_type_question() -> None:
    mixed_question = Question(
        question_id="q3",
        prompt="Соотнесите понятия с описаниями из текста.",
        question_type="fill_blank",
        correct_answer="листе",
        matching_pairs=build_grounded_pairs(),
    )

    recovered, warnings = recover_displayable_quiz(
        build_quiz(mixed_question),
        build_generation_request(question_count=1),
        PHOTOSYNTHESIS_SOURCE,
    )

    validate_quiz(recovered)
    assert recovered.questions[0].question_id == "q3"
    assert recovered.questions[0].question_type == "matching"
    assert recovered.questions[0].correct_answer is None
    assert len(recovered.questions[0].matching_pairs) == 4
    assert any(warning.code == "recovered_mixed_question_fields" for warning in warnings)


def test_display_recovery_replaces_placeholder_question() -> None:
    placeholder = Question(
        question_id="q4",
        prompt="Какие соответствия между понятиями описаны в тексте?",
        question_type="short_answer",
        correct_answer="Ответ должен опираться только на явно описанные в тексте соответствия.",
    )

    recovered, warnings = recover_displayable_quiz(
        build_quiz(placeholder),
        build_generation_request(question_count=1),
        PHOTOSYNTHESIS_SOURCE,
    )

    validate_quiz(recovered)
    question = recovered.questions[0]
    assert question.question_id == "q4"
    assert question.question_type == "short_answer"
    assert "соответствия между понятиями" not in question.prompt.casefold()
    assert "Ответ должен опираться" not in question.correct_answer
    assert any(warning.code == "replaced_placeholder_question" for warning in warnings)


def test_display_recovery_replaces_matching_prompt_in_short_answer() -> None:
    matching_as_answer = Question(
        question_id="q-fallback",
        prompt="Какие соответствия между этими понятиями описаны в тексте: Устьица, Фотолиз воды?",
        question_type="short_answer",
        correct_answer=(
            "Устьица — проводят углекислый газ в лист; "
            "Фотолиз воды — расщепление молекул воды под действием света"
        ),
    )

    recovered, warnings = recover_displayable_quiz(
        build_quiz(matching_as_answer),
        build_generation_request(question_count=1),
        PHOTOSYNTHESIS_SOURCE,
    )

    validate_quiz(recovered)
    question = recovered.questions[0]
    assert question.question_id == "q-fallback"
    assert question.question_type == "short_answer"
    assert "соответствия" not in question.prompt.casefold()
    assert "Устьица —" not in question.correct_answer
    assert any(warning.code == "replaced_placeholder_question" for warning in warnings)


def test_display_recovery_returns_structurally_valid_quiz_with_warnings() -> None:
    mixed_choice = replace(
        build_valid_choice(),
        correct_answer="В листьях",
        matching_pairs=(MatchingPair(left="Лист", right="фотосинтез"),),
    )

    recovered, warnings = recover_displayable_quiz(
        build_quiz(mixed_choice),
        build_generation_request(question_count=1),
        PHOTOSYNTHESIS_SOURCE,
    )

    validate_quiz(recovered)
    assert recovered.questions[0].question_type == "single_choice"
    assert recovered.questions[0].correct_answer is None
    assert recovered.questions[0].matching_pairs == ()
    assert any(warning.code == "recovered_mixed_question_fields" for warning in warnings)


def test_display_recovery_can_return_partial_quiz_without_placeholders() -> None:
    placeholder = Question(
        question_id="q4",
        prompt="Какие соответствия между понятиями описаны в тексте?",
        question_type="short_answer",
        correct_answer="Ответ должен опираться только на явно описанные в тексте соответствия.",
    )

    recovered, warnings = recover_displayable_quiz(
        build_quiz(build_valid_choice(), placeholder),
        build_generation_request(question_count=2),
        "Коротко.",
    )

    validate_quiz(recovered)
    assert len(recovered.questions) == 1
    assert all("соответствия между понятиями" not in question.prompt.casefold() for question in recovered.questions)
    assert any(warning.code == "display_recovery_partial_quiz" for warning in warnings)


def test_bad_photosynthesis_case_is_display_safe() -> None:
    bad_fill = Question(
        question_id="q3",
        prompt="В какой органоиде листа находятся хлоропласты?",
        question_type="fill_blank",
        correct_answer="листе",
        matching_pairs=build_grounded_pairs(),
    )
    placeholder = Question(
        question_id="q4",
        prompt="Какие соответствия между понятиями описаны в тексте?",
        question_type="short_answer",
        correct_answer="Ответ должен опираться только на явно описанные в тексте соответствия.",
    )

    recovered, warnings = recover_displayable_quiz(
        build_quiz(build_valid_choice(), bad_fill, placeholder),
        build_generation_request(question_count=3),
        PHOTOSYNTHESIS_SOURCE,
    )

    validate_quiz(recovered)
    assert warnings
    assert len(recovered.questions) == 3
    for question in recovered.questions:
        if question.question_type != "matching":
            assert question.matching_pairs == ()
        assert "Ответ должен опираться" != (question.correct_answer or "")
        assert "соответствия между понятиями" not in question.prompt.casefold()


def test_deterministic_short_answer_builder_uses_source_sentence() -> None:
    source_text = "Российские исследователи описали новый метод очистки воды. Метод снижает количество примесей."

    question = build_deterministic_short_answer_question(
        source_text,
        question_id="q-safe",
        language="ru",
        used_prompts=set(),
    )

    assert question is not None
    assert question.question_type == "short_answer"
    assert question.question_id == "q-safe"
    assert question.correct_answer == "Российские исследователи описали новый метод очистки воды."
    assert question.matching_pairs == ()
