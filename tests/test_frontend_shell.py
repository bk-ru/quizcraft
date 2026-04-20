from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"
STYLES_CSS = FRONTEND_DIR / "styles.css"
CONFIG_JS = FRONTEND_DIR / "config.js"
APP_JS = FRONTEND_DIR / "app.js"
API_CLIENT_JS = FRONTEND_DIR / "api" / "client.js"


def test_frontend_shell_files_exist() -> None:
    assert FRONTEND_DIR.is_dir()
    assert INDEX_HTML.is_file()
    assert STYLES_CSS.is_file()
    assert CONFIG_JS.is_file()
    assert APP_JS.is_file()
    assert API_CLIENT_JS.is_file()


def test_frontend_index_references_local_assets_and_uses_russian_defaults() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert '<html lang="ru">' in content
    assert '<meta charset="utf-8"' in content.lower()
    assert "QuizCraft" in content
    assert "Панель состояния" in content
    assert "./styles.css" in content
    assert "./config.js" in content
    assert "./app.js" in content

    referenced_assets = re.findall(r'(?:href|src)="(\./[^"]+)"', content)
    assert referenced_assets
    for relative_asset in referenced_assets:
        target_path = (FRONTEND_DIR / relative_asset[2:]).resolve()
        assert target_path.is_file(), f"missing referenced asset: {relative_asset}"


def test_api_client_exposes_existing_backend_endpoint_methods() -> None:
    content = API_CLIENT_JS.read_text(encoding="utf-8")

    assert "export class QuizCraftApiClient" in content
    assert "getBackendHealth" in content
    assert "getProviderHealth" in content
    assert "uploadDocument" in content
    assert "generateQuiz" in content
    assert "getQuiz" in content
    assert "updateQuiz" in content
    assert "/health" in content
    assert "/health/lm-studio" in content
    assert "/documents" in content
    assert "/quizzes/" in content


def test_frontend_config_exposes_backend_base_url() -> None:
    content = CONFIG_JS.read_text(encoding="utf-8")

    assert "backendBaseUrl" in content
    assert "window.QuizCraftConfig" in content
