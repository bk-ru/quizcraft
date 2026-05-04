# QuizCraft - Диаграмма классов

## Обзор архитектуры классов

Диаграмма показывает основные классы и их взаимосвязи в проекте QuizCraft, включая доменные модели, провайдеров LLM, систему генерации и экспорта.

## Диаграмма классов

```mermaid
classDiagram
    direction LR
    
    %% Domain Models
    class Quiz {
        +quiz_id: str
        +document_id: str
        +title: str
        +version: int
        +last_edited_at: str
        +questions: tuple[Question, ...]
        +to_dict() dict
        +from_dict(payload: dict) Quiz
    }
    class Question {
        +question_id: str
        +prompt: str
        +options: tuple[Option, ...]
        +correct_option_index: int | None
        +explanation: Explanation | None
        +question_type: str
        +correct_answer: str | None
        +matching_pairs: tuple[MatchingPair, ...]
    }
    class Option {
        +option_id: str
        +text: str
    }
    class Explanation {
        +text: str
    }
    class MatchingPair {
        +left: str
        +right: str
    }
    class GenerationRequest {
        +question_count: int
        +language: str
        +difficulty: str
        +quiz_type: str
        +generation_mode: GenerationMode
        +model_name: str | None
        +profile_name: str | None
        +inference_parameters: dict
        +quiz_types: tuple[str, ...]
        +to_dict() dict
        +from_dict(payload: dict) GenerationRequest
    }
    class GenerationSettings {
        +question_count: int
        +language: str
        +difficulty: str
        +quiz_type: str
        +model_name: str | None
        +profile_name: str | None
        +to_generation_request() GenerationRequest
    }
    class GenerationResult {
        +quiz: Quiz
        +model_name: str
        +prompt_version: str
    }
    class DocumentRecord {
        +document_id: str
        +filename: str
        +media_type: str
        +file_size_bytes: int
        +metadata: dict
        +content: str
    }

    %% LLM Providers
    class LLMProvider {
        <<abstract>>
        +healthcheck() ProviderHealthStatus
        +generate_structured(request) StructuredGenerationResponse
        +embed(request) EmbeddingResponse
    }
    class LMStudioClient {
        -_base_url: str
        -_default_model: str
        -_timeout_seconds: int
        -_retrying_caller: RetryingCaller
        +healthcheck() ProviderHealthStatus
        +generate_structured(request) StructuredGenerationResponse
        +embed(request) EmbeddingResponse
    }
    class OllamaClient {
        -_base_url: str
        -_default_model: str
        -_default_embedding_model: str
        -_timeout_seconds: int
        -_retrying_caller: RetryingCaller
        +healthcheck() ProviderHealthStatus
        +generate_structured(request) StructuredGenerationResponse
        +embed(request) EmbeddingResponse
    }
    class ExternalApiClient {
        -_base_url: str
        -_api_key: str
        -_default_model: str
        -_timeout_seconds: int
        -_retrying_caller: RetryingCaller
        +healthcheck() ProviderHealthStatus
        +generate_structured(request) StructuredGenerationResponse
        +embed(request) EmbeddingResponse
    }

    %% Generation System
    class DirectGenerationOrchestrator {
        -_document_repository
        -_quiz_repository
        -_generation_result_repository
        -_request_builder: DirectGenerationRequestBuilder
        -_provider
        -_quality_checker: GenerationQualityChecker
        +generate(document_id: str, request) GenerationResult
    }
    class RAGOrchestrator {
        -_document_repository
        -_quiz_repository
        -_generation_result_repository
        -_request_builder
        -_provider
        -_retrieval
        -_rag_cache
        +generate(document_id: str, request) GenerationResult
    }
    class GenerationDispatcher {
        -_direct_orchestrator: DirectGenerationOrchestrator
        -_rag_orchestrator: RAGOrchestrator
        +dispatch(document_id: str, request) GenerationResult
    }
    class GenerationQualityChecker {
        +validate_quiz(quiz) bool
        +enrich_generation_error(error) str
    }

    %% Export System
    class QuizExporter {
        <<protocol>>
        +media_type: str
        +export(quiz) ExportedQuizFile
    }
    class QuizExportRegistry {
        -_exporters: dict[str, QuizExporter]
        +supported_formats() tuple[str, ...]
        +get(export_format: str) QuizExporter
        +export(quiz, export_format: str) ExportedQuizFile
    }
    class QuizJsonExporter {
        +media_type: str
        +export(quiz) ExportedQuizFile
    }
    class QuizDocxExporter {
        +media_type: str
        +export(quiz) ExportedQuizFile
    }
    class QuizPptxExporter {
        +media_type: str
        +export(quiz) ExportedQuizFile
    }
    class QuizMarkdownExporter {
        +media_type: str
        +export(quiz) ExportedQuizFile
    }
    class QuizCsvExporter {
        +media_type: str
        +export(quiz) ExportedQuizFile
    }
    class ExportedQuizFile {
        +filename: str
        +media_type: str
        +content_bytes: bytes
    }

    %% Storage Layer
    class FileSystemQuizRepository {
        -_storage_path: Path
        +save(quiz) Quiz
        +get(quiz_id: str) Quiz
        -_build_last_edited_at(existing_quiz) str
    }
    class FileSystemDocumentRepository {
        -_storage_path: Path
        +save(document) DocumentRecord
        +get(document_id: str) DocumentRecord
    }
    class FileSystemGenerationResultRepository {
        -_storage_path: Path
        +save(result) GenerationResult
        +get(result_id: str) GenerationResult
    }

    %% Relationships
    Quiz *-- "*" Question : contains
    Question *-- "*" Option : has
    Question *-- "0..1" Explanation : has
    Question *-- "*" MatchingPair : has

    GenerationRequest --> GenerationMode : uses
    GenerationResult --> Quiz : contains

    LLMProvider <|-- LMStudioClient : implements
    LLMProvider <|-- OllamaClient : implements
    LLMProvider <|-- ExternalApiClient : implements

    DirectGenerationOrchestrator --> LLMProvider : uses
    DirectGenerationOrchestrator --> GenerationQualityChecker : uses
    RAGOrchestrator --> LLMProvider : uses
    RAGOrchestrator --> FileSystemDocumentRepository : uses

    GenerationDispatcher --> DirectGenerationOrchestrator : uses
    GenerationDispatcher --> RAGOrchestrator : uses

    QuizExporter <|.. QuizJsonExporter : implements
    QuizExporter <|.. QuizDocxExporter : implements
    QuizExporter <|.. QuizPptxExporter : implements
    QuizExporter <|.. QuizMarkdownExporter : implements
    QuizExporter <|.. QuizCsvExporter : implements

    QuizExportRegistry --> QuizExporter : uses
    QuizExportRegistry --> ExportedQuizFile : creates

    FileSystemQuizRepository --> Quiz : stores
    FileSystemDocumentRepository --> DocumentRecord : stores
    FileSystemGenerationResultRepository --> GenerationResult : stores

    DirectGenerationOrchestrator --> FileSystemQuizRepository : uses
    DirectGenerationOrchestrator --> FileSystemDocumentRepository : uses
    DirectGenerationOrchestrator --> FileSystemGenerationResultRepository : uses
```

