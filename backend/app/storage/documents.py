"""Filesystem-backed document repository."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import DocumentRecord


class FileSystemDocumentRepository:
    """Store and load document records from the local filesystem."""

    def __init__(self, root_path: Path) -> None:
        self._storage_path = Path(root_path) / "documents"
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def save(self, document: DocumentRecord) -> DocumentRecord:
        """Persist a document record to disk."""

        target_path = self._storage_path / f"{document.document_id}.json"
        target_path.write_text(json.dumps(document.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return document

    def get(self, document_id: str) -> DocumentRecord:
        """Load a document record by its identifier."""

        target_path = self._storage_path / f"{document_id}.json"
        if not target_path.exists():
            raise RepositoryNotFoundError("document", document_id)

        payload = json.loads(target_path.read_text(encoding="utf-8"))
        return DocumentRecord.from_dict(payload)
