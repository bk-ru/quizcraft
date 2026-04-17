import pytest

from backend.app.core.config import AppConfig, ConfigurationError


def test_loads_required_and_optional_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv("REQUEST_TIMEOUT", "45")
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "20")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    config = AppConfig.from_env()

    assert config.lm_studio_base_url == "http://localhost:1234/v1"
    assert config.lm_studio_model == "local-model"
    assert config.request_timeout == 45
    assert config.max_file_size_mb == 20
    assert config.log_level == "DEBUG"


def test_raises_when_required_setting_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LM_STUDIO_BASE_URL", raising=False)
    monkeypatch.delenv("LM_STUDIO_MODEL", raising=False)

    with pytest.raises(ConfigurationError, match="LM_STUDIO_BASE_URL"):
        AppConfig.from_env()
