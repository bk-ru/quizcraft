import { QuizCraftApiClient } from "./api/client.js";
import { createJsonExporter } from "./download.js";
import { createGenerationFlow } from "./generation-flow.js";
import { createProgressController } from "./progress.js";
import { createQuizEditor } from "./quiz-editor.js";
import { createQuizRenderer } from "./quiz-renderer.js";
import { createThemeController } from "./theme.js";
import { createToastController } from "./toast.js";
import { describeError, describeValidationError } from "./validation-errors.js";

const config = window.QuizCraftConfig ?? {};
const backendBaseUrl = typeof config.backendBaseUrl === "string" && config.backendBaseUrl.trim()
  ? config.backendBaseUrl.trim()
  : "http://127.0.0.1:8000";
const timeouts = config.timeouts ?? {};

const client = new QuizCraftApiClient({
  baseUrl: backendBaseUrl,
  timeouts,
});

const form = document.getElementById("generation-form");
const fileInput = document.getElementById("document-file");
const submitButton = document.getElementById("submit-button");
const resultPanel = document.getElementById("generation-result");
const resultStateBadge = document.getElementById("result-state-badge");
const questionList = document.getElementById("quiz-question-list");
const quizEditorLoader = document.getElementById("quiz-editor-loader");
const quizIdInput = document.getElementById("quiz-id-input");
const loadQuizButton = document.getElementById("load-quiz-button");
const saveQuizButton = document.getElementById("save-quiz-button");
const quizEditorFields = document.getElementById("quiz-editor-fields");
const exportJsonButton = document.getElementById("export-json-button");
const editShortcutButton = document.getElementById("edit-quiz-shortcut");
const themeToggleButton = document.getElementById("theme-toggle");
const themeToggleLabel = document.getElementById("theme-toggle-label");
const dropzone = document.getElementById("dropzone");
const toastRegion = document.getElementById("toast-region");
const stepper = document.getElementById("stepper");
const generationProgressPanel = document.getElementById("generation-progress");

const editorState = {
  loadedQuiz: null,
  isDirty: false,
  lastGeneratedQuizId: null,
};

const statusMap = {
  ok: "ok",
  available: "ok",
  unavailable: "bad",
};

const LM_STUDIO_UNAVAILABLE_INSTRUCTION =
  "LM Studio недоступен. Запустите приложение LM Studio, загрузите модель и убедитесь, что сервер слушает http://127.0.0.1:1234.";

