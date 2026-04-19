# QuizCraft MVP Staged Delivery Plan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

After this plan is executed, the repository will move from planning artifacts and static UI concepts to a working local single-user QuizCraft MVP that can accept one document, extract text, generate a quiz through LM Studio, let the user review and edit the result, and export the final quiz as JSON. The user can verify progress stage by stage by running targeted pytest suites, starting the backend, exercising the documented HTTP endpoints, and finally opening the real UI implementation instead of the concept-only HTML files in `docs/design/concepts/v2/`.

This plan does not implement code by itself. It organizes the remaining backlog into small, reviewable delivery stages that can be finished in one to three atomic commits each. Repo cleanup work was already completed in commit `4e293fb` and is treated as finished groundwork rather than part of feature delivery.

## Progress

- [x] (2026-04-17 15:53:15Z) Reviewed the current repository state, including the cleanup commit `4e293fb`, the current file tree, and the tracked planning artifacts.
- [x] (2026-04-17 15:53:15Z) Re-read `docs/planning/backlog.md` and mapped all remaining backlog items into sequential implementation stages.
- [x] (2026-04-17 15:53:15Z) Chose a conservative MVP boundary that stops after JSON export and leaves RAG, DOCX/PPTX, status streaming, and multi-provider work for later stages.
- [x] (2026-04-17 16:19:40Z) Implemented Stage 1, `Foundation Skeleton and Core Contracts`, in worktree `D:\github\diplom\.worktrees\stage-01-foundation`, including backend bootstrap, config loading, domain errors and models, `direct` mode registry, filesystem repositories, and Stage 1 tests.
- [x] (2026-04-17 16:55:49Z) Closed the Stage 1 review gaps in the same worktree by adding the explicit quiz JSON Schema artifact, quiz version and last-edit timestamp persistence, controlled config parsing errors, duplicate-option validation, and `LOG_FORMAT` support, then re-ran the Stage 1 pytest suites successfully.
- [x] (2026-04-17 17:36:28Z) Implemented Batch 1 of Stage 2 in worktree `D:\github\diplom\.worktrees\stage-02-batch-01-txt-ingestion`, covering TXT file validation, TXT parsing, TXT normalization, base TXT metadata assembly, and TXT ingestion persistence with dedicated pytest coverage.
- [x] (2026-04-17 18:04:18Z) Implemented Batch 2 of Stage 2 in worktree `D:\github\diplom\.worktrees\stage-02-batch-02-docx-ingestion`, extending the existing ingestion flow with DOCX validation, DOCX parsing, reused normalization and metadata assembly, and DOCX pytest coverage.
- [x] (2026-04-17 18:28:07Z) Implemented Batch 3 of Stage 2 in worktree `D:\github\diplom\.worktrees\stage-02-batch-03-pdf-ingestion`, adding PDF validation, page-by-page PDF text extraction, PDF page-count metadata, and PDF pytest coverage, including invalid and no-text PDF cases.
- [x] (2026-04-18) Implemented, reviewed, and integrated Batch 1 of Stage 3 on `main` via merge commit `88dc67f`, covering `LM-001`, `LM-002`, `LM-004`, and the client slice of `TS-004` with the provider contract, structured LM Studio client, retry-timeout wrapper, and client-slice pytest coverage.
- [x] (2026-04-18) Implemented, reviewed, and integrated Batch 2 of Stage 3 on `main` via merge commit `b65f58d`, covering `LM-003` and the healthcheck slice of `TS-004` with LM Studio health classification for available, timeout, connection-failure, and malformed-response states.
- [x] (2026-04-18) Implemented, reviewed, and integrated Batch 1 of Stage 4 on `main` via merge commit `3c595a2`, covering `PM-001`, `PM-002`, and `GN-001` with the versioned prompt registry, direct-generation master prompt, and provider request builder.
- [ ] Revisit this plan after each completed stage and update `Progress`, `Decision Log`, and `Outcomes & Retrospective` before starting the next stage.

## Surprises & Discoveries

- Observation: The repository still contains no executable backend or frontend source code; it currently contains only planning documents, one layout test, and static design concepts.
  Evidence: `README.md` states that application source code is not present yet, and the tracked files outside `docs/` are limited to `AGENTS.md`, `.agent/PLANS.md`, `README.md`, `LICENSE`, and `tests/test_repository_layout.py`.

- Observation: The backlog is detailed at the task level, but it is not yet grouped into implementation-sized increments; a direct "MVP all at once" reading would create stages that touch too many layers at once.
  Evidence: `docs/planning/backlog.md` lists twelve MVP task groups and three later priority groups, but its built-in MVP summary still groups the work into one broad tranche rather than reviewable delivery stages.

- Observation: The repository has uncommitted local edits in `AGENTS.md` that are not part of backlog implementation and must not be mixed into feature work.
  Evidence: `git status --short` shows `M AGENTS.md`, and `git diff -- AGENTS.md` contains planning-policy additions only.

