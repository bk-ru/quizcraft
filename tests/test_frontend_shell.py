from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler
from http.server import ThreadingHTTPServer
from pathlib import Path
import re
from threading import Thread
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"
CONFIG_JS = FRONTEND_DIR / "config.js"
APP_JS = FRONTEND_DIR / "app.js"
API_CLIENT_JS = FRONTEND_DIR / "api" / "client.js"
VALIDATION_ERRORS_JS = FRONTEND_DIR / "validation-errors.js"
QUIZ_RENDERER_JS = FRONTEND_DIR / "quiz-renderer.js"
QUIZ_EDITOR_JS = FRONTEND_DIR / "quiz-editor.js"
GENERATION_FLOW_JS = FRONTEND_DIR / "generation-flow.js"
PROGRESS_JS = FRONTEND_DIR / "progress.js"
THEME_JS = FRONTEND_DIR / "theme.js"
TOAST_JS = FRONTEND_DIR / "toast.js"
DOWNLOAD_JS = FRONTEND_DIR / "download.js"
FRONTEND_JS_MODULES = (
    APP_JS,
    VALIDATION_ERRORS_JS,
    QUIZ_RENDERER_JS,
    QUIZ_EDITOR_JS,
    GENERATION_FLOW_JS,
    PROGRESS_JS,
    THEME_JS,
    TOAST_JS,
    DOWNLOAD_JS,
)
FRONTEND_CSS_FILES = tuple(
    FRONTEND_DIR / filename
    for filename in (
        "tokens.css",
        "base.css",
        "layout.css",
        "forms.css",
        "quiz.css",
        "feedback.css",
        "responsive.css",
    )
)


@contextmanager
def serve_frontend():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        partial(SimpleHTTPRequestHandler, directory=str(FRONTEND_DIR)),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def read_frontend_js_bundle() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND_JS_MODULES)


def read_frontend_css_bundle() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND_CSS_FILES)


def test_frontend_shell_files_exist() -> None:
    assert FRONTEND_DIR.is_dir()
    assert INDEX_HTML.is_file()
    assert CONFIG_JS.is_file()
    assert API_CLIENT_JS.is_file()
    for module_path in FRONTEND_JS_MODULES:
        assert module_path.is_file()
    for css_path in FRONTEND_CSS_FILES:
        assert css_path.is_file()


def test_frontend_index_exposes_split_static_assets() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert "./styles.css" not in content
    for css_path in FRONTEND_CSS_FILES:
        assert f'./{css_path.name}' in content
    assert "./config.js" in content
    assert "./app.js" in content

    referenced_assets = re.findall(r'(?:href|src)="(\./[^"]+)"', content)
    assert referenced_assets
    for relative_asset in referenced_assets:
        target_path = (FRONTEND_DIR / relative_asset[2:]).resolve()
        assert target_path.is_file(), f"missing referenced asset: {relative_asset}"


def test_frontend_index_exposes_russian_result_view_shell() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert '<html lang="ru">' in content
    assert '<meta charset="utf-8"' in content.lower()
    assert "QuizCraft" in content
    assert "Панель состояния" in content
    assert "Загрузить документ" in content
    assert "Параметры генерации" in content
    assert "Сгенерировать квиз" in content
    assert "Результат генерации" in content
    assert "Квиз появится здесь после успешной генерации." in content
    assert 'id="generation-result"' in content
    assert 'id="quiz-title"' in content


def test_frontend_index_exposes_russian_quiz_edit_shell() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert "Редактирование квиза" in content
    assert "Открыть существующий квиз" in content
    assert "Идентификатор квиза" in content
    assert "Загрузить квиз" in content
    assert "Сохранить изменения" in content
    assert "Изменения пока не сохранены." in content
    assert 'id="quiz-editor-loader"' in content
    assert 'id="quiz-id-input"' in content
    assert 'id="quiz-editor-fields"' in content
    assert 'id="quiz-editor-status"' in content
    assert 'id="save-quiz-button"' in content


def test_frontend_app_imports_focused_modules() -> None:
    content = APP_JS.read_text(encoding="utf-8")

    for module_name in (
        "validation-errors.js",
        "quiz-renderer.js",
        "quiz-editor.js",
        "generation-flow.js",
        "progress.js",
        "theme.js",
        "toast.js",
        "download.js",
    ):
        assert f'./{module_name}' in content
    assert "createGenerationFlow" in content
    assert "createQuizEditor" in content
    assert "createQuizRenderer" in content


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


def test_api_client_uses_role_based_timeouts() -> None:
    content = API_CLIENT_JS.read_text(encoding="utf-8")

    assert "DEFAULT_TIMEOUTS" in content
    for role in ("health", "upload", "generate", "quizEditor"):
        assert f'"{role}"' in content or f"'{role}'" in content or role in content
    assert "timeoutMs" in content
    assert "this._timeouts" in content


def test_frontend_config_exposes_backend_base_url() -> None:
    content = CONFIG_JS.read_text(encoding="utf-8")

    assert "backendBaseUrl" in content
    assert "window.QuizCraftConfig" in content


