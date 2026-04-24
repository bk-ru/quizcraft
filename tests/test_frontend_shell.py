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
QUIZ_HISTORY_JS = FRONTEND_DIR / "quiz-history.js"
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
    QUIZ_HISTORY_JS,
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
        "quiz-history.js",
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
    assert "createQuizHistory" in content


def test_api_client_exposes_existing_backend_endpoint_methods() -> None:
    content = API_CLIENT_JS.read_text(encoding="utf-8")

    assert "export class QuizCraftApiClient" in content
    assert "getBackendHealth" in content
    assert "getProviderHealth" in content
    assert "uploadDocument" in content
    assert "generateQuiz" in content
    assert "getQuiz" in content
    assert "updateQuiz" in content
    assert "regenerateQuestion" in content
    assert "/health" in content
    assert "/health/lm-studio" in content
    assert "/documents" in content
    assert "/quizzes/" in content
    assert "/questions/" in content
    assert "/regenerate" in content


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
    assert "regenerateQuizQuestion" in content
    assert "replaceRegeneratedQuestion" in content
    assert "Загрузите документ" in content
    assert "Квиз создан" in content
    assert "Результат готов" in content
    assert "Квиз появится здесь после успешной генерации." in content
    assert "Изменения пока не сохранены." in content
    assert "Изменения сохранены." in content
    assert "Исправьте ошибки и повторите сохранение." in content


def test_frontend_editor_wires_single_question_regeneration_action() -> None:
    app_content = APP_JS.read_text(encoding="utf-8")
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")
    client_content = API_CLIENT_JS.read_text(encoding="utf-8")

    assert "regenerateQuestion(quizId, questionId" in client_content
    assert 'method: "POST"' in client_content
    assert "/questions/" in client_content
    assert "/regenerate" in client_content
    assert "timeoutMs: this._timeouts.generate" in client_content
    assert "regenerateQuizQuestion" in editor_content
    assert "client.regenerateQuestion" in editor_content
    assert 'data-editor-action", "regenerate-question"' in editor_content
    assert "Перегенерировать вопрос" in editor_content
    assert "Перегенерируем вопрос" in editor_content
    assert "Не удалось перегенерировать вопрос" in editor_content
    assert "quizEditorFields?.addEventListener(\"click\", quizEditor.regenerateQuizQuestion)" in app_content


def test_frontend_editor_replaces_only_target_question_after_regeneration() -> None:
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")

    assert "function replaceRegeneratedQuestion" in editor_content
    assert "regeneratedQuestion.question_id" in editor_content
    assert "question.question_id === regeneratedQuestion.question_id" in editor_content
    assert "return regeneratedQuestion" in editor_content
    assert "renderQuizEditor(updatedQuiz)" in editor_content
    assert "renderQuizResult" in editor_content
    assert "regenerated_question" in editor_content
    assert "Остальные вопросы сохранены без изменений" in editor_content


def test_frontend_editor_preserves_displayed_state_outside_regenerated_question() -> None:
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")

    assert "const hadUnsavedEdits = editorState.isDirty" in editor_content
    assert "const displayedQuiz = buildQuizUpdatePayload()" in editor_content
    assert "...displayedQuiz" in editor_content
    assert "if (hadUnsavedEdits)" in editor_content
    assert "setEditorSaveState({ disabled: false })" in editor_content
    assert "сохранены локально" in editor_content


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
        "completeGenerationProgressWithBackendEvidence",
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
    assert "completeGenerationProgressWithBackendEvidence(generationPayload)" in generation_content
    assert "failGenerationProgress(failedStep)" in generation_content


def test_frontend_progress_aligns_with_backend_generation_status_evidence() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    progress_content = PROGRESS_JS.read_text(encoding="utf-8")

    for backend_status in ("queued", "running", "done", "failed"):
        assert backend_status in progress_content
    for backend_step in ("parse", "generate", "repair", "persist"):
        assert backend_step in progress_content

    assert "BACKEND_STEP_TO_PROGRESS_STEP" in progress_content
    assert 'repair: "generate"' in progress_content
    assert 'persist: "validate"' in progress_content
    assert "applyBackendGenerationStatusEvidence" in progress_content
    assert "completeGenerationProgressWithBackendEvidence" in progress_content
    assert "generation_status" in progress_content
    assert "pipeline_status" in progress_content
    assert "pipeline_events" in progress_content
    assert "completeGenerationProgressWithBackendEvidence: progressController.completeGenerationProgressWithBackendEvidence" in app_content
    assert "Генерируем" in index_content
    assert "Валидируем" in index_content


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
    assert "regenerateQuizQuestion" in editor_js
    assert "Перегенерировать вопрос" in editor_js
    assert "submitGeneration" in generation_js
    assert "generateQuiz" in client_js
    assert "regenerateQuestion" in client_js
    assert ".generation-progress" in css


def test_edit_shortcut_autoloads_last_generated_quiz_without_extra_click() -> None:
    content = APP_JS.read_text(encoding="utf-8")

    assert "function openEditorForCurrentQuiz" in content
    assert "editorState.lastGeneratedQuizId" in content
    assert "quizEditor.loadQuizForEditing" in content, (
        "edit shortcut must invoke the editor loader, not only scroll/focus"
    )
    assert (
        "editShortcutButton?.addEventListener(\"click\", openEditorForCurrentQuiz)"
        in content
    )


