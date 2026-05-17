from backend.app.domain.models import GenerationWarning
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.generation.partial import merge_display_generation_warnings


def test_display_warnings_drop_raw_matching_error_after_recovery_without_matching() -> None:
    raw_warning = GenerationWarning(
        code="generation_quality_error",
        message=(
            "Квиз показан с предупреждением: "
            "Вопрос на соответствие не прошёл проверку: пары должны быть явно основаны на тексте документа."
        ),
        recommendations=(
            "Проверьте показанный квиз перед использованием.",
            "Если предупреждение связано с соответствием, проверьте пары и повторите генерацию.",
        ),
    )
    recovery_warning = GenerationWarning(
        code="matching_fallback_applied",
        message=(
            "Квиз был автоматически исправлен. Вопрос на соответствие был заменён другим типом вопроса, "
            "потому что часть пар не подтверждалась текстом."
        ),
    )
    final_quiz = Quiz(
        quiz_id="quiz-warning",
        document_id="doc-warning",
        title="Квиз",
        version=1,
        last_edited_at="2026-05-17T00:00:00Z",
        questions=(
            Question(
                question_id="q1",
                prompt="Что указано в тексте?",
                question_type="short_answer",
                correct_answer="Текст содержит факт.",
            ),
        ),
    )

    warnings = merge_display_generation_warnings((raw_warning,), (recovery_warning,), final_quiz)

    assert warnings == (recovery_warning,)


def test_display_warnings_remove_pair_recommendation_when_final_quiz_has_no_matching() -> None:
    raw_warning = GenerationWarning(
        code="generation_quality_error",
        message="Квиз показан с предупреждением: проверьте результат.",
        recommendations=(
            "Проверьте показанный квиз перед использованием.",
            "Если предупреждение связано с соответствием, проверьте пары и повторите генерацию.",
        ),
    )
    final_quiz = Quiz(
        quiz_id="quiz-warning",
        document_id="doc-warning",
        title="Квиз",
        version=1,
        last_edited_at="2026-05-17T00:00:00Z",
        questions=(
            Question(
                question_id="q1",
                prompt="Что указано в тексте?",
                question_type="short_answer",
                correct_answer="Текст содержит факт.",
            ),
        ),
    )

    warnings = merge_display_generation_warnings((raw_warning,), (), final_quiz)

    assert warnings[0].recommendations == ("Проверьте показанный квиз перед использованием.",)
