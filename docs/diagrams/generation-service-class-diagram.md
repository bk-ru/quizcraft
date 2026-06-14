# Диаграмма классов Generation Service

Файл описывает элементы и связи диаграммы [class.drawio](../class.drawio). Диаграмма показывает классы сервиса генерации, связанные вспомогательные классы и внешние зависимости, которые используются этим сервисом.

## Обозначения связей

- Сплошная стрелка с открытым наконечником означает ассоциацию: класс хранит ссылку на другой класс в поле.
- Пунктирная стрелка `«use»` означает зависимость использования: класс вызывает методы другого элемента, но не обязательно владеет им.
- Пунктирная стрелка `«create»` означает зависимость создания: класс создаёт объект указанного типа.
- Сплошная линия с закрашенным ромбом означает композицию: владелец содержит один или несколько объектов другого класса.
- Пунктирная линия с полым треугольником означает реализацию интерфейса.
- `<<external>>` обозначает класс вне пакета `backend.app.generation`, но он показан, потому что сервис генерации напрямую с ним взаимодействует.

## Элементы

### GenerationOrchestratorDispatcher

Диспетчер выбора режима генерации. Он принимает запрос генерации, смотрит на размер документа и настройки режима, затем передаёт выполнение в direct- или RAG-оркестратор.

Связи:

- `GenerationOrchestratorDispatcher -> DirectGenerationOrchestrator`, ассоциация `_direct_orchestrator`: хранит ссылку на direct-оркестратор.
- `GenerationOrchestratorDispatcher -> RagGenerationOrchestrator`, ассоциация `_rag_orchestrator`: хранит ссылку на RAG-оркестратор.
- `GenerationOrchestratorDispatcher -> FileSystemDocumentRepository`, зависимость `«use»`: читает документ, чтобы принять решение о маршрутизации.

### DirectGenerationOrchestrator

Оркестратор прямой генерации. Загружает документ, строит prompt-запрос, вызывает LLM-провайдер, нормализует и проверяет результат, сохраняет квиз и результат генерации.

Связи:

- `DirectGenerationOrchestrator -> DirectGenerationRequestBuilder`, ассоциация `_request_builder`: использует builder для сборки `StructuredGenerationRequest`.
- `DirectGenerationOrchestrator -> GenerationQualityChecker`, ассоциация `_quality_checker`: проверяет качество и структуру сгенерированного квиза.
- `DirectGenerationOrchestrator -> FileSystemGenerationDiagnosticLogger`, ассоциация `_diagnostic_logger`: пишет диагностические артефакты успешной или ошибочной генерации.
- `DirectGenerationOrchestrator -> LLMProvider`, зависимость `«use»`: вызывает структурированную генерацию модели.
- `DirectGenerationOrchestrator -> FileSystemDocumentRepository`, зависимость `«use»`: загружает исходный документ.
- `DirectGenerationOrchestrator -> FileSystemQuizRepository`, зависимость `«use»`: сохраняет созданный квиз.
- `DirectGenerationOrchestrator -> FileSystemGenerationResultRepository`, зависимость `«use»`: сохраняет `GenerationResult`.
- `DirectGenerationOrchestrator -> GenerationCancellationControl`, зависимость `«use»`: проверяет отмену во время выполнения.

### RagGenerationOrchestrator

Оркестратор RAG-генерации. Делит документ на chunks, строит или загружает embedding-кэш, собирает релевантный контекст, вызывает LLM-провайдер и сохраняет результат генерации.

Связи:

- `RagGenerationOrchestrator -> GenerationQualityChecker`, ассоциация `_quality_checker`: проверяет итоговый квиз.
- `RagGenerationOrchestrator -> FileSystemGenerationDiagnosticLogger`, ассоциация `_diagnostic_logger`: пишет diagnostics для RAG pipeline.
- `RagGenerationOrchestrator -> InMemoryVectorIndex`, зависимость `«create»`: создаёт in-memory индекс для поиска релевантных chunks.
- `RagGenerationOrchestrator -> RagCacheEntry`, зависимость `«use»`: использует объект RAG-кэша для восстановления embeddings.
- `RagGenerationOrchestrator -> LLMProvider`, зависимость `«use»`: вызывает генерацию и embeddings.
- `RagGenerationOrchestrator -> FileSystemDocumentRepository`, зависимость `«use»`: загружает исходный документ.
- `RagGenerationOrchestrator -> FileSystemQuizRepository`, зависимость `«use»`: сохраняет созданный квиз.
- `RagGenerationOrchestrator -> FileSystemGenerationResultRepository`, зависимость `«use»`: сохраняет `GenerationResult`.
- `RagGenerationOrchestrator -> FileSystemRagCacheRepository`, ассоциация `_rag_cache_repository`: читает и сохраняет RAG cache.
- `RagGenerationOrchestrator -> GenerationCancellationControl`, зависимость `«use»`: проверяет отмену во время долгих операций.

