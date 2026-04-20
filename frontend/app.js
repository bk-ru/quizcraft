import { QuizCraftApiClient, QuizCraftApiError } from "./api/client.js";

const config = window.QuizCraftConfig ?? {};
const backendBaseUrl = typeof config.backendBaseUrl === "string" && config.backendBaseUrl.trim()
  ? config.backendBaseUrl.trim()
  : "http://127.0.0.1:8000";
const requestTimeoutMs = Number.isFinite(config.requestTimeoutMs) ? config.requestTimeoutMs : 8000;

const client = new QuizCraftApiClient({
  baseUrl: backendBaseUrl,
  requestTimeoutMs,
});

const form = document.getElementById("generation-form");
const fileInput = document.getElementById("document-file");
const submitButton = document.getElementById("submit-button");
const resultPanel = document.getElementById("generation-result");
const resultStateBadge = document.getElementById("result-state-badge");
const questionList = document.getElementById("quiz-question-list");

const statusMap = {
  ok: "ok",
  available: "ok",
  unavailable: "warn",
};

const mediaTypeByExtension = {
  txt: "text/plain",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  pdf: "application/pdf",
};

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

function setLogMessage(text, tone) {
  const element = document.getElementById("shell-log-message");
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

function setSubmissionStatus(text, tone) {
  const element = document.getElementById("submission-status");
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

function setResultState(text, tone, badgeText) {
  const element = document.getElementById("result-status");
  if (element) {
    element.textContent = text;
    if (tone) {
      element.dataset.statusTone = tone;
    } else {
      delete element.dataset.statusTone;
    }
  }
  if (resultPanel) {
    if (tone) {
      resultPanel.dataset.resultTone = tone;
    } else {
      delete resultPanel.dataset.resultTone;
    }
  }
  if (resultStateBadge) {
    resultStateBadge.textContent = badgeText;
  }
}

function describeError(error) {
  if (error instanceof QuizCraftApiError) {
    const backendMessage = error.payload?.error?.message;
    if (typeof backendMessage === "string" && backendMessage.trim()) {
      return backendMessage.trim();
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Неизвестная ошибка";
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

function formatFileSummary(file) {
  if (!(file instanceof File)) {
    return "Загрузите документ в формате TXT, DOCX или PDF.";
  }
  const mediaType = resolveMediaType(file);
  return `${file.name} · ${mediaType} · ${file.size} байт`;
}

function updateSelectedFileSummary() {
  const file = fileInput?.files?.[0] ?? null;
  setTextContent("file-summary", formatFileSummary(file));
  setTextContent("last-filename", file ? file.name : "Ещё не загружен");
}

function resolveMediaType(file) {
  if (typeof file.type === "string" && file.type.trim()) {
    return file.type.trim();
  }
  const name = typeof file.name === "string" ? file.name.trim() : "";
  const extension = name.includes(".") ? name.split(".").pop().toLowerCase() : "";
  return mediaTypeByExtension[extension] ?? "application/octet-stream";
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

  return {
    question_count: questionCount,
    language,
    difficulty,
    quiz_type: quizType,
    generation_mode: generationMode,
  };
}

function updateOperationSummary(uploadPayload, generationPayload) {
  setTextContent("last-filename", uploadPayload.filename ?? "Ещё не загружен");
  setTextContent("last-document-id", uploadPayload.document_id ?? "Ещё нет");
  setTextContent("last-quiz-id", generationPayload.quiz_id ?? "Ещё нет");
  setTextContent("last-request-id", generationPayload.request_id ?? "Ещё нет");
}

function clearQuizResult() {
  setTextContent("quiz-title", "Ещё нет результата");
  setTextContent("quiz-question-count", "0");
  setTextContent("quiz-model-name", "Ещё нет результата");
  setTextContent("quiz-prompt-version", "Ещё нет результата");
  if (questionList) {
    questionList.replaceChildren();
  }
}

function buildQuestionCard(question, index) {
  const item = document.createElement("li");
  item.className = "question-card";

  const heading = document.createElement("div");
  heading.className = "question-card-header";

  const indexBadge = document.createElement("span");
  indexBadge.className = "question-index";
  indexBadge.textContent = `Вопрос ${index + 1}`;

  const prompt = document.createElement("h4");
  prompt.className = "question-prompt";
  prompt.textContent = question.prompt ?? `Вопрос ${index + 1}`;

  heading.append(indexBadge, prompt);
  item.append(heading);

  const optionList = document.createElement("ol");
  optionList.className = "option-list";

  for (const [optionIndex, option] of (question.options ?? []).entries()) {
    const optionItem = document.createElement("li");
    optionItem.className = "option-item";

    const label = document.createElement("span");
    label.className = "option-label";
    label.textContent = option.text ?? "";
    optionItem.append(label);

    if (optionIndex === question.correct_option_index) {
      optionItem.dataset.correct = "true";
      const correctBadge = document.createElement("span");
      correctBadge.className = "option-badge";
      correctBadge.textContent = "Верный ответ";
      optionItem.append(correctBadge);
    }

    optionList.append(optionItem);
  }

  item.append(optionList);

  if (question.explanation?.text) {
    const explanation = document.createElement("p");
    explanation.className = "question-explanation";
    explanation.textContent = `Пояснение: ${question.explanation.text}`;
    item.append(explanation);
  }

  return item;
}

function renderQuizResult(generationPayload) {
  const quiz = generationPayload.quiz ?? {};
  const questions = Array.isArray(quiz.questions) ? quiz.questions : [];

  setTextContent("quiz-title", quiz.title ?? "Без названия");
  setTextContent("quiz-question-count", String(questions.length));
  setTextContent("quiz-model-name", generationPayload.model_name ?? "Не указана");
  setTextContent("quiz-prompt-version", generationPayload.prompt_version ?? "Не указана");

  if (questionList) {
    questionList.replaceChildren(...questions.map((question, index) => buildQuestionCard(question, index)));
  }

  setResultState("Результат готов. Квиз отображён ниже.", "ok", "Результат готов");
}

async function bootstrapShell() {
  setTextContent("backend-base-url", backendBaseUrl);
  setTextContent("request-timeout", `${requestTimeoutMs} мс`);
  updateSelectedFileSummary();
  clearQuizResult();
  setResultState("Квиз появится здесь после успешной генерации.", "idle", "Ожидание результата");

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
    setStatus(
      "provider",
      `${providerHealth.status} · ${providerHealth.message}`,
      statusMap[providerHealth.status] ?? "warn",
    );
    setLogMessage("Shell успешно связался с backend health endpoint-ами.", "ok");
  } catch (error) {
    setStatus("backend", "Проверка не удалась", "bad");
    setStatus("provider", "Проверка не удалась", "bad");
    setLogMessage(`Shell не смог получить health-статус: ${describeError(error)}`, "bad");
  }
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

  try {
    clearQuizResult();
    setBusyState(true);
    setSubmissionStatus("Загружаем документ…", "warn");
    setResultState("Генерируем квиз. Результат появится после ответа backend.", "warn", "Генерация…");
    setLogMessage(`Начата загрузка файла ${file.name}.`, "warn");

    uploadPayload = await client.uploadDocument({
      filename: file.name,
      mediaType: resolveMediaType(file),
      content: await file.arrayBuffer(),
    });

    setTextContent("last-filename", uploadPayload.filename ?? file.name);
    setTextContent("last-document-id", uploadPayload.document_id ?? "Ещё нет");
    setSubmissionStatus("Документ загружен. Запускаем генерацию…", "warn");
    setLogMessage(`Документ ${uploadPayload.document_id} загружен, запускаем генерацию.`, "warn");

    generationPayload = await client.generateQuiz(
      uploadPayload.document_id,
      buildGenerationPayload(),
    );

    updateOperationSummary(uploadPayload, generationPayload);
    renderQuizResult(generationPayload);
    setSubmissionStatus("Квиз создан и отрисован ниже.", "ok");
    setLogMessage(
      `Квиз создан: ${generationPayload.quiz_id}. Result view отрисовал содержимое без потери кириллицы.`,
      "ok",
    );
  } catch (error) {
    clearQuizResult();
    setSubmissionStatus(`Операция не завершена: ${describeError(error)}`, "bad");
    setResultState(`Результат не получен: ${describeError(error)}`, "bad", "Ошибка");
    setLogMessage(`Submit flow завершился ошибкой: ${describeError(error)}`, "bad");
  } finally {
    setBusyState(false);
  }
}

fileInput?.addEventListener("change", updateSelectedFileSummary);
form?.addEventListener("submit", submitGeneration);

bootstrapShell();
