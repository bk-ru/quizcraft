import { QuizCraftApiError } from "./api/client.js";
import {
  addMatchingPair,
  changeQuestionType,
  createEmptyQuestion,
  duplicateQuestion,
  moveQuestionById,
  removeMatchingPair,
  validateEditableQuiz,
} from "./question-shape.js";
import { createUndoStack } from "./undo-stack.js";

export function cloneQuizPayload(quiz) {
  if (typeof structuredClone === "function") {
    return structuredClone(quiz);
  }
  return JSON.parse(JSON.stringify(quiz));
}

const REGENERATE_CONFIRM_TITLE = "Перегенерировать вопрос?";
const REGENERATE_CONFIRM_BODY =
  "Текущий текст вопроса, ответы и пояснение будут заменены новой версией. Несохранённые правки других вопросов останутся без изменений.";
const REGENERATE_CONFIRM_LABEL = "Перегенерировать";
const REGENERATE_CONFIRM_CANCEL_LABEL = "Оставить как есть";

function defaultConfirmAction() {
  return Promise.resolve(true);
}

const DEFAULT_REGENERATION_LANGUAGE = "ru";
const CHOICE_QUESTION_TYPES = Object.freeze(["single_choice", "true_false"]);
const QUESTION_TYPE_LABELS = Object.freeze({
  single_choice: "Одиночный выбор",
  true_false: "Верно / Неверно",
  fill_blank: "Заполнить пропуск",
  short_answer: "Краткий ответ",
  matching: "Сопоставление",
});
const STRUCTURAL_ACTIONS = new Set([
  "change-question-type",
  "duplicate-question",
  "delete-question",
  "move-question-up",
  "move-question-down",
  "add-question",
  "add-option",
  "delete-option",
  "add-matching-pair",
  "delete-matching-pair",
  "undo-structural-edit",
]);

