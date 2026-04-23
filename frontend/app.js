import { QuizCraftApiClient, QuizCraftApiError } from "./api/client.js";

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

const THEME_STORAGE_KEY = "quizcraft.theme";
const THEME_ORDER = ["auto", "light", "dark"];
const THEME_LABELS = { auto: "Авто", light: "Светлая", dark: "Тёмная" };

const statusMap = {
  ok: "ok",
  available: "ok",
  unavailable: "bad",
};

const LM_STUDIO_UNAVAILABLE_INSTRUCTION =
  "LM Studio недоступен. Запустите приложение LM Studio, загрузите модель и убедитесь, что сервер слушает http://127.0.0.1:1234.";

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

const VALIDATION_FIELD_EXACT_LABELS = {
  "question_count": "Количество вопросов",
  "language": "Язык квиза",
  "difficulty": "Сложность",
  "quiz_type": "Формат квиза",
  "generation_mode": "Режим генерации",
  "quiz": "Квиз",
  "quiz.quiz_id": "Идентификатор квиза",
  "quiz.document_id": "Идентификатор документа",
  "quiz.title": "Заголовок квиза",
  "quiz.version": "Версия квиза",
  "quiz.last_edited_at": "Дата последнего редактирования",
  "quiz.questions": "Список вопросов",
};

const VALIDATION_MESSAGE_RULES = [
  [/^string should have at least (\d+) character/i, (m) => `минимум ${m[1]} символ(ов)`],
  [/^string should have at most (\d+) character/i, (m) => `максимум ${m[1]} символ(ов)`],
  [/^field required$/i, () => "обязательное поле"],
  [/^input should be a valid integer/i, () => "ожидается целое число"],
  [/^input should be a valid number/i, () => "ожидается число"],
  [/^input should be a valid string/i, () => "ожидается строка"],
  [/^input should be greater than or equal to (\S+)/i, (m) => `значение должно быть не меньше ${m[1]}`],
  [/^input should be greater than (\S+)/i, (m) => `значение должно быть больше ${m[1]}`],
  [/^input should be less than or equal to (\S+)/i, (m) => `значение должно быть не больше ${m[1]}`],
  [/^input should be less than (\S+)/i, (m) => `значение должно быть меньше ${m[1]}`],
  [/^list should have at least (\d+) item/i, (m) => `минимум ${m[1]} элемент(ов) в списке`],
  [/^list should have at most (\d+) item/i, (m) => `максимум ${m[1]} элемент(ов) в списке`],
  [/^extra inputs are not permitted/i, () => "лишнее поле не допускается"],
  [/^input should be '[^']+'/i, (m) => `допустимые значения: ${m[0].replace(/input should be /i, "")}`],
  [/^quiz title must not be empty/i, () => "Заголовок квиза не должен быть пустым"],
  [/^quiz must contain at least one question/i, () => "Квиз должен содержать хотя бы один вопрос"],
  [/^question prompt must not be empty/i, () => "Текст вопроса не должен быть пустым"],
  [/^question must have at least two options/i, () => "В вопросе должно быть минимум два варианта"],
  [/^option text must not be empty/i, () => "Текст варианта не должен быть пустым"],
  [/^question options must not contain duplicates/i, () => "Варианты ответа не должны повторяться"],
  [/^correct option index is out of range/i, () => "Номер правильного варианта вне диапазона"],
  [/^quiz_id in payload must match path/i, () => "Идентификатор квиза в теле запроса не совпадает с URL"],
  [/^document_id must match the stored quiz/i, () => "Идентификатор документа не совпадает с сохранённым квизом"],
];

function translateValidationMessage(rawMessage) {
  const trimmed = rawMessage.trim();
  for (const [pattern, transform] of VALIDATION_MESSAGE_RULES) {
    const match = trimmed.match(pattern);
    if (match) {
      return transform(match);
    }
  }
  return trimmed;
}

