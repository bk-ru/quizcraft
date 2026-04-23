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
STYLES_CSS = FRONTEND_DIR / "styles.css"
CONFIG_JS = FRONTEND_DIR / "config.js"
APP_JS = FRONTEND_DIR / "app.js"
API_CLIENT_JS = FRONTEND_DIR / "api" / "client.js"


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


def test_frontend_shell_files_exist() -> None:
    assert FRONTEND_DIR.is_dir()
    assert INDEX_HTML.is_file()
    assert STYLES_CSS.is_file()
    assert CONFIG_JS.is_file()
    assert APP_JS.is_file()
    assert API_CLIENT_JS.is_file()


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
    assert "./styles.css" in content
    assert "./config.js" in content
    assert "./app.js" in content

    referenced_assets = re.findall(r'(?:href|src)="(\./[^"]+)"', content)
    assert referenced_assets
    for relative_asset in referenced_assets:
        target_path = (FRONTEND_DIR / relative_asset[2:]).resolve()
        assert target_path.is_file(), f"missing referenced asset: {relative_asset}"


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
    content = APP_JS.read_text(encoding="utf-8")

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
    content = APP_JS.read_text(encoding="utf-8")

    submit_match = re.search(
        r"async function submitGeneration[\s\S]+?^}\n",
        content,
        re.MULTILINE,
    )
    assert submit_match is not None, "submitGeneration function must exist"
    submit_body = submit_match.group(0)

    assert "renderQuizResult(generationPayload)" in submit_body
    assert "renderQuizEditor(generatedQuiz)" in submit_body, (
        "submitGeneration must auto-render the freshly generated quiz into the editor"
    )
    assert "setQuizEditorSummary(generatedQuiz)" in submit_body, (
        "submitGeneration must refresh the editor summary with the generated quiz"
    )
    assert "Новый квиз загружен в редактор" in submit_body, (
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
    content = STYLES_CSS.read_text(encoding="utf-8")

    assert ".inline-details" in content, (
        "styles must theme the inline-details blocks so they match the panel aesthetic"
    )
    assert ".inline-details > summary" in content
    assert ".inline-details[open]" in content


def test_frontend_app_translates_422_validation_errors_to_russian() -> None:
    content = APP_JS.read_text(encoding="utf-8")

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
    content = APP_JS.read_text(encoding="utf-8")

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
    content = APP_JS.read_text(encoding="utf-8")

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
    content = APP_JS.read_text(encoding="utf-8")

    submit_edits_match = re.search(
        r"async function submitQuizEdits[\s\S]+?^}\n",
        content,
        re.MULTILINE,
    )
    assert submit_edits_match is not None, "submitQuizEdits function must exist"
    submit_edits_body = submit_edits_match.group(0)

    assert "describeValidationError(error)" in submit_edits_body, (
        "editor save catch must invoke the Russian 422 mapper on validation errors"
    )
    assert "Исправьте ошибки и повторите сохранение" in submit_edits_body


def test_frontend_app_routes_422_through_russian_mapper_in_generation() -> None:
    content = APP_JS.read_text(encoding="utf-8")

    submit_gen_match = re.search(
        r"async function submitGeneration[\s\S]+?^}\n",
        content,
        re.MULTILINE,
    )
    assert submit_gen_match is not None, "submitGeneration function must exist"
    submit_gen_body = submit_gen_match.group(0)

    assert "describeValidationError(error)" in submit_gen_body, (
        "generation catch must invoke the Russian 422 mapper on validation errors"
    )
    assert "error.status === 422" in submit_gen_body


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
    content = APP_JS.read_text(encoding="utf-8")

    for helper in (
        "startGenerationProgress",
        "advanceGenerationProgress",
        "completeGenerationProgress",
        "failGenerationProgress",
        "waitForProgressVisibility",
    ):
        assert f"function {helper}" in content, (
            f"app must define the {helper} progress helper"
        )

    submit_gen_match = re.search(
        r"async function submitGeneration[\s\S]+?^}\n",
        content,
        re.MULTILINE,
    )
    assert submit_gen_match is not None
    submit_body = submit_gen_match.group(0)

    assert "startGenerationProgress()" in submit_body
    assert 'advanceGenerationProgress("upload", "parse")' in submit_body
    assert 'advanceGenerationProgress("parse", "generate")' in submit_body
    assert 'advanceGenerationProgress("generate", "validate")' in submit_body
    assert "completeGenerationProgress()" in submit_body
    assert "failGenerationProgress(failedStep)" in submit_body


def test_frontend_styles_theme_generation_progress() -> None:
    content = STYLES_CSS.read_text(encoding="utf-8")

    assert ".generation-progress" in content
    assert ".progress-step" in content
    assert '.progress-step[data-state="active"]' in content
    assert '.progress-step[data-state="done"]' in content
    assert '.progress-step[data-state="failed"]' in content
    assert "progress-pulse" in content, (
        "progress panel must pulse the active step dot"
    )
    assert "@media (prefers-reduced-motion: reduce)" in content


def test_frontend_static_smoke_serves_russian_result_view_assets() -> None:
    with serve_frontend() as base_url:
        html = urlopen(f"{base_url}/").read().decode("utf-8")
        config_js = urlopen(f"{base_url}/config.js").read().decode("utf-8")
        app_js = urlopen(f"{base_url}/app.js").read().decode("utf-8")
        client_js = urlopen(f"{base_url}/api/client.js").read().decode("utf-8")

    assert "Загрузить документ" in html
    assert "Параметры генерации" in html
    assert "Сгенерировать квиз" in html
    assert "Результат генерации" in html
    assert "Редактирование квиза" in html
    assert "Открыть существующий квиз" in html
    assert "Сохранить изменения" in html
    assert "backendBaseUrl" in config_js
    assert "renderQuizResult" in app_js
    assert "renderQuizEditor" in app_js
    assert "submitQuizEdits" in app_js
    assert "generateQuiz" in client_js
