"""DOCX parsing support for document ingestion."""

from __future__ import annotations

import logging
from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from backend.app.domain.errors import TextExtractionError
from backend.app.parsing.files import ValidatedFile

logger = logging.getLogger(__name__)

_WORDPROCESSING_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


class DocxParser:
    """Extract text from validated DOCX files."""

    def parse(self, validated_file: ValidatedFile) -> str:
        """Read paragraph text from a DOCX archive."""

        try:
            with ZipFile(BytesIO(validated_file.content)) as archive:
                document_xml = archive.read("word/document.xml")
        except (BadZipFile, KeyError) as error:
            raise TextExtractionError(f"unable to extract docx text: {validated_file.filename}") from error

        try:
            root = ElementTree.fromstring(document_xml)
        except ElementTree.ParseError as error:
            raise TextExtractionError(f"unable to parse docx xml: {validated_file.filename}") from error

        paragraphs = []
        for paragraph in root.findall(".//w:p", _WORDPROCESSING_NAMESPACE):
            fragments = [
                node.text or ""
                for node in paragraph.findall(".//w:t", _WORDPROCESSING_NAMESPACE)
            ]
            paragraph_text = "".join(fragments)
            if paragraph_text:
                paragraphs.append(paragraph_text)

        extracted_text = "\n\n".join(paragraphs).strip()
        if not extracted_text:
            raise TextExtractionError(f"docx file does not contain extractable text: {validated_file.filename}")

        logger.debug("Extracted DOCX text from %s", validated_file.filename)
        return extracted_text
