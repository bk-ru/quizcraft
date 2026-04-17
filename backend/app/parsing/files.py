"""Uploaded-file validation for document ingestion."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from backend.app.domain.errors import FileValidationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ValidatedFile:
    """Validated uploaded file accepted by the parsing layer."""

    filename: str
    media_type: str
    file_size_bytes: int
    content: bytes


class UploadedFileValidator:
    """Validate uploaded files before parser dispatch."""

    _supported_media_types = {
        ".txt": {"text/plain"},
        ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        ".pdf": {"application/pdf"},
    }

    def __init__(self, max_file_size_bytes: int) -> None:
        self._max_file_size_bytes = max_file_size_bytes

    def validate(self, filename: str, media_type: str, content: bytes) -> ValidatedFile:
        """Validate filename, MIME type, size, and content presence."""

        extension = Path(filename).suffix.lower()
        normalized_media_type = media_type.split(";", maxsplit=1)[0].strip().lower()
        if extension not in self._supported_media_types:
            raise FileValidationError(f"unsupported file extension: {extension or '<missing>'}")
        if normalized_media_type not in self._supported_media_types[extension]:
            raise FileValidationError(f"unsupported MIME type: {normalized_media_type or '<missing>'}")
        if not content:
            raise FileValidationError("uploaded file is empty")

        file_size_bytes = len(content)
        if file_size_bytes > self._max_file_size_bytes:
            raise FileValidationError(
                f"uploaded file size exceeds limit: {file_size_bytes} bytes > {self._max_file_size_bytes} bytes"
            )

        logger.debug("Validated uploaded file %s (%s, %s bytes)", filename, normalized_media_type, file_size_bytes)
        return ValidatedFile(
            filename=filename,
            media_type=normalized_media_type,
            file_size_bytes=file_size_bytes,
            content=content,
        )