- Observation: The backlog defines Python backend technology in enough detail to plan a concrete backend layout, but it does not define a frontend framework.
  Evidence: The backlog introduction explicitly mentions Python, FastAPI, Pydantic, pytest, and logging, while the UI section defines screens and behaviors but never names React, Vue, or any other framework.

- Observation: Stage 1 did not need any new production dependencies.
  Evidence: Backend bootstrap, config loading, domain modeling, validation, generation mode registration, and filesystem repositories were all implemented with the Python standard library, while pytest remained sufficient for test coverage.

## Decision Log

- Decision: Treat the current repository cleanup as complete and start the delivery plan from "no application code exists yet."
  Rationale: The cleanup commit `4e293fb` reorganized documents and concepts but did not implement any backlog tasks, so backlog completion remains effectively at zero percent.
  Date/Author: 2026-04-17 / Codex

- Decision: Use `backend/` for the executable Python service and `frontend/` for the real web UI implementation, while keeping `docs/design/concepts/v2/` as reference material only.
  Rationale: The current repository contains design references but no runtime code. A clean split between backend and frontend keeps future stages focused and prevents design artifacts from being confused with runnable code.
  Date/Author: 2026-04-17 / Codex

- Decision: Use filesystem-backed repositories for the early MVP.
  Rationale: The backlog defines a local single-user service and does not require a database. Filesystem storage keeps the first stages smaller, easier to test, and consistent with the repository's current simplicity.
  Date/Author: 2026-04-17 / Codex

- Decision: Split the API work into two stages and the UI work into three stages.
  Rationale: Health/upload/generate, quiz read/update, and JSON export are each independently testable. Keeping them separate avoids a single oversized stage that spans too many endpoints, frontend flows, and storage behaviors at once.
  Date/Author: 2026-04-17 / Codex

- Decision: Keep RAG, DOCX/PPTX, status streaming, profile persistence, and provider expansion outside the early MVP.
  Rationale: The backlog itself marks those items as `P2` or `Future`, and the user explicitly asked not to pull them into the early MVP when a working increment is possible without them.
  Date/Author: 2026-04-17 / Codex

- Decision: Leave `.agent/PLANS.md` unchanged and create a separate ExecPlan for feature delivery.
  Rationale: `.agent/PLANS.md` is the reusable format specification for ExecPlans. The correct way to "update ExecPlan/PLANS.md" for this task is to produce a new ExecPlan that follows that specification, not to rewrite the specification itself.
  Date/Author: 2026-04-17 / Codex

- Decision: Keep Stage 1 dependency-free on the production side and defer FastAPI/Pydantic introduction until the HTTP stage.
  Rationale: The current stage only needed a runnable Python package, config, domain contracts, logging bootstrap, and filesystem persistence. Pulling in HTTP or schema libraries earlier would enlarge the foundation stage without improving the verified behavior.
  Date/Author: 2026-04-17 / Codex

- Decision: Deliver Stage 2 in a TXT-first batch before introducing DOCX or PDF parsing.
  Rationale: The user narrowed the next increment to `PR-001`, `PR-002`, the TXT slice of `PR-005`, the base TXT slice of `PR-006`, and their tests. Keeping that batch TXT-only preserves the small-stage property of the plan and avoids adding parser dependencies before the ingestion contract is stable.
  Date/Author: 2026-04-17 / Codex

- Decision: Implement the DOCX slice with the Python standard library instead of introducing a DOCX parsing dependency.
  Rationale: Batch 2 only needed paragraph text extraction from `.docx` packages, which can be handled with `zipfile` and XML parsing. This keeps the batch within scope and respects the no-new-dependencies constraint while leaving room for a richer parser later if a later stage truly needs it.
  Date/Author: 2026-04-17 / Codex

- Decision: Add `pypdf` as the sole production dependency for the PDF slice of Stage 2.
  Rationale: The Python standard library does not provide PDF parsing or text extraction. `pypdf` is the smallest dependency that satisfies the backlog requirement for page-by-page text extraction and understandable errors for PDFs without extractable text, while keeping OCR and heavier PDF stacks out of scope.
  Date/Author: 2026-04-17 / Codex

- Decision: Split Stage 3 into two batches so the provider request path can land before healthcheck behavior.
  Rationale: `LM-001`, `LM-002`, `LM-004`, and the client slice of `TS-004` form one reviewable unit around structured generation requests, while `LM-003` and the healthcheck slice of `TS-004` are a separate operational concern that should follow only after the client path is integrated.
  Date/Author: 2026-04-18 / Codex

## Outcomes & Retrospective

At this stopping point, the repository no longer contains only planning artifacts. `main` now includes the Stage 1 foundation contracts, the full Stage 2 ingestion and parsing scope for TXT, DOCX, and PDF, and the complete Stage 3 LM Studio provider integration scope. The remaining work is still intentionally staged, but the plan must now reflect partially implemented delivery rather than a planning-only repository.

The key outcome is that the remaining work is grouped into narrow, verifiable increments with explicit dependencies and commit guidance, and the completed increments are already integrated on `main`. The next contributor should continue from Stage 4 rather than revisiting foundation, parsing, or LM Studio integration work.

## Context and Orientation

