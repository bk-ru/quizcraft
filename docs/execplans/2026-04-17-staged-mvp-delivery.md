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
- [x] (2026-04-19) Implemented, reviewed, and integrated Batch 2 of Stage 6 on `main` via merge commit `e29e229`, covering `BE-009` and the update slice of `TS-007` with persisted quiz update behavior, canonical-structure preservation, domain validation, version bumping, and timestamp refresh on save.
- [x] (2026-04-19) Completed and integrated all of Stage 6 on `main`, covering both quiz read and quiz update API flows.
- [x] (2026-04-20) Integrated the Cyrillic compatibility audit/fix on `main` via merge commit `dd0861f`, adding targeted UTF-8 JSON persistence fixes, a Russian fallback quiz title, and Russian-language regression coverage across implemented parsing, storage, normalization, generation, and API flows.
- [x] (2026-04-20) Implemented, reviewed, and integrated Batch 1 of Stage 7 on `main` via merge commit `3ebc9d1`, covering the thin `frontend/` shell, plain JavaScript API client foundation, frontend runtime config, and minimal smoke coverage.
- [x] (2026-04-20) Implemented, reviewed, and integrated Batch 2 of Stage 7 on `main` via direct commits `b5f9cf7`, `79a9e51`, and `5762736`, covering the upload surface, generation parameter form, UTF-8-safe submit flow to the current backend API, and frontend smoke coverage with Russian UI text.
- [x] (2026-04-22) Implemented, reviewed, and integrated Batch 3 of Stage 7 on `main` via merge commit `a7f3cd3`, covering `UI-003` with the result view, plain JavaScript rendering of generated quiz content, loading/error/result states, and Russian-language smoke coverage.
- [x] (2026-04-22) Completed and integrated all of Stage 7 on `main`, covering the full upload-to-result frontend flow.
- [x] (2026-04-22) Implemented, reviewed, and integrated Batch 1 of Stage 8 on `main` via merge commit `16fc33b`, covering the quiz edit read-shell with persisted quiz loading into editable Russian/Cyrillic fields and frontend smoke coverage.
- [x] (2026-04-22) Implemented, reviewed, and integrated Batch 2 of Stage 8 on `main` via merge commit `7082baf`, covering the quiz save flow, validation-state handling, save-and-reload persistence behavior, and Russian/Cyrillic smoke coverage.
- [x] (2026-04-22) Completed and integrated all of Stage 8 on `main`, covering the full quiz edit flow from load through validated save and reload.
- [x] (2026-04-23) Implemented, reviewed, and integrated Batch 1 of Stage 9 on `main` via merge commit `9c4330a`, covering `EX-001`, `BE-010`, and the export slice of `TS-007` with the canonical JSON exporter, the `GET /quizzes/{quiz_id}/export/json` download endpoint, and exporter/API pytest coverage.
- [x] (2026-04-23) Integrated an unplanned API quality hardening batch on `main` via merge commit `11bf5eb`, covering Pydantic-based request bodies, enum whitelists for `difficulty`, `quiz_type`, and `language`, strict numeric coercion rejection, a controlled `413` response for oversized documents, and the initial `pyproject.toml`, Ruff, and GitHub Actions CI tooling.
- [x] (2026-04-23) Implemented, reviewed, and integrated Batch 2 of Stage 9 on `main` via merge commit `bc93358` (PR #2), covering `UI-005` with the frontend JSON export action; the same merge also bundled a broader 2026 UI redesign (stepper, dark mode, visual refresh) and two follow-up fixes (`bbe3fd8`, `9c66adb`).
- [x] (2026-04-23) Completed and integrated all of Stage 9 on `main`, closing the early MVP per the Validation and Acceptance section: a user can upload a document, generate a quiz through LM Studio, review, edit, and export the final quiz as JSON.
- [x] (2026-04-23) Fixed the MVP-blocking frontend generation timeout on `main` via merge commit `d964ad1` (PR #3, feature commit `2f24024`), replacing the single 8 s `requestTimeoutMs` with role-based timeouts (`health` 5 s, `upload` 30 s, `generate` 120 s, `quizEditor` 15 s), also guarding the JSON export `fetch` with `AbortController`, returning a Russian-language timeout error, and adding smoke coverage for the new configuration shape.
- [x] (2026-04-23) Integrated post-MVP frontend UX polish Batch 1 on `main` via commit `eb1f79b`, three coherent user-facing improvements: (1) auto-load the freshly generated quiz into the editor so no manual `quiz_id` paste is required, (2) collapse `Document ID`, `Quiz ID`, `Request ID`, `Модель`, and `Prompt version` into `<details class="inline-details">` blocks with Russian summaries, (3) escalate LM Studio `unavailable` from `warn` to `bad` with a Russian topbar marker plus a toast/log instruction pointing to `http://127.0.0.1:1234`.
- [x] (2026-04-23) Integrated post-MVP frontend UX polish Batch 2 on `main` via commit `99529e2`, two operation-feedback improvements that partially cover Stage 10 task `UI-007` without requiring `GN-006`: (1) `describeValidationError` translates backend 422 responses into Russian field labels and messages through a `VALIDATION_FIELD_EXACT_LABELS` registry plus nested `quiz.questions.N.*` and `options.M.*` regex handlers and a `VALIDATION_MESSAGE_RULES` dictionary, wired into both `submitQuizEdits` and `submitGeneration`; (2) a pseudo-step generation progress panel (`#generation-progress`) with four Russian labels `Загружаем документ → Парсим → Генерируем → Валидируем` and a per-state styling (pending/active/done/failed), driven by `startGenerationProgress` / `advanceGenerationProgress` / `completeGenerationProgress` / `failGenerationProgress`.
- [x] (2026-04-24) Implemented, reviewed, and integrated Stage 10 Batch 1 on `main` via merge commit `05ff078`, covering `GN-006` and `LG-005` with the backend generation status model, controlled status transitions, and structured pipeline step logging around parse, generate, repair, and persist phases.
- [x] (2026-04-24) Implemented, reviewed, and integrated Stage 10 Batch 2 on `main` via merge commit `3e816de`, covering the remaining `UI-007` slice by aligning the existing plain-JS progress UI with backend status evidence when available while preserving Russian/Cyrillic-safe rendering and avoiding a visual redesign.
- [x] (2026-04-24) Completed and integrated all of Stage 10 on `main`, covering backend generation status, pipeline step logging, and frontend progress behavior aligned with backend evidence.
- [x] (2026-04-24) Implemented, reviewed, and integrated Stage 11 Batch 1 on `main` via merge commit `e212758`, covering `LM-006` and the `CF-003` model/profile slice with model whitelist configuration, request-time model validation, named generation profile resolution, default profile behavior, and backward-compatible generation requests.
- [x] (2026-04-24) Implemented, reviewed, and integrated Stage 11 Batch 2 on `main` via merge commit `10c00e0`, covering `ST-003` and the remaining settings portion of `CF-003` with local generation settings persistence, minimal settings API support, saved-settings reuse as generation defaults, model/profile compatibility, and backward-compatible generation requests.
- [x] (2026-04-24) Completed and integrated all of Stage 11 on `main`, covering model selection, generation profiles, and settings persistence/reuse.
- [x] (2026-04-24) Implemented, reviewed, and integrated Stage 12 Batch 1 on `main` via merge commit `651daed`, covering the `BE-013` API/request-contract slice with the single-question regeneration endpoint, strict request validation, quiz lookup, target question lookup, controlled not-found and validation errors, and explicit no-provider/no-mutation contract evidence.
- [x] (2026-04-24) Implemented, reviewed, and integrated Stage 12 Batch 2 on `main` via merge commit `98c5b48`, covering `PM-005` and the `CF-002` single-question regeneration mode slice with the targeted prompt template, `single_question_regen` mode support, provider request builder/orchestration path, profile/settings compatibility, isolated target-question replacement, and persisted quiz updates through the existing quiz repository.
- [x] (2026-04-24) Implemented, reviewed, and integrated Stage 12 Batch 3 on `main` via merge commit `8accaec`, closing the frontend UI wiring for isolated question regeneration. Feature commits on the branch: `e78ae6d` (feat(frontend): add single-question regeneration action), `8616e0d` (feat(frontend): update quiz view after isolated regeneration), and `b15d829` (test(frontend): cover single-question regeneration smoke paths). Russian/Cyrillic UI preservation is verified by the shell tests, and the rest of the quiz stays unchanged outside the targeted question.
- [x] (2026-04-24) Integrated a comprehensive post-MVP frontend UX polish pass on `main` under the same merge commit `8accaec`, split into three in-branch batches. Batch P1 unifies the shell (commits `1d69faa`, `c3017ff`, `8f2574d`, `133dafb`, `b346959`): four-phase stepper as single source of truth, dropzone preview with remove, confirm dialog before destructive regeneration, model/profile selectors driven by `/generation/settings`, and removal of the global diagnostics panel. Batch P2 sharpens feedback (commits `4cffb47`, `6a9257b`, `655994d`, `975293b`, `732571a`, `a252a3a`): failed review phase highlight, real empty state in the idle result panel, auto-persisted defaults hint plus post-generation refresh, Ctrl/⌘+Enter/S/. keyboard shortcuts, copy buttons for quiz/document IDs, and removal of duplicate stepper phases inside panel headings. Batch P3 polishes the surface (commits `e90f918`, `ed4476d`, `b4804e1`): compact hero with reduced-motion-guarded pulse, per-theme icon in the theme toggle, and accessibility hooks for disabled actions plus elevated `role="alert"` for error toasts.
- [x] (2026-04-24) Integrated a dev-experience batch on `main` under the same merge commit `8accaec`, feature commit `bf030d3`. Adds a dotenv-style loader to `AppConfig.from_env` (with `QUIZCRAFT_ENV_FILE` override), lazy FastAPI app export in `backend/app/main.py`, a committed `.env.example`, PowerShell helpers `run-backend.ps1` and `run-frontend.ps1`, `.gitignore` entries for `.env`, `.env.local`, and `*.egg-info/`, and a README "Running Locally" section that documents the new one-command flow. Backend tests isolate `QUIZCRAFT_ENV_FILE` so the real `.env` cannot leak into CI.
- [x] (2026-04-24) Integrated a config hotfix on `main` via merge commit `bdfca15`, feature commit `1e083ac`. Raises the default `REQUEST_TIMEOUT` from 30 to 300 seconds, matching the `.env.example` template, so fresh installs no longer 504 on slow local CPU inference through LM Studio. Evidence: a regression test pins the 300-second default; shell variables and a loaded `.env` file continue to override it.
- [x] (2026-04-24) Completed and integrated all of Stage 12 on `main`, closing the single-question regeneration stage (backend endpoint, generation-mode prompt and pipeline, and frontend UI wiring).
- [x] (2026-04-25) Synced this ExecPlan to Stage 13 entry state on `main` via merge commit `2254813`, feature commit `ee4bd7c`. Updated `Outcomes & Retrospective` to point at Stage 13 as the next stage, refreshed `Context and Orientation` to reflect the implemented runtime layout, fixed the repository root path under `Concrete Steps`, and split the Stage 13 commit breakdown into five batches.
- [x] (2026-04-25) Implemented, reviewed, and integrated Stage 13 Batch 1 on `main` via merge commit `9c1e7ef`, feature commit `4f16f2e`. Adds the `QuizExporter`/`ExportedQuizFile` contract and `QuizExportRegistry` under `backend/app/export/`, routes the existing JSON exporter through the registry, preserves `GET /quizzes/{quiz_id}/export/json` backward compatibility, and adds focused tests for registry resolution, unsupported-format errors, and Russian/Cyrillic content preservation through the registry.
- [x] (2026-04-25) Implemented, reviewed, and integrated Stage 13 Batch 2 on `main` via merge commit `48fd6ae`, feature commit `385392c`. Adds `QuizDocxExporter` using `python-docx`, registers it in `DEFAULT_QUIZ_EXPORT_REGISTRY`, and covers it with tests for openable DOCX files, registry exposure, Russian/Cyrillic content preservation, and validation of `correct_option_index`.
- [x] (2026-04-25) Implemented, reviewed, and integrated Stage 13 Batch 3 on `main` via merge commit `d4fe651`, feature commit `12b4747`. Adds `QuizPptxExporter` using `python-pptx` with one slide per question, registers it in `DEFAULT_QUIZ_EXPORT_REGISTRY`, and covers it with tests for openable PPTX files, registry exposure, Russian/Cyrillic content preservation, and validation of `correct_option_index`.
- [x] (2026-04-25) Implemented, reviewed, and integrated Stage 13 Batch 4 on `main` via merge commit `95774a4`, feature commit `c4cb067`. Adds `GET /quizzes/{quiz_id}/export/{export_format}` and `GET /export/formats` to the quiz API while keeping `GET /quizzes/{quiz_id}/export/json` backward compatible, routes downloads through the registry, and adds API tests for the new endpoints (including an `unsupported_export_format` 400 case) with Russian/Cyrillic body content.
- [x] (2026-04-25) Implemented, reviewed, and integrated Stage 13 Batch 5 on `main` via merge commit `7acc1c7`, feature commit `46c2009`. Adds `QuizCraftApiClient.getExportFormats()`, refactors `frontend/download.js` into a generic `createQuizExporter` (JSON/DOCX/PPTX) while keeping `createJsonExporter` backward compatible, adds DOCX and PPTX result-actions buttons in `frontend/index.html` with Russian-language a11y hints, wires capability-driven enable/disable in `frontend/app.js` from `/export/formats` (with a graceful warn fallback when the capability fetch fails), and extends `tests/test_frontend_shell.py` smoke coverage for the API client method, the new buttons, and the capability-driven wiring.
- [x] (2026-04-25) Completed and integrated all of Stage 13 on `main`, closing the advanced export formats stage end-to-end: export registry, DOCX exporter, PPTX exporter, advanced quiz export endpoints with capability reporting, and capability-driven frontend export controls preserving the existing JSON action.
- [x] (2026-04-25) Synced this ExecPlan to Stage 13 completion state on `main` via merge commit `4da1f50`, feature commit `b88c6a3`. Recorded Progress entries for Stage 13 Batches 1–5 and the Stage 13 closeout, extended `Outcomes & Retrospective` and `Context and Orientation` to include Stage 13 (advanced export formats), appended the Stage 13 merge commits to `Artifacts and Notes / Current integrated state`, added the Stage 13 entries to `Current backlog completion status`, and switched `Next recommended stage` to Stage 14 RAG Generation.
- [x] (2026-04-25) Implemented, reviewed, and integrated Stage 14 Batch 1 on `main` via merge commit `a8b2ad9`, feature commits `50bd844` (`feat(parsing): add deterministic text chunker for retrieval`) and `47e3cd0` (`feat(llm): add lm studio embeddings client`). Adds `backend/app/parsing/chunking.py` with `TextChunk` plus `chunk_text(text, *, chunk_size, overlap)` returning deterministic overlapping character chunks (`DomainValidationError` for invalid inputs, empty text returns an empty tuple, no extra step after the chunk reaches end of text), wires `LMStudioClient.embed` to LM Studio `/v1/embeddings` through the existing `RetryingCaller` (refactored shared `_post_json(path, payload)` helper, response items sorted by `index` with controlled `LLMResponseFormatError` on count mismatch or non-numeric vectors), and tightens `EmbeddingRequest.__post_init__` to reject empty/blank/non-string texts and blank `model_name`. Adds `backend/tests/test_chunking.py` and `backend/tests/test_lm_studio_embeddings.py` covering positive Russian/Cyrillic round-trip flows, retry-on-timeout/503 behavior, malformed-response branches, and `EmbeddingRequest` validation negatives.
- [x] (2026-04-25) Implemented, reviewed, and integrated Stage 14 Batch 2 on `main` via merge commit `e8350c8`, feature commits `d0da510` (`feat(generation): add chunk embeddings and in-memory vector index`) and `89cb3f9` (`feat(generation): add bounded retrieval context assembler`). Adds `backend/app/generation/retrieval.py` with `EmbeddedChunk`, `ScoredChunk`, the `embed_chunks(chunks, *, provider, model_name=None, batch_size=32)` helper that batches embedding requests through any `LLMProvider` and validates the response length, and the `InMemoryVectorIndex(embedded_chunks)` class exposing `__len__`, `dimension`, `embedded_chunks`, and `search(query_vector, *, top_k)` with deterministic cosine-similarity ranking (insertion-order tie-break, top-`k` clamping, controlled `DomainValidationError` for empty vectors, mixed dimensions, dimension mismatch, non-positive `top_k`, or string query vectors). Adds `backend/app/generation/context.py` with `assemble_context(scored_chunks, *, max_chars, separator='\n\n')` that joins retrieved chunks in supplied order, stops when the next chunk would exceed `max_chars`, truncates the first chunk if it alone exceeds `max_chars`, returns `""` for empty input, and rejects non-positive `max_chars`, non-string `separator`, or non-`ScoredChunk` entries. Adds `backend/tests/test_retrieval.py` and `backend/tests/test_context_assembler.py` covering Russian/Cyrillic positive flows (Москва, Россия, Питер, Беларусь, Кемерово), batched embedding requests through a `FakeEmbeddingProvider` stub, deterministic tie-break, empty-index/zero-vector edge cases, dimension validation, and full input-validation negatives.
- [x] (2026-04-25) Implemented, reviewed, and integrated Stage 14 Batch 3 on `main` via merge commit `63c890c`, feature commits `ce174a4` (`feat(rag): register rag mode and add master prompt`), `0b22c32` (`feat(rag): add rule-based direct vs rag mode selector`), and `7ba075e` (`feat(rag): add rag generation orchestrator`). Adds `GenerationMode.RAG` to `backend/app/core/modes.py`, registers a versioned `rag_generation` master prompt (`rag-v1`, `quiz_payload` schema, `{retrieved_context}` template) in `backend/app/prompts/registry.py`, adds `backend/app/generation/mode_selector.py` with `select_generation_mode(*, requested_mode, document_length_chars, rag_threshold_chars=DEFAULT_RAG_THRESHOLD_CHARS=6000)` that promotes `direct` to `rag` once the document exceeds the threshold while passing `rag` and `single_question_regen` through unchanged, and adds `backend/app/generation/rag_orchestrator.py` with `RagGenerationOrchestrator` running the full `parse → chunk → embed → retrieve → assemble → generate → validate → repair → persist` pipeline through the existing `LLMProvider`, `RetryingCaller`, `GenerationQualityChecker`, and pipeline-step logging surface. Adds `backend/tests/test_rag_prompt.py`, `backend/tests/test_mode_selector.py`, and `backend/tests/test_rag_orchestrator.py` with Russian/Cyrillic fixtures (Москва, Санкт-Петербург, Кемерово) covering the prompt registry, the selector across requested-mode/threshold/Cyrillic-length combinations, and orchestrator end-to-end flows including chunked embedding, retrieved-context propagation into the structured request, repair after quality failure, repair exhaustion, non-RAG-mode rejection, oversized-document guard, empty-document rejection, and invalid construction parameters. Updates `backend/tests/test_api_health.py` (`generation_modes` now includes `"rag"`) and `backend/tests/test_domain_models.py` (unknown-mode test now uses `hybrid_super_mode` instead of `rag`).
- [x] (2026-04-25) Completed and integrated Stage 14 primitives on `main`, closing the RAG generation primitives end-to-end (chunker, LM Studio embeddings client, in-memory vector index, top-`k` retriever, bounded context assembler, RAG master prompt, RAG generation orchestrator, and rule-based direct/RAG mode selector). The current generation API endpoint still routes only through `DirectGenerationOrchestrator`; the explicit wiring of `RagGenerationOrchestrator` and `select_generation_mode` into the runtime API path is deliberately deferred to Stage 14 Batch 4, recorded in `Surprises & Discoveries` for visibility.
- [x] (2026-04-25) Implemented, reviewed, and integrated Stage 14 Batch 4 on `main` via merge commit `19300f1`, feature commits `9688edb` (`feat(generation): add orchestrator dispatcher routing direct and rag`) and `8c2b0fb` (`feat(api): wire generation dispatcher into POST /documents/{id}/generate`). Adds `backend/app/generation/dispatcher.py` with `GenerationOrchestratorDispatcher` (constructor takes `direct_orchestrator`, `rag_orchestrator`, `document_repository`, optional `rag_threshold_chars=DEFAULT_RAG_THRESHOLD_CHARS=6000` validated against booleans and non-positive integers, exposes a `rag_threshold_chars` property; `dispatch(document_id, generation_request)` loads the document via the repository, applies `select_generation_mode` against `len(document.normalized_text)`, replaces the request's `generation_mode` via `dataclasses.replace` only when the resolved mode differs from the requested one, routes resolved `rag` to `RagGenerationOrchestrator.generate`, resolved `direct` to `DirectGenerationOrchestrator.generate`, and raises `UnsupportedGenerationModeError` for `single_question_regen` or unknown modes; `RepositoryNotFoundError` propagates unchanged). Wires the dispatcher into the runtime through `backend/app/api/runtime.py` (adds `get_rag_generation_orchestrator(app)` and `get_generation_dispatcher(app)` lazy builders that share the same filesystem-backed `FileSystemDocumentRepository`, `FileSystemQuizRepository`, `FileSystemGenerationResultRepository`, `app.state.provider`, `GenerationQualityChecker()`, and `max_document_chars=app.state.config.max_document_chars`) and updates `backend/app/api/generation.py` so that `POST /documents/{document_id}/generate` calls `get_generation_dispatcher(...).dispatch(...)` instead of the direct-only orchestrator while preserving settings persistence and request-id serialization. Exports `GenerationOrchestratorDispatcher` through `backend/app/generation/__init__.py`. Adds `backend/tests/test_orchestrator_dispatcher.py` (13 tests with stub orchestrators and stub repository covering direct-below-threshold routing, direct-above-threshold promotion to rag, explicit `rag` below threshold, request not mutated when mode unchanged, mode replacement on promotion, `single_question_regen` rejection, `RepositoryNotFoundError` propagation, custom `rag_threshold_chars=10` promoting at length 11, Cyrillic normalized length used for selection, non-positive and boolean threshold rejection, and the `rag_threshold_chars` property) and `backend/tests/test_api_generation_rag.py` (8 integration tests with `FastAPI TestClient` and a `StubRagApiProvider` that handles both `embed` and `generate_structured`, covering explicit `generation_mode=rag` returning `prompt_version=rag-v1` with a Cyrillic quiz round-trip, embed called twice (chunks batch + retrieval query), retrieved context propagated into the structured request `user_prompt`, `direct` promoted to `rag` when the document exceeds 6000 characters, `direct` below threshold staying on the direct path with `prompt_version=direct-v1` and zero embed calls, `single_question_regen` rejected with `400 unsupported_generation_mode` and zero provider calls, oversized document mapped to `413 document_too_large_for_generation` through the RAG path, and a Russian quiz round-trip preserving Москва, Санкт-Петербург, Кемерово and the explanation `"Столицей России является Москва."`). Existing direct-path tests in `backend/tests/test_api_upload_and_generate.py` stay green without changes because the dispatcher routes small documents to the direct orchestrator without ever calling `embed`.
- [x] (2026-04-25) Completed and integrated all of Stage 14 end-to-end on `main`, closing the RAG generation stage including the runtime API wiring. `POST /documents/{document_id}/generate` now dispatches between the direct and RAG orchestrators through `GenerationOrchestratorDispatcher` and `select_generation_mode`, the deferred-API-wiring observation in `Surprises & Discoveries` is resolved, and the next contributor should start from Stage 15 (Additional Providers and Feature Flags). Known follow-ups (not blockers): exposing `rag_threshold_chars` through `AppConfig` (env `RAG_PROMOTION_THRESHOLD_CHARS`), avoiding the dispatcher's double document load on the RAG path, surfacing the resolved generation mode in the API response, and adding a frontend mode toggle that lets the user pick `direct`/`rag` directly instead of relying on the persisted `/generation/settings` value.
- [x] (2026-04-25) Implemented, reviewed, and integrated post-Stage 14 UX quick wins Batch A on `main` via merge commit `c3adbc0`, feature commit `788b726` (`fix(frontend): batch A ux quick wins`). Three independent UX-hardening fixes bundled into one reviewable slice: (1) question regeneration now preserves the original quiz language instead of hard-coding `"ru"` — `frontend/quiz-history.js` extends `normalizeEntry` and `saveQuizToHistory({quiz_id, title, language})` to persist the language alongside the quiz id, exposes a new `findLanguageByQuizId(quizId)` lookup, `frontend/generation-flow.js` forwards `generationBody.language` when saving the just-generated quiz to history, and `frontend/quiz-editor.js` accepts a `getLanguageForQuiz` callback (wired to `quizHistory.findLanguageByQuizId` from `frontend/app.js`), introduces `editorState.loadedQuizLanguage`, encapsulates the fallback in `resolveQuizLanguage(quizId)` and `DEFAULT_REGENERATION_LANGUAGE = "ru"`, and forwards the resolved language to `client.regenerateQuestion`; (2) the active stepper item now exposes `aria-current="step"` so screen readers announce the current step instead of relying on `data-state` styling alone (`frontend/progress.js` `setStepState` toggles the attribute on every state transition); (3) the page now warns the user before unloading whenever `editorState.isDirty` is true (a `window.beforeunload` listener in `frontend/app.js` short-circuits when the editor is clean and otherwise sets `event.returnValue = ""` so browsers display their native confirmation). Adds 6 new positive smoke tests in `tests/test_frontend_shell.py` (`test_frontend_quiz_history_persists_language_for_regeneration`, `test_frontend_generation_flow_records_language_in_history`, `test_frontend_editor_uses_recorded_language_for_question_regeneration`, `test_frontend_editor_falls_back_to_russian_when_language_is_unknown`, `test_frontend_progress_marks_active_step_with_aria_current`, `test_frontend_app_warns_before_unloading_dirty_editor`); cumulative test count is 356 (was 350 + 6 new), all green. Stage 15 remains the next recommended stage; this batch is recorded as ongoing post-Stage 14 UX hardening on top of `main`.
- [x] (2026-04-25) Implemented, reviewed, and integrated post-Stage 14 UX Batch B on `main` via merge commit `942e9d7`, feature commit `935eaa3` (`feat(frontend): expose generation_mode selector and surface resolved mode`). Closes the Stage 14 frontend follow-up that was previously listed as a known-not-blocker by giving the user explicit control over the generation mode and visible feedback about the resolved mode after generation. Adds a `<select id="generation-mode" name="generation_mode">` to the parameters panel of `frontend/index.html` next to the language/model/profile fields with two Russian-labelled options: `direct` (default, "Прямая (с авто-RAG для длинных документов)") and `rag` ("RAG (всегда использовать поиск по документу)"). `frontend/generation-flow.js` replaces the previous hard-coded `generationMode` with a whitelist-driven read: a new `SUPPORTED_REQUEST_MODES = Object.freeze(["direct", "rag"])` plus `formData.get("generation_mode")` parses the user's choice and falls back to `DEFAULT_GENERATION_MODE` only when the value is missing or unsupported. Backward-compatible with `GenerationOrchestratorDispatcher`: `direct` still triggers automatic promotion to `rag` for documents above 6000 characters; `rag` always forces the RAG path. Adds a new "Режим" slot to the result-overview (`<dd id="quiz-generation-mode">`) so the actually used mode is visible without expanding the technical-details disclosure, and `frontend/quiz-renderer.js` now exports `describeGenerationMode(promptVersion)` mapping `rag-*` to `"RAG (поиск по документу)"`, `direct-*` to `"Прямая"`, `single_question_regen-*` to `"Регенерация одного вопроса"`, with `"Не указан"` as the safe fallback; `clearQuizResult`/`renderQuizResult` populate the new slot through the helper. Adds 4 new positive smoke tests in `tests/test_frontend_shell.py` (`test_frontend_index_exposes_generation_mode_selector`, `test_frontend_index_surfaces_resolved_generation_mode_in_result`, `test_frontend_generation_flow_forwards_requested_generation_mode`, `test_frontend_quiz_renderer_describes_generation_mode_from_prompt_version`); cumulative test count is 360 (was 356 + 4 new), all green. The legacy `test_frontend_hero_is_compact_and_pulse_is_not_infinite` is updated to reflect the new policy: the no-selector and no-FormData-read assertions are removed because they encoded the previous "hidden mode constant" decision that this batch deliberately reverses, while the hero-compactness, pulse-animation, and `DEFAULT_GENERATION_MODE` fallback-constant checks remain in place.
- [x] (2026-04-25) Implemented, reviewed, and integrated post-Stage 14 UX Batch C on `main` via merge commit `2bf78ee`, feature commit `652a501` (`feat(frontend): add custom confirm modal and cancel for question regeneration`). Replaces the native `globalThis.confirm` dialog used for the destructive single-question regeneration with a styled, accessible confirm modal, and adds the ability to cancel an in-flight regeneration request through both a visible cancel button and the Esc shortcut. Closes audit issues 2.3 (native `confirm()` jarring on the polished UI) and 2.4 (no cancel for in-flight question regeneration). Adds `frontend/modal.js` exposing `createConfirmModal({modalRegion, documentRef, windowRef})` built on the native `<dialog>` element (free focus trap, `::backdrop` dimming, Esc handling) that resolves a `Promise<boolean>` on confirm/cancel/backdrop click and restores focus to the previously focused element on close. Adds a `<div id="modal-region" class="modal-region">` mount point in `frontend/index.html` next to the toast region. Adds `.modal-region`, `.confirm-modal`, `.confirm-modal::backdrop`, title/body typography, and the action row with primary/ghost button styling to `frontend/feedback.css`, with a motion-respecting entry animation guarded by `prefers-reduced-motion: no-preference`. Extends `frontend/api/client.js` so `regenerateQuestion(quizId, questionId, payload, {signal})` accepts and forwards an optional `AbortSignal` to the shared `_request` helper. Refactors `frontend/quiz-editor.js` to: (a) replace the synchronous `globalThis.confirm` fallback with a `Promise<boolean>` `defaultConfirmAction`; (b) split the destructive copy into `REGENERATE_CONFIRM_TITLE` ("Перегенерировать вопрос?"), `REGENERATE_CONFIRM_BODY` (Russian explanation about untouched edits), `REGENERATE_CONFIRM_LABEL` ("Перегенерировать"), and `REGENERATE_CONFIRM_CANCEL_LABEL` ("Оставить как есть") and route them through `await askForConfirmation({title, body, confirmLabel, cancelLabel, tone: "warn"})`; (c) track an `activeRegenerationController` in module scope, allocate a fresh `AbortController` per regenerate request, forward its `signal` to the API client, distinguish cancellation (status 0 + `signal.aborted`) from generic errors with dedicated Russian status copy ("Регенерация отменена пользователем."), and reset the controller in a `finally` block; (d) render a hidden `cancel-regenerate-question` button per editor card that becomes visible while busy through `setRegenerationActionState`; (e) export `cancelActiveRegeneration()` for external callers. Wires the new pieces in `frontend/app.js`: imports `createConfirmModal`, locates `modal-region`, builds a shared `confirmModal` and passes its `confirm` method as `confirmAction` into `createQuizEditor`, and adds a click listener on `quizEditorFields` that delegates clicks on `cancel-regenerate-question` buttons to `quizEditor.cancelActiveRegeneration()`. Extends `frontend/keyboard.js` so Esc tries `quizEditor.cancelActiveRegeneration()` after the primary generation cancel and before the toast dismissal fallback, giving keyboard users a consistent cancel affordance. Tests: rewrites `test_frontend_editor_confirms_destructive_regenerate_action` for the new contract (`REGENERATE_CONFIRM_TITLE`/`BODY`, `Promise.resolve(true)`, no `globalThis.confirm`, `const confirmed = await askForConfirmation({` before the regenerate API call). Adds 8 new positive smoke tests in `tests/test_frontend_shell.py` (`test_frontend_modal_module_exposes_createConfirmModal`, `test_frontend_index_mounts_modal_region`, `test_frontend_modal_region_is_styled_in_feedback_css`, `test_frontend_app_wires_confirm_modal_into_quiz_editor`, `test_frontend_app_attaches_cancel_regeneration_listener`, `test_frontend_editor_renders_cancel_button_for_active_regeneration`, `test_frontend_editor_aborts_in_flight_regeneration_request`, `test_frontend_api_client_forwards_signal_for_question_regeneration`, `test_frontend_keyboard_shortcut_cancels_active_regeneration`); cumulative test count is 369 (was 360 + 9 new), all green. Russian/Cyrillic copy preserved across the modal, the editor cancel state, the toast text, and the Esc-cancellation status. Stage 15 remains the next recommended stage; this batch is recorded as the final post-Stage 14 UX hardening slice.
- [x] (2026-04-26) Started Stage 15 Batch 1 planning on branch `codex/stage-15-batch-1-provider-registry` from a clean, synchronized `main` state. Scope is limited to `CF-004`: provider feature flags, typed registry/enforcement on top of the existing LM Studio provider, runtime wiring, and focused positive/negative tests with Russian/Cyrillic generation coverage. Concrete Ollama and external API adapters remain deferred to Stage 15 Batches 2 and 3.
- [x] (2026-04-26) Implemented, reviewed, and integrated Stage 15 Batch 1 on `main` via merge commit `41e829c`, feature commit `44f36f7`. Adds `PROVIDERS_ENABLED` parsing/validation to `AppConfig`, a typed `ProviderName`/`ProviderRegistry` enforcement layer over the existing LM Studio provider, provider-disabled API error mapping, `/health` enabled-provider reporting, and positive/negative pytest coverage including Russian/Cyrillic generation and embedding examples. No new concrete provider adapters or production dependencies were added; Ollama and external API adapters remain deferred.
- [x] (2026-04-26) Started Stage 15 Batch 2 planning on branch `codex/stage-15-batch-2-ollama-provider` from a clean, synchronized `main` state. Scope is limited to `LM-007`: add an Ollama adapter implementing the existing `LLMProvider` contract for healthcheck, structured generation, and embeddings, register it behind the Stage 15 Batch 1 provider registry/enforcement path, and add focused positive/negative tests including Russian/Cyrillic examples. External API adapters, frontend provider selection, and broad generation request contract changes remain deferred.
- [x] (2026-04-26) Implemented, reviewed, and integrated Stage 15 Batch 2 on `main` via merge commit `d735974`, feature commit `c80424f`, planning commit `ecca475`. Adds `OllamaClient` implementing `LLMProvider` healthcheck, structured generation, and embeddings over the native Ollama HTTP API without new production dependencies; extends `AppConfig` with Ollama base URL/model/embedding-model settings and default-provider resolution from `PROVIDERS_ENABLED`; wires provider construction through `ProviderRegistry` while avoiding disabled-provider initialization for normal Ollama-only runtime; adds `/health/ollama` and active-provider generation coverage with Russian/Cyrillic examples. External API adapters, frontend provider selection, and request-contract provider selection remain deferred.
- [ ] Revisit this plan after each completed stage and update `Progress`, `Decision Log`, and `Outcomes & Retrospective` before starting the next stage.

## Surprises & Discoveries

- Observation: The repository now contains executable backend and frontend source code through Stage 8, while some older narrative plan text still reflects the earlier planning-only state.
  Evidence: `backend/` and `frontend/` are implemented on `main`, and the integrated-history section below records completed stages through Stage 8.

- Observation: The backlog is detailed at the task level, but it is not yet grouped into implementation-sized increments; a direct "MVP all at once" reading would create stages that touch too many layers at once.
  Evidence: `docs/planning/backlog.md` lists twelve MVP task groups and three later priority groups, but its built-in MVP summary still groups the work into one broad tranche rather than reviewable delivery stages.

- Observation: The repository has uncommitted local edits in `AGENTS.md` that are not part of backlog implementation and must not be mixed into feature work.
  Evidence: `git status --short` shows `M AGENTS.md`, and `git diff -- AGENTS.md` contains planning-policy additions only.

- Observation: The backlog defines Python backend technology in enough detail to plan a concrete backend layout, but it does not define a frontend framework.
  Evidence: The backlog introduction explicitly mentions Python, FastAPI, Pydantic, pytest, and logging, while the UI section defines screens and behaviors but never names React, Vue, or any other framework.

- Observation: Stage 1 did not need any new production dependencies.
  Evidence: Backend bootstrap, config loading, domain modeling, validation, generation mode registration, and filesystem repositories were all implemented with the Python standard library, while pytest remained sufficient for test coverage.

- Observation: Stage 9 Batch 2 was integrated as part of a broader 2026 UI redesign PR rather than a narrowly scoped `UI-005`-only integration commit.
  Evidence: `git show bc93358` bundles the JSON export action with an unrelated visual refresh (`2ae37f9 feat(frontend): redesign UI with 2026 trends, stepper, dark mode, JSON export`) and two follow-up fixes (`bbe3fd8`, `9c66adb`). This diverges from the "keep integration separate from implementation" batch policy, but the result is already on `main` and the working tree is clean.

- Observation: Between Stage 9 Batch 1 and Stage 9 Batch 2 an unplanned API quality hardening batch was integrated on `main`.
  Evidence: `git log` shows `11bf5eb merge(api): integrate api quality branch` landing after `9c4330a` and before `bc93358`, bundling `b64956a` (enum whitelists), `63b5486` (Pydantic migration for generate/quiz-update bodies), `33d96aa` (enforced max document size with controlled `413`), `c43322c` (`pyproject.toml`, Ruff, GitHub Actions CI), and `d7a4ecb` (rejection of coerced numeric request fields). The plan did not anticipate this batch, but it hardens the API surface the remaining stages will rely on.

- Observation: The frontend generation call was capped at the generic `requestTimeoutMs` of 8000 ms, which is well below realistic LM Studio latency and would abort successful generations while the backend kept running.
  Evidence: `frontend/config.js` used a single timeout value and `QuizCraftApiClient._request` applied it uniformly; a 30–120 s generation would be aborted by `AbortController` long before LM Studio responded. Fixed on `main` via PR #3 (merge `d964ad1`, feature commit `2f24024`) with role-based timeouts (`health` 5 s, `upload` 30 s, `generate` 120 s, `quizEditor` 15 s), export-`fetch` `AbortController` coverage, and a Russian-language timeout error string.

- Observation: Codex began an independent fix for the same generation-timeout defect while PR #3 was open on the remote; the two branches implemented equivalent-in-intent but different-in-shape solutions.
  Evidence: Codex committed `4bd32d8 fix(frontend): allow per-endpoint timeouts and lift generation timeout to 180s` and `087984e docs(execplan): sync stage 9 integration, artifacts, and next stage pointer` locally. A `git push` was rejected because `origin/main` had already advanced through PR #3. Codex reset local `main` to `origin/main` to drop both commits because the Devin-authored role-based timeout fix is strictly broader (covers all four endpoint roles plus the JSON export `fetch`, returns a Russian error message). Only the docs sync was redone and committed on top of `origin/main`.

- Observation: Stage 14 closes the RAG primitives plus the RAG orchestrator and selector, but the runtime generation API endpoint is still hard-wired to `DirectGenerationOrchestrator` and never invokes `RagGenerationOrchestrator` or `select_generation_mode`.
  Evidence: `backend/app/api/runtime.py` and `backend/app/api/generation.py` construct only the direct orchestrator on `app.state`; `backend/app/generation/__init__.py` already exports both orchestrators and the mode selector, and the smoke and unit tests cover the RAG pipeline in isolation through stubs. The mismatch is intentional for this batch to keep the integration risk contained: the new RAG path is fully unit-tested but is reachable only through Python imports, not through the public HTTP `POST /generate` surface. Wiring is reserved for an explicit Stage 14 Batch 4 commit so that the API behavior change is reviewed separately from the new code.
  Resolution: Resolved by Stage 14 Batch 4 (merge `19300f1`, feature commits `9688edb` and `8c2b0fb`). `backend/app/generation/dispatcher.py` introduces `GenerationOrchestratorDispatcher`, `backend/app/api/runtime.py` exposes `get_rag_generation_orchestrator` and `get_generation_dispatcher` lazy builders sharing the existing filesystem repositories, and `backend/app/api/generation.py` routes `POST /documents/{document_id}/generate` through the dispatcher. Explicit `generation_mode=rag` and `direct → rag` promotion above the 6000-character threshold are covered by 8 integration tests in `backend/tests/test_api_generation_rag.py` plus 13 dispatcher unit tests in `backend/tests/test_orchestrator_dispatcher.py`.

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

- Decision: Keep Stage 15 Batch 1 as provider registry enforcement only, without adding new concrete provider adapters.
  Rationale: `CF-004` can be verified independently by wrapping the existing LM Studio provider with typed enablement checks for health, structured generation, and embeddings. Ollama and external API adapters widen the integration surface and remain separate Stage 15 batches.
  Date/Author: 2026-04-26 / Cascade

## Outcomes & Retrospective

At this stopping point, the early MVP is complete on `main`, Stage 14 (RAG generation) is fully integrated end-to-end including the runtime API wiring, and only the Future-tier provider expansion and RAG caching backlog remain. The integrated surface includes Stages 1 through 9 (foundation, ingestion, LM Studio integration, direct generation pipeline, HTTP API, quiz read/update, Cyrillic fixes, frontend upload-to-result, frontend editing, and JSON export), the unplanned API quality hardening batch, the role-based frontend timeout fix, Stage 10 (backend generation status with pipeline step logging and a Russian/Cyrillic-safe progress UI), Stage 11 (model whitelist, named generation profiles, and persisted generation settings reused as defaults), Stage 12 (single-question regeneration: backend endpoint, `single_question_regen` prompt and pipeline, and frontend UI wiring), Stage 13 (advanced export formats: registry-backed exporter contract, DOCX and PPTX exporters, advanced quiz export endpoints with capability reporting, and capability-driven frontend export controls preserving the existing JSON action), and Stage 14 (RAG generation primitives plus runtime API wiring: chunker, LM Studio embeddings client, in-memory vector index, top-`k` retriever, bounded context assembler, RAG master prompt, `RagGenerationOrchestrator`, rule-based direct/RAG mode selector, and the `GenerationOrchestratorDispatcher` that routes `POST /documents/{document_id}/generate` between the direct and RAG paths). On top of those feature stages, `main` also carries the post-MVP frontend UX polish batches, the additional UX cleanup batch that simplified the primary generation flow, a dev-experience batch with a dotenv loader, PowerShell run scripts, and the committed `.env.example`, a config hotfix that raises the default `REQUEST_TIMEOUT` from 30 to 300 seconds, and a generation cleanup that removed an unused structured response import.

The key outcome is that the Validation and Acceptance criteria for the early MVP still hold end-to-end and are now complemented by a more approachable UX surface, a richer export surface, and a real RAG generation path reachable through the public HTTP API: a user can upload a document, choose generation parameters (with model and profile selectors driven by `/generation/settings`), trigger quiz generation through LM Studio (direct for short documents, RAG for documents above 6000 characters or whenever `generation_mode=rag` is set explicitly) with a cancel button and live timer, review the generated quiz, regenerate individual questions after an explicit confirmation, edit the quiz, and export the final quiz as JSON, DOCX, or PPTX through capability-driven controls. Keyboard shortcuts, copy buttons, a compact hero, a per-theme toggle icon, screen-reader hints for disabled actions, and the simplified primary generation flow round out the polish. The next contributor should start from Stage 15 (Additional Providers and Feature Flags) rather than revisiting any Stage 1–14 surface, the dev-experience batch, the post-MVP UX/UX-cleanup batches, or the REQUEST_TIMEOUT hotfix. Known Stage 14 follow-ups that are explicitly not blockers: exposing `rag_threshold_chars` through `AppConfig` (env `RAG_PROMOTION_THRESHOLD_CHARS`), avoiding the dispatcher's double document load on the RAG path, surfacing the resolved generation mode in the API response, and adding a frontend mode toggle for `direct`/`rag`.

Stage 15 Batch 1 is now integrated on `main` as the provider-registry foundation slice. Provider expansion remains intentionally incremental: Batch 2 should add the Ollama adapter on the established registry contract, Batch 3 should add the external API adapter, and both should reuse the existing `PROVIDERS_ENABLED` enforcement path.

## Context and Orientation

The current repository has both planning artifacts and implemented product slices. `AGENTS.md` and `.agent/PLANS.md` contain repository and planning rules. `docs/planning/backlog.md` remains the source-of-truth feature inventory. `docs/design/concepts/v2/` still contains static mockups for the intended product screens. `backend/` now contains the implemented foundation, storage, parsing, LM Studio integration, direct generation pipeline, HTTP API, status, settings, editing, single-question regeneration, JSON/DOCX/PPTX export layers, and the full Stage 14 RAG generation stack (chunker, embeddings client, in-memory vector index, top-`k` retriever, bounded context assembler, RAG master prompt, `RagGenerationOrchestrator`, rule-based direct/RAG mode selector, and the `GenerationOrchestratorDispatcher` wired into `POST /documents/{document_id}/generate`). `frontend/` now contains the plain JavaScript shell, upload/generation flow, result view, editing UI, single-question regeneration controls, capability-driven JSON/DOCX/PPTX download actions, and post-MVP UX polish. `tests/test_repository_layout.py` still checks repository structure, while `backend/tests/` and the frontend smoke coverage now cover the implemented behavior including dispatcher routing and RAG-path API integration. Additional providers and RAG caching remain pending.

The backlog assumes a Python backend with typed contracts, FastAPI/Pydantic-style API models, pytest tests, standard-library logging, and LM Studio as the only model provider for the MVP. The backlog does not pick a frontend framework. The implemented frontend currently stays on plain HTML, CSS, and JavaScript in `frontend/`, and later stages should preserve that minimal stack unless a separate framework decision is explicitly made and recorded.

The implemented runtime layout for the current codebase is:

    backend/
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
      assets/

This layout is now implemented with the project-level `pyproject.toml`, backend packages for `api`, `core`, `domain`, `parsing`, `storage`, `llm`, `generation`, `prompts`, and `export`, plus a plain JavaScript frontend under `frontend/`. Later stages should extend those existing locations instead of introducing a new runtime layout.

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

Planned batch breakdown:
1. Batch 1: edit view and quiz loading
2. Batch 2: save flow and validation handling

Definition of done: The UI can open a generated quiz, edit question text, options, correct answers, and explanations, submit valid changes to the backend, and show validation errors when the edit payload is invalid.

Required tests/checks: Keep backend API tests green. Run a manual browser smoke test that edits a quiz, refreshes the page, and confirms the saved data persists.

Recommended commit breakdown:
1. `feat(ui): add quiz editing and save flow`
2. `test(ui): verify edit-save-refresh behavior`

## Stage 9: JSON Export and MVP Closeout

Task IDs: `EX-001`, `BE-010`, `UI-005`, `TS-007` (export slice).

Rationale for grouping: JSON export is the clean closeout for the early MVP. The exporter, endpoint, and UI button form one tight delivery unit and complete the user-visible promise defined in the backlog's MVP boundary.

Dependencies: Stages 6 through 8.

Current status on `main`: fully implemented and integrated. Batch 1 landed via merge commit `9c4330a` with feature commits `db8d303` (canonical JSON exporter), `3af8aa4` (download endpoint), and `50a9f60` (exporter and API test coverage). Batch 2 landed via merge commit `bc93358` (PR #2), which also bundled a broader 2026 UI redesign alongside `UI-005`. A follow-up role-based frontend timeout fix landed via merge commit `d964ad1` (PR #3, feature commit `2f24024`) so LM Studio generation is no longer aborted by the old 8 s request timeout.

Planned batch breakdown:
1. Batch 1: canonical JSON exporter and download endpoint
2. Batch 2: frontend JSON export action

### Batch 1: Canonical JSON exporter and download endpoint

Task IDs: `EX-001`, `BE-010`, `TS-007` export slice.

Definition of done: The backend can export a quiz from the canonical domain model into a deterministic JSON file, the API exposes `GET /quizzes/{quiz_id}/export/json` with a `content-disposition` download header, and pytest coverage exercises both the exporter and the download endpoint.

Required tests/checks: Run `python -m pytest backend/tests/test_json_exporter.py backend/tests/test_api_export_json.py -q` and expect all tests to pass. Keep `python -m pytest backend/tests -q`, `python -m pytest tests/test_repository_layout.py -q`, and `python -c "from backend.app.main import create_app"` green.

Recommended commit breakdown:
1. `feat(export): add canonical json exporter`
2. `feat(api): add json export download endpoint`
3. `test(export): cover exporter and json download behavior`

Current status on `main`: implemented and integrated via merge commit `9c4330a`.

### Batch 2: Frontend JSON export action

Task IDs: `UI-005`.

Definition of done: The UI offers an export action that downloads the canonical JSON for the currently loaded quiz after generation or editing, using the backend `GET /quizzes/{quiz_id}/export/json` endpoint.

Required tests/checks: Keep backend API tests green. Manually verify in the browser that the exported file downloads with the expected name and content after generating or editing a quiz.

Recommended commit breakdown:
1. `feat(ui): add json export action to the frontend`

Current status on `main`: implemented and integrated via merge commit `bc93358` (PR #2). The same merge also bundled an unplanned UI redesign (stepper, dark mode, visual refresh) and two follow-up fixes (`bbe3fd8`, `9c66adb`); see the Surprises & Discoveries note about this bundling. A subsequent PR #3 (merge `d964ad1`) further hardened the frontend timeout behavior for all endpoints, including the export `fetch`.

## Stage 10: Generation Status and User-Facing Operation States

Task IDs: `GN-006`, `UI-007`, `LG-005`.

Rationale for grouping: Once the MVP works, the next useful improvement is visibility. Pipeline step logging, backend status models, and UI status indicators all describe one concern: helping the user and the developer understand what the system is doing while generation runs.

Dependencies: Stages 4 through 9.

Current status on `main`: fully implemented and integrated. Batch 1 landed via merge commit `05ff078`, covering `GN-006` and `LG-005` with backend generation status transitions and structured pipeline step logging. Batch 2 landed via merge commit `3e816de`, covering the remaining `UI-007` behavior by keeping the existing Russian/Cyrillic-safe progress UI and aligning it with backend status evidence where available.

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

Recommended batch breakdown:
1. Batch 1: model whitelist and generation profile resolution.
2. Batch 2: settings persistence and reuse (`ST-003` and the remaining settings portion of `CF-003`).

Current status on `main`: fully implemented and integrated. Batch 1 landed via merge commit `e212758`, covering model whitelist configuration, request-time model validation and resolution, named profile resolution, invalid model/profile rejection, default profile behavior, and compatibility with the existing generation request shape. Batch 2 landed via merge commit `10c00e0`, covering local generation settings persistence, the minimal settings API surface, saved-settings reuse as generation defaults, invalid settings rejection, and compatibility with allowed model/profile resolution.

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

Recommended batch breakdown:
1. Batch 1: backend single-question regeneration endpoint and request model.
2. Batch 2: prompt template and generation-mode support for targeted regeneration, including the provider request builder/orchestration path and compatibility with profiles/settings.
3. Batch 3: focused tests and frontend UI wiring for isolated question replacement, including Russian/Cyrillic preservation in the UI and unchanged quiz structure outside the target question.

Current status on `main`: fully implemented and integrated. Batch 1 landed via merge commit `651daed` (API/request contract). Batch 2 landed via merge commit `98c5b48` (targeted-regeneration prompt template, `single_question_regen` generation-mode support, provider request builder/orchestration path, profile/settings compatibility, isolated target-question replacement, and persisted quiz updates). Batch 3 landed via merge commit `8accaec` (frontend UI wiring for isolated question replacement, Russian/Cyrillic UI preservation confirmed by shell tests, and unchanged quiz structure outside the target question). Stage 12 is complete.

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

Recommended batch and commit breakdown:
1. `refactor(export): add export registry` — introduce the export contract and registry, route the existing JSON exporter through it, and keep `/quizzes/{quiz_id}/export/json` backward compatible.
2. `feat(export): add docx quiz exporter` — add the DOCX exporter and focused exporter tests, including Russian/Cyrillic content checks.
3. `feat(export): add pptx quiz exporter` — add the PPTX exporter and focused exporter tests, including Russian/Cyrillic content checks.
4. `feat(api): add advanced quiz export endpoints` — expose DOCX/PPTX downloads through the registry and add backend support reporting for export formats.
5. `feat(frontend): add docx and pptx export actions` — add capability-driven frontend controls for DOCX/PPTX downloads without replacing the existing JSON action.

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

Work from the repository root, `D:\github\quizcraft`. Before each stage, create a dedicated branch or worktree so the stage stays isolated and reviewable. A typical sequence is:

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
    e29e229 merge(stage6): integrate quiz update batch 2
    dd0861f merge(i18n): integrate cyrillic compatibility audit
    3ebc9d1 merge(frontend): integrate stage 7 batch 1 shell
    b5f9cf7 feat(frontend): add upload surface
    79a9e51 feat(frontend): add generation parameter form and submit flow
    5762736 test(frontend): cover upload and parameter flow smoke paths
    a7f3cd3 merge(frontend): integrate stage 7 batch 3 result view
    16fc33b merge(frontend): integrate stage 8 batch 1 edit shell
    7082baf merge(frontend): integrate stage 8 batch 2 save flow
    9c4330a merge(export): integrate stage 9 batch 1 json export
    11bf5eb merge(api): integrate api quality branch
    bc93358 Merge pull request #2 from bk-ru/devin/1776933488-ui-redesign-2026
    d964ad1 Merge pull request #3 from bk-ru/devin/1776937949-frontend-timeouts
    eb1f79b feat(frontend): declutter happy path and escalate lm studio unavailable state
    99529e2 feat(frontend): surface operation feedback with 422 mapper and progress indicator
    8accaec merge(frontend): stage 12 batch 03 — full UX pass + dev experience
    bdfca15 merge(config): raise default REQUEST_TIMEOUT to 300s
    2254813 merge(docs): integrate stage 13 execplan sync
    9c1e7ef merge(export): integrate stage 13 batch 1 registry
    48fd6ae merge(export): integrate stage 13 batch 2 docx
    d4fe651 merge(export): integrate stage 13 batch 3 pptx
    95774a4 merge(api): integrate stage 13 batch 4 exports
    7acc1c7 merge(frontend): integrate stage 13 batch 5 exports
    4da1f50 merge(docs): integrate stage 13 completion sync
    a8b2ad9 merge(rag): integrate stage 14 batch 1 embeddings
    20fe09c merge(docs): integrate stage 14 batch 1 sync
    e8350c8 merge(rag): integrate stage 14 batch 2 retrieval
    5ce976d merge(docs): integrate stage 14 batch 2 sync
    63c890c merge(rag): integrate stage 14 batch 3 rag orchestrator
    22016fe merge(docs): integrate stage 14 batch 3 sync
    19300f1 merge(rag): integrate stage 14 batch 4 rag api wiring
    8bff790 merge(docs): integrate stage 14 batch 4 sync
    c3adbc0 merge(frontend): integrate ux quick wins batch a
    ad805ca merge(docs): integrate ux quick wins batch a sync
    942e9d7 merge(frontend): integrate rag mode ui batch b
    5c6ed85 merge(docs): integrate rag mode ui batch b sync
    2bf78ee merge(frontend): integrate confirm modal and regen cancel batch c

Current backlog completion status:

    Stage 1: integrated on main
    Stage 2: integrated on main
    Stage 3: integrated on main
    Stage 4: integrated on main
    Stage 5 Batch 1 (`BE-004`, `BE-005`, `LG-002`, `LG-004`, `TS-007` health slice): integrated on main
    Stage 5 Batch 2 (`BE-006`, `BE-007`, `TS-007` upload/generate slice): integrated on main
    Stage 5: fully integrated on main
    Stage 6 Batch 1 (`BE-008`, `TS-007` read slice): integrated on main
    Stage 6 Batch 2 (`BE-009`, `TS-007` update slice): integrated on main
    Stage 6: fully integrated on main
    Cyrillic compatibility audit/fix: integrated on main
    Stage 7 Batch 1 (`UI-001` shell slice): integrated on main
    Stage 7 Batch 2 (`UI-001` flow slice, `UI-002`): integrated on main
    Stage 7 Batch 3 (`UI-003`): integrated on main
    Stage 7: fully integrated on main
    Stage 8 Batch 1 (`UI-004` read/edit shell slice): integrated on main
    Stage 8 Batch 2 (`UI-004` save slice): integrated on main
    Stage 8: fully integrated on main
    Stage 9 Batch 1 (`EX-001`, `BE-010`, `TS-007` export slice): integrated on main
    Stage 9 Batch 2 (`UI-005`): integrated on main (bundled with the 2026 UI redesign in PR #2)
    Stage 9: fully integrated on main
    Early MVP: complete on main (Stages 1–9 integrated; Validation and Acceptance criteria satisfied)
    API quality hardening (unplanned post-Stage 9 Batch 1 audit): integrated on main
    Frontend role-based timeouts (PR #3): integrated on main
    Post-MVP UX polish Batch 1 (editor autoload, collapsed technical fields, critical LM Studio tone): integrated on main
    Post-MVP UX polish Batch 2 (Russian 422 mapper, `UI-007` pseudo-step progress panel): integrated on main
    Stage 10 Batch 1 (`GN-006`, `LG-005`): integrated on main
    Stage 10 Batch 2 (remaining `UI-007`): integrated on main
    Stage 10: fully integrated on main
    Stage 11 Batch 1 (`LM-006`, `CF-003` model/profile slice): integrated on main
    Stage 11 Batch 2 (`ST-003`, remaining settings portion of `CF-003`): integrated on main
    Stage 11: fully integrated on main
    Stage 12 Batch 1 (`BE-013` API/request-contract slice): integrated on main
    Stage 12 Batch 2 (`PM-005`, `CF-002` single-question regeneration mode slice): integrated on main
    Stage 12 Batch 3 (frontend UI wiring for isolated question replacement): integrated on main
    Stage 12: fully integrated on main
    Post-MVP UX polish Batch P1 (unified shell: stepper, dropzone preview, regenerate confirm, model/profile selectors, diagnostics panel removal): integrated on main
    Post-MVP UX polish Batch P2 (sharper feedback: failed step highlight, idle empty state, auto-persisted defaults hint, keyboard shortcuts, copy buttons, duplicate stepper badges removed): integrated on main
    Post-MVP UX polish Batch P3 (polish: compact hero, per-theme icon, a11y hints, alert-role toasts): integrated on main
    Dev-experience batch (dotenv loader, run scripts, README, .env.example, .gitignore): integrated on main
    Config hotfix (raise default `REQUEST_TIMEOUT` from 30 to 300 seconds): integrated on main
    UX cleanup Batch 1 (simplified primary generation flow and smoke coverage): integrated on main
    Generation cleanup (remove unused structured response import): integrated on main
    Stage 13 ExecPlan entry sync: integrated on main (merge `2254813`, feature `ee4bd7c`)
    Stage 13 Batch 1 (`EX-004`, `TS-009` registry slice): integrated on main
    Stage 13 Batch 2 (`EX-002`, `TS-009` DOCX slice): integrated on main
    Stage 13 Batch 3 (`EX-003`, `TS-009` PPTX slice): integrated on main
    Stage 13 Batch 4 (`BE-011`, `BE-012`, `TS-009` API slice): integrated on main
    Stage 13 Batch 5 (`UI-006` capability-driven frontend export controls): integrated on main
    Stage 13: fully integrated on main
    Stage 13 completion sync: integrated on main (merge `4da1f50`, feature `b88c6a3`)
    Stage 14 Batch 1 (`LM-005`, `PR-007`, `TS-008` embeddings/chunker slice): integrated on main
    Stage 14 Batch 1 sync: integrated on main (merge `20fe09c`, feature `6279dd6`)
    Stage 14 Batch 2 (`RAG-001` through `RAG-004`, `TS-008` retrieval/context slice): integrated on main
    Stage 14 Batch 2 sync: integrated on main (merge `5ce976d`, feature `ad27a98`)
    Stage 14 Batch 3 (`PM-004`, `RAG-005`, `GN-007`, `CF-002` RAG slice, `TS-008` orchestration slice): integrated on main
    Stage 14 primitives: fully integrated on main; runtime API wiring of `RagGenerationOrchestrator` and `select_generation_mode` deferred to Stage 14 Batch 4
    Stage 14 Batch 3 sync: integrated on main (merge `22016fe`, feature `418f653`)
    Stage 14 Batch 4 (`TS-008` dispatcher slice, runtime API wiring of `CF-002`): integrated on main
    Stage 14: fully integrated on main (including runtime API wiring through `GenerationOrchestratorDispatcher`)
    Stage 14 Batch 4 sync: integrated on main (merge `8bff790`, feature `5d766a9`)
    UX quick wins Batch A (post-Stage 14 UX hardening: language preservation in question regeneration, `aria-current="step"` on the active stepper item, `beforeunload` guard for unsaved editor edits): integrated on main (merge `c3adbc0`, feature `788b726`)
    UX quick wins Batch A sync: integrated on main (merge `ad805ca`, feature `ce39086`)
    UX RAG mode UI Batch B (post-Stage 14 UX hardening: explicit `generation_mode` selector in the parameters panel and resolved-mode badge in the result overview, closing the Stage 14 frontend follow-up): integrated on main (merge `942e9d7`, feature `935eaa3`)
    UX RAG mode UI Batch B sync: integrated on main (merge `5c6ed85`, feature `3c9c8b4`)
    UX confirm modal and regen cancel Batch C (post-Stage 14 UX hardening: native `<dialog>`-backed confirm modal replacing `globalThis.confirm`, AbortController-driven cancel for in-flight question regeneration with a visible per-card cancel button and an Esc shortcut, signal-forwarding API client, closing audit issues 2.3 and 2.4): integrated on main (merge `2bf78ee`, feature `652a501`)
    Stage 15 Batch 1 (`CF-004` provider registry and feature flags foundation): integrated on main (merge `41e829c`, feature `44f36f7`)

Next recommended stage:

    Stage 15: Additional Providers and Feature Flags

Next recommended batch:

    Stage 15 Batch 3: add an external-API provider adapter (`LM-008`) on the same typed provider registry and `PROVIDERS_ENABLED` enforcement contract. Keep frontend provider selection and broad generation request contract changes deferred unless explicitly promoted into scope. After Stage 15 the only remaining backlog tier is Stage 16 (`RAG-006` retrieval cache) and any cross-cutting Future-tier hardening that has not yet been promoted into a stage.

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
