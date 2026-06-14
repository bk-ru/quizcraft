import { QuizCraftApiClient } from "./api/client.js";
import { createQuizExporter } from "./download.js";
import { createExportModal } from "./export-modal.js";
import { createCopyButtonController } from "./copy.js";
import { createGenerationFlow } from "./generation-flow.js";
import { createGenerationSettingsController } from "./generation-settings.js";
import { createKeyboardShortcuts } from "./keyboard.js";
import { createConfirmModal } from "./modal.js";
import { createProgressController } from "./progress.js";
import { createPlayablePreview } from "./preview-mode.js";
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
const backendBaseUrl =
  typeof config.backendBaseUrl === "string" && config.backendBaseUrl.trim()
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
const quizTitleInput = document.getElementById("quiz-title");
const loadQuizButton = document.getElementById("load-quiz-button");
const saveQuizButton = document.getElementById("save-quiz-button");
const quizEditorFields = document.getElementById("quiz-editor-fields");
const undoQuizEditButton = document.getElementById("undo-quiz-edit-button");
const addQuestionButton = document.getElementById("add-question-button");
const addQuestionTypeSelect = document.getElementById("add-question-type");
const previewQuizButton = document.getElementById("preview-quiz-button");
const exportJsonButton = document.getElementById("export-json-button");
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
const generationProgressPanel = document.getElementById("generation-progress");
const generationLiveJournal = document.getElementById(
  "generation-live-journal",
);
const cancelGenerationButton = document.getElementById(
  "cancel-generation-button",
);
const generationTimerElement = document.getElementById("generation-timer");
const stageRoot = document.querySelector("[data-stage-root]");
const dropzoneFileName = document.getElementById("dropzone-file-name");
const dropzoneFileMeta = document.getElementById("dropzone-file-meta");
const dropzoneRemoveButton = document.getElementById("dropzone-remove");
const modelSelect = document.getElementById("generation-model");
const profileSelect = document.getElementById("generation-profile");
const generationTemperatureInput = document.getElementById(
  "generation-temperature",
);
const generationTemperatureValue = document.getElementById(
  "generation-temperature-value",
);
const questionCountRange = document.getElementById("question-count-range");
const questionCountInput = document.getElementById("question-count");
const generationEstimate = document.getElementById("generation-estimate");
const difficultySelect = document.getElementById("difficulty");
const difficultyButtons = [
  ...document.querySelectorAll("[data-difficulty-value]"),
];
const wordCountElement = document.getElementById("word-count");
const wordCountSummaryElement = document.getElementById("word-count-summary");
const charCountTopElement = document.getElementById("char-count-top");
const resultBackButton = document.getElementById("result-back-button");
const retryBackendButton = document.getElementById("retry-backend-button");
const retryProviderButton = document.getElementById("retry-provider-button");
const preflightStatus = document.getElementById("preflight-status");
const lmStudioHostInput = document.getElementById("lm-studio-host");
const lmStudioPortInput = document.getElementById("lm-studio-port");
const applyLMStudioConnectionButton = document.getElementById(
  "apply-lm-studio-connection",
);
const lmStudioConnectionStatus = document.getElementById(
  "lm-studio-connection-status",
);
const lmStudioConnectionSection = document.getElementById("lm-studio-connection-section");
const lmStudioProviderHint = document.getElementById("lm-studio-provider-hint");
const providerModelStatus = document.getElementById("provider-model-status");
const tooltipPopover = document.getElementById("workspace-tooltip-popover");
const workspaceRoot = document.querySelector(".compact-workspace");
const workspaceSidebar = document.getElementById("workspace-sidebar");
const sidebarToggleButton = document.getElementById("sidebar-toggle");
const sidebarNewQuizButton = document.getElementById("sidebar-new-quiz");
const sidebarHistoryList = document.getElementById("sidebar-history-list");
const sidebarStatusCell = document.getElementById("sidebar-status-cell");
const sidebarStatusPrimary = document.getElementById("sidebar-status-primary");
const sidebarStatusSecondary = document.getElementById(
  "sidebar-status-secondary",
);

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
});