The current repository has both planning artifacts and implemented backend slices. `AGENTS.md` and `.agent/PLANS.md` contain repository and planning rules. `docs/planning/backlog.md` remains the source-of-truth feature inventory. `docs/design/concepts/v2/` still contains static mockups for the intended product screens. `backend/` now contains the foundation, storage, parsing, and LM Studio integration layers covered by Stages 1, 2, and 3. `tests/test_repository_layout.py` still checks repository structure, while `backend/tests/` now covers the implemented backend behavior. There is still no HTTP API surface, no generation orchestration, no runnable frontend, and no export implementation yet.

The backlog assumes a Python backend with typed contracts, FastAPI/Pydantic-style API models, pytest tests, standard-library logging, and LM Studio as the only model provider for the MVP. The backlog does not pick a frontend framework. Because the repository currently contains only HTML concepts, this plan assumes a thin frontend in `frontend/` that can start as plain HTML, CSS, and JavaScript while reusing the visual structure from the concept files. If a richer framework is chosen later, the plan should be revised before Stage 7.

The planned runtime layout for implementation is:

    backend/
      pyproject.toml
      app/
        main.py
        api/
        core/
        domain/
        parsing/
        prompts/
        generation/
        llm/
        storage/
        export/
      tests/
    frontend/
      index.html
      src/
      assets/

This layout is now partially implemented. `backend/` exists with `core`, `domain`, `parsing`, `storage`, and `llm` packages, while the HTTP API, generation, prompt, export, and `frontend/` portions remain target layout for later stages.

## Plan of Work

The work should proceed from the center outward. First, create the executable skeleton, configuration, core domain contracts, error hierarchy, repositories, and logging baseline. Next, implement document ingestion and parsing without any HTTP or frontend concerns. Once document handling is stable, add the LM Studio provider abstraction and HTTP client. After that, implement the direct-generation pipeline, including prompt registry, request assembly, output normalization, validation, repair-pass, and persistence.

Only after those non-HTTP layers are stable should the backend API be exposed. The first API stage should cover health, LM Studio connectivity, document upload, and quiz generation. The second API stage should cover quiz retrieval and quiz updates. Then build the real UI in three small passes: upload/generation/result viewing, editing, and finally JSON export. That sequence yields the earliest working MVP without dragging in second-wave features.

After JSON export, continue with second-wave stages in this order: status streaming and user-facing operation states, profile and model selection support, single-question regeneration, advanced export formats, RAG, provider expansion, and finally RAG caching. This keeps the highest-value local MVP path short while preserving a clear route for the rest of the backlog.

## Stage 1: Foundation Skeleton and Core Contracts

Task IDs: `BE-001`, `BE-002`, `BE-003`, `DM-001`, `DM-002`, `DM-004`, `ST-001`, `ST-002`, `CF-001`, `LG-001`, `TS-001`.

Rationale for grouping: This stage creates the non-negotiable base that every later layer depends on: runnable backend skeleton, configuration loading, logging bootstrap, generation-mode registry, domain models, business validation, repository contracts, and the first storage implementation. The stage is intentionally limited to core contracts and local persistence so later stages can build on stable interfaces instead of raw dictionaries or ad hoc files.

Dependencies: None beyond the already completed repository cleanup. This is the first implementation stage.

Definition of done: The repository contains a runnable `backend/` package, configuration loads from environment variables, the generation mode registry supports `direct`, the application defines explicit domain exceptions and domain models for document and quiz data, and filesystem repositories can persist and retrieve documents and quizzes locally. Invalid quiz structures fail through business validation rather than passing silently.

Required tests/checks: Run `python -m pytest backend/tests/test_config.py backend/tests/test_domain_models.py backend/tests/test_repositories.py -q` and expect all tests to pass. Start the backend import path with `python -c "from backend.app.main import create_app"` and expect no import errors. Keep `python -m pytest tests/test_repository_layout.py -q` green.

Recommended commit breakdown:
1. `feat(backend): scaffold service package and configuration bootstrap`
2. `feat(domain): add core models, error hierarchy, repositories, and mode registry`
3. `test(core): cover config, validators, and filesystem repositories`

## Stage 2: Document Ingestion and Parsing

Task IDs: `PR-001`, `PR-002`, `PR-003`, `PR-004`, `PR-005`, `PR-006`, `TS-002`, `TS-003`.

Rationale for grouping: This stage finishes the document-handling layer before any provider or API work begins. File validation, text extraction, text normalization, and metadata extraction belong together because they produce the stored document artifact that all later generation work will consume.

Dependencies: Stage 1, especially `ST-001`, config loading, logging, and the error model.

Definition of done: The backend can accept a file abstraction from tests, reject invalid or oversized inputs, extract text from TXT, DOCX, and PDF, normalize the text into a canonical form, compute metadata, and persist the resulting document record through the document repository. No LM Studio calls or HTTP endpoints are involved yet.

Required tests/checks: Run `python -m pytest backend/tests/test_file_validation.py backend/tests/test_parsers.py backend/tests/test_document_ingestion_service.py -q` and expect all tests to pass. Use fixture files for positive and negative cases, including empty files, invalid extensions, and corrupted documents where practical.

