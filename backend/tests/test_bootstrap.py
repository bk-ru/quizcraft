import logging

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

    create_app(config=config)

    root_logger = logging.getLogger()
    assert root_logger.handlers
    assert root_logger.handlers[0].formatter._fmt == "%(levelname)s:%(message)s"
