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
const quizEditorLoader = document.getElementById("quiz-editor-loader");
const quizIdInput = document.getElementById("quiz-id-input");
const loadQuizButton = document.getElementById("load-quiz-button");
const quizEditorFields = document.getElementById("quiz-editor-fields");

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

function setEditorStatus(text, tone) {
  const element = document.getElementById("quiz-editor-status");
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

function setEditorBusyState(isBusy) {
  if (!quizEditorLoader) {
    return;
  }
  for (const element of quizEditorLoader.elements) {
    if (element instanceof HTMLElement) {
      element.disabled = isBusy;
    }
  }
  if (loadQuizButton) {
    loadQuizButton.textContent = isBusy ? "Загрузка…" : "Загрузить квиз";
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

function setQuizEditorSummary(quiz) {
  setTextContent("editor-quiz-id", quiz.quiz_id ?? "Ещё не загружен");
  setTextContent("editor-document-id", quiz.document_id ?? "Ещё не загружен");
  setTextContent("editor-quiz-version", Number.isInteger(quiz.version) ? String(quiz.version) : "Ещё не загружен");
  setTextContent("editor-last-edited", quiz.last_edited_at || "Ещё не загружен");
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

function clearQuizEditor() {
  setQuizEditorSummary({});
  if (quizEditorFields) {
    const placeholder = document.createElement("p");
    placeholder.className = "field-hint";
    placeholder.textContent = "Сохранение будет добавлено в следующем batch-е.";
    quizEditorFields.replaceChildren(placeholder);
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

function createEditorField(labelText, control) {
  const wrapper = document.createElement("label");
  wrapper.className = "field";

  const label = document.createElement("span");
  label.className = "field-label";
  label.textContent = labelText;

  wrapper.append(label, control);
  return wrapper;
}

function createEditorInput(value) {
  const input = document.createElement("input");
  input.type = "text";
  input.value = typeof value === "string" ? value : "";
  return input;
}

function createEditorTextarea(value, rows = 3) {
  const textarea = document.createElement("textarea");
  textarea.rows = rows;
  textarea.value = typeof value === "string" ? value : "";
  return textarea;
}

function buildQuestionEditor(question, index) {
  const article = document.createElement("article");
  article.className = "editor-card";
  article.dataset.questionId = question.question_id ?? `question-${index + 1}`;

  const header = document.createElement("div");
  header.className = "editor-card-header";

  const badge = document.createElement("span");
  badge.className = "question-index";
  badge.textContent = `Вопрос ${index + 1}`;

  const note = document.createElement("p");
  note.className = "panel-copy";
  note.textContent = "Поле можно редактировать локально. Сохранение будет доступно в следующем batch-е.";

  header.append(badge, note);
  article.append(header);

  const promptField = createEditorField("Текст вопроса", createEditorTextarea(question.prompt ?? "", 3));
  article.append(promptField);

  const optionsGrid = document.createElement("div");
  optionsGrid.className = "editor-options";

  const options = Array.isArray(question.options) ? question.options : [];
  options.forEach((option, optionIndex) => {
    const optionField = createEditorField(
      `Вариант ${optionIndex + 1}`,
      createEditorInput(option.text ?? ""),
    );
    optionField.dataset.optionId = option.option_id ?? `option-${optionIndex + 1}`;
    optionsGrid.append(optionField);
  });
  article.append(optionsGrid);

  const correctAnswerSelect = document.createElement("select");
  options.forEach((option, optionIndex) => {
    const selectOption = document.createElement("option");
    selectOption.value = String(optionIndex);
    selectOption.textContent = `Вариант ${optionIndex + 1}: ${option.text ?? ""}`;
    if (optionIndex === question.correct_option_index) {
      selectOption.selected = true;
    }
    correctAnswerSelect.append(selectOption);
  });
  article.append(createEditorField("Правильный ответ", correctAnswerSelect));

  const explanationText = question.explanation?.text ?? "";
  article.append(createEditorField("Пояснение", createEditorTextarea(explanationText, 4)));

  return article;
}

function renderQuizEditor(quiz) {
  if (!quizEditorFields) {
    return;
  }

  const fragment = document.createDocumentFragment();
  fragment.append(createEditorField("Заголовок квиза", createEditorInput(quiz.title ?? "")));

  const questions = Array.isArray(quiz.questions) ? quiz.questions : [];
  questions.forEach((question, index) => {
    fragment.append(buildQuestionEditor(question, index));
  });

  const note = document.createElement("p");
  note.className = "editor-readonly-note";
  note.textContent = "Сохранение будет доступно в следующем batch-е.";
  fragment.append(note);

  quizEditorFields.replaceChildren(fragment);
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

async function loadQuizForEditing(event) {
  event.preventDefault();

  const quizId = typeof quizIdInput?.value === "string" ? quizIdInput.value.trim() : "";
  if (!quizId) {
    setEditorStatus("Укажите идентификатор квиза перед загрузкой.", "bad");
    return;
  }

  try {
    setEditorBusyState(true);
    setEditorStatus("Загружаем сохранённый квиз…", "warn");
    const payload = await client.getQuiz(quizId);
    const quiz = payload.quiz ?? {};

    renderQuizEditor(quiz);
    setQuizEditorSummary(quiz);
    setEditorStatus("Квиз загружен в режим редактирования. Сохранение будет доступно в следующем batch-е.", "ok");
    setLogMessage(`Открыт квиз ${payload.quiz_id ?? quizId} для локального редактирования без сохранения.`, "ok");
  } catch (error) {
    setEditorStatus(`Не удалось открыть квиз: ${describeError(error)}`, "bad");
  } finally {
    setEditorBusyState(false);
  }
}

async function bootstrapShell() {
  setTextContent("backend-base-url", backendBaseUrl);
  setTextContent("request-timeout", `${requestTimeoutMs} мс`);
  updateSelectedFileSummary();
  clearQuizResult();
  clearQuizEditor();
  setEditorStatus("Загрузите существующий квиз, чтобы открыть редактируемые поля. Сохранение будет добавлено в следующем batch-е.", null);
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
    if (quizIdInput) {
      quizIdInput.value = generationPayload.quiz_id ?? "";
    }
    setEditorStatus("Новый квиз готов к открытию в режиме редактирования. Сохранение будет доступно в следующем batch-е.", "warn");
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
quizEditorLoader?.addEventListener("submit", loadQuizForEditing);

bootstrapShell();
