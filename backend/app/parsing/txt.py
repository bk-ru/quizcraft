"""TXT parsing support for document ingestion."""

from __future__ import annotations

import logging

from backend.app.domain.errors import TextExtractionError
from backend.app.parsing.files import ValidatedFile

logger = logging.getLogger(__name__)


class TxtParser:
    """Extract text from validated TXT files."""

    def __init__(self, encodings: tuple[str, ...] = ("utf-8-sig", "utf-8", "cp1251", "koi8-r")) -> None:
        self._encodings = encodings

    def parse(self, validated_file: ValidatedFile) -> str:
        """Decode TXT bytes into raw text using controlled fallback encodings."""

        for encoding in self._encodings:
            try:
                decoded_text = validated_file.content.decode(encoding)
            except UnicodeDecodeError:
                continue
            if self._looks_corrupted(decoded_text):
                continue

            logger.debug("Decoded TXT file %s with %s", validated_file.filename, encoding)
            return decoded_text

        raise TextExtractionError(f"unable to decode text file: {validated_file.filename}")

    @staticmethod
    def _looks_corrupted(decoded_text: str) -> bool:
        """Detect obviously broken decoded content."""

        if "\x00" in decoded_text:
            return True

        control_character_count = sum(
            1 for character in decoded_text if ord(character) < 32 and character not in {"\n", "\r", "\t"}
        )
        return control_character_count > 0
