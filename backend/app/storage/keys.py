"""Shared filesystem storage key validation."""

from __future__ import annotations

import re
from pathlib import Path
from pathlib import PureWindowsPath

from backend.app.domain.errors import StorageKeyError

STORAGE_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")


def validate_storage_key(key: str) -> str:
    """Return a safe storage key or raise a controlled backend error."""

    if not isinstance(key, str):
        raise StorageKeyError("storage key must be a string")
    if not STORAGE_KEY_PATTERN.fullmatch(key):
        raise StorageKeyError("storage key contains unsupported characters")
    if "." in key or "/" in key or "\\" in key:
        raise StorageKeyError("storage key must not contain path separators or dots")

    windows_key = PureWindowsPath(key)
    if Path(key).is_absolute() or windows_key.is_absolute() or windows_key.drive:
        raise StorageKeyError("storage key must be relative")
    return key


def storage_json_path(base_path: Path, key: str) -> Path:
    """Build a resolved JSON path and verify it stays inside the storage base."""

    safe_key = validate_storage_key(key)
    resolved_base = Path(base_path).resolve()
    candidate = (resolved_base / f"{safe_key}.json").resolve()
    if not candidate.is_relative_to(resolved_base):
        raise StorageKeyError("storage key resolves outside storage directory")
    return candidate
