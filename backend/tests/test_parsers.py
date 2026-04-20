import pytest

from backend.app.domain.errors import TextExtractionError
from backend.app.parsing.files import ValidatedFile
from backend.app.parsing.normalization import normalize_text
from backend.app.parsing.docx import DocxParser
from backend.app.parsing.pdf import PdfParser
from backend.app.parsing.txt import TxtParser
from backend.tests.docx_samples import build_docx_bytes
from backend.tests.pdf_samples import build_pdf_bytes
from backend.tests.pdf_samples import build_russian_pdf_bytes


def build_validated_file(content: bytes) -> ValidatedFile:
    return ValidatedFile(
        filename="lecture.txt",
        media_type="text/plain",
        file_size_bytes=len(content),
        content=content,
    )


def build_docx_validated_file(content: bytes) -> ValidatedFile:
    return ValidatedFile(
        filename="lecture.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_size_bytes=len(content),
        content=content,
    )


def build_pdf_validated_file(content: bytes) -> ValidatedFile:
    return ValidatedFile(
        filename="lecture.pdf",
        media_type="application/pdf",
        file_size_bytes=len(content),
        content=content,
    )


def test_txt_parser_decodes_utf8_content() -> None:
    parser = TxtParser()

    text = parser.parse(build_validated_file("Привет, мир".encode("utf-8")))

    assert text == "Привет, мир"


def test_txt_parser_uses_fallback_encoding_for_cp1251_content() -> None:
    parser = TxtParser()

    text = parser.parse(build_validated_file("Привет, мир".encode("cp1251")))

    assert text == "Привет, мир"


def test_txt_parser_raises_controlled_error_for_broken_content() -> None:
    parser = TxtParser()

    with pytest.raises(TextExtractionError, match="decode"):
        parser.parse(build_validated_file(b"\x00\x00\x00\x00"))


def test_txt_parser_preserves_russian_text_for_cp1251_content() -> None:
    parser = TxtParser()

    text = parser.parse(build_validated_file("Привет, мир".encode("cp1251")))

    assert text == "Привет, мир"


def test_docx_parser_extracts_paragraph_text() -> None:
    parser = DocxParser()

    text = parser.parse(build_docx_validated_file(build_docx_bytes(["First line", "Second line"])))

    assert text == "First line\n\nSecond line"


def test_docx_parser_raises_controlled_error_for_corrupted_document() -> None:
    parser = DocxParser()

    with pytest.raises(TextExtractionError, match="docx"):
        parser.parse(build_docx_validated_file(b"not a zip archive"))


def test_docx_parser_extracts_russian_paragraph_text() -> None:
    parser = DocxParser()

    text = parser.parse(
        build_docx_validated_file(build_docx_bytes(["Первый абзац", "Второй абзац"]))
    )

    assert text == "Первый абзац\n\nВторой абзац"


def test_pdf_parser_extracts_text_page_by_page() -> None:
    parser = PdfParser()

    text = parser.parse(build_pdf_validated_file(build_pdf_bytes(["First page", "Second page"])))

    assert text == "First page\n\nSecond page"


def test_pdf_parser_raises_controlled_error_for_invalid_pdf() -> None:
    parser = PdfParser()

    with pytest.raises(TextExtractionError, match="pdf"):
        parser.parse(build_pdf_validated_file(b"not a pdf"))


def test_pdf_parser_raises_controlled_error_for_pdf_without_extractable_text() -> None:
    parser = PdfParser()

    with pytest.raises(TextExtractionError, match="extractable text"):
        parser.parse(build_pdf_validated_file(build_pdf_bytes([None])))


def test_pdf_parser_extracts_russian_text_from_fixture() -> None:
    parser = PdfParser()

    text = parser.parse(build_pdf_validated_file(build_russian_pdf_bytes()))

    assert "Привет, мир" in text
    assert "Это русский PDF для теста." in text


def test_normalize_text_canonicalizes_whitespace_and_control_characters() -> None:
    normalized_text = normalize_text("  First line\r\n\r\n\tSecond\x00   line \n\n\nThird line  ")

    assert normalized_text == "First line\n\nSecond line\n\nThird line"


def test_normalize_text_preserves_cyrillic_characters() -> None:
    normalized_text = normalize_text("  Первый\r\n\r\n\tвторой  \n\n\nТретий\x00 ")

    assert normalized_text == "Первый\n\nвторой\n\nТретий"
