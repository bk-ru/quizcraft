import { validateEditableQuiz } from "./question-shape.js";

const CHOICE_QUESTION_TYPES = new Set(["single_choice", "true_false"]);
const ANSWER_QUESTION_TYPES = new Set(["fill_blank", "short_answer"]);

function normalizeAnswer(value) {
  return typeof value === "string" ? value.trim().toLocaleLowerCase() : "";
}

function getQuestionId(question, index) {
  return question?.question_id ?? `question-${index + 1}`;
}

function describePreviewError(error) {
  return error instanceof Error && error.message ? error.message : "неизвестная ошибка";
}

export function clonePreviewQuiz(quiz) {
  if (typeof structuredClone === "function") {
    return structuredClone(quiz);
  }
  if (quiz === undefined) {
    return undefined;
  }
  return JSON.parse(JSON.stringify(quiz));
}

function ensureChangedOrder(original, shuffled) {
  const hasMultipleValues = shuffled.some((value) => !Object.is(value, shuffled[0]));
  const orderChanged = shuffled.some((value, index) => !Object.is(value, original[index]));
  if (shuffled.length < 2 || !hasMultipleValues || orderChanged) {
    return shuffled;
  }
  return [...shuffled.slice(1), shuffled[0]];
}

export function shufflePreviewValues(values, { random = Math.random } = {}) {
  const shuffled = Array.isArray(values) ? [...values] : [];
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    [shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]];
  }
  return ensureChangedOrder(values, shuffled);
}

function gradeQuestion(question, answer) {
  if (CHOICE_QUESTION_TYPES.has(question.question_type)) {
    const options = Array.isArray(question.options) ? question.options : [];
    const expectedIndex = question.correct_option_index;
    return {
      correct: Number.parseInt(answer, 10) === expectedIndex,
      expected: options[expectedIndex]?.text ?? "",
    };
  }
  if (ANSWER_QUESTION_TYPES.has(question.question_type)) {
    return {
      correct: normalizeAnswer(answer) === normalizeAnswer(question.correct_answer),
      expected: question.correct_answer ?? "",
    };
  }
  if (question.question_type === "matching") {
    const pairs = Array.isArray(question.matching_pairs) ? question.matching_pairs : [];
    const selectedValues = Array.isArray(answer) ? answer : [];
    return {
      correct: pairs.every((pair, index) => normalizeAnswer(selectedValues[index]) === normalizeAnswer(pair.right)),
      expected: pairs.map((pair) => `${pair.left} — ${pair.right}`).join("; "),
    };
  }
  return {
    correct: false,
    expected: "",
  };
}

export function gradeQuizPreview(quiz, answers = {}) {
  const snapshot = clonePreviewQuiz(quiz);
  const questions = Array.isArray(snapshot?.questions) ? snapshot.questions : [];
  const results = questions.map((question, index) => {
    const questionId = getQuestionId(question, index);
    return {
      question_id: questionId,
      ...gradeQuestion(question, answers[questionId]),
    };
  });
  return {
    correct_count: results.filter((result) => result.correct).length,
    total_count: results.length,
    results,
  };
}

