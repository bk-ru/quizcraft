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
const saveQuizButton = document.getElementById("save-quiz-button");
const quizEditorFields = document.getElementById("quiz-editor-fields");

const editorState = {
  loadedQuiz: null,
  isDirty: false,
};

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

function cloneQuizPayload(quiz) {
  if (typeof structuredClone === "function") {
    return structuredClone(quiz);
  }
  return JSON.parse(JSON.stringify(quiz));
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

function setEditorSaveState({ disabled, busy = false } = {}) {
  if (!saveQuizButton) {
    return;
  }
  saveQuizButton.disabled = Boolean(disabled);
  saveQuizButton.textContent = busy ? "Сохраняем…" : "Сохранить изменения";
}

function markEditorDirty() {
  if (!editorState.loadedQuiz) {
    return;
  }
  editorState.isDirty = true;
  setEditorSaveState({ disabled: false });
  setEditorStatus("Изменения пока не сохранены.", "warn");
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
  editorState.loadedQuiz = null;
  editorState.isDirty = false;
  setQuizEditorSummary({});
  setEditorSaveState({ disabled: true });
  if (quizEditorFields) {
    const placeholder = document.createElement("p");
    placeholder.className = "field-hint";
    placeholder.textContent = "После загрузки квиза здесь появятся редактируемые поля.";
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
  note.textContent = "После редактирования это содержимое можно сохранить в backend.";

  header.append(badge, note);
  article.append(header);

  const promptField = createEditorField("Текст вопроса", createEditorTextarea(question.prompt ?? "", 3));
  promptField.querySelector("textarea")?.setAttribute("data-editor-field", "prompt");
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
    optionField.querySelector("input")?.setAttribute("data-editor-field", "option-text");
    optionField.querySelector("input")?.setAttribute("data-option-id", option.option_id ?? `option-${optionIndex + 1}`);
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
  correctAnswerSelect.setAttribute("data-editor-field", "correct-option-index");
  article.append(createEditorField("Правильный ответ", correctAnswerSelect));

  const explanationText = question.explanation?.text ?? "";
  const explanationField = createEditorField("Пояснение", createEditorTextarea(explanationText, 4));
  explanationField.querySelector("textarea")?.setAttribute("data-editor-field", "explanation");
  article.append(explanationField);

  return article;
}

function renderQuizEditor(quiz) {
  if (!quizEditorFields) {
    return;
  }

  const fragment = document.createDocumentFragment();
  const titleField = createEditorField("Заголовок квиза", createEditorInput(quiz.title ?? ""));
  titleField.querySelector("input")?.setAttribute("data-editor-field", "title");
  fragment.append(titleField);

  const questions = Array.isArray(quiz.questions) ? quiz.questions : [];
  questions.forEach((question, index) => {
    fragment.append(buildQuestionEditor(question, index));
  });

  const note = document.createElement("p");
  note.className = "editor-readonly-note";
  note.textContent = "Изменения пока не сохранены.";
  fragment.append(note);

  quizEditorFields.replaceChildren(fragment);
  editorState.loadedQuiz = cloneQuizPayload(quiz);
  editorState.isDirty = false;
  setEditorSaveState({ disabled: true });
}

function buildQuizUpdatePayload() {
  if (!editorState.loadedQuiz || !quizEditorFields) {
    throw new Error("Сначала загрузите квиз для редактирования.");
  }

  const quiz = cloneQuizPayload(editorState.loadedQuiz);
  const titleInput = quizEditorFields.querySelector('[data-editor-field="title"]');
  if (titleInput instanceof HTMLInputElement) {
    quiz.title = titleInput.value;
  }

  const questionCards = Array.from(quizEditorFields.querySelectorAll(".editor-card"));
  quiz.questions = questionCards.map((card, questionIndex) => {
    const baseQuestion = quiz.questions?.[questionIndex] ?? {};
    const promptInput = card.querySelector('[data-editor-field="prompt"]');
    const correctAnswerSelect = card.querySelector('[data-editor-field="correct-option-index"]');
    const explanationInput = card.querySelector('[data-editor-field="explanation"]');
    const optionInputs = Array.from(card.querySelectorAll('[data-editor-field="option-text"]'));

    return {
      ...baseQuestion,
      prompt: promptInput instanceof HTMLTextAreaElement ? promptInput.value : baseQuestion.prompt,
      options: optionInputs.map((input, optionIndex) => ({
        ...(baseQuestion.options?.[optionIndex] ?? {}),
        text: input instanceof HTMLInputElement ? input.value : baseQuestion.options?.[optionIndex]?.text,
      })),
      correct_option_index: correctAnswerSelect instanceof HTMLSelectElement
        ? Number.parseInt(correctAnswerSelect.value, 10)
        : baseQuestion.correct_option_index,
      explanation: {
        text: explanationInput instanceof HTMLTextAreaElement ? explanationInput.value : baseQuestion.explanation?.text ?? "",
      },
    };
  });

  return quiz;
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
    setEditorStatus("Квиз загружен в режим редактирования. Можно вносить изменения и сохранять их.", "ok");
    setLogMessage(`Открыт квиз ${payload.quiz_id ?? quizId} для локального редактирования и последующего сохранения.`, "ok");
  } catch (error) {
    setEditorStatus(`Не удалось открыть квиз: ${describeError(error)}`, "bad");
    setEditorSaveState({ disabled: true });
  } finally {
    setEditorBusyState(false);
  }
}

async function submitQuizEdits() {
  if (!editorState.loadedQuiz) {
    setEditorStatus("Сначала откройте существующий квиз.", "bad");
    return;
  }

  try {
    setEditorSaveState({ disabled: true, busy: true });
    setEditorStatus("Сохраняем изменения…", "warn");
    const updatePayload = buildQuizUpdatePayload();
    const saveResponse = await client.updateQuiz(editorState.loadedQuiz.quiz_id, { quiz: updatePayload });
    const reloadResponse = await client.getQuiz(saveResponse.quiz_id ?? editorState.loadedQuiz.quiz_id);
    const persistedQuiz = reloadResponse.quiz ?? saveResponse.quiz ?? updatePayload;

    renderQuizEditor(persistedQuiz);
    setQuizEditorSummary(persistedQuiz);
    setTextContent("last-quiz-id", reloadResponse.quiz_id ?? saveResponse.quiz_id ?? persistedQuiz.quiz_id ?? "Ещё нет");
    setTextContent("last-request-id", reloadResponse.request_id ?? saveResponse.request_id ?? "Ещё нет");
    setEditorStatus("Изменения сохранены.", "ok");
    setLogMessage(
      `Изменения квиза ${persistedQuiz.quiz_id} сохранены и перечитаны из backend без потери кириллицы.`,
      "ok",
    );
  } catch (error) {
    if (error instanceof QuizCraftApiError && error.status === 422) {
      setEditorStatus(`Исправьте ошибки и повторите сохранение. ${describeError(error)}`, "bad");
    } else {
      setEditorStatus(`Не удалось сохранить квиз: ${describeError(error)}`, "bad");
    }
    setEditorSaveState({ disabled: false, busy: false });
  }
}

async function bootstrapShell() {
  setTextContent("backend-base-url", backendBaseUrl);
  setTextContent("request-timeout", `${requestTimeoutMs} мс`);
  updateSelectedFileSummary();
  clearQuizResult();
  clearQuizEditor();
  setEditorStatus("Загрузите существующий квиз, чтобы открыть редактируемые поля и сохранить изменения.", null);
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
    setEditorStatus("Новый квиз готов к открытию в режиме редактирования. После загрузки можно сохранить изменения.", "warn");
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
quizEditorFields?.addEventListener("input", markEditorDirty);
quizEditorFields?.addEventListener("change", markEditorDirty);
saveQuizButton?.addEventListener("click", submitQuizEdits);

bootstrapShell();