### SingleQuestionRegenerationOrchestrator

Оркестратор точечной регенерации одного вопроса в уже существующем квизе. Загружает квиз и документ, формирует prompt для выбранного вопроса, вызывает LLM и заменяет только один вопрос.

Связи:

- `SingleQuestionRegenerationOrchestrator -> SingleQuestionRegenerationRequestBuilder`, ассоциация `_request_builder`: собирает request для регенерации одного вопроса.
- `SingleQuestionRegenerationOrchestrator -> SingleQuestionRegenerationResult`, зависимость `«create»`: создаёт результат регенерации.
- `SingleQuestionRegenerationOrchestrator -> LLMProvider`, зависимость `«use»`: вызывает структурированную генерацию.
- `SingleQuestionRegenerationOrchestrator -> FileSystemDocumentRepository`, зависимость `«use»`: загружает документ, связанный с квизом.
- `SingleQuestionRegenerationOrchestrator -> FileSystemQuizRepository`, зависимость `«use»`: загружает и сохраняет квиз.

### DirectGenerationRequestBuilder

Builder запроса для direct-генерации. Преобразует `DocumentRecord` и `GenerationRequest` в `StructuredGenerationRequest` для LLM-провайдера.

Связи:

- `DirectGenerationRequestBuilder -> PromptRegistry`, зависимость `«use»`: получает prompt по ключу режима генерации.
- `DirectGenerationOrchestrator -> DirectGenerationRequestBuilder`, входящая ассоциация `_request_builder`: direct-оркестратор делегирует ему сборку provider request.

### SingleQuestionRegenerationRequestBuilder

Builder запроса для регенерации одного вопроса. Формирует prompt с исходным документом, текущим квизом, целевым вопросом и пользовательскими инструкциями.

Связи:

- `SingleQuestionRegenerationRequestBuilder -> PromptRegistry`, зависимость `«use»`: получает prompt для single-question regeneration.
- `SingleQuestionRegenerationOrchestrator -> SingleQuestionRegenerationRequestBuilder`, входящая ассоциация `_request_builder`: оркестратор регенерации делегирует ему сборку request.

### GenerationQualityChecker

Сервис проверки качества результата генерации. Проверяет количество вопросов, допустимые типы вопросов и согласованность структуры квиза.

Связи:

- `DirectGenerationOrchestrator -> GenerationQualityChecker`, входящая ассоциация `_quality_checker`: используется в direct pipeline.
- `RagGenerationOrchestrator -> GenerationQualityChecker`, входящая ассоциация `_quality_checker`: используется в RAG pipeline.

### FileSystemGenerationDiagnosticLogger

Логгер диагностических артефактов генерации. Сохраняет компактные JSON-логи успехов, ошибок валидации и runtime-ошибок.

Связи:

- `DirectGenerationOrchestrator -> FileSystemGenerationDiagnosticLogger`, входящая ассоциация `_diagnostic_logger`: direct pipeline пишет диагностику.
- `RagGenerationOrchestrator -> FileSystemGenerationDiagnosticLogger`, входящая ассоциация `_diagnostic_logger`: RAG pipeline пишет диагностику.

### SingleQuestionRegenerationResult

DTO результата точечной регенерации. Содержит обновлённый квиз, заменённый вопрос, имя модели и версию prompt.

Связи:

- `SingleQuestionRegenerationOrchestrator -> SingleQuestionRegenerationResult`, входящая зависимость `«create»`: результат создаётся после успешной регенерации.

### InMemoryVectorIndex

