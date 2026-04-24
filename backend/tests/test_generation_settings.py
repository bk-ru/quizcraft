from __future__ import annotations

import json

import pytest

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import GenerationSettingsError
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import GenerationSettings
from backend.app.storage.generation_settings import FileSystemGenerationSettingsRepository


def build_settings(**overrides: object) -> GenerationSettings:
    values: dict[str, object] = {
        "question_count": 3,
        "language": "ru",
        "difficulty": "medium",
        "quiz_type": "single_choice",
        "generation_mode": GenerationMode.DIRECT,
        "model_name": "local-model",
        "profile_name": "balanced",
    }
    values.update(overrides)
    return GenerationSettings(**values)


def test_generation_settings_repository_persists_and_loads_settings(tmp_path) -> None:
    repository = FileSystemGenerationSettingsRepository(tmp_path)
    settings = build_settings(profile_name="strict", model_name=None)

    saved = repository.save(settings)
    loaded = repository.get()

    assert saved == settings
    assert loaded == settings
    payload = json.loads((tmp_path / "settings" / "generation.json").read_text(encoding="utf-8"))
    assert payload["language"] == "ru"
    assert payload["profile_name"] == "strict"
    assert "model_name" not in payload


def test_generation_settings_repository_raises_when_settings_are_missing(tmp_path) -> None:
    repository = FileSystemGenerationSettingsRepository(tmp_path)

    with pytest.raises(RepositoryNotFoundError):
        repository.get()


def test_generation_settings_rejects_invalid_values() -> None:
    with pytest.raises(GenerationSettingsError, match="question_count"):
        build_settings(question_count=0)

    with pytest.raises(GenerationSettingsError, match="language"):
        build_settings(language="")


def test_generation_settings_roundtrips_without_losing_profile_fields() -> None:
    settings = build_settings(model_name=None, profile_name="strict")

    loaded = GenerationSettings.from_dict(settings.to_dict())

    assert loaded == settings
    assert loaded.profile_name == "strict"
    assert loaded.model_name is None
