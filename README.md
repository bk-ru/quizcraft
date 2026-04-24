# QuizCraft

QuizCraft is a local single-user quiz generation service backed by LM Studio. The current MVP can ingest a TXT, DOCX, or PDF document, extract text, generate a Russian-friendly quiz through the backend, let the user review and edit the result, and export the final quiz as JSON.

## Repository Layout

- `backend/` contains the FastAPI service, domain models, parsers, generation orchestration, LM Studio client, filesystem storage, and JSON export code.
- `frontend/` contains the static Russian-language browser UI implemented with plain HTML, CSS, and JavaScript modules.
- `frontend/api/client.js` contains the browser API client.
- `frontend/app.js` is the frontend composition entry point. Focused modules such as `generation-flow.js`, `quiz-editor.js`, `quiz-renderer.js`, `validation-errors.js`, `progress.js`, `theme.js`, `toast.js`, and `download.js` hold feature-specific behavior.
- `frontend/tokens.css`, `base.css`, `layout.css`, `forms.css`, `quiz.css`, `feedback.css`, and `responsive.css` split the UI styling by responsibility.
- `backend/tests/` and `tests/` contain pytest coverage for backend behavior, frontend shell structure, and Russian/Cyrillic text preservation.
- `docs/execplans/` stores task-specific execution plans.
- `docs/planning/backlog.md` stores the product backlog and MVP decomposition.
- `docs/design/concepts/v2/` stores earlier static UI concepts kept as design references.
- `.agent/PLANS.md` defines the ExecPlan format used for complex work.
- `AGENTS.md` contains repository-specific instructions for coding agents.

## Running Checks

From the repository root:

```powershell
python -m pytest -q
python -m ruff check .
```

The pytest suite covers the backend and static frontend shell. Ruff currently checks the Python codebase.

## Running Locally

Configure the environment once by copying the template and editing values:

```powershell
Copy-Item .env.example .env
```

Then start both services (each in its own PowerShell window):

```powershell
.\run-backend.ps1
.\run-frontend.ps1
```

Open the frontend at http://127.0.0.1:5500. It talks to the backend at http://127.0.0.1:8000 and expects LM Studio to be running on http://127.0.0.1:1234 with the model named in `LM_STUDIO_MODEL` loaded.

### Manual start

If you prefer running the services directly:

```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
python -m http.server 5500 --directory frontend
```

Environment variables from `.env` are loaded automatically by `AppConfig.from_env`. Real shell variables always take precedence. Point `QUIZCRAFT_ENV_FILE` at an alternative path to override the default discovery.

## Russian/Cyrillic Support

User-facing document processing must preserve Russian and Cyrillic text across parsing, storage, generation, API responses, UI rendering, editing, and JSON export. New text-processing, API, storage, generation, export, and UI changes should include at least one Russian/Cyrillic pytest example.
