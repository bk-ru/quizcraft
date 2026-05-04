# QuizCraft - Диаграмма компонентов проекта

## Обзор архитектуры

QuizCraft - это веб-приложение для генерации учебных квизов из документов с поддержкой русского языка. Архитектура разделена на frontend и backend компоненты с локальным хранением данных.

## Диаграмма компонентов

```mermaid
graph TB
    subgraph "External Systems"
        LM_STUDIO[LM Studio API<br/>http://localhost:1234/v1]
        OLLAMA[Ollama API<br/>http://localhost:11434]
        EXTERNAL_API[External API<br/>OpenAI-compatible]
    end

    subgraph "Frontend (Port 5500)"
        HTML[index.html]
        CSS[CSS Files<br/>base.css, layout.css<br/>forms.css, quiz.css]
        JS[JavaScript Modules]
        API_CLIENT[QuizCraftApiClient]
    end

    subgraph "Frontend Modules"
        GEN_FLOW[generation-flow.js]
        QUIZ_EDITOR[quiz-editor.js]
        DOWNLOAD[download.js]
        APP[app.js]
        THEME[theme.js]
        VALIDATION[validation-errors.js]
    end

    subgraph "Backend (Port 8000)"
        FASTAPI[FastAPI main.py]
        CORS[CORS Middleware]
        CORRELATION[Correlation ID]
    end

    subgraph "API Routes"
        HEALTH[health]
        DOCS[documents]
        GEN[generate]
        QUIZ[quizzes, export]
        SETTINGS[settings]
    end

    subgraph "Core Services"
        CONFIG[config.py]
        PROVIDER_REGISTRY[LLM Registry]
        STORAGE[.quizcraft/]
    end

    subgraph "Domain Layer"
        MODELS[models.py]
        VALIDATION[validation.py]
        ERRORS[errors.py]
        ENUMS[enums.py]
    end

    subgraph "Document Processing"
        PARSING[parsing/]
        CHUNKING[chunking.py]
        INGESTION[ingestion.py]
    end

    subgraph "Generation Engine"
        DISPATCHER[dispatcher.py]
        ORCHESTRATOR[orchestrator.py]
        RAG_ORCH[rag_orchestrator.py]
        PROFILES[profiles.py]
        PROMPTS[prompts/]
    end

    subgraph "LLM Providers"
        LM_STUDIO_PROV[lm_studio.py]
        OLLAMA_PROV[ollama.py]
        EXTERNAL_PROV[external_api.py]
        PROVIDER_FACTORY[factory.py]
    end

    subgraph "Export System"
        EXPORT_REGISTRY[registry.py]
        JSON_EXP[JSON]
        DOCX_EXP[DOCX]
        PPTX_EXP[PPTX]
        MD_EXP[Markdown]
        CSV_EXP[CSV]
    end

    subgraph "Storage Layer"
        DOC_STORAGE[documents.py]
        QUIZ_STORAGE[quizzes.py]
        GEN_STORAGE[generation_results.py]
        RAG_CACHE[rag_cache.py]
        SETTINGS_STORAGE[generation_settings.py]
    end

    %% Connections
    USER --> HTML
    HTML --> CSS
    HTML --> JS
    JS --> API_CLIENT
    API_CLIENT --> FASTAPI
    
    APP --> GEN_FLOW
    APP --> QUIZ_EDITOR
    APP --> EXPORT
    APP --> THEME
    APP --> VALIDATION
    
    FASTAPI --> CORS
    FASTAPI --> CORRELATION
    FASTAPI --> HEALTH
    FASTAPI --> DOCS
    FASTAPI --> GEN
    FASTAPI --> QUIZ
    FASTAPI --> SETTINGS
    
    HEALTH --> PROVIDER_REGISTRY
    DOCS --> INGESTION
    GEN --> DISPATCHER
    QUIZ --> EXPORT_REGISTRY
    SETTINGS --> STORAGE
    
    DISPATCHER --> ORCHESTRATOR
    ORCHESTRATOR --> RAG_ORCH
    ORCHESTRATOR --> PROMPTS
    ORCHESTRATOR --> PROFILES
    
    PROVIDER_REGISTRY --> LM_STUDIO_PROV
    PROVIDER_REGISTRY --> OLLAMA_PROV
    PROVIDER_REGISTRY --> EXTERNAL_PROV
    PROVIDER_REGISTRY --> PROVIDER_FACTORY
    
    LM_STUDIO_PROV --> LM_STUDIO
    OLLAMA_PROV --> OLLAMA
    EXTERNAL_PROV --> EXTERNAL_API
    
    INGESTION --> PARSING
    PARSING --> CHUNKING
    
    EXPORT_REGISTRY --> JSON_EXP
    EXPORT_REGISTRY --> DOCX_EXP
    EXPORT_REGISTRY --> PPTX_EXP
    EXPORT_REGISTRY --> MD_EXP
    EXPORT_REGISTRY --> CSV_EXP
    
    STORAGE --> DOC_STORAGE
    STORAGE --> QUIZ_STORAGE
    STORAGE --> GEN_STORAGE
    STORAGE --> RAG_CACHE
    STORAGE --> SETTINGS_STORAGE
    
    ORCHESTRATOR --> STORAGE
    RAG_ORCH --> RAG_CACHE
    
    %% Styling
    classDef frontend fill:#e1f5fe
    classDef backend fill:#f3e5f5
    classDef external fill:#fff3e0
    classDef storage fill:#e8f5e8
    classDef api fill:#fce4ec
    
    class HTML,CSS,JS,API_CLIENT,APP,GEN_FLOW,QUIZ_EDITOR,EXPORT,THEME,VALIDATION frontend
    class FASTAPI,CORS,CORRELATION,HEALTH,DOCS,GEN,QUIZ,SETTINGS backend
    class LM_STUDIO,OLLAMA,EXTERNAL_API external
    class STORAGE,DOC_STORAGE,QUIZ_STORAGE,GEN_STORAGE,RAG_CACHE,SETTINGS_STORAGE storage
    class CONFIG,PROVIDER_REGISTRY,MODELS,VALIDATION,ERRORS,ENUMS,PARSING,CHUNKING,INGESTION,DISPATCHER,ORCHESTRATOR,RAG_ORCH,PROFILES,PROMPTS,LM_STUDIO_PROV,OLLAMA_PROV,EXTERNAL_PROV,PROVIDER_FACTORY,EXPORT_REGISTRY,JSON_EXP,DOCX_EXP,PPTX_EXP,MD_EXP,CSV_EXP api
```