const statusMap = {
  ok: "ok",
  available: "ok",
  unavailable: "bad",
  disabled: "bad",
  bad: "bad",
};

function hideTooltipPopover() {
  if (!tooltipPopover) {
    return;
  }
  tooltipPopover.dataset.visible = "false";
  tooltipPopover.setAttribute("aria-hidden", "true");
}

function showTooltipPopover(target) {
  if (!tooltipPopover || !(target instanceof HTMLElement)) {
    return;
  }
  const text =
    target.dataset.tooltip || target.getAttribute("aria-label") || "";
  if (!text) {
    hideTooltipPopover();
    return;
  }
  tooltipPopover.textContent = text;
  tooltipPopover.setAttribute("aria-hidden", "false");
  tooltipPopover.dataset.visible = "true";
  const card = target.closest(".workspace-modal-card");
  if (!card) {
    return;
  }
  const cardRect = card.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  const popRect = tooltipPopover.getBoundingClientRect();
  const margin = 10;
  let top = targetRect.top - cardRect.top - popRect.height - margin;
  if (top < margin) {
    top = targetRect.bottom - cardRect.top + margin;
  }
  const maxTop = cardRect.height - popRect.height - margin;
  if (maxTop >= margin) {
    top = Math.min(Math.max(top, margin), maxTop);
  }
  let left =
    targetRect.left - cardRect.left + targetRect.width / 2 - popRect.width / 2;
  const minLeft = margin;
  const maxLeft = cardRect.width - popRect.width - margin;
  if (maxLeft >= minLeft) {
    left = Math.min(Math.max(left, minLeft), maxLeft);
  }
  tooltipPopover.style.top = `${top}px`;
  tooltipPopover.style.left = `${left}px`;
}

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
  if (!element) {
    return;
  }
  if (
    element instanceof HTMLInputElement ||
    element instanceof HTMLTextAreaElement
  ) {
    element.value = value;
  } else {
    element.textContent = value;
  }
}

