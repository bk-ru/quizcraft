import os
from pathlib import Path

import pytest

from backend.app.core.config import AppConfig, ConfigurationError, load_env_file
from backend.app.llm.registry import ProviderName


@pytest.fixture(autouse=True)
def _isolate_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point the config loader at an empty path so real ``.env`` files never leak into tests."""

    monkeypatch.setenv("QUIZCRAFT_ENV_FILE", str(tmp_path / "missing.env"))


def test_loads_required_and_optional_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv("REQUEST_TIMEOUT", "45")
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "20")
    monkeypatch.setenv("MAX_DOCUMENT_CHARS", "12345")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "%(levelname)s:%(message)s")

    config = AppConfig.from_env()

    assert config.lm_studio_base_url == "http://localhost:1234/v1"
    assert config.lm_studio_model == "local-model"
    assert config.request_timeout == 45
    assert config.max_file_size_mb == 20
    assert config.max_document_chars == 12345
    assert config.log_level == "DEBUG"
    assert config.log_format == "%(levelname)s:%(message)s"
    assert config.providers_enabled == (ProviderName.LM_STUDIO,)
    assert config.default_provider is ProviderName.LM_STUDIO
    assert config.default_model == "local-model"
    assert config.ollama_base_url == "http://localhost:11434"
    assert config.ollama_model == "local-model"
    assert config.ollama_embedding_model == "local-model"


def test_loads_provider_feature_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv("PROVIDERS_ENABLED", "lm_studio, ollama")

    config = AppConfig.from_env()

    assert config.providers_enabled == (ProviderName.LM_STUDIO, ProviderName.OLLAMA)


def test_loads_ollama_provider_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv("PROVIDERS_ENABLED", "ollama")
    monkeypatch.setenv("DEFAULT_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")
    monkeypatch.setenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

    config = AppConfig.from_env()

    assert config.providers_enabled == (ProviderName.OLLAMA,)
    assert config.default_provider is ProviderName.OLLAMA
    assert config.default_model == "qwen2.5:7b"
    assert config.ollama_base_url == "http://localhost:11434"
    assert config.ollama_model == "qwen2.5:7b"
    assert config.ollama_embedding_model == "nomic-embed-text"
    assert config.allowed_models == ("local-model", "qwen2.5:7b")


def test_uses_first_enabled_provider_as_default_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv("PROVIDERS_ENABLED", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")

    config = AppConfig.from_env()

    assert config.default_provider is ProviderName.OLLAMA
    assert config.default_model == "qwen2.5:7b"


def test_rejects_ollama_model_outside_allowed_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv("PROVIDERS_ENABLED", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")
    monkeypatch.setenv("LM_STUDIO_ALLOWED_MODELS", "local-model")

    with pytest.raises(ConfigurationError, match="OLLAMA_MODEL"):
        AppConfig.from_env()


def test_rejects_invalid_default_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv("DEFAULT_PROVIDER", "unknown")

    with pytest.raises(ConfigurationError, match="provider"):
        AppConfig.from_env()


@pytest.mark.parametrize(
    "providers_enabled",
    (
        "",
        "lm_studio,",
        "lm_studio,unknown",
        "lm_studio,lm_studio",
    ),
)
def test_rejects_invalid_provider_feature_flags(
    monkeypatch: pytest.MonkeyPatch,
    providers_enabled: str,
) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv("PROVIDERS_ENABLED", providers_enabled)

    with pytest.raises(ConfigurationError, match="PROVIDERS_ENABLED|provider"):
        AppConfig.from_env()


def test_max_document_chars_defaults_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.delenv("MAX_DOCUMENT_CHARS", raising=False)

    config = AppConfig.from_env()

    assert config.max_document_chars == 50_000


def test_request_timeout_defaults_to_five_minutes_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure local CPU LM Studio installs do not 504 on a fresh install.

    The default matches the `.env.example` value so behaviour is consistent
    whether or not the developer copied the template.
    """

    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.delenv("REQUEST_TIMEOUT", raising=False)

    config = AppConfig.from_env()

    assert config.request_timeout == 300


def test_max_document_chars_rejects_non_positive_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv("MAX_DOCUMENT_CHARS", "0")

    with pytest.raises(ConfigurationError, match="MAX_DOCUMENT_CHARS"):
        AppConfig.from_env()


def test_raises_when_required_setting_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LM_STUDIO_BASE_URL", raising=False)
    monkeypatch.delenv("LM_STUDIO_MODEL", raising=False)

    with pytest.raises(ConfigurationError, match="LM_STUDIO_BASE_URL"):
        AppConfig.from_env()


@pytest.mark.parametrize(
    ("env_name", "env_value"),
    (
        ("REQUEST_TIMEOUT", "oops"),
        ("MAX_FILE_SIZE_MB", "NaN"),
    ),
)
def test_raises_controlled_error_for_invalid_numeric_values(
    monkeypatch: pytest.MonkeyPatch,
    env_name: str,
    env_value: str,
) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv(env_name, env_value)

    with pytest.raises(ConfigurationError, match=env_name):
        AppConfig.from_env()


def test_load_env_file_returns_empty_when_missing(tmp_path: Path) -> None:
    result = load_env_file(tmp_path / "missing.env")

    assert result == {}


def test_load_env_file_parses_keys_values_comments_and_quotes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LM_STUDIO_BASE_URL", raising=False)
    monkeypatch.delenv("LM_STUDIO_MODEL", raising=False)
    monkeypatch.delenv("QUIZ_TITLE", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "# Комментарий на русском",
                "",
                "LM_STUDIO_BASE_URL=http://localhost:1234/v1",
                'LM_STUDIO_MODEL="local-model"',
                "export QUIZ_TITLE='Пример квиза'",
                "MALFORMED_LINE_WITHOUT_EQUALS",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_env_file(env_file)

    assert loaded == {
        "LM_STUDIO_BASE_URL": "http://localhost:1234/v1",
        "LM_STUDIO_MODEL": "local-model",
        "QUIZ_TITLE": "Пример квиза",
    }
    assert os.environ["QUIZ_TITLE"] == "Пример квиза"


def test_load_env_file_preserves_existing_env_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LM_STUDIO_MODEL", "shell-wins")
    env_file = tmp_path / ".env"
    env_file.write_text("LM_STUDIO_MODEL=file-value\n", encoding="utf-8")

    load_env_file(env_file)

    assert os.environ["LM_STUDIO_MODEL"] == "shell-wins"


def test_load_env_file_overrides_when_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LM_STUDIO_MODEL", "shell-value")
    env_file = tmp_path / ".env"
    env_file.write_text("LM_STUDIO_MODEL=file-wins\n", encoding="utf-8")

    load_env_file(env_file, override=True)

    assert os.environ["LM_STUDIO_MODEL"] == "file-wins"


def test_from_env_loads_quizcraft_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LM_STUDIO_BASE_URL", raising=False)
    monkeypatch.delenv("LM_STUDIO_MODEL", raising=False)
    monkeypatch.delenv("REQUEST_TIMEOUT", raising=False)

    env_file = tmp_path / "custom.env"
    env_file.write_text(
        "LM_STUDIO_BASE_URL=http://localhost:1234/v1\n"
        "LM_STUDIO_MODEL=local-model\n"
        "REQUEST_TIMEOUT=240\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("QUIZCRAFT_ENV_FILE", str(env_file))

    config = AppConfig.from_env()

    assert config.lm_studio_base_url == "http://localhost:1234/v1"
    assert config.lm_studio_model == "local-model"
    assert config.request_timeout == 240
