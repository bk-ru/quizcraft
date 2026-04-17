"""Document ingestion service for supported local formats."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from backend.app.domain.errors import TextExtractionError
from backend.app.domain.models import DocumentRecord
from backend.app.parsing.docx import DocxParser
from backend.app.parsing.files import UploadedFileValidator
from backend.app.parsing.normalization import build_document_metadata, normalize_text
from backend.app.parsing.txt import TxtParser
from backend.app.storage.documents import FileSystemDocumentRepository

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """Validate, parse, normalize, and persist supported documents."""

    def __init__(
        self,
        repository: FileSystemDocumentRepository,
        validator: UploadedFileValidator,
        txt_parser: TxtParser,
        docx_parser: DocxParser,
    ) -> None:
        self._repository = repository
        self._validator = validator
        self._parsers_by_extension = {
            ".txt": txt_parser.parse,
            ".docx": docx_parser.parse,
        }

    def ingest(self, filename: str, media_type: str, content: bytes) -> DocumentRecord:
        """Ingest a supported document into the document repository."""

        validated_file = self._validator.validate(
            filename=filename,
            media_type=media_type,
            content=content,
        )
        extension = Path(validated_file.filename).suffix.lower()
        raw_text = self._get_parser(extension)(validated_file)
        normalized_text = normalize_text(raw_text)
        if not normalized_text:
            raise TextExtractionError(f"document does not contain extractable text: {validated_file.filename}")

        document = DocumentRecord(
            document_id=f"doc-{uuid4().hex}",
            filename=validated_file.filename,
            media_type=validated_file.media_type,
            file_size_bytes=validated_file.file_size_bytes,
            normalized_text=normalized_text,
            metadata=build_document_metadata(validated_file, normalized_text),
        )
        persisted_document = self._repository.save(document)
        logger.info("Persisted ingested document %s", persisted_document.document_id)
        return persisted_document

    def _get_parser(self, extension: str):
        """Resolve a parser for the validated file extension."""

        try:
            return self._parsers_by_extension[extension]
        except KeyError as error:
            raise TextExtractionError(f"no parser registered for file extension: {extension}") from error