export function createPlayablePreview({
  modalRegion,
  getQuizSnapshot,
  showToast = () => {},
  documentRef = (typeof document !== "undefined" ? document : null),
  windowRef = (typeof window !== "undefined" ? window : null),
  random = Math.random,
} = {}) {
  let activeDialog = null;
  let restoreFocus = null;

  function restoreTriggerFocus() {
    const target = restoreFocus;
    restoreFocus = null;
    if (!target || typeof target.focus !== "function") {
      return;
    }
    try {
      target.focus({ preventScroll: true });
    } catch (_error) {
      target.focus();
    }
  }

  function removeDialog(dialog) {
    if (dialog?.parentNode) {
      dialog.parentNode.removeChild(dialog);
    }
    if (activeDialog === dialog) {
      activeDialog = null;
      restoreTriggerFocus();
    }
  }

  function close() {
    if (!activeDialog) {
      return false;
    }
    const dialog = activeDialog;
    if (dialog.open) {
      dialog.close();
    }
    removeDialog(dialog);
    return true;
  }

  function createChoiceFields(question, questionId) {
    const wrapper = documentRef.createElement("div");
    wrapper.className = "preview-options";
    const options = Array.isArray(question.options) ? question.options : [];
    options.forEach((option, optionIndex) => {
      const label = documentRef.createElement("label");
      label.className = "preview-option";
      const input = documentRef.createElement("input");
      input.type = "radio";
      input.name = `preview-${questionId}`;
      input.value = String(optionIndex);
      input.dataset.previewQuestionId = questionId;
      input.dataset.previewKind = "choice";
      const text = documentRef.createElement("span");
      text.textContent = option.text ?? "";
      label.append(input, text);
      wrapper.append(label);
    });
    return wrapper;
  }

  function createAnswerField(questionId) {
    const input = documentRef.createElement("input");
    input.type = "text";
    input.className = "preview-answer-input";
    input.dataset.previewQuestionId = questionId;
    input.dataset.previewKind = "text";
    input.setAttribute("aria-label", "Введите ответ");
    return input;
  }

  function createMatchingFields(question, questionId) {
    const wrapper = documentRef.createElement("div");
    wrapper.className = "preview-matching";
    const pairs = Array.isArray(question.matching_pairs) ? question.matching_pairs : [];
    const rightValues = shufflePreviewValues(pairs.map((pair) => pair.right), { random });
    pairs.forEach((pair, pairIndex) => {
      const label = documentRef.createElement("label");
      label.className = "preview-matching-row";
      const left = documentRef.createElement("span");
      left.textContent = pair.left ?? "";
      const select = documentRef.createElement("select");
      select.dataset.previewQuestionId = questionId;
      select.dataset.previewKind = "matching";
      select.dataset.previewPairIndex = String(pairIndex);
      select.setAttribute("aria-label", `Соответствие для «${pair.left ?? ""}»`);
      const placeholder = documentRef.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "Выберите соответствие";
      select.append(placeholder);
      rightValues.forEach((rightValue) => {
        const option = documentRef.createElement("option");
        option.value = rightValue;
        option.textContent = rightValue;
        select.append(option);
      });
      label.append(left, select);
      wrapper.append(label);
    });
    return wrapper;
  }

  function createQuestionFields(question, index) {
    const fieldset = documentRef.createElement("fieldset");
    fieldset.className = "preview-question";
    const legend = documentRef.createElement("legend");
    legend.textContent = `Вопрос ${index + 1}. ${question.prompt ?? ""}`;
    fieldset.append(legend);
    const questionId = getQuestionId(question, index);
    if (CHOICE_QUESTION_TYPES.has(question.question_type)) {
      fieldset.append(createChoiceFields(question, questionId));
    } else if (ANSWER_QUESTION_TYPES.has(question.question_type)) {
      fieldset.append(createAnswerField(questionId));
    } else if (question.question_type === "matching") {
      fieldset.append(createMatchingFields(question, questionId));
    }
    return fieldset;
  }

  function collectAnswers(form) {
    const answers = {};
    form.querySelectorAll("[data-preview-question-id]").forEach((control) => {
      const questionId = control.dataset.previewQuestionId;
      const kind = control.dataset.previewKind;
      if (!questionId) {
        return;
      }
      if (kind === "choice" && control instanceof HTMLInputElement && control.checked) {
        answers[questionId] = control.value;
      } else if (kind === "text" && control instanceof HTMLInputElement) {
        answers[questionId] = control.value;
      } else if (kind === "matching" && control instanceof HTMLSelectElement) {
        const pairIndex = Number.parseInt(control.dataset.previewPairIndex ?? "", 10);
        if (!Array.isArray(answers[questionId])) {
          answers[questionId] = [];
        }
        answers[questionId][pairIndex] = control.value;
      }
    });
    return answers;
  }

  function renderResults(target, score) {
    const heading = documentRef.createElement("strong");
    heading.textContent = `Результат: ${score.correct_count} из ${score.total_count}`;
    const list = documentRef.createElement("ol");
    list.className = "preview-result-list";
    score.results.forEach((result, index) => {
      const item = documentRef.createElement("li");
      item.dataset.correct = String(result.correct);
      item.textContent = result.correct
        ? `Вопрос ${index + 1}: верно. Правильный ответ: ${result.expected}`
        : `Вопрос ${index + 1}: неверно. Правильный ответ: ${result.expected}`;
      list.append(item);
    });
    target.replaceChildren(heading, list);
    target.hidden = false;
  }

  function open(event) {
    event?.preventDefault();
    if (!modalRegion || !documentRef || typeof getQuizSnapshot !== "function") {
      showToast("Предпросмотр сейчас недоступен.", "bad");
      return false;
    }
    close();
    let quiz;
    try {
      quiz = clonePreviewQuiz(getQuizSnapshot());
      const validationErrors = validateEditableQuiz(quiz);
      if (validationErrors.length > 0) {
        throw new Error(validationErrors.join("\n"));
      }
    } catch (error) {
      showToast(`Не удалось открыть предпросмотр: ${describePreviewError(error)}`, "bad");
      return false;
    }

    const dialog = documentRef.createElement("dialog");
    dialog.className = "quiz-preview-modal";
    dialog.setAttribute("aria-labelledby", "quiz-preview-title");
    const heading = documentRef.createElement("div");
    heading.className = "quiz-preview-heading";
    const title = documentRef.createElement("h2");
    title.id = "quiz-preview-title";
    title.textContent = quiz.title ?? "Предпросмотр квиза";
    const closeButton = documentRef.createElement("button");
    closeButton.type = "button";
    closeButton.className = "quiz-preview-close";
    closeButton.textContent = "×";
    closeButton.setAttribute("aria-label", "Закрыть предпросмотр");
    heading.append(title, closeButton);

    const form = documentRef.createElement("form");
    form.className = "quiz-preview-form";
    const questions = Array.isArray(quiz.questions) ? quiz.questions : [];
    questions.forEach((question, index) => form.append(createQuestionFields(question, index)));
    const submitButton = documentRef.createElement("button");
    submitButton.type = "submit";
    submitButton.className = "primary-action";
    submitButton.textContent = "Проверить ответы";
    const result = documentRef.createElement("div");
    result.className = "quiz-preview-result";
    result.setAttribute("aria-live", "polite");
    result.hidden = true;
    form.append(submitButton, result);
    dialog.append(heading, form);

    closeButton.addEventListener("click", close);
    form.addEventListener("submit", (submitEvent) => {
      submitEvent.preventDefault();
      renderResults(result, gradeQuizPreview(quiz, collectAnswers(form)));
    });
    dialog.addEventListener("cancel", (cancelEvent) => {
      cancelEvent.preventDefault();
      close();
    });
    dialog.addEventListener("close", () => removeDialog(dialog));
    dialog.addEventListener("click", (clickEvent) => {
      if (clickEvent.target === dialog) {
        close();
      }
    });

    restoreFocus = documentRef.activeElement instanceof HTMLElement ? documentRef.activeElement : null;
    modalRegion.append(dialog);
    activeDialog = dialog;
    try {
      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      } else {
        dialog.setAttribute("open", "");
      }
    } catch (error) {
      removeDialog(dialog);
      showToast(`Не удалось открыть предпросмотр: ${describePreviewError(error)}`, "bad");
      return false;
    }
    const focusTarget = form.querySelector("input, select, button") ?? closeButton;
    if (windowRef && typeof windowRef.requestAnimationFrame === "function") {
      windowRef.requestAnimationFrame(() => focusTarget.focus());
    } else {
      focusTarget.focus();
    }
    return true;
  }

  return { open, close, isActive: () => Boolean(activeDialog?.open) };
}
