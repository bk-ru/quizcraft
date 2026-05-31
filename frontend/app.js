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
import { createSidebarController } from "./sidebar.js";
import { createStageFlowController } from "./stage-flow.js";
import { createThemeController } from "./theme.js";
import { createToastController } from "./toast.js";
import { describeError, describeValidationError } from "./validation-errors.js";
import { createWorkspaceController } from "./workspace.js";

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
const exportMarkdownButton = document.getElementById("export-markdown-button");
const exportCsvButton = document.getElementById("export-csv-button");
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
const documentDropOverlay = document.getElementById("document-drop-overlay");
const toastRegion = document.getElementById("toast-region");
const stepper = document.getElementById("stepper");
const generationProgressPanel = document.getElementById("generation-progress");
const generationLiveJournal = document.getElementById("generation-live-journal");
const cancelGenerationButton = document.getElementById("cancel-generation-button");
const generationTimerElement = document.getElementById("generation-timer");
const stageRoot = document.querySelector("[data-stage-root]");
const dropzoneFileName = document.getElementById("dropzone-file-name");
const dropzoneFileMeta = document.getElementById("dropzone-file-meta");
const dropzoneRemoveButton = document.getElementById("dropzone-remove");
const modelSelect = document.getElementById("generation-model");
const profileSelect = document.getElementById("generation-profile");
const generationTemperatureInput = document.getElementById("generation-temperature");
const generationTemperatureValue = document.getElementById("generation-temperature-value");
const questionCountRange = document.getElementById("question-count-range");
const questionCountInput = document.getElementById("question-count");
const generationEstimate = document.getElementById("generation-estimate");
const exportSplitToggle = document.getElementById("export-split-toggle");
const exportSplitMenu = document.getElementById("export-split-menu");
const editorExportJsonButton = document.getElementById("editor-export-json-button");
const editorExportDocxButton = document.getElementById("editor-export-docx-button");
const editorExportPptxButton = document.getElementById("editor-export-pptx-button");
const editorExportMarkdownButton = document.getElementById("editor-export-markdown-button");
const editorExportCsvButton = document.getElementById("editor-export-csv-button");
const editorExportSplitToggle = document.getElementById("editor-export-split-toggle");
const editorExportSplitMenu = document.getElementById("editor-export-split-menu");
const editorExportActions = document.getElementById("editor-export-actions");
const retryBackendButton = document.getElementById("retry-backend-button");
const retryProviderButton = document.getElementById("retry-provider-button");
const preflightStatus = document.getElementById("preflight-status");
const lmStudioHostInput = document.getElementById("lm-studio-host");
const lmStudioPortInput = document.getElementById("lm-studio-port");
const applyLMStudioConnectionButton = document.getElementById("apply-lm-studio-connection");
const lmStudioConnectionStatus = document.getElementById("lm-studio-connection-status");
const lmStudioConnectionSection = document.getElementById("lm-studio-connection-section");
const lmStudioProviderHint = document.getElementById("lm-studio-provider-hint");
const providerModelStatus = document.getElementById("provider-model-status");
const workspaceRoot = document.querySelector(".compact-workspace");
const workspaceSidebar = document.getElementById("workspace-sidebar");
const sidebarToggleButton = document.getElementById("sidebar-toggle");
const sidebarNewQuizButton = document.getElementById("sidebar-new-quiz");
const sidebarHistoryList = document.getElementById("sidebar-history-list");
const sidebarStatusCell = document.getElementById("sidebar-status-cell");

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
  markdown: {
    button: exportMarkdownButton,
    hintId: "export-markdown-hint",
    editorButton: editorExportMarkdownButton,
    editorHintId: "editor-export-markdown-hint",
  },
  csv: {
    button: exportCsvButton,
    hintId: "export-csv-hint",
    editorButton: editorExportCsvButton,
    editorHintId: "editor-export-csv-hint",
  },
});

const statusMap = {
  ok: "ok",
  available: "ok",
  unavailable: "bad",
  disabled: "bad",
  bad: "bad",
};

