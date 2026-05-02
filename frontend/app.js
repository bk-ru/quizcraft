import { QuizCraftApiClient } from "./api/client.js";
import { createQuizExporter } from "./download.js";
import { createCopyButtonController } from "./copy.js";
import { createGenerationFlow } from "./generation-flow.js";
import { createGenerationSettingsController } from "./generation-settings.js";
import { createKeyboardShortcuts } from "./keyboard.js";
import { createConfirmModal } from "./modal.js";
import { createProgressController } from "./progress.js";
import { createQuizEditor } from "./quiz-editor.js";
import { createQuizHistory } from "./quiz-history.js";
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
const exportDocxButton = document.getElementById("export-docx-button");
const exportPptxButton = document.getElementById("export-pptx-button");
const editShortcutButton = document.getElementById("edit-quiz-shortcut");
const themeToggleButton = document.getElementById("theme-toggle");
const themeToggleLabel = document.getElementById("theme-toggle-label");
const dropzone = document.getElementById("dropzone");
const toastRegion = document.getElementById("toast-region");
const stepper = document.getElementById("stepper");
const generationProgressPanel = document.getElementById("generation-progress");
const cancelGenerationButton = document.getElementById("cancel-generation-button");
const generationTimerElement = document.getElementById("generation-timer");
const dropzoneFileName = document.getElementById("dropzone-file-name");
const dropzoneFileMeta = document.getElementById("dropzone-file-meta");
const dropzoneRemoveButton = document.getElementById("dropzone-remove");
const modelSelect = document.getElementById("generation-model");
const profileSelect = document.getElementById("generation-profile");
const retryBackendButton = document.getElementById("retry-backend-button");
const retryProviderButton = document.getElementById("retry-provider-button");

const editorState = {
  loadedQuiz: null,
  loadedQuizLanguage: null,
  isDirty: false,
  lastGeneratedQuizId: null,
  supportedExportFormats: new Set(["json"]),
};

const exportButtons = Object.freeze({
  json: {
    button: exportJsonButton,
    hintId: "export-json-hint",
  },
  docx: {
    button: exportDocxButton,
    hintId: "export-docx-hint",
  },
  pptx: {
    button: exportPptxButton,
    hintId: "export-pptx-hint",
  },
});

const statusMap = {
  ok: "ok",
  available: "ok",
  unavailable: "bad",
};

const LM_STUDIO_UNAVAILABLE_INSTRUCTION =
  "LM Studio недоступен. Запустите приложение LM Studio, загрузите модель и убедитесь, что сервер слушает http://127.0.0.1:1234.";
const BACKEND_AVAILABLE_INSTRUCTION =
  "Backend отвечает. Если генерация не запускается, проверьте LM Studio и выбранную модель.";
const BACKEND_CHECK_FAILED_INSTRUCTION =
  "Backend недоступен. Запустите сервер командой .\\run-backend.ps1 из корня проекта и проверьте, что порт 8000 свободен.";
const PROVIDER_AVAILABLE_INSTRUCTION =
  "LM Studio отвечает через backend. Если генерация падает, проверьте загруженную модель и поддержку structured output.";
const PROVIDER_CHECK_FAILED_INSTRUCTION =
  "LM Studio не удалось проверить через backend. Убедитесь, что backend запущен, LM Studio открыт, модель загружена, а server mode включен.";
const PROVIDER_CHECK_BLOCKED_INSTRUCTION =
  "LM Studio проверяется через backend. Сначала восстановите подключение к серверу.";

