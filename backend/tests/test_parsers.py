import pytest

from backend.app.domain.errors import TextExtractionError
from backend.app.parsing.files import ValidatedFile
from backend.app.parsing.normalization import normalize_text
from backend.app.parsing.txt import TxtParser


def build_validated_file(content: bytes) -> ValidatedFile:
    return ValidatedFile(
        filename="lecture.txt",
        media_type="text/plain",
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


def test_normalize_text_canonicalizes_whitespace_and_control_characters() -> None:
    normalized_text = normalize_text("  First line\r\n\r\n\tSecond\x00   line \n\n\nThird line  ")

    assert normalized_text == "First line\n\nSecond line\n\nThird line"