function setStatus(surface, text, tone, description) {
  const container = document.querySelector(
    `[data-status-surface="${surface}"]`,
  );
  const target = document.getElementById(`${surface}-status-text`);
  if (target) {
    target.textContent = text;
  }
  if (container) {
    const label = container.dataset.statusLabel || surface;
    const title = description
      ? `${label} · ${text}. ${description}`
      : `${label} · ${text}`;
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
  const normalized =
    typeof providerName === "string" ? providerName.trim().toLowerCase() : "";
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

function buildProviderUnavailableMessage(
  reason = "",
  providerKey = generationConnectionState.providerKey,
) {
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
    if (
      typeof parsed?.host !== "string" ||
      !Number.isFinite(Number(parsed?.port))
    ) {
      return null;
    }
    return { host: parsed.host, port: Number(parsed.port) };
  } catch {
    return null;
  }
}

function storeLMStudioConnection(connection) {
  try {
    window.localStorage?.setItem(
      LM_STUDIO_CONNECTION_STORAGE_KEY,
      JSON.stringify(connection),
    );
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
  editorState.lastGeneratedQuizId =
    typeof quizId === "string" && quizId.trim() ? quizId.trim() : null;
  const hasQuiz = Boolean(editorState.lastGeneratedQuizId);
  for (const [format, exportButton] of Object.entries(exportButtons)) {
    const supported =
      format === "json" || editorState.supportedExportFormats.has(format);
    toggleUnavailableHint(
      exportButton.button,
      exportButton.hintId,
      !(hasQuiz && supported),
    );
  }
  toggleUnavailableHint(previewQuizButton, "preview-quiz-hint", !hasQuiz);
  if (resultBackButton) {
    resultBackButton.disabled = !hasQuiz;
  }
}

function getCurrentGenerationReadiness() {
  const hasDocument = Boolean(
    fileInput?.files?.[0] || docTextInput?.value?.trim(),
  );
  if (!hasDocument) {
    return {
      ready: false,
      message: "Вставьте текст или прикрепите файл.",
      tone: "warn",
    };
  }
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
      ? buildProviderUnavailableMessage(
          generationConnectionState.providerReason,
          generationConnectionState.providerKey,
        )
      : PROVIDER_GENERATION_BLOCKED_MESSAGE;
    return { ready: false, message, tone: "bad" };
  }
  return {
    ready: false,
    message: SERVICES_GENERATION_BLOCKED_MESSAGE,
    tone: "bad",
  };
}

function updateGenerationSubmitAvailability() {
  if (!submitButton) {
    return;
  }
  const readiness = getCurrentGenerationReadiness();
  if (sidebarStatusPrimary && sidebarStatusSecondary) {
    if (generationConnectionState.provider === "ok") {
      sidebarStatusPrimary.textContent = "Готов";
      sidebarStatusSecondary.textContent =
        generationConnectionState.providerName || "Провайдер подключён";
    } else if (generationConnectionState.backend === "ok") {
      sidebarStatusPrimary.textContent = "Сервер доступен";
      sidebarStatusSecondary.textContent =
        generationConnectionState.providerName || "Проверяем провайдера";
    } else {
      sidebarStatusPrimary.textContent = "Статус подключения";
      sidebarStatusSecondary.textContent =
        generationConnectionState.backend === "checking"
          ? "Проверка…"
          : "Требуется проверка";
    }
  }
  if (!readiness.ready) {
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
const workspaceController = createWorkspaceController({
  root: workspaceRoot,
  stageFlow,
});
const progressController = createProgressController({
  generationProgressPanel,
  stageFlow,
});
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
  generationTemperatureValue.value = Number(
    generationTemperatureInput.value,
  ).toFixed(1);
}

function syncQuestionCount(
  source = questionCountInput,
  target = questionCountRange,
) {
  if (!source || !target) {
    return;
  }
  const parsedValue = Number.parseInt(source.value, 10);
  const normalizedValue = Number.isInteger(parsedValue)
    ? Math.min(50, Math.max(3, parsedValue))
    : 5;
  source.value = String(normalizedValue);
  target.value = String(normalizedValue);
  const sliderProgress = ((normalizedValue - 3) / 47) * 100;
  questionCountRange?.style.setProperty(
    "--slider-progress",
    `${sliderProgress}%`,
  );
}

function syncDifficulty(value = difficultySelect?.value) {
  const normalizedValue = typeof value === "string" ? value : "";
  if (difficultySelect && normalizedValue) {
    difficultySelect.value = normalizedValue;
  }
  for (const button of difficultyButtons) {
    button.setAttribute(
      "aria-pressed",
      String(button.dataset.difficultyValue === normalizedValue),
    );
  }
}

function updateDocWordCount() {
  const text = docTextInput?.value?.trim() ?? "";
  const wordCount = text ? text.split(/\s+/u).length : 0;
  const charCount = docTextInput?.value?.length ?? 0;
  const localizedWordCount = wordCount.toLocaleString("ru-RU");
  const localizedCharCount = charCount.toLocaleString("ru-RU");
  if (wordCountElement) {
    wordCountElement.textContent = `${localizedWordCount} слов`;
  }
  if (wordCountSummaryElement) {
    wordCountSummaryElement.textContent = `· ${localizedWordCount} слов`;
  }
  if (charCountTopElement) {
    charCountTopElement.textContent = `${localizedCharCount} символов`;
  }
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
    generationEstimate.textContent =
      "Оценка времени уточнится после загрузки документа.";
    return;
  }
  const charCount = docTextInput?.value?.trim().length ?? 0;
  const totalMs = genTiming.estimateTotalMs(charCount);
  generationEstimate.textContent = totalMs
    ? `Оценка времени генерации: ${formatEstimateDuration(totalMs)}`
    : "Оценка времени: ~ 43 сек.";
}

function updateLMStudioConnectionVisibility(
  providerKey = generationConnectionState.providerKey,
) {
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
  const hasDefault = typeof defaultModel === "string" && defaultModel.trim();
  providerModelStatus.replaceChildren();
  const defaultLine = document.createElement("span");
  defaultLine.className = "provider-model-default";
  defaultLine.textContent = hasDefault
    ? defaultModel.trim()
    : "Модель по умолчанию не указана.";
  providerModelStatus.append(defaultLine);
  if (availableModels.length > 0) {
    const listLabel = document.createElement("span");
    listLabel.className = "provider-model-list-label";
    listLabel.textContent = "Доступные модели:";
    const list = document.createElement("ul");
    list.className = "provider-model-list";
    availableModels.forEach((name) => {
      const item = document.createElement("li");
      item.className = "provider-model-chip";
      item.textContent = name;
      list.append(item);
    });
    providerModelStatus.append(listLabel, list);
  }
}

syncGenerationTemperatureValue();
generationTemperatureInput?.addEventListener(
  "input",
  syncGenerationTemperatureValue,
);
syncQuestionCount();
syncDifficulty();
updateDocWordCount();
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
difficultyButtons.forEach((button) => {
  button.addEventListener("click", () =>
    syncDifficulty(button.dataset.difficultyValue),
  );
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
  questionList: null,
  setTextContent,
  setExportAvailability,
  activateWorkflowStage: progressController.activateWorkflowStage,
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
  undoQuizEditButton,
  addQuestionButton,
  addQuestionTypeSelect,
  setTextContent,
  setEditorStatus,
  setLogMessage,
  setExportAvailability,
  activateWorkflowStage: progressController.activateWorkflowStage,
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
  onDocInputSummaryChange: () => {
    updateGenerationEstimate();
    updateGenerationSubmitAvailability();
  },
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
  presentQuizInline: quizEditor.presentQuizInline,
  focusResultView,
  activateWorkflowStage: progressController.activateWorkflowStage,
  markWorkflowStageFailed: progressController.markWorkflowStageFailed,
  startGenerationProgress: progressController.startGenerationProgress,
  advanceGenerationProgress: progressController.advanceGenerationProgress,
  applyBackendGenerationStatusEvidence:
    progressController.applyBackendGenerationStatusEvidence,
  completeGenerationProgress: progressController.completeGenerationProgress,
  completeGenerationProgressWithBackendEvidence: progressController.completeGenerationProgressWithBackendEvidence,
  failGenerationProgress: progressController.failGenerationProgress,
  cancelGenerationProgress: progressController.cancelGenerationProgress,
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
  getSuggestedName: () => quizTitleInput?.value ?? "",
  showToast: toastController.showToast,
});

const previewMode = createPlayablePreview({
  modalRegion,
  getQuizSnapshot: quizEditor.buildQuizUpdatePayload,
  showToast: toastController.showToast,
});

const exportModal = createExportModal({
  modalRegion,
  client,
  editorState,
  getQuizSnapshot: quizEditor.buildQuizUpdatePayload,
  saveQuiz: quizEditor.submitQuizEdits,
  serverExporter: quizExporter,
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
  updateDocWordCount();
  quizRenderer.clearQuizResult();
  quizEditor.clearQuizEditor();
  editorState.isDirty = false;
  setExportAvailability(null);
  quizRenderer.setResultState(
    "Квиз появится здесь после успешной генерации.",
    "idle",
    "Ожидание результата",
  );
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
    quizEditor.presentQuizInline(payload.quiz ?? {}, {
      language: payload.language,
    });
    quizHistory.saveQuizToHistory({
      quiz_id: normalizedQuizId,
      title: payload.quiz?.title,
      language: payload.language,
    });
    workspaceController.activateState("result", { focus: true });
    toastController.showToast("Квиз загружен из истории.", "ok");
  } catch (error) {
    toastController.showToast(
      `Не удалось открыть квиз из истории: ${describeError(error)}`,
      "bad",
    );
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
  updateDocWordCount();
  quizRenderer.clearQuizResult();
  quizEditor.clearQuizEditor();
  setEditorStatus(
    "Загрузите существующий квиз, чтобы открыть редактируемые поля и сохранить изменения.",
    null,
  );
  quizRenderer.setResultState(
    "Квиз появится здесь после успешной генерации.",
    "idle",
    "Ожидание результата",
  );
  const backendHealth = await checkBackendConnection({
    loadExports: false,
    refreshSettings: true,
  });
  if (!backendHealth) {
    setStatus(
      "provider",
      "Проверка не удалась",
      "bad",
      PROVIDER_CHECK_BLOCKED_INSTRUCTION,
    );
    setExportAvailability(editorState.lastGeneratedQuizId);
    return;
  }
  await loadLMStudioConnectionSettings();
  await checkProviderConnection();
  await loadExportFormats();
}

async function checkBackendConnection({
  loadExports = true,
  refreshSettings = true,
} = {}) {
  generationConnectionState.backend = "checking";
  generationConnectionState.backendReason = "";
  updateGenerationSubmitAvailability();
  setPreflightStatus("", null);
  setStatus(
    "backend",
    "Проверка…",
    null,
    "Проверяем доступность backend-сервера.",
  );
  setRetryButtonBusy(retryBackendButton, true);
  try {
    const backendHealth = await client.getBackendHealth();
    generationConnectionState.backend = "ok";
    generationConnectionState.backendReason = "";
    generationConnectionState.providerKey =
      backendHealth.default_provider ?? generationConnectionState.providerKey;
    generationConnectionState.providerName = formatProviderName(
      generationConnectionState.providerKey,
    );
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
    generationConnectionState.providerReason =
      "Сначала восстановите подключение к серверу.";
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
    generationConnectionState.providerReason =
      "Сначала восстановите подключение к серверу.";
    updateProviderModelStatus();
    setPreflightStatus(PROVIDER_CHECK_BLOCKED_INSTRUCTION, "bad");
    setStatus(
      "provider",
      "Недоступен · сначала сервер",
      "bad",
      PROVIDER_CHECK_BLOCKED_INSTRUCTION,
    );
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
  setStatus(
    "provider",
    "Проверка…",
    null,
    "Проверяем подключение к активному провайдеру через backend.",
  );
  setRetryButtonBusy(retryProviderButton, true);
  try {
    const providerHealth = await client.getProviderHealth();
    const providerName = formatProviderName(providerHealth.provider);
    generationConnectionState.providerKey =
      providerHealth.provider ?? generationConnectionState.providerKey;
    generationConnectionState.providerName = providerName;
    updateLMStudioConnectionVisibility();
    updateProviderModelStatus(providerHealth.default_model, providerHealth.available_models);
    if (!isProviderReadyStatus(providerHealth.status)) {
      generationConnectionState.provider = "bad";
      generationConnectionState.providerReason =
        providerHealth.message || `status: ${providerHealth.status}`;
      const message = buildProviderUnavailableMessage(
        generationConnectionState.providerReason,
        generationConnectionState.providerKey,
      );
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
      if (
        Array.isArray(providerHealth.available_models) &&
        providerHealth.available_models.length > 0
      ) {
        generationSettings.updateAvailableModels(
          providerHealth.available_models,
        );
      }
    }
    return providerHealth;
  } catch (error) {
    const reason = describeError(error);
    generationConnectionState.provider = "bad";
    generationConnectionState.providerReason = reason;
    const message = buildProviderUnavailableMessage(
      reason,
      generationConnectionState.providerKey,
    );
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
    setLMStudioConnectionStatus(
      `Не удалось получить адрес LM Studio: ${describeError(error)}`,
      "warn",
    );
    return null;
  }
}

async function applyLMStudioConnectionSettings() {
  const host = lmStudioHostInput?.value?.trim() ?? "";
  const port = Number(lmStudioPortInput?.value);
  if (!host || !Number.isInteger(port) || port < 1 || port > 65535) {
    setLMStudioConnectionStatus(
      "Введите IP/host и порт LM Studio от 1 до 65535.",
      "bad",
    );
    return;
  }
  if (host.includes("://") || /[/?#@:\\]/.test(host)) {
    setLMStudioConnectionStatus(
      "Введите только IP или host без http://, /v1 и порта.",
      "bad",
    );
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
      setLMStudioConnectionStatus(
        `LM Studio подключён: ${connection.base_url}`,
        "ok",
      );
      setLogMessage("Адрес LM Studio применён.", "ok");
    } else {
      generationConnectionState.provider = "bad";
      generationConnectionState.providerReason =
        connection.message || `status: ${connection.status}`;
      const message = buildProviderUnavailableMessage(
        generationConnectionState.providerReason,
        "lm_studio",
      );
      setStatus("provider", "Недоступен · проверьте LM Studio", "bad", message);
      setLMStudioConnectionStatus(message, "bad");
      setLogMessage(message, "bad");
    }
  } catch (error) {
    generationConnectionState.provider = "bad";
    generationConnectionState.providerReason = describeError(error);
    const message = buildProviderUnavailableMessage(
      generationConnectionState.providerReason,
      "lm_studio",
    );
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
    setLogMessage(
      `Не удалось получить форматы экспорта: ${describeError(error)}`,
      "warn",
    );
    setExportAvailability(editorState.lastGeneratedQuizId);
  }
}

function parseSupportedExportFormats(payload) {
  const formats = Array.isArray(payload?.formats) ? payload.formats : [];
  return new Set(
    formats
      .map((item) =>
        typeof item?.format === "string"
          ? item.format.trim().toLowerCase()
          : "",
      )
      .filter(Boolean),
  );
}

themeController.applyTheme(themeController.resolveStoredTheme());
workspaceController.register();
sidebarController.register();

const fieldTooltips = workspaceRoot?.querySelectorAll(".field-tooltip") ?? [];
fieldTooltips.forEach((tooltip) => {
  tooltip.addEventListener("mouseenter", () => showTooltipPopover(tooltip));
  tooltip.addEventListener("mouseleave", hideTooltipPopover);
  tooltip.addEventListener("focus", () => showTooltipPopover(tooltip));
  tooltip.addEventListener("blur", hideTooltipPopover);
});
tooltipPopover?.addEventListener("mouseenter", hideTooltipPopover);
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
window.addEventListener("beforeunload", (event) => {
  if (!editorState.isDirty) {
    return;
  }
  event.preventDefault();
  event.returnValue = "";
});
generationFlow.attachDropzone();
previewQuizButton?.addEventListener("click", previewMode.open);
exportJsonButton?.addEventListener("click", exportModal.open);
resultBackButton?.addEventListener("click", (event) => {
  event.preventDefault();
  startNewQuiz();
});
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
    progressController.activateWorkflowStage("setup");
  }
});