function setTextContent(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function setStatus(surface, text, tone, description) {
  const container = document.querySelector(`[data-status-surface="${surface}"]`);
  const target = document.getElementById(`${surface}-status-text`);
  if (target) {
    target.textContent = text;
  }
  if (container) {
    const label = container.dataset.statusLabel || surface;
    const title = description ? `${label} · ${text}. ${description}` : `${label} · ${text}`;
    container.setAttribute("title", title);
    container.setAttribute("aria-label", title);
    if (tone) {
      container.dataset.statusTone = tone;
    } else {
      delete container.dataset.statusTone;
    }
  }
}

function setRetryButtonBusy(buttonElement, busy, busyText) {
  if (!buttonElement) {
    return;
  }
  if (!buttonElement.dataset.idleLabel) {
    buttonElement.dataset.idleLabel = buttonElement.textContent.trim();
  }
  buttonElement.disabled = Boolean(busy);
  buttonElement.textContent = busy ? busyText : buttonElement.dataset.idleLabel;
}

function setToneMessage(element, text, tone) {
  if (!element) {
    return;
  }
  element.textContent = text;
  element.hidden = !text;
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

function toggleUnavailableHint(buttonElement, hintId, isDisabled) {
  if (!buttonElement) {
    return;
  }
  buttonElement.disabled = Boolean(isDisabled);
  if (!hintId) {
    return;
  }
  if (isDisabled) {
    buttonElement.setAttribute("aria-describedby", hintId);
  } else {
    buttonElement.removeAttribute("aria-describedby");
  }
}

function setExportAvailability(quizId) {
  editorState.lastGeneratedQuizId = typeof quizId === "string" && quizId.trim() ? quizId.trim() : null;
  const hasQuiz = Boolean(editorState.lastGeneratedQuizId);
  for (const [format, exportButton] of Object.entries(exportButtons)) {
    const supported = format === "json" || editorState.supportedExportFormats.has(format);
    toggleUnavailableHint(exportButton.button, exportButton.hintId, !(hasQuiz && supported));
  }
  toggleUnavailableHint(editShortcutButton, "edit-shortcut-hint", !hasQuiz);
}

const modalRegion = document.getElementById("modal-region");
const toastController = createToastController(toastRegion);
const confirmModal = createConfirmModal({ modalRegion });
const progressController = createProgressController({ stepper, generationProgressPanel });
const themeController = createThemeController({ themeToggleLabel });
const quizHistory = createQuizHistory({
  datalistElement: document.getElementById("quiz-history-options"),
});
quizHistory.renderHistoryDatalist();
const generationSettings = createGenerationSettingsController({
  client,
  modelSelect,
  profileSelect,
  setLogMessage,
});

const quizRenderer = createQuizRenderer({
  resultPanel,
  resultStateBadge,
  questionList,
  setTextContent,
  setExportAvailability,
  advanceStepper: progressController.advanceStepper,
});

function focusResultView() {
  if (!resultPanel) {
    return;
  }
  resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  resultPanel.focus({ preventScroll: true });
}

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
  renderQuizResult: quizRenderer.renderQuizResult,
  showToast: toastController.showToast,
  describeError,
  describeValidationError,
  saveQuizToHistory: quizHistory.saveQuizToHistory,
  getLanguageForQuiz: quizHistory.findLanguageByQuizId,
  confirmAction: confirmModal.confirm,
});

const generationFlow = createGenerationFlow({
  client,
  form,
  fileInput,
  submitButton,
  dropzone,
  quizIdInput,
  cancelButton: cancelGenerationButton,
  timerElement: generationTimerElement,
  dropzoneFileName,
  dropzoneFileMeta,
  dropzoneRemoveButton,
  setTextContent,
  setSubmissionStatus,
  setResultState: quizRenderer.setResultState,
  setLogMessage,
  setEditorStatus,
  setExportAvailability,
  clearQuizResult: quizRenderer.clearQuizResult,
  renderQuizResult: quizRenderer.renderQuizResult,
  focusResultView,
  advanceStepper: progressController.advanceStepper,
  markStepperFailed: progressController.markStepperFailed,
  waitForProgressVisibility: progressController.waitForProgressVisibility,
  startGenerationProgress: progressController.startGenerationProgress,
  advanceGenerationProgress: progressController.advanceGenerationProgress,
  completeGenerationProgress: progressController.completeGenerationProgress,
  completeGenerationProgressWithBackendEvidence: progressController.completeGenerationProgressWithBackendEvidence,
  failGenerationProgress: progressController.failGenerationProgress,
  showToast: toastController.showToast,
  saveQuizToHistory: quizHistory.saveQuizToHistory,
  refreshGenerationDefaults: generationSettings.refreshAfterGeneration,
});

const quizExporter = createQuizExporter({
  backendBaseUrl,
  client,
  editorState,
  showToast: toastController.showToast,
});

const keyboardShortcuts = createKeyboardShortcuts({
  generationForm: form,
  generationFlow,
  quizEditor,
  editorState,
  toastController,
});
keyboardShortcuts.register();

const copyButtons = createCopyButtonController({
  showToast: toastController.showToast,
});
copyButtons.register();

async function bootstrapShell() {
  generationFlow.updateSelectedFileSummary();
  quizRenderer.clearQuizResult();
  quizEditor.clearQuizEditor();
  setEditorStatus("Загрузите существующий квиз, чтобы открыть редактируемые поля и сохранить изменения.", null);
  quizRenderer.setResultState("Квиз появится здесь после успешной генерации.", "idle", "Ожидание результата");
  const backendHealth = await checkBackendConnection({ loadExports: false, refreshSettings: true });
  if (!backendHealth) {
    setStatus("provider", "Проверка не удалась", "bad", PROVIDER_CHECK_BLOCKED_INSTRUCTION);
    setExportAvailability(editorState.lastGeneratedQuizId);
    return;
  }
  await checkProviderConnection();
  await loadExportFormats();
}