function translateValidationFieldPath(path) {
  if (VALIDATION_FIELD_EXACT_LABELS[path]) {
    return VALIDATION_FIELD_EXACT_LABELS[path];
  }

  const questionMatch = path.match(/^quiz\.questions\.(\d+)(?:\.(.+))?$/);
  if (questionMatch) {
    const questionNumber = Number.parseInt(questionMatch[1], 10) + 1;
    const subPath = questionMatch[2] ?? "";

    const optionMatch = subPath.match(/^options\.(\d+)(?:\.(.+))?$/);
    if (optionMatch) {
      const optionNumber = Number.parseInt(optionMatch[1], 10) + 1;
      const optionSub = optionMatch[2] ?? "";
      const optionLabels = {
        "": `вариант ${optionNumber}`,
        "text": `текст варианта ${optionNumber}`,
        "option_id": `идентификатор варианта ${optionNumber}`,
      };
      const optionLabel = optionLabels[optionSub] ?? `вариант ${optionNumber} (${optionSub})`;
      return `Вопрос ${questionNumber}: ${optionLabel}`;
    }

    const questionLabels = {
      "": "данные вопроса",
      "prompt": "текст вопроса",
      "correct_option_index": "номер правильного варианта",
      "explanation.text": "текст пояснения",
      "explanation": "пояснение",
      "question_id": "идентификатор вопроса",
      "options": "список вариантов",
    };
    return `Вопрос ${questionNumber}: ${questionLabels[subPath] ?? subPath}`;
  }

  return path;
}

function translateValidationFragment(fragment) {
  const trimmed = fragment.trim();
  if (!trimmed) {
    return "";
  }
  const colonIndex = trimmed.indexOf(":");
  if (colonIndex === -1) {
    return translateValidationMessage(trimmed);
  }
  const path = trimmed.slice(0, colonIndex).trim();
  const message = trimmed.slice(colonIndex + 1).trim();
  if (!path) {
    return translateValidationMessage(message);
  }
  const fieldLabel = translateValidationFieldPath(path);
  const messageTranslation = translateValidationMessage(message);
  return `${fieldLabel} — ${messageTranslation}`;
}

function describeValidationError(error) {
  if (!(error instanceof QuizCraftApiError) || error.status !== 422) {
    return describeError(error);
  }
  const rawMessage = error.payload?.error?.message;
  if (typeof rawMessage !== "string" || !rawMessage.trim()) {
    return describeError(error);
  }
  const fragments = rawMessage
    .split(";")
    .map((fragment) => translateValidationFragment(fragment))
    .filter(Boolean);
  if (fragments.length === 0) {
    return rawMessage.trim();
  }
  if (fragments.length === 1) {
    return fragments[0];
  }
  return fragments.map((fragment) => `• ${fragment}`).join("\n");
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
  setExportAvailability(generationPayload.quiz_id ?? quiz.quiz_id ?? null);
  advanceStepper("review");
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
    setExportAvailability(payload.quiz_id ?? quiz.quiz_id ?? quizId);
    advanceStepper("edit");
    showToast("Квиз загружен в редактор.", "ok");
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
    setExportAvailability(reloadResponse.quiz_id ?? saveResponse.quiz_id ?? persistedQuiz.quiz_id ?? null);
    setEditorStatus("Изменения сохранены.", "ok");
    showToast("Изменения сохранены.", "ok");
    setLogMessage(
      `Изменения квиза ${persistedQuiz.quiz_id} сохранены и перечитаны из backend без потери кириллицы.`,
      "ok",
    );
  } catch (error) {
    if (error instanceof QuizCraftApiError && error.status === 422) {
      setEditorStatus(`Исправьте ошибки и повторите сохранение.\n${describeValidationError(error)}`, "bad");
    } else {
      setEditorStatus(`Не удалось сохранить квиз: ${describeError(error)}`, "bad");
    }
    setEditorSaveState({ disabled: false, busy: false });
  }
}

