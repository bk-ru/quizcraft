# QuizCraft Use Case Diagram for draw.io

This diagram is written in Mermaid format for diagrams.net / draw.io.

Import path in draw.io:

1. Open diagrams.net / draw.io.
2. Select `Insert -> Advanced -> Mermaid`.
3. Paste the Mermaid code below.

```mermaid
flowchart LR
  User["User<br/>single local browser user"]
  Provider["LLM provider<br/>LM Studio / Ollama / external OpenAI-compatible API"]
  Storage["Local JSON storage<br/>.quizcraft"]

  subgraph Site["QuizCraft website"]
    UC_Check["Check service status<br/>backend and provider health"]
    UC_Settings["View or save generation defaults<br/>models, profiles, language, difficulty, mode"]
    UC_Input["Provide source document<br/>paste text or attach TXT/DOCX/PDF"]
    UC_Params["Choose quiz parameters<br/>question count, types, language, difficulty, mode"]
    UC_Generate["Generate quiz from document"]
    UC_Direct["Generate directly from normalized text"]
    UC_RAG["Generate with RAG<br/>chunk, embed, retrieve context"]
    UC_CancelGeneration["Cancel quiz generation"]
    UC_View["View generated quiz result"]
    UC_LoadQuiz["Load existing quiz by ID"]
    UC_Edit["Edit quiz title, questions, answers, pairs, explanations"]
    UC_SaveEdit["Save edited quiz"]
    UC_RegenerateQuestion["Regenerate one quiz question"]
    UC_CancelQuestionRegen["Cancel question regeneration"]
    UC_Export["Export quiz"]
    UC_ExportFormats["Download JSON, DOCX, PPTX, Markdown, or CSV"]
    UC_History["Use recent quiz history<br/>browser localStorage"]
    UC_Copy["Copy technical IDs<br/>quiz, document, request"]
    UC_Theme["Switch UI theme"]
  end

  subgraph Backend["Backend responsibilities"]
    UC_Parse["Validate, parse, and normalize source file"]
    UC_PersistDoc["Persist document record"]
    UC_Profile["Resolve model and generation profile"]
    UC_CallLLM["Call provider for structured JSON or embeddings"]
    UC_ValidateQuiz["Normalize, validate, and repair generated quiz"]
    UC_PersistQuiz["Persist quiz and generation metadata"]
    UC_UpdateQuiz["Validate and persist quiz updates"]
    UC_PersistSettings["Persist generation settings"]
    UC_RenderExport["Render export artifact"]
  end

  User --> UC_Check
  User --> UC_Settings
  User --> UC_Input
  User --> UC_Params
  User --> UC_Generate
  User --> UC_CancelGeneration
  User --> UC_View
  User --> UC_LoadQuiz
  User --> UC_Edit
  User --> UC_SaveEdit
  User --> UC_RegenerateQuestion
  User --> UC_CancelQuestionRegen
  User --> UC_Export
  User --> UC_History
  User --> UC_Copy
  User --> UC_Theme

  UC_Generate -. includes .-> UC_Input
  UC_Generate -. includes .-> UC_Params
  UC_Generate -. includes .-> UC_Parse
  UC_Generate -. includes .-> UC_PersistDoc
  UC_Generate -. includes .-> UC_Profile
  UC_Generate -. includes .-> UC_CallLLM
  UC_Generate -. includes .-> UC_ValidateQuiz
  UC_Generate -. includes .-> UC_PersistQuiz
  UC_Generate -. extends .-> UC_Direct
  UC_Generate -. extends .-> UC_RAG

  UC_RAG -. includes .-> UC_CallLLM
  UC_RAG -. includes .-> UC_ValidateQuiz

  UC_Settings -. includes .-> UC_Profile
  UC_Settings -. includes .-> UC_PersistSettings

  UC_LoadQuiz -. includes .-> UC_View
  UC_Edit -. includes .-> UC_LoadQuiz
  UC_SaveEdit -. includes .-> UC_UpdateQuiz
  UC_SaveEdit -. includes .-> UC_View

  UC_RegenerateQuestion -. includes .-> UC_LoadQuiz
  UC_RegenerateQuestion -. includes .-> UC_Profile
  UC_RegenerateQuestion -. includes .-> UC_CallLLM
  UC_RegenerateQuestion -. includes .-> UC_UpdateQuiz
  UC_RegenerateQuestion -. includes .-> UC_View

  UC_Export -. includes .-> UC_RenderExport
  UC_Export -. includes .-> UC_ExportFormats

  UC_Check --> Provider
  UC_CallLLM --> Provider

  UC_PersistDoc --> Storage
  UC_PersistQuiz --> Storage
  UC_UpdateQuiz --> Storage
  UC_PersistSettings --> Storage
  UC_RenderExport --> Storage
```

## Source Check

The diagram was checked against these implementation points:

- `frontend/api/client.js`: health, settings, upload, generation, quiz read/update, question regeneration.
- `backend/app/main.py`: FastAPI application setup and route registration.
- `backend/app/api/*.py`: actual HTTP routes.
- `backend/app/api/runtime.py`: backend service wiring.
- `backend/app/generation/*.py`: direct, RAG, and single-question generation flows.
- `backend/app/export/registry.py`: export formats.
- `backend/app/storage/*.py`: local JSON storage layout.
