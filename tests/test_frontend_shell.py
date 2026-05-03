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
FORMS_CSS = FRONTEND_DIR / "forms.css"
API_CLIENT_JS = FRONTEND_DIR / "api" / "client.js"
VALIDATION_ERRORS_JS = FRONTEND_DIR / "validation-errors.js"
QUIZ_RENDERER_JS = FRONTEND_DIR / "quiz-renderer.js"
QUIZ_EDITOR_JS = FRONTEND_DIR / "quiz-editor.js"
QUIZ_HISTORY_JS = FRONTEND_DIR / "quiz-history.js"
GENERATION_FLOW_JS = FRONTEND_DIR / "generation-flow.js"
GENERATION_SETTINGS_JS = FRONTEND_DIR / "generation-settings.js"
KEYBOARD_JS = FRONTEND_DIR / "keyboard.js"
COPY_JS = FRONTEND_DIR / "copy.js"
PROGRESS_JS = FRONTEND_DIR / "progress.js"
STAGE_FLOW_JS = FRONTEND_DIR / "stage-flow.js"
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
    GENERATION_SETTINGS_JS,
    KEYBOARD_JS,
    COPY_JS,
    PROGRESS_JS,
    STAGE_FLOW_JS,
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
    assert "<title>QuizCraft</title>" in content
    assert "QuizCraft · Генерация квизов" not in content
    assert "Загрузить документ" in content
    assert "Параметры генерации" in content
    assert "Сгенерировать квиз" in content
    assert "Результат генерации" in content
    assert "Квиз появится здесь после успешной генерации." in content
    assert 'id="generation-result"' in content
    assert 'id="quiz-title"' in content


def test_frontend_index_exposes_supported_question_type_labels() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert "Типы вопросов:" in content
    assert 'data-question-type-group' in content
    assert 'class="question-type-label"' in content
    assert 'class="required-marker" aria-hidden="true">*</span>' in content
    assert 'class="question-type-list"' in content
    assert 'class="question-type-option"' in content
    assert "checkbox-grid" not in content
    assert "checkbox-option" not in content
    assert "quiz-type-hint" not in content
    styles = FORMS_CSS.read_text(encoding="utf-8")
    assert "color-scheme: inherit;" in styles
    assert ".question-type-option input" in styles
    assert "min-height: 16px;" in styles
    assert "padding: 0;" in styles
    assert "border: 0;" in styles
    assert 'name="quiz_types"' in content
    assert 'value="single_choice" checked' not in content
    for value, label in (
        ("single_choice", "Множественный Выбор"),
        ("true_false", "Истина /Ложь"),
        ("fill_blank", "Заполните пробел"),
        ("short_answer", "Краткий Ответ"),
        ("matching", "Соответствие"),
    ):
        assert f'value="{value}"' in content
        assert label in content


def test_frontend_index_exposes_russian_quiz_edit_shell() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert "Редактирование квиза" in content
    assert "Откройте редактор только когда нужно править готовый квиз или загрузить сохранённый." in content
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
    assert '<details id="quiz-editor" class="panel panel-editor editor-disclosure workflow-stage"' in content
    assert 'data-workflow-stage="edit"' in content


def test_frontend_app_imports_focused_modules() -> None:
    content = APP_JS.read_text(encoding="utf-8")

    for module_name in (
        "validation-errors.js",
        "quiz-renderer.js",
        "quiz-editor.js",
        "quiz-history.js",
        "generation-flow.js",
        "generation-settings.js",
        "keyboard.js",
        "copy.js",
        "progress.js",
        "stage-flow.js",
        "theme.js",
        "toast.js",
        "download.js",
    ):
        assert f'./{module_name}' in content
    assert "createGenerationFlow" in content
    assert "createStageFlowController" in content
    assert "createQuizEditor" in content
    assert "createQuizRenderer" in content
    assert "createQuizHistory" in content
    assert "createGenerationSettingsController" in content
    assert "createKeyboardShortcuts" in content
    assert "createCopyButtonController" in content


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
    assert "getExportFormats" in content
    assert "/health" in content
    assert "/health/lm-studio" in content
    assert "/export/formats" in content
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


def test_frontend_wires_capability_driven_advanced_exports() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    download_content = DOWNLOAD_JS.read_text(encoding="utf-8")

    assert 'id="export-json-button"' in index_content
    assert 'id="export-docx-button"' in index_content
    assert 'id="export-pptx-button"' in index_content
    assert 'id="export-split-toggle"' in index_content
    assert 'id="export-split-menu"' in index_content
    assert 'class="split-button"' in index_content
    assert "Скачать JSON" in index_content
    assert "Скачать DOCX" in index_content
    assert "Скачать PPTX" in index_content
    assert "подтверждения поддержки DOCX сервером" in index_content
    assert "подтверждения поддержки PPTX сервером" in index_content

    assert "supportedExportFormats" in app_content
    assert "getExportFormats" in app_content
    assert "parseSupportedExportFormats" in app_content
    assert "loadExportFormats" in app_content
    assert "format === \"json\" || editorState.supportedExportFormats.has(format)" in app_content
    assert "exportDocxButton?.addEventListener(\"click\", quizExporter.exportQuizAsDocx)" in app_content
    assert "exportPptxButton?.addEventListener(\"click\", quizExporter.exportQuizAsPptx)" in app_content
    assert "exportSplitToggle?.addEventListener" in app_content
    assert "exportSplitMenu" in app_content

    assert "createQuizExporter" in download_content
    assert "exportQuizAsDocx" in download_content
    assert "exportQuizAsPptx" in download_content
    assert "/export/${exportFormat}" in download_content
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in download_content
    assert "application/vnd.openxmlformats-officedocument.presentationml.presentation" in download_content
    assert "Не удалось скачать ${describeExportFormat(format)}" in download_content
    assert "function describeExportFormat" in download_content
    assert "${formatConfig.label}-файл квиза скачан." in download_content