const PROVIDER_DISPLAY_NAMES = Object.freeze({
  lm_studio: "LM Studio",
  ollama: "Ollama",
  external_api: "External API",
});
const LM_STUDIO_CONNECTION_STORAGE_KEY = "quizcraft.lmStudioConnection";
const PROVIDER_AVAILABLE_TEXT = "Доступен";

const PROVIDER_UNAVAILABLE_INSTRUCTION =
  "Провайдер недоступен. Проверьте активный провайдер, загрузите настроенную модель и повторите проверку подключения.";
const BACKEND_AVAILABLE_INSTRUCTION =
  "Backend отвечает. Если генерация не запускается, проверьте активный провайдер и настроенную модель.";
const BACKEND_CHECK_FAILED_INSTRUCTION =
  "Backend недоступен. Запустите сервер командой .\\run-backend.ps1 из корня проекта и проверьте, что порт 8000 свободен.";
const PROVIDER_AVAILABLE_INSTRUCTION =
  "Подключение к программе с ИИ-моделью проверено. Можно запускать генерацию.";
const PROVIDER_CHECK_FAILED_INSTRUCTION =
  "Провайдер не удалось проверить через backend. Убедитесь, что backend запущен, активный провайдер доступен и модель загружена.";
const PROVIDER_CHECK_BLOCKED_INSTRUCTION =
  "Провайдер проверяется через backend. Сначала восстановите подключение к серверу.";
const GENERATION_CHECKING_MESSAGE =
  "Проверка подключений ещё не завершена. Дождитесь статусов сервера и провайдера или нажмите кнопки проверки повторно.";
const BACKEND_GENERATION_BLOCKED_MESSAGE =
  "Backend недоступен. Запустите сервер командой .\\run-backend.ps1 и нажмите «Проверить сервер».";
const PROVIDER_GENERATION_BLOCKED_MESSAGE =
  "Провайдер недоступен. Проверьте активный провайдер, загрузите модель и нажмите «Проверить провайдер».";
const SERVICES_GENERATION_BLOCKED_MESSAGE =
  "Генерация недоступна: backend и провайдер не подключены. Запустите backend и активный провайдер, затем повторите проверку подключений.";

