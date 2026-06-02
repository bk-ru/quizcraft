from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler
from http.server import ThreadingHTTPServer
from pathlib import Path
import re
import shutil
import subprocess
from threading import Thread
from urllib.request import urlopen

import pytest


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
QUESTION_SHAPE_JS = FRONTEND_DIR / "question-shape.js"
UNDO_STACK_JS = FRONTEND_DIR / "undo-stack.js"
PREVIEW_MODE_JS = FRONTEND_DIR / "preview-mode.js"
QUIZ_HISTORY_JS = FRONTEND_DIR / "quiz-history.js"
SIDEBAR_JS = FRONTEND_DIR / "sidebar.js"
WORKSPACE_JS = FRONTEND_DIR / "workspace.js"
GENERATION_FLOW_JS = FRONTEND_DIR / "generation-flow.js"
GENERATION_SETTINGS_JS = FRONTEND_DIR / "generation-settings.js"
KEYBOARD_JS = FRONTEND_DIR / "keyboard.js"
COPY_JS = FRONTEND_DIR / "copy.js"
PROGRESS_JS = FRONTEND_DIR / "progress.js"
STAGE_FLOW_JS = FRONTEND_DIR / "stage-flow.js"
THEME_JS = FRONTEND_DIR / "theme.js"
TOAST_JS = FRONTEND_DIR / "toast.js"
DOWNLOAD_JS = FRONTEND_DIR / "download.js"
TEXT_EXPORT_JS = FRONTEND_DIR / "text-export.js"
EXPORT_MODAL_JS = FRONTEND_DIR / "export-modal.js"
FRONTEND_JS_MODULES = (
    APP_JS,
    VALIDATION_ERRORS_JS,
    QUIZ_RENDERER_JS,
    QUIZ_EDITOR_JS,
    QUESTION_SHAPE_JS,
    UNDO_STACK_JS,
    PREVIEW_MODE_JS,
    QUIZ_HISTORY_JS,
    SIDEBAR_JS,
    WORKSPACE_JS,
    GENERATION_FLOW_JS,
    GENERATION_SETTINGS_JS,
    KEYBOARD_JS,
    COPY_JS,
    PROGRESS_JS,
    STAGE_FLOW_JS,
    THEME_JS,
    TOAST_JS,
    DOWNLOAD_JS,
    TEXT_EXPORT_JS,
    EXPORT_MODAL_JS,
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


def test_frontend_index_exposes_single_compact_workspace_shell() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")
    sidebar = content.split('<aside id="workspace-sidebar" class="workspace-sidebar"', maxsplit=1)[1].split("</aside>", maxsplit=1)[0]

    assert 'class="compact-workspace"' in content
    assert content.count('class="compact-workspace"') == 1
    assert 'class="workspace-sidebar"' in content
    assert 'aria-label="QuizCraft"' in sidebar
    assert 'id="workspace-workbench"' in content
    assert content.count("<main") == 1
    assert "compact-workspace-enabled" not in content
    assert "data-compact-workspace" not in content
    assert 'id="generation-progress"' in content
    assert 'id="generation-result"' in content
    assert 'id="modal-region"' in content
    assert 'id="toast-region"' in content
    assert 'id="document-drop-overlay"' in content


def test_frontend_shell_uses_offline_compact_workspace_tokens() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    tokens = (FRONTEND_DIR / "tokens.css").read_text(encoding="utf-8")
    layout = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")

    assert "fonts.googleapis.com" not in index_content
    assert '--font-sans: "Geist", system-ui, -apple-system, "Segoe UI", sans-serif;' in tokens
    assert '--font-display: "Fraunces", Georgia, serif;' in tokens
    assert '--font-mono: "JetBrains Mono", Consolas, monospace;' in tokens
    assert "--sidebar-width: 264px;" in tokens
    assert ".compact-workspace .workspace-sidebar" in layout
    assert ".compact-workspace .workspace-workbench" in layout


def test_frontend_index_exposes_working_sidebar_shell() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="workspace-sidebar"' in content
    assert 'id="sidebar-toggle"' in content
    assert 'id="sidebar-new-quiz"' in content
    assert 'id="sidebar-history-list"' in content
    assert 'id="sidebar-status-cell"' in content
    assert 'id="theme-toggle"' in content
    assert content.count("История") == 1
    assert "Новый квиз" in content
    assert 'id="workspace-status-modal"' in content
    assert 'data-workspace-modal="status"' in content
    assert 'data-workspace-modal-close' in content


def test_frontend_sidebar_module_owns_sidebar_dom_without_backend_calls() -> None:
    content = SIDEBAR_JS.read_text(encoding="utf-8")

    assert "export function createSidebarController" in content
    assert "onNewQuiz" in content
    assert "onSelectQuiz" in content
    assert "onOpenStatus" in content
    assert "onToggleTheme" in content
    assert "historyStore.loadQuizHistory()" in content
    assert "historyStore.subscribe(renderHistory)" in content
    assert "client." not in content
    assert "fetch(" not in content


def test_frontend_workspace_module_owns_states_and_modals_without_quiz_payload() -> None:
    content = WORKSPACE_JS.read_text(encoding="utf-8")

    assert "export function createWorkspaceController" in content
    assert 'setup: "setup"' in content
    assert 'generating: "generation"' in content
    assert 'result: "result"' in content
    assert "stageFlow.activateStage" in content
    assert "openModal" in content
    assert "closeModal" in content
    assert 'bodyElement.classList.add("workspace-modal-open")' in content
    assert 'bodyElement.classList.remove("workspace-modal-open")' in content
    assert "quiz" not in content.lower()


def test_frontend_app_wires_sidebar_history_and_workspace_navigation() -> None:
    content = APP_JS.read_text(encoding="utf-8")

    assert 'import { createSidebarController } from "./sidebar.js"' in content
    assert 'import { createWorkspaceController } from "./workspace.js"' in content
    assert "const workspaceController = createWorkspaceController" in content
    assert "const sidebarController = createSidebarController" in content
    assert "historyStore: quizHistory" in content
    assert "onNewQuiz: startNewQuiz" in content
    assert "onSelectQuiz: openQuizFromHistory" in content
    assert 'onOpenStatus: () => workspaceController.openModal("status")' in content
    assert "onToggleTheme: themeController.cycleTheme" in content
    assert "const payload = await client.getQuiz(quizId)" in content
    assert "quizIdInput.value = normalizedQuizId" in content
    assert "quizRenderer.renderQuizResult" in content
    assert 'workspaceController.activateState("setup"' in content


def test_frontend_quiz_history_notifies_sidebar_subscribers() -> None:
    content = QUIZ_HISTORY_JS.read_text(encoding="utf-8")

    assert "const subscribers = new Set()" in content
    assert "function subscribe" in content
    assert "subscribers.add(callback)" in content
    assert "notifySubscribers()" in content
    assert "subscribe," in content


def test_frontend_index_exposes_russian_result_view_shell() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert '<html lang="ru">' in content
    assert '<meta charset="utf-8"' in content.lower()
    assert "QuizCraft" in content
    assert "<title>QuizCraft</title>" in content
    assert "QuizCraft · Генерация квизов" not in content
    assert "Текстовое содержание" in content
    assert "Параметры генерации" in content
    assert "Сгенерировать квиз" in content
    assert "Результат генерации" not in content
    assert 'class="result-head"' in content
    assert "Квиз появится здесь после успешной генерации." in content
    assert 'id="generation-result"' in content
    assert 'class="panel panel-result result workflow-stage"' in content
    assert 'class="result-head"' in content
    assert 'id="quiz-title" class="result-title"' in content
    for pill_id in ("quiz-id-pill", "quiz-version-pill", "quiz-count-pill", "quiz-edited-pill"):
        assert f'id="{pill_id}"' in content
    assert 'class="result-overview-panel"' in content
    assert 'class="form-actions inline-editor-add-actions result-foot"' in content
    assert 'class="result-foot-spacer"' in content
    assert 'id="result-back-button"' in content
    assert 'id="add-question-button"' in content
    assert 'id="add-question-type"' in content
    assert 'class="field inline-editor-add-type"' in content


def test_frontend_index_exposes_supported_question_type_labels() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert "Типы вопросов:" in content
    assert 'data-question-type-group' in content
    assert 'class="question-type-label"' in content
    assert 'class="required-marker" aria-hidden="true">*</span>' in content
    assert 'class="question-type-list"' in content
    assert 'class="question-type-option question-type-chip"' in content
    assert "checkbox-grid" not in content
    assert "checkbox-option" not in content
    assert "quiz-type-hint" not in content
    styles = FORMS_CSS.read_text(encoding="utf-8")
    assert "color-scheme: inherit;" in styles
    assert ".field input[type=\"checkbox\"]" in styles
    assert "min-height: 15px;" in styles
    assert "padding: 0;" in styles
    assert "appearance: none;" in styles
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
    assert "выпадающем списке" in content
    assert "Название или ID квиза" in content
    assert "Загрузить" in content
    assert "Сохранить" in content
    assert 'id="quiz-editor-loader"' in content
    assert 'id="quiz-id-input"' in content
    assert 'id="quiz-editor-fields"' in content
    assert 'id="quiz-editor-status"' in content
    assert 'id="save-quiz-button"' in content
    assert '<details id="quiz-editor" class="panel panel-editor editor-disclosure workflow-stage"' in content
    assert 'data-workflow-stage="edit"' in content
    assert 'id="editor-export-actions"' not in content
    assert 'id="editor-export-json-button"' not in content
    assert 'id="editor-export-split"' not in content


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
    assert "/health/provider" in content
    assert "/health/lm-studio" not in content
    assert "/providers/lm-studio/connection" in content
    assert "getLMStudioConnection" in content
    assert "putLMStudioConnection" in content
    assert "getGenerationEvents" in content
    assert "cancelGeneration" in content
    assert "/generation/runs/" in content
    assert "/export/formats" in content
    assert "/documents" in content
    assert "/quizzes/" in content
    assert "/questions/" in content
    assert "/regenerate" in content


def test_api_client_uses_role_based_timeouts() -> None:
    content = API_CLIENT_JS.read_text(encoding="utf-8")

    assert "DEFAULT_TIMEOUTS" in content
    assert "health: 15000" in content
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
    assert "health: 15000" in content
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
    assert "\u041a\u0432\u0438\u0437 \u0433\u043e\u0442\u043e\u0432 \u043a \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044e" in content
    assert "Квиз появится здесь после успешной генерации." in content
    assert "Изменения пока не сохранены." in content
    assert "Изменения сохранены." in content
    assert "Исправьте ошибки и повторите сохранение." in content


def test_frontend_editor_load_renders_saved_quiz_result_actions() -> None:
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")
    load_section = editor_content.split("async function loadQuizForEditing", 1)[1].split(
        "async function regenerateQuizQuestion",
        1,
    )[0]

    assert "renderQuizResult({" in load_section
    assert "...payload," in load_section
    assert "quiz_id: payload.quiz_id ?? quiz.quiz_id ?? quizId," in load_section
    assert "quiz," in load_section


def test_frontend_wires_mockup_export_action_to_capability_driven_modal() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    download_content = DOWNLOAD_JS.read_text(encoding="utf-8")
    export_modal_content = EXPORT_MODAL_JS.read_text(encoding="utf-8")

    assert 'id="export-json-button"' in index_content
    assert 'id="export-split-toggle"' not in index_content
    assert 'id="export-split-menu"' not in index_content
    assert 'class="split-button result-export-split"' not in index_content
    assert 'id="editor-export-split"' not in index_content
    assert "Экспорт" in index_content

    assert "supportedExportFormats" in app_content
    assert "getExportFormats" in app_content
    assert "parseSupportedExportFormats" in app_content
    assert "loadExportFormats" in app_content
    assert "format === \"json\" || editorState.supportedExportFormats.has(format)" in app_content
    assert "serverExporter: quizExporter" in app_content
    assert 'exportJsonButton?.addEventListener("click", exportModal.open)' in app_content
    assert "exportSplitToggle" not in app_content
    assert "exportSplitMenu" not in app_content

    assert 'docx: { label: "DOCX"' in export_modal_content
    assert 'pptx: { label: "PPTX"' in export_modal_content

    assert "createQuizExporter" in download_content
    assert "exportQuizAsDocx" in download_content
    assert "exportQuizAsPptx" in download_content
    assert "/export/${exportFormat}" in download_content
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in download_content
    assert "application/vnd.openxmlformats-officedocument.presentationml.presentation" in download_content
    assert "Не удалось скачать ${describeExportFormat(format)}" in download_content
    assert "function describeExportFormat" in download_content
    assert "${formatConfig.label}-файл квиза скачан." in download_content


def test_frontend_export_modal_serializes_text_and_saves_dirty_quiz_before_download() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    export_modal_content = EXPORT_MODAL_JS.read_text(encoding="utf-8")
    text_export_content = TEXT_EXPORT_JS.read_text(encoding="utf-8")
    layout_css = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")
    forms_css = FORMS_CSS.read_text(encoding="utf-8")
    responsive_css = (FRONTEND_DIR / "responsive.css").read_text(encoding="utf-8")

    assert 'data-export-format="json"' in index_content
    assert 'docx: { label: "DOCX"' in export_modal_content
    assert 'pptx: { label: "PPTX"' in export_modal_content
    assert 'import { createExportModal } from "./export-modal.js";' in app_content
    assert "createExportModal({" in app_content
    assert "exportModal.open" in app_content
    for serializer in (
        "prepareTextExportQuiz",
        "serializeQuizAsJson",
        "serializeQuizAsMarkdown",
        "serializeQuizAsCsv",
    ):
        assert f"export function {serializer}" in text_export_content
    assert "correct_option_index" in text_export_content
    assert "warning_count" in text_export_content
    assert 'question.question_type === "matching"' in text_export_content
    assert "client.getExportFormats()" in export_modal_content
    assert "validateEditableQuiz" in export_modal_content
    assert "editorState.isDirty" in export_modal_content
    assert "await saveQuiz()" in export_modal_content
    assert "serverExporter.exportQuiz(format)" in export_modal_content
    assert "triggerFileDownload" in export_modal_content
    assert 'dialog.addEventListener("cancel"' in export_modal_content
    assert ".target === dialog" in export_modal_content
    assert "restoreFocus" in export_modal_content
    assert ".quiz-export-modal" in layout_css
    assert ".export-option" in forms_css
    assert ".quiz-export-modal" in responsive_css


def test_frontend_text_export_runtime_preserves_cyrillic_and_answer_invariants() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed")
    script = r'''
import {
  prepareTextExportQuiz,
  serializeQuizAsJson,
  serializeQuizAsMarkdown,
  serializeQuizAsCsv,
} from "./frontend/text-export.js";

const quiz = {
  quiz_id: "quiz-ru",
  title: "\u0422\u0435\u0441\u0442 \u043f\u043e \u0438\u0441\u0442\u043e\u0440\u0438\u0438",
  questions: [
    {
      question_type: "single_choice",
      prompt: "\u0421\u0442\u043e\u043b\u0438\u0446\u0430 \u0420\u043e\u0441\u0441\u0438\u0438?",
      options: [
        { text: "\u041c\u043e\u0441\u043a\u0432\u0430" },
        { text: "\u041a\u0430\u0437\u0430\u043d\u044c" },
        { text: "\u041e\u043c\u0441\u043a" },
        { text: "\u0422\u0443\u043b\u0430" },
      ],
      correct_option_index: 0,
      explanation: { text: "\u041c\u043e\u0441\u043a\u0432\u0430 \u2014 \u0441\u0442\u043e\u043b\u0438\u0446\u0430." },
    },
    {
      question_type: "true_false",
      prompt: "\u0412\u043e\u043b\u0433\u0430 \u2014 \u0440\u0435\u043a\u0430.",
      options: [{ text: "\u0412\u0435\u0440\u043d\u043e" }, { text: "\u041d\u0435\u0432\u0435\u0440\u043d\u043e" }],
      correct_option_index: 0,
    },
    {
      question_type: "matching",
      prompt: "\u0421\u043e\u043f\u043e\u0441\u0442\u0430\u0432\u044c\u0442\u0435 \u0433\u043e\u0440\u043e\u0434\u0430 \u0438 \u0440\u0435\u043a\u0438.",
      matching_pairs: [
        { left: "\u041c\u043e\u0441\u043a\u0432\u0430", right: "\u041c\u043e\u0441\u043a\u0432\u0430-\u0440\u0435\u043a\u0430" },
        { left: "\u041a\u0430\u0437\u0430\u043d\u044c", right: "\u0412\u043e\u043b\u0433\u0430" },
        { left: "\u041e\u043c\u0441\u043a", right: "\u0418\u0440\u0442\u044b\u0448" },
        { left: "\u0422\u0443\u043b\u0430", right: "\u0423\u043f\u0430" },
      ],
    },
  ],
};
const before = JSON.stringify(quiz);
const prepared = prepareTextExportQuiz(quiz, { shuffleOptions: true, random: () => 0 });
if (JSON.stringify(quiz) !== before) throw new Error("source quiz mutated");
if (prepared.questions[0].options[prepared.questions[0].correct_option_index].text !== "\u041c\u043e\u0441\u043a\u0432\u0430") throw new Error("single-choice answer desynchronized");
if (prepared.questions[1].options.map((option) => option.text).join("|") !== "\u0412\u0435\u0440\u043d\u043e|\u041d\u0435\u0432\u0435\u0440\u043d\u043e") throw new Error("true-false options shuffled");
const json = serializeQuizAsJson(quiz, { includeAnswers: false, includeExplanations: false });
if (json.includes("correct_option_index") || json.includes("explanation")) throw new Error("excluded JSON fields retained");
const markdown = serializeQuizAsMarkdown(quiz, { includeAnswers: true });
if (!markdown.includes("\u0422\u0435\u0441\u0442 \u043f\u043e \u0438\u0441\u0442\u043e\u0440\u0438\u0438") || !markdown.includes("\u041f\u043e\u044f\u0441\u043d\u0435\u043d\u0438\u0435")) throw new Error("Cyrillic lost in Markdown");
const csv = serializeQuizAsCsv(quiz, { includeAnswers: true });
if (csv.warning_count !== 1 || csv.content.includes("\u0421\u043e\u043f\u043e\u0441\u0442\u0430\u0432\u044c\u0442\u0435") || !csv.content.includes("\u0421\u0442\u043e\u043b\u0438\u0446\u0430 \u0420\u043e\u0441\u0441\u0438\u0438")) throw new Error("CSV export mismatch");
console.log("text export runtime checks passed");
'''
    completed = subprocess.run(
        [node, "--input-type=module"],
        input=script,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "text export runtime checks passed"


def test_frontend_status_modal_exposes_generation_mode() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")
    styles = (FRONTEND_DIR / "forms.css").read_text(encoding="utf-8")

    assert 'id="advanced-params"' not in content
    assert 'class="form-advanced"' not in content
    assert 'id="generation-model"' in content
    assert 'id="generation-temperature"' in content
    assert 'name="temperature"' in content
    assert "\u0410\u0432\u0442\u043e (RAG \u0434\u043b\u044f \u0434\u043b\u0438\u043d\u043d\u044b\u0445 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u043e\u0432)" in content
    assert "RAG \u2014 \u0432\u0441\u0435\u0433\u0434\u0430" in content
    assert ".settings-modal-grid" in styles
    assert ".settings-form-grid" in styles


def test_frontend_exposes_manual_lm_studio_connection_controls() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert 'id="lm-studio-host"' in index_content
    assert 'id="lm-studio-port"' in index_content
    assert 'id="apply-lm-studio-connection"' in index_content
    assert 'id="lm-studio-connection-status"' in index_content
    assert "IP или host устройства" in index_content
    assert "IP или host ноутбука" not in index_content
    assert "Порт LM Studio" in index_content
    assert "function loadLMStudioConnectionSettings" in app_content
    assert "function applyLMStudioConnectionSettings" in app_content
    assert "client.getLMStudioConnection" in app_content
    assert "client.putLMStudioConnection" in app_content
    assert "localStorage" in app_content
    assert 'applyLMStudioConnectionButton?.addEventListener("click"' in app_content


def test_frontend_setup_uses_compact_main_controls() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="question-count-range"' in content
    assert 'id="question-count" name="question_count" type="number" min="3" max="50"' in content
    assert 'id="question-count-range" type="range" min="3" max="50"' in content
    assert '<option value="easy">Легко</option>' in content
    assert '<option value="medium" selected>Средне</option>' in content
    assert '<option value="hard">Сложно</option>' in content
    assert 'id="generation-estimate"' in content
    assert 'id="advanced-params"' not in content


def test_frontend_status_modal_hosts_real_connection_controls() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")
    modal = content.split('id="workspace-status-modal"', maxsplit=1)[1].split("</section>", maxsplit=1)[0]

    for expected in (
        'data-status-surface="backend"',
        'data-status-surface="provider"',
        'id="retry-backend-button"',
        'id="retry-provider-button"',
        'id="generation-mode"',
        'id="generation-temperature"',
        'id="generation-model"',
        'id="lm-studio-connection-section"',
        'id="lm-studio-host"',
        'id="lm-studio-port"',
        'id="apply-lm-studio-connection"',
    ):
        assert expected in modal
    assert "Сменить провайдера" not in content


def test_frontend_app_syncs_question_count_estimate_and_lm_studio_visibility() -> None:
    content = APP_JS.read_text(encoding="utf-8")

    assert 'document.getElementById("question-count-range")' in content
    assert 'document.getElementById("question-count")' in content
    assert "function syncQuestionCount" in content
    assert 'questionCountInput?.addEventListener("change"' in content
    assert 'questionCountInput?.addEventListener("input"' not in content
    assert 'document.getElementById("generation-estimate")' in content
    assert "function updateGenerationEstimate" in content
    assert 'document.getElementById("lm-studio-connection-section")' in content
    assert "function updateLMStudioConnectionVisibility" in content
    assert 'providerKey === "lm_studio"' in content
    assert "updateProviderModelStatus(providerHealth.default_model, providerHealth.available_models)" in content
    assert content.count("updateProviderModelStatus();") >= 2


def test_frontend_forms_define_compact_pills_and_viewport_safe_tooltips() -> None:
    styles = FORMS_CSS.read_text(encoding="utf-8")

    assert ".question-type-option:has(input:checked)" in styles
    assert ".field input[type=\"checkbox\"]:checked" in styles
    assert "border-radius: 50%;" in styles
    assert "calc(100vw - 32px)" in styles
    assert ".settings-modal-grid" in styles
    assert styles.index(".field-tooltip:hover::before") < styles.index(".field-tooltip--edge:hover::before")


def test_frontend_gen_timing_estimates_total_duration_for_setup() -> None:
    content = (FRONTEND_DIR / "gen-timing.js").read_text(encoding="utf-8")

    assert "function estimateTotalMs" in content
    assert "estimateTotalMs }" in content


def test_frontend_short_text_advice_respects_compact_minimum_count() -> None:
    content = (FRONTEND_DIR / "generation-flow.js").read_text(encoding="utf-8")

    assert "{ maxChars: 300, maxQuestions: 3 }" in content
    assert "{ maxChars: 300, maxQuestions: 2 }" not in content
    assert "questionCount < 3 || questionCount > 50" in content


def test_frontend_mobile_status_modal_stacks_status_rows() -> None:
    content = (FRONTEND_DIR / "responsive.css").read_text(encoding="utf-8")

    assert ".settings-status-grid" in content
    assert "grid-template-columns: 1fr;" in content


def test_frontend_mobile_result_visual_parity_breakpoints() -> None:
    content = (FRONTEND_DIR / "responsive.css").read_text(encoding="utf-8")

    assert ".compact-workspace .result-head" in content
    assert ".compact-workspace .result-head-actions" in content
    assert ".compact-workspace .result-foot" in content
    assert ".compact-workspace .q-actions" in content
    assert ".compact-workspace .q-opt" in content
    assert ".compact-workspace .q-expl-head" in content
    assert ".compact-workspace .q-card" in content
    assert ".compact-workspace .q-head" in content
    assert ".compact-workspace .q-num" in content


def test_frontend_modal_controls_preserve_form_busy_state_and_shortcut() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    keyboard_content = KEYBOARD_JS.read_text(encoding="utf-8")

    for control_id in ("lm-studio-host", "lm-studio-port", "apply-lm-studio-connection"):
        control = index_content.split(f'id="{control_id}"', maxsplit=1)[1].split(">", maxsplit=1)[0]
        assert 'form="generation-form"' in control
    assert "target.form !== generationForm" in keyboard_content


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
    assert 'cancelRegenerateButton.title = "\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c \u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u044e"' in editor_content
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


def test_frontend_generation_renders_inline_editor_in_result_screen() -> None:
    content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    index_content = INDEX_HTML.read_text(encoding="utf-8")

    assert "async function submitGeneration" in content
    assert "renderQuizResult(generationPayload)" in content
    assert "presentQuizInline(generatedQuiz" in content
    assert "presentQuizInline: quizEditor.presentQuizInline" in app_content
    assert "focusResultView()" in content
    assert 'id="generation-result"' in index_content and 'tabindex="-1"' in index_content
    assert "function focusResultView" in app_content
    assert "resultPanel.scrollIntoView" in app_content
    assert "resultPanel.focus" in app_content
    assert "openEditorForCurrentQuiz" not in app_content, (
        "legacy edit shortcut must be removed once the inline editor is the canonical view"
    )


def test_frontend_marks_provider_unready_statuses_as_critical() -> None:
    app_content = APP_JS.read_text(encoding="utf-8")

    assert re.search(r"unavailable\s*:\s*\"bad\"", app_content), (
        "statusMap must map provider unavailable to the critical bad tone"
    )
    assert re.search(r"disabled\s*:\s*\"bad\"", app_content), (
        "statusMap must map provider disabled to the critical bad tone"
    )
    assert re.search(r"bad\s*:\s*\"bad\"", app_content), (
        "statusMap must preserve backend bad statuses as critical"
    )
    assert "PROVIDER_UNAVAILABLE_INSTRUCTION" in app_content
    assert "LM_STUDIO_UNAVAILABLE_INSTRUCTION" not in app_content
    assert "isProviderReadyStatus" in app_content
    assert "formatProviderName" in app_content


def test_frontend_provider_available_status_is_plain_language() -> None:
    app_content = APP_JS.read_text(encoding="utf-8")

    assert 'const PROVIDER_AVAILABLE_TEXT = "Доступен"' in app_content
    assert "Подключение к программе с ИИ-моделью проверено" in app_content
    assert 'setStatus(\n        "provider",\n        PROVIDER_AVAILABLE_TEXT,' in app_content
    assert '`LM Studio \u00b7 ${connection.message}`' not in app_content
    assert '`${providerName}`' not in app_content


def test_frontend_status_tooltips_and_retry_buttons_are_wired() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    layout_content = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")

    assert 'data-status-label="Сервер"' in index_content
    assert 'data-status-label="Провайдер"' in index_content
    assert 'data-status-tooltip="Сервер · Проверка…"' in index_content
    assert 'data-status-tooltip="Провайдер · Проверка…"' in index_content
    assert 'tabindex="0"' in index_content
    assert 'id="retry-backend-button"' in index_content
    assert 'id="retry-provider-button"' in index_content
    assert 'aria-label="Повторно проверить подключение к серверу"' in index_content
    assert 'aria-label="Повторно проверить активный провайдер"' in index_content
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
    assert "backend и провайдер" in app_content
    assert "Провайдер недоступен" in app_content


def test_frontend_provider_unavailable_help_includes_reason_and_recovery_steps() -> None:
    app_content = APP_JS.read_text(encoding="utf-8")
    layout_content = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")

    assert "function buildProviderUnavailableMessage" in app_content
    assert "function buildBackendUnavailableMessage" in app_content
    assert "Причина:" in app_content
    assert "Что сделать:" in app_content
    assert "Откройте LM Studio" in app_content
    assert "Запустите Local Server" in app_content
    assert "Проверьте LM_STUDIO_BASE_URL в .env" in app_content
    assert 'Нажмите "Проверить снова"' in app_content
    assert "Запустите backend командой .\\\\run-backend.ps1" in app_content
    assert "white-space: pre-line" in layout_content


def test_frontend_generation_button_is_visually_blocked_with_reason_when_services_fail() -> None:
    app_content = APP_JS.read_text(encoding="utf-8")
    forms_content = FORMS_CSS.read_text(encoding="utf-8")

    assert "function updateGenerationSubmitAvailability" in app_content
    assert 'submitButton.setAttribute("aria-disabled", "true")' in app_content
    assert "submitButton.dataset.disabledReason = readiness.message" in app_content
    assert "submitButton.title = readiness.message" in app_content
    assert "function showSubmitUnavailableReason" in app_content
    assert 'submitButton?.addEventListener("pointerenter", showSubmitUnavailableReason)' in app_content
    assert 'submitButton?.addEventListener("focus", showSubmitUnavailableReason)' in app_content
    assert "updateGenerationSubmitAvailability()" in app_content
    assert '.primary-action[aria-disabled="true"]' in forms_content
    assert "cursor: not-allowed" in forms_content


def test_frontend_backend_available_status_does_not_show_default_model() -> None:
    app_content = APP_JS.read_text(encoding="utf-8")

    assert "`Доступен · модель ${backendHealth.default_model}`" not in app_content
    assert '"backend",\n      "Доступен",' in app_content


def test_frontend_generation_flow_blocks_submit_when_services_are_unavailable() -> None:
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert "getGenerationReadiness" in generation_content
    assert "const readiness = getGenerationReadiness()" in generation_content
    submit_index = generation_content.find("async function submitGeneration")
    readiness_index = generation_content.find("const readiness = getGenerationReadiness()", submit_index)
    file_index = generation_content.find("const file = resolveInputFile()", submit_index)
    upload_index = generation_content.find("uploadPayload = await client.uploadDocument")
    assert readiness_index != -1 and file_index != -1 and upload_index != -1
    assert readiness_index < file_index < upload_index, (
        "connection readiness must be checked before file validation and network calls"
    )
    assert "if (!readiness.ready)" in generation_content
    assert "return;" in generation_content[readiness_index:upload_index]
    assert "createGenerationReadinessChecker" in app_content
    assert "generationConnectionState" in app_content


def test_frontend_hides_generation_technical_identifiers() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert "\u0414\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0430 \u0438 \u0442\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u0438\u0435 ID" not in content
    assert 'id="last-document-id"' not in content
    assert 'id="last-quiz-id"' not in content
    assert 'id="last-request-id"' not in content
    assert "\u0422\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u0434\u0435\u0442\u0430\u043b\u0438 \u043a\u0432\u0438\u0437\u0430" not in content
    assert '<details class="inline-details" open' not in content

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

    assert "Модель не смогла корректно оформить вопрос на соответствие" in content
    assert "недостаточно информации в тексте" not in content


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
    for data_step in ("upload", "parse", "generate", "persist"):
        assert f'data-step="{data_step}"' in content, (
            f"progress panel must declare the {data_step} pseudo-step"
        )
    for russian_label in (
        "Загружаем документ",
        "Извлекаем текст",
        "Генерируем",
        "Сохраняем квиз",
    ):
        assert russian_label in content, (
            f"progress panel must include Russian label: {russian_label}"
        )
    assert 'id="generation-live-journal"' in content
    assert "\u0416\u0443\u0440\u043d\u0430\u043b \u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u0438" in content
    assert 'id="generation-live-journal-count"' in content


def test_frontend_app_drives_generation_progress_state() -> None:
    progress_content = PROGRESS_JS.read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    for helper in (
        "startGenerationProgress",
        "advanceGenerationProgress",
        "completeGenerationProgressWithBackendEvidence",
        "failGenerationProgress",
        "cancelGenerationProgress",
    ):
        assert f"function {helper}" in progress_content, (
            f"progress module must define the {helper} progress helper"
        )

    assert "startGenerationProgress()" in generation_content
    assert 'advanceGenerationProgress("upload", "parse")' in generation_content
    assert "waitForProgressVisibility" not in generation_content
    assert "completeGenerationProgressWithBackendEvidence(generationPayload)" in generation_content
    assert "failGenerationProgress(failedStep)" in generation_content
    assert "startGenerationEventPolling(generationRequestId)" in generation_content
    assert "stopGenerationEventPolling" in generation_content
    assert "client.getGenerationEvents" in generation_content
    assert "generateRequestId" in generation_content
    assert "LIVE_JOURNAL_ENTRY_STAGGER_MS" in generation_content
    assert "animationDelay" in generation_content
    assert "liveJournalElement.childElementCount * LIVE_JOURNAL_ENTRY_STAGGER_MS" in generation_content
    assert "last-filename" not in generation_content
    assert "Вставленный текст" not in generation_content


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
    assert 'persist: "persist"' in progress_content
    assert "applyBackendGenerationStatusEvidence" in progress_content
    assert "completeGenerationProgressWithBackendEvidence" in progress_content
    assert "generation_status" in progress_content
    assert "pipeline_status" in progress_content
    assert "pipeline_events" in progress_content
    assert "completeGenerationProgressWithBackendEvidence: progressController.completeGenerationProgressWithBackendEvidence" in app_content
    assert "Генерируем" in index_content
    assert "Сохраняем квиз" in index_content


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
    assert ".live-journal" in content
    assert ".live-journal-entry" in content
    assert "live-journal-entry-in" in content
    assert ".generation-progress-orbit" in content
    assert ".generation-progress-fill" in content
    assert "generation-orbit-spin" in content
    assert "@media (prefers-reduced-motion: reduce)" in content


def test_frontend_progress_uses_honest_skeletons_until_final_quiz() -> None:
    progress_content = PROGRESS_JS.read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert "function ensureGenerationSkeletons" in progress_content
    assert "function setGenerationSkeletonsVisible" in progress_content
    assert "data-generation-skeletons" in progress_content
    assert "generation-skeleton-card" in progress_content
    assert "setGenerationSkeletonsVisible(true)" in progress_content
    assert progress_content.count("setGenerationSkeletonsVisible(false)") >= 2
    assert 'failGenerationProgress("persist")' in generation_content
    assert "Вопрос 1" not in progress_content
    assert "question-card" not in progress_content


def test_frontend_styles_compact_generation_skeletons() -> None:
    feedback_content = (FRONTEND_DIR / "feedback.css").read_text(encoding="utf-8")
    layout_content = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")

    assert ".generation-skeleton-stream" in feedback_content
    assert ".generation-skeleton-card" in feedback_content
    assert ".generation-skeleton-bar" in feedback_content
    assert "generation-skeleton-shimmer" in feedback_content
    assert ".compact-workspace .panel-status" in layout_content


def test_frontend_progress_clears_stale_autohide_before_retry() -> None:
    content = PROGRESS_JS.read_text(encoding="utf-8")

    assert "let progressAutoHideTimeoutId = null" in content
    assert "function clearProgressAutoHide" in content
    assert "clearProgressAutoHide()" in content
    assert "progressAutoHideTimeoutId = windowRef.setTimeout" in content


def test_frontend_generation_polling_ignores_terminal_late_events() -> None:
    content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert "generationEventPollingRequestId" in content
    assert "pollGenerationEvents(requestId, { force = false } = {})" in content
    assert "flush = true" in content
    assert "flush: shouldFlushGenerationEvents" in content


def test_frontend_generation_flushes_terminal_non_displayable_payload_events() -> None:
    content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    failed_payload_handler = (
        'if (!isDisplayableGenerationResult(generationPayload)) {\n'
        "        shouldFlushGenerationEvents = true;\n"
        '        failGenerationProgress("persist");'
    )
    successful_render = (
        "renderQuizResult(generationPayload);\n"
        "      shouldFlushGenerationEvents = true;"
    )

    assert failed_payload_handler in content
    assert successful_render in content


def test_frontend_generation_file_read_observes_abort_signal() -> None:
    content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert "async function readFileArrayBuffer" in content
    assert "file.stream()" in content
    assert 'signal?.addEventListener("abort"' in content
    assert "reader.cancel()" in content
    assert "throwIfGenerationAborted(signal)" in content
    assert "content: await readFileArrayBuffer(file, abortController.signal)" in content


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

    assert "Текстовое содержание" in html
    assert "Параметры генерации" in html
    assert "Сгенерировать квиз" in html
    assert "Результат генерации" not in html
    assert 'class="result-head"' in html
    assert 'id="result-back-button"' in html
    assert 'class="form-actions inline-editor-add-actions result-foot"' in html
    assert "Редактирование квиза" in html
    assert "Название или ID квиза" in html
    assert "Сохранить" in html
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
    assert "client.cancelGeneration" in generation_content
    assert "CANCEL_CONFIRMATION_MAX_ATTEMPTS" in generation_content
    assert "Не удалось подтвердить отмену генерации" in generation_content
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


def test_frontend_compact_workspace_has_no_legacy_stepper() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    layout_css = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")
    responsive_css = (FRONTEND_DIR / "responsive.css").read_text(encoding="utf-8")
    progress_content = PROGRESS_JS.read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert 'id="stepper"' not in index_content
    assert 'class="stepper"' not in index_content
    assert 'data-stage-target=' not in index_content
    assert ".stepper" not in layout_css
    assert ".stepper" not in responsive_css
    assert "advanceStepper" not in progress_content
    assert "markStepperFailed" not in progress_content
    assert "activateWorkflowStage" in progress_content
    assert 'activateWorkflowStage("generation", { focus: true })' in generation_content
    assert 'activateWorkflowStage("setup", { focus: true })' in generation_content

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
    assert 'data-stage-target=' not in index_content
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
    assert "progressController.activateWorkflowStage" in app_content
    assert ".workflow-stage[hidden]" in layout_content
    assert "@keyframes stage-in" in layout_content


def test_frontend_panels_do_not_duplicate_stage_badges() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    for step_label in ("Шаг 1", "Шаг 2", "Шаг 3", "Шаг 4", "Шаг 5"):
        assert step_label not in content
    assert 'id="stepper"' not in content

def test_frontend_dropzone_surface_exposes_filled_preview_affordance() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    forms_css = (FRONTEND_DIR / "forms.css").read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert 'id="doc-input-wrap"' in index_content
    assert 'id="doc-text-input"' in index_content
    assert 'id="doc-file-pill"' in index_content
    assert 'id="doc-file-remove"' in index_content, (
        "doc input must expose a remove-file affordance"
    )
    assert 'id="document-file"' in index_content
    assert "Прикрепить файл" in index_content

    assert ".doc-input-wrap" in forms_css
    assert ".doc-file-pill" in forms_css
    assert ".doc-file-remove" in forms_css

    assert "function formatFileSize" in generation_content
    assert "function resolveInputFile" in generation_content
    assert "function removeSelectedFile" in generation_content
    assert "function updateDocInputSummary" in generation_content
    assert "removeSelectedFile" in app_content
    assert "docFileRemoveButton?.addEventListener" in app_content


def test_frontend_page_wide_document_drag_drop_overlay_is_wired() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    forms_css = (FRONTEND_DIR / "forms.css").read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert re.search(
        r'<div id="document-drop-overlay"[^>]*role="status"[^>]*aria-live="polite"',
        index_content,
    )
    assert "Отпустите файл, чтобы прикрепить документ" in index_content
    assert "TXT, DOCX или PDF" in index_content

    assert ".document-drop-overlay" in forms_css
    assert ".document-drop-overlay-card" in forms_css
    assert "backdrop-filter: blur" in forms_css
    assert "transition: opacity" in forms_css
    assert 'body[data-document-drag-active="true"] .document-drop-overlay' in forms_css

    assert "const documentDropOverlay = document.getElementById(\"document-drop-overlay\")" in app_content
    assert "documentDropOverlay" in app_content
    assert "function attachPageDocumentDropzone" in generation_content
    assert "function isFileDragEvent" in generation_content
    assert "function isSupportedDocumentFile" in generation_content
    assert "SUPPORTED_DOCUMENT_EXTENSIONS" in generation_content
    assert "Можно прикрепить только документ TXT, DOCX или PDF." in generation_content
    assert "isSupportedDocumentFile(file)" in generation_content
    assert 'document.addEventListener("dragenter"' in generation_content
    assert 'document.addEventListener("drop"' in generation_content
    assert 'document.body.dataset.documentDragActive = "true"' in generation_content
    assert 'showToast(`Файл «${file.name}» готов к загрузке.`, "ok")' in generation_content


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
    base_css = (FRONTEND_DIR / "base.css").read_text(encoding="utf-8")
    layout_css = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert 'class="hero-copy"' in index_content, (
        "the mockup fidelity shell must expose the compact hero subtitle"
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
    assert "aurora-drift" not in base_css
    assert "animation: aurora-drift" not in base_css
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
        "editor-quiz-id",
        "editor-document-id",
    ):
        assert f'data-copy-for="{source_id}"' in index_content, (
            f"{source_id} must have an associated copy button"
        )
        assert f'id="{source_id}"' in index_content

    assert 'aria-label="\u0421\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c Quiz ID \u0440\u0435\u0434\u0430\u043a\u0442\u043e\u0440\u0430"' in index_content, (
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


def test_frontend_generation_error_marks_workflow_stage_failed() -> None:
    progress_content = PROGRESS_JS.read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert "markWorkflowStageFailed" in progress_content
    assert 'state: "failed"' in progress_content
    assert "dataset.failedStage" in progress_content
    assert "markWorkflowStageFailed: progressController.markWorkflowStageFailed" in app_content
    assert 'markWorkflowStageFailed("generation")' in generation_content
    assert 'activateWorkflowStage("setup", { focus: true })' in generation_content

def test_frontend_legacy_stepper_styles_are_removed() -> None:
    layout_content = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")
    responsive_content = (FRONTEND_DIR / "responsive.css").read_text(encoding="utf-8")

    assert ".stepper" not in layout_content
    assert ".step-button" not in layout_content
    assert ".stepper" not in responsive_content

def test_frontend_model_picker_and_temperature_slider_are_wired_to_backend() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    settings_content = GENERATION_SETTINGS_JS.read_text(encoding="utf-8")
    client_content = API_CLIENT_JS.read_text(encoding="utf-8")
    generation_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert 'id="model-picker-field"' in index_content, (
        "index must expose a model picker field for advanced mode"
    )
    assert "model-picker-field" in index_content and "hidden" in index_content.split("model-picker-field", 1)[1][:20], (
        "model picker field must be hidden by default"
    )
    assert 'id="generation-model"' in index_content, (
        "index must contain the model select element inside the picker"
    )
    assert 'name="model_name"' in index_content

    assert 'id="generation-temperature"' in index_content
    assert 'name="temperature"' in index_content
    assert 'type="range"' in index_content
    assert 'min="0"' in index_content
    assert 'max="1"' in index_content
    assert 'step="0.1"' in index_content
    assert "Температура" in index_content
    assert "ниже — ответы стабильнее" in index_content
    assert "выше — больше разнообразия" in index_content
    assert 'id="generation-temperature-value"' in index_content
    assert 'id="generation-profile"' not in index_content
    assert 'name="profile_name"' not in index_content
    assert "Профиль" not in index_content

    assert "export function createGenerationSettingsController" in settings_content
    assert "loadSettings" in settings_content
    assert "populateModelSelect" in settings_content
    assert "available_models" in settings_content
    assert "default_model" in settings_content

    assert "getGenerationSettings" in client_content, (
        "API client must expose getGenerationSettings"
    )
    assert '"/generation/settings"' in client_content

    assert "enableModelPicker" in generation_content, (
        "generation flow must accept enableModelPicker to decide whether to send model_name"
    )
    assert 'formData.get("model_name")' in generation_content, (
        "generation payload must still be able to pick up model_name when picker is enabled"
    )
    assert 'formData.get("temperature")' in generation_content, (
        "generation payload must pick up the temperature override from the form"
    )
    assert "payload.temperature = temperature" in generation_content
    assert 'formData.get("profile_name")' not in generation_content
    assert "payload.profile_name = profileName" not in generation_content

    assert "generationSettings.loadSettings()" in app_content, (
        "app bootstrap must request available models from backend"
    )
    assert "generationTemperatureInput" in app_content
    assert "generationTemperatureValue" in app_content


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
    quiz_css = (FRONTEND_DIR / "quiz.css").read_text(encoding="utf-8")

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
    assert ".question-icon-action[hidden]" in quiz_css, (
        "hidden regeneration actions must stay visually hidden despite their grid display rule"
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


def test_frontend_progress_uses_stage_flow_without_aria_stepper() -> None:
    progress_content = PROGRESS_JS.read_text(encoding="utf-8")

    assert "stageFlow.activateStage" in progress_content
    assert "aria-current" not in progress_content
    assert "stepper" not in progress_content.lower()

def test_frontend_question_shape_exposes_backend_shaped_draft_helpers() -> None:
    content = QUESTION_SHAPE_JS.read_text(encoding="utf-8")

    for helper in (
        "createEmptyQuestion",
        "changeQuestionType",
        "validateEditableQuiz",
        "moveQuestionById",
    ):
        assert f"export function {helper}" in content
    assert "correct_option_index" in content
    assert "correct_answer" in content
    assert "matching_pairs" in content
    assert "Верно" in content
    assert "Неверно" in content


def test_frontend_result_screen_hosts_canonical_inline_editor() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")
    quiz_css = (FRONTEND_DIR / "quiz.css").read_text(encoding="utf-8")

    result_section = index_content.split('<section id="generation-result"', 1)[1].split("</section>", 1)[0]
    assert 'id="quiz-editor-fields"' in result_section
    assert 'id="save-quiz-button"' in result_section
    assert "validateEditableQuiz," in editor_content
    assert '} from "./question-shape.js";' in editor_content
    assert "validateEditableQuiz(updatePayload)" in editor_content
    assert 'deleteOptionButton.textContent = "×"' in editor_content
    assert 'deleteOptionButton.setAttribute("aria-label"' in editor_content
    assert 'data-editor-action", "delete-option"' in editor_content
    assert '.editor-option-row[data-correct="true"]' in quiz_css
    assert ".option-delete-action:focus-visible" in quiz_css


def test_frontend_inline_editor_exposes_structural_actions_and_undo() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    undo_stack_content = UNDO_STACK_JS.read_text(encoding="utf-8")
    quiz_css = (FRONTEND_DIR / "quiz.css").read_text(encoding="utf-8")

    assert 'id="undo-quiz-edit-button"' in index_content
    assert 'id="add-question-button"' in index_content
    assert 'from "./undo-stack.js"' in editor_content
    for helper in (
        "createEmptyQuestion",
        "changeQuestionType",
        "duplicateQuestion",
        "moveQuestionById",
    ):
        assert helper in editor_content
    for action in (
        "change-question-type",
        "duplicate-question",
        "delete-question",
        "move-question-up",
        "move-question-down",
        "add-question",
        "undo-structural-edit",
    ):
        assert action in editor_content
    assert "createUndoStack" in undo_stack_content
    assert "limit = 50" in undo_stack_content
    assert "quizEditor.handleStructuralAction" in app_content
    assert "quizEditor.undoLastStructuralEdit" in app_content
    assert ".question-reorder-actions" in quiz_css
    assert ".editor-card:focus-within .question-reorder-actions" in quiz_css


def test_frontend_result_foot_wires_back_to_setup() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")

    assert 'id="result-back-button"' in index_content
    assert 'data-editor-action="back-to-setup"' in index_content
    assert "resultBackButton?.addEventListener" in app_content
    assert "startNewQuiz" in app_content
    assert "editorExportJsonButton" not in app_content
    assert "editorExportSplitToggle" not in app_content
    assert "editorExportActions" not in app_content


def test_frontend_icon_only_actions_expose_tooltips() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    sidebar_content = SIDEBAR_JS.read_text(encoding="utf-8")
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")
    toast_content = TOAST_JS.read_text(encoding="utf-8")
    preview_content = PREVIEW_MODE_JS.read_text(encoding="utf-8")
    export_content = EXPORT_MODAL_JS.read_text(encoding="utf-8")

    for action_id in (
        "sidebar-toggle",
        "sidebar-new-quiz",
        "sidebar-status-cell",
        "theme-toggle",
        "doc-file-remove",
    ):
        element = index_content.split(f'id="{action_id}"', 1)[1].split(">", 1)[0]
        assert "title=" in element
    assert 'data-workspace-modal-close aria-label="Закрыть окно статуса" title=' in index_content
    assert "toggleButton.title = label;" in sidebar_content
    assert 'moveUpButton.title = "Переместить вопрос вверх";' in editor_content
    assert 'moveDownButton.title = "Переместить вопрос вниз";' in editor_content
    assert 'close.title = "Закрыть уведомление";' in toast_content
    assert 'closeButton.title = "Закрыть предпросмотр";' in preview_content
    assert 'closeButton.title = "Закрыть экспорт";' in export_content


def test_frontend_matching_editor_uses_dedicated_pair_rows_without_distractors() -> None:
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")
    shape_content = QUESTION_SHAPE_JS.read_text(encoding="utf-8")
    quiz_css = (FRONTEND_DIR / "quiz.css").read_text(encoding="utf-8")

    assert "export function addMatchingPair" in shape_content
    assert "export function removeMatchingPair" in shape_content
    assert 'pairsGrid.className = "matching-pairs-editor"' in editor_content
    assert 'pairRow.className = "matching-pair-row"' in editor_content
    assert '.className = "matching-pair-badge"' in editor_content
    assert 'link.className = "matching-pair-link"' in editor_content
    assert '"add-matching-pair"' in editor_content
    assert '"delete-matching-pair"' in editor_content
    assert "Для сопоставления нужны минимум 4 пары." in editor_content
    assert "distractors" not in editor_content
    assert "Лишние варианты" not in editor_content
    assert ".matching-pair-row:hover .matching-pair-delete" in quiz_css
    assert ".matching-pair-row:focus-within .matching-pair-delete" in quiz_css


def test_frontend_question_regeneration_uses_stable_snapshot_and_compact_busy_state() -> None:
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")
    quiz_css = (FRONTEND_DIR / "quiz.css").read_text(encoding="utf-8")

    assert 'regenerateButton.textContent = "↻"' in editor_content
    assert 'cancelRegenerateButton.textContent = "■"' in editor_content
    assert 'revertButton.textContent = "↶"' in editor_content
    assert 'body.className = "editor-card-body"' in editor_content
    assert 'content.className = "editor-card-content"' in editor_content
    assert 'overlay.className = "question-regenerate-overlay"' in editor_content
    assert '.classList.toggle("is-regenerating", Boolean(busy))' in editor_content
    assert "stableQuestion = cloneQuizPayload(displayedQuestion)" in editor_content
    assert "function normalizeRegeneratedQuestion" in editor_content
    assert "function restoreStableQuestionCard" in editor_content
    assert "activeRegenerationController && !activeRegenerationController.signal.aborted" in editor_content
    assert 'regenerateButton.textContent = "Перегенерировать вопрос"' not in editor_content
    assert 'revertButton.textContent = "Отменить правки"' not in editor_content
    assert ".editor-card.is-regenerating .editor-card-content" in quiz_css
    assert ".question-regenerate-overlay" in quiz_css
    assert "@keyframes question-regeneration-pulse" in quiz_css


def test_frontend_playable_preview_supports_all_question_types_without_mutating_editor() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    app_content = APP_JS.read_text(encoding="utf-8")
    preview_content = PREVIEW_MODE_JS.read_text(encoding="utf-8")
    quiz_css = (FRONTEND_DIR / "quiz.css").read_text(encoding="utf-8")
    layout_css = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")
    responsive_css = (FRONTEND_DIR / "responsive.css").read_text(encoding="utf-8")

    assert 'id="preview-quiz-button"' in index_content
    assert 'id="preview-quiz-hint"' in index_content
    assert 'import { createPlayablePreview } from "./preview-mode.js";' in app_content
    assert "createPlayablePreview({" in app_content
    assert 'previewQuizButton?.addEventListener("click", previewMode.open)' in app_content
    assert "export function clonePreviewQuiz" in preview_content
    assert "export function shufflePreviewValues" in preview_content
    assert "function ensureChangedOrder" in preview_content
    assert "export function gradeQuizPreview" in preview_content
    assert "validateEditableQuiz" in preview_content
    for question_type in ("single_choice", "true_false", "fill_blank", "short_answer", "matching"):
        assert question_type in preview_content
    assert "matching_pairs" in preview_content
    assert "distractors" not in preview_content
    assert 'dialog.addEventListener("cancel"' in preview_content
    assert ".target === dialog" in preview_content
    assert "restoreFocus" in preview_content
    assert ".preview-question" in quiz_css
    assert ".quiz-preview-modal" in layout_css
    assert ".quiz-preview-modal" in responsive_css


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
    assert '<option value="auto" selected>' in index_content, (
        "auto must be the default generation mode"
    )
    assert '<option value="direct">' in index_content, (
        "direct must remain selectable as an explicit mode"
    )
    assert '<option value="rag">' in index_content, (
        "rag must be selectable"
    )
    assert "Авто (RAG для длинных документов)" in index_content, (
        "auto option copy must explain the automatic RAG behaviour in Russian"
    )
    assert "RAG — всегда" in index_content, (
        "rag option copy must explain the explicit retrieval mode in Russian"
    )


def test_frontend_index_hides_resolved_generation_mode_from_result() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="quiz-generation-mode"' not in index_content
    assert "<dt>\u0420\u0435\u0436\u0438\u043c</dt>" not in index_content

def test_frontend_generation_flow_forwards_requested_generation_mode() -> None:
    content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert 'DEFAULT_GENERATION_MODE = "auto"' in content, (
        "unsupported modes must fall back to auto"
    )
    assert 'SUPPORTED_REQUEST_MODES = Object.freeze(["auto", "direct", "rag"])' in content, (
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


def test_frontend_surfaces_generation_warnings_as_partial_result() -> None:
    renderer_content = QUIZ_RENDERER_JS.read_text(encoding="utf-8")
    flow_content = GENERATION_FLOW_JS.read_text(encoding="utf-8")

    assert "generationPayload.warnings" in renderer_content
    assert "generationPayload.quality_status" in renderer_content
    assert "qualityStatus === \"failed\"" in renderer_content
    assert "Квиз показан с предупреждениями" in renderer_content
    assert "formatWarningSummary(warnings)" in renderer_content
    assert "Результат частичный" in renderer_content
    assert "hasGenerationWarnings" in flow_content
    assert "isDisplayableGenerationResult" in flow_content
    assert "quality_status" in flow_content
    assert "часть результата была автоматически исправлена" in flow_content
    assert "Проверьте предупреждение над квизом" in flow_content


def test_frontend_p3_visual_tokens() -> None:
    tokens = (FRONTEND_DIR / "tokens.css").read_text(encoding="utf-8")
    layout = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")

    assert "--radius-xs: 6px" in tokens
    assert "--radius-sm: 10px" in tokens
    assert "--radius-md: 14px" in tokens
    assert "--radius-lg: 20px" in tokens

    assert "--bg: #f6f3ec" in tokens
    assert "--bg: #0b0d14" in tokens
    assert "--surface: rgba(255, 252, 244, 0.85)" in tokens
    assert "--surface: rgba(22, 25, 36, 0.72)" in tokens
    assert "--ink: #1a1827" in tokens
    assert "--ink: #f1efe9" in tokens
    assert "--muted: #6a6781" in tokens
    assert "--muted: #9a9aa8" in tokens
    assert "--brand: #5c4dd6" in tokens
    assert "--brand: #8b7dff" in tokens
    assert "--accent: #d62f93" in tokens
    assert "--accent: #ff5fae" in tokens
    assert "--bad: #ff6b82" in tokens
    assert "--duration-fast: 140ms" in tokens
    assert "--duration-base: 260ms" in tokens
    assert "--duration-slow: 540ms" in tokens

    assert "blur(10px)" in layout
    assert "blur(8px)" in layout
    assert "font-size: 1.1rem" in layout
    assert "font-size: 0.88rem" in layout


def test_frontend_config_exposes_enable_model_picker_flag() -> None:
    content = CONFIG_JS.read_text(encoding="utf-8")

    assert "enableModelPicker" in content, (
        "config must expose enableModelPicker feature flag"
    )
    assert "enableModelPicker: false" in content, (
        "enableModelPicker must default to false so model selection is hidden"
    )


def test_frontend_index_exposes_model_picker_for_advanced_mode() -> None:
    content = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="model-picker-field"' in content, (
        "index must expose the model picker label for advanced mode"
    )
    assert 'id="generation-model"' in content, (
        "index must expose the model select inside the picker"
    )
    assert 'class="field field-model-picker"' in content


def test_frontend_model_picker_styles_are_defined() -> None:
    content = FORMS_CSS.read_text(encoding="utf-8")

    assert ".field-model-picker" in content, (
        "forms.css must style the model picker for advanced mode"
    )


def test_frontend_generation_settings_respects_enable_model_picker() -> None:
    settings_content = GENERATION_SETTINGS_JS.read_text(encoding="utf-8")

    assert "enableModelPicker" in settings_content, (
        "generation-settings must accept enableModelPicker parameter"
    )


def test_frontend_generation_settings_omits_model_name_when_picker_disabled() -> None:
    settings_content = GENERATION_SETTINGS_JS.read_text(encoding="utf-8")

    guard = "if (enableModelPicker && modelSelect"
    assert guard in settings_content, (
        "getGenerationOverrides must guard model_name behind enableModelPicker flag"
    )


def test_frontend_app_wires_enable_model_picker_flag() -> None:
    app_content = APP_JS.read_text(encoding="utf-8")

    assert "enableModelPicker" in app_content, (
        "app.js must read enableModelPicker from config"
    )
    assert "modelPickerField" in app_content


def test_frontend_compact_workspace_uses_mockup_fidelity_layout() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    fidelity_css = (FRONTEND_DIR / "fidelity.css").read_text(encoding="utf-8")

    assert '<link rel="stylesheet" href="./fidelity.css">' in index_content
    assert "width: min(1080px, calc(100vw - var(--sidebar-width) - 48px));" in fidelity_css
    assert "--workspace-gutter: max(24px, calc((100vw - var(--sidebar-width) - 1080px) / 2));" in fidelity_css
    assert "margin-left: calc(var(--sidebar-width) + var(--workspace-gutter));" in fidelity_css
    assert "margin-right: var(--workspace-gutter);" in fidelity_css
    assert "grid-template-columns: minmax(0, 1fr);" in fidelity_css
    assert "padding: 22px 22px 23px;" in fidelity_css
    assert "padding: 22px 22px 11px;" in fidelity_css
    assert "text-align: center;" in fidelity_css


def test_frontend_result_foot_uses_mockup_ghost_link_and_compact_type_select() -> None:
    fidelity_css = (FRONTEND_DIR / "fidelity.css").read_text(encoding="utf-8")

    assert ".compact-workspace .ghost-link" in fidelity_css
    assert ".compact-workspace .result-foot-spacer" in fidelity_css
    assert ".compact-workspace .inline-editor-add-actions .add-question-type-select" in fidelity_css
    assert ".compact-workspace .inline-editor-add-actions .add-question-button" in fidelity_css


def test_frontend_result_screen_hides_setup_hero_and_legacy_question_cards() -> None:
    fidelity_css = (FRONTEND_DIR / "fidelity.css").read_text(encoding="utf-8")

    assert '.workspace[data-active-stage]:not([data-active-stage="setup"])' in fidelity_css
    assert ".compact-workspace .panel-result .question-list" in fidelity_css
    assert "flex-direction: row;" in fidelity_css
    assert "field-sizing: content;" in fidelity_css


def test_frontend_result_question_type_stays_next_to_question_number() -> None:
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")
    card_actions = editor_content.split(
        'cardActions.className = "question-structure-actions q-actions";',
        1,
    )[1].split("header.append(", 1)[0]

    assert "questionTypeSelect" not in card_actions
    assert "regenerateButton" in card_actions
    assert "duplicateButton" in card_actions


def test_frontend_result_removes_technical_details_and_uses_review_copy() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    renderer_content = QUIZ_RENDERER_JS.read_text(encoding="utf-8")

    assert "Технические детали квиза" not in index_content
    assert "Результат готов. Квиз отображён ниже." not in renderer_content
    assert "Проверьте вопросы, поправьте формулировки и выберите формат экспорта." in renderer_content


def test_frontend_correct_option_marker_click_preserves_viewport() -> None:
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")

    assert 'event.target.closest("[data-option-mark]")' in editor_content
    assert "function preserveViewportPosition" in editor_content
    assert "preserveViewportPosition(() => renderQuizEditor(quiz))" in editor_content


def test_frontend_question_regeneration_stop_and_dirty_states_match_mockup() -> None:
    editor_content = QUIZ_EDITOR_JS.read_text(encoding="utf-8")
    fidelity_css = (FRONTEND_DIR / "fidelity.css").read_text(encoding="utf-8")

    assert 'cancelRegenerateButton.title = "Остановить генерацию"' in editor_content
    assert ".compact-workspace .q-card.is-dirty::before" in fidelity_css
    assert ".compact-workspace .q-card.is-regenerating .q-act:not(.q-act-stop)" in fidelity_css


def test_frontend_setup_markup_uses_mockup_control_structure() -> None:
    index_content = INDEX_HTML.read_text(encoding="utf-8")

    assert 'class="panel-heading visually-hidden"' in index_content
    assert 'id="word-count"' in index_content
    assert 'class="doc-input-meta"' in index_content
    assert 'class="textarea-wrap"' in index_content
    assert 'class="doc-toolbar source-toolbar"' in index_content
    assert 'class="slider-rail-marks"' in index_content
    assert 'class="difficulty-segment"' in index_content
    assert 'data-difficulty-value="medium"' in index_content
    assert 'class="question-type-option question-type-chip"' in index_content


def test_frontend_sidebar_uses_mockup_collapse_transition() -> None:
    fidelity_css = (FRONTEND_DIR / "fidelity.css").read_text(encoding="utf-8")

    assert "transition: width var(--duration-base) var(--easing);" in fidelity_css
    assert "transition: transform var(--duration-base) var(--easing);" in fidelity_css