## Описание классов

### Доменные модели (Domain Models)
- **Quiz** - Основной агрегат квиза с вопросами и метаданными
- **Question** - Вопрос квиза с опциями и объяснениями
- **Option** - Вариант ответа для вопроса
- **Explanation** - Пояснение к вопросу
- **MatchingPair** - Пара для вопросов на соответствие
- **GenerationRequest** - Запрос на генерацию квиза
- **GenerationSettings** - Сохраненные настройки генерации
- **GenerationResult** - Результат генерации квиза
- **DocumentRecord** - Запись о загруженном документе

### LLM провайдеры
- **LLMProvider** - Абстрактный интерфейс провайдера
- **LMStudioClient** - Клиент для LM Studio
- **OllamaClient** - Клиент для Ollama
- **ExternalApiClient** - Клиент для внешних API

### Система генерации
- **DirectGenerationOrchestrator** - Прямая генерация квизов
- **RAGOrchestrator** - RAG генерация для длинных документов
- **GenerationDispatcher** - Диспетчер генерации
- **GenerationQualityChecker** - Проверка качества генерации

### Система экспорта
- **QuizExporter** - Протокол экспортера
- **QuizExportRegistry** - Реестр экспортеров
- **Конкретные экспортеры** - JSON, DOCX, PPTX, Markdown, CSV
- **ExportedQuizFile** - Результат экспорта

### Хранилище
- **FileSystemQuizRepository** - Файловое хранилище квизов
- **FileSystemDocumentRepository** - Файловое хранилище документов
- **FileSystemGenerationResultRepository** - Файловое хранилище результатов

## Взаимосвязи

1. **Агрегаты**: Quiz содержит вопросы, вопросы содержат опции
2. **Наследование**: LLM провайдеры реализуют общий интерфейс
3. **Композиция**: Экспортеры реализуют протокол QuizExporter
4. **Зависимости**: Оркестраторы используют репозитории и провайдеры
5. **Хранилище**: Репозитории сохраняют соответствующие модели