Recommended commit breakdown:
1. `feat(parsing): add file validation and text extraction for txt and docx`
2. `feat(parsing): add pdf parsing, text normalization, and metadata assembly`
3. `test(parsing): cover validator, parsers, and document ingestion flow`

## Stage 3: LM Studio Provider Integration

Task IDs: `LM-001`, `LM-002`, `LM-003`, `LM-004`, `TS-004`.

Rationale for grouping: Stage 3 owns the LM Studio integration boundary, but it is now split into two batches. Batch 1 lands the provider contract, structured request path, and centralized retry-timeout behavior. Batch 2 adds only the provider-facing healthcheck behavior. This keeps the request path reviewable and integrated before adding the operational status slice.

Dependencies: Stage 1 for config, error model, logging, and generation mode registry.

### Batch 1: Provider Contract, Structured Client, and Retry Wrapper

Task IDs: `LM-001`, `LM-002`, `LM-004`, `TS-004` client slice.

Definition of done: The backend defines a provider interface that hides LM Studio details from callers, the LM Studio client can request structured quiz data through `/v1/chat/completions`, and retry-timeout handling for generation requests is centralized rather than duplicated.

Required tests/checks: Run `python -m pytest backend/tests/test_lm_studio_client.py -q` and expect all tests to pass. Mock LM Studio responses for `200`, timeout, invalid JSON, `5xx`, and malformed structured response cases.

Recommended commit breakdown:
1. `feat(llm): add provider abstraction and structured LM Studio client`
2. `feat(llm): add retry-timeout wrapper for generation requests`
3. `test(llm): cover structured client success and failure paths`

Current status on `main`: implemented and integrated via merge commit `88dc67f`.

### Batch 2: LM Studio Healthcheck Behavior

Task IDs: `LM-003`, `TS-004` healthcheck slice.

Definition of done: The LM Studio healthcheck behavior distinguishes connection failures, timeout failures, and malformed responses, and maps them to controlled domain errors without introducing orchestration or API work.

Required tests/checks: Run `python -m pytest backend/tests/test_lm_studio_healthcheck.py backend/tests/test_lm_studio_client.py -q` and expect all tests to pass. Mock LM Studio responses for available, timeout, connection failure, and malformed response cases.

Recommended commit breakdown:
1. `feat(llm): add lm studio healthcheck behavior`
2. `test(llm): cover healthcheck availability and failure modes`

Current status on `main`: implemented and integrated via merge commit `b65f58d`.

## Stage 4: Direct Generation Pipeline

Task IDs: `PM-001`, `PM-002`, `PM-003`, `GN-001`, `GN-002`, `GN-003`, `GN-004`, `GN-005`, `DM-003`, `TS-005`, `TS-006`, `LG-003`.

Rationale for grouping: This is the core application value path. Stage 4 is now split into three batches so prompt/version contracts, output normalization rules, and the full direct-generation orchestrator can be reviewed independently without mixing too many moving parts in one batch.

Dependencies: Stages 1 through 3.

Current status on `main`: fully implemented and integrated via merge commit `b70ff27`.

### Batch 1: Prompt Registry and Request Assembly

Task IDs: `PM-001`, `PM-002`, `GN-001`.

Definition of done: The backend has a versioned prompt registry, a direct-generation master prompt, and a single request builder that converts a stored document and generation command into one provider-facing structured request.

Required tests/checks: Run `python -m pytest backend/tests/test_prompt_registry.py backend/tests/test_generation_request_builder.py -q` and expect all tests to pass. Keep `python -m pytest backend/tests -q`, `python -m pytest tests/test_repository_layout.py -q`, and `python -c "from backend.app.main import create_app"` green.

Recommended commit breakdown:
1. `feat(prompts): add prompt registry and direct generation prompt`
2. `feat(generation): add direct generation request builder`
3. `test(generation): cover prompt resolution and request assembly`

Current status on `main`: implemented and integrated via merge commit `3c595a2`.

### Batch 2: Output Normalization and Quality Validation

Task IDs: `DM-003`, `GN-003`, `TS-005`.

Definition of done: Raw model output is normalized into the canonical quiz structure, extra fields are dropped, strings are trimmed, invalid or empty options are filtered, and quality checks reject structurally valid but unusable quizzes.

Required tests/checks: Run `python -m pytest backend/tests/test_quiz_normalization.py backend/tests/test_quiz_validation.py -q` and expect all tests to pass. Keep `python -m pytest backend/tests -q`, `python -m pytest tests/test_repository_layout.py -q`, and `python -c "from backend.app.main import create_app"` green.

Recommended commit breakdown:
1. `feat(domain): add quiz output normalizer and quality checks`
2. `test(generation): cover normalization and business validation`

Current status on `main`: implemented and integrated via merge commit `43ce420`.

### Batch 3: Direct Orchestrator, Repair Loop, and Persistence

Task IDs: `PM-003`, `GN-002`, `GN-004`, `GN-005`, `LG-003`, `TS-006`.