const generationConnectionState = {
  backend: "checking",
  provider: "checking",
  backendReason: "",
  providerReason: "",
  providerKey: "",
  providerName: "Провайдер",
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

function formatProviderName(providerName) {
  const normalized = typeof providerName === "string" ? providerName.trim().toLowerCase() : "";
  return PROVIDER_DISPLAY_NAMES[normalized] ?? "Провайдер";
}

function isProviderReadyStatus(status) {
  return status === "available" || status === "ok";
}

function buildBackendUnavailableMessage(reason = "") {
  return [
    "Сервер недоступен",
    `Причина: ${reason || "backend не отвечает на запрос проверки."}`,
    "Что сделать:",
    "1. Запустите backend командой .\\run-backend.ps1 из корня проекта",
    `2. Проверьте, что ${backendBaseUrl} доступен в браузере`,
    "3. Проверьте backendBaseUrl в frontend/config.js",
    '4. Нажмите "Проверить снова"',
  ].join("\n");
}

function buildProviderRecoverySteps(providerKey) {
  if (providerKey === "ollama") {
    return [
      "1. Запустите Ollama",
      "2. Проверьте, что выбранная модель скачана и доступна",
      "3. Проверьте OLLAMA_BASE_URL в .env",
      '4. Нажмите "Проверить снова"',
    ];
  }
  if (providerKey === "external_api") {
    return [
      "1. Проверьте доступ к внешнему API",
      "2. Проверьте API-ключ и базовый URL в .env",
      "3. Проверьте имя модели в настройках",
      '4. Нажмите "Проверить снова"',
    ];
  }
  return [
    "1. Откройте LM Studio",
    "2. Запустите Local Server",
    "3. Проверьте LM_STUDIO_BASE_URL в .env",
    '4. Нажмите "Проверить снова"',
  ];
}

function buildProviderUnavailableMessage(reason = "", providerKey = generationConnectionState.providerKey) {
  return [
    "Провайдер недоступен",
    `Причина: ${reason || "активный провайдер не отвечает на запрос проверки."}`,
    "Что сделать:",
    ...buildProviderRecoverySteps(providerKey),
  ].join("\n");
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

function setLMStudioConnectionStatus(text, tone) {
  setToneMessage(lmStudioConnectionStatus, text, tone);
}

function setEditorStatus(text, tone) {
  setToneMessage(document.getElementById("quiz-editor-status"), text, tone);
}

function readStoredLMStudioConnection() {
  try {
    const raw = window.localStorage?.getItem(LM_STUDIO_CONNECTION_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (typeof parsed?.host !== "string" || !Number.isFinite(Number(parsed?.port))) {
      return null;
    }
    return { host: parsed.host, port: Number(parsed.port) };
  } catch {
    return null;
  }
}

function storeLMStudioConnection(connection) {
  try {
    window.localStorage?.setItem(LM_STUDIO_CONNECTION_STORAGE_KEY, JSON.stringify(connection));
  } catch {
    // localStorage may be blocked in private or file-based browser contexts.
  }
}

function fillLMStudioConnectionForm(connection) {
  if (!connection) {
    return;
  }
  if (lmStudioHostInput && typeof connection.host === "string") {
    lmStudioHostInput.value = connection.host;
  }
  if (lmStudioPortInput && Number.isFinite(Number(connection.port))) {
    lmStudioPortInput.value = String(connection.port);
  }
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

function getCurrentGenerationReadiness() {
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
  if (!backendReady) {
    const message = generationConnectionState.backendReason
      ? buildBackendUnavailableMessage(generationConnectionState.backendReason)
      : BACKEND_GENERATION_BLOCKED_MESSAGE;
    return { ready: false, message, tone: "bad" };
  }
  if (!providerReady) {
    const message = generationConnectionState.providerReason
      ? buildProviderUnavailableMessage(generationConnectionState.providerReason, generationConnectionState.providerKey)
      : PROVIDER_GENERATION_BLOCKED_MESSAGE;
    return { ready: false, message, tone: "bad" };
  }
  return { ready: false, message: SERVICES_GENERATION_BLOCKED_MESSAGE, tone: "bad" };
}

function updateGenerationSubmitAvailability() {
  if (!submitButton) {
    return;
  }
  const readiness = getCurrentGenerationReadiness();
  if (!readiness.ready && readiness.tone === "bad") {
    submitButton.setAttribute("aria-disabled", "true");
    submitButton.dataset.disabledReason = readiness.message;
    submitButton.title = readiness.message;
  } else {
    submitButton.removeAttribute("aria-disabled");
    delete submitButton.dataset.disabledReason;
    submitButton.removeAttribute("title");
  }
}

function showSubmitUnavailableReason() {
  const reason = submitButton?.dataset.disabledReason;
  if (!reason) {
    return;
  }
  setPreflightStatus(reason, "bad");
}

function createGenerationReadinessChecker() {
  return getCurrentGenerationReadiness;
}

const modalRegion = document.getElementById("modal-region");
const toastController = createToastController(toastRegion);
const confirmModal = createConfirmModal({ modalRegion });
const stageFlow = createStageFlowController({ root: stageRoot });
const workspaceController = createWorkspaceController({ root: workspaceRoot, stageFlow });
const progressController = createProgressController({ stepper, generationProgressPanel, stageFlow });
const themeController = createThemeController({ themeToggleLabel });
const quizHistory = createQuizHistory({
  datalistElement: document.getElementById("quiz-history-options"),
});
quizHistory.renderHistoryDatalist();
const enableModelPicker = Boolean(config.enableModelPicker);
const modelPickerField = document.getElementById("model-picker-field");
const genTiming = createGenTiming();

if (enableModelPicker && modelPickerField) {
  modelPickerField.hidden = false;
}

function syncGenerationTemperatureValue() {
  if (!generationTemperatureInput || !generationTemperatureValue) {
    return;
  }
  generationTemperatureValue.value = Number(generationTemperatureInput.value).toFixed(1);
}

function syncQuestionCount(source = questionCountInput, target = questionCountRange) {
  if (!source || !target) {
    return;
  }
  const parsedValue = Number.parseInt(source.value, 10);
  const normalizedValue = Number.isInteger(parsedValue) ? Math.min(50, Math.max(3, parsedValue)) : 5;
  source.value = String(normalizedValue);
  target.value = String(normalizedValue);
}

function formatEstimateDuration(durationMs) {
  const seconds = Math.max(1, Math.round(durationMs / 1000));
  if (seconds < 60) {
    return `около ${seconds} сек.`;
  }
  return `около ${Math.ceil(seconds / 60)} мин.`;
}

function updateGenerationEstimate() {
  if (!generationEstimate) {
    return;
  }
  if (fileInput?.files?.[0]) {
    generationEstimate.textContent = "Оценка времени уточнится после загрузки документа.";
    return;
  }
  const charCount = docTextInput?.value?.trim().length ?? 0;
  const totalMs = genTiming.estimateTotalMs(charCount);
  generationEstimate.textContent = totalMs
    ? `Оценка времени генерации: ${formatEstimateDuration(totalMs)}`
    : "";
}

function updateLMStudioConnectionVisibility(providerKey = generationConnectionState.providerKey) {
  const isLMStudio = providerKey === "lm_studio";
  if (lmStudioConnectionSection) {
    lmStudioConnectionSection.hidden = !isLMStudio;
  }
  if (lmStudioProviderHint) {
    lmStudioProviderHint.hidden = isLMStudio;
  }
}

function updateProviderModelStatus(defaultModel = "", models = []) {
  if (!providerModelStatus) {
    return;
  }
  const availableModels = Array.isArray(models) ? models.filter(Boolean) : [];
  const defaultModelLabel = typeof defaultModel === "string" && defaultModel.trim()
    ? `Модель по умолчанию: ${defaultModel.trim()}.`
    : "Модель по умолчанию не указана.";
  providerModelStatus.textContent = availableModels.length > 0
    ? `${defaultModelLabel} Доступные модели: ${availableModels.join(", ")}`
    : defaultModelLabel;
}

syncGenerationTemperatureValue();
generationTemperatureInput?.addEventListener("input", syncGenerationTemperatureValue);
syncQuestionCount();
updateGenerationEstimate();
updateLMStudioConnectionVisibility();
questionCountRange?.addEventListener("input", () => {
  syncQuestionCount(questionCountRange, questionCountInput);
  updateGenerationEstimate();
});
questionCountInput?.addEventListener("change", () => {
  syncQuestionCount(questionCountInput, questionCountRange);
  updateGenerationEstimate();
});

const generationSettings = createGenerationSettingsController({
  client,
  modelSelect,
  profileSelect,
  setLogMessage,
  enableModelPicker,
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
  docTextInput,
  docFilePill,
  docFilePillName,
  docFilePillMeta,
  docFileRemoveButton,
  docInputWrap,
  documentDropOverlay,
  submitButton,
  dropzone,
  quizIdInput,
  liveJournalElement: generationLiveJournal,
  liveJournalContainer: document.querySelector(".generation-live-journal"),
  cancelButton: cancelGenerationButton,
  timerElement: generationTimerElement,
  timerElapsedElement: document.getElementById("timer-elapsed"),
  timerEtaElement: document.getElementById("timer-eta"),
  timerEtaValueElement: document.getElementById("timer-eta-value"),
  charCountElement: document.getElementById("char-count"),
  docLengthHintElement: document.getElementById("doc-length-hint"),
  onDocInputSummaryChange: updateGenerationEstimate,
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
  applyBackendGenerationStatusEvidence: progressController.applyBackendGenerationStatusEvidence,
  completeGenerationProgress: progressController.completeGenerationProgress,
  completeGenerationProgressWithBackendEvidence: progressController.completeGenerationProgressWithBackendEvidence,
  failGenerationProgress: progressController.failGenerationProgress,
  showToast: toastController.showToast,
  saveQuizToHistory: quizHistory.saveQuizToHistory,
  refreshGenerationDefaults: generationSettings.refreshAfterGeneration,
  getGenerationReadiness: createGenerationReadinessChecker(),
  enableModelPicker,
});

const quizExporter = createQuizExporter({
  backendBaseUrl,
  client,
  editorState,
  showToast: toastController.showToast,
});

async function startNewQuiz() {
  if (editorState.isDirty) {
    const confirmed = await confirmModal.confirm({
      title: "Начать новый квиз?",
      body: "Несохранённые изменения текущего квиза будут потеряны.",
      confirmLabel: "Начать новый квиз",
      cancelLabel: "Продолжить редактирование",
      tone: "warn",
    });
    if (!confirmed) {
      return false;
    }
  }
  if (docTextInput) {
    docTextInput.value = "";
  }
  generationFlow.removeSelectedFile();
  generationFlow.updateDocInputSummary();
  quizRenderer.clearQuizResult();
  quizEditor.clearQuizEditor();
  editorState.isDirty = false;
  setExportAvailability(null);
  quizRenderer.setResultState("Квиз появится здесь после успешной генерации.", "idle", "Ожидание результата");
  workspaceController.activateState("setup", { focus: true });
  docTextInput?.focus();
  return true;
}

async function openQuizFromHistory(quizId) {
  if (typeof quizId !== "string" || !quizId.trim()) {
    return;
  }
  try {
    const payload = await client.getQuiz(quizId);
    const normalizedQuizId = payload.quiz_id ?? payload.quiz?.quiz_id ?? quizId;
    if (quizIdInput) {
      quizIdInput.value = normalizedQuizId;
    }
    quizRenderer.renderQuizResult({
      ...payload,
      quiz_id: normalizedQuizId,
      quiz: payload.quiz ?? {},
    });
    quizHistory.saveQuizToHistory({
      quiz_id: normalizedQuizId,
      title: payload.quiz?.title,
      language: payload.language,
    });
    workspaceController.activateState("result", { focus: true });
    toastController.showToast("Квиз загружен из истории.", "ok");
  } catch (error) {
    toastController.showToast(`Не удалось открыть квиз из истории: ${describeError(error)}`, "bad");
  }
}

const sidebarController = createSidebarController({
  sidebar: workspaceSidebar,
  toggleButton: sidebarToggleButton,
  newQuizButton: sidebarNewQuizButton,
  historyList: sidebarHistoryList,
  statusCell: sidebarStatusCell,
  themeButton: themeToggleButton,
  historyStore: quizHistory,
  onNewQuiz: startNewQuiz,
  onSelectQuiz: openQuizFromHistory,
  onOpenStatus: () => workspaceController.openModal("status"),
  onToggleTheme: themeController.cycleTheme,
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
  await loadLMStudioConnectionSettings();
  await checkProviderConnection();
  await loadExportFormats();
}

async function checkBackendConnection({ loadExports = true, refreshSettings = true } = {}) {
  generationConnectionState.backend = "checking";
  generationConnectionState.backendReason = "";
  updateGenerationSubmitAvailability();
  setPreflightStatus("", null);
  setStatus("backend", "Проверка…", null, "Проверяем доступность backend-сервера.");
  setRetryButtonBusy(retryBackendButton, true);
  try {
    const backendHealth = await client.getBackendHealth();
    generationConnectionState.backend = "ok";
    generationConnectionState.backendReason = "";
    generationConnectionState.providerKey = backendHealth.default_provider ?? generationConnectionState.providerKey;
    generationConnectionState.providerName = formatProviderName(generationConnectionState.providerKey);
    updateLMStudioConnectionVisibility();
    setStatus(
      "backend",
      "Доступен",
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
    const reason = describeError(error);
    generationConnectionState.backend = "bad";
    generationConnectionState.provider = "blocked";
    generationConnectionState.backendReason = reason;
    generationConnectionState.providerReason = "Сначала восстановите подключение к серверу.";
    updateProviderModelStatus();
    const message = buildBackendUnavailableMessage(reason);
    setStatus("backend", "Проверка не удалась", "bad", message);
    setLogMessage(message, "bad");
    setExportAvailability(editorState.lastGeneratedQuizId);
    return null;
  } finally {
    setRetryButtonBusy(retryBackendButton, false);
    updateGenerationSubmitAvailability();
  }
}

async function checkProviderConnection() {
  if (generationConnectionState.backend !== "ok") {
    generationConnectionState.provider = "blocked";
    generationConnectionState.providerReason = "Сначала восстановите подключение к серверу.";
    updateProviderModelStatus();
    setPreflightStatus(PROVIDER_CHECK_BLOCKED_INSTRUCTION, "bad");
    setStatus("provider", "Недоступен · сначала сервер", "bad", PROVIDER_CHECK_BLOCKED_INSTRUCTION);
    setLogMessage(PROVIDER_CHECK_BLOCKED_INSTRUCTION, "bad");
    toastController.showToast(PROVIDER_CHECK_BLOCKED_INSTRUCTION, "bad");
    updateGenerationSubmitAvailability();
    return null;
  }
  generationConnectionState.provider = "checking";
  generationConnectionState.providerReason = "";
  updateProviderModelStatus();
  updateGenerationSubmitAvailability();
  setPreflightStatus("", null);
  setStatus("provider", "Проверка…", null, "Проверяем подключение к активному провайдеру через backend.");
  setRetryButtonBusy(retryProviderButton, true);
  try {
    const providerHealth = await client.getProviderHealth();
    const providerName = formatProviderName(providerHealth.provider);
    generationConnectionState.providerKey = providerHealth.provider ?? generationConnectionState.providerKey;
    generationConnectionState.providerName = providerName;
    updateLMStudioConnectionVisibility();
    updateProviderModelStatus(providerHealth.default_model, providerHealth.available_models);
    if (!isProviderReadyStatus(providerHealth.status)) {
      generationConnectionState.provider = "bad";
      generationConnectionState.providerReason = providerHealth.message || `status: ${providerHealth.status}`;
      const message = buildProviderUnavailableMessage(generationConnectionState.providerReason, generationConnectionState.providerKey);
      setStatus("provider", "Недоступен · проверьте провайдер", "bad", message);
      setLogMessage(message, "bad");
      toastController.showToast(message, "bad");
    } else {
      generationConnectionState.provider = "ok";
      generationConnectionState.providerReason = "";
      setPreflightStatus("", null);
      setStatus(
        "provider",
        PROVIDER_AVAILABLE_TEXT,
        statusMap[providerHealth.status] ?? "warn",
        PROVIDER_AVAILABLE_INSTRUCTION,
      );
      setLogMessage("Подключение к провайдеру проверено.", "ok");
      if (Array.isArray(providerHealth.available_models) && providerHealth.available_models.length > 0) {
        generationSettings.updateAvailableModels(providerHealth.available_models);
      }
    }
    return providerHealth;
  } catch (error) {
    const reason = describeError(error);
    generationConnectionState.provider = "bad";
    generationConnectionState.providerReason = reason;
    const message = buildProviderUnavailableMessage(reason, generationConnectionState.providerKey);
    setStatus("provider", "Проверка не удалась", "bad", message);
    setLogMessage(message, "bad");
    return null;
  } finally {
    setRetryButtonBusy(retryProviderButton, false);
    updateGenerationSubmitAvailability();
  }
}

async function loadLMStudioConnectionSettings() {
  const storedConnection = readStoredLMStudioConnection();
  if (storedConnection) {
    fillLMStudioConnectionForm(storedConnection);
  }
  if (!client || typeof client.getLMStudioConnection !== "function") {
    return null;
  }
  try {
    const connection = await client.getLMStudioConnection();
    if (!storedConnection) {
      fillLMStudioConnectionForm(connection);
    }
    setLMStudioConnectionStatus(`Текущий адрес: ${connection.base_url}`, "ok");
    return connection;
  } catch (error) {
    setLMStudioConnectionStatus(`Не удалось получить адрес LM Studio: ${describeError(error)}`, "warn");
    return null;
  }
}

async function applyLMStudioConnectionSettings() {
  const host = lmStudioHostInput?.value?.trim() ?? "";
  const port = Number(lmStudioPortInput?.value);
  if (!host || !Number.isInteger(port) || port < 1 || port > 65535) {
    setLMStudioConnectionStatus("Введите IP/host и порт LM Studio от 1 до 65535.", "bad");
    return;
  }
  if (host.includes("://") || /[/?#@:\\]/.test(host)) {
    setLMStudioConnectionStatus("Введите только IP или host без http://, /v1 и порта.", "bad");
    return;
  }
  setRetryButtonBusy(applyLMStudioConnectionButton, true);
  setLMStudioConnectionStatus("Применяем адрес LM Studio…", "warn");
  try {
    const connection = await client.putLMStudioConnection({ host, port });
    fillLMStudioConnectionForm(connection);
    storeLMStudioConnection({ host: connection.host, port: connection.port });
    generationConnectionState.providerKey = "lm_studio";
    generationConnectionState.providerName = "LM Studio";
    updateLMStudioConnectionVisibility();
    if (isProviderReadyStatus(connection.status)) {
      generationConnectionState.provider = "ok";
      generationConnectionState.providerReason = "";
      setStatus(
        "provider",
        PROVIDER_AVAILABLE_TEXT,
        statusMap[connection.status] ?? "ok",
        PROVIDER_AVAILABLE_INSTRUCTION,
      );
      setPreflightStatus("", null);
      setLMStudioConnectionStatus(`LM Studio подключён: ${connection.base_url}`, "ok");
      setLogMessage("Адрес LM Studio применён.", "ok");
    } else {
      generationConnectionState.provider = "bad";
      generationConnectionState.providerReason = connection.message || `status: ${connection.status}`;
      const message = buildProviderUnavailableMessage(generationConnectionState.providerReason, "lm_studio");
      setStatus("provider", "Недоступен · проверьте LM Studio", "bad", message);
      setLMStudioConnectionStatus(message, "bad");
      setLogMessage(message, "bad");
    }
  } catch (error) {
    generationConnectionState.provider = "bad";
    generationConnectionState.providerReason = describeError(error);
    const message = buildProviderUnavailableMessage(generationConnectionState.providerReason, "lm_studio");
    setLMStudioConnectionStatus(message, "bad");
    setLogMessage(message, "bad");
  } finally {
    setRetryButtonBusy(applyLMStudioConnectionButton, false);
    updateGenerationSubmitAvailability();
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
workspaceController.register();
sidebarController.register();
retryBackendButton?.addEventListener("click", () => {
  checkBackendConnection();
});
retryProviderButton?.addEventListener("click", () => {
  checkProviderConnection();
});
applyLMStudioConnectionButton?.addEventListener("click", () => {
  applyLMStudioConnectionSettings();
});
submitButton?.addEventListener("pointerenter", showSubmitUnavailableReason);
submitButton?.addEventListener("focus", showSubmitUnavailableReason);
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
exportMarkdownButton?.addEventListener("click", quizExporter.exportQuizAsMarkdown);
exportCsvButton?.addEventListener("click", quizExporter.exportQuizAsCsv);
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
editorExportMarkdownButton?.addEventListener("click", quizExporter.exportQuizAsMarkdown);
editorExportCsvButton?.addEventListener("click", quizExporter.exportQuizAsCsv);
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

const DOC_EXAMPLE_TEXT = `Фотосинтез — это процесс, при котором зелёные растения, водоросли и некоторые бактерии создают органические вещества из углекислого газа и воды, используя энергию света. Его часто называют основой жизни на Земле, потому что именно благодаря фотосинтезу в биосфере постоянно образуются углеводы и выделяется кислород. Без этого процесса большинство животных, грибов и людей не имели бы ни пищи, ни достаточного количества кислорода для дыхания.

У растений фотосинтез происходит главным образом в листьях. Лист приспособлен к поглощению света: он обычно имеет широкую и тонкую пластинку, через которую лучи легко проникают к внутренним клеткам. В клетках листа находятся хлоропласты — особые органоиды, содержащие зелёный пигмент хлорофилл. Хлорофилл поглощает прежде всего красные и синие лучи солнечного спектра, а зелёные отражает, поэтому листья кажутся зелёными.

Для фотосинтеза необходимы три основные исходные составляющие: свет, вода и углекислый газ. Вода поступает в растение из почвы через корни, затем поднимается по проводящим тканям к листьям. Углекислый газ поступает из воздуха через устьица — маленькие отверстия в кожице листа. Через устьица также выходит кислород и испаряется водяной пар. Если устьица закрываются из-за жары или недостатка воды, поступление углекислого газа уменьшается, и скорость фотосинтеза падает.

Процесс фотосинтеза условно делят на две стадии: световую и темновую. Световая стадия протекает на мембранах тилакоидов внутри хлоропластов и требует света. В это время энергия света превращается в химическую энергию, запасаемую в молекулах АТФ и НАДФН. Одновременно происходит фотолиз воды: молекулы воды расщепляются, в результате чего образуются электроны, протоны и кислород. Именно кислород световой стадии выходит в атмосферу.

Темновая стадия, или цикл Кальвина, происходит в строме хлоропласта. Она не требует прямого света, но использует АТФ и НАДФН, полученные на световой стадии. На этой стадии углекислый газ включается в цепочку реакций и постепенно превращается в углеводы. Главным первичным продуктом можно считать простые сахара, из которых затем образуются глюкоза, крахмал, целлюлоза и другие органические соединения. Поэтому фотосинтез не только выделяет кислород, но и создаёт строительный материал для роста растения.

Общее уравнение фотосинтеза часто записывают так: 6CO₂ + 6H₂O + световая энергия → C₆H₁₂O₆ + 6O₂. Эта запись показывает, что из шести молекул углекислого газа и шести молекул воды при участии света образуется одна молекула глюкозы и шесть молекул кислорода. Однако реальный процесс состоит из большого числа последовательных реакций, поэтому уравнение является только общей схемой.

На скорость фотосинтеза влияют освещённость, концентрация углекислого газа, температура, обеспеченность водой и минеральное питание. При слабом освещении растение получает мало энергии, поэтому образование органических веществ идёт медленно. При увеличении освещённости скорость фотосинтеза сначала растёт, но затем достигает предела: другие факторы становятся ограничивающими. Слишком высокая температура может нарушать работу ферментов, а слишком низкая замедляет реакции. Недостаток воды приводит к закрытию устьиц и уменьшает поглощение углекислого газа.

Фотосинтез тесно связан с дыханием растений, но эти процессы нельзя считать одинаковыми. При дыхании органические вещества расщепляются, кислород поглощается, а энергия высвобождается для нужд клетки. При фотосинтезе, наоборот, энергия света запасается в органических веществах, а кислород выделяется. Днём в зелёных частях растения обычно преобладает фотосинтез, а ночью, когда света нет, продолжается только дыхание.

Значение фотосинтеза выходит далеко за пределы одного растения. Он поддерживает газовый состав атмосферы, снижает количество углекислого газа и пополняет запасы кислорода. Органические вещества, созданные растениями, служат пищей травоядным животным, а затем переходят по пищевым цепям к хищникам и разрушителям. Даже ископаемое топливо, такое как уголь, нефть и природный газ, связано с древней органикой, накопленной в результате фотосинтеза.

Разные группы организмов используют фотосинтез не одинаково. У высших растений и водорослей он сопровождается выделением кислорода, поэтому называется кислородным. У некоторых бактерий встречается бескислородный фотосинтез: они используют не воду, а другие вещества, например сероводород, и кислород при этом не выделяют. Это показывает, что фотосинтез является не одним простым действием, а сложным набором биохимических путей.

Понимание фотосинтеза важно для сельского хозяйства и экологии. Зная, какие факторы ограничивают этот процесс, человек может повышать урожайность: регулировать освещение в теплицах, поддерживать влажность почвы, обеспечивать растения минеральными веществами и контролировать содержание углекислого газа. В то же время уничтожение лесов и загрязнение среды уменьшают способность экосистем связывать углекислый газ. Поэтому сохранение растений и водорослей имеет значение не только для природы, но и для устойчивости жизни человека.Точный анализ этих связей помогает понять обмен веществ в экосистемах Земли.
`;

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

workspaceController.activateState("setup");
updateGenerationSubmitAvailability();
bootstrapShell();
