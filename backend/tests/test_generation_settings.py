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
    assert payload["mode_policy_version"] == 2
    assert "model_name" not in payload


def test_generation_settings_repository_reads_legacy_direct_as_auto(tmp_path) -> None:
    target_path = tmp_path / "settings" / "generation.json"
    target_path.parent.mkdir(parents=True)
    target_path.write_text(
        json.dumps(build_settings().to_dict(), ensure_ascii=False),
        encoding="utf-8",
    )
    repository = FileSystemGenerationSettingsRepository(tmp_path)

    loaded = repository.get()

    assert loaded.generation_mode is GenerationMode.AUTO
    assert loaded.language == "ru"


def test_generation_settings_repository_keeps_versioned_direct_explicit(tmp_path) -> None:
    repository = FileSystemGenerationSettingsRepository(tmp_path)

    repository.save(build_settings(generation_mode=GenerationMode.DIRECT))

    assert repository.get().generation_mode is GenerationMode.DIRECT


def test_generation_settings_repository_does_not_treat_null_policy_version_as_legacy(tmp_path) -> None:
    target_path = tmp_path / "settings" / "generation.json"
    target_path.parent.mkdir(parents=True)
    payload = build_settings().to_dict()
    payload["mode_policy_version"] = None
    target_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    repository = FileSystemGenerationSettingsRepository(tmp_path)

    loaded = repository.get()

    assert loaded.generation_mode is GenerationMode.DIRECT


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