In-memory индекс embeddings для RAG-поиска. Хранит embedded chunks и возвращает наиболее релевантные `ScoredChunk`.

Связи:

- `RagGenerationOrchestrator -> InMemoryVectorIndex`, входящая зависимость `«create»`: RAG-оркестратор создаёт индекс для поиска.
- `InMemoryVectorIndex -> EmbeddedChunk`, композиция `1..*`: индекс состоит из одного или нескольких embedded chunks.
- `InMemoryVectorIndex -> ScoredChunk`, зависимость `«create»`: метод поиска создаёт scored results.

### EmbeddedChunk

Value object одного текстового chunk вместе с embedding-вектором.

Связи:

- `InMemoryVectorIndex -> EmbeddedChunk`, входящая композиция `1..*`: индекс владеет набором embedded chunks.
- `RagCacheEntry -> EmbeddedChunk`, входящая композиция `1..*`: cache entry хранит embedded chunks для повторного использования.

### ScoredChunk

Value object результата поиска в vector index. Содержит найденный chunk и score релевантности.

Связи:

- `InMemoryVectorIndex -> ScoredChunk`, входящая зависимость `«create»`: создаётся при выполнении поиска.

### RagCacheEntry

Сериализуемая запись RAG cache. Хранит hash документа, параметры chunking, имя embedding-модели и embedded chunks.

Связи:

- `RagGenerationOrchestrator -> RagCacheEntry`, входящая зависимость `«use»`: RAG pipeline использует cache entry при восстановлении embeddings.
- `RagCacheEntry -> EmbeddedChunk`, композиция `1..*`: cache entry содержит embedded chunks.
- `FileSystemRagCacheRepository -> RagCacheEntry`, входящая зависимость через операции `save()` и `get()`: repository сохраняет и загружает cache entry.

### GenerationCancellationControl

Интерфейс cooperative cancellation для generation pipeline. Даёт оркестраторам общий контракт проверки отмены и безопасного commit.

Связи:

- `GenerationCancellationToken -> GenerationCancellationControl`, реализация интерфейса: token реализует все операции cancellation control.
- `DirectGenerationOrchestrator -> GenerationCancellationControl`, входящая зависимость `«use»`: direct pipeline проверяет отмену.
- `RagGenerationOrchestrator -> GenerationCancellationControl`, входящая зависимость `«use»`: RAG pipeline проверяет отмену.

### GenerationCancellationToken

Токен одного активного запуска генерации. Хранит request/document id, состояние отмены и callbacks.

Связи:

- `GenerationCancellationToken -> GenerationCancellationControl`, реализация: token является конкретной реализацией cancellation-контракта.
- `GenerationCancellationRegistry -> GenerationCancellationToken`, композиция `0..*`: registry владеет активными tokens.

### GenerationCancellationRegistry

Registry активных generation runs и terminal tombstones. Создаёт tokens, принимает отмену и фиксирует terminal outcome.

Связи:

- `GenerationCancellationRegistry -> GenerationCancellationToken`, композиция `0..*`: хранит активные tokens.
- `GenerationCancellationRegistry -> GenerationCancellationOutcome`, зависимость `«create»`: создаёт outcome для cancel/finish/get_outcome.

### GenerationCancellationOutcome

DTO результата lifecycle-операции отмены или завершения generation run.

Связи:

- `GenerationCancellationRegistry -> GenerationCancellationOutcome`, входящая зависимость `«create»`: создаётся registry при terminal state.

### GenerationEventStore

In-memory store пользовательских событий generation pipeline. Хранит bounded journal по run id.

Связи:

- `GenerationEventStore -> GenerationJournalEntry`, композиция `0..*`: store владеет списками journal entries для запусков генерации.

### GenerationJournalEntry

Пользовательская запись журнала генерации. Оборачивает `GenerationPipelineEvent` и добавляет event id, время создания, elapsed time и готовое сообщение.

Связи:

- `GenerationEventStore -> GenerationJournalEntry`, входящая композиция `0..*`: entries хранятся внутри event store.
- `GenerationJournalEntry -> GenerationPipelineEvent`, ассоциация `event`: entry содержит одно событие pipeline.

### GenerationPipelineEvent

Структурированное событие pipeline. Описывает статус, шаг, document id, optional quiz id, metadata и ошибку.