def test_frontend_index_hides_legacy_developer_only_sections() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert "endpoint-list" not in content, (
        "endpoint reference list is a developer concern and must not be surfaced in the default UI"
    )
    assert 'id="endpoint-title"' not in content
    assert 'id="shell-runtime-badge"' not in content
    assert "Используемые endpoint" not in content
    assert "technical-details" in content, (
        "the collapsed diagnostics panel must still exist for advanced users"
    )
    assert "Технические детали" in content


def test_frontend_quiz_history_module_and_wiring() -> None:
    history_content = QUIZ_HISTORY_JS.read_text(encoding="utf-8")
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert "export function createQuizHistory" in history_content
    assert "localStorage" in history_content or "storage.getItem" in history_content
    assert "quizcraft:recent-quizzes" in history_content, (
        "history module must persist under a namespaced localStorage key"
    )
    assert "saveQuizToHistory" in history_content
    assert "removeQuizFromHistory" in history_content
    assert "renderHistoryDatalist" in history_content

    assert 'id="quiz-history-options"' in index_content, (
        "index must expose the datalist used for quiz id autocompletion"
    )
    assert 'list="quiz-history-options"' in index_content, (
        "quiz id input must reference the datalist to surface local history"
    )

    assert "createQuizHistory" in app_content
    assert "quizHistory.renderHistoryDatalist" in app_content
    assert "saveQuizToHistory: quizHistory.saveQuizToHistory" in app_content

    assert "saveQuizToHistory" in editor_content, (
        "successful quiz load must record the entry in local history"
    )
    assert "saveQuizToHistory" in generation_content, (
        "successful generation must record the fresh quiz in local history"
    )


def test_frontend_quiz_history_module_persists_russian_titles() -> None:
    content = QUIZ_HISTORY_JS.read_text(encoding="utf-8")

    assert "JSON.stringify" in content
    assert "JSON.parse" in content
    assert "quiz_id" in content
    assert "title" in content
    assert "MAX_ENTRIES" in content
    assert "timestamp" in content


def test_frontend_generation_progress_has_cancel_button_and_timer() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    css_content = (FRONTEND_DIR / "feedback.css").read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert 'id="cancel-generation-button"' in index_content, (
        "generation progress must expose a cancel affordance"
    )
    assert "Отменить генерацию" in index_content
    assert 'id="generation-timer"' in index_content, (
        "generation progress must expose an elapsed-time readout"
    )
    assert ".generation-timer" in css_content
    assert ".generation-cancel" in css_content
    assert 'cancel-generation-button' in app_content
    assert "generation-timer" in app_content


def test_frontend_generation_flow_threads_abort_signal_and_cancel() -> None:
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    client_content = API_CLIENT_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert "new AbortController()" in generation_content
    assert "function cancelGeneration" in generation_content
    assert "cancelGeneration" in app_content, (
        "the cancel button click must be bound to the generation flow cancel helper"
    )
    assert (
        'cancelGenerationButton?.addEventListener("click", generationFlow.cancelGeneration)'
        in app_content
    )

    assert "abortController.signal" in generation_content
    assert "signal:" in client_content, (
        "API client helpers must thread the external signal through fetch"
    )
    assert "removeEventListener" in client_content
    assert "Запрос отменён пользователем" in client_content, (
        "user-cancel must map to a dedicated Russian message, not the timeout one"
    )
    assert "Генерация отменена" in generation_content or "отмен" in generation_content


def test_frontend_generation_timer_formats_and_warns_on_slow_generation() -> None:
    content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert "function formatElapsed" in content, (
        "generation flow must format the elapsed time locally"
    )
    assert 'padStart(2, "0")' in content
    assert "SLOW_GENERATION_WARNING_MS" in content
    assert "setInterval" in content
    assert "clearInterval" in content


def test_frontend_main_stepper_holds_four_product_phases() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    layout_css = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")
    progress_content = PROGRESS_JS.read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    stepper_block = re.search(
        r'<ol class="stepper"[^>]*id="stepper"[\s\S]+?</ol>',
        index_content,
    )
    assert stepper_block is not None, "main stepper must exist in the index"
    stepper_html = stepper_block.group(0)
    stepper_steps = re.findall(r'data-step="([^"]+)"', stepper_html)
    assert stepper_steps == ["upload", "params", "review", "edit"], (
        "main stepper must expose exactly the four product phases"
    )
    assert 'data-step="generate"' not in stepper_html, (
        "the technical generate stage must not duplicate the product stepper"
    )
    assert "Результат" in stepper_html, (
        "the third stepper phase must be labelled Результат, not Просмотр"
    )

    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in layout_css
    assert 'STEPPER_ORDER = ["upload", "params", "review", "edit"]' in progress_content
    assert 'advanceStepper("generate")' not in generation_content, (
        "generation flow must drive the product stepper, not the technical generate slot"
    )
    assert 'advanceStepper("review")' in generation_content


def test_frontend_editor_panel_badge_matches_four_step_product_flow() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert "Шаг 5" not in content, (
        "editor badge must match the collapsed four-phase flow"
    )
    assert "Шаг 4" in content
    assert "Шаг 1" in content
    assert "Шаг 2" in content
