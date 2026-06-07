const CHOICE_QUESTION_TYPES = Object.freeze(["single_choice", "true_false"]);
const ANSWER_QUESTION_TYPES = Object.freeze(["fill_blank", "short_answer"]);
const SUPPORTED_QUESTION_TYPES = Object.freeze([...CHOICE_QUESTION_TYPES, ...ANSWER_QUESTION_TYPES, "matching"]);
const TRUE_FALSE_LABELS = Object.freeze(["Верно", "Неверно"]);
const MATCHING_SYMBOLIC_RIGHT_VALUES = Object.freeze(["a", "b", "c", "d", "1", "2", "3", "4"]);

function createId(idFactory, prefix) {
  if (typeof idFactory === "function") {
    return String(idFactory(prefix));
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createOption(idFactory, text = "") {
  return {
    option_id: createId(idFactory, "option"),
    text,
  };
}

export function createEmptyQuestion(questionType, { idFactory } = {}) {
  if (!SUPPORTED_QUESTION_TYPES.includes(questionType)) {
    throw new Error(`Неподдерживаемый тип вопроса: ${questionType}`);
  }
  const normalizedType = questionType;
  const question = {
    question_id: createId(idFactory, "question"),
    question_type: normalizedType,
    prompt: "",
    options: [],
    correct_option_index: null,
    correct_answer: null,
    matching_pairs: [],
    explanation: null,
  };

  if (normalizedType === "single_choice") {
    question.options = Array.from({ length: 4 }, () => createOption(idFactory));
    question.correct_option_index = 0;
  } else if (normalizedType === "true_false") {
    question.options = TRUE_FALSE_LABELS.map((text) => createOption(idFactory, text));
    question.correct_option_index = 0;
  } else if (ANSWER_QUESTION_TYPES.includes(normalizedType)) {
    question.correct_answer = "";
  } else if (normalizedType === "matching") {
    question.matching_pairs = Array.from({ length: 4 }, () => ({ left: "", right: "" }));
  }

  return question;
}

export function changeQuestionType(question, nextType, { idFactory } = {}) {
  return {
    ...createEmptyQuestion(nextType, { idFactory }),
    question_id: question?.question_id ?? createId(idFactory, "question"),
    prompt: typeof question?.prompt === "string" ? question.prompt : "",
    explanation: question?.explanation?.text ? { text: question.explanation.text } : null,
  };
}

export function duplicateQuestion(question, { idFactory } = {}) {
  const copy = {
    ...question,
    question_id: createId(idFactory, "question"),
    options: Array.isArray(question?.options)
      ? question.options.map((option) => ({
        ...option,
        option_id: createId(idFactory, "option"),
      }))
      : [],
    matching_pairs: Array.isArray(question?.matching_pairs)
      ? question.matching_pairs.map((pair) => ({
        left: pair?.left ?? "",
        right: pair?.right ?? "",
      }))
      : [],
    explanation: question?.explanation?.text ? { text: question.explanation.text } : null,
  };
  return copy;
}

export function addMatchingPair(question) {
  if (question?.question_type !== "matching") {
    throw new Error("Добавлять пары можно только в вопрос сопоставления.");
  }
  const pairs = Array.isArray(question.matching_pairs) ? question.matching_pairs : [];
  return {
    ...question,
    matching_pairs: [...pairs, { left: "", right: "" }],
  };
}

export function removeMatchingPair(question, pairIndex) {
  if (question?.question_type !== "matching") {
    throw new Error("Удалять пары можно только из вопроса сопоставления.");
  }
  const pairs = Array.isArray(question.matching_pairs) ? question.matching_pairs : [];
  if (!Number.isInteger(pairIndex) || pairIndex < 0 || pairIndex >= pairs.length || pairs.length <= 4) {
    return question;
  }
  return {
    ...question,
    matching_pairs: pairs.filter((_, index) => index !== pairIndex),
  };
}

function addError(errors, questionIndex, message) {
  errors.push(`Вопрос ${questionIndex + 1}: ${message}`);
}

export function validateEditableQuiz(quiz) {
  const errors = [];
  if (!quiz?.title?.trim()) {
    errors.push("Заполните заголовок квиза.");
  }
  const questions = Array.isArray(quiz?.questions) ? quiz.questions : [];
  if (questions.length === 0) {
    return [...errors, "Добавьте хотя бы один вопрос."];
  }

  questions.forEach((question, questionIndex) => {
    const questionType = typeof question?.question_type === "string" ? question.question_type.trim() : "";
    if (!SUPPORTED_QUESTION_TYPES.includes(questionType)) {
      addError(errors, questionIndex, "выбран неподдерживаемый тип.");
      return;
    }
    if (!question?.prompt?.trim()) {
      addError(errors, questionIndex, "заполните текст вопроса.");
    }

    const options = Array.isArray(question?.options) ? question.options : [];
    const matchingPairs = Array.isArray(question?.matching_pairs) ? question.matching_pairs : [];
    if (questionType === "single_choice") {
      if (options.length !== 4) {
        addError(errors, questionIndex, "для одиночного выбора нужны ровно 4 варианта.");
      }
      if (options.some((option) => !option?.text?.trim())) {
        addError(errors, questionIndex, "заполните все варианты ответа.");
      }
      if (!Number.isInteger(question.correct_option_index) || question.correct_option_index < 0 || question.correct_option_index >= options.length) {
        addError(errors, questionIndex, "выберите правильный вариант.");
      }
      if (question.correct_answer !== null || matchingPairs.length > 0) {
        addError(errors, questionIndex, "удалите поля, несовместимые с одиночным выбором.");
      }
    } else if (questionType === "true_false") {
      if (options.length !== 2 || options.some((option, index) => option?.text !== TRUE_FALSE_LABELS[index])) {
        addError(errors, questionIndex, "используйте варианты «Верно» и «Неверно».");
      }
      if (!Number.isInteger(question.correct_option_index) || question.correct_option_index < 0 || question.correct_option_index > 1) {
        addError(errors, questionIndex, "выберите правильный вариант.");
      }
      if (question.correct_answer !== null || matchingPairs.length > 0) {
        addError(errors, questionIndex, "удалите поля, несовместимые с форматом «Верно / Неверно».");
      }
    } else if (ANSWER_QUESTION_TYPES.includes(questionType)) {
      if (!question?.correct_answer?.trim()) {
        addError(errors, questionIndex, "заполните правильный ответ.");
      }
      if (options.length > 0 || question.correct_option_index !== null || matchingPairs.length > 0) {
        addError(errors, questionIndex, "удалите поля, несовместимые с текстовым ответом.");
      }
      if (questionType === "fill_blank" && !/_{2,}|…|\.\.\./u.test(question.prompt)) {
        addError(errors, questionIndex, "добавьте пропуск в текст вопроса.");
      }
    } else if (questionType === "matching") {
      if (matchingPairs.length < 4) {
        addError(errors, questionIndex, "для сопоставления нужны минимум 4 пары.");
      }
      if (matchingPairs.some((pair) => !pair?.left?.trim() || !pair?.right?.trim())) {
        addError(errors, questionIndex, "заполните обе части каждой пары.");
      }
      if (matchingPairs.some((pair) => MATCHING_SYMBOLIC_RIGHT_VALUES.includes(pair?.right?.trim().toLowerCase()))) {
        addError(errors, questionIndex, "укажите полный текст справа вместо символа.");
      }
      if (options.length > 0 || question.correct_option_index !== null || question.correct_answer !== null) {
        addError(errors, questionIndex, "удалите поля, несовместимые с сопоставлением.");
      }
    }
  });

  return errors;
}

export function moveQuestionById(questions, questionId, direction) {
  const copy = Array.isArray(questions) ? [...questions] : [];
  const currentIndex = copy.findIndex((question) => question?.question_id === questionId);
  const offset = direction === "up" ? -1 : direction === "down" ? 1 : 0;
  const nextIndex = currentIndex + offset;
  if (currentIndex < 0 || offset === 0 || nextIndex < 0 || nextIndex >= copy.length) {
    return copy;
  }
  [copy[currentIndex], copy[nextIndex]] = [copy[nextIndex], copy[currentIndex]];
  return copy;
}
