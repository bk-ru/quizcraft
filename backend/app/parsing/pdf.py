"""PDF parsing support for document ingestion."""

from __future__ import annotations

import logging
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from backend.app.domain.errors import TextExtractionError
from backend.app.parsing.files import ValidatedFile

logger = logging.getLogger(__name__)


class PdfParser:
    """Extract text and page metadata from validated PDF files."""

    def parse(self, validated_file: ValidatedFile) -> str:
        """Read page-by-page text from a PDF file."""

        reader = self._load_reader(validated_file)
        extracted_pages = []
        for page in reader.pages:
            page_text = (page.extract_text() or "").strip()
            if page_text:
                extracted_pages.append(page_text)

        if not extracted_pages:
            raise TextExtractionError(f"pdf file does not contain extractable text: {validated_file.filename}")

        extracted_text = "\n\n".join(extracted_pages)
        logger.debug("Extracted PDF text from %s across %s pages", validated_file.filename, len(reader.pages))
        return extracted_text

    def extract_page_count(self, validated_file: ValidatedFile) -> int:
        """Return the total page count for a validated PDF file."""

        reader = self._load_reader(validated_file)
        return len(reader.pages)

    @staticmethod
    def _load_reader(validated_file: ValidatedFile) -> PdfReader:
        """Create a PdfReader for the validated file or raise a controlled error."""

        try:
            return PdfReader(BytesIO(validated_file.content))
        except PdfReadError as error:
            raise TextExtractionError(f"unable to parse pdf file: {validated_file.filename}") from error