Definition of done: Given an already stored document and a generation request, the backend can build the direct-mode prompt payload, call LM Studio, normalize and validate the model response, attempt a bounded repair-pass when needed, redact sensitive text in logs, and persist the final quiz with prompt and model metadata.

Required tests/checks: Run `python -m pytest backend/tests/test_generation_orchestrator.py backend/tests/test_safe_logging.py -q` and expect all tests to pass. The orchestrator tests must cover a clean success path, a repair-pass success path, and a final failure path after repair is exhausted. Keep `python -m pytest backend/tests -q`, `python -m pytest tests/test_repository_layout.py -q`, and `python -c "from backend.app.main import create_app"` green.

Recommended commit breakdown:
1. `feat(prompts): add repair prompt`
2. `feat(generation): add direct orchestrator, repair loop, and metadata persistence`
3. `test(generation): cover direct pipeline success, repair, terminal failure, and safe logging`

Current status on `main`: implemented and integrated via merge commit `b70ff27`.

## Stage 5: API Bootstrap, Health, Upload, and Generate

Task IDs: `BE-004`, `BE-005`, `BE-006`, `BE-007`, `LG-002`, `LG-004`, `TS-007` (health, upload, generate slice).

Rationale for grouping: These endpoints are the minimum HTTP surface needed to prove that the backend is usable from outside unit tests. Stage 5 is now split into two batches so the HTTP runtime shell and operational health behavior land before the upload-plus-generate flow.

Dependencies: Stages 1 through 4.

### Batch 1: HTTP bootstrap, correlation IDs, error mapping, and health endpoints

Task IDs: `BE-004`, `BE-005`, `LG-002`, `LG-004`, `TS-007` (health slice).

Definition of done: The backend starts as an HTTP service, exposes a health endpoint that does not depend on LM Studio, exposes an LM Studio connectivity endpoint, attaches a correlation ID to logs, and maps expected domain exceptions into stable HTTP error responses.

Required tests/checks: Run `python -m pytest backend/tests/test_api_health.py backend/tests/test_api_lm_studio.py -q` and expect all tests to pass. Keep `python -m pytest backend/tests -q`, `python -m pytest tests/test_repository_layout.py -q`, and `python -c "from backend.app.main import create_app"` green.

Recommended commit breakdown:
1. `feat(api): bootstrap http app and request correlation ids`
2. `feat(api): add health endpoints and error-to-http mapping`
3. `test(api): cover backend and lm studio health flows`

### Batch 2: Upload and generate endpoints

Task IDs: `BE-006`, `BE-007`, `TS-007` (upload, generate slice).

Definition of done: The backend accepts a document upload with validation, creates a stored document record, accepts a generation request for that document, and returns the generated canonical quiz structure with `quiz_id`.

Required tests/checks: Run `python -m pytest backend/tests/test_api_upload_and_generate.py -q` and expect all tests to pass. Keep `python -m pytest backend/tests -q`, `python -m pytest tests/test_repository_layout.py -q`, and `python -c "from backend.app.main import create_app"` green. Start the server with `python -m uvicorn backend.app.main:app --reload` and verify that `/health` returns HTTP 200 and that an upload-plus-generate request produces a `quiz_id`.

Recommended commit breakdown:
1. `feat(api): add document upload endpoint`
2. `feat(api): add direct generation endpoint`
3. `test(api): cover upload validation and generation flows`

## Stage 6: API Quiz Read and Update

Task IDs: `BE-008`, `BE-009`, `TS-007` (read, update slice).

Rationale for grouping: Reading and updating a quiz are the smallest coherent follow-up to generation. They share the quiz repository, validation rules, and response model, and they are needed before any real editing UI can be built.

Dependencies: Stage 5 and the Stage 1 quiz repository.

### Batch 1: Quiz read endpoint

Task IDs: `BE-008`, `TS-007` (read slice).

Definition of done: The HTTP API can fetch a persisted quiz by `quiz_id` and return the canonical stored quiz structure with stable error handling for missing identifiers.

Required tests/checks: Run `python -m pytest backend/tests/test_api_quiz_read.py -q` and expect all tests to pass. Keep `python -m pytest backend/tests -q`, `python -m pytest tests/test_repository_layout.py -q`, and `python -c "from backend.app.main import create_app"` green.

Recommended commit breakdown:
1. `feat(api): add quiz read endpoint`
2. `test(api): cover quiz read flows`

### Batch 2: Quiz update endpoint

Task IDs: `BE-009`, `TS-007` (update slice).

Definition of done: The HTTP API can accept validated quiz edits, reject invalid quiz updates through stable domain-to-HTTP mapping, persist the updated canonical quiz structure, and return the saved result with the expected version bump.

Required tests/checks: Run `python -m pytest backend/tests/test_api_quiz_update.py -q` and expect all tests to pass. Keep `python -m pytest backend/tests -q`, `python -m pytest tests/test_repository_layout.py -q`, and `python -c "from backend.app.main import create_app"` green. Manually verify with the running server that a generated quiz can be fetched, modified, and saved.

