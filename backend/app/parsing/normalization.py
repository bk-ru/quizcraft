"""Text normalization and metadata assembly for ingested documents."""

from __future__ import annotations

import re

from backend.app.parsing.files import ValidatedFile

_MULTISPACE_PATTERN = re.compile(r" {2,}")
_EXCESSIVE_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")


def normalize_text(raw_text: str) -> str:
    """Normalize extracted document content into a deterministic canonical form."""

    normalized_text = raw_text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "").replace("\t", " ")
    normalized_text = "".join(
        character
        for character in normalized_text
        if ord(character) >= 32 or character == "\n"
    )
    normalized_lines = [_MULTISPACE_PATTERN.sub(" ", line).strip() for line in normalized_text.split("\n")]
    normalized_text = "\n".join(normalized_lines)
    normalized_text = _EXCESSIVE_BLANK_LINES_PATTERN.sub("\n\n", normalized_text)
    return normalized_text.strip()


def build_document_metadata(
    validated_file: ValidatedFile,
    normalized_text: str,
    extra_metadata: dict[str, int] | None = None,
) -> dict[str, int]:
    """Build base document metadata for the ingestion flow."""

    metadata = {"text_length": len(normalized_text)}
    if extra_metadata:
        metadata.update(extra_metadata)
    return metadata