export function createQuizEditor({
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
  advanceStepper,
  renderQuizResult,
  showToast,
  describeError,
  describeValidationError,
  saveQuizToHistory,
  getLanguageForQuiz,
  confirmAction,
}, documentRef = document) {
  const askForConfirmation = typeof confirmAction === "function" ? confirmAction : defaultConfirmAction;
  const lookupLanguage = typeof getLanguageForQuiz === "function" ? getLanguageForQuiz : null;
  const undoStack = createUndoStack({});
  let activeRegenerationController = null;
  let savedQuiz = null;
  let currentClientQuiz = null;
  let fieldEditTimer = null;
  let fieldEditOpen = false;

  function updateUndoButtonState() {
    if (undoQuizEditButton) {
      undoQuizEditButton.disabled = !undoStack.canUndo;
    }
  }

  function setStructuralControlState(hasQuiz) {
    if (addQuestionButton) {
      addQuestionButton.disabled = !hasQuiz;
    }
    if (addQuestionTypeSelect) {
      addQuestionTypeSelect.disabled = !hasQuiz;
    }
    updateUndoButtonState();
  }

  function closeFieldEditGroup() {
    if (fieldEditTimer) {
      clearTimeout(fieldEditTimer);
      fieldEditTimer = null;
    }
    fieldEditOpen = false;
  }

  function resetUndoHistory() {
    closeFieldEditGroup();
    undoStack.clear();
    updateUndoButtonState();
  }

  function pushUndoSnapshot(snapshot) {
    if (!snapshot) {
      return;
    }
    undoStack.push(snapshot);
    updateUndoButtonState();
  }

  function isSavedQuiz(quiz) {
    return Boolean(savedQuiz) && JSON.stringify(quiz) === JSON.stringify(savedQuiz);
  }

  function refreshQuestionDirtyStates(quiz) {
    const savedQuestions = Array.isArray(savedQuiz?.questions) ? savedQuiz.questions : [];
    const questions = Array.isArray(quiz?.questions) ? quiz.questions : [];
    quizEditorFields?.querySelectorAll(".editor-card").forEach((card, index) => {
      const question = questions[index];
      const savedQuestion = savedQuestions.find((candidate) => candidate.question_id === question?.question_id);
      const isDirty = Boolean(savedQuestion) && JSON.stringify(question) !== JSON.stringify(savedQuestion);
      card.classList.toggle("is-dirty", isDirty);
      const revertButton = card.querySelector('[data-editor-action="revert-question"]');
      if (revertButton instanceof HTMLButtonElement) {
        revertButton.hidden = !isDirty;
      }
    });
  }

  function setLocalQuizState(quiz, message) {
    renderQuizEditor(quiz);
    const hasUnsavedChanges = !isSavedQuiz(quiz);
    editorState.isDirty = hasUnsavedChanges;
    refreshQuestionDirtyStates(quiz);
    setEditorSaveState({ disabled: !hasUnsavedChanges });
    setEditorStatus(
      hasUnsavedChanges ? message : "Все локальные изменения отменены.",
      hasUnsavedChanges ? "warn" : "ok",
    );
    updateUndoButtonState();
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
    const isDisabled = Boolean(disabled);
    saveQuizButton.disabled = isDisabled;
    saveQuizButton.textContent = busy ? "Сохраняем…" : "Сохранить изменения";
    if (isDisabled) {
      saveQuizButton.setAttribute("aria-describedby", "save-quiz-hint");
    } else {
      saveQuizButton.removeAttribute("aria-describedby");
    }
  }

  function setRegenerationActionState(card, { busy, text, tone } = {}) {
    const button = card?.querySelector('[data-editor-action="regenerate-question"]');
    const cancelButton = card?.querySelector('[data-editor-action="cancel-regenerate-question"]');
    const status = card?.querySelector('[data-regeneration-status="question"]');
    if (button instanceof HTMLButtonElement) {
      button.hidden = Boolean(busy);
    }
    if (cancelButton instanceof HTMLButtonElement) {
      cancelButton.hidden = !busy;
      cancelButton.disabled = !busy;
    }
    if (status instanceof HTMLElement) {
      status.textContent = text ?? "";
      status.hidden = !text;
      if (tone) {
        status.dataset.statusTone = tone;
      } else {
        delete status.dataset.statusTone;
      }
    }
    card?.classList.toggle("is-regenerating", Boolean(busy));
    const body = card?.querySelector(".editor-card-body");
    if (body instanceof HTMLElement) {
      body.setAttribute("aria-busy", String(Boolean(busy)));
    }
  }

  function cancelActiveRegeneration() {
    if (!activeRegenerationController || activeRegenerationController.signal.aborted) {
      return false;
    }
    activeRegenerationController.abort();
    return true;
  }

  function markEditorDirty(event) {
    if (!editorState.loadedQuiz) {
      return;
    }
    const target = event?.target instanceof Element ? event.target : null;
    if (target?.matches('[data-editor-action="change-question-type"]')) {
      return;
    }
    if (!fieldEditOpen) {
      pushUndoSnapshot(currentClientQuiz ?? buildQuizUpdatePayload());
      fieldEditOpen = true;
    }
    currentClientQuiz = buildQuizUpdatePayload();
    if (fieldEditTimer) {
      clearTimeout(fieldEditTimer);
    }
    fieldEditTimer = setTimeout(closeFieldEditGroup, 350);
    editorState.isDirty = true;
    setEditorSaveState({ disabled: false });
    setEditorStatus("Изменения пока не сохранены.", "warn");
    const card = event?.target instanceof Element
      ? event.target.closest(".editor-card")
      : null;
    if (card instanceof HTMLElement) {
      updateCorrectOptionState(card);
      card.classList.add("is-dirty");
      const revertBtn = card.querySelector('[data-editor-action="revert-question"]');
      if (revertBtn) {
        revertBtn.hidden = false;
      }
    }
  }

  function updateCorrectOptionState(card) {
    const select = card?.querySelector('[data-editor-field="correct-option-index"]');
    const selectedIndex = select instanceof HTMLSelectElement
      ? Number.parseInt(select.value, 10)
      : -1;
    card?.querySelectorAll(".editor-option-row").forEach((row, optionIndex) => {
      if (optionIndex === selectedIndex) {
        row.dataset.correct = "true";
      } else {
        delete row.dataset.correct;
      }
    });
  }

  function revertQuestionEdits(event) {
    const action = event?.target instanceof Element
      ? event.target.closest('[data-editor-action="revert-question"]')
      : null;
    if (!(action instanceof HTMLButtonElement)) {
      return;
    }
    event.preventDefault();
    const card = action.closest(".editor-card");
    if (!(card instanceof HTMLElement) || !editorState.loadedQuiz) {
      return;
    }
    const questionId = card.dataset.questionId;
    const questions = Array.isArray(savedQuiz?.questions)
      ? savedQuiz.questions
      : [];
    const original = questions.find((q) => q.question_id === questionId);
    if (!original) {
      return;
    }
    const questionCards = Array.from(quizEditorFields.querySelectorAll(".editor-card"));
    const index = questionCards.indexOf(card);
    const freshCard = buildQuestionEditor(original, index, questionCards.length);
    card.replaceWith(freshCard);
    currentClientQuiz = buildQuizUpdatePayload();
    editorState.isDirty = !isSavedQuiz(currentClientQuiz);
    refreshQuestionDirtyStates(currentClientQuiz);
    setEditorSaveState({ disabled: !editorState.isDirty });
    if (!editorState.isDirty) {
      setEditorStatus("Квиз загружен в режим редактирования. Можно вносить изменения и сохранять их.", "ok");
    }
  }

  function setQuizEditorSummary(quiz) {
    setTextContent("editor-quiz-id", quiz.quiz_id ?? "Ещё не загружен");
    setTextContent("editor-document-id", quiz.document_id ?? "Ещё не загружен");
    setTextContent("editor-quiz-version", Number.isInteger(quiz.version) ? String(quiz.version) : "Ещё не загружен");
    setTextContent("editor-last-edited", quiz.last_edited_at || "Ещё не загружен");
  }

  function clearQuizEditor() {
    editorState.loadedQuiz = null;
    editorState.isDirty = false;
    editorState.loadedQuizLanguage = null;
    savedQuiz = null;
    currentClientQuiz = null;
    resetUndoHistory();
    setStructuralControlState(false);
    setQuizEditorSummary({});
    setEditorSaveState({ disabled: true });
    if (quizEditorFields) {
      const placeholder = documentRef.createElement("p");
      placeholder.className = "field-hint";
      placeholder.textContent = "После загрузки квиза здесь появятся редактируемые поля.";
      quizEditorFields.replaceChildren(placeholder);
    }
  }

  function resolveQuizLanguage(quizId) {
    if (lookupLanguage) {
      const recovered = lookupLanguage(quizId);
      if (typeof recovered === "string" && recovered.trim()) {
        return recovered.trim();
      }
    }
    return DEFAULT_REGENERATION_LANGUAGE;
  }

  function createEditorField(labelText, control) {
    const wrapper = documentRef.createElement("label");
    wrapper.className = "field";

    const label = documentRef.createElement("span");
    label.className = "field-label";
    label.textContent = labelText;

    wrapper.append(label, control);
    return wrapper;
  }

  function createEditorInput(value) {
    const input = documentRef.createElement("input");
    input.type = "text";
    input.value = typeof value === "string" ? value : "";
    return input;
  }

  function createEditorTextarea(value, rows = 3) {
    const textarea = documentRef.createElement("textarea");
    textarea.rows = rows;
    textarea.value = typeof value === "string" ? value : "";
    return textarea;
  }

  function populateQuestionTypeOptions(select, selectedType) {
    Object.entries(QUESTION_TYPE_LABELS).forEach(([questionType, label]) => {
      const option = documentRef.createElement("option");
      option.value = questionType;
      option.textContent = label;
      option.selected = questionType === selectedType;
      select.append(option);
    });
  }

  function getAlphabeticBadge(index) {
    let value = index + 1;
    let badge = "";
    while (value > 0) {
      value -= 1;
      badge = String.fromCharCode(65 + (value % 26)) + badge;
      value = Math.floor(value / 26);
    }
    return badge;
  }

  function buildQuestionEditor(question, index, questionCount) {
    const article = documentRef.createElement("article");
    article.className = "editor-card";
    article.dataset.questionId = question.question_id ?? `question-${index + 1}`;

    const header = documentRef.createElement("div");
    header.className = "editor-card-header";

    const badge = documentRef.createElement("span");
    badge.className = "question-index";
    badge.textContent = `Вопрос ${index + 1} · ${QUESTION_TYPE_LABELS[question.question_type] ?? "Тип не указан"}`;

    const questionTypeSelect = documentRef.createElement("select");
    questionTypeSelect.className = "question-type-pill";
    questionTypeSelect.setAttribute("data-editor-action", "change-question-type");
    questionTypeSelect.setAttribute("aria-label", `Изменить тип вопроса ${index + 1}`);
    populateQuestionTypeOptions(questionTypeSelect, question.question_type);

    const note = documentRef.createElement("p");
    note.className = "panel-copy";
    note.textContent = "После редактирования это содержимое можно сохранить.";

    const regenerateButton = documentRef.createElement("button");
    regenerateButton.className = "question-icon-action question-regenerate-action";
    regenerateButton.type = "button";
    regenerateButton.textContent = "↻";
    regenerateButton.setAttribute("data-editor-action", "regenerate-question");
    regenerateButton.dataset.questionId = article.dataset.questionId;
    regenerateButton.setAttribute("aria-label", `Перегенерировать вопрос ${index + 1}`);
    regenerateButton.title = "Перегенерировать вопрос";

    const cancelRegenerateButton = documentRef.createElement("button");
    cancelRegenerateButton.className = "question-icon-action question-regenerate-cancel";
    cancelRegenerateButton.type = "button";
    cancelRegenerateButton.textContent = "■";
    cancelRegenerateButton.setAttribute("data-editor-action", "cancel-regenerate-question");
    cancelRegenerateButton.dataset.questionId = article.dataset.questionId;
    cancelRegenerateButton.setAttribute("aria-label", `Отменить перегенерацию вопроса ${index + 1}`);
    cancelRegenerateButton.title = "Остановить перегенерацию";
    cancelRegenerateButton.hidden = true;
    cancelRegenerateButton.disabled = true;

    const regenerationStatus = documentRef.createElement("span");
    regenerationStatus.className = "question-regenerate-status";
    regenerationStatus.setAttribute("data-regeneration-status", "question");
    regenerationStatus.setAttribute("aria-live", "polite");
    regenerationStatus.hidden = true;

    const revertButton = documentRef.createElement("button");
    revertButton.className = "question-icon-action question-revert-action";
    revertButton.type = "button";
    revertButton.textContent = "↶";
    revertButton.setAttribute("data-editor-action", "revert-question");
    revertButton.dataset.questionId = article.dataset.questionId;
    revertButton.setAttribute("aria-label", `Отменить правки вопроса ${index + 1}`);
    revertButton.title = "Отменить правки вопроса";
    revertButton.hidden = true;

    const duplicateButton = documentRef.createElement("button");
    duplicateButton.className = "ghost-action question-structure-action";
    duplicateButton.type = "button";
    duplicateButton.textContent = "Дублировать";
    duplicateButton.setAttribute("data-editor-action", "duplicate-question");
    duplicateButton.setAttribute("aria-label", `Дублировать вопрос ${index + 1}`);

    const deleteButton = documentRef.createElement("button");
    deleteButton.className = "ghost-action question-structure-action";
    deleteButton.type = "button";
    deleteButton.textContent = "Удалить";
    deleteButton.setAttribute("data-editor-action", "delete-question");
    deleteButton.setAttribute("aria-label", `Удалить вопрос ${index + 1}`);

    const reorderActions = documentRef.createElement("div");
    reorderActions.className = "question-reorder-actions";
    const moveUpButton = documentRef.createElement("button");
    moveUpButton.className = "question-reorder-action";
    moveUpButton.type = "button";
    moveUpButton.textContent = "↑";
    moveUpButton.disabled = index === 0;
    moveUpButton.setAttribute("data-editor-action", "move-question-up");
    moveUpButton.setAttribute("aria-label", `Переместить вопрос ${index + 1} вверх`);
    const moveDownButton = documentRef.createElement("button");
    moveDownButton.className = "question-reorder-action";
    moveDownButton.type = "button";
    moveDownButton.textContent = "↓";
    moveDownButton.disabled = index === questionCount - 1;
    moveDownButton.setAttribute("data-editor-action", "move-question-down");
    moveDownButton.setAttribute("aria-label", `Переместить вопрос ${index + 1} вниз`);
    reorderActions.append(moveUpButton, moveDownButton);

    const cardActions = documentRef.createElement("div");
    cardActions.className = "question-structure-actions";
    cardActions.append(
      questionTypeSelect,
      duplicateButton,
      deleteButton,
      regenerateButton,
      cancelRegenerateButton,
      revertButton,
    );

    header.append(badge, cardActions, note, regenerationStatus);

    const body = documentRef.createElement("div");
    body.className = "editor-card-body";
    body.setAttribute("aria-busy", "false");
    const content = documentRef.createElement("div");
    content.className = "editor-card-content";
    const overlay = documentRef.createElement("div");
    overlay.className = "question-regenerate-overlay";
    overlay.textContent = "Перегенерируем вопрос…";
    overlay.setAttribute("aria-hidden", "true");
    body.append(content, overlay);
    article.append(header, reorderActions, body);

    const promptField = createEditorField("Текст вопроса", createEditorTextarea(question.prompt ?? "", 3));
    promptField.querySelector("textarea")?.setAttribute("data-editor-field", "prompt");
    content.append(promptField);

    const options = Array.isArray(question.options) ? question.options : [];
    if (CHOICE_QUESTION_TYPES.includes(question.question_type ?? "single_choice")) {
      const optionsGrid = documentRef.createElement("div");
      optionsGrid.className = "editor-options";

      options.forEach((option, optionIndex) => {
        const optionRow = documentRef.createElement("div");
        optionRow.className = "editor-option-row";
        const optionField = createEditorField(
          `Вариант ${optionIndex + 1}`,
          createEditorInput(option.text ?? ""),
        );
        optionField.dataset.optionId = option.option_id ?? `option-${optionIndex + 1}`;
        optionField.querySelector("input")?.setAttribute("data-editor-field", "option-text");
        optionField.querySelector("input")?.setAttribute("data-option-id", option.option_id ?? `option-${optionIndex + 1}`);
        const deleteOptionButton = documentRef.createElement("button");
        deleteOptionButton.className = "option-delete-action";
        deleteOptionButton.type = "button";
        deleteOptionButton.textContent = "×";
        deleteOptionButton.setAttribute("aria-label", `Удалить вариант ${optionIndex + 1}`);
        deleteOptionButton.setAttribute("data-editor-action", "delete-option");
        deleteOptionButton.dataset.optionIndex = String(optionIndex);
        deleteOptionButton.disabled = question.question_type === "true_false";
        deleteOptionButton.title = deleteOptionButton.disabled
          ? "Для формата «Верно / Неверно» используются фиксированные варианты."
          : "Удалить вариант ответа.";
        optionRow.append(optionField, deleteOptionButton);
        optionsGrid.append(optionRow);
      });
      content.append(optionsGrid);

      if (question.question_type === "single_choice") {
        const addOptionButton = documentRef.createElement("button");
        addOptionButton.className = "ghost-action question-option-add";
        addOptionButton.type = "button";
        addOptionButton.textContent = "Добавить вариант";
        addOptionButton.disabled = options.length >= 4;
        addOptionButton.setAttribute("data-editor-action", "add-option");
        content.append(addOptionButton);
      }

      const correctAnswerSelect = documentRef.createElement("select");
      options.forEach((option, optionIndex) => {
        const selectOption = documentRef.createElement("option");
        selectOption.value = String(optionIndex);
        selectOption.textContent = `Вариант ${optionIndex + 1}: ${option.text ?? ""}`;
        if (optionIndex === question.correct_option_index) {
          selectOption.selected = true;
        }
        correctAnswerSelect.append(selectOption);
      });
      correctAnswerSelect.setAttribute("data-editor-field", "correct-option-index");
      content.append(createEditorField("Правильный ответ", correctAnswerSelect));
      updateCorrectOptionState(article);
    } else if (question.question_type === "matching") {
      const pairsGrid = documentRef.createElement("div");
      pairsGrid.className = "matching-pairs-editor";
      const pairs = Array.isArray(question.matching_pairs) ? question.matching_pairs : [];
      pairs.forEach((pair, pairIndex) => {
        const pairRow = documentRef.createElement("div");
        pairRow.className = "matching-pair-row";
        const leftField = createEditorField(`Левая часть ${pairIndex + 1}`, createEditorInput(pair.left ?? ""));
        leftField.classList.add("matching-pair-cell");
        leftField.querySelector("input")?.setAttribute("data-editor-field", "matching-left");
        leftField.querySelector("input")?.setAttribute("aria-label", `Левая часть пары ${pairIndex + 1}`);
        const leftBadge = documentRef.createElement("span");
        leftBadge.className = "matching-pair-badge";
        leftBadge.textContent = String(pairIndex + 1);
        leftField.querySelector(".field-label")?.after(leftBadge);

        const link = documentRef.createElement("span");
        link.className = "matching-pair-link";
        link.textContent = "↔";
        link.setAttribute("aria-hidden", "true");

        const rightField = createEditorField(`Правая часть ${pairIndex + 1}`, createEditorInput(pair.right ?? ""));
        rightField.classList.add("matching-pair-cell");
        rightField.querySelector("input")?.setAttribute("data-editor-field", "matching-right");
        rightField.querySelector("input")?.setAttribute("aria-label", `Правая часть пары ${pairIndex + 1}`);
        const rightBadge = documentRef.createElement("span");
        rightBadge.className = "matching-pair-badge";
        rightBadge.textContent = getAlphabeticBadge(pairIndex);
        rightField.querySelector(".field-label")?.after(rightBadge);

        const deletePairButton = documentRef.createElement("button");
        deletePairButton.className = "matching-pair-delete";
        deletePairButton.type = "button";
        deletePairButton.textContent = "×";
        deletePairButton.disabled = pairs.length <= 4;
        deletePairButton.dataset.pairIndex = String(pairIndex);
        deletePairButton.setAttribute("data-editor-action", "delete-matching-pair");
        deletePairButton.setAttribute("aria-label", `Удалить пару ${pairIndex + 1}`);
        deletePairButton.title = deletePairButton.disabled
          ? "Для сопоставления нужны минимум 4 пары."
          : "Удалить пару.";

        pairRow.append(leftField, link, rightField, deletePairButton);
        pairsGrid.append(pairRow);
      });
      content.append(pairsGrid);

      const addPairButton = documentRef.createElement("button");
      addPairButton.className = "ghost-action matching-pair-add";
      addPairButton.type = "button";
      addPairButton.textContent = "Добавить пару";
      addPairButton.setAttribute("data-editor-action", "add-matching-pair");
      content.append(addPairButton);
    } else {
      const correctAnswerField = createEditorField("Правильный ответ", createEditorInput(question.correct_answer ?? ""));
      correctAnswerField.querySelector("input")?.setAttribute("data-editor-field", "correct-answer");
      content.append(correctAnswerField);
    }

    const explanationText = question.explanation?.text ?? "";
    const explanationField = createEditorField("Пояснение", createEditorTextarea(explanationText, 4));
    explanationField.querySelector("textarea")?.setAttribute("data-editor-field", "explanation");
    content.append(explanationField);

    return article;
  }

  function normalizeRegeneratedQuestion(regeneratedQuestion, stableQuestion) {
    const questionType = regeneratedQuestion?.question_type ?? stableQuestion?.question_type;
    const normalized = {
      ...cloneQuizPayload(stableQuestion),
      ...cloneQuizPayload(regeneratedQuestion),
      question_type: questionType,
      prompt: typeof regeneratedQuestion?.prompt === "string" ? regeneratedQuestion.prompt : "",
      explanation: regeneratedQuestion?.explanation?.text
        ? { text: regeneratedQuestion.explanation.text }
        : null,
      options: Array.isArray(regeneratedQuestion?.options)
        ? regeneratedQuestion.options.map((option) => ({
          option_id: option.option_id,
          text: option.text ?? "",
        }))
        : [],
      matching_pairs: Array.isArray(regeneratedQuestion?.matching_pairs)
        ? regeneratedQuestion.matching_pairs.map((pair) => ({
          left: pair.left ?? "",
          right: pair.right ?? "",
        }))
        : [],
    };
    if (CHOICE_QUESTION_TYPES.includes(questionType)) {
      normalized.correct_answer = null;
      normalized.matching_pairs = [];
    } else if (questionType === "matching") {
      normalized.options = [];
      normalized.correct_option_index = null;
      normalized.correct_answer = null;
    } else {
      normalized.options = [];
      normalized.correct_option_index = null;
      normalized.matching_pairs = [];
    }
    return normalized;
  }

  function restoreStableQuestionCard(card, stableQuestion) {
    if (!(card instanceof HTMLElement) || !stableQuestion || !quizEditorFields) {
      return null;
    }
    const questionCards = Array.from(quizEditorFields.querySelectorAll(".editor-card"));
    const index = questionCards.indexOf(card);
    if (index < 0) {
      return null;
    }
    const freshCard = buildQuestionEditor(stableQuestion, index, questionCards.length);
    card.replaceWith(freshCard);
    currentClientQuiz = buildQuizUpdatePayload();
    editorState.isDirty = !isSavedQuiz(currentClientQuiz);
    refreshQuestionDirtyStates(currentClientQuiz);
    setEditorSaveState({ disabled: !editorState.isDirty });
    return freshCard;
  }

  function replaceRegeneratedQuestion(quiz, regeneratedQuestion) {
    const updatedQuiz = cloneQuizPayload(quiz);
    const questions = Array.isArray(updatedQuiz.questions) ? updatedQuiz.questions : [];
    const hasTargetQuestion = questions.some((question) => (
      question.question_id === regeneratedQuestion.question_id
    ));
    if (!hasTargetQuestion) {
      throw new Error("Backend вернул вопрос, которого нет в текущем квизе.");
    }
    updatedQuiz.questions = questions.map((question) => {
      if (question.question_id === regeneratedQuestion.question_id) {
        return regeneratedQuestion;
      }
      return question;
    });
    return updatedQuiz;
  }

  function renderQuizEditor(quiz) {
    if (!quizEditorFields) {
      return;
    }

    const fragment = documentRef.createDocumentFragment();
    const titleField = createEditorField("Заголовок квиза", createEditorInput(quiz.title ?? ""));
    titleField.querySelector("input")?.setAttribute("data-editor-field", "title");
    fragment.append(titleField);

    const questions = Array.isArray(quiz.questions) ? quiz.questions : [];
    questions.forEach((question, index) => {
      fragment.append(buildQuestionEditor(question, index, questions.length));
    });

    const note = documentRef.createElement("p");
    note.className = "editor-readonly-note";
    note.textContent = "Изменения пока не сохранены.";
    fragment.append(note);

    quizEditorFields.replaceChildren(fragment);
    editorState.loadedQuiz = cloneQuizPayload(quiz);
    currentClientQuiz = cloneQuizPayload(quiz);
    editorState.isDirty = false;
    quizEditorFields.querySelectorAll(".editor-card.is-dirty").forEach((c) => c.classList.remove("is-dirty"));
    setEditorSaveState({ disabled: true });
    setStructuralControlState(true);
  }

  function presentQuizInline(quiz, { language } = {}) {
    resetUndoHistory();
    savedQuiz = cloneQuizPayload(quiz);
    renderQuizEditor(quiz);
    setQuizEditorSummary(quiz);
    editorState.loadedQuizLanguage = resolveQuizLanguage(quiz.quiz_id);
    if (typeof language === "string" && language.trim()) {
      editorState.loadedQuizLanguage = language.trim();
    }
    advanceStepper("result");
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
      const correctAnswerInput = card.querySelector('[data-editor-field="correct-answer"]');
      const explanationInput = card.querySelector('[data-editor-field="explanation"]');
      const optionInputs = Array.from(card.querySelectorAll('[data-editor-field="option-text"]'));
      const matchingLeftInputs = Array.from(card.querySelectorAll('[data-editor-field="matching-left"]'));
      const matchingRightInputs = Array.from(card.querySelectorAll('[data-editor-field="matching-right"]'));

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
        correct_answer: correctAnswerInput instanceof HTMLInputElement
          ? correctAnswerInput.value
          : baseQuestion.correct_answer,
        matching_pairs: matchingLeftInputs.map((leftInput, pairIndex) => ({
          ...(baseQuestion.matching_pairs?.[pairIndex] ?? {}),
          left: leftInput instanceof HTMLInputElement ? leftInput.value : baseQuestion.matching_pairs?.[pairIndex]?.left,
          right: matchingRightInputs[pairIndex] instanceof HTMLInputElement
            ? matchingRightInputs[pairIndex].value
            : baseQuestion.matching_pairs?.[pairIndex]?.right,
        })),
        explanation: (() => {
          const text = explanationInput instanceof HTMLTextAreaElement
            ? explanationInput.value.trim()
            : (baseQuestion.explanation?.text ?? "").trim();
          return text ? { text } : null;
        })(),
      };
    });

    return quiz;
  }

  async function handleStructuralAction(event) {
    const action = event?.target instanceof Element
      ? event.target.closest("[data-editor-action]")
      : null;
    const actionName = action?.getAttribute("data-editor-action") ?? "";
    if (!STRUCTURAL_ACTIONS.has(actionName) || actionName === "undo-structural-edit") {
      return;
    }
    if (actionName === "change-question-type" && event.type !== "change") {
      return;
    }
    if (actionName !== "change-question-type" && event.type === "change") {
      return;
    }
    event.preventDefault();
    if (!editorState.loadedQuiz) {
      setEditorStatus("Сначала откройте или сгенерируйте квиз.", "bad");
      return;
    }

    closeFieldEditGroup();
    const snapshot = buildQuizUpdatePayload();
    const updatedQuiz = cloneQuizPayload(snapshot);
    const questions = Array.isArray(updatedQuiz.questions) ? updatedQuiz.questions : [];
    const card = action.closest(".editor-card");
    const questionId = card instanceof HTMLElement ? card.dataset.questionId : "";
    const questionIndex = questions.findIndex((question) => question?.question_id === questionId);
    const question = questionIndex >= 0 ? questions[questionIndex] : null;

    if (actionName === "add-question") {
      const questionType = addQuestionTypeSelect?.value || "single_choice";
      questions.push(createEmptyQuestion(questionType));
    } else if (actionName === "change-question-type" && question && action instanceof HTMLSelectElement) {
      questions[questionIndex] = changeQuestionType(question, action.value);
    } else if (actionName === "duplicate-question" && question) {
      questions.splice(questionIndex + 1, 0, duplicateQuestion(question));
    } else if (actionName === "delete-question" && question) {
      const confirmed = await askForConfirmation({
        title: "Удалить вопрос?",
        body: "Вопрос будет удалён из текущего черновика. При необходимости действие можно отменить верхней кнопкой.",
        confirmLabel: "Удалить",
        cancelLabel: "Оставить вопрос",
        tone: "warn",
      });
      if (!confirmed) {
        return;
      }
      questions.splice(questionIndex, 1);
    } else if (actionName === "move-question-up" && question) {
      updatedQuiz.questions = moveQuestionById(questions, question.question_id, "up");
    } else if (actionName === "move-question-down" && question) {
      updatedQuiz.questions = moveQuestionById(questions, question.question_id, "down");
    } else if (actionName === "delete-option" && question?.question_type === "single_choice") {
      const optionIndex = Number.parseInt(action.dataset.optionIndex ?? "", 10);
      if (!Number.isInteger(optionIndex) || optionIndex < 0 || optionIndex >= question.options.length) {
        return;
      }
      question.options.splice(optionIndex, 1);
      if (question.correct_option_index > optionIndex) {
        question.correct_option_index -= 1;
      } else if (question.correct_option_index === optionIndex) {
        question.correct_option_index = question.options.length > 0 ? 0 : null;
      }
    } else if (actionName === "add-option" && question?.question_type === "single_choice" && question.options.length < 4) {
      question.options.push(createEmptyQuestion("single_choice").options[0]);
    } else if (actionName === "add-matching-pair" && question?.question_type === "matching") {
      questions[questionIndex] = addMatchingPair(question);
    } else if (actionName === "delete-matching-pair" && question?.question_type === "matching") {
      const pairIndex = Number.parseInt(action.dataset.pairIndex ?? "", 10);
      const updatedQuestion = removeMatchingPair(question, pairIndex);
      if (updatedQuestion === question) {
        setEditorStatus("Для сопоставления нужны минимум 4 пары.", "warn");
        return;
      }
      questions[questionIndex] = updatedQuestion;
    } else {
      return;
    }

    if (JSON.stringify(updatedQuiz) === JSON.stringify(snapshot)) {
      return;
    }
    pushUndoSnapshot(snapshot);
    setLocalQuizState(updatedQuiz, "Структура квиза изменена. Сохраните изменения после проверки.");
  }

  function undoLastStructuralEdit(event) {
    event?.preventDefault();
    closeFieldEditGroup();
    const snapshot = undoStack.pop();
    if (!snapshot) {
      return false;
    }
    setLocalQuizState(snapshot, "Последнее изменение отменено. Проверьте квиз перед сохранением.");
    return true;
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

      presentQuizInline(quiz, { language: payload.language });
      setEditorStatus("Квиз загружен в режим редактирования. Можно вносить изменения и сохранять их.", "ok");
      setExportAvailability(payload.quiz_id ?? quiz.quiz_id ?? quizId);
      if (typeof saveQuizToHistory === "function") {
        saveQuizToHistory({
          quiz_id: payload.quiz_id ?? quiz.quiz_id ?? quizId,
          title: quiz.title,
        });
      }
      showToast("Квиз загружен в редактор.", "ok");
      setLogMessage("Квиз открыт в редакторе.", "ok");
    } catch (error) {
      setEditorStatus(`Не удалось открыть квиз: ${describeError(error)}`, "bad");
      setEditorSaveState({ disabled: true });
    } finally {
      setEditorBusyState(false);
    }
  }

  async function regenerateQuizQuestion(event) {
    const action = event.target instanceof Element
      ? event.target.closest('[data-editor-action="regenerate-question"]')
      : null;
    if (!(action instanceof HTMLButtonElement)) {
      return;
    }

    event.preventDefault();
    const card = action.closest(".editor-card");
    const quizId = editorState.loadedQuiz?.quiz_id;
    const questionId = typeof action.dataset.questionId === "string" ? action.dataset.questionId.trim() : "";
    if (!quizId || !questionId || !(card instanceof HTMLElement)) {
      setEditorStatus("Сначала откройте сохранённый квиз и выберите вопрос для перегенерации.", "bad");
      return;
    }
    if (activeRegenerationController && !activeRegenerationController.signal.aborted) {
      setEditorStatus("Дождитесь завершения текущей перегенерации или остановите её.", "warn");
      showToast("Уже выполняется перегенерация другого вопроса.", "warn");
      return;
    }

    const confirmed = await askForConfirmation({
      title: REGENERATE_CONFIRM_TITLE,
      body: REGENERATE_CONFIRM_BODY,
      confirmLabel: REGENERATE_CONFIRM_LABEL,
      cancelLabel: REGENERATE_CONFIRM_CANCEL_LABEL,
      tone: "warn",
    });
    if (!confirmed) {
      setEditorStatus("Перегенерация отменена. Текущий вопрос остался без изменений.", "warn");
      return;
    }

    const abortController = new AbortController();
    activeRegenerationController = abortController;
    let stableQuestion = null;
    try {
      const hadUnsavedEdits = editorState.isDirty;
      const displayedQuiz = buildQuizUpdatePayload();
      const displayedQuestion = displayedQuiz.questions.find((question) => question.question_id === questionId);
      if (!displayedQuestion) {
        throw new Error("Не удалось найти вопрос в текущем квизе.");
      }
      stableQuestion = cloneQuizPayload(displayedQuestion);
      setRegenerationActionState(card, {
        busy: true,
        text: "Перегенерируем вопрос…",
        tone: "warn",
      });
      setEditorStatus("Перегенерируем один вопрос. Остальные вопросы останутся без изменений.", "warn");
      const language = typeof editorState.loadedQuizLanguage === "string" && editorState.loadedQuizLanguage.trim()
        ? editorState.loadedQuizLanguage.trim()
        : resolveQuizLanguage(quizId);
      const response = await client.regenerateQuestion(
        quizId,
        questionId,
        {
          quiz_id: quizId,
          question_id: questionId,
          language,
        },
        { signal: abortController.signal },
      );
      const regeneratedQuestion = response.regenerated_question;
      if (!regeneratedQuestion?.question_id) {
        throw new Error("Backend не вернул обновлённый вопрос.");
      }
      const normalizedRegeneratedQuestion = normalizeRegeneratedQuestion(regeneratedQuestion, stableQuestion);
      const persistedQuiz = response.quiz ?? editorState.loadedQuiz;
      const updatedQuiz = replaceRegeneratedQuestion({
        ...displayedQuiz,
        quiz_id: persistedQuiz.quiz_id ?? displayedQuiz.quiz_id,
        document_id: persistedQuiz.document_id ?? displayedQuiz.document_id,
        version: persistedQuiz.version ?? displayedQuiz.version,
        last_edited_at: persistedQuiz.last_edited_at ?? displayedQuiz.last_edited_at,
      }, normalizedRegeneratedQuestion);

      pushUndoSnapshot(displayedQuiz);
      savedQuiz = cloneQuizPayload(response.quiz ?? updatedQuiz);
      renderQuizEditor(updatedQuiz);
      refreshQuestionDirtyStates(updatedQuiz);
      setQuizEditorSummary(updatedQuiz);
      setTextContent("last-quiz-id", response.quiz_id ?? updatedQuiz.quiz_id ?? quizId);
      setTextContent("last-request-id", response.request_id ?? "Ещё нет");
      setExportAvailability(response.quiz_id ?? updatedQuiz.quiz_id ?? quizId);
      if (typeof renderQuizResult === "function") {
        renderQuizResult({
          ...response,
          quiz_id: response.quiz_id ?? updatedQuiz.quiz_id ?? quizId,
          quiz: updatedQuiz,
        });
      }
      if (hadUnsavedEdits) {
        editorState.isDirty = true;
        setEditorSaveState({ disabled: false });
        setEditorStatus(
          "Вопрос перегенерирован. Несохранённые правки в остальных полях сохранены локально; сохраните квиз, чтобы применить их.",
          "warn",
        );
      } else {
        setEditorStatus("Вопрос перегенерирован. Остальные вопросы сохранены без изменений.", "ok");
      }
      showToast("Вопрос перегенерирован.", "ok");
      setLogMessage(
        "Вопрос перегенерирован; остальные вопросы и кириллица сохранены без изменений.",
        "ok",
      );
    } catch (error) {
      const wasCancelled = abortController.signal.aborted
        && error instanceof QuizCraftApiError
        && error.status === 0;
      const restoredCard = stableQuestion ? restoreStableQuestionCard(card, stableQuestion) : card;
      if (wasCancelled) {
        setRegenerationActionState(restoredCard, {
          busy: false,
          text: "Регенерация отменена. Вопрос остался без изменений.",
          tone: "warn",
        });
        setEditorStatus("Регенерация отменена пользователем.", "warn");
        showToast("Регенерация вопроса отменена.", "warn");
      } else {
        setRegenerationActionState(restoredCard, {
          busy: false,
          text: `Не удалось перегенерировать вопрос: ${describeError(error)}`,
          tone: "bad",
        });
        setEditorStatus(`Не удалось перегенерировать вопрос: ${describeError(error)}`, "bad");
        showToast("Не удалось перегенерировать вопрос.", "bad");
      }
    } finally {
      if (activeRegenerationController === abortController) {
        activeRegenerationController = null;
      }
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
      const validationErrors = validateEditableQuiz(updatePayload);
      if (validationErrors.length > 0) {
        throw new Error(`Исправьте структуру квиза:\n${validationErrors.join("\n")}`);
      }
      const saveResponse = await client.updateQuiz(editorState.loadedQuiz.quiz_id, { quiz: updatePayload });
      const reloadResponse = await client.getQuiz(saveResponse.quiz_id ?? editorState.loadedQuiz.quiz_id);
      const persistedQuiz = reloadResponse.quiz ?? saveResponse.quiz ?? updatePayload;

      savedQuiz = cloneQuizPayload(persistedQuiz);
      resetUndoHistory();
      renderQuizEditor(persistedQuiz);
      setQuizEditorSummary(persistedQuiz);
      setTextContent("last-quiz-id", reloadResponse.quiz_id ?? saveResponse.quiz_id ?? persistedQuiz.quiz_id ?? "Ещё нет");
      setTextContent("last-request-id", reloadResponse.request_id ?? saveResponse.request_id ?? "Ещё нет");
      setExportAvailability(reloadResponse.quiz_id ?? saveResponse.quiz_id ?? persistedQuiz.quiz_id ?? null);
      if (typeof saveQuizToHistory === "function") {
        saveQuizToHistory({
          quiz_id: reloadResponse.quiz_id ?? saveResponse.quiz_id ?? persistedQuiz.quiz_id,
          title: persistedQuiz.title,
        });
      }
      setEditorStatus("Изменения сохранены.", "ok");
      showToast("Изменения сохранены.", "ok");
      setLogMessage(
        "Изменения квиза сохранены и перечитаны без потери кириллицы.",
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

  return {
    clearQuizEditor,
    renderQuizEditor,
    presentQuizInline,
    setQuizEditorSummary,
    setEditorBusyState,
    setEditorSaveState,
    markEditorDirty,
    revertQuestionEdits,
    handleStructuralAction,
    undoLastStructuralEdit,
    buildQuizUpdatePayload,
    loadQuizForEditing,
    regenerateQuizQuestion,
    cancelActiveRegeneration,
    submitQuizEdits,
  };
}