def test_frontend_params_advanced_block_and_generation_mode() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")
    styles = (FRONTEND_DIR / "forms.css").read_text(encoding="utf-8")

    assert 'id="advanced-params"' in content
    assert 'class="form-advanced"' in content
    assert "\u0414\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044c\u043d\u043e" in content
    assert 'id="generation-model"' in content
    assert 'id="generation-profile"' in content
    assert "\u0410\u0432\u0442\u043e (RAG \u0434\u043b\u044f \u0434\u043b\u0438\u043d\u043d\u044b\u0445 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u043e\u0432)" in content
    assert "RAG \u2014 \u0432\u0441\u0435\u0433\u0434\u0430" in content
    assert ".form-advanced" in styles
    assert ".form-advanced-summary" in styles


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


def test_frontend_generation_focuses_result_before_explicit_editor_open() -> None:
    content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    index_content = INDEX_HTML.read_text(encoding="utf-8")

    assert "async function submitGeneration" in content
    assert "renderQuizResult(generationPayload)" in content
    assert "renderQuizEditor(generatedQuiz)" not in content, (
        "submitGeneration must not auto-present the freshly generated quiz in the editor"
    )
    assert "setQuizEditorSummary(generatedQuiz)" not in content, (
        "submitGeneration must leave editor rendering to the explicit edit action"
    )
    assert "Квиз готов. Нажмите «Редактировать квиз», чтобы открыть редактор." in content, (
        "generation completion must explain the explicit edit action in Russian"
    )
    assert "focusResultView()" in content
    assert 'id="generation-result"' in index_content and 'tabindex="-1"' in index_content
    assert "function focusResultView" in app_content
    assert "resultPanel.scrollIntoView" in app_content
    assert "resultPanel.focus" in app_content
    assert "editorPanel.open = true" in app_content, (
        "the result edit action must explicitly open the collapsed editor"
    )
    assert 'stageFlow.activateStage("edit", { focus: true })' in app_content, (
        "the result edit action must switch to the dedicated edit stage"
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
    assert 'setStatus("provider", "Недоступен · запустите LM Studio", "bad", LM_STUDIO_UNAVAILABLE_INSTRUCTION)' in app_content, (
        "provider topbar must surface the critical Russian marker on unavailable status"
    )


def test_frontend_status_tooltips_and_retry_buttons_are_wired() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    layout_content = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")

    assert 'data-status-label="Сервер"' in index_content
    assert 'data-status-label="LM Studio"' in index_content
    assert 'data-status-tooltip="Сервер · Проверка…"' in index_content
    assert 'data-status-tooltip="LM Studio · Проверка…"' in index_content
    assert 'tabindex="0"' in index_content
    assert 'id="retry-backend-button"' in index_content
    assert 'id="retry-provider-button"' in index_content
    assert 'aria-label="Повторно проверить подключение к серверу"' in index_content
    assert 'aria-label="Повторно проверить подключение к LM Studio"' in index_content
    assert 'class="status-retry-inline"' in index_content

    assert "BACKEND_CHECK_FAILED_INSTRUCTION" in app_content
    assert "PROVIDER_CHECK_FAILED_INSTRUCTION" in app_content
    assert "PROVIDER_CHECK_BLOCKED_INSTRUCTION" in app_content
    assert "container.dataset.statusTooltip = title" in app_content
    assert 'container.setAttribute("aria-label", title)' in app_content
    assert "function setRetryButtonBusy" in app_content
    assert "function checkBackendConnection" in app_content
    assert "function checkProviderConnection" in app_content
    assert 'retryBackendButton?.addEventListener("click"' in app_content
    assert 'retryProviderButton?.addEventListener("click"' in app_content

    assert ".status-retry" in layout_content
    assert ".status-retry-inline" in layout_content
    assert ".topbar-status-group" in layout_content
    assert ".topbar-status::after" in layout_content
    assert "content: attr(data-status-tooltip)" in layout_content
    assert "border-radius: var(--radius-md)" in layout_content
    assert "transition: opacity 120ms" in layout_content
    assert ".topbar-status:hover::after" in layout_content
    assert ".topbar-status:focus-visible::after" in layout_content


def test_frontend_generation_preflight_status_is_visible_on_setup_stage() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert 'id="preflight-status"' in index_content, (
        "setup stage must expose a visible status slot for blocked generation attempts"
    )
    assert 'aria-live="polite"' in index_content
    assert "setPreflightStatus" in generation_content
    assert "setPreflightStatus" in app_content
    assert "Генерация недоступна" in app_content
    assert "backend и LM Studio" in app_content
    assert "LM Studio недоступен" in app_content


def test_frontend_generation_flow_blocks_submit_when_services_are_unavailable() -> None:
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert "getGenerationReadiness" in generation_content
    assert "const readiness = getGenerationReadiness()" in generation_content
    submit_index = generation_content.find("async function submitGeneration")
    readiness_index = generation_content.find("const readiness = getGenerationReadiness()", submit_index)
    file_index = generation_content.find("const file = fileInput?.files?.[0]", submit_index)
    upload_index = generation_content.find("uploadPayload = await client.uploadDocument")
    assert readiness_index != -1 and file_index != -1 and upload_index != -1
    assert readiness_index < file_index < upload_index, (
        "connection readiness must be checked before file validation and network calls"
    )
    assert "if (!readiness.ready)" in generation_content
    assert "return;" in generation_content[readiness_index:upload_index]
    assert "createGenerationReadinessChecker" in app_content
    assert "generationConnectionState" in app_content


def test_frontend_collapses_technical_identifiers_into_details() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert 'class="inline-details"' in content, (
        "technical fields must be wrapped into collapsible inline-details blocks"
    )
    assert "<summary>Диагностика и технические ID</summary>" in content, (
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
    assert '<details class="inline-details" open' not in content, (
        "technical identifiers must stay collapsed by default"
    )


def test_frontend_visible_status_surface_receives_shell_log_messages() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert 'id="shell-log-message"' in index_content, (
        "index must expose a visible Russian status target for setLogMessage"
    )
    assert "Проверяем подключение к сервисам генерации" in index_content
    assert 'document.getElementById("shell-log-message")' in app_content
    assert "element.hidden = !text" in app_content, (
        "empty log messages must hide the status target instead of leaving stale text"
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
        "Типы вопросов",
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
        "Извлекаем текст",
        "Генерируем",
        "Проверяем квиз",
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
    assert "Проверяем квиз" in index_content


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
    assert 'id="technical-details"' not in content, (
        "the global diagnostics panel must be removed; technical IDs live in per-section inline-details"
    )
    assert 'id="shell-log-message"' in content, (
        "the shell log target now backs the visible Russian status surface"
    )
    assert 'id="backend-base-url"' not in content
    assert 'id="request-timeout"' not in content


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
    assert stepper_steps == ["setup", "generation", "result", "edit"], (
        "main stepper must expose the four staged product phases"
    )
    assert 'data-step="generate"' not in stepper_html, (
        "the technical generate stage must not duplicate the product stepper"
    )
    assert "Документ и параметры" in stepper_html, (
        "the first stage must combine document upload and generation parameters"
    )
    assert "Генерация" in stepper_html, (
        "the second stage must focus on request progress"
    )
    assert "Результат" in stepper_html, (
        "the third stage must be labelled Результат"
    )
    assert "Редактирование и экспорт" in stepper_html

    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in layout_css
    assert 'STEPPER_ORDER = ["setup", "generation", "result", "edit"]' in progress_content
    assert 'normalizeWorkflowStage(stageName)' in progress_content
    assert 'advanceStepper("generate")' not in generation_content, (
        "generation flow must drive the product stepper, not the technical generate slot"
    )
    assert 'advanceStepper("generation", { focus: true })' in generation_content
    assert 'advanceStepper("setup", { focus: true })' in generation_content


def test_frontend_index_uses_staged_workflow_sections() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    stage_content = STAGE_FLOW_JS.read_text(encoding="utf-8")
    layout_content = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")

    assert 'data-stage-root data-active-stage="setup"' in index_content
    assert 'id="generation-form" class="workspace-grid workflow-stage" data-workflow-stage="setup"' in index_content
    assert 'data-workflow-stage="generation"' in index_content
    assert 'data-workflow-stage="result"' in index_content
    assert 'data-workflow-stage="edit"' in index_content
    assert 'data-stage-target="setup"' in index_content
    assert 'data-stage-target="generation"' in index_content
    assert 'data-stage-target="result"' in index_content
    assert 'data-stage-target="edit"' in index_content
    assert "panel-upload panel-form" in index_content
    assert "panel-params panel-form" in index_content

    assert "export function normalizeWorkflowStage" in stage_content
    assert 'upload: "setup"' in stage_content
    assert 'params: "setup"' in stage_content
    assert 'review: "result"' in stage_content
    assert "createStageFlowController" in stage_content
    assert "stage.hidden = !isActive" in stage_content

    assert "const stageRoot = document.querySelector" in app_content
    assert "const stageFlow = createStageFlowController" in app_content
    assert "progressController.advanceStepper(target.dataset.stageTarget" in app_content
    assert ".workflow-stage[hidden]" in layout_content
    assert "@keyframes stage-in" in layout_content


def test_frontend_stepper_is_the_single_source_of_truth_for_phases() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert "Шаг 5" not in content, (
        "the stepper only has four phases, so Шаг 5 must not leak into the UI"
    )
    for step_label in ("Шаг 1", "Шаг 2", "Шаг 3", "Шаг 4"):
        assert step_label not in content, (
            f"panels must not duplicate the stepper with a '{step_label}' badge"
        )
    assert 'id="stepper"' in content, (
        "the main stepper remains the single source of truth for the phase"
    )


def test_frontend_dropzone_surface_exposes_filled_preview_affordance() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    forms_css = (FRONTEND_DIR / "forms.css").read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert 'data-state="empty"' in index_content
    assert 'class="dropzone-empty"' in index_content
    assert 'class="dropzone-filled"' in index_content
    assert 'id="dropzone-file-name"' in index_content
    assert 'id="dropzone-file-meta"' in index_content
    assert 'id="dropzone-remove"' in index_content, (
        "dropzone preview must expose a remove-file affordance"
    )
    assert "Убрать" in index_content

    assert '.dropzone[data-state="filled"]' in forms_css
    assert ".dropzone-remove" in forms_css
    assert ".dropzone-file-name" in forms_css

    assert "function formatFileSize" in generation_content
    assert "function applyDropzoneFilled" in generation_content
    assert "function removeSelectedFile" in generation_content
    assert 'dropzone.dataset.state = "filled"' in generation_content
    assert 'dropzone.dataset.state = "empty"' in generation_content
    assert "removeSelectedFile" in app_content
    assert "dropzoneRemoveButton?.addEventListener" in app_content


def test_frontend_dropzone_file_size_formatter_uses_russian_units() -> None:
    content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert 'unit: "Б"' in content
    assert 'unit: "КБ"' in content
    assert 'unit: "МБ"' in content
    assert "replace(\".\", \",\")" in content, (
        "file size formatter must emit locale-friendly decimal commas"
    )


def test_frontend_a11y_disabled_buttons_have_screen_reader_hints() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")
    base_css = (FRONTEND_DIR / "base.css").read_text(encoding="utf-8")

    assert ".visually-hidden" in base_css, (
        "a visually-hidden utility class must exist for screen-reader-only text"
    )
    assert "clip: rect(0, 0, 0, 0);" in base_css

    for button_id, hint_id in (
        ("export-json-button", "export-json-hint"),
        ("export-docx-button", "export-docx-hint"),
        ("export-pptx-button", "export-pptx-hint"),
        ("edit-quiz-shortcut", "edit-shortcut-hint"),
        ("save-quiz-button", "save-quiz-hint"),
    ):
        assert f'id="{button_id}"' in index_content
        assert f'aria-describedby="{hint_id}"' in index_content, (
            f"{button_id} must be described by {hint_id} while disabled"
        )
        assert f'id="{hint_id}" class="visually-hidden"' in index_content, (
            f"{hint_id} must be a visually-hidden Russian hint"
        )

    assert "Доступно после успешной генерации квиза" in index_content, (
        "result-action hints must explain the unavailable state in Russian"
    )
    assert "Доступно после загрузки квиза" in index_content, (
        "save hint must explain the unavailable state in Russian"
    )

    assert "toggleUnavailableHint" in app_content, (
        "app must expose a helper that flips aria-describedby alongside disabled"
    )
    assert "removeAttribute(\"aria-describedby\")" in app_content

    assert 'setAttribute("aria-describedby", "save-quiz-hint")' in editor_content, (
        "editor must restore the save hint when the button re-disables"
    )
    assert 'removeAttribute("aria-describedby")' in editor_content


def test_frontend_a11y_toast_uses_alert_role_for_bad_tone() -> None:
    toast_content = TOAST_JS.read_text(encoding="utf-8")

    assert 'tone === "bad" ? "alert" : "status"' in toast_content, (
        "toast must use role=alert for errors and role=status otherwise"
    )
    assert 'setAttribute("aria-atomic", "true")' in toast_content, (
        "toast must be announced atomically so the full message is re-read"
    )


def test_frontend_theme_toggle_swaps_icon_per_active_theme() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    layout_css = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")

    for theme_icon in ("auto", "light", "dark"):
        assert f'data-theme-icon="{theme_icon}"' in index_content, (
            f"theme toggle must carry an icon for the {theme_icon} theme"
        )

    assert ".theme-toggle .theme-toggle-icon" in layout_css, (
        "icons must be hidden by default so only the active one renders"
    )
    for theme_name in ("auto", "light", "dark"):
        assert f':root[data-theme="{theme_name}"] .theme-toggle .theme-toggle-icon[data-theme-icon="{theme_name}"]' in layout_css, (
            f"stylesheet must reveal the {theme_name} icon when that theme is active"
        )

    assert ':root:not([data-theme]) .theme-toggle .theme-toggle-icon[data-theme-icon="auto"]' in layout_css, (
        "when no theme is applied yet, the auto icon must still be visible"
    )


def test_frontend_hero_is_compact_and_pulse_is_not_infinite() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    layout_css = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert 'class="hero-copy"' not in index_content, (
        "the hero must not duplicate the upload-panel copy"
    )

    assert "padding: 28px 0 20px;" in layout_css, (
        "hero vertical footprint must be compact"
    )
    assert "font-size: clamp(1.8rem, 3.2vw, 2.6rem);" in layout_css, (
        "hero heading must use the smaller clamp range"
    )
    assert "animation: pulse 1.8s infinite" not in layout_css, (
        "pulse animation must not loop forever"
    )
    assert "prefers-reduced-motion: no-preference" in layout_css, (
        "pulse animation must be guarded by a reduced-motion media query"
    )

    assert "DEFAULT_GENERATION_MODE" in generation_content, (
        "generation_mode must keep a module-level fallback constant for unsupported user input"
    )


def test_frontend_copy_buttons_module_and_wiring() -> None:
    copy_content = COPY_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    forms_css = (FRONTEND_DIR / "forms.css").read_text(encoding="utf-8")

    assert "export function createCopyButtonController" in copy_content
    assert "clipboard.writeText" in copy_content, (
        "copy controller must use navigator.clipboard.writeText"
    )
    assert "data-copy-for" in copy_content, (
        "copy buttons must be discovered by the data-copy-for attribute"
    )
    assert "EMPTY_VALUE_MARKERS" in copy_content, (
        "copy controller must refuse to copy placeholder values"
    )
    assert "Ещё нет" in copy_content and "Ещё не загружен" in copy_content, (
        "placeholder markers must cover the Russian copy"
    )
    assert "Скопировано" in copy_content, (
        "success toast must confirm the copy in Russian"
    )

    assert "createCopyButtonController({" in app_content
    assert "copyButtons.register()" in app_content

    for source_id in (
        "last-document-id",
        "last-quiz-id",
        "last-request-id",
        "editor-quiz-id",
        "editor-document-id",
    ):
        assert f'data-copy-for="{source_id}"' in index_content, (
            f"{source_id} must have an associated copy button"
        )
        assert f'id="{source_id}"' in index_content

    assert 'aria-label="Скопировать Quiz ID"' in index_content, (
        "copy buttons must expose an accessible Russian label"
    )

    assert ".copy-button" in forms_css and ".copyable-field" in forms_css, (
        "copy buttons must be styled"
    )


def test_frontend_keyboard_shortcuts_module_and_wiring() -> None:
    keyboard_content = KEYBOARD_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    toast_content = TOAST_JS.read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    base_css = (FRONTEND_DIR / "base.css").read_text(encoding="utf-8")

    assert "export function createKeyboardShortcuts" in keyboard_content
    assert "isPrimaryModifier" in keyboard_content, (
        "shortcut handler must detect Ctrl or Cmd as the primary modifier"
    )
    assert "metaKey" in keyboard_content and "ctrlKey" in keyboard_content
    assert 'key === "escape"' in keyboard_content, (
        "Escape must be handled"
    )
    assert 'key === "s"' in keyboard_content and 'key === "enter"' in keyboard_content, (
        "Ctrl/Cmd+S and Ctrl/Cmd+Enter must be handled"
    )
    assert "isEditableTarget" in keyboard_content, (
        "shortcut handler must know when the user is typing in an input"
    )
    assert "cancelGeneration" in keyboard_content
    assert "dismissAllToasts" in keyboard_content
    assert "submitQuizEdits" in keyboard_content
    assert "requestSubmit" in keyboard_content

    assert "createKeyboardShortcuts({" in app_content, (
        "app must construct the keyboard shortcuts controller"
    )
    assert "keyboardShortcuts.register()" in app_content, (
        "app must register the keydown handler at bootstrap"
    )

    assert "dismissAllToasts" in toast_content, (
        "toast controller must expose a bulk-dismiss helper for Escape"
    )
    assert "return true" in generation_content and "return false" in generation_content, (
        "cancelGeneration must report whether it actually cancelled a run"
    )

    assert "<kbd>Ctrl/⌘</kbd>" in index_content and "<kbd>Enter</kbd>" in index_content, (
        "submit hint must advertise the Ctrl/Cmd+Enter shortcut"
    )
    assert "<kbd>S</kbd>" in index_content, (
        "save hint must advertise the Ctrl/Cmd+S shortcut"
    )
    assert "kbd {" in base_css, (
        "kbd elements must be styled as keyboard key pills"
    )


def test_frontend_explains_auto_persisted_generation_defaults() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    settings_content = GENERATION_SETTINGS_JS.read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    forms_css = (FRONTEND_DIR / "forms.css").read_text(encoding="utf-8")

    assert 'data-hint="defaults"' in index_content, (
        "form must carry an inline hint explaining that parameters are remembered automatically"
    )
    assert "После успешной генерации выбранные параметры запоминаются" in index_content, (
        "hint copy must explain the behavior in Russian"
    )
    assert "id=\"remember-generation-settings\"" not in index_content, (
        "the misleading remember checkbox must not ship"
    )
    assert ".form-hint" in forms_css

    assert "refreshAfterGeneration" in settings_content, (
        "controller must expose a refresh helper so selectors reflect the freshly saved defaults"
    )
    assert "rememberCheckbox" not in settings_content, (
        "controller must not depend on a remember checkbox"
    )

    assert "refreshGenerationDefaults: generationSettings.refreshAfterGeneration" in app_content, (
        "app bootstrap must wire the refresh helper into the generation flow"
    )
    assert "refreshGenerationDefaults()" in generation_content, (
        "generation flow must refresh the defaults after a successful run"
    )


def test_frontend_result_panel_has_idle_empty_state_illustration() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    quiz_css = (FRONTEND_DIR / "quiz.css").read_text(encoding="utf-8")

    assert "result-empty-state" in index_content, (
        "result panel must render a dedicated empty state block"
    )
    assert "Здесь появится ваш квиз" in index_content, (
        "empty state must show a clear Russian title"
    )
    assert "Загрузите документ слева" in index_content, (
        "empty state must hint the user at the next action in Russian"
    )
    assert 'role="img"' in index_content and "Иллюстрация пустого квиза" in index_content, (
        "empty state illustration must have an accessible role and label"
    )

    assert ".result-empty-state" in quiz_css
    assert "panel-result[data-result-tone=\"idle\"] .result-empty-state" in quiz_css, (
        "empty state must be wired to the idle tone"
    )
    assert "panel-result[data-result-tone=\"idle\"] .result-overview" in quiz_css and "display: none" in quiz_css, (
        "legacy placeholders must be hidden while the empty state is active"
    )


def test_frontend_stepper_exposes_failed_state_on_generation_error() -> None:
    progress_content = PROGRESS_JS.read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    layout_content = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")

    assert "markStepperFailed" in progress_content, (
        "progress controller must expose a helper to mark a stepper phase as failed"
    )
    assert "options.state === \"failed\"" in progress_content, (
        "advanceStepper must accept an explicit failed state option"
    )

    assert "markStepperFailed: progressController.markStepperFailed" in app_content, (
        "the failed-step helper must be wired into the generation flow"
    )
    assert "markStepperFailed(\"generation\")" in generation_content, (
        "generation flow must mark the generation phase as failed on real errors"
    )
    assert "advanceStepper(\"setup\", { focus: true })" in generation_content, (
        "user-cancelled generation must roll the stepper back to setup, not failed"
    )

    assert ".step[data-state=\"failed\"]" in layout_content, (
        "stylesheet must provide a visual for the failed step state"
    )


def test_frontend_model_and_profile_selectors_are_wired_to_backend() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    settings_content = GENERATION_SETTINGS_JS.read_text(encoding="utf-8")
    client_content = API_CLIENT_JS.read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert 'id="generation-model"' in index_content, (
        "upload form must expose a model selector"
    )
    assert 'id="generation-profile"' in index_content, (
        "upload form must expose a generation profile selector"
    )
    assert 'name="model_name"' in index_content
    assert 'name="profile_name"' in index_content
    assert "Модель" in index_content
    assert "Профиль" in index_content
    assert ">Авто<" in index_content, (
        "selectors must default to Russian auto-mode when no override is picked"
    )

    assert "export function createGenerationSettingsController" in settings_content
    assert "loadSettings" in settings_content
    assert "populateModelSelect" in settings_content
    assert "populateProfileSelect" in settings_content
    assert "available_models" in settings_content
    assert "available_profiles" in settings_content
    assert "default_model" in settings_content
    assert "default_profile" in settings_content
    assert "humanizeProfile" in settings_content
    assert "Быстрый" in settings_content and "Сбалансированный" in settings_content and "Строгий" in settings_content

    assert "getGenerationSettings" in client_content, (
        "API client must expose getGenerationSettings"
    )
    assert '"/generation/settings"' in client_content

    assert 'formData.get("model_name")' in generation_content, (
        "generation payload must pick up the model_name override from the form"
    )
    assert 'formData.get("profile_name")' in generation_content, (
        "generation payload must pick up the profile_name override from the form"
    )
    assert "payload.model_name = modelName" in generation_content
    assert "payload.profile_name = profileName" in generation_content

    assert "generationSettings.loadSettings()" in app_content, (
        "app bootstrap must request available models/profiles from backend"
    )


def test_frontend_editor_confirms_destructive_regenerate_action() -> None:
    content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")

    assert "REGENERATE_CONFIRM_TITLE" in content, (
        "the confirmation title must be extracted into a single Russian constant"
    )
    assert "REGENERATE_CONFIRM_BODY" in content, (
        "the confirmation body must be extracted into a single Russian constant"
    )
    assert "Перегенерировать вопрос?" in content, (
        "confirmation title must ask the user in Russian"
    )
    assert "Несохранённые правки других вопросов останутся" in content, (
        "confirmation body must reassure the user about unsaved edits"
    )
    assert "askForConfirmation" in content
    assert "defaultConfirmAction" in content
    assert "globalThis.confirm" not in content, (
        "default confirmation must no longer delegate to the native window.confirm"
    )
    assert "Promise.resolve(true)" in content, (
        "defaultConfirmAction must keep its async Promise<boolean> contract"
    )
    assert "Перегенерация отменена" in content, (
        "cancel path must show a Russian status about leaving the question untouched"
    )
    confirm_guard_index = content.find("const confirmed = await askForConfirmation({")
    client_call_index = content.find("client.regenerateQuestion(")
    assert confirm_guard_index != -1, (
        "regenerate must await an async confirmation that receives a structured options object"
    )
    assert client_call_index != -1
    assert confirm_guard_index < client_call_index, (
        "confirmation must run before invoking the backend regenerate endpoint"
    )


def test_frontend_modal_module_exposes_createConfirmModal() -> None:
    modal_path = FRONTEND_DIR / "modal.js"
    assert modal_path.is_file(), "frontend must ship a modal module backing destructive confirmations"
    content = modal_path.read_text(encoding="utf-8")

    assert "export function createConfirmModal" in content, (
        "modal module must expose createConfirmModal as the only public factory"
    )
    assert "dialog.showModal" in content, (
        "confirm modal must use the native <dialog> element so focus trap and Esc are free"
    )
    assert "dialog.addEventListener(\"cancel\"" in content, (
        "Esc on the dialog must resolve the promise as cancelled"
    )
    assert "dialog.addEventListener(\"close\"" in content, (
        "dialog close must resolve the promise"
    )
    assert "dialog.addEventListener(\"click\"" in content, (
        "backdrop click must resolve the promise as cancelled"
    )
    assert "restore.focus" in content, (
        "modal must restore focus to the previously focused element after closing"
    )


def test_frontend_index_mounts_modal_region() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="modal-region"' in content, (
        "index must expose a modal-region container so confirm dialogs have a stable mount point"
    )
    assert 'class="modal-region"' in content, (
        "modal-region must use a styled class to opt into the fixed-position overlay"
    )


def test_frontend_modal_region_is_styled_in_feedback_css() -> None:
    feedback_css = (FRONTEND_DIR / "feedback.css").read_text(encoding="utf-8")

    assert ".modal-region" in feedback_css, (
        "feedback.css must style the modal-region container"
    )
    assert ".confirm-modal" in feedback_css, (
        "feedback.css must style the confirm-modal dialog"
    )
    assert ".confirm-modal::backdrop" in feedback_css, (
        "confirm-modal must dim the page behind the dialog using ::backdrop"
    )
    assert ".confirm-modal-actions" in feedback_css, (
        "confirm-modal action row must be styled"
    )


def test_frontend_app_wires_confirm_modal_into_quiz_editor() -> None:
    app_content = APP_JS.read_text(encoding="utf-8")

    assert 'import { createConfirmModal } from "./modal.js"' in app_content, (
        "app must import the modal factory"
    )
    assert "const modalRegion = document.getElementById(\"modal-region\")" in app_content, (
        "app must locate the modal-region container before constructing the modal"
    )
    assert "const confirmModal = createConfirmModal({ modalRegion })" in app_content, (
        "app must construct the confirm modal against the modal-region"
    )
    assert "confirmAction: confirmModal.confirm" in app_content, (
        "quizEditor must receive the modal-backed async confirm action"
    )


def test_frontend_app_attaches_cancel_regeneration_listener() -> None:
    app_content = APP_JS.read_text(encoding="utf-8")

    assert "cancel-regenerate-question" in app_content, (
        "app must listen for clicks on the cancel-regeneration buttons"
    )
    assert "quizEditor.cancelActiveRegeneration()" in app_content, (
        "the cancel listener must delegate to quizEditor.cancelActiveRegeneration"
    )


def test_frontend_editor_renders_cancel_button_for_active_regeneration() -> None:
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")

    assert 'data-editor-action", "cancel-regenerate-question"' in editor_content, (
        "every editor card must render a cancel-regenerate-question button"
    )
    assert "cancelRegenerateButton.hidden = true" in editor_content, (
        "cancel button must start hidden until a regeneration is in flight"
    )
    assert "cancelButton.hidden = !busy" in editor_content, (
        "setRegenerationActionState must show the cancel button while busy"
    )
    assert "cancelButton.disabled = !busy" in editor_content, (
        "cancel button must be disabled while no regeneration is running"
    )


def test_frontend_editor_aborts_in_flight_regeneration_request() -> None:
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")

    assert "let activeRegenerationController = null" in editor_content, (
        "editor must track the active AbortController in module scope"
    )
    assert "const abortController = new AbortController()" in editor_content, (
        "regenerateQuizQuestion must allocate a new AbortController per request"
    )
    assert "{ signal: abortController.signal }" in editor_content, (
        "regenerate request must forward the abort signal to the API client"
    )
    assert "function cancelActiveRegeneration" in editor_content, (
        "editor must expose cancelActiveRegeneration so external callers can abort"
    )
    assert "activeRegenerationController.abort()" in editor_content, (
        "cancelActiveRegeneration must call abort on the live controller"
    )
    assert "abortController.signal.aborted" in editor_content, (
        "the catch path must distinguish cancellation from generic errors"
    )
    assert "Регенерация отменена пользователем" in editor_content, (
        "cancellation status must be in Russian"
    )
    assert "cancelActiveRegeneration," in editor_content, (
        "createQuizEditor must export cancelActiveRegeneration"
    )


def test_frontend_api_client_forwards_signal_for_question_regeneration() -> None:
    client_content = API_CLIENT_JS.read_text(encoding="utf-8")

    assert "regenerateQuestion(quizId, questionId, payload = {}, { signal } = {})" in client_content, (
        "regenerateQuestion must accept an optional signal so callers can cancel the request"
    )
    assert (
        "json: payload ?? {}," in client_content
        and "signal," in client_content
    ), "the regenerate _request must include the forwarded signal alongside the payload"


def test_frontend_keyboard_shortcut_cancels_active_regeneration() -> None:
    keyboard_content = KEYBOARD_JS.read_text(encoding="utf-8")

    assert "quizEditor.cancelActiveRegeneration" in keyboard_content, (
        "Esc must try to cancel a running question regeneration before falling back to toast dismissal"
    )
    cancel_index = keyboard_content.find("quizEditor.cancelActiveRegeneration")
    dismiss_index = keyboard_content.find("toastController.dismissAllToasts")
    assert cancel_index != -1 and dismiss_index != -1
    assert cancel_index < dismiss_index, (
        "regeneration cancel must be attempted before toast dismissal so an in-flight request is stopped"
    )


def test_frontend_quiz_history_persists_language_for_regeneration() -> None:
    history_content = QUIZ_HISTORY_JS.read_text(encoding="utf-8")

    assert "function findLanguageByQuizId" in history_content, (
        "history must expose a lookup so the editor can recover the original language"
    )
    assert "saveQuizToHistory({ quiz_id, title, language }" in history_content, (
        "saveQuizToHistory must accept the language used to generate the quiz"
    )
    assert "normalized.language = language" in history_content, (
        "history entries must carry language when provided"
    )
    assert "findLanguageByQuizId," in history_content, (
        "createQuizHistory must export findLanguageByQuizId"
    )


def test_frontend_generation_flow_records_language_in_history() -> None:
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert "language: generationBody.language" in generation_content, (
        "successful generation must save the requested language alongside the quiz id"
    )


def test_frontend_editor_uses_recorded_language_for_question_regeneration() -> None:
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert "getLanguageForQuiz," in editor_content, (
        "createQuizEditor must accept a language lookup callback"
    )
    assert "function resolveQuizLanguage" in editor_content, (
        "editor must encapsulate the language fallback in a single helper"
    )
    assert "editorState.loadedQuizLanguage = resolveQuizLanguage" in editor_content, (
        "loadQuizForEditing must remember the resolved language for the open quiz"
    )
    assert 'language: "ru"' not in editor_content, (
        "regeneration request must not hardcode language to ru"
    )
    assert "language," in editor_content, (
        "regeneration request must forward the resolved language variable to the backend"
    )
    assert "loadedQuizLanguage: null" in app_content, (
        "editorState must expose a slot for the resolved language at bootstrap"
    )
    assert "getLanguageForQuiz: quizHistory.findLanguageByQuizId" in app_content, (
        "app must wire history.findLanguageByQuizId into the editor"
    )


def test_frontend_editor_falls_back_to_russian_when_language_is_unknown() -> None:
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")

    assert 'DEFAULT_REGENERATION_LANGUAGE = "ru"' in editor_content, (
        "explicit fallback constant must keep Russian as the safe default for legacy quizzes"
    )
    assert "return DEFAULT_REGENERATION_LANGUAGE" in editor_content


def test_frontend_progress_marks_active_step_with_aria_current() -> None:
    progress_content = PROGRESS_JS.read_text(encoding="utf-8")

    assert 'target.setAttribute("aria-current", "step")' in progress_content, (
        "active stepper item must announce itself as the current step"
    )
    assert 'target.removeAttribute("aria-current")' in progress_content, (
        "non-active stepper items must drop aria-current"
    )


def test_frontend_app_warns_before_unloading_dirty_editor() -> None:
    app_content = APP_JS.read_text(encoding="utf-8")

    assert 'window.addEventListener("beforeunload"' in app_content, (
        "app must register a beforeunload listener to protect unsaved editor changes"
    )
    assert "if (!editorState.isDirty)" in app_content, (
        "beforeunload guard must short-circuit when the editor has no unsaved changes"
    )
    assert "event.returnValue = \"\"" in app_content, (
        "beforeunload guard must populate returnValue so browsers display the native confirmation"
    )


def test_frontend_index_exposes_generation_mode_selector() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="generation-mode"' in index_content, (
        "parameters panel must offer an explicit generation_mode select"
    )
    assert 'name="generation_mode"' in index_content, (
        "select must use the backend-aligned name generation_mode"
    )
    assert "Режим генерации" in index_content, (
        "selector label must be in Russian"
    )
    assert '<option value="direct" selected>' in index_content, (
        "direct must be the default generation mode"
    )
    assert '<option value="rag">' in index_content, (
        "rag must be selectable"
    )
    assert "Авто (RAG для длинных документов)" in index_content, (
        "direct option copy must explain the auto-promotion behaviour in Russian"
    )
    assert "RAG — всегда" in index_content, (
        "rag option copy must explain the explicit retrieval mode in Russian"
    )


def test_frontend_index_surfaces_resolved_generation_mode_in_result() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="quiz-generation-mode"' in index_content, (
        "result panel must expose a dedicated slot for the resolved generation mode"
    )
    assert "<dt>Режим</dt>" in index_content, (
        "result panel must label the slot in Russian"
    )


