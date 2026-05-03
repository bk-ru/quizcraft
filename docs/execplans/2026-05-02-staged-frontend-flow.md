# Staged Frontend Flow

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

After this change, the main QuizCraft frontend will move from a long single-page workspace to a staged workflow. The first stage combines document upload and generation parameters. The following stages focus the user on generation progress, result review, and editing/export. The app must keep the existing plain HTML/CSS/JavaScript runtime, existing DOM ids consumed by modules, backend API contracts, Russian UI, Cyrillic text preservation, export actions, quiz editing, single-question regeneration, cancellation, and connection controls.

The user can verify the result by opening `frontend/index.html` through `run-frontend.ps1`, running the frontend shell tests, and completing the existing local manual flow. No production dependency or frontend framework will be added.

## Progress

- [x] (2026-05-02 19:51 MSK) User approved the standalone staged-flow prototype and requested transfer into the main frontend with `Документ` and `Параметры` combined.
- [x] (2026-05-02 19:53 MSK) Confirmed `main` working tree is clean before implementation planning.
- [x] (2026-05-02 19:55 MSK) Inspected current `frontend/index.html`, `frontend/app.js`, `frontend/progress.js`, `frontend/generation-flow.js`, and relevant frontend shell tests.
- [x] (2026-05-03 14:10 MSK) Implemented `frontend/stage-flow.js` with `createStageFlowController` and `normalizeWorkflowStage`, added staged regions and `data-stage-root` wiring to `frontend/index.html`, added staged layout rules and `@keyframes stage-in` to `frontend/layout.css`, wired stage transitions through `frontend/progress.js` and `frontend/app.js`, adjusted `frontend/responsive.css`, and extended `tests/test_frontend_shell.py` for the Russian staged flow.
- [x] (2026-05-03 14:10 MSK) Ran full pytest suite and `ruff check .`; both green.

## Surprises & Discoveries

- Observation: The current progress controller already treats the old top stepper as stateful UI with stages `upload`, `params`, `review`, and `edit`.
  Evidence: `frontend/progress.js` defines `STEPPER_ORDER = ["upload", "params", "review", "edit"]` and modules call `advanceStepper` with those names.

- Observation: The current generation form must keep its existing element ids because `frontend/app.js` and `frontend/generation-flow.js` query them directly.
  Evidence: `frontend/app.js` obtains `generation-form`, `document-file`, `submit-button`, `generation-result`, `quiz-editor`, export buttons, and progress ids at module startup.

- Observation: A separate Multiple Question Types batch (`docs/execplans/2026-05-03-multiple-question-types.md`) landed on top of the staged-flow working tree before this plan was finalized, so both batches now share the same frontend files and are delivered together in one combined feature commit.
  Evidence: The MQT ExecPlan explicitly recorded that `frontend/stage-flow.js` was already untracked and staged-flow frontend files were already modified when MQT started, and the user approved integrating both in one commit.

## Decision Log

- Decision: Keep the implementation in the existing no-build static frontend.
  Rationale: The project already runs with plain browser ES modules and static CSS; a staged workflow does not require a new dependency.
  Date/Author: 2026-05-02 / Cascade

- Decision: Combine document upload and generation parameters into the first stage named `setup` while preserving compatibility aliases for existing calls to `upload` and `params`.
  Rationale: The user explicitly asked to combine `Документ` and `Параметры`, and existing modules still call `advanceStepper("params")` and `advanceStepper("review")`.
  Date/Author: 2026-05-02 / Cascade

- Decision: Add a small frontend stage controller rather than migrating to a router.
  Rationale: The current app is static and has a small number of sections. A DOM-based controller is sufficient and keeps changes localized.
  Date/Author: 2026-05-02 / Cascade

## Outcomes & Retrospective

Implemented. The main QuizCraft frontend now uses a staged workflow with four stages: `setup` (combined document upload plus generation parameters), `generation` (progress and cancellation), `result` (review and exports), and `edit` (editor/save/regeneration). Stage navigation is handled by `createStageFlowController` in `frontend/stage-flow.js`, which understands legacy stage aliases (`upload`/`params` → `setup`, `review` → `result`) so existing `advanceStepper` calls and module hooks keep working. The static frontend remains plain HTML/CSS/JavaScript, no new production dependency was added, all existing DOM ids and backend contracts are preserved, and Russian/Cyrillic UI strings remain intact.

Validation evidence: `python -m pytest -q` passed, `python -m ruff check .` reported `All checks passed!`, `git diff --check` reported only LF→CRLF line-ending warnings.

Integration note: this implementation lands together with the Multiple Question Types feature (see `docs/execplans/2026-05-03-multiple-question-types.md`) because the two WIP batches shared the same frontend files on an already-dirty working tree. The user explicitly approved a single combined feature commit after both ExecPlans were updated in separate doc commits.

## Context and Orientation

The executable frontend lives under `frontend/`. `frontend/index.html` contains the current long-page shell. `frontend/app.js` wires DOM elements and modules. `frontend/progress.js` updates the stepper and generation progress panel. `frontend/generation-flow.js` owns upload/generation submission, cancellation, and progress transitions. `frontend/quiz-renderer.js` renders generated results and moves the current step to result review. `frontend/quiz-editor.js` renders editor fields and moves the current step to editing.

The standalone prototype already exists at `staged-flow-prototype/index.html`, but it is intentionally not wired into production.

## Plan of Work

First, update the main HTML shell so the workspace uses staged regions: `setup` for document upload plus parameters, `generation` for request state and progress, `result` for generated quiz and exports, and `edit` for editor/save/regeneration. Keep existing ids and form controls intact.

Second, add CSS for staged layout, stage cards, navigation controls, and responsive behavior while preserving existing component classes.

Third, update frontend JavaScript so stage navigation is explicit. Existing progress step names should map into the new stages without breaking generation flow, cancellation, result focus, editor opening, keyboard shortcuts, or export actions.

Fourth, update frontend shell tests to verify the staged Russian UI, combined document/parameters stage, compatibility wiring, and Cyrillic coverage.

Finally, run relevant tests and create an atomic implementation commit after review.

## Concrete Steps

From `D:\github\quizcraft`, run:

    python -m pytest tests/test_frontend_shell.py tests/test_repository_layout.py -q
    python -m ruff check tests/test_frontend_shell.py tests/test_repository_layout.py
    git diff --check
    git status --short --branch

The test command should pass. Ruff should report `All checks passed!`. The final git status should be clean after commits are created.

## Validation and Acceptance

The staged frontend is accepted when the main page exposes a Russian staged flow with combined document upload and parameters, generation/progress, result, and editing/export stages; existing generation and editor DOM ids remain present; frontend shell tests pass; Cyrillic UI text remains intact; and no backend/API contracts or production dependencies change.

## Idempotence and Recovery

The implementation is limited to static frontend files and tests. If the staged navigation breaks visibility, restore all panels by removing stage `hidden` state in `frontend/app.js` or by disabling staged CSS selectors. If progress transitions do not activate the expected stage, check the compatibility mapping in the stage controller first.

## Artifacts and Notes

No new production dependency is expected. The prototype in `staged-flow-prototype/index.html` remains a reference artifact and should not be imported by the production frontend.

## Interfaces and Dependencies

`frontend/app.js` remains the browser entry point. Existing modules keep their public factory functions. Existing backend endpoints and request payloads are unchanged.