Recommended commit breakdown:
1. `feat(api): add quiz update endpoint`
2. `test(api): cover quiz update validation and persistence flows`

## Stage 7: UI Upload, Parameters, and Result View

Task IDs: `UI-001`, `UI-002`, `UI-003`.

Rationale for grouping: This is the smallest user-facing UI slice that turns the backend into an actual product flow. The user needs one screen to upload a document, one step to choose generation parameters, and one screen to inspect the generated result.

Dependencies: Stages 5 and 6. The UI should consume the existing HTTP API rather than bypass it.

Definition of done: The repository contains a real `frontend/` implementation, separate from the concept files in `docs/design/concepts/v2/`, that allows the user to upload a document, set generation parameters, submit generation, and see the resulting quiz rendered on screen.

Required tests/checks: Keep all existing backend pytest suites green. Run the frontend locally and manually verify the upload-to-result flow in a browser. If lightweight frontend automation is added without introducing unnecessary production dependencies, keep it scoped to this flow only.

Recommended commit breakdown:
1. `feat(ui): bootstrap mvp frontend shell and api client`
2. `feat(ui): add upload, generation parameters, and result view flows`
3. `test(ui): add the smallest practical smoke coverage or document a manual browser smoke checklist`

## Stage 8: UI Quiz Editing

Task IDs: `UI-004`.

Rationale for grouping: Editing is a separate flow from generation and deserves its own review point. Keeping it isolated prevents the first UI stage from growing into a large mixed change.

Dependencies: Stage 6 for the read and update endpoints, and Stage 7 for the initial UI shell.

Definition of done: The UI can open a generated quiz, edit question text, options, correct answers, and explanations, submit valid changes to the backend, and show validation errors when the edit payload is invalid.

Required tests/checks: Keep backend API tests green. Run a manual browser smoke test that edits a quiz, refreshes the page, and confirms the saved data persists.

Recommended commit breakdown:
1. `feat(ui): add quiz editing and save flow`
2. `test(ui): verify edit-save-refresh behavior`

## Stage 9: JSON Export and MVP Closeout

Task IDs: `EX-001`, `BE-010`, `UI-005`, `TS-007` (export slice).

Rationale for grouping: JSON export is the clean closeout for the early MVP. The exporter, endpoint, and UI button form one tight delivery unit and complete the user-visible promise defined in the backlog's MVP boundary.

Dependencies: Stages 6 through 8.

Definition of done: The backend can export a quiz from the canonical domain model into a deterministic JSON file, the API exposes a download endpoint, and the UI offers an export button that downloads the JSON after generation or editing.

Required tests/checks: Run `python -m pytest backend/tests/test_json_exporter.py backend/tests/test_api_export_json.py -q` and expect all tests to pass. Manually verify in the browser that the exported file downloads with the expected name and content after editing a quiz.

Recommended commit breakdown:
1. `feat(export): add canonical json exporter and download endpoint`
2. `feat(ui): add json export action to the frontend`
3. `test(export): cover exporter and api download behavior`

## Stage 10: Generation Status and User-Facing Operation States

Task IDs: `GN-006`, `UI-007`, `LG-005`.

Rationale for grouping: Once the MVP works, the next useful improvement is visibility. Pipeline step logging, backend status models, and UI status indicators all describe one concern: helping the user and the developer understand what the system is doing while generation runs.

Dependencies: Stages 4 through 9.

Definition of done: The generation pipeline emits step-level logs, the backend can report status transitions such as `queued`, `running`, `done`, and `failed`, and the UI reflects those states without appearing frozen.

Required tests/checks: Run `python -m pytest backend/tests/test_generation_status.py backend/tests/test_logging_pipeline_steps.py -q` and expect all tests to pass. Manually verify that the UI shows meaningful status transitions during generation and when an induced failure occurs.

Recommended commit breakdown:
1. `feat(generation): add generation status model and pipeline step logging`
2. `feat(ui): surface loading, success, and error states`
3. `test(generation): cover status transitions and pipeline logging`

## Stage 11: Model Selection, Profiles, and Settings Persistence

Task IDs: `LM-006`, `CF-003`, `ST-003`.

Rationale for grouping: Per-request model selection, named generation profiles, and saved generation settings all refine how generation is configured. They change the same responsibility boundary and should be reviewed together rather than being spread across unrelated stages.

Dependencies: Stages 1 through 5, and preferably Stage 10 so status behavior already exists when new generation options are introduced.

Definition of done: The generation request path can accept a whitelisted model name, resolve a named profile such as `fast`, `balanced`, or `strict`, persist the user's most recent generation settings, and reuse those settings on the next request.

Required tests/checks: Run `python -m pytest backend/tests/test_generation_profiles.py backend/tests/test_generation_settings_repository.py backend/tests/test_model_whitelist.py -q` and expect all tests to pass. Extend existing API generation tests to cover profile and model selection.

Recommended commit breakdown:
1. `feat(config): add generation profiles and model whitelist support`
2. `feat(storage): persist generation settings`
3. `test(config): cover profiles, settings persistence, and model selection`

## Stage 12: Single-Question Regeneration