docTextInput?.addEventListener("input", () => {
  generationFlow.updateDocInputSummary();
  updateDocWordCount();
});

const DOC_EXAMPLE_TEXT = `Полное наименование учебного заведения — Федеральное государственное бюджетное образовательное учреждение высшего образования «Московский государственный университет геодезии и картографии», а сокращённо — МИИГАиК. Это один из старейших технических вузов России и ведущий профильный центр подготовки специалистов в области геодезии, картографии, кадастра и пространственных данных.

История
Историю университета принято отсчитывать с 1779 года. В этом году указом императрицы Екатерины II при Межевой канцелярии была основана Землемерная школа, открытая 14 мая (по старому стилю). Школа создавалась для решения практических задач межевания и управления российскими землями: стране требовались грамотные землемеры, способные точно описывать и разграничивать земельные владения.

Своё название учебное заведение позже получило в честь великого князя Константина Павловича, родившегося 27 апреля того же 1779 года. Развитие школы шло поэтапно: в 1819 году она была преобразована в Константиновское землемерное училище, а в 1835 году — в Константиновский межевой институт. В 1844 году институту были дарованы новый устав и штат, что закрепило его статус как полноценного высшего учебного заведения. Таким образом, скромная землемерная школа XVIII века постепенно выросла в крупный инженерный институт, а затем — в современный университет.

Расположение и здание
Университет находится в центре Москвы по адресу: Гороховский переулок, дом 4. Историческое здание вуза является памятником архитектуры, а сам кампус считается закрытым и компактным, что отличает МИИГАиК от многих других московских вузов. В распоряжении университета — два основных и несколько вспомогательных учебных корпусов, два геодезических полигона для летней практики, спортивно-оздоровительный лагерь и два общежития, обеспечивающих проживание иногородних студентов.

Чему учат в МИИГАиК
МИИГАиК готовит инженеров широкого спектра специальностей. Среди ключевых направлений подготовки — геодезия, картография, землеустройство и кадастр, аэрофотосъёмка и фотограмметрия, геоинформатика (ГИС), спутниковая (космическая) навигация и оптическое приборостроение. Помимо инженерных профессий, в университете обучают также архитекторов и юристов, специалистов по земельному кадастру и дистанционному зондированию Земли. Такое сочетание точных технических дисциплин с гуманитарными и прикладными направлениями делает вуз многопрофильным.

Университет сегодня
Сегодня в МИИГАиК действуют 7 факультетов, охватывающих все ключевые направления подготовки. В университете обучается более 5000 студентов, приехавших из 61 региона России и 39 стран мира. Ежегодно вузу выделяется значительное число бюджетных мест — в 2025 году их было 1318. Средний балл ЕГЭ при поступлении на бюджет в том же году составил 72,6. Особо примечателен высокий уровень трудоустройства: более 95 % выпускников находят работу в течение первого года после окончания вуза, что ставит МИИГАиК на одно из первых мест среди московских университетов по этому показателю.

МИИГАиК является участником государственной программы развития высшего образования «Приоритет-2030». Университет имеет статус опорного вуза Росреестра — то есть центра подготовки специалистов для сферы пространственных данных, — а также опорного вуза Роскосмоса, готовящего кадры для космической отрасли. Кроме того, вуз выступает базовой организацией стран СНГ по подготовке кадров в области геодезии, картографии, кадастра и дистанционного зондирования Земли. При университете работает военный учебный центр, где готовят офицеров запаса для Вооружённых сил Российской Федерации.

Известные люди
Президентом университета является Виктор Петрович Савиных — лётчик-космонавт, дважды Герой Советского Союза, что подчёркивает тесную связь вуза с космической отраслью. Должность ректора занимает Надежда Ростиславовна Камынина. Учредителем университета выступает Министерство науки и высшего образования Российской Федерации (Минобрнауки России).

Значение вуза
За свою более чем двухвековую историю МИИГАиК прошёл путь от Землемерной школы при Межевой канцелярии до современного исследовательского университета. Сочетание богатых исторических традиций, признанной научной школы и связи с такими ведомствами, как Росреестр и Роскосмос, делает его уникальным учебным заведением. Выпускники университета занимаются съёмкой и описанием территорий, созданием карт и геоинформационных систем, ведением земельного кадастра, спутниковой навигацией и разработкой оптических приборов — то есть теми задачами, которые лежат в основе управления пространственными данными любой страны.
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
  updateDocWordCount();
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
quizTitleInput?.addEventListener("input", quizEditor.markEditorDirty);
quizTitleInput?.addEventListener("change", quizEditor.markEditorDirty);
quizEditorFields?.addEventListener("click", quizEditor.regenerateQuizQuestion);
quizEditorFields?.addEventListener("click", quizEditor.revertQuestionEdits);
quizEditorFields?.addEventListener("click", quizEditor.handleStructuralAction);
quizEditorFields?.addEventListener("change", quizEditor.handleStructuralAction);
addQuestionButton?.addEventListener("click", quizEditor.handleStructuralAction);
undoQuizEditButton?.addEventListener(
  "click",
  quizEditor.undoLastStructuralEdit,
);
saveQuizButton?.addEventListener("click", quizEditor.submitQuizEdits);
quizEditorFields?.addEventListener("click", (event) => {
  const cancelTarget =
    event.target instanceof Element
      ? event.target.closest(
          '[data-editor-action="cancel-regenerate-question"]',
        )
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
