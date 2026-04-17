import pytest

from backend.app.domain.errors import FileValidationError
from backend.app.domain.errors import TextExtractionError
from backend.app.parsing.files import UploadedFileValidator
from backend.app.parsing.ingestion import DocumentIngestionService
from backend.app.parsing.docx import DocxParser
from backend.app.parsing.pdf import PdfParser
from backend.app.parsing.txt import TxtParser
from backend.app.storage.documents import FileSystemDocumentRepository
from backend.tests.docx_samples import build_docx_bytes
from backend.tests.pdf_samples import build_pdf_bytes


def build_service(tmp_path, max_file_size_bytes: int = 1024) -> DocumentIngestionService:
    return DocumentIngestionService(
        repository=FileSystemDocumentRepository(tmp_path),
        validator=UploadedFileValidator(max_file_size_bytes=max_file_size_bytes),
        txt_parser=TxtParser(),
        docx_parser=DocxParser(),
        pdf_parser=PdfParser(),
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


def test_ingestion_service_persists_normalized_docx_document(tmp_path) -> None:
    service = build_service(tmp_path)
    content = build_docx_bytes(["  First line  ", "Second\tline"])

    document = service.ingest(
        filename="lecture.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=content,
    )

    assert document.filename == "lecture.docx"
    assert document.media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert document.file_size_bytes == len(content)
    assert document.normalized_text == "First line\n\nSecond line"
    assert document.metadata == {"text_length": len("First line\n\nSecond line")}

    stored_document = FileSystemDocumentRepository(tmp_path).get(document.document_id)
    assert stored_document == document


def test_ingestion_service_surfaces_corrupted_docx_errors(tmp_path) -> None:
    service = build_service(tmp_path)

    with pytest.raises(TextExtractionError, match="docx"):
        service.ingest(
            filename="lecture.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content=b"corrupted",
        )


def test_ingestion_service_persists_normalized_pdf_document(tmp_path) -> None:
    service = build_service(tmp_path)
    content = build_pdf_bytes(["  First page  ", "Second\tpage"])

    document = service.ingest(
        filename="lecture.pdf",
        media_type="application/pdf",
        content=content,
    )

    assert document.filename == "lecture.pdf"
    assert document.media_type == "application/pdf"
    assert document.file_size_bytes == len(content)
    assert document.normalized_text == "First page\n\nSecond page"
    assert document.metadata == {"text_length": len("First page\n\nSecond page"), "page_count": 2}

    stored_document = FileSystemDocumentRepository(tmp_path).get(document.document_id)
    assert stored_document == document


def test_ingestion_service_surfaces_invalid_pdf_errors(tmp_path) -> None:
    service = build_service(tmp_path)

    with pytest.raises(TextExtractionError, match="pdf"):
        service.ingest(
            filename="lecture.pdf",
            media_type="application/pdf",
            content=b"not a pdf",
        )


def test_ingestion_service_surfaces_pdf_without_extractable_text_errors(tmp_path) -> None:
    service = build_service(tmp_path)

    with pytest.raises(TextExtractionError, match="extractable text"):
        service.ingest(
            filename="lecture.pdf",
            media_type="application/pdf",
            content=build_pdf_bytes([None]),
        )


def test_ingestion_service_surfaces_unsupported_pdf_content_path(tmp_path) -> None:
    service = build_service(tmp_path)

    with pytest.raises(FileValidationError, match="MIME"):
        service.ingest(
            filename="lecture.pdf",
            media_type="application/octet-stream",
            content=build_pdf_bytes(["First page"]),
        )