def test_frontend_config_exposes_role_based_timeouts() -> None:
    content = CONFIG_JS.read_text(encoding="utf-8")

    assert "timeouts" in content
    assert "health" in content
    assert "upload" in content
    assert "generate" in content
    assert "quizEditor" in content


def test_frontend_app_wires_generation_and_edit_save_states() -> None:
    content = read_frontend_js_bundle()

    assert "uploadDocument" in content
    assert "generateQuiz" in content
    assert "renderQuizResult" in content
    assert "setResultState" in content
    assert '"ru"' in content
    assert '"direct"' in content
    assert "getQuiz" in content
    assert "updateQuiz" in content
    assert "renderQuizEditor" in content
    assert "loadQuizForEditing" in content
    assert "buildQuizUpdatePayload" in content
    assert "submitQuizEdits" in content
    assert "Загрузите документ" in content
    assert "Квиз создан" in content
    assert "Результат готов" in content
    assert "Квиз появится здесь после успешной генерации." in content
    assert "Изменения пока не сохранены." in content
    assert "Изменения сохранены." in content
    assert "Исправьте ошибки и повторите сохранение." in content


def test_frontend_app_autoloads_generated_quiz_into_editor() -> None:
    content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert "async function submitGeneration" in content
    assert "renderQuizResult(generationPayload)" in content
    assert "renderQuizEditor(generatedQuiz)" in content, (
        "submitGeneration must auto-render the freshly generated quiz into the editor"
    )
    assert "setQuizEditorSummary(generatedQuiz)" in content, (
        "submitGeneration must refresh the editor summary with the generated quiz"
    )
    assert "Новый квиз загружен в редактор" in content, (
        "editor status after auto-load must be in Russian and confirm the load"
    )


def test_frontend_marks_lm_studio_unavailable_as_critical() -> None:
    app_content = APP_JS.read_text(encoding="utf-8")

    assert re.search(r"unavailable\s*:\s*\"bad\"", app_content), (
        "statusMap must map LM Studio unavailable to the critical bad tone"
    )
    assert "LM_STUDIO_UNAVAILABLE_INSTRUCTION" in app_content
    assert "LM Studio недоступен" in app_content, (
        "Russian instruction for LM Studio unavailable state must be present"
    )
    assert "http://127.0.0.1:1234" in app_content, (
        "LM Studio instruction must point the user to the default provider URL"
    )
    assert 'setStatus("provider", "Недоступен · запустите LM Studio", "bad")' in app_content, (
        "provider topbar must surface the critical Russian marker on unavailable status"
    )


def test_frontend_collapses_technical_identifiers_into_details() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert 'class="inline-details"' in content, (
        "technical fields must be wrapped into collapsible inline-details blocks"
    )
    assert "<summary>Технические идентификаторы</summary>" in content, (
        "operation summary must expose a Russian-language collapse affordance"
    )
    assert "<summary>Технические детали квиза</summary>" in content, (
        "result overview must expose a Russian-language collapse affordance for model/prompt details"
    )

    document_id_match = re.search(
        r"<details class=\"inline-details\">[\s\S]+?Document ID[\s\S]+?</details>",
        content,
    )
    assert document_id_match is not None, (
        "Document ID must live inside a collapsed inline-details block"
    )
    assert 'id="last-filename"' in content.split('<details class="inline-details">', 1)[0], (
        "filename must stay visible outside the collapsed technical identifiers block"
    )


def test_frontend_styles_define_inline_details_affordance() -> None:
    content = (FRONTEND_DIR / "feedback.css").read_text(encoding="utf-8")

    assert ".inline-details" in content, (
        "styles must theme the inline-details blocks so they match the panel aesthetic"
    )
    assert ".inline-details > summary" in content
    assert ".inline-details[open]" in content


def test_frontend_app_translates_422_validation_errors_to_russian() -> None:
    content = VALIDATION_ERRORS_JS.read_text(encoding="utf-8")

    assert "describeValidationError" in content, (
        "app must expose a dedicated 422-error translator"
    )
    assert "VALIDATION_FIELD_EXACT_LABELS" in content, (
        "app must keep an exact field-path to Russian-label registry"
    )
    assert "VALIDATION_MESSAGE_RULES" in content, (
        "app must keep a rule registry for translating Pydantic and domain messages"
    )
    for russian_label in (
        "Заголовок квиза",
        "Количество вопросов",
        "Язык квиза",
        "Сложность",
        "Формат квиза",
    ):
        assert russian_label in content, f"missing Russian label: {russian_label}"


def test_frontend_app_translates_nested_question_and_option_paths() -> None:
    content = VALIDATION_ERRORS_JS.read_text(encoding="utf-8")

    assert "translateValidationFieldPath" in content
    assert r"quiz\.questions\.(\d+)" in content, (
        "translator must match the questions.N path pattern"
    )
    assert r"options\.(\d+)" in content, (
        "translator must match the options.M path pattern"
    )
    for russian_fragment in (
        "текст вопроса",
        "номер правильного варианта",
        "текст пояснения",
        "текст варианта",
    ):
        assert russian_fragment in content, (
            f"Russian translation for nested path is missing: {russian_fragment}"
        )


