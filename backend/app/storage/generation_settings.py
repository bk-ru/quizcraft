"""Filesystem-backed generation settings repository."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import GenerationSettings


class FileSystemGenerationSettingsRepository:
    """Store and load single-user generation settings from the local filesystem."""

    def __init__(self, root_path: Path) -> None:
        self._storage_path = Path(root_path) / "settings"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._target_path = self._storage_path / "generation.json"

    def save(self, settings: GenerationSettings) -> GenerationSettings:
        """Persist generation settings to disk."""

        self._target_path.write_text(
            json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return settings

    def get(self) -> GenerationSettings:
        """Load saved generation settings."""

        if not self._target_path.exists():
            raise RepositoryNotFoundError("generation_settings", "default")

        payload = json.loads(self._target_path.read_text(encoding="utf-8"))
        return GenerationSettings.from_dict(payload)
