from __future__ import annotations

import pytest

from backend.app.core.config import AppConfig
from backend.app.core.config import ConfigurationError
from backend.app.core.config import GenerationProfile
from backend.app.domain.errors import GenerationProfileError
from backend.app.domain.errors import ModelSelectionError
from backend.app.generation.profiles import GenerationProfileResolver


def test_config_loads_model_whitelist_and_default_profiles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv("LM_STUDIO_ALLOWED_MODELS", "local-model, draft-model")

    config = AppConfig.from_env()

    assert config.allowed_models == ("local-model", "draft-model")
    assert sorted(config.generation_profiles) == ["balanced", "fast", "strict"]
    assert config.default_generation_profile == "balanced"


def test_config_rejects_default_model_outside_allowed_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv("LM_STUDIO_ALLOWED_MODELS", "draft-model")

    with pytest.raises(ConfigurationError, match="LM_STUDIO_MODEL"):
        AppConfig.from_env()


def test_config_loads_generation_profiles_from_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv("LM_STUDIO_ALLOWED_MODELS", "local-model, strict-model")
    monkeypatch.setenv("DEFAULT_GENERATION_PROFILE", "strict")
    monkeypatch.setenv(
        "GENERATION_PROFILES",
        '{"balanced": {"inference_parameters": {"temperature": 0.2}}, '
        '"strict": {"model_name": "strict-model", "inference_parameters": {"temperature": 0.0}}}',
    )

    config = AppConfig.from_env()

    assert config.default_generation_profile == "strict"
    assert config.generation_profiles["strict"].model_name == "strict-model"
    assert config.generation_profiles["strict"].inference_parameters == {"temperature": 0.0}


def test_profile_resolver_applies_default_profile_without_forcing_model_name() -> None:
    config = AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        allowed_models=("local-model", "draft-model"),
        generation_profiles={
            "balanced": GenerationProfile(
                name="balanced",
                inference_parameters={"temperature": 0.2},
            )
        },
        default_generation_profile="balanced",
    )

    resolved = GenerationProfileResolver(config).resolve(model_name=None, profile_name=None)

    assert resolved.profile_name == "balanced"
    assert resolved.model_name is None
    assert resolved.inference_parameters == {"temperature": 0.2}


def test_profile_resolver_validates_requested_model_against_whitelist() -> None:
    config = AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        allowed_models=("local-model",),
    )

    with pytest.raises(ModelSelectionError, match="not allowed"):
        GenerationProfileResolver(config).resolve(model_name="rogue-model", profile_name=None)


def test_profile_resolver_rejects_unknown_profile_name() -> None:
    config = AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        allowed_models=("local-model",),
    )

    with pytest.raises(GenerationProfileError, match="unknown generation profile"):
        GenerationProfileResolver(config).resolve(model_name=None, profile_name="experimental")
