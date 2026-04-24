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
  renderQuizResult,
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

  function setRegenerationActionState(card, { busy, text, tone } = {}) {
    const button = card?.querySelector('[data-editor-action="regenerate-question"]');
    const status = card?.querySelector('[data-regeneration-status="question"]');
    if (button instanceof HTMLButtonElement) {
      button.disabled = Boolean(busy);
      button.textContent = busy ? "Перегенерируем вопрос…" : "Перегенерировать вопрос";
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

    const regenerateButton = documentRef.createElement("button");
    regenerateButton.className = "ghost-action question-regenerate-action";
    regenerateButton.type = "button";
    regenerateButton.textContent = "Перегенерировать вопрос";
    regenerateButton.setAttribute("data-editor-action", "regenerate-question");
    regenerateButton.dataset.questionId = article.dataset.questionId;
    regenerateButton.setAttribute("aria-label", `Перегенерировать вопрос ${index + 1}`);

    const regenerationStatus = documentRef.createElement("span");
    regenerationStatus.className = "question-regenerate-status";
    regenerationStatus.setAttribute("data-regeneration-status", "question");
    regenerationStatus.setAttribute("aria-live", "polite");
    regenerationStatus.hidden = true;

    header.append(badge, note, regenerateButton, regenerationStatus);
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

    try {
      const hadUnsavedEdits = editorState.isDirty;
      const displayedQuiz = buildQuizUpdatePayload();
      setRegenerationActionState(card, {
        busy: true,
        text: "Перегенерируем вопрос через backend…",
        tone: "warn",
      });
      setEditorStatus("Перегенерируем один вопрос. Остальные вопросы останутся без изменений.", "warn");
      const response = await client.regenerateQuestion(quizId, questionId, {
        quiz_id: quizId,
        question_id: questionId,
        language: "ru",
      });
      const regeneratedQuestion = response.regenerated_question;
      if (!regeneratedQuestion?.question_id) {
        throw new Error("Backend не вернул обновлённый вопрос.");
      }
      const persistedQuiz = response.quiz ?? editorState.loadedQuiz;
      const updatedQuiz = replaceRegeneratedQuestion({
        ...displayedQuiz,
        quiz_id: persistedQuiz.quiz_id ?? displayedQuiz.quiz_id,
        document_id: persistedQuiz.document_id ?? displayedQuiz.document_id,
        version: persistedQuiz.version ?? displayedQuiz.version,
        last_edited_at: persistedQuiz.last_edited_at ?? displayedQuiz.last_edited_at,
      }, regeneratedQuestion);

      renderQuizEditor(updatedQuiz);
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
          "Вопрос перегенерирован. Несохранённые правки в остальных полях сохранены локально; сохраните квиз, чтобы отправить их в backend.",
          "warn",
        );
      } else {
        setEditorStatus("Вопрос перегенерирован. Остальные вопросы сохранены без изменений.", "ok");
      }
      showToast("Вопрос перегенерирован.", "ok");
      setLogMessage(
        `Вопрос ${questionId} перегенерирован через backend; остальные вопросы и кириллица сохранены без изменений.`,
        "ok",
      );
    } catch (error) {
      setRegenerationActionState(card, {
        busy: false,
        text: `Не удалось перегенерировать вопрос: ${describeError(error)}`,
        tone: "bad",
      });
      setEditorStatus(`Не удалось перегенерировать вопрос: ${describeError(error)}`, "bad");
      showToast("Не удалось перегенерировать вопрос.", "bad");
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
    regenerateQuizQuestion,
    submitQuizEdits,
  };
}