Task IDs: `BE-013`, `PM-005`, `CF-002` (single-question regeneration slice).

Rationale for grouping: Single-question regeneration is a coherent post-MVP editing enhancement. It needs one API capability, one prompt template, and one generation-mode extension, but it does not require full RAG support.

Dependencies: Stages 4 through 8 and Stage 11 if profiles should influence regeneration behavior.

Definition of done: The backend exposes an endpoint that can regenerate one question inside an existing quiz without replacing the rest of the quiz, using a dedicated prompt template and a new `single_question_regen` generation mode. The operation is verifiable through API tests even if a dedicated UI story is added later rather than now.

Required tests/checks: Run `python -m pytest backend/tests/test_single_question_regeneration.py -q` and expect all tests to pass. Manually verify through the API that only the targeted question changes.

Recommended commit breakdown:
1. `feat(prompts): add single-question regeneration prompt and mode support`
2. `feat(api): add single-question regeneration endpoint`
3. `test(generation): cover isolated question regeneration behavior`

## Stage 13: Advanced Export Formats

Task IDs: `BE-011`, `BE-012`, `EX-002`, `EX-003`, `EX-004`, `UI-006`, `TS-009`.

Rationale for grouping: DOCX and PPTX export are one family of features. The exporter mapping, two new exporters, two download endpoints, and the UI controls should be reviewed together because they all extend the same export surface.

Dependencies: Stage 9.

Definition of done: The backend can export DOCX and PPTX from the canonical `Quiz` model, select the exporter via a registry rather than `if/elif` chains, expose download endpoints, and let the UI trigger those exports only when the backend supports the target format.

Required tests/checks: Run `python -m pytest backend/tests/test_docx_exporter.py backend/tests/test_pptx_exporter.py backend/tests/test_export_registry.py backend/tests/test_api_advanced_exports.py -q` and expect all tests to pass. Open the generated files in compatible software to verify they render.

Recommended commit breakdown:
1. `feat(export): add exporter registry, docx exporter, and pptx exporter`
2. `feat(api): add docx and pptx export endpoints and ui controls`
3. `test(export): cover exporters, registry resolution, and api downloads`

## Stage 14: RAG Generation

Task IDs: `LM-005`, `PR-007`, `PM-004`, `RAG-001`, `RAG-002`, `RAG-003`, `RAG-004`, `RAG-005`, `GN-007`, `CF-002` (RAG slice), `TS-008`.

Rationale for grouping: RAG is a complete alternative generation path. Chunking, embeddings, in-memory indexing, retrieval, context assembly, prompt selection, orchestration, and mode selection must be built and validated as one coherent subsystem.

Dependencies: Stages 2 through 4, plus Stage 11 if profiles influence mode selection.

Definition of done: The backend can chunk normalized documents, compute embeddings through LM Studio, build a local in-memory document index, retrieve top-k chunks for a generation request, assemble a bounded context block, run a dedicated RAG orchestrator, and select `direct` or `rag` through the generation-mode registry and the rule-based selector.

Required tests/checks: Run `python -m pytest backend/tests/test_chunking.py backend/tests/test_embeddings_client.py backend/tests/test_retriever.py backend/tests/test_rag_orchestrator.py -q` and expect all tests to pass. Extend manual API verification to compare one direct generation request against one RAG generation request on a large enough document.

Recommended commit breakdown:
1. `feat(rag): add chunking, embeddings client, and in-memory retrieval primitives`
2. `feat(rag): add rag prompt, rag orchestrator, and mode selection logic`
3. `test(rag): cover retrieval, context assembly, and rag orchestration`

## Stage 15: Additional Providers and Feature Flags

Task IDs: `LM-007`, `LM-008`, `CF-004`.

Rationale for grouping: Provider expansion and provider feature flags are one concern. They should remain late because they widen the integration surface without improving the core single-provider MVP path.

Dependencies: Stage 3 and any stage that depends on provider selection behavior, especially Stage 11.

Definition of done: The backend can instantiate additional provider adapters such as Ollama or an external API behind the same provider interface, and feature flags can enable or disable providers centrally so disabled providers are neither initialized nor exposed.

Required tests/checks: Run `python -m pytest backend/tests/test_provider_registry.py backend/tests/test_provider_feature_flags.py -q` and expect all tests to pass. Verify that turning off a provider removes it from the available-provider list and prevents accidental use.

Recommended commit breakdown:
1. `feat(llm): add secondary provider adapters`
2. `feat(config): add provider feature flags and provider registry enforcement`
3. `test(llm): cover provider selection and disablement`

## Stage 16: RAG Caching and Reuse

Task IDs: `RAG-006`.

Rationale for grouping: Embedding and index caching optimize an already working RAG path. This should be the last stage because it adds complexity without changing the product's core capability.

Dependencies: Stage 14.

Definition of done: The backend can reuse cached embeddings and cached indexes for unchanged documents, keyed by a stable document hash, and fall back safely when a cache entry is missing or stale.