function setTextContent(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function setStatus(surface, text, tone) {
  const container = document.querySelector(`[data-status-surface="${surface}"]`);
  const target = document.getElementById(`${surface}-status-text`);
  if (target) {
    target.textContent = text;
  }
  if (container) {
    if (tone) {
      container.dataset.statusTone = tone;
    } else {
      delete container.dataset.statusTone;
    }
  }
}

function setToneMessage(element, text, tone) {
  if (!element) {
    return;
  }
  element.textContent = text;
  if (tone) {
    element.dataset.statusTone = tone;
  } else {
    delete element.dataset.statusTone;
  }
}

function setLogMessage(text, tone) {
  setToneMessage(document.getElementById("shell-log-message"), text, tone);
}

function setSubmissionStatus(text, tone) {
  setToneMessage(document.getElementById("submission-status"), text, tone);
}

function setEditorStatus(text, tone) {
  setToneMessage(document.getElementById("quiz-editor-status"), text, tone);
}

function setExportAvailability(quizId) {
  editorState.lastGeneratedQuizId = typeof quizId === "string" && quizId.trim() ? quizId.trim() : null;
  const available = Boolean(editorState.lastGeneratedQuizId);
  if (exportJsonButton) {
    exportJsonButton.disabled = !available;
  }
  if (editShortcutButton) {
    editShortcutButton.disabled = !available;
  }
}

const toastController = createToastController(toastRegion);
const progressController = createProgressController({ stepper, generationProgressPanel });
const themeController = createThemeController({ themeToggleLabel });

const quizRenderer = createQuizRenderer({
  resultPanel,
  resultStateBadge,
  questionList,
  setTextContent,
  setExportAvailability,
  advanceStepper: progressController.advanceStepper,
});

const quizEditor = createQuizEditor({
  editorState,
  client,
  quizEditorLoader,
  quizIdInput,
  loadQuizButton,
  saveQuizButton,
  quizEditorFields,
  setTextContent,
  setEditorStatus,
  setLogMessage,
  setExportAvailability,
  advanceStepper: progressController.advanceStepper,
  showToast: toastController.showToast,
  describeError,
  describeValidationError,
});

const generationFlow = createGenerationFlow({
  client,
  form,
  fileInput,
  submitButton,
  dropzone,
  quizIdInput,
  setTextContent,
  setSubmissionStatus,
  setResultState: quizRenderer.setResultState,
  setLogMessage,
  setEditorStatus,
  setExportAvailability,
  clearQuizResult: quizRenderer.clearQuizResult,
  renderQuizResult: quizRenderer.renderQuizResult,
  renderQuizEditor: quizEditor.renderQuizEditor,
  setQuizEditorSummary: quizEditor.setQuizEditorSummary,
  advanceStepper: progressController.advanceStepper,
  waitForProgressVisibility: progressController.waitForProgressVisibility,
  startGenerationProgress: progressController.startGenerationProgress,
  advanceGenerationProgress: progressController.advanceGenerationProgress,
  completeGenerationProgress: progressController.completeGenerationProgress,
  completeGenerationProgressWithBackendEvidence: progressController.completeGenerationProgressWithBackendEvidence,
  failGenerationProgress: progressController.failGenerationProgress,
  showToast: toastController.showToast,
});

const jsonExporter = createJsonExporter({
  backendBaseUrl,
  client,
  editorState,
  showToast: toastController.showToast,
});

async function bootstrapShell() {
  setTextContent("backend-base-url", backendBaseUrl);
  const t = client.timeouts;
  setTextContent("request-timeout",
    `health ${t.health / 1000} с · upload ${t.upload / 1000} с · generate ${t.generate / 1000} с · editor ${t.quizEditor / 1000} с`,
  );
  generationFlow.updateSelectedFileSummary();
  quizRenderer.clearQuizResult();
  quizEditor.clearQuizEditor();
  setEditorStatus("Загрузите существующий квиз, чтобы открыть редактируемые поля и сохранить изменения.", null);
  quizRenderer.setResultState("Квиз появится здесь после успешной генерации.", "idle", "Ожидание результата");

  try {
    const [backendHealth, providerHealth] = await Promise.all([
      client.getBackendHealth(),
      client.getProviderHealth(),
    ]);

    setStatus(
      "backend",
      `Доступен · модель ${backendHealth.default_model}`,
      statusMap[backendHealth.status] ?? "ok",
    );
    if (providerHealth.status === "unavailable") {
      setStatus("provider", "Недоступен · запустите LM Studio", "bad");
      setLogMessage(LM_STUDIO_UNAVAILABLE_INSTRUCTION, "bad");
      toastController.showToast(LM_STUDIO_UNAVAILABLE_INSTRUCTION, "bad");
    } else {
      setStatus(
        "provider",
        `${providerHealth.status} · ${providerHealth.message}`,
        statusMap[providerHealth.status] ?? "warn",
      );
      setLogMessage("Shell успешно связался с backend health endpoint-ами.", "ok");
    }
  } catch (error) {
    setStatus("backend", "Проверка не удалась", "bad");
    setStatus("provider", "Проверка не удалась", "bad");
    setLogMessage(`Shell не смог получить health-статус: ${describeError(error)}`, "bad");
  }
}

function openEditorForCurrentQuiz() {
  const quizId = editorState.lastGeneratedQuizId;
  if (!quizId || !quizIdInput) {
    return;
  }
  quizIdInput.value = quizId;
  const editorPanel = document.getElementById("quiz-editor");
  if (editorPanel) {
    editorPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  loadQuizButton?.focus();
}

themeController.applyTheme(themeController.resolveStoredTheme());
themeToggleButton?.addEventListener("click", themeController.cycleTheme);
generationFlow.attachDropzone();
exportJsonButton?.addEventListener("click", jsonExporter.exportQuizAsJson);
editShortcutButton?.addEventListener("click", openEditorForCurrentQuiz);

fileInput?.addEventListener("change", () => {
  generationFlow.updateSelectedFileSummary();
  if (fileInput.files?.[0]) {
    progressController.advanceStepper("params");
  }
});
form?.addEventListener("submit", generationFlow.submitGeneration);
quizEditorLoader?.addEventListener("submit", quizEditor.loadQuizForEditing);
quizEditorFields?.addEventListener("input", quizEditor.markEditorDirty);
quizEditorFields?.addEventListener("change", quizEditor.markEditorDirty);
saveQuizButton?.addEventListener("click", quizEditor.submitQuizEdits);

bootstrapShell();
