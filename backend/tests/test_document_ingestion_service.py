import pytest

from backend.app.domain.errors import FileValidationError
from backend.app.parsing.files import UploadedFileValidator
from backend.app.parsing.ingestion import DocumentIngestionService
from backend.app.parsing.txt import TxtParser
from backend.app.storage.documents import FileSystemDocumentRepository


def build_service(tmp_path, max_file_size_bytes: int = 1024) -> DocumentIngestionService:
    return DocumentIngestionService(
        repository=FileSystemDocumentRepository(tmp_path),
        validator=UploadedFileValidator(max_file_size_bytes=max_file_size_bytes),
        txt_parser=TxtParser(),
    )


def test_ingestion_service_persists_normalized_txt_document(tmp_path) -> None:
    service = build_service(tmp_path)

    document = service.ingest(
        filename="lecture.txt",
        media_type="text/plain",
        content="  First line\r\n\r\n\tSecond line  ".encode("utf-8"),
    )

    assert document.filename == "lecture.txt"
    assert document.media_type == "text/plain"
    assert document.file_size_bytes == len("  First line\r\n\r\n\tSecond line  ".encode("utf-8"))
    assert document.normalized_text == "First line\n\nSecond line"
    assert document.metadata == {"text_length": len("First line\n\nSecond line")}

    stored_document = FileSystemDocumentRepository(tmp_path).get(document.document_id)
    assert stored_document == document


def test_ingestion_service_surfaces_validation_errors(tmp_path) -> None:
    service = build_service(tmp_path, max_file_size_bytes=4)

    with pytest.raises(FileValidationError, match="size"):
        service.ingest(
            filename="lecture.txt",
            media_type="text/plain",
            content=b"12345",
        )
