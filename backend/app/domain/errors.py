"""Иерархия ошибок доменного уровня."""

from __future__ import annotations

from typing import Any


class BackendError(Exception):
    """Базовый тип ошибки для backend-специфичных сбоев."""

    code = "backend_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(BackendError):
    """Вызывается, когда обязательная runtime-конфигурация отсутствует или некорректна."""

    code = "configuration_error"


class DomainValidationError(BackendError):
    """Вызывается, когда доменная сущность нарушает бизнес-правила."""

    code = "validation_error"


class GenerationQualityError(DomainValidationError):
    """Вызывается, когда нормализованный результат генерации структурно валиден, но непригоден."""

    code = "generation_quality_error"


class ModelSelectionError(DomainValidationError):
    """Вызывается, когда запрошенная модель не разрешена конфигурацией."""

    code = "model_selection_error"


class GenerationProfileError(DomainValidationError):
    """Вызывается, когда запрошенный профиль генерации неизвестен или некорректен."""

    code = "generation_profile_error"


class GenerationSettingsError(DomainValidationError):
    """Вызывается, когда сохраненные или request-time настройки генерации некорректны."""

    code = "generation_settings_error"


class DocumentTooLargeForGenerationError(DomainValidationError):
    """Вызывается, когда сохраненный документ превышает допустимый размер входа для генерации."""

    code = "document_too_large_for_generation"


class ParsingError(BackendError):
    """Вызывается при сбое валидации или парсинга документа."""

    code = "parsing_error"


class FileValidationError(ParsingError):
    """Вызывается, когда загруженный файл не проходит валидацию."""

    code = "file_validation_error"


class DocumentTooLargeError(ParsingError):
    """Raised when an uploaded document exceeds the configured request size limit."""

    code = "document_too_large"


class TextExtractionError(ParsingError):
    """Вызывается, когда из валидированного файла невозможно извлечь текст."""

    code = "text_extraction_error"


class UnsupportedGenerationModeError(BackendError):
    """Вызывается, когда запрошенный режим генерации не зарегистрирован."""

    code = "unsupported_generation_mode"


class UnsupportedExportFormatError(BackendError):
    """Вызывается, когда запрошенный формат экспорта квиза не зарегистрирован."""

    code = "unsupported_export_format"

    def __init__(self, export_format: str, supported_formats: tuple[str, ...]) -> None:
        self.export_format = export_format
        self.supported_formats = supported_formats
        supported_message = ", ".join(supported_formats) if supported_formats else "none"
        super().__init__(
            f"export format '{export_format}' is not supported; supported formats: {supported_message}"
        )


class RepositoryNotFoundError(BackendError):
    """Вызывается, когда repository не может загрузить запрошенную сущность."""

    code = "not_found"

    def __init__(self, entity_name: str, entity_id: str) -> None:
        super().__init__(f"{entity_name} '{entity_id}' was not found")
        self.entity_name = entity_name
        self.entity_id = entity_id


class StorageKeyError(BackendError):
    """Raised when a filesystem storage key is unsafe or malformed."""

    code = "invalid_storage_key"


class LLMProviderError(BackendError):
    """Базовый тип ошибки для сбоев, связанных с провайдерами."""

    code = "llm_provider_error"
    retryable = False

    def __init__(self, message: str, *, diagnostic: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.diagnostic = {} if diagnostic is None else dict(diagnostic)


class UnsupportedProviderError(LLMProviderError):
    """Вызывается, когда запрошенный провайдер не зарегистрирован."""

    code = "unsupported_provider"

    def __init__(self, provider_name: str, registered_provider_names: tuple[str, ...]) -> None:
        self.provider_name = provider_name
        self.registered_provider_names = registered_provider_names
        registered_message = ", ".join(registered_provider_names) if registered_provider_names else "none"
        super().__init__(
            f"provider '{provider_name}' is not registered; registered providers: {registered_message}"
        )


class ProviderDisabledError(LLMProviderError):
    """Вызывается, когда отключенный провайдер получает запрос генерации или embeddings."""

    code = "provider_disabled"

    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name
        super().__init__(f"provider '{provider_name}' is disabled by PROVIDERS_ENABLED")


class LLMConnectionError(LLMProviderError):
    """Вызывается, когда провайдер недоступен."""

    code = "llm_connection_error"
    retryable = True


class LLMTimeoutError(LLMProviderError):
    """Вызывается, когда провайдер не отвечает до timeout."""

    code = "llm_timeout_error"
    retryable = True


class LLMRequestError(LLMProviderError):
    """Вызывается, когда провайдер отклоняет запрос как некорректный."""

    code = "llm_request_error"

    def __init__(self, status_code: int, message: str, *, diagnostic: dict[str, Any] | None = None) -> None:
        super().__init__(message, diagnostic=diagnostic)
        self.status_code = status_code


class LLMServerError(LLMProviderError):
    """Вызывается, когда провайдер падает с повторяемой upstream-ошибкой."""

    code = "llm_server_error"
    retryable = True

    def __init__(self, status_code: int, message: str, *, diagnostic: dict[str, Any] | None = None) -> None:
        super().__init__(message, diagnostic=diagnostic)
        self.status_code = status_code


class LLMResponseFormatError(LLMProviderError):
    """Вызывается, когда провайдер возвращает некорректный или malformed payload."""

    code = "llm_response_format_error"


class UnsupportedProviderCapabilityError(LLMProviderError):
    """Вызывается, когда возможность провайдера объявлена, но еще не реализована."""

    code = "unsupported_provider_capability"


class PromptResolutionError(BackendError):
    """Вызывается, когда ключ prompt не удается разрешить через registry."""

    code = "prompt_resolution_error"