Связи:

- `GenerationJournalEntry -> GenerationPipelineEvent`, входящая ассоциация `event`: journal entry содержит событие pipeline.

### LLMProvider

Абстрактная граница LLM-провайдера. Определяет healthcheck, структурированную генерацию и embeddings.

Связи:

- `DirectGenerationOrchestrator -> LLMProvider`, входящая зависимость `«use»`: direct pipeline вызывает `generate_structured()`.
- `RagGenerationOrchestrator -> LLMProvider`, входящая зависимость `«use»`: RAG pipeline вызывает `generate_structured()` и `embed()`.
- `SingleQuestionRegenerationOrchestrator -> LLMProvider`, входящая зависимость `«use»`: single-question pipeline вызывает `generate_structured()`.

### PromptRegistry

Внешний registry prompt-шаблонов. Возвращает prompt по ключу.

Связи:

- `DirectGenerationRequestBuilder -> PromptRegistry`, входящая зависимость `«use»`: direct builder получает prompt для direct mode.
- `SingleQuestionRegenerationRequestBuilder -> PromptRegistry`, входящая зависимость `«use»`: single-question builder получает prompt для регенерации одного вопроса.

### FileSystemDocumentRepository

Внешний filesystem repository документов. Сохраняет и загружает `DocumentRecord`.

Связи:

- `GenerationOrchestratorDispatcher -> FileSystemDocumentRepository`, входящая зависимость `«use»`: dispatcher читает документ для выбора режима.
- `DirectGenerationOrchestrator -> FileSystemDocumentRepository`, входящая зависимость `«use»`: direct pipeline загружает документ.
- `RagGenerationOrchestrator -> FileSystemDocumentRepository`, входящая зависимость `«use»`: RAG pipeline загружает документ.
- `SingleQuestionRegenerationOrchestrator -> FileSystemDocumentRepository`, входящая зависимость `«use»`: single-question pipeline загружает документ квиза.

### FileSystemQuizRepository

Внешний filesystem repository квизов. Сохраняет и загружает `Quiz`.

Связи:

- `DirectGenerationOrchestrator -> FileSystemQuizRepository`, входящая зависимость `«use»`: сохраняет новый квиз.
- `RagGenerationOrchestrator -> FileSystemQuizRepository`, входящая зависимость `«use»`: сохраняет новый RAG-квиз.
- `SingleQuestionRegenerationOrchestrator -> FileSystemQuizRepository`, входящая зависимость `«use»`: загружает и сохраняет квиз при замене вопроса.

### FileSystemGenerationResultRepository

Внешний filesystem repository результатов генерации. Сохраняет и загружает `GenerationResult`.

Связи:

- `DirectGenerationOrchestrator -> FileSystemGenerationResultRepository`, входящая зависимость `«use»`: сохраняет результат direct generation.
- `RagGenerationOrchestrator -> FileSystemGenerationResultRepository`, входящая зависимость `«use»`: сохраняет результат RAG generation.

### FileSystemRagCacheRepository

Внешний filesystem repository RAG cache. Сохраняет, загружает, проверяет наличие и удаляет `RagCacheEntry`.

Связи:

- `RagGenerationOrchestrator -> FileSystemRagCacheRepository`, входящая ассоциация `_rag_cache_repository`: RAG pipeline использует repository для cache lifecycle.
- `FileSystemRagCacheRepository -> RagCacheEntry`, зависимость через операции `save(entry)` и `get(cache_key)`: repository работает с cache entry как сохраняемой моделью.

## Общая логика взаимодействия

1. `GenerationOrchestratorDispatcher` выбирает direct или RAG pipeline.
2. `DirectGenerationOrchestrator` использует `DirectGenerationRequestBuilder`, `LLMProvider`, `GenerationQualityChecker`, repositories и diagnostic logger.
3. `RagGenerationOrchestrator` дополнительно использует `InMemoryVectorIndex`, `RagCacheEntry` и `FileSystemRagCacheRepository`.
4. `SingleQuestionRegenerationOrchestrator` не проходит через dispatcher: это отдельный сценарий редактирования существующего квиза.
5. Cancellation и live journal вынесены отдельными группами классов, потому что обслуживают lifecycle генерации, но не являются генераторами вопросов.