def test_frontend_generation_flow_forwards_requested_generation_mode() -> None:
    content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert 'SUPPORTED_REQUEST_MODES = Object.freeze(["direct", "rag"])' in content, (
        "frontend must whitelist the modes it can send to the backend"
    )
    assert 'formData.get("generation_mode")' in content, (
        "generation flow must read the user-selected mode instead of hardcoding it"
    )
    assert "SUPPORTED_REQUEST_MODES.includes(requestedMode)" in content, (
        "unsupported modes must fall back to the default before being sent to the backend"
    )
    assert "const generationMode = DEFAULT_GENERATION_MODE;" not in content, (
        "generation_mode must no longer be hardcoded to the default"
    )


def test_frontend_generation_flow_forwards_checked_question_types() -> None:
    content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert 'formData.getAll("quiz_types")' in content
    assert "payload.quiz_types = quizTypes" in content
    assert "payload.quiz_type = quizTypes[0]" in content
    assert "Выберите хотя бы один тип вопросов." in content


def test_frontend_quiz_renderer_describes_generation_mode_from_prompt_version() -> None:
    content = QUIZ_RENDERER_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert "export function describeGenerationMode" in content, (
        "renderer must expose a deterministic prompt_version -> mode label mapping"
    )
    assert 'rag: "RAG (поиск по документу)"' in content, (
        "rag prompt versions must surface a Russian RAG label"
    )
    assert 'direct: "Прямая"' in content, (
        "direct prompt versions must surface a Russian direct label"
    )
    assert 'single_question_regen: "Регенерация одного вопроса"' in content, (
        "single-question regeneration must be labelled in Russian"
    )
    assert 'describeGenerationMode(generationPayload.prompt_version)' in content, (
        "renderQuizResult must populate the mode field via the helper"
    )
    assert 'setTextContent("quiz-generation-mode"' in content, (
        "renderer must write into the quiz-generation-mode slot"
    )
    assert 'setTextContent("quiz-generation-mode", "Ещё нет результата")' in content, (
        "clearQuizResult must reset the generation mode label between runs"
    )
    assert "describeGenerationMode" not in app_content, (
        "describeGenerationMode is a renderer concern and should not leak into app.js"
    )


def test_frontend_p3_visual_tokens() -> None:
    tokens = (FRONTEND_DIR / "tokens.css").read_text(encoding="utf-8")
    layout = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")
    forms = FORMS_CSS.read_text(encoding="utf-8")

    assert "--radius-xs: 6px" in tokens
    assert "--radius-sm: 10px" in tokens
    assert "--radius-md: 14px" in tokens
    assert "--radius-lg: 20px" in tokens

    assert "0 12px 36px rgba(98, 69, 255, 0.18)" in tokens
    assert "0 12px 36px rgba(152, 133, 255, 0.24)" in tokens

    assert "--muted: #4a4468" in tokens
    assert "--muted: #c0bacf" in tokens

    assert "blur(10px)" in layout
    assert "blur(8px)" in layout
    assert "font-size: 1.1rem" in layout
    assert "font-size: 0.88rem" in layout

    assert "font-size: 0.8rem" in forms
