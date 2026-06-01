import { QuizCraftApiError } from "./api/client.js";
import { describeError, describeValidationError } from "./validation-errors.js";

const mediaTypeByExtension = {
  txt: "text/plain",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  pdf: "application/pdf",
};
const SUPPORTED_DOCUMENT_EXTENSIONS = Object.freeze(Object.keys(mediaTypeByExtension));
const SUPPORTED_DOCUMENT_MEDIA_TYPES = Object.freeze(new Set(Object.values(mediaTypeByExtension)));

const SLOW_GENERATION_WARNING_MS = 60000;
const GENERATION_EVENT_POLL_MS = 1000;
const LIVE_JOURNAL_ENTRY_STAGGER_MS = 90;
const CANCEL_CONFIRMATION_MAX_ATTEMPTS = 3;
const CANCEL_CONFIRMATION_RETRY_MS = 180;
const DEFAULT_GENERATION_MODE = "auto";
const SUPPORTED_REQUEST_MODES = Object.freeze(["auto", "direct", "rag"]);
const SUPPORTED_QUIZ_TYPES = Object.freeze(["single_choice", "true_false", "fill_blank", "short_answer", "matching"]);

const DOC_LENGTH_THRESHOLDS = Object.freeze([
  { maxChars: 300, maxQuestions: 3 },
  { maxChars: 800, maxQuestions: 5 },
  { maxChars: 2000, maxQuestions: 10 },
  { maxChars: 5000, maxQuestions: 15 },
]);

function getDocLengthAdvice(charCount) {
  const match = DOC_LENGTH_THRESHOLDS.find((t) => charCount < t.maxChars);
  if (!match) {
    return null;
  }
  return `Текст короткий (${charCount.toLocaleString("ru-RU")} символов) — рекомендуется не более ${match.maxQuestions} вопросов.`;
}

const FILE_SIZE_UNITS = Object.freeze([
  { limit: 1024, unit: "Б", divisor: 1 },
  { limit: 1024 * 1024, unit: "КБ", divisor: 1024 },
  { limit: 1024 * 1024 * 1024, unit: "МБ", divisor: 1024 * 1024 },
]);