async function bootstrapShell() {
  setTextContent("backend-base-url", backendBaseUrl);
  const t = client.timeouts;
  setTextContent("request-timeout",
    `health ${t.health / 1000} с · upload ${t.upload / 1000} с · generate ${t.generate / 1000} с · editor ${t.quizEditor / 1000} с`,
  );
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
    if (providerHealth.status === "unavailable") {
      setStatus("provider", "Недоступен · запустите LM Studio", "bad");
      setLogMessage(LM_STUDIO_UNAVAILABLE_INSTRUCTION, "bad");
      showToast(LM_STUDIO_UNAVAILABLE_INSTRUCTION, "bad");
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

  try {
    clearQuizResult();
    setBusyState(true);
    setExportAvailability(null);
    advanceStepper("generate");
    startGenerationProgress();
    setSubmissionStatus("Загружаем документ…", "warn");
    setResultState("Генерируем квиз. Результат появится после ответа backend.", "warn", "Генерация…");
    setLogMessage(`Начата загрузка файла ${file.name}.`, "warn");

    uploadPayload = await client.uploadDocument({
      filename: file.name,
      mediaType: resolveMediaType(file),
      content: await file.arrayBuffer(),
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
    setEditorStatus("Новый квиз загружен в редактор. Внесите правки и нажмите «Сохранить изменения».", "ok");
    setSubmissionStatus("Квиз создан и отрисован ниже.", "ok");
    showToast("Квиз создан и готов к просмотру.", "ok");
    setLogMessage(
      `Квиз создан: ${generationPayload.quiz_id}. Result view отрисовал содержимое без потери кириллицы.`,
      "ok",
    );
    completeGenerationProgress();
  } catch (error) {
    clearQuizResult();
    setExportAvailability(null);
    const failedStep = !uploadPayload ? "upload" : (!generationPayload ? "generate" : "validate");
    failGenerationProgress(failedStep);
    const isValidationError = error instanceof QuizCraftApiError && error.status === 422;
    const message = isValidationError ? describeValidationError(error) : describeError(error);
    setSubmissionStatus(`Операция не завершена: ${message}`, "bad");
    setResultState(`Результат не получен: ${message}`, "bad", "Ошибка");
    setLogMessage(`Submit flow завершился ошибкой: ${message}`, "bad");
    showToast(message, "bad");
  } finally {
    setBusyState(false);
  }
}

function setStepState(step, state) {
  if (!stepper) {
    return;
  }
  const target = stepper.querySelector(`.step[data-step="${step}"]`);
  if (!target) {
    return;
  }
  if (state) {
    target.dataset.state = state;
  } else {
    delete target.dataset.state;
  }
}

function advanceStepper(stageName) {
  const order = ["upload", "params", "generate", "review", "edit"];
  const activeIndex = order.indexOf(stageName);
  if (activeIndex < 0 || !stepper) {
    return;
  }
  for (const [index, step] of order.entries()) {
    if (index < activeIndex) {
      setStepState(step, "done");
    } else if (index === activeIndex) {
      setStepState(step, "active");
    } else {
      setStepState(step, null);
    }
  }
}

const GENERATION_PROGRESS_ORDER = ["upload", "parse", "generate", "validate"];
const PROGRESS_STEP_VISIBILITY_MS = 300;
const PROGRESS_SUCCESS_AUTOHIDE_MS = 900;
const PROGRESS_FAILURE_AUTOHIDE_MS = 2400;

function waitForProgressVisibility(ms = PROGRESS_STEP_VISIBILITY_MS) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function setGenerationProgressVisible(visible) {
  if (!generationProgressPanel) {
    return;
  }
  if (visible) {
    generationProgressPanel.hidden = false;
    generationProgressPanel.dataset.visible = "true";
  } else {
    generationProgressPanel.hidden = true;
    delete generationProgressPanel.dataset.visible;
  }
}

function setGenerationProgressStepState(step, state) {
  if (!generationProgressPanel) {
    return;
  }
  const target = generationProgressPanel.querySelector(`.progress-step[data-step="${step}"]`);
  if (!target) {
    return;
  }
  target.dataset.state = state;
}

function resetGenerationProgress() {
  if (!generationProgressPanel) {
    return;
  }
  for (const step of GENERATION_PROGRESS_ORDER) {
    setGenerationProgressStepState(step, "pending");
  }
  generationProgressPanel.dataset.currentStep = "";
}

function startGenerationProgress() {
  if (!generationProgressPanel) {
    return;
  }
  resetGenerationProgress();
  setGenerationProgressVisible(true);
  setGenerationProgressStepState("upload", "active");
  generationProgressPanel.dataset.currentStep = "upload";
}

function advanceGenerationProgress(completedStep, nextStep) {
  if (!generationProgressPanel) {
    return;
  }
  if (completedStep) {
    setGenerationProgressStepState(completedStep, "done");
  }
  if (nextStep) {
    setGenerationProgressStepState(nextStep, "active");
    generationProgressPanel.dataset.currentStep = nextStep;
  } else {
    generationProgressPanel.dataset.currentStep = "";
  }
}

function completeGenerationProgress() {
  if (!generationProgressPanel) {
    return;
  }
  for (const step of GENERATION_PROGRESS_ORDER) {
    setGenerationProgressStepState(step, "done");
  }
  generationProgressPanel.dataset.currentStep = "done";
  window.setTimeout(() => {
    setGenerationProgressVisible(false);
  }, PROGRESS_SUCCESS_AUTOHIDE_MS);
}

function failGenerationProgress(failedStep) {
  if (!generationProgressPanel) {
    return;
  }
  if (failedStep) {
    setGenerationProgressStepState(failedStep, "failed");
    generationProgressPanel.dataset.currentStep = "failed";
  }
  window.setTimeout(() => {
    setGenerationProgressVisible(false);
  }, PROGRESS_FAILURE_AUTOHIDE_MS);
}

function resolveStoredTheme() {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored && THEME_ORDER.includes(stored)) {
      return stored;
    }
  } catch (error) {
    return "auto";
  }
  return "auto";
}

function applyTheme(theme) {
  const next = THEME_ORDER.includes(theme) ? theme : "auto";
  document.documentElement.setAttribute("data-theme", next);
  if (themeToggleLabel) {
    themeToggleLabel.textContent = THEME_LABELS[next];
  }
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, next);
  } catch (error) {
    /* ignore write failures (private mode) */
  }
}

