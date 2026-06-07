"""Filesystem-backed repository настроек генерации."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import GenerationSettings

MODE_POLICY_VERSION = 2


class FileSystemGenerationSettingsRepository:
    """Сохранять и загружать single-user настройки генерации из локальной файловой системы."""

    def __init__(self, root_path: Path) -> None:
        self._storage_path = Path(root_path) / "settings"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._target_path = self._storage_path / "generation.json"

    def save(self, settings: GenerationSettings) -> GenerationSettings:
        """Сохранить настройки генерации на диск."""

        payload = settings.to_dict()
        payload["mode_policy_version"] = MODE_POLICY_VERSION
        self._target_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return settings

    def get(self) -> GenerationSettings:
        """Загрузить сохраненные настройки генерации."""

        if not self._target_path.exists():
            raise RepositoryNotFoundError("generation_settings", "default")

        payload = json.loads(self._target_path.read_text(encoding="utf-8"))
        if "mode_policy_version" not in payload and payload.get("generation_mode") == "direct":
            payload["generation_mode"] = "auto"
        return GenerationSettings.from_dict(payload)
