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
import { createGenTiming } from "./gen-timing.js";
import { createQuizRenderer } from "./quiz-renderer.js";
import { createStageFlowController } from "./stage-flow.js";
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
const docInputWrap = document.getElementById("doc-input-wrap");
const docTextInput = document.getElementById("doc-text-input");
const docFilePill = document.getElementById("doc-file-pill");
const docFilePillName = document.getElementById("doc-file-pill-name");
const docFilePillMeta = document.getElementById("doc-file-pill-meta");
const docFileRemoveButton = document.getElementById("doc-file-remove");
const docClearButton = document.getElementById("doc-clear-button");
const docExampleButton = document.getElementById("doc-example-button");
const toastRegion = document.getElementById("toast-region");
const stepper = document.getElementById("stepper");
const generationProgressPanel = document.getElementById("generation-progress");
const cancelGenerationButton = document.getElementById("cancel-generation-button");
const generationTimerElement = document.getElementById("generation-timer");
const stageRoot = document.querySelector("[data-stage-root]");
const dropzoneFileName = document.getElementById("dropzone-file-name");
const dropzoneFileMeta = document.getElementById("dropzone-file-meta");
const dropzoneRemoveButton = document.getElementById("dropzone-remove");
const modelSelect = document.getElementById("generation-model");
const profileSelect = document.getElementById("generation-profile");
const exportSplitToggle = document.getElementById("export-split-toggle");
const exportSplitMenu = document.getElementById("export-split-menu");
const editorExportJsonButton = document.getElementById("editor-export-json-button");
const editorExportDocxButton = document.getElementById("editor-export-docx-button");
const editorExportPptxButton = document.getElementById("editor-export-pptx-button");
const editorExportSplitToggle = document.getElementById("editor-export-split-toggle");
const editorExportSplitMenu = document.getElementById("editor-export-split-menu");
const editorExportActions = document.getElementById("editor-export-actions");
const retryBackendButton = document.getElementById("retry-backend-button");
const retryProviderButton = document.getElementById("retry-provider-button");
const preflightStatus = document.getElementById("preflight-status");

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
    editorButton: editorExportJsonButton,
    editorHintId: "editor-export-json-hint",
  },
  docx: {
    button: exportDocxButton,
    hintId: "export-docx-hint",
    editorButton: editorExportDocxButton,
    editorHintId: "editor-export-docx-hint",
  },
  pptx: {
    button: exportPptxButton,
    hintId: "export-pptx-hint",
    editorButton: editorExportPptxButton,
    editorHintId: "editor-export-pptx-hint",
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
const GENERATION_CHECKING_MESSAGE =
  "Проверка подключений ещё не завершена. Дождитесь статусов сервера и LM Studio или нажмите кнопки проверки повторно.";
const BACKEND_GENERATION_BLOCKED_MESSAGE =
  "Backend недоступен. Запустите сервер командой .\\run-backend.ps1 и нажмите «Проверить сервер».";
const PROVIDER_GENERATION_BLOCKED_MESSAGE =
  "LM Studio недоступен. Запустите LM Studio, загрузите модель и нажмите «Проверить LM Studio».";
const SERVICES_GENERATION_BLOCKED_MESSAGE =
  "Генерация недоступна: backend и LM Studio не подключены. Запустите backend и LM Studio, затем повторите проверку подключений.";

const generationConnectionState = {
  backend: "checking",
  provider: "checking",
};

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
    container.dataset.statusTooltip = title;
    container.setAttribute("aria-label", title);
    if (tone) {
      container.dataset.statusTone = tone;
    } else {
      delete container.dataset.statusTone;
    }
  }
}

function setRetryButtonBusy(buttonElement, busy) {
  if (!buttonElement) {
    return;
  }
  buttonElement.disabled = Boolean(busy);
  if (busy) {
    buttonElement.dataset.busy = "true";
  } else {
    delete buttonElement.dataset.busy;
  }
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
  setToneMessage(document.getElementById("shell-log-message"), text, tone);
}

function setPreflightStatus(text, tone) {
  setToneMessage(preflightStatus, text, tone);
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
    toggleUnavailableHint(exportButton.editorButton, exportButton.editorHintId, !(hasQuiz && supported));
  }
  toggleUnavailableHint(editShortcutButton, "edit-shortcut-hint", !hasQuiz);
  if (exportSplitToggle) {
    exportSplitToggle.disabled = !hasQuiz;
  }
  if (editorExportSplitToggle) {
    editorExportSplitToggle.disabled = !hasQuiz;
  }
  if (editorExportActions) {
    editorExportActions.hidden = !hasQuiz;
  }
}