async function checkBackendConnection({ loadExports = true, refreshSettings = true } = {}) {
  setStatus("backend", "Проверка…", null, "Проверяем доступность backend-сервера.");
  setRetryButtonBusy(retryBackendButton, true, "Проверяем сервер…");
  try {
    const backendHealth = await client.getBackendHealth();
    setStatus(
      "backend",
      `Доступен · модель ${backendHealth.default_model}`,
      statusMap[backendHealth.status] ?? "ok",
      BACKEND_AVAILABLE_INSTRUCTION,
    );
    setLogMessage("Сервер доступен.", "ok");
    if (refreshSettings) {
      await generationSettings.loadSettings();
    }
    if (loadExports) {
      await loadExportFormats();
    }
    return backendHealth;
  } catch (error) {
    setStatus("backend", "Проверка не удалась", "bad", BACKEND_CHECK_FAILED_INSTRUCTION);
    setLogMessage(`Не удалось подключиться к серверу: ${describeError(error)}. ${BACKEND_CHECK_FAILED_INSTRUCTION}`, "bad");
    setExportAvailability(editorState.lastGeneratedQuizId);
    return null;
  } finally {
    setRetryButtonBusy(retryBackendButton, false, "Проверяем сервер…");
  }
}

async function checkProviderConnection() {
  setStatus("provider", "Проверка…", null, "Проверяем подключение к LM Studio через backend.");
  setRetryButtonBusy(retryProviderButton, true, "Проверяем LM Studio…");
  try {
    const providerHealth = await client.getProviderHealth();
    if (providerHealth.status === "unavailable") {
      setStatus("provider", "Недоступен · запустите LM Studio", "bad", LM_STUDIO_UNAVAILABLE_INSTRUCTION);
      setLogMessage(LM_STUDIO_UNAVAILABLE_INSTRUCTION, "bad");
      toastController.showToast(LM_STUDIO_UNAVAILABLE_INSTRUCTION, "bad");
    } else {
      setStatus(
        "provider",
        `${providerHealth.status} · ${providerHealth.message}`,
        statusMap[providerHealth.status] ?? "warn",
        PROVIDER_AVAILABLE_INSTRUCTION,
      );
      setLogMessage("Подключение к LM Studio проверено.", "ok");
    }
    return providerHealth;
  } catch (error) {
    setStatus("provider", "Проверка не удалась", "bad", PROVIDER_CHECK_FAILED_INSTRUCTION);
    setLogMessage(`Не удалось проверить LM Studio: ${describeError(error)}. ${PROVIDER_CHECK_FAILED_INSTRUCTION}`, "bad");
    return null;
  } finally {
    setRetryButtonBusy(retryProviderButton, false, "Проверяем LM Studio…");
  }
}

async function loadExportFormats() {
  try {
    const payload = await client.getExportFormats();
    editorState.supportedExportFormats = parseSupportedExportFormats(payload);
    editorState.supportedExportFormats.add("json");
    setExportAvailability(editorState.lastGeneratedQuizId);
  } catch (error) {
    setLogMessage(`Не удалось получить форматы экспорта: ${describeError(error)}`, "warn");
    setExportAvailability(editorState.lastGeneratedQuizId);
  }
}

function parseSupportedExportFormats(payload) {
  const formats = Array.isArray(payload?.formats) ? payload.formats : [];
  return new Set(
    formats
      .map((item) => typeof item?.format === "string" ? item.format.trim().toLowerCase() : "")
      .filter(Boolean),
  );
}

function openEditorForCurrentQuiz() {
  const quizId = editorState.lastGeneratedQuizId;
  if (!quizId || !quizIdInput) {
    return;
  }
  quizIdInput.value = quizId;
  const editorPanel = document.getElementById("quiz-editor");
  if (editorPanel) {
    if (editorPanel instanceof HTMLDetailsElement) {
      editorPanel.open = true;
    }
    editorPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  quizEditor.loadQuizForEditing({ preventDefault: () => {} });
}

themeController.applyTheme(themeController.resolveStoredTheme());
themeToggleButton?.addEventListener("click", themeController.cycleTheme);
retryBackendButton?.addEventListener("click", () => {
  checkBackendConnection();
});
retryProviderButton?.addEventListener("click", () => {
  checkProviderConnection();
});

window.addEventListener("beforeunload", (event) => {
  if (!editorState.isDirty) {
    return;
  }
  event.preventDefault();
  event.returnValue = "";
});
generationFlow.attachDropzone();
exportJsonButton?.addEventListener("click", quizExporter.exportQuizAsJson);
exportDocxButton?.addEventListener("click", quizExporter.exportQuizAsDocx);
exportPptxButton?.addEventListener("click", quizExporter.exportQuizAsPptx);
editShortcutButton?.addEventListener("click", openEditorForCurrentQuiz);
cancelGenerationButton?.addEventListener("click", generationFlow.cancelGeneration);
dropzoneRemoveButton?.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  generationFlow.removeSelectedFile();
});

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
quizEditorFields?.addEventListener("click", quizEditor.regenerateQuizQuestion);
saveQuizButton?.addEventListener("click", quizEditor.submitQuizEdits);
quizEditorFields?.addEventListener("click", (event) => {
  const cancelTarget = event.target instanceof Element
    ? event.target.closest('[data-editor-action="cancel-regenerate-question"]')
    : null;
  if (!cancelTarget) {
    return;
  }
  event.preventDefault();
  quizEditor.cancelActiveRegeneration();
});

bootstrapShell();