Required tests/checks: Run `python -m pytest backend/tests/test_rag_cache.py -q` and expect all tests to pass. Verify manually or through tests that repeated RAG generation requests reuse cached artifacts for identical documents.

Recommended commit breakdown:
1. `feat(rag): add embedding and index cache keyed by document hash`
2. `test(rag): cover cache hits, misses, and invalidation`

## Concrete Steps

Work from the repository root, `D:\github\diplom`. Before each stage, create a dedicated branch or worktree so the stage stays isolated and reviewable. A typical sequence is:

    git switch -c codex/stage-01-foundation

Implement only the task IDs listed for that stage. Keep all unrelated files untouched, especially `AGENTS.md` unless the user explicitly asks for instruction changes. During implementation, run the stage-specific pytest commands listed above, plus:

    python -m pytest tests/test_repository_layout.py -q

At the end of each stage, record the completed work back into this ExecPlan, then create one to three atomic commits using the recommended breakdown for that stage.

## Validation and Acceptance

The early MVP is complete after Stage 9. At that point, the following human-verifiable behavior must exist. A user can start the backend, upload one TXT, DOCX, or PDF document, choose generation parameters, trigger quiz generation through LM Studio, review the generated quiz, edit it, and export the final quiz as a JSON file. The backend API tests and the targeted unit tests for each earlier stage must all pass.

The second-wave backlog begins after Stage 9. Each later stage has its own acceptance condition and should not be pulled forward unless a dependency requires it. In particular, RAG, DOCX/PPTX export, model profile persistence, status streaming, and multi-provider work are intentionally not required to call the early MVP complete.

## Idempotence and Recovery

Each stage is designed to be independently restartable. If a stage stalls, do not jump ahead. Re-open this plan, update `Progress`, and continue from the same stage. If an implementation branch becomes messy, discard only that branch or worktree and restart the stage from the last clean commit. Because the plan keeps stages small, the cost of restarting a single stage stays low.

Do not mix repository-organization edits, planning-doc edits, or `AGENTS.md` changes into feature stages unless the user explicitly broadens the scope. Those changes are not dependencies for the delivery stages and would make review noisier.

## Artifacts and Notes

Current integrated state:

    0fa0789 merge(stage1): integrate foundation skeleton
    c74f97d merge(stage2): integrate txt ingestion batch 1
    cd570dd merge(stage2): integrate docx ingestion batch 2
    75fa87c merge(stage2): integrate pdf ingestion batch 3
    88dc67f merge(stage3): integrate lm client batch 1
    b65f58d merge(stage3): integrate lm healthcheck batch 2
    3c595a2 merge(stage4): integrate prompt registry batch 1
    43ce420 merge(stage4): integrate normalization batch 2
    b70ff27 merge(stage4): integrate orchestrator batch 3
    6094481 merge(stage5): integrate api health batch 1
    53eb42a merge(stage5): integrate upload and generate batch 2
    752cb26 merge(stage6): integrate quiz read batch 1

Current backlog completion status:

    Stage 1: integrated on main
    Stage 2: integrated on main
    Stage 3: integrated on main
    Stage 4: integrated on main
    Stage 5 Batch 1 (`BE-004`, `BE-005`, `LG-002`, `LG-004`, `TS-007` health slice): integrated on main
    Stage 5 Batch 2 (`BE-006`, `BE-007`, `TS-007` upload/generate slice): integrated on main
    Stage 5: fully integrated on main
    Stage 6 Batch 1 (`BE-008`, `TS-007` read slice): integrated on main

Next recommended stage:

    Stage 6: API Quiz Read and Update

Next recommended batch:

    Stage 6 Batch 2: Quiz update endpoint

## Interfaces and Dependencies

The early MVP should converge on the following stable interfaces and boundaries:

    backend/app/core/config.py
      Loads runtime configuration and validates required environment variables.

    backend/app/domain/models.py
      Defines document, quiz, question, option, generation request, and generation result models.

    backend/app/domain/errors.py
      Defines domain-specific exceptions that later map cleanly to API errors.

    backend/app/storage/documents.py
      Provides document repository operations for filesystem-backed storage.

    backend/app/storage/quizzes.py
      Provides quiz repository operations for filesystem-backed storage.

    backend/app/parsing/
      Holds file validation, parser implementations, and document normalization.

    backend/app/llm/
      Holds the provider interface and LM Studio client implementation.

    backend/app/prompts/
      Holds prompt registry entries and prompt builders.

    backend/app/generation/
      Holds request assembly, orchestration, repair-loop logic, and mode selection.

    backend/app/api/
      Holds the HTTP surface only after the non-HTTP layers are already stable.

    frontend/
      Holds the runnable web UI and remains distinct from `docs/design/concepts/v2/`.

Dependencies are intentionally conservative. No production dependency should be added unless the standard library or the chosen existing stack is insufficient. PDF and DOCX parsing, DOCX/PPTX export, and the HTTP server will likely require implementation dependencies, but those choices should be introduced only in the stages that need them and justified in the corresponding commits.

Revision note: Created this ExecPlan to turn the backlog into small, verifiable delivery stages after the repository cleanup was completed and before any feature code was started.
