"""Filesystem-backed repository документов."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.errors import StorageKeyError
from backend.app.domain.models import DocumentRecord
from backend.app.storage.keys import storage_json_path


class FileSystemDocumentRepository:
    """Сохранять и загружать записи документов из локальной файловой системы."""

    def __init__(self, root_path: Path) -> None:
        self._storage_path = Path(root_path) / "documents"
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def save(self, document: DocumentRecord) -> DocumentRecord:
        """Сохранить запись документа на диск."""

        target_path = storage_json_path(self._storage_path, document.document_id)
        target_path.write_text(json.dumps(document.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return document

    def get(self, document_id: str) -> DocumentRecord:
        """Загрузить запись документа по ее идентификатору."""

        try:
            target_path = storage_json_path(self._storage_path, document_id)
        except StorageKeyError as error:
            raise RepositoryNotFoundError("document", document_id) from error
        if not target_path.exists():
            raise RepositoryNotFoundError("document", document_id)

        payload = json.loads(target_path.read_text(encoding="utf-8"))
        return DocumentRecord.from_dict(payload)