function formatElapsed(totalMs) {
  const totalSeconds = Math.max(0, Math.floor(totalMs / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return "";
  }
  const match = FILE_SIZE_UNITS.find((rule) => bytes < rule.limit) ?? FILE_SIZE_UNITS[FILE_SIZE_UNITS.length - 1];
  const value = bytes / match.divisor;
  const precision = match.unit === "Б" ? 0 : 1;
  const formatted = value.toFixed(precision).replace(".", ",");
  return `${formatted} ${match.unit}`;
}

function hasGenerationWarnings(generationPayload) {
  const qualityStatus = typeof generationPayload?.quality_status === "string"
    ? generationPayload.quality_status.trim().toLowerCase()
    : "ok";
  if (qualityStatus === "recovered" || qualityStatus === "warning" || qualityStatus === "partial") {
    return true;
  }
  return Array.isArray(generationPayload?.warnings)
    && generationPayload.warnings.some((warning) => typeof warning?.message === "string" && warning.message.trim());
}

function isDisplayableGenerationResult(generationPayload) {
  const qualityStatus = typeof generationPayload?.quality_status === "string"
    ? generationPayload.quality_status.trim().toLowerCase()
    : "ok";
  return qualityStatus !== "failed";
}

export function createGenerationFlow({
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
  liveJournalElement = null,
  liveJournalContainer = null,
  cancelButton,
  timerElement,
  timerElapsedElement = null,
  timerEtaElement = null,
  timerEtaValueElement = null,
  charCountElement = null,
  docLengthHintElement = null,
  onDocInputSummaryChange = () => {},
  genTiming = null,
  dropzoneFileName,
  dropzoneFileMeta,
  dropzoneRemoveButton,
  setTextContent,
  setPreflightStatus = null,
  setSubmissionStatus,
  setResultState,
  setLogMessage,
  enableModelPicker = false,
  setEditorStatus,
  setExportAvailability,
  clearQuizResult,
  renderQuizResult,
  presentQuizInline = null,
  focusResultView = null,
  activateWorkflowStage,
  markWorkflowStageFailed,
  startGenerationProgress,
  advanceGenerationProgress,
  applyBackendGenerationStatusEvidence = null,
  completeGenerationProgress,
  completeGenerationProgressWithBackendEvidence,
  failGenerationProgress,
  cancelGenerationProgress,
  showToast,
  saveQuizToHistory,
  refreshGenerationDefaults = null,
  getGenerationReadiness = null,
}, windowRef = (typeof window !== "undefined" ? window : null)) {
  let currentAbortController = null;
  let currentGenerationRequestId = null;
  let cancellationRequestInFlight = false;
  let timerIntervalId = null;
  let generationEventPollId = null;
  let generationEventPollingRequestId = null;
  let generationEventAfter = 0;
  const generationEventIds = new Set();
  let timerStartedAt = 0;
  let currentGenCharCount = 0;

  function generateRequestId() {
    if (windowRef?.crypto && typeof windowRef.crypto.randomUUID === "function") {
      return windowRef.crypto.randomUUID();
    }
    return `generation-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function setBusyState(isBusy) {
    if (!form) {
      return;
    }
    for (const element of form.elements) {
      if (element instanceof HTMLElement) {
        element.disabled = isBusy;
      }
    }
    if (submitButton) {
      submitButton.textContent = isBusy ? "Генерация…" : "Сгенерировать квиз";
    }
  }

  function setCancelButtonVisible(visible) {
    if (!cancelButton) {
      return;
    }
    cancelButton.hidden = !visible;
    cancelButton.disabled = !visible;
  }

  function updateTimerLabel() {
    if (!timerElement) {
      return;
    }
    const elapsed = Date.now() - timerStartedAt;
    const elapsedLabel = formatElapsed(elapsed);
    if (timerElapsedElement) {
      timerElapsedElement.textContent = elapsedLabel;
    } else {
      timerElement.textContent = elapsedLabel;
    }
    if (elapsed >= SLOW_GENERATION_WARNING_MS) {
      timerElement.dataset.tone = "warn";
    } else {
      delete timerElement.dataset.tone;
    }
    if (timerEtaElement && timerEtaValueElement && genTiming) {
      const remainingMs = genTiming.estimateRemainingMs(currentGenCharCount, elapsed);
      if (remainingMs !== null) {
        timerEtaValueElement.textContent = formatElapsed(remainingMs);
        timerEtaElement.hidden = false;
      } else {
        timerEtaElement.hidden = true;
      }
    }
  }

  function startTimer(charCount = 0) {
    if (!timerElement || !windowRef) {
      return;
    }
    currentGenCharCount = charCount;
    timerStartedAt = Date.now();
    timerElement.hidden = false;
    if (timerElapsedElement) {
      timerElapsedElement.textContent = "00:00";
    } else {
      timerElement.textContent = "00:00";
    }
    if (timerEtaElement) {
      timerEtaElement.hidden = true;
    }
    delete timerElement.dataset.tone;
    if (timerIntervalId) {
      windowRef.clearInterval(timerIntervalId);
    }
    timerIntervalId = windowRef.setInterval(updateTimerLabel, 1000);
  }

  function stopTimer() {
    if (!windowRef || timerIntervalId === null) {
      if (timerElement) {
        timerElement.hidden = true;
      }
      return;
    }
    windowRef.clearInterval(timerIntervalId);
    timerIntervalId = null;
    if (timerElement) {
      timerElement.hidden = true;
      delete timerElement.dataset.tone;
    }
    if (timerEtaElement) {
      timerEtaElement.hidden = true;
    }
  }

  function clearGenerationJournal() {
    generationEventIds.clear();
    generationEventAfter = 0;
    if (liveJournalElement) {
      liveJournalElement.replaceChildren();
    }
    if (liveJournalContainer) {
      liveJournalContainer.hidden = true;
    }
  }

  function formatJournalTime(elapsedMs) {
    const totalSeconds = Math.max(0, Math.floor((Number(elapsedMs) || 0) / 1000));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  function appendGenerationJournalEvents(events) {
    if (!liveJournalElement || !Array.isArray(events)) {
      return;
    }
    for (const event of events) {
      const eventId = Number(event?.event_id);
      const message = typeof event?.message === "string" ? event.message : "";
      if (!Number.isFinite(eventId) || !message || generationEventIds.has(eventId)) {
        continue;
      }
      generationEventIds.add(eventId);
      const item = document.createElement("li");
      item.className = "live-journal-entry";
      item.dataset.eventId = String(eventId);
      item.dataset.status = typeof event.status === "string" ? event.status : "";
      item.style.animationDelay = `${liveJournalElement.childElementCount * LIVE_JOURNAL_ENTRY_STAGGER_MS}ms`;
      const time = document.createElement("span");
      time.className = "live-journal-time";
      time.textContent = formatJournalTime(event.elapsed_ms);
      const text = document.createElement("span");
      text.className = "live-journal-message";
      text.textContent = message;
      item.append(time, text);
      liveJournalElement.append(item);
    }
    if (liveJournalContainer && generationEventIds.size > 0) {
      liveJournalContainer.hidden = false;
    }
  }

  async function pollGenerationEvents(requestId, { force = false } = {}) {
    if (!client || typeof client.getGenerationEvents !== "function") {
      return;
    }
    if (!force && generationEventPollingRequestId !== requestId) {
      return;
    }
    const payload = await client.getGenerationEvents(requestId, { after: generationEventAfter });
    if (!force && generationEventPollingRequestId !== requestId) {
      return;
    }
    const events = Array.isArray(payload?.events) ? payload.events : [];
    if (events.length === 0) {
      return;
    }
    generationEventAfter = Number(payload.next_after) || generationEventAfter;
    appendGenerationJournalEvents(events);
    if (typeof applyBackendGenerationStatusEvidence === "function") {
      applyBackendGenerationStatusEvidence(events);
    }
  }

  function startGenerationEventPolling(generationRequestId) {
    if (!windowRef || !generationRequestId) {
      return;
    }
    stopGenerationEventPolling();
    clearGenerationJournal();
    generationEventPollingRequestId = generationRequestId;
    pollGenerationEvents(generationRequestId).catch(() => {});
    generationEventPollId = windowRef.setInterval(() => {
      pollGenerationEvents(generationRequestId).catch(() => {});
    }, GENERATION_EVENT_POLL_MS);
  }

  async function stopGenerationEventPolling(generationRequestId = null, { flush = true } = {}) {
    const activeRequestId = generationEventPollingRequestId;
    generationEventPollingRequestId = null;
    if (windowRef && generationEventPollId !== null) {
      windowRef.clearInterval(generationEventPollId);
      generationEventPollId = null;
    }
    if (generationRequestId && flush && generationRequestId === activeRequestId) {
      try {
        await pollGenerationEvents(generationRequestId, { force: true });
      } catch (_error) {
        // Final generation success/error handling remains authoritative.
      }
    }
  }

  function waitForCancelRetry() {
    if (!windowRef) {
      return Promise.resolve();
    }
    return new Promise((resolve) => windowRef.setTimeout(resolve, CANCEL_CONFIRMATION_RETRY_MS));
  }

  async function requestGenerationCancellation(requestId) {
    for (let attempt = 1; attempt <= CANCEL_CONFIRMATION_MAX_ATTEMPTS; attempt += 1) {
      try {
        return await client.cancelGeneration(requestId);
      } catch (error) {
        const canRetry = error instanceof QuizCraftApiError
          && error.status === 404
          && attempt < CANCEL_CONFIRMATION_MAX_ATTEMPTS;
        if (!canRetry) {
          throw error;
        }
        await waitForCancelRetry();
      }
    }
    return null;
  }

  async function confirmGenerationCancellation(requestId, abortController) {
    let shouldRestoreCancelButton = true;
    try {
      const outcome = await requestGenerationCancellation(requestId);
      if (currentAbortController !== abortController) {
        return;
      }
      if (outcome?.status === "cancelled") {
        shouldRestoreCancelButton = false;
        abortController.abort();
        setCancelButtonVisible(false);
        return;
      }
      if (outcome?.status === "done") {
        shouldRestoreCancelButton = false;
        setCancelButtonVisible(false);
        showToast("Квиз уже завершён. Получаем результат.", "warn");
        return;
      }
      showToast("Не удалось подтвердить отмену генерации.", "bad");
    } catch (error) {
      if (currentAbortController === abortController) {
        showToast(`Не удалось подтвердить отмену генерации: ${describeError(error)}`, "bad");
      }
    } finally {
      if (currentAbortController === abortController) {
        cancellationRequestInFlight = false;
        if (shouldRestoreCancelButton && !abortController.signal.aborted) {
          setCancelButtonVisible(true);
        }
      }
    }
  }

  function cancelGeneration() {
    if (!currentAbortController || currentAbortController.signal.aborted) {
      return false;
    }
    if (currentGenerationRequestId) {
      if (!cancellationRequestInFlight) {
        cancellationRequestInFlight = true;
        if (cancelButton) {
          cancelButton.disabled = true;
        }
        confirmGenerationCancellation(currentGenerationRequestId, currentAbortController);
      }
      return true;
    }
    currentAbortController.abort();
    setCancelButtonVisible(false);
    return true;
  }

  function throwIfGenerationAborted(signal) {
    if (signal?.aborted) {
      throw new QuizCraftApiError("Запрос отменён пользователем.", { status: 0 });
    }
  }

  async function readFileArrayBuffer(file, signal) {
    throwIfGenerationAborted(signal);
    if (typeof file.stream !== "function") {
      const content = await file.arrayBuffer();
      throwIfGenerationAborted(signal);
      return content;
    }
    const reader = file.stream().getReader();
    const cancelRead = () => {
      reader.cancel().catch(() => {});
    };
    signal?.addEventListener("abort", cancelRead, { once: true });
    try {
      const chunks = [];
      while (true) {
        throwIfGenerationAborted(signal);
        const { done, value } = await reader.read();
        throwIfGenerationAborted(signal);
        if (done) {
          break;
        }
        chunks.push(value);
      }
      const content = await new Blob(chunks).arrayBuffer();
      throwIfGenerationAborted(signal);
      return content;
    } finally {
      signal?.removeEventListener("abort", cancelRead);
      reader.releaseLock();
    }
  }

  function resolveMediaType(file) {
    if (typeof file.type === "string" && file.type.trim()) {
      return file.type.trim();
    }
    const name = typeof file.name === "string" ? file.name.trim() : "";
    const extension = name.includes(".") ? name.split(".").pop().toLowerCase() : "";
    return mediaTypeByExtension[extension] ?? "application/octet-stream";
  }

  function formatFileSummary(file) {
    if (!(file instanceof File)) {
      return "Загрузите документ в формате TXT, DOCX или PDF.";
    }
    const mediaType = resolveMediaType(file);
    return `${file.name} · ${mediaType} · ${file.size} байт`;
  }

  function applyDropzoneFilled(file) {
    if (!dropzone) {
      return;
    }
    if (file instanceof File) {
      dropzone.dataset.state = "filled";
      if (dropzoneFileName) {
        dropzoneFileName.textContent = file.name;
      }
      if (dropzoneFileMeta) {
        const sizeLabel = formatFileSize(file.size);
        const mediaType = resolveMediaType(file);
        dropzoneFileMeta.textContent = sizeLabel ? `${sizeLabel} · ${mediaType}` : mediaType;
      }
    } else {
      dropzone.dataset.state = "empty";
      if (dropzoneFileName) {
        dropzoneFileName.textContent = "";
      }
      if (dropzoneFileMeta) {
        dropzoneFileMeta.textContent = "";
      }
    }
  }

  function updateSelectedFileSummary() {
    const file = fileInput?.files?.[0] ?? null;
    setTextContent("file-summary", formatFileSummary(file));
    applyDropzoneFilled(file);
  }

  function updateCharCount() {
    const file = fileInput?.files?.[0] ?? null;
    const isFile = file instanceof File;
    if (charCountElement) {
      if (isFile) {
        charCountElement.textContent = "";
      } else {
        const text = docTextInput?.value ?? "";
        const count = text.length;
        charCountElement.textContent = count > 0 ? `${count.toLocaleString("ru-RU")} символов` : "";
      }
    }
    if (docLengthHintElement) {
      if (isFile) {
        docLengthHintElement.hidden = true;
        docLengthHintElement.textContent = "";
      } else {
        const count = (docTextInput?.value ?? "").length;
        const advice = count > 0 ? getDocLengthAdvice(count) : null;
        if (advice) {
          docLengthHintElement.textContent = advice;
          docLengthHintElement.hidden = false;
        } else {
          docLengthHintElement.hidden = true;
          docLengthHintElement.textContent = "";
        }
      }
    }
  }

  function updateDocInputSummary() {
    const file = fileInput?.files?.[0] ?? null;
    const hasFile = file instanceof File;
    updateCharCount();
    if (docInputWrap) {
      docInputWrap.dataset.hasFile = String(hasFile);
    }
    if (docFilePill) {
      docFilePill.hidden = !hasFile;
    }
    if (docFileRemoveButton) {
      docFileRemoveButton.hidden = !hasFile;
    }
    if (hasFile) {
      if (docFilePillName) {
        docFilePillName.textContent = file.name;
      }
      if (docFilePillMeta) {
        const sizeLabel = formatFileSize(file.size);
        const mediaType = resolveMediaType(file);
        docFilePillMeta.textContent = sizeLabel ? `${sizeLabel} · ${mediaType}` : mediaType;
      }
      if (docTextInput) {
        docTextInput.placeholder = "Файл прикреплён — текст игнорируется";
      }
      setTextContent("file-summary", `Файл: ${file.name}`);
    } else {
      if (docFilePillName) {
        docFilePillName.textContent = "";
      }
      if (docFilePillMeta) {
        docFilePillMeta.textContent = "";
      }
      if (docTextInput) {
        docTextInput.placeholder = "Вставьте текст, чтобы создать викторину…";
      }
      const hasText = Boolean(docTextInput?.value?.trim());
      setTextContent("file-summary", hasText ? "Текст готов к генерации." : "Вставьте текст или прикрепите файл.");
    }
    onDocInputSummaryChange();
  }

  function resolveInputFile() {
    const attached = fileInput?.files?.[0];
    if (attached instanceof File) {
      return attached;
    }
    const text = docTextInput?.value?.trim() ?? "";
    if (!text) {
      return null;
    }
    return new File([text], "paste.txt", { type: "text/plain" });
  }

  function removeSelectedFile() {
    if (!fileInput) {
      return;
    }
    try {
      fileInput.value = "";
      if (typeof DataTransfer === "function") {
        fileInput.files = new DataTransfer().files;
      }
    } catch (_error) {
      fileInput.value = "";
    }
    updateDocInputSummary();
    activateWorkflowStage("upload");
    showToast("Файл удалён из формы.", "warn");
  }

  function isFileDragEvent(event) {
    const types = Array.from(event.dataTransfer?.types ?? []);
    return types.includes("Files");
  }

  function isSupportedDocumentFile(file) {
    if (!(file instanceof File)) {
      return false;
    }
    const name = typeof file.name === "string" ? file.name.trim().toLowerCase() : "";
    const extension = name.includes(".") ? name.split(".").pop() : "";
    const mediaType = resolveMediaType(file).toLowerCase();
    return SUPPORTED_DOCUMENT_EXTENSIONS.includes(extension) || SUPPORTED_DOCUMENT_MEDIA_TYPES.has(mediaType);
  }

  function setPageDocumentDragActive(isActive) {
    const document = windowRef?.document;
    if (!document?.body) {
      return;
    }
    if (isActive) {
      document.body.dataset.documentDragActive = "true";
      documentDropOverlay?.setAttribute("aria-hidden", "false");
    } else {
      delete document.body.dataset.documentDragActive;
      documentDropOverlay?.setAttribute("aria-hidden", "true");
    }
  }

  function attachFileToInput(file) {
    if (!fileInput || !(file instanceof File)) {
      return false;
    }
    if (!isSupportedDocumentFile(file)) {
      showToast("Можно прикрепить только документ TXT, DOCX или PDF.", "bad");
      return false;
    }
    const DataTransferConstructor = windowRef?.DataTransfer ?? (typeof DataTransfer === "function" ? DataTransfer : null);
    if (typeof DataTransferConstructor !== "function") {
      showToast("Браузер не смог прикрепить файл перетаскиванием. Используйте кнопку «Прикрепить файл».", "bad");
      return false;
    }
    try {
      const dataTransfer = new DataTransferConstructor();
      dataTransfer.items.add(file);
      fileInput.files = dataTransfer.files;
    } catch (_error) {
      showToast("Не удалось прикрепить файл перетаскиванием. Используйте кнопку «Прикрепить файл».", "bad");
      return false;
    }
    updateDocInputSummary();
    activateWorkflowStage("setup");
    showToast(`Файл «${file.name}» готов к загрузке.`, "ok");
    return true;
  }

  function buildGenerationPayload() {
    if (!form) {
      throw new Error("Форма генерации недоступна");
    }
    const formData = new FormData(form);
    const questionCount = Number.parseInt(String(formData.get("question_count") ?? ""), 10);
    if (!Number.isInteger(questionCount) || questionCount < 3 || questionCount > 50) {
      throw new Error("Количество вопросов должно быть целым числом от 3 до 50.");
    }
    const difficulty = String(formData.get("difficulty") ?? "").trim();
    const quizTypes = formData.getAll("quiz_types")
      .map((value) => String(value).trim())
      .filter((value) => SUPPORTED_QUIZ_TYPES.includes(value));
    const language = String(formData.get("language") ?? "").trim() || "ru";
    const requestedMode = String(formData.get("generation_mode") ?? "").trim();
    const generationMode = SUPPORTED_REQUEST_MODES.includes(requestedMode)
      ? requestedMode
      : DEFAULT_GENERATION_MODE;

    if (!difficulty) {
      throw new Error("Заполните обязательные параметры генерации.");
    }
    if (quizTypes.length === 0) {
      throw new Error("Выберите хотя бы один тип вопросов.");
    }

    const payload = {
      question_count: questionCount,
      language,
      difficulty,
      generation_mode: generationMode,
    };
    payload.quiz_type = quizTypes[0];
    payload.quiz_types = quizTypes;

    if (enableModelPicker) {
      const modelName = String(formData.get("model_name") ?? "").trim();
      if (modelName) {
        payload.model_name = modelName;
      }
    }
    const temperatureRaw = String(formData.get("temperature") ?? "").trim();
    if (temperatureRaw) {
      const temperature = Number(temperatureRaw);
      if (!Number.isFinite(temperature) || temperature < 0 || temperature > 1) {
        throw new Error("Температура должна быть числом от 0 до 1.");
      }
      payload.temperature = temperature;
    }

    return payload;
  }

  function updateOperationSummary(uploadPayload, generationPayload) {
    setTextContent("last-document-id", uploadPayload.document_id ?? "Ещё нет");
    setTextContent("last-quiz-id", generationPayload.quiz_id ?? "Ещё нет");
    setTextContent("last-request-id", generationPayload.request_id ?? "Ещё нет");
  }

  async function submitGeneration(event) {
    event.preventDefault();

    if (typeof getGenerationReadiness === "function") {
      const readiness = getGenerationReadiness();
      if (!readiness.ready) {
        const message = readiness.message || "Генерация сейчас недоступна.";
        const tone = readiness.tone || "bad";
        if (typeof setPreflightStatus === "function") {
          setPreflightStatus(message, tone);
        }
        setSubmissionStatus(message, tone);
        setResultState(message, tone, "Недоступно");
        setLogMessage(message, tone);
        showToast(message, tone);
        return;
      }
    }

    const file = resolveInputFile();
    if (!file) {
      const message = "Вставьте текст или прикрепите файл перед запуском генерации.";
      if (typeof setPreflightStatus === "function") {
        setPreflightStatus(message, "bad");
      }
      setSubmissionStatus(message, "bad");
      setLogMessage("Вставьте текст или прикрепите файл.", "bad");
      setResultState("Результат не может быть построен без документа или текста.", "bad", "Нет документа");
      return;
    }

    let uploadPayload;
    let generationPayload;
    let generationBody;
    let generationRequestId = null;
    let shouldFlushGenerationEvents = false;
    try {
      generationBody = buildGenerationPayload();
    } catch (error) {
      const message = `Операция не завершена: ${describeError(error)}`;
      if (typeof setPreflightStatus === "function") {
        setPreflightStatus(message, "bad");
      }
      setSubmissionStatus(message, "bad");
      setResultState(`Результат не получен: ${describeError(error)}`, "bad", "Ошибка");
      setLogMessage(`Проверьте параметры генерации: ${describeError(error)}`, "bad");
      showToast(describeError(error), "bad");
      return;
    }

    const abortController = new AbortController();
    currentAbortController = abortController;
    currentGenerationRequestId = null;
    cancellationRequestInFlight = false;

    try {
      clearQuizResult();
      if (typeof setPreflightStatus === "function") {
        setPreflightStatus("", null);
      }
      setBusyState(true);
      setExportAvailability(null);
      clearGenerationJournal();
      activateWorkflowStage("generation", { focus: true });
      startGenerationProgress();
      const inputCharCount = (docTextInput?.value ?? "").length;
      startTimer(inputCharCount);
      setCancelButtonVisible(true);
      setSubmissionStatus("Загружаем документ…", "warn");
      setResultState("Генерируем квиз. Результат появится после завершения генерации.", "warn", "Генерация…");
      const isPastedText = !fileInput?.files?.[0];
      setLogMessage(isPastedText ? "Начата загрузка текста." : `Начата загрузка файла ${file.name}.`, "warn");

      uploadPayload = await client.uploadDocument({
        filename: file.name,
        mediaType: resolveMediaType(file),
        content: await readFileArrayBuffer(file, abortController.signal),
        signal: abortController.signal,
      });

      advanceGenerationProgress("upload", "parse");

      setTextContent("last-document-id", uploadPayload.document_id ?? "Ещё нет");
      setSubmissionStatus("Документ загружен. Запускаем генерацию…", "warn");
      setLogMessage("Документ загружен, запускаем генерацию.", "warn");

      generationRequestId = generateRequestId();
      currentGenerationRequestId = generationRequestId;
      setTextContent("last-request-id", generationRequestId);
      startGenerationEventPolling(generationRequestId);
      generationPayload = await client.generateQuiz(
        uploadPayload.document_id,
        generationBody,
        { signal: abortController.signal, requestId: generationRequestId },
      );

      updateOperationSummary(uploadPayload, generationPayload);
      if (quizIdInput) {
        quizIdInput.value = generationPayload.quiz_id ?? "";
      }
      if (!isDisplayableGenerationResult(generationPayload)) {
        shouldFlushGenerationEvents = true;
        failGenerationProgress("persist");
        setResultState("Результат не показан: квиз не прошёл безопасное восстановление.", "bad", "Результат недоступен");
        setEditorStatus("Квиз не готов к редактированию: безопасное восстановление не удалось.", "bad");
        setSubmissionStatus("Генерация завершилась без отображаемого результата.", "bad");
        setExportAvailability(null);
        return;
      }
      renderQuizResult(generationPayload);
      shouldFlushGenerationEvents = true;
      const generatedQuiz = generationPayload.quiz ?? {};
      if (typeof presentQuizInline === "function") {
        presentQuizInline(generatedQuiz, { language: generationBody.language });
      }
      if (typeof saveQuizToHistory === "function") {
        saveQuizToHistory({
          quiz_id: generationPayload.quiz_id ?? generatedQuiz.quiz_id,
          title: generatedQuiz.title,
          language: generationBody.language,
        });
      }
      if (hasGenerationWarnings(generationPayload)) {
        setEditorStatus("Квиз показан, но часть результата была автоматически исправлена. Проверьте сообщение над квизом перед редактированием.", "warn");
        setSubmissionStatus("Квиз создан частично и отрисован ниже.", "warn");
        showToast("Квиз показан с предупреждениями.", "warn");
        setLogMessage("Проверьте предупреждение над квизом.", "warn");
      } else {
        setEditorStatus("Квиз готов. Нажмите «Редактировать квиз», чтобы открыть редактор.", "ok");
        setSubmissionStatus("Квиз создан и отрисован ниже.", "ok");
        showToast("Квиз создан и готов к просмотру.", "ok");
        setLogMessage(
          "Квиз создан.",
          "ok",
        );
      }
      if (typeof completeGenerationProgressWithBackendEvidence === "function") {
        completeGenerationProgressWithBackendEvidence(generationPayload);
      } else {
        completeGenerationProgress();
      }
      if (typeof refreshGenerationDefaults === "function") {
        refreshGenerationDefaults();
      }
      if (genTiming && currentGenCharCount > 0) {
        genTiming.record(currentGenCharCount, Date.now() - timerStartedAt);
      }
      if (typeof focusResultView === "function") {
        focusResultView();
      }
    } catch (error) {
      clearQuizResult();
      setExportAvailability(null);
      const failedStep = !uploadPayload ? "upload" : (!generationPayload ? "generate" : "persist");
      const errorCode = error instanceof QuizCraftApiError ? error.payload?.error?.code : null;
      const wasCancelled = error instanceof QuizCraftApiError
        && ((abortController.signal.aborted && error.status === 0) || errorCode === "generation_cancelled");
      if (wasCancelled) {
        shouldFlushGenerationEvents = true;
        cancelGenerationProgress();
        setSubmissionStatus("Генерация отменена пользователем.", "warn");
        setResultState("Генерация отменена. Запустите повторно, когда будете готовы.", "warn", "Отменено");
        setLogMessage("Генерация отменена пользователем.", "warn");
        showToast("Генерация отменена.", "warn");
        activateWorkflowStage("setup", { focus: true });
      } else {
        failGenerationProgress(failedStep);
        const isValidationError = error instanceof QuizCraftApiError && error.status === 422;
        const message = isValidationError ? describeValidationError(error) : describeError(error);
        setSubmissionStatus(`Операция не завершена: ${message}`, "bad");
        setResultState(`Результат не получен: ${message}`, "bad", "Ошибка");
        setLogMessage(`Генерация завершилась ошибкой: ${message}`, "bad");
        showToast(message, "bad");
        if (typeof markWorkflowStageFailed === "function") {
          markWorkflowStageFailed("generation");
        }
      }
    } finally {
      await stopGenerationEventPolling(generationRequestId, { flush: shouldFlushGenerationEvents });
      setBusyState(false);
      stopTimer();
      setCancelButtonVisible(false);
      if (currentAbortController === abortController) {
        currentAbortController = null;
        currentGenerationRequestId = null;
        cancellationRequestInFlight = false;
      }
    }
  }

  function attachInlineDropzone() {
    if (!dropzone || !fileInput) {
      return;
    }
    const setDragActive = (isActive) => {
      if (isActive) {
        dropzone.dataset.dragActive = "true";
      } else {
        delete dropzone.dataset.dragActive;
      }
    };

    for (const eventName of ["dragenter", "dragover"]) {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        setDragActive(true);
      });
    }
    for (const eventName of ["dragleave", "dragend"]) {
      dropzone.addEventListener(eventName, () => setDragActive(false));
    }
    dropzone.addEventListener("drop", (event) => {
      event.preventDefault();
      event.stopPropagation();
      setDragActive(false);
      const dropped = event.dataTransfer?.files?.[0];
      if (!dropped) {
        return;
      }
      attachFileToInput(dropped);
    });
  }

  function attachPageDocumentDropzone() {
    const document = windowRef?.document;
    if (!document || !fileInput) {
      return;
    }
    let dragDepth = 0;
    const clearDragState = () => {
      dragDepth = 0;
      setPageDocumentDragActive(false);
    };

    document.addEventListener("dragenter", (event) => {
      if (!isFileDragEvent(event)) {
        return;
      }
      event.preventDefault();
      dragDepth += 1;
      setPageDocumentDragActive(true);
    });
    document.addEventListener("dragover", (event) => {
      if (!isFileDragEvent(event)) {
        return;
      }
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
      setPageDocumentDragActive(true);
    });
    document.addEventListener("dragleave", (event) => {
      if (!isFileDragEvent(event)) {
        return;
      }
      dragDepth = Math.max(0, dragDepth - 1);
      if (dragDepth === 0) {
        setPageDocumentDragActive(false);
      }
    });
    document.addEventListener("drop", (event) => {
      if (!isFileDragEvent(event)) {
        return;
      }
      event.preventDefault();
      clearDragState();
      const dropped = event.dataTransfer?.files?.[0];
      if (!dropped) {
        return;
      }
      attachFileToInput(dropped);
    });
    document.addEventListener("dragend", clearDragState);
    windowRef?.addEventListener?.("blur", clearDragState);
  }

  function attachDropzone() {
    attachInlineDropzone();
    attachPageDocumentDropzone();
  }

  return {
    setBusyState,
    resolveMediaType,
    formatFileSummary,
    formatFileSize,
    updateSelectedFileSummary,
    updateDocInputSummary,
    resolveInputFile,
    removeSelectedFile,
    buildGenerationPayload,
    updateOperationSummary,
    appendGenerationJournalEvents,
    submitGeneration,
    attachDropzone,
    cancelGeneration,
  };
}