function cycleTheme() {
  const current = document.documentElement.getAttribute("data-theme") ?? "auto";
  const index = THEME_ORDER.indexOf(current);
  const next = THEME_ORDER[(index + 1) % THEME_ORDER.length];
  applyTheme(next);
}

function showToast(message, tone = "ok", duration = 4200) {
  if (!toastRegion || typeof message !== "string" || !message.trim()) {
    return;
  }
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.setAttribute("role", "status");
  if (tone) {
    toast.dataset.tone = tone;
  }

  const dot = document.createElement("span");
  dot.className = "toast-dot";
  dot.setAttribute("aria-hidden", "true");

  const body = document.createElement("span");
  body.className = "toast-body";
  body.textContent = message;

  const close = document.createElement("button");
  close.className = "toast-close";
  close.type = "button";
  close.setAttribute("aria-label", "Закрыть уведомление");
  close.textContent = "×";
  close.addEventListener("click", () => toast.remove());

  toast.append(dot, body, close);
  toastRegion.append(toast);

  if (Number.isFinite(duration) && duration > 0) {
    window.setTimeout(() => {
      toast.remove();
    }, duration);
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

function triggerJsonDownload(blob, suggestedName) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = suggestedName;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

async function exportQuizAsJson() {
  if (!editorState.lastGeneratedQuizId) {
    showToast("Сначала сгенерируйте или загрузите квиз.", "warn");
    return;
  }
  try {
    const exportController = new AbortController();
    const exportTimeoutId = window.setTimeout(
      () => exportController.abort(),
      client.timeouts.quizEditor,
    );
    let response;
    try {
      response = await fetch(
        `${backendBaseUrl}/quizzes/${encodeURIComponent(editorState.lastGeneratedQuizId)}/export/json`,
        { headers: { Accept: "application/json" }, signal: exportController.signal },
      );
    } finally {
      window.clearTimeout(exportTimeoutId);
    }
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const blob = await response.blob();
    triggerJsonDownload(blob, `${editorState.lastGeneratedQuizId}.json`);
    showToast("JSON-файл квиза скачан.", "ok");
  } catch (error) {
    showToast(`Не удалось скачать JSON: ${describeError(error)}`, "bad");
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

applyTheme(resolveStoredTheme());
themeToggleButton?.addEventListener("click", cycleTheme);
attachDropzone();
exportJsonButton?.addEventListener("click", exportQuizAsJson);
editShortcutButton?.addEventListener("click", openEditorForCurrentQuiz);

fileInput?.addEventListener("change", () => {
  updateSelectedFileSummary();
  if (fileInput.files?.[0]) {
    advanceStepper("params");
  }
});
form?.addEventListener("submit", submitGeneration);
quizEditorLoader?.addEventListener("submit", loadQuizForEditing);
quizEditorFields?.addEventListener("input", markEditorDirty);
quizEditorFields?.addEventListener("change", markEditorDirty);
saveQuizButton?.addEventListener("click", submitQuizEdits);

bootstrapShell();
