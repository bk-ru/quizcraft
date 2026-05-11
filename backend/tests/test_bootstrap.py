import logging

from fastapi import FastAPI

from backend.app.core.config import AppConfig
from backend.app.main import create_app


def test_create_app_is_callable() -> None:
    assert callable(create_app)


def test_create_app_configures_requested_log_format() -> None:
    config = AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        log_format="%(levelname)s:%(message)s",
    )

    app = create_app(config=config)

    root_logger = logging.getLogger()
    assert isinstance(app, FastAPI)
    assert root_logger.handlers
    assert root_logger.handlers[0].formatter._fmt == "%(levelname)s:%(message)s"


def test_create_app_accepts_documented_json_log_format() -> None:
    config = AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        log_format="json",
    )

    app = create_app(config=config)

    root_logger = logging.getLogger()
    assert isinstance(app, FastAPI)
    assert root_logger.handlers
    assert root_logger.handlers[0].formatter.__class__.__name__ == "JsonLogFormatter"


def test_create_app_accepts_documented_text_log_format() -> None:
    config = AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        log_format="text",
    )

    app = create_app(config=config)

    root_logger = logging.getLogger()
    assert isinstance(app, FastAPI)
    assert root_logger.handlers
    assert root_logger.handlers[0].formatter._fmt == "%(asctime)s %(levelname)s %(name)s %(message)s"
