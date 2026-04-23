# Frontend Decomposition Without Dependencies

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

After this change, the QuizCraft frontend keeps the same user-visible behavior while becoming easier to maintain. The current plain JavaScript app shell concentrates validation error translation, quiz rendering, quiz editing, generation orchestration, progress UI, theme handling, toast notifications, downloads, and event wiring in one large file. The current stylesheet similarly concentrates design tokens, layout, forms, quiz presentation, feedback UI, and responsive rules in one large file.

The user can verify the result by opening `frontend/index.html` through the existing static smoke test and by running the project test suite. The page should still expose the Russian upload, generation, review, editing, and JSON export UI. No frontend framework and no new production dependency will be added.

## Progress

- [x] (2026-04-23 22:08 MSK) Confirmed `main` is clean before starting the batch.
- [x] (2026-04-23 22:08 MSK) Inspected the existing frontend layout, `frontend/app.js`, `frontend/styles.css`, `tests/test_frontend_shell.py`, and the current README.
- [ ] Split frontend JavaScript into focused ES modules while keeping `frontend/app.js` as the composition and event-wiring entry point.
- [ ] Split frontend CSS into focused static stylesheets and update `frontend/index.html` with multiple stylesheet links.
- [ ] Update frontend smoke tests so they verify the new module and stylesheet structure without losing Russian/Cyrillic coverage.
- [ ] Update `README.md` in a separate docs commit after the refactor commit.
- [ ] Run `python -m pytest -q`, `python -m ruff check .`, review the diff against `main`, and confirm a clean working tree.

## Surprises & Discoveries

- Observation: `rg --files` is unavailable in this local PowerShell session due to an access-denied failure, so file inventory uses PowerShell recursion instead.
  Evidence: Running `rg --files` from `D:\github\diplom` returned `NativeCommandFailed` with `Отказано в доступе`.

- Observation: The frontend files preserve Russian text correctly when read as UTF-8; earlier mojibake was caused by default PowerShell output encoding.
  Evidence: `Get-Content -LiteralPath frontend\index.html -Encoding utf8 -TotalCount 12` displays `QuizCraft · Панель состояния` correctly.

## Decision Log

- Decision: Keep the frontend on plain browser ES modules and static CSS files.
  Rationale: The user explicitly requested no framework or dependency addition, and the current app already runs as static HTML, CSS, and JavaScript.
  Date/Author: 2026-04-23 / Codex

- Decision: Keep `frontend/app.js` as the root composition file.
  Rationale: Existing `index.html` already imports `app.js`; retaining it as the entry point preserves the runtime contract while allowing internal responsibilities to move into focused modules.
  Date/Author: 2026-04-23 / Codex

- Decision: Split CSS by stable UI responsibility rather than by exact HTML section.
  Rationale: Files such as `tokens.css`, `forms.css`, `quiz.css`, and `feedback.css` map to reusable styling responsibilities and should remain stable as the UI evolves.
  Date/Author: 2026-04-23 / Codex

## Outcomes & Retrospective

This section will be completed after implementation, validation, review, and commits.

## Context and Orientation

The executable frontend lives under `frontend/`. `frontend/index.html` is a static Russian-language shell that loads `frontend/config.js` and `frontend/app.js`. `frontend/api/client.js` contains the API client for backend calls. `frontend/app.js` currently contains all browser behavior. `frontend/styles.css` currently contains all styles.

The backend is out of scope for this task. The tests in `tests/test_frontend_shell.py` verify that the frontend shell exposes Russian/Cyrillic UI text, links expected assets, and wires upload, generation, editing, operation feedback, and JSON export behavior. Those tests must be updated to inspect the new files without weakening coverage.

## Plan of Work

First, split JavaScript responsibilities into focused ES modules in `frontend/`: `validation-errors.js` for Russian validation error translation, `quiz-renderer.js` for generated quiz display cards, `quiz-editor.js` for editor rendering and update-payload extraction, `progress.js` for stepper and generation progress state, `theme.js` for persisted theme handling, `toast.js` for notification rendering, `download.js` for JSON export download helpers, and `generation-flow.js` for upload/generation orchestration. `frontend/app.js` will import these modules, collect DOM references, initialize shared state, wire events, and bootstrap health checks.

Second, split `frontend/styles.css` into `frontend/styles/tokens.css`, `frontend/styles/base.css`, `frontend/styles/layout.css`, `frontend/styles/forms.css`, `frontend/styles/quiz.css`, `frontend/styles/feedback.css`, and `frontend/styles/responsive.css`. `frontend/index.html` will link them in dependency order so CSS variables and base rules load before component rules.

Third, update `tests/test_frontend_shell.py` so asset discovery accepts the new stylesheet links, frontend structure tests point at the new module files, and Russian/Cyrillic text assertions remain explicit.

Finally, update `README.md` in a separate docs commit to describe the implemented backend and frontend layout instead of the old planning-only repository description.

## Concrete Steps

From `D:\github\diplom`, run:

    python -m pytest -q
    python -m ruff check .
    git status --short --branch

The test command should report all tests passing. Ruff should report `All checks passed!`. The final git status should show a clean branch after commits are created.

## Validation and Acceptance

The refactor is accepted when `frontend/index.html` still references all runtime assets, `tests/test_frontend_shell.py` still proves the Russian upload/generation/review/edit/export UI exists, and the full pytest suite passes. The generated quiz flow, editor save flow, 422 validation mapper, progress panel, theme toggle, toast notifications, dropzone handling, and JSON export action must remain wired through `frontend/app.js` and its imported modules.

## Idempotence and Recovery

The changes are additive and mechanical: modules and CSS files can be re-read and adjusted without data migrations or destructive commands. If a split introduces a runtime import error, restore behavior by checking `frontend/index.html` script and link paths first, then confirm each imported JavaScript module exports the functions consumed by `frontend/app.js`.

## Artifacts and Notes

This plan intentionally does not add new production dependencies. The existing browser module system and static stylesheet links are sufficient for the requested decomposition.

## Interfaces and Dependencies

`frontend/app.js` remains the browser entry point imported by `frontend/index.html`. New JavaScript files export plain functions and constants only. New CSS files are static files linked from `frontend/index.html`. No package manager, bundler, or frontend framework is introduced.

Plan revision note, 2026-04-23 / Codex: Created the plan because the requested frontend decomposition changes a large JavaScript entry point, a large stylesheet, tests, and docs; repository instructions require an ExecPlan before large implementation changes.
