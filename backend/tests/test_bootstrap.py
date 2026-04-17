from backend.app.main import create_app


def test_create_app_is_callable() -> None:
    assert callable(create_app)
