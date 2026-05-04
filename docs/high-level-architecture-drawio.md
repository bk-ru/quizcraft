# QuizCraft High-Level Architecture Diagram for draw.io

This diagram is written in Mermaid format for diagrams.net / draw.io.

Import path in draw.io:

1. Open diagrams.net / draw.io.
2. Select `Insert -> Advanced -> Mermaid`.
3. Paste the Mermaid code below.

```mermaid
flowchart TB
  Browser["Browser<br/>single local user"]

  subgraph Frontend["Static frontend<br/>frontend/"]
    HTML["index.html<br/>application shell"]
    CSS["CSS modules<br/>tokens, layout, forms, quiz, feedback, responsive"]
    AppJS["app.js<br/>composition root"]
    UIControllers["UI controllers<br/>generation flow, editor, renderer,<br/>progress, settings, history, modal, toast"]
    ApiClient["QuizCraftApiClient<br/>HTTP client and timeouts"]
    LocalStorage["Browser localStorage<br/>recent quiz history, UI preferences"]
  end

  subgraph Backend["FastAPI backend<br/>backend/app/"]
    Main["main.py<br/>app factory, CORS, logging, correlation ID"]
    Routes["API route modules<br/>health, documents, generation,<br/>settings, quizzes, exports"]
    Schemas["Pydantic API schemas<br/>request validation and DTO conversion"]
    Runtime["api/runtime.py<br/>lazy service wiring"]
  end

  subgraph Application["Application services"]
    Ingestion["Document ingestion<br/>validate, parse, normalize, persist"]
    Dispatcher["Generation dispatcher<br/>direct vs RAG mode selection"]
    Direct["Direct generation orchestrator"]
    Rag["RAG generation orchestrator<br/>chunk, embed, retrieve, assemble"]
    SingleQuestion["Single-question regeneration orchestrator"]
    ExportRegistry["Export registry<br/>JSON, DOCX, PPTX, Markdown, CSV"]
    SettingsService["Generation settings and profile resolution"]
  end

  subgraph Domain["Domain layer"]
    Models["Domain models<br/>DocumentRecord, Quiz, Question,<br/>GenerationRequest, GenerationResult"]
    Validation["Domain validation<br/>quiz shape, quality checks, errors"]
    Normalization["Normalization<br/>document text and LLM quiz output"]
    Prompts["Prompt registry<br/>direct, RAG, repair, question regeneration"]
    Modes["Generation modes and enums"]
  end

  subgraph Infrastructure["Infrastructure adapters"]
    StorageRepos["Filesystem repositories<br/>documents, quizzes, results,<br/>settings, RAG cache"]
    Parsers["Document parsers<br/>TXT, DOCX, PDF"]
    LLMRegistry["Provider registry<br/>enabled-provider enforcement"]
    LMStudio["LM Studio client<br/>OpenAI-compatible API"]
    Ollama["Ollama client<br/>native HTTP API"]
    ExternalAPI["External API client<br/>OpenAI-compatible API"]
  end

  subgraph LocalDisk["Local project data"]
    DotQuizcraft[".quizcraft/<br/>JSON artifacts and cache"]
    Env[".env / environment<br/>models, providers, limits, profiles"]
  end

  Browser --> HTML
  HTML --> CSS
  HTML --> AppJS
  AppJS --> UIControllers
  UIControllers --> ApiClient
  UIControllers --> LocalStorage

  ApiClient --> Main
  Main --> Routes
  Routes --> Schemas
  Routes --> Runtime

  Runtime --> Ingestion
  Runtime --> Dispatcher
  Runtime --> SingleQuestion
  Runtime --> SettingsService
  Routes --> ExportRegistry

  Ingestion --> Parsers
  Ingestion --> StorageRepos
  Dispatcher --> Direct
  Dispatcher --> Rag
  Direct --> Prompts
  Rag --> Prompts
  SingleQuestion --> Prompts
  Direct --> LLMRegistry
  Rag --> LLMRegistry
  SingleQuestion --> LLMRegistry
  ExportRegistry --> StorageRepos
  SettingsService --> StorageRepos

  Ingestion --> Models
  Direct --> Models
  Rag --> Models
  SingleQuestion --> Models
  ExportRegistry --> Models
  Models --> Validation
  Direct --> Normalization
  Rag --> Normalization
  SingleQuestion --> Normalization
  Dispatcher --> Modes

  StorageRepos --> DotQuizcraft
  Main --> Env
  Runtime --> Env

  LLMRegistry --> LMStudio
  LLMRegistry --> Ollama
  LLMRegistry --> ExternalAPI
```

## Source Check

The diagram was checked against these implementation points:

- `frontend/index.html` and `frontend/app.js`: static shell and frontend composition root.
- `frontend/api/client.js`: HTTP boundary from frontend to backend.
- `backend/app/main.py`: FastAPI app factory, CORS, logging, correlation middleware, route registration.
- `backend/app/api/*.py`: route layer and API schemas.
- `backend/app/api/runtime.py`: service graph construction.
- `backend/app/parsing/*.py`: validators and TXT/DOCX/PDF parsers.
- `backend/app/generation/*.py`: direct, RAG, dispatcher, retrieval, and question-regeneration flows.
- `backend/app/domain/*.py`: domain models, validation, normalization, enums, errors, schemas.
- `backend/app/export/*.py`: export registry and format adapters.
- `backend/app/llm/*.py`: provider abstraction, registry, LM Studio, Ollama, external API clients.
- `backend/app/storage/*.py`: filesystem-backed JSON repositories under `.quizcraft`.