function createGenerationReadinessChecker() {
  return () => {
    const backendState = generationConnectionState.backend;
    const providerState = generationConnectionState.provider;
    const backendReady = backendState === "ok";
    const providerReady = providerState === "ok";
    if (backendReady && providerReady) {
      return { ready: true };
    }
    if (backendState === "checking" || providerState === "checking") {
      return { ready: false, message: GENERATION_CHECKING_MESSAGE, tone: "warn" };
    }
    if (!backendReady && !providerReady) {
      return { ready: false, message: SERVICES_GENERATION_BLOCKED_MESSAGE, tone: "bad" };
    }
    if (!backendReady) {
      return { ready: false, message: BACKEND_GENERATION_BLOCKED_MESSAGE, tone: "bad" };
    }
    return { ready: false, message: PROVIDER_GENERATION_BLOCKED_MESSAGE, tone: "bad" };
  };
}

const modalRegion = document.getElementById("modal-region");
const toastController = createToastController(toastRegion);
const confirmModal = createConfirmModal({ modalRegion });
const stageFlow = createStageFlowController({ root: stageRoot });
const progressController = createProgressController({ stepper, generationProgressPanel, stageFlow });
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

const genTiming = createGenTiming();
const generationFlow = createGenerationFlow({
  client,
  form,
  fileInput,
  docTextInput,
  docFilePill,
  docFilePillName,
  docFilePillMeta,
  docFileRemoveButton,
  docInputWrap,
  submitButton,
  dropzone,
  quizIdInput,
  cancelButton: cancelGenerationButton,
  timerElement: generationTimerElement,
  timerElapsedElement: document.getElementById("timer-elapsed"),
  timerEtaElement: document.getElementById("timer-eta"),
  timerEtaValueElement: document.getElementById("timer-eta-value"),
  charCountElement: document.getElementById("char-count"),
  genTiming,
  dropzoneFileName,
  dropzoneFileMeta,
  dropzoneRemoveButton,
  setTextContent,
  setPreflightStatus,
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
  getGenerationReadiness: createGenerationReadinessChecker(),
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
  generationFlow.updateDocInputSummary();
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
  generationConnectionState.backend = "checking";
  setPreflightStatus("", null);
  setStatus("backend", "Проверка…", null, "Проверяем доступность backend-сервера.");
  setRetryButtonBusy(retryBackendButton, true);
  try {
    const backendHealth = await client.getBackendHealth();
    generationConnectionState.backend = "ok";
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
    generationConnectionState.backend = "bad";
    generationConnectionState.provider = "blocked";
    setStatus("backend", "Проверка не удалась", "bad", BACKEND_CHECK_FAILED_INSTRUCTION);
    setLogMessage(`Не удалось подключиться к серверу: ${describeError(error)}. ${BACKEND_CHECK_FAILED_INSTRUCTION}`, "bad");
    setExportAvailability(editorState.lastGeneratedQuizId);
    return null;
  } finally {
    setRetryButtonBusy(retryBackendButton, false);
  }
}

async function checkProviderConnection() {
  if (generationConnectionState.backend !== "ok") {
    generationConnectionState.provider = "blocked";
    setPreflightStatus(PROVIDER_CHECK_BLOCKED_INSTRUCTION, "bad");
    setStatus("provider", "Недоступен · сначала сервер", "bad", PROVIDER_CHECK_BLOCKED_INSTRUCTION);
    setLogMessage(PROVIDER_CHECK_BLOCKED_INSTRUCTION, "bad");
    toastController.showToast(PROVIDER_CHECK_BLOCKED_INSTRUCTION, "bad");
    return null;
  }
  generationConnectionState.provider = "checking";
  setPreflightStatus("", null);
  setStatus("provider", "Проверка…", null, "Проверяем подключение к LM Studio через backend.");
  setRetryButtonBusy(retryProviderButton, true);
  try {
    const providerHealth = await client.getProviderHealth();
    if (providerHealth.status === "unavailable") {
      generationConnectionState.provider = "bad";
      setStatus("provider", "Недоступен · запустите LM Studio", "bad", LM_STUDIO_UNAVAILABLE_INSTRUCTION);
      setLogMessage(LM_STUDIO_UNAVAILABLE_INSTRUCTION, "bad");
      toastController.showToast(LM_STUDIO_UNAVAILABLE_INSTRUCTION, "bad");
    } else {
      generationConnectionState.provider = "ok";
      setPreflightStatus("", null);
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
    generationConnectionState.provider = "bad";
    setStatus("provider", "Проверка не удалась", "bad", PROVIDER_CHECK_FAILED_INSTRUCTION);
    setLogMessage(`Не удалось проверить LM Studio: ${describeError(error)}. ${PROVIDER_CHECK_FAILED_INSTRUCTION}`, "bad");
    return null;
  } finally {
    setRetryButtonBusy(retryProviderButton, false);
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
    stageFlow.activateStage("edit", { focus: true });
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
stepper?.addEventListener("click", (event) => {
  const target = event.target instanceof Element
    ? event.target.closest("[data-stage-target]")
    : null;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  progressController.advanceStepper(target.dataset.stageTarget, { focus: true });
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
exportSplitToggle?.addEventListener("click", () => {
  const open = exportSplitMenu?.hidden === false;
  if (exportSplitMenu) {
    exportSplitMenu.hidden = open;
  }
  if (exportSplitToggle) {
    exportSplitToggle.setAttribute("aria-expanded", String(!open));
  }
});
document.addEventListener("click", (event) => {
  if (exportSplitMenu?.hidden === false) {
    const inside = event.target instanceof Element && event.target.closest("#export-split");
    if (!inside) {
      exportSplitMenu.hidden = true;
      exportSplitToggle?.setAttribute("aria-expanded", "false");
    }
  }
});
editorExportJsonButton?.addEventListener("click", quizExporter.exportQuizAsJson);
editorExportDocxButton?.addEventListener("click", quizExporter.exportQuizAsDocx);
editorExportPptxButton?.addEventListener("click", quizExporter.exportQuizAsPptx);
editorExportSplitToggle?.addEventListener("click", () => {
  const open = editorExportSplitMenu?.hidden === false;
  if (editorExportSplitMenu) {
    editorExportSplitMenu.hidden = open;
  }
  if (editorExportSplitToggle) {
    editorExportSplitToggle.setAttribute("aria-expanded", String(!open));
  }
});
document.addEventListener("click", (event) => {
  if (editorExportSplitMenu?.hidden === false) {
    const inside = event.target instanceof Element && event.target.closest("#editor-export-split");
    if (!inside) {
      editorExportSplitMenu.hidden = true;
      editorExportSplitToggle?.setAttribute("aria-expanded", "false");
    }
  }
});
editShortcutButton?.addEventListener("click", openEditorForCurrentQuiz);
cancelGenerationButton?.addEventListener("click", generationFlow.cancelGeneration);
dropzoneRemoveButton?.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  generationFlow.removeSelectedFile();
});

docFileRemoveButton?.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  generationFlow.removeSelectedFile();
});

fileInput?.addEventListener("change", () => {
  generationFlow.updateDocInputSummary();
  if (fileInput.files?.[0]) {
    progressController.advanceStepper("setup");
  }
});

docTextInput?.addEventListener("input", () => {
  generationFlow.updateDocInputSummary();
});

const DOC_EXAMPLE_TEXT = `Фотосинтез — процесс, при котором растения, водоросли и некоторые бактерии преобразуют световую энергию в химическую. В ходе реакции углекислый газ (CO₂) и вода (H₂O) под действием солнечного света превращаются в глюкозу и кислород. Реакция протекает в хлоропластах, содержащих пигмент хлорофилл, который поглощает красный и синий диапазоны спектра. Выделяемый кислород является побочным продуктом расщепления молекул воды. Фотосинтез лежит в основе почти всех пищевых цепочек на Земле и обеспечивает кислородный состав атмосферы.`;

docClearButton?.addEventListener("click", () => {
  if (docTextInput) {
    docTextInput.value = "";
  }
  if (fileInput) {
    try {
      fileInput.value = "";
      if (typeof DataTransfer === "function") {
        fileInput.files = new DataTransfer().files;
      }
    } catch (_e) {
      fileInput.value = "";
    }
  }
  generationFlow.updateDocInputSummary();
  toastController.showToast("Текст удалён из формы.", "warn");
  docTextInput?.focus();
});

docExampleButton?.addEventListener("click", () => {
  if (docTextInput) {
    docTextInput.value = DOC_EXAMPLE_TEXT;
    docTextInput.dispatchEvent(new Event("input"));
    docTextInput.focus();
  }
});

form?.addEventListener("submit", generationFlow.submitGeneration);
quizEditorLoader?.addEventListener("submit", quizEditor.loadQuizForEditing);
quizEditorFields?.addEventListener("input", quizEditor.markEditorDirty);
quizEditorFields?.addEventListener("change", quizEditor.markEditorDirty);
quizEditorFields?.addEventListener("click", quizEditor.regenerateQuizQuestion);
quizEditorFields?.addEventListener("click", quizEditor.revertQuestionEdits);
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

stageFlow.activateStage("setup");
bootstrapShell();
