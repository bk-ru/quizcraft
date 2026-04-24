import { QuizCraftApiError } from "./api/client.js";
import { describeError, describeValidationError } from "./validation-errors.js";

const mediaTypeByExtension = {
  txt: "text/plain",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  pdf: "application/pdf",
};

const SLOW_GENERATION_WARNING_MS = 60000;

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

export function createGenerationFlow({
  client,
  form,
  fileInput,
  submitButton,
  dropzone,
  quizIdInput,
  cancelButton,
  timerElement,
  dropzoneFileName,
  dropzoneFileMeta,
  dropzoneRemoveButton,
  setTextContent,
  setSubmissionStatus,
  setResultState,
  setLogMessage,
  setEditorStatus,
  setExportAvailability,
  clearQuizResult,
  renderQuizResult,
  renderQuizEditor,
  setQuizEditorSummary,
  advanceStepper,
  markStepperFailed,
  waitForProgressVisibility,
  startGenerationProgress,
  advanceGenerationProgress,
  completeGenerationProgress,
  completeGenerationProgressWithBackendEvidence,
  failGenerationProgress,
  showToast,
  saveQuizToHistory,
}, windowRef = (typeof window !== "undefined" ? window : null)) {
  let currentAbortController = null;
  let timerIntervalId = null;
  let timerStartedAt = 0;

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
    timerElement.textContent = formatElapsed(elapsed);
    if (elapsed >= SLOW_GENERATION_WARNING_MS) {
      timerElement.dataset.tone = "warn";
    } else {
      delete timerElement.dataset.tone;
    }
  }

  function startTimer() {
    if (!timerElement || !windowRef) {
      return;
    }
    timerStartedAt = Date.now();
    timerElement.hidden = false;
    timerElement.textContent = "00:00";
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
  }

  function cancelGeneration() {
    if (!currentAbortController || currentAbortController.signal.aborted) {
      return;
    }
    currentAbortController.abort();
    setCancelButtonVisible(false);
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
    setTextContent("last-filename", file ? file.name : "Ещё не загружен");
    applyDropzoneFilled(file);
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
    updateSelectedFileSummary();
    advanceStepper("upload");
    showToast("Файл удалён из формы.", "warn");
  }

  function buildGenerationPayload() {
    if (!form) {
      throw new Error("Форма генерации недоступна");
    }
    const formData = new FormData(form);
    const questionCount = Number.parseInt(String(formData.get("question_count") ?? ""), 10);
    if (!Number.isInteger(questionCount) || questionCount <= 0) {
      throw new Error("Количество вопросов должно быть положительным целым числом.");
    }
    const difficulty = String(formData.get("difficulty") ?? "").trim();
    const quizType = String(formData.get("quiz_type") ?? "").trim();
    const language = String(formData.get("language") ?? "").trim() || "ru";
    const generationMode = String(formData.get("generation_mode") ?? "").trim() || "direct";

    if (!difficulty || !quizType) {
      throw new Error("Заполните обязательные параметры генерации.");
    }

    const payload = {
      question_count: questionCount,
      language,
      difficulty,
      quiz_type: quizType,
      generation_mode: generationMode,
    };

    const modelName = String(formData.get("model_name") ?? "").trim();
    if (modelName) {
      payload.model_name = modelName;
    }
    const profileName = String(formData.get("profile_name") ?? "").trim();
    if (profileName) {
      payload.profile_name = profileName;
    }

    return payload;
  }

  function updateOperationSummary(uploadPayload, generationPayload) {
    setTextContent("last-filename", uploadPayload.filename ?? "Ещё не загружен");
    setTextContent("last-document-id", uploadPayload.document_id ?? "Ещё нет");
    setTextContent("last-quiz-id", generationPayload.quiz_id ?? "Ещё нет");
    setTextContent("last-request-id", generationPayload.request_id ?? "Ещё нет");
  }

  async function submitGeneration(event) {
    event.preventDefault();

    const file = fileInput?.files?.[0] ?? null;
    if (!(file instanceof File)) {
      setSubmissionStatus("Загрузите документ перед запуском генерации.", "bad");
      setLogMessage("Submit flow остановлен: документ не выбран.", "bad");
      setResultState("Результат не может быть построен без документа.", "bad", "Нет документа");
      return;
    }

    let uploadPayload;
    let generationPayload;
    let generationBody;
    try {
      generationBody = buildGenerationPayload();
    } catch (error) {
      setSubmissionStatus(`Операция не завершена: ${describeError(error)}`, "bad");
      setResultState(`Результат не получен: ${describeError(error)}`, "bad", "Ошибка");
      setLogMessage(`Submit flow остановлен: ${describeError(error)}`, "bad");
      showToast(describeError(error), "bad");
      return;
    }

    const abortController = new AbortController();
    currentAbortController = abortController;

    try {
      clearQuizResult();
      setBusyState(true);
      setExportAvailability(null);
      advanceStepper("review");
      startGenerationProgress();
      startTimer();
      setCancelButtonVisible(true);
      setSubmissionStatus("Загружаем документ…", "warn");
      setResultState("Генерируем квиз. Результат появится после ответа backend.", "warn", "Генерация…");
      setLogMessage(`Начата загрузка файла ${file.name}.`, "warn");

      uploadPayload = await client.uploadDocument({
        filename: file.name,
        mediaType: resolveMediaType(file),
        content: await file.arrayBuffer(),
        signal: abortController.signal,
      });

      advanceGenerationProgress("upload", "parse");
      await waitForProgressVisibility();
      advanceGenerationProgress("parse", "generate");

      setTextContent("last-filename", uploadPayload.filename ?? file.name);
      setTextContent("last-document-id", uploadPayload.document_id ?? "Ещё нет");
      setSubmissionStatus("Документ загружен. Запускаем генерацию…", "warn");
      setLogMessage(`Документ ${uploadPayload.document_id} загружен, запускаем генерацию.`, "warn");

      generationPayload = await client.generateQuiz(
        uploadPayload.document_id,
        generationBody,
        { signal: abortController.signal },
      );

      advanceGenerationProgress("generate", "validate");
      await waitForProgressVisibility();

      updateOperationSummary(uploadPayload, generationPayload);
      if (quizIdInput) {
        quizIdInput.value = generationPayload.quiz_id ?? "";
      }
      renderQuizResult(generationPayload);
      const generatedQuiz = generationPayload.quiz ?? {};
      renderQuizEditor(generatedQuiz);
      setQuizEditorSummary(generatedQuiz);
      if (typeof saveQuizToHistory === "function") {
        saveQuizToHistory({
          quiz_id: generationPayload.quiz_id ?? generatedQuiz.quiz_id,
          title: generatedQuiz.title,
        });
      }
      setEditorStatus("Новый квиз загружен в редактор. Внесите правки и нажмите «Сохранить изменения».", "ok");
      setSubmissionStatus("Квиз создан и отрисован ниже.", "ok");
      showToast("Квиз создан и готов к просмотру.", "ok");
      setLogMessage(
        `Квиз создан: ${generationPayload.quiz_id}. Result view отрисовал содержимое без потери кириллицы.`,
        "ok",
      );
      if (typeof completeGenerationProgressWithBackendEvidence === "function") {
        completeGenerationProgressWithBackendEvidence(generationPayload);
      } else {
        completeGenerationProgress();
      }
    } catch (error) {
      clearQuizResult();
      setExportAvailability(null);
      const failedStep = !uploadPayload ? "upload" : (!generationPayload ? "generate" : "validate");
      failGenerationProgress(failedStep);
      const wasCancelled = abortController.signal.aborted
        && error instanceof QuizCraftApiError
        && error.status === 0;
      if (wasCancelled) {
        setSubmissionStatus("Генерация отменена пользователем.", "warn");
        setResultState("Генерация отменена. Запустите повторно, когда будете готовы.", "warn", "Отменено");
        setLogMessage("Генерация отменена пользователем до завершения ответа backend.", "warn");
        showToast("Генерация отменена.", "warn");
        advanceStepper("params");
      } else {
        const isValidationError = error instanceof QuizCraftApiError && error.status === 422;
        const message = isValidationError ? describeValidationError(error) : describeError(error);
        setSubmissionStatus(`Операция не завершена: ${message}`, "bad");
        setResultState(`Результат не получен: ${message}`, "bad", "Ошибка");
        setLogMessage(`Submit flow завершился ошибкой: ${message}`, "bad");
        showToast(message, "bad");
        if (typeof markStepperFailed === "function") {
          markStepperFailed("review");
        }
      }
    } finally {
      setBusyState(false);
      stopTimer();
      setCancelButtonVisible(false);
      if (currentAbortController === abortController) {
        currentAbortController = null;
      }
    }
  }

  function attachDropzone() {
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
      setDragActive(false);
      const dropped = event.dataTransfer?.files?.[0];
      if (!dropped) {
        return;
      }
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(dropped);
      fileInput.files = dataTransfer.files;
      updateSelectedFileSummary();
      advanceStepper("params");
      showToast(`Файл «${dropped.name}» готов к загрузке.`, "ok");
    });
  }

  return {
    setBusyState,
    resolveMediaType,
    formatFileSummary,
    formatFileSize,
    updateSelectedFileSummary,
    removeSelectedFile,
    buildGenerationPayload,
    updateOperationSummary,
    submitGeneration,
    attachDropzone,
    cancelGeneration,
  };
}
