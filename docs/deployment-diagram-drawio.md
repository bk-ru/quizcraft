# QuizCraft Deployment Diagram for draw.io

This diagram is written in Mermaid format for diagrams.net / draw.io.

Import path in draw.io:

1. Open diagrams.net / draw.io.
2. Select `Insert -> Advanced -> Mermaid`.
3. Paste the Mermaid code below.

```mermaid
flowchart TB
  User["Пользователь"]

  subgraph Workstation["Рабочая станция пользователя<br/>Windows / macOS / Linux"]
    Browser["Браузер<br/>открывает http://127.0.0.1:5500"]

    subgraph Repo["Локальная копия репозитория QuizCraft"]
      FrontendFiles["frontend/<br/>HTML, CSS, JavaScript-модули"]
      BackendCode["backend/app/<br/>пакет FastAPI-приложения"]
      Venv["Python-окружение<br/>.venv или системный Python<br/>FastAPI, Uvicorn, pypdf, python-docx, python-pptx"]
      EnvFile[".env<br/>URL провайдеров, имена моделей,<br/>таймауты, лимиты файлов и документов"]
      Storage[".quizcraft/<br/>documents, quizzes, generation_results,<br/>settings, rag_cache<br/>JSON-файлы"]
      Scripts["run-frontend.ps1<br/>run-backend.ps1"]
    end

    FrontendServer["Frontend-сервер<br/>python -m http.server 5500<br/>раздаёт frontend/"]
    BackendServer["Backend API<br/>uvicorn backend.app.main:app<br/>127.0.0.1:8000"]

    subgraph LocalProvider["Локальный LLM-провайдер"]
      LMStudio["LM Studio Local Server<br/>http://localhost:1234/v1"]
      Ollama["Ollama service<br/>http://localhost:11434"]
    end
  end

  subgraph RemoteProvider["Удалённый провайдер"]
    ExternalAPI["OpenAI-compatible API<br/>EXTERNAL_API_BASE_URL"]
  end

  BrowserStorage["Browser localStorage<br/>история последних квизов и настройки UI"]

  User --> Browser
  Scripts --> FrontendServer
  Scripts --> BackendServer

  FrontendServer --> FrontendFiles
  BackendServer --> BackendCode
  BackendServer --> Venv
  BackendServer --> EnvFile
  BackendServer --> Storage

  Browser -- "GET статических файлов<br/>http://127.0.0.1:5500" --> FrontendServer
  Browser -- "HTTP JSON/file API<br/>CORS: 127.0.0.1:5500, localhost:5500" --> BackendServer

  BackendServer -- "health, generation, embeddings<br/>PROVIDERS_ENABLED содержит lm_studio" --> LMStudio
  BackendServer -- "health, generation, embeddings<br/>PROVIDERS_ENABLED содержит ollama" --> Ollama
  BackendServer -- "health, generation, embeddings<br/>PROVIDERS_ENABLED содержит external_api" --> ExternalAPI

  BackendServer -- "чтение/запись UTF-8 JSON" --> Storage
  Browser -- "история последних квизов<br/>настройки UI" --> BrowserStorage
```

## Runtime Ports

- Frontend: `http://127.0.0.1:5500`, served from `frontend/` by `python -m http.server`.
- Backend: `http://127.0.0.1:8000`, served by Uvicorn from `backend.app.main:app`.
- LM Studio default: `http://localhost:1234/v1`.
- Ollama default: `http://localhost:11434`.
- External OpenAI-compatible API: configured by `EXTERNAL_API_BASE_URL`.

## Deployment Notes

- The application is designed as a local single-user deployment.
- The frontend and backend are separate local processes.
- Backend CORS explicitly allows `http://127.0.0.1:5500` and `http://localhost:5500`.
- Persistent application data is stored as UTF-8 JSON under `.quizcraft/`.
- `.env` controls active providers, default model, allowed models, generation profiles, timeouts, file size limits, and document length limits.
- Remote provider access is optional and only used when `external_api` is configured and enabled.

## Source Check

The diagram was checked against these implementation points:

- `run-frontend.ps1`: starts `python -m http.server` on port `5500` with `frontend/` as the document root.
- `run-backend.ps1`: starts `uvicorn backend.app.main:app` on port `8000`.
- `.env.example`: documents default LM Studio URL, request timeout, file size and document limits.
- `backend/app/main.py`: CORS origins, app state, provider runtime, storage root, route registration.
- `backend/app/api/runtime.py`: default `.quizcraft` storage root and filesystem-backed repositories.
- `backend/app/llm/factory.py`: LM Studio, Ollama, and external API provider runtime wiring.
