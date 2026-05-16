# Grounded Matching Questions

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document is maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

QuizCraft already enforces that matching questions contain at least four pairs, but structurally valid model output can still be poor if it uses option IDs like `A` and `B`, includes `options`, or introduces terms that are absent from the uploaded document. After this change, matching questions are accepted only when their pairs are grounded in the document text, repair prompts receive source context to fix invalid pairs, and fallback conversion avoids preserving unsupported matching content.

The behavior is visible through backend tests that reproduce the photosynthesis defect: a generated matching question with `Цианобактерии` and `Хемосинтезирующие бактерии` must trigger repair or fallback instead of being saved as a matching question.

## Progress

- [x] (2026-05-16 12:30 MSK) Confirmed the target branch is dirty before implementation; relevant backend files and tests already contain partial matching-quality changes.
- [x] (2026-05-16 12:30 MSK) Ran focused tests and observed RED failures in matching groundedness and fallback handling.
- [x] (2026-05-16 12:34 MSK) Completed the focused implementation for matching fallback, groundedness, and prompt rules.
- [x] (2026-05-16 12:35 MSK) Confirmed focused backend tests pass: `backend/tests/test_quiz_validation.py`, `backend/tests/test_generation_orchestrator.py`, `backend/tests/test_question_type_rules.py`, `backend/tests/test_prompt_registry.py`, `backend/tests/test_generation_request_builder.py`, and `backend/tests/test_rag_prompt.py`.
- [x] (2026-05-16 12:41 MSK) Ran the requested full test and lint commands successfully; `git diff --check` reported only LF-to-CRLF warnings.
- [ ] Review the final diff against the base branch and commit the completed task.

## Surprises & Discoveries

- Observation: The working tree already contains partial prompt, validation, quality, and orchestrator changes for grounded matching.
  Evidence: `backend/app/domain/validation.py` already rejects matching `options` and symbolic right values, while `backend/app/generation/orchestrator.py` already passes `source_text` to `fallback_invalid_matching_questions`.

- Observation: The current fallback helper signature does not accept `source_text`, so repair exhaustion can fail with `TypeError` before producing a controlled result.
  Evidence: `python -m pytest backend/tests/test_quiz_validation.py backend/tests/test_generation_orchestrator.py -q` failed with `fallback_invalid_matching_questions() got an unexpected keyword argument 'source_text'`.

## Decision Log

- Decision: Keep groundedness lightweight by checking normalized phrases from each matching side against the source text, and use it as a quality failure that triggers the existing repair path.
  Rationale: The requirement calls for a safe heuristic, not a full NLP system, and repair/fallback is already the right control point for generation quality failures.
  Date/Author: 2026-05-16 / Codex

- Decision: Convert unsupported matching questions to short answer only when `short_answer` is allowed, and filter fallback answer content to grounded pairs.
  Rationale: This avoids saving unsupported terms after repair fails while preserving useful document-backed pairs when possible.
  Date/Author: 2026-05-16 / Codex

## Outcomes & Retrospective

Focused implementation is complete. The matching fallback now accepts source text, expands option IDs through matching `options` before converting to short answer, filters unsupported pairs, and uses a natural Russian fallback prompt. The quality checker now raises the required Russian groundedness error message for unsupported matching pairs. The requested backend, frontend shell, repository layout, ruff, and diff-check commands pass.

## Context and Orientation

Prompt rules for question types live in `backend/app/generation/question_types.py`, while direct, RAG, and repair prompt templates live in `backend/app/prompts/registry.py`. Domain shape validation is in `backend/app/domain/validation.py`. Quality checks after normalization are in `backend/app/generation/quality.py`, and direct generation repair/fallback control flow is in `backend/app/generation/orchestrator.py`. Matching fallback helpers live in `backend/app/generation/matching_fallback.py`.

The generation orchestrator normalizes provider JSON into a `Quiz`, runs `GenerationQualityChecker.ensure_quality`, and catches `DomainValidationError` failures to call the repair prompt. `GenerationQualityError` derives from the same domain validation base class, so groundedness failures can use the same repair path.

## Plan of Work

First, keep the existing regression tests as the specification and make them fail for the right reasons. The key tests are in `backend/tests/test_quiz_validation.py` and `backend/tests/test_generation_orchestrator.py`.

Second, update `backend/app/generation/matching_fallback.py` so `fallback_invalid_matching_questions` accepts `source_text`, converts invalid or ungrounded matching questions only when a safe fallback type is allowed, removes unsupported pairs from the fallback answer, and uses a natural Russian short-answer prompt.

Third, adjust `backend/app/generation/quality.py` so the groundedness error message is the requested Russian message and the heuristic remains phrase-based rather than overly broad.

Fourth, verify prompt text in `backend/app/generation/question_types.py` and `backend/app/prompts/registry.py` contains the matching restrictions for no options, no A/B/1/2 right values, full answer text, and no absent document terms.

Finally, run the requested checks from `D:\github\quizcraft`, review the diff, and commit only the files relevant to this task.

## Concrete Steps

From `D:\github\quizcraft`, run:

    python -m pytest backend/tests/test_quiz_validation.py backend/tests/test_generation_orchestrator.py -q
    python -m pytest backend/tests -q
    python -m pytest tests/test_frontend_shell.py -q
    python -m pytest tests/test_repository_layout.py -q
    python -m ruff check .
    git diff --check

The first focused command must fail before implementation and pass after implementation. The full requested commands must pass before reporting completion.

## Validation and Acceptance

Acceptance requires that matching questions with `options`, symbolic right values, or absent terms trigger repair. If repair returns grounded full-text pairs, the quiz is saved as matching. If repair still returns invalid matching and `short_answer` is allowed, the saved quiz must not contain unsupported terms. If only matching is allowed, the backend must raise `Вопрос на соответствие не прошёл проверку: пары должны быть явно основаны на тексте документа.` for groundedness failure.

## Idempotence and Recovery

All changes are local Python code and tests. Test commands can be rerun safely. If a fallback conversion accidentally drops every matching pair, the helper should return `None` so the orchestrator raises a controlled generation error instead of saving an empty answer.

## Artifacts and Notes

Focused RED transcript summary:

    6 failed, 25 passed
    TypeError: fallback_invalid_matching_questions() got an unexpected keyword argument 'source_text'
    GenerationQualityError: matching question pairs must be explicitly based on the source text

## Interfaces and Dependencies

No new production dependencies are needed. The implementation uses existing dataclasses, existing `GenerationQualityError`, existing `allowed_question_types`, and plain string normalization.
