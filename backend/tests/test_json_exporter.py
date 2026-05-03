from __future__ import annotations

import json

from backend.app.domain.models import Explanation
from backend.app.domain.models import Option
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.export.json_exporter import QuizJsonExporter


def build_quiz() -> Quiz:
    return Quiz(
        quiz_id="quiz-ru-1",
        document_id="doc-ru-1",
        title="Тренировочный квиз по географии",
        version=3,
        last_edited_at="2026-04-22T12:00:00.000000Z",
        questions=(
            Question(
                question_id="question-1",
                prompt="Какой город является столицей России?",
                options=(
                    Option(option_id="option-1", text="Москва"),
                    Option(option_id="option-2", text="Казань"),
                ),
                correct_option_index=0,
                explanation=Explanation(text="Москва является столицей России."),
            ),
        ),
    )


def test_json_exporter_builds_deterministic_utf8_quiz_file() -> None:
    exporter = QuizJsonExporter()
    quiz = build_quiz()

    first_export = exporter.export(quiz)
    second_export = exporter.export(quiz)

    expected_payload = """{
  "quiz_id": "quiz-ru-1",
  "document_id": "doc-ru-1",
  "title": "Тренировочный квиз по географии",
  "version": 3,
  "last_edited_at": "2026-04-22T12:00:00.000000Z",
  "questions": [
    {
      "question_id": "question-1",
      "question_type": "single_choice",
      "prompt": "Какой город является столицей России?",
      "options": [
        {
          "option_id": "option-1",
          "text": "Москва"
        },
        {
          "option_id": "option-2",
          "text": "Казань"
        }
      ],
      "correct_option_index": 0,
      "correct_answer": null,
      "matching_pairs": [],
      "explanation": {
        "text": "Москва является столицей России."
      }
    }
  ]
}"""

    assert first_export.filename == "quiz-ru-1.json"
    assert first_export.media_type == "application/json; charset=utf-8"
    assert first_export.content_bytes == second_export.content_bytes
    assert first_export.content_bytes.decode("utf-8") == expected_payload
    assert json.loads(first_export.content_bytes) == quiz.to_dict()
