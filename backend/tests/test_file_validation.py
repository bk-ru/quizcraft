import pytest

from backend.app.domain.errors import FileValidationError
from backend.app.parsing.files import UploadedFileValidator


def build_validator(max_file_size_bytes: int = 1024) -> UploadedFileValidator:
    return UploadedFileValidator(max_file_size_bytes=max_file_size_bytes)


def test_validator_accepts_supported_txt_file() -> None:
    validator = build_validator()

    validated_file = validator.validate(
        filename="lecture.txt",
        media_type="text/plain; charset=utf-8",
        content=b"hello world",
    )

    assert validated_file.filename == "lecture.txt"
    assert validated_file.media_type == "text/plain"
    assert validated_file.file_size_bytes == 11
    assert validated_file.content == b"hello world"


def test_validator_rejects_unsupported_extension() -> None:
    validator = build_validator()

    with pytest.raises(FileValidationError, match="extension"):
        validator.validate(
            filename="lecture.pdf",
            media_type="application/pdf",
            content=b"fake pdf",
        )


def test_validator_rejects_unsupported_media_type() -> None:
    validator = build_validator()

    with pytest.raises(FileValidationError, match="MIME"):
        validator.validate(
            filename="lecture.txt",
            media_type="application/octet-stream",
            content=b"hello world",
        )


def test_validator_rejects_empty_file() -> None:
    validator = build_validator()

    with pytest.raises(FileValidationError, match="empty"):
        validator.validate(
            filename="lecture.txt",
            media_type="text/plain",
            content=b"",
        )


def test_validator_rejects_file_larger_than_limit() -> None:
    validator = build_validator(max_file_size_bytes=4)

    with pytest.raises(FileValidationError, match="size"):
        validator.validate(
            filename="lecture.txt",
            media_type="text/plain",
            content=b"12345",
        )
