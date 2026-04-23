import { QuizCraftApiError } from "./api/client.js";

export function cloneQuizPayload(quiz) {
  if (typeof structuredClone === "function") {
    return structuredClone(quiz);
  }
  return JSON.parse(JSON.stringify(quiz));
}

export function createQuizEditor({
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
  advanceStepper,
  showToast,
  describeError,
  describeValidationError,
}, documentRef = document) {
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

  function setQuizEditorSummary(quiz) {
    setTextContent("editor-quiz-id", quiz.quiz_id ?? "Ещё не загружен");
    setTextContent("editor-document-id", quiz.document_id ?? "Ещё не загружен");
    setTextContent("editor-quiz-version", Number.isInteger(quiz.version) ? String(quiz.version) : "Ещё не загружен");
    setTextContent("editor-last-edited", quiz.last_edited_at || "Ещё не загружен");
  }

  function clearQuizEditor() {
    editorState.loadedQuiz = null;
    editorState.isDirty = false;
    setQuizEditorSummary({});
    setEditorSaveState({ disabled: true });
    if (quizEditorFields) {
      const placeholder = documentRef.createElement("p");
      placeholder.className = "field-hint";
      placeholder.textContent = "После загрузки квиза здесь появятся редактируемые поля.";
      quizEditorFields.replaceChildren(placeholder);
    }
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

  function buildQuestionEditor(question, index) {
    const article = documentRef.createElement("article");
    article.className = "editor-card";
    article.dataset.questionId = question.question_id ?? `question-${index + 1}`;

    const header = documentRef.createElement("div");
    header.className = "editor-card-header";

    const badge = documentRef.createElement("span");
    badge.className = "question-index";
    badge.textContent = `Вопрос ${index + 1}`;

    const note = documentRef.createElement("p");
    note.className = "panel-copy";
    note.textContent = "После редактирования это содержимое можно сохранить в backend.";

    header.append(badge, note);
    article.append(header);

    const promptField = createEditorField("Текст вопроса", createEditorTextarea(question.prompt ?? "", 3));
    promptField.querySelector("textarea")?.setAttribute("data-editor-field", "prompt");
    article.append(promptField);

    const optionsGrid = documentRef.createElement("div");
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

    const fragment = documentRef.createDocumentFragment();
    const titleField = createEditorField("Заголовок квиза", createEditorInput(quiz.title ?? ""));
    titleField.querySelector("input")?.setAttribute("data-editor-field", "title");
    fragment.append(titleField);

    const questions = Array.isArray(quiz.questions) ? quiz.questions : [];
    questions.forEach((question, index) => {
      fragment.append(buildQuestionEditor(question, index));
    });

    const note = documentRef.createElement("p");
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

  return {
    clearQuizEditor,
    renderQuizEditor,
    setQuizEditorSummary,
    setEditorBusyState,
    setEditorSaveState,
    markEditorDirty,
    buildQuizUpdatePayload,
    loadQuizForEditing,
    submitQuizEdits,
  };
}
