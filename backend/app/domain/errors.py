"""Domain-level error hierarchy."""

from __future__ import annotations


class BackendError(Exception):
    """Base error type for backend-specific failures."""

    code = "backend_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(BackendError):
    """Raised when required runtime configuration is missing or invalid."""

    code = "configuration_error"


class DomainValidationError(BackendError):
    """Raised when a domain entity violates business rules."""

    code = "validation_error"


class ParsingError(BackendError):
    """Raised when document validation or parsing fails."""

    code = "parsing_error"


class FileValidationError(ParsingError):
    """Raised when an uploaded file fails validation."""

    code = "file_validation_error"


class TextExtractionError(ParsingError):
    """Raised when text cannot be extracted from a validated file."""

    code = "text_extraction_error"


class UnsupportedGenerationModeError(BackendError):
    """Raised when a requested generation mode is not registered."""

    code = "unsupported_generation_mode"


class RepositoryNotFoundError(BackendError):
    """Raised when a repository cannot load a requested entity."""

    code = "not_found"

    def __init__(self, entity_name: str, entity_id: str) -> None:
        super().__init__(f"{entity_name} '{entity_id}' was not found")
        self.entity_name = entity_name
        self.entity_id = entity_id
