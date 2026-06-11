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

  function createExplanation(text, className = "", { force = false, labelText = "Пояснение" } = {}) {
    if (!force && !String(text ?? "").trim()) {
      return null;
    }
    const explanation = documentRef.createElement("div");
    explanation.className = `q-expl ${className}`.trim();
    const label = documentRef.createElement("span");
    label.className = "q-expl-label";
    label.textContent = labelText;
    explanation.append(label, text ?? "");
    return explanation;
  }

  function hideQuestionValidationMessage(wrapper, questionId, validationMessages) {
    validationMessages.delete(questionId);
    const message = wrapper.closest(".play-question")?.querySelector(".quiz-preview-inline-error");
    if (message) {
      message.hidden = true;
    }
  }

  function createChoiceFields(question, questionId, answers, evaluatedQuestionIds, validationMessages) {
    const wrapper = documentRef.createElement("div");
    wrapper.className = "preview-options play-options";
    const options = Array.isArray(question.options) ? question.options : [];
    const updateChoiceState = () => {
      const evaluated = evaluatedQuestionIds.has(questionId);
      wrapper.querySelectorAll(".play-opt").forEach((optionButton, optionIndex) => {
        optionButton.classList.toggle("is-correct", evaluated && optionIndex === question.correct_option_index);
        optionButton.classList.toggle("is-wrong", evaluated && optionIndex !== question.correct_option_index);
      });
      if (explanation) {
        explanation.hidden = !evaluated;
      }
    };
    options.forEach((option, optionIndex) => {
      const label = documentRef.createElement("label");
      label.className = "preview-option play-opt";
      const input = documentRef.createElement("input");
      input.type = "radio";
      input.name = `preview-${questionId}`;
      input.value = String(optionIndex);
      input.dataset.previewQuestionId = questionId;
      input.dataset.previewKind = "choice";
      input.checked = answers[questionId] === input.value;
      input.addEventListener("change", () => {
        answers[questionId] = input.value;
        evaluatedQuestionIds.delete(questionId);
        hideQuestionValidationMessage(wrapper, questionId, validationMessages);
        updateChoiceState();
      });
      const mark = documentRef.createElement("span");
      mark.className = "play-opt-mark";
      mark.textContent = String.fromCharCode(65 + optionIndex);
      const text = documentRef.createElement("span");
      text.textContent = option.text ?? "";
      label.append(input, mark, text);
      wrapper.append(label);
    });
    const explanation = createExplanation(question.explanation?.text);
    if (explanation) {
      explanation.hidden = true;
    }
    updateChoiceState();
    return [wrapper, explanation].filter(Boolean);
  }

  function createAnswerField(question, questionId, answers, evaluatedQuestionIds, validationMessages) {
    const wrapper = documentRef.createElement("div");
    wrapper.className = "play-answer-wrap";
    const input = documentRef.createElement("input");
    input.type = "text";
    input.className = "preview-answer-input play-answer";
    input.dataset.previewQuestionId = questionId;
    input.dataset.previewKind = "text";
    input.setAttribute("aria-label", "Введите ответ");
    input.placeholder = "Введите ответ";
    input.value = answers[questionId] ?? "";
    const feedback = createExplanation("", "play-answer-feedback", { force: true, labelText: "" });
    feedback.hidden = true;
    const explanation = createExplanation(question.explanation?.text);
    if (explanation) {
      explanation.hidden = true;
    }
    const updateAnswerState = () => {
      const answer = input.value.trim();
      const evaluated = evaluatedQuestionIds.has(questionId);
      input.classList.toggle("is-correct", false);
      input.classList.toggle("is-wrong", false);
      feedback.hidden = !evaluated;
      if (explanation) {
        explanation.hidden = !evaluated;
      }
      if (!evaluated) {
        return;
      }
      const correct = normalizeAnswer(answer) === normalizeAnswer(question.correct_answer);
      input.classList.toggle("is-correct", correct);
      input.classList.toggle("is-wrong", !correct);
      feedback.classList.toggle("play-match-ok", correct);
      feedback.classList.toggle("play-match-bad", !correct);
      feedback.replaceChildren();
      const label = documentRef.createElement("span");
      label.className = "q-expl-label";
      label.textContent = correct ? "Верно" : "Проверьте";
      feedback.append(label, correct ? "Ответ совпадает с ожидаемым." : `Ожидаемый ответ: ${question.correct_answer ?? ""}`);
    };
    input.addEventListener("input", () => {
      answers[questionId] = input.value;
      evaluatedQuestionIds.delete(questionId);
      hideQuestionValidationMessage(wrapper, questionId, validationMessages);
      updateAnswerState();
    });
    updateAnswerState();
    wrapper.append(input, feedback);
    if (explanation) {
      wrapper.append(explanation);
    }
    return [wrapper];
  }

  function createMatchingFields(question, questionId, answers, evaluatedQuestionIds, validationMessages) {
    const wrapper = documentRef.createElement("div");
    wrapper.className = "preview-matching play-match";
    const pairs = Array.isArray(question.matching_pairs) ? question.matching_pairs : [];
    const rightValues = shufflePreviewValues(pairs.map((pair) => pair.right), { random });
    const selectedValues = Array.isArray(answers[questionId]) ? answers[questionId] : [];
    answers[questionId] = selectedValues;
    const letters = new Map(rightValues.map((value, index) => [value, String.fromCharCode(65 + index)]));
    const feedback = createExplanation("", "play-match-feedback", { force: true, labelText: "" });
    feedback.hidden = true;
    const explanation = createExplanation(question.explanation?.text);
    if (explanation) {
      explanation.hidden = true;
    }
    const updateMatchingState = () => {
      const answered = pairs.every((_pair, index) => selectedValues[index]);
      const evaluated = evaluatedQuestionIds.has(questionId);
      feedback.hidden = !evaluated;
      if (explanation) {
        explanation.hidden = !evaluated;
      }
      if (!evaluated) {
        return;
      }
      const correct = pairs.every((pair, index) => normalizeAnswer(selectedValues[index]) === normalizeAnswer(pair.right));
      feedback.classList.toggle("play-match-ok", correct);
      feedback.classList.toggle("play-match-bad", !correct);
      feedback.replaceChildren();
      const label = documentRef.createElement("span");
      label.className = "q-expl-label";
      label.textContent = correct ? "Верно" : "Проверьте";
      feedback.append(label, correct ? "Все пары сопоставлены правильно." : "Некоторые соответствия выбраны неверно.");
    };
    pairs.forEach((pair, pairIndex) => {
      const label = documentRef.createElement("label");
      label.className = "preview-matching-row play-match-row";
      const badge = documentRef.createElement("span");
      badge.className = "q-match-badge";
      badge.textContent = String(pairIndex + 1);
      const left = documentRef.createElement("span");
      left.className = "play-match-left";
      left.textContent = pair.left ?? "";
      const select = documentRef.createElement("select");
      select.className = "play-match-pick";
      select.dataset.previewQuestionId = questionId;
      select.dataset.previewKind = "matching";
      select.dataset.previewPairIndex = String(pairIndex);
      select.setAttribute("aria-label", `Соответствие для «${pair.left ?? ""}»`);
      const placeholder = documentRef.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "—";
      select.append(placeholder);
      rightValues.forEach((rightValue) => {
        const option = documentRef.createElement("option");
        option.value = rightValue;
        option.textContent = letters.get(rightValue);
        select.append(option);
      });
      select.value = selectedValues[pairIndex] ?? "";
      select.addEventListener("change", () => {
        selectedValues[pairIndex] = select.value;
        evaluatedQuestionIds.delete(questionId);
        hideQuestionValidationMessage(wrapper, questionId, validationMessages);
        updateMatchingState();
      });
      label.append(badge, left, select);
      wrapper.append(label);
    });
    const bank = documentRef.createElement("div");
    bank.className = "play-match-bank";
    rightValues.forEach((rightValue) => {
      const item = documentRef.createElement("div");
      item.className = "play-match-bank-item";
      const badge = documentRef.createElement("span");
      badge.className = "q-match-badge q-match-badge-alt";
      badge.textContent = letters.get(rightValue);
      const text = documentRef.createElement("span");
      text.textContent = rightValue;
      item.append(badge, text);
      bank.append(item);
    });
    updateMatchingState();
    return [wrapper, bank, feedback, explanation].filter(Boolean);
  }

  function createQuestionFields(question, index, answers, evaluatedQuestionIds, validationMessages) {
    const fieldset = documentRef.createElement("section");
    fieldset.className = "preview-question play-question";
    const heading = documentRef.createElement("h3");
    heading.className = "play-q-text";
    heading.textContent = `${index + 1}. ${question.prompt ?? ""}`;
    fieldset.append(heading);
    const questionId = getQuestionId(question, index);
    const validationMessage = validationMessages.get(questionId);
    if (validationMessage) {
      const inlineError = documentRef.createElement("div");
      inlineError.className = "quiz-preview-inline-error";
      inlineError.setAttribute("role", "alert");
      inlineError.textContent = validationMessage;
      fieldset.append(inlineError);
    }
    if (evaluatedQuestionIds.has(questionId)) {
      const result = gradeQuestion(question, answers[questionId]);
      fieldset.classList.add(result.correct ? "is-correct" : "is-wrong");
    }
    if (CHOICE_QUESTION_TYPES.has(question.question_type)) {
      fieldset.append(...createChoiceFields(question, questionId, answers, evaluatedQuestionIds, validationMessages));
    } else if (ANSWER_QUESTION_TYPES.has(question.question_type)) {
      fieldset.append(...createAnswerField(question, questionId, answers, evaluatedQuestionIds, validationMessages));
    } else if (question.question_type === "matching") {
      fieldset.append(...createMatchingFields(question, questionId, answers, evaluatedQuestionIds, validationMessages));
    }
    return fieldset;
  }

  function isQuestionAnswered(question, questionId, answers) {
    if (CHOICE_QUESTION_TYPES.has(question.question_type)) {
      return Number.isInteger(Number.parseInt(answers[questionId], 10));
    }
    if (ANSWER_QUESTION_TYPES.has(question.question_type)) {
      return Boolean(String(answers[questionId] ?? "").trim());
    }
    if (question.question_type === "matching") {
      const pairs = Array.isArray(question.matching_pairs) ? question.matching_pairs : [];
      const selectedValues = Array.isArray(answers[questionId]) ? answers[questionId] : [];
      return pairs.length > 0 && pairs.every((_pair, index) => Boolean(selectedValues[index]));
    }
    return true;
  }

  function getAnswerRequiredMessage(question) {
    if (CHOICE_QUESTION_TYPES.has(question.question_type)) {
      return "Выберите вариант ответа.";
    }
    if (ANSWER_QUESTION_TYPES.has(question.question_type)) {
      return "Введите ответ.";
    }
    if (question.question_type === "matching") {
      return "Заполните все соответствия.";
    }
    return "Ответьте на вопрос.";
  }

  function countEvaluatedCorrectAnswers(questions, answers, evaluatedQuestionIds) {
    return questions.filter((question, index) => {
      const questionId = getQuestionId(question, index);
      return evaluatedQuestionIds.has(questionId) && gradeQuestion(question, answers[questionId]).correct;
    }).length;
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
    title.textContent = "Превью квиза";
    const closeButton = documentRef.createElement("button");
    closeButton.type = "button";
    closeButton.className = "quiz-preview-close";
    const closeIcon = documentRef.createElementNS("http://www.w3.org/2000/svg", "svg");
    closeIcon.setAttribute("viewBox", "0 0 24 24");
    closeIcon.setAttribute("width", "18");
    closeIcon.setAttribute("height", "18");
    closeIcon.setAttribute("fill", "none");
    closeIcon.setAttribute("stroke", "currentColor");
    closeIcon.setAttribute("stroke-width", "1.8");
    const closePath = documentRef.createElementNS("http://www.w3.org/2000/svg", "path");
    closePath.setAttribute("d", "M18 6L6 18M6 6l12 12");
    closeIcon.append(closePath);
    closeButton.append(closeIcon);
    closeButton.setAttribute("aria-label", "Закрыть предпросмотр");
    closeButton.title = "Закрыть предпросмотр";
    heading.append(title, closeButton);

    const form = documentRef.createElement("form");
    form.className = "quiz-preview-form";
    const questions = Array.isArray(quiz.questions) ? quiz.questions : [];
    const answers = {};
    const evaluatedQuestionIds = new Set();
    const validationMessages = new Map();
    let activeQuestionIndex = 0;
    const questionBody = documentRef.createElement("div");
    questionBody.className = "quiz-preview-body";
    const footer = documentRef.createElement("div");
    footer.className = "quiz-preview-footer";
    const progress = documentRef.createElement("span");
    progress.className = "quiz-preview-progress";
    const scoreCounter = documentRef.createElement("span");
    scoreCounter.className = "quiz-preview-score";
    const footerSpacer = documentRef.createElement("span");
    footerSpacer.className = "quiz-preview-footer-spacer";
    const previousButton = documentRef.createElement("button");
    previousButton.type = "button";
    previousButton.className = "secondary-action";
    previousButton.textContent = "\u2190 \u041d\u0430\u0437\u0430\u0434";
    const nextButton = documentRef.createElement("button");
    nextButton.type = "button";
    nextButton.className = "primary-action primary-action-sm";
    footer.append(progress, scoreCounter, footerSpacer, previousButton, nextButton);
    form.append(questionBody, footer);
    dialog.append(heading, form);

    function updatePreviewPage() {
      questionBody.replaceChildren(createQuestionFields(
        questions[activeQuestionIndex],
        activeQuestionIndex,
        answers,
        evaluatedQuestionIds,
        validationMessages,
      ));
      progress.textContent = `\u0412\u043e\u043f\u0440\u043e\u0441 ${activeQuestionIndex + 1} / ${questions.length}`;
      scoreCounter.textContent = `${countEvaluatedCorrectAnswers(questions, answers, evaluatedQuestionIds)} / ${questions.length}`;
      previousButton.disabled = activeQuestionIndex === 0;
      nextButton.textContent = activeQuestionIndex === questions.length - 1
        ? "\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c"
        : "\u0414\u0430\u043b\u044c\u0448\u0435 \u2192";
    }

    closeButton.addEventListener("click", close);
    previousButton.addEventListener("click", () => {
      activeQuestionIndex = Math.max(0, activeQuestionIndex - 1);
      updatePreviewPage();
    });
    nextButton.addEventListener("click", () => {
      const currentQuestion = questions[activeQuestionIndex];
      const currentQuestionId = getQuestionId(currentQuestion, activeQuestionIndex);
      if (!evaluatedQuestionIds.has(currentQuestionId)) {
        if (!isQuestionAnswered(currentQuestion, currentQuestionId, answers)) {
          validationMessages.set(currentQuestionId, getAnswerRequiredMessage(currentQuestion));
          updatePreviewPage();
          return;
        }
        validationMessages.delete(currentQuestionId);
        evaluatedQuestionIds.add(currentQuestionId);
        updatePreviewPage();
        return;
      }
      if (activeQuestionIndex < questions.length - 1) {
        activeQuestionIndex += 1;
        updatePreviewPage();
        return;
      }
      if (typeof form.requestSubmit === "function") {
        form.requestSubmit();
        return;
      }
      close();
    });
    form.addEventListener("submit", (submitEvent) => {
      submitEvent.preventDefault();
      close();
    });
    updatePreviewPage();
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