## Описание компонентов

### Frontend компоненты
- **index.html** - Основная HTML страница приложения
- **CSS модули** - Стили для различных компонентов интерфейса
- **JavaScript модули** - Модульная архитектура фронтенда
- **QuizCraftApiClient** - HTTP клиент для взаимодействия с backend API

### Backend компоненты
- **FastAPI Application** - Основное веб-приложение с middleware
- **API Routes** - Эндпоинты для различных операций
- **Core Services** - Конфигурация, регистрация провайдеров, хранилище
- **Domain Layer** - Модели данных, валидация, ошибки

### Обработка документов
- **Document Parsing** - Парсинг TXT, DOCX, PDF файлов
- **Text Chunking** - Разделение текста на части для обработки
- **Document Ingestion** - Загрузка и предварительная обработка

### Генерация квизов
- **Generation Dispatcher** - Диспетчер запросов генерации
- **Generation Orchestrator** - Оркестратор процесса генерации
- **RAG Orchestrator** - RAG (Retrieval-Augmented Generation) обработка
- **Prompt Registry** - Реестр промптов для LLM

### LLM провайдеры
- **LM Studio Provider** - Интеграция с LM Studio
- **Ollama Provider** - Интеграция с Ollama
- **External API Provider** - Интеграция с внешними API

### Экспорт
- **Export Registry** - Реестр экспортеров
- **Экспортеры** - JSON, DOCX, PPTX, Markdown, CSV

### Хранилище
- **Local Storage** - Локальное файловое хранилище в `.quizcraft/`
- **Различные хранилища** - Для документов, квизов, результатов, кеша

## Потоки данных

1. **Загрузка документа**: Frontend → API → Document Ingestion → Storage
2. **Генерация квиза**: Frontend → API → Generation Dispatcher → LLM Provider → Storage
3. **Редактирование**: Frontend → API → Quiz Storage
4. **Экспорт**: Frontend → API → Export Registry → Frontend

## Конфигурация
- **Environment variables** - Настройки через .env файл
- **Generation profiles** - Профили генерации с параметрами
- **Provider configuration** - Настройки LLM провайдеров
