# Multiple Question Types

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

After this change, QuizCraft users can generate quizzes that mix several question types in one run. The setup screen will no longer expose a disabled single-select field for only `Множественный Выбор`; it will show checkbox options for multiple choice, true/false, fill-in-the-blank, short answer, and matching. The backend will accept and validate the new type list, instruct the model to generate the requested mix, normalize and store the new question shapes without corrupting Russian text, and keep older single-choice quizzes compatible.

The result can be observed by selecting multiple question type checkboxes in `frontend/index.html`, submitting a request payload that contains `quiz_types`, and running pytest tests that cover Russian/Cyrillic examples for the new shapes.

## Progress

- [x] (2026-05-03 09:50 MSK) Confirmed the target branch is not clean before starting: staged-flow/preflight frontend files are already modified and `frontend/stage-flow.js` is untracked.
- [x] (2026-05-03 09:54 MSK) Inspected current domain enums, Pydantic schemas, quiz dataclasses, normalization, validation, prompt schema, request builders, renderer, editor, and frontend form wiring.
- [x] (2026-05-03 09:58 MSK) Added failing tests for backend enum/schema/model/normalization/validation support for all question types with Russian examples.
- [x] (2026-05-03 09:59 MSK) Added failing tests for frontend checkbox selection and `quiz_types` request payload.
- [x] (2026-05-03 10:07 MSK) Implemented backend support for `quiz_types`, new question shapes, compatible serialization, validation, JSON Schema, prompts, API serialization, and DOCX/PPTX export.
- [x] (2026-05-03 10:11 MSK) Implemented frontend checkbox UI, payload collection, result rendering, and editor preservation/editing for non-choice question shapes.
- [x] (2026-05-03 10:17 MSK) Ran full pytest, ruff, diff-check, and a Chrome visual check of multiple checkbox selection.

## Surprises & Discoveries

- Observation: The current persisted `Question` model assumes every question has at least two options and one integer `correct_option_index`.
  Evidence: `backend/app/domain/models.py` defines `Question(options, correct_option_index)`, and `backend/app/domain/validation.py` rejects every question with fewer than two options.

- Observation: The frontend already labels several unsupported types, but they are disabled options in a single `<select>`.
  Evidence: `frontend/index.html` has disabled `<option>` elements for `true_false`, `fill_blank`, `short_answer`, and `matching`.

- Observation: The first checkbox layout used two columns inside a narrow parameter grid cell and caused label overlap.
  Evidence: Chrome screenshot `C:\Users\batyr\AppData\Local\Temp\quizcraft-question-types-ui.png` showed question type labels colliding; after switching to one column, the browser overflow probe returned `overflowing: []`.

## Decision Log

- Decision: Keep backward compatibility by retaining `quiz_type`, `options`, and `correct_option_index`, while adding optional `quiz_types`, `question_type`, `correct_answer`, and `matching_pairs`.
  Rationale: Existing stored quizzes, exporters, editor tests, and generation flows expect the old fields. Optional additions allow new shapes without breaking old JSON.
  Date/Author: 2026-05-03 / Codex

- Decision: Represent multi-type generation requests as `quiz_types: list[str]` and derive the legacy `quiz_type` field from the first selected type for older code paths.
  Rationale: The UI needs multiple checkboxes, while existing saved settings and prompt formatting currently use one string. This is the smallest compatible bridge.
  Date/Author: 2026-05-03 / Codex

## Outcomes & Retrospective

Implemented. Users can now select one or more question types with checkboxes. The frontend sends both legacy `quiz_type` and new `quiz_types`, while the backend accepts all five supported values and stores generated questions with optional `question_type`, `correct_answer`, and `matching_pairs`. Existing single-choice quizzes remain compatible because missing `question_type` defaults to `single_choice`, and old fields remain in serialized payloads.

Validation evidence: `python -m pytest -q` passed, `python -m ruff check .` passed, and `git diff --check` passed with only Git line-ending warnings. A Chrome visual check confirmed selecting `single_choice`, `true_false`, and `matching` together and found no overflow in the question-type control after the layout fix.

## Context and Orientation

The backend request contract lives in `backend/app/api/schemas.py`. The allowed generation type enum lives in `backend/app/domain/enums.py`. The persisted quiz dataclasses are in `backend/app/domain/models.py`; they serialize to dictionaries that are saved by repositories and returned to the frontend. Model output normalization is in `backend/app/domain/normalization.py`, and business validation is in `backend/app/domain/validation.py`. Provider JSON Schema and prompt instructions are in `backend/app/domain/schema.py` and `backend/app/prompts/registry.py`. Direct and RAG prompt builders use `generation_request.quiz_type` in `backend/app/generation/request_builder.py` and `backend/app/generation/rag_orchestrator.py`.

The frontend form lives in `frontend/index.html`. `frontend/generation-flow.js` reads form fields and builds the generation payload. `frontend/quiz-renderer.js` renders generated questions. `frontend/quiz-editor.js` renders editable question cards and builds update payloads.

## Plan of Work

First, add tests that prove all new quiz type enum values are accepted, that request bodies can carry `quiz_types`, and that normalization/validation preserve Russian true/false, fill-blank, short-answer, and matching questions.

Second, extend backend dataclasses and schemas compatibly. `Question` will gain `question_type`, `correct_answer`, and `matching_pairs`; old single-choice questions can omit them and still serialize as before. Validation will branch by `question_type`: choice and true/false require options plus a valid index, fill-blank and short-answer require `correct_answer`, and matching requires at least one pair.

Third, update prompt JSON Schema and prompt text so the model knows how to output the correct shape per question. The schema will keep legacy fields valid while allowing `question_type`, `correct_answer`, and `matching_pairs`.

Fourth, replace the frontend single select with checkbox controls named `quiz_types`, update `buildGenerationPayload()` to collect all checked values, and update renderer/editor output for non-choice shapes.

Finally, run focused backend and frontend tests, run ruff, run diff-check, and update this plan with results.

## Concrete Steps

From `D:\github\quizcraft`, run focused tests as the implementation proceeds:

    python -m pytest backend/tests/test_domain_enums.py backend/tests/test_api_schemas.py backend/tests/test_domain_models.py backend/tests/test_quiz_normalization.py backend/tests/test_quiz_validation.py backend/tests/test_generation_request_builder.py tests/test_frontend_shell.py -q
    python -m ruff check backend/app backend/tests tests
    git diff --check
    git status --short --branch

The first new tests must fail before production code changes and pass after implementation.

## Validation and Acceptance

Acceptance requires that the frontend exposes checkbox controls for all five question types, allows multiple selected values, and sends `quiz_types` in the generation payload. Backend acceptance requires that API schemas accept multiple types and reject empty type lists, normalization preserves Russian text for new question shapes, and validation rejects invalid shapes with explicit errors. Existing single-choice tests must keep passing.

## Idempotence and Recovery

All changes are additive and can be retried safely. If new shapes break old quizzes, restore compatibility by defaulting missing `question_type` to `single_choice` and missing `options` to an empty tuple only for non-choice shapes. If frontend checkbox handling breaks generation, the fallback is to keep `single_choice` checked by default and derive `quiz_type` from the first checked value.

## Artifacts and Notes

Plan commit is deferred because the working tree was already dirty before this feature started. This violates the repository preference for a separate plan commit, but avoids mixing previous uncommitted frontend work into a misleading plan-only commit.

## Interfaces and Dependencies

No production dependency is expected. The implementation uses existing Python dataclasses, Pydantic schemas, plain JavaScript form handling, and pytest.