def test_frontend_app_translates_common_pydantic_and_domain_messages() -> None:
    content = VALIDATION_ERRORS_JS.read_text(encoding="utf-8")

    for russian_fragment in (
        "обязательное поле",
        "минимум",
        "ожидается целое число",
        "лишнее поле не допускается",
        "Варианты ответа не должны повторяться",
        "Номер правильного варианта вне диапазона",
        "Заголовок квиза не должен быть пустым",
    ):
        assert russian_fragment in content, (
            f"Russian translation for common validation message is missing: {russian_fragment}"
        )


def test_frontend_app_routes_422_through_russian_mapper_in_editor_save() -> None:
    content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")

    assert "async function submitQuizEdits" in content
    assert "describeValidationError(error)" in content, (
        "editor save catch must invoke the Russian 422 mapper on validation errors"
    )
    assert "Исправьте ошибки и повторите сохранение" in content


def test_frontend_app_routes_422_through_russian_mapper_in_generation() -> None:
    content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert "async function submitGeneration" in content
    assert "describeValidationError(error)" in content, (
        "generation catch must invoke the Russian 422 mapper on validation errors"
    )
    assert "error.status === 422" in content


def test_frontend_index_exposes_generation_progress_panel() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="generation-progress"' in content, (
        "index must expose the generation progress panel"
    )
    assert 'aria-live="polite"' in content
    for data_step in ("upload", "parse", "generate", "validate"):
        assert f'data-step="{data_step}"' in content, (
            f"progress panel must declare the {data_step} pseudo-step"
        )
    for russian_label in (
        "Загружаем документ",
        "Парсим",
        "Генерируем",
        "Валидируем",
    ):
        assert russian_label in content, (
            f"progress panel must include Russian label: {russian_label}"
        )


def test_frontend_app_drives_generation_progress_state() -> None:
    progress_content = PROGRESS_JS.read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    for helper in (
        "startGenerationProgress",
        "advanceGenerationProgress",
        "completeGenerationProgress",
        "failGenerationProgress",
        "waitForProgressVisibility",
    ):
        assert f"function {helper}" in progress_content, (
            f"progress module must define the {helper} progress helper"
        )

    assert "startGenerationProgress()" in generation_content
    assert 'advanceGenerationProgress("upload", "parse")' in generation_content
    assert 'advanceGenerationProgress("parse", "generate")' in generation_content
    assert 'advanceGenerationProgress("generate", "validate")' in generation_content
    assert "completeGenerationProgress()" in generation_content
    assert "failGenerationProgress(failedStep)" in generation_content


def test_frontend_styles_theme_generation_progress() -> None:
    content = (FRONTEND_DIR / "feedback.css").read_text(encoding="utf-8")

    assert ".generation-progress" in content
    assert ".progress-step" in content
    assert '.progress-step[data-state="active"]' in content
    assert '.progress-step[data-state="done"]' in content
    assert '.progress-step[data-state="failed"]' in content
    assert "progress-pulse" in content, (
        "progress panel must pulse the active step dot"
    )
    assert "@media (prefers-reduced-motion: reduce)" in content


def test_frontend_split_css_keeps_responsive_rules() -> None:
    content = (FRONTEND_DIR / "responsive.css").read_text(encoding="utf-8")

    assert "@media (max-width: 900px)" in content
    assert ".workspace-grid > .panel-upload" in content
    assert ".editor-loader" in content
    assert "@media (prefers-reduced-motion: reduce)" in content


def test_frontend_static_smoke_serves_russian_result_view_assets() -> None:
    with serve_frontend() as base_url:
        html = urlopen(f"{base_url}/").read().decode("utf-8")
        config_js = urlopen(f"{base_url}/config.js").read().decode("utf-8")
        app_js = urlopen(f"{base_url}/app.js").read().decode("utf-8")
        renderer_js = urlopen(f"{base_url}/quiz-renderer.js").read().decode("utf-8")
        editor_js = urlopen(f"{base_url}/quiz-editor.js").read().decode("utf-8")
        generation_js = urlopen(f"{base_url}/generation-flow.js").read().decode("utf-8")
        client_js = urlopen(f"{base_url}/api/client.js").read().decode("utf-8")
        css = urlopen(f"{base_url}/feedback.css").read().decode("utf-8")

    assert "Загрузить документ" in html
    assert "Параметры генерации" in html
    assert "Сгенерировать квиз" in html
    assert "Результат генерации" in html
    assert "Редактирование квиза" in html
    assert "Открыть существующий квиз" in html
    assert "Сохранить изменения" in html
    assert "backendBaseUrl" in config_js
    assert "createGenerationFlow" in app_js
    assert "renderQuizResult" in renderer_js
    assert "renderQuizEditor" in editor_js
    assert "submitQuizEdits" in editor_js
    assert "submitGeneration" in generation_js
    assert "generateQuiz" in client_js
    assert ".generation-progress" in css
