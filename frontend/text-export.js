const MAX_CSV_OPTIONS = 10;
const CHOICE_QUESTION_TYPES = new Set(["single_choice", "true_false"]);
const ANSWER_QUESTION_TYPES = new Set(["fill_blank", "short_answer"]);

function cloneExportQuiz(quiz) {
  if (typeof structuredClone === "function") {
    return structuredClone(quiz);
  }
  return JSON.parse(JSON.stringify(quiz));
}

function shuffleValues(values, random) {
  const shuffled = [...values];
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    [shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]];
  }
  return shuffled;
}

function shuffleSingleChoiceOptions(question, random) {
  if (question.question_type !== "single_choice" || !Array.isArray(question.options)) {
    return question;
  }
  const indexedOptions = question.options.map((option, index) => ({ option, index }));
  const shuffledOptions = shuffleValues(indexedOptions, random);
  const nextCorrectIndex = shuffledOptions.findIndex(({ index }) => index === question.correct_option_index);
  return {
    ...question,
    options: shuffledOptions.map(({ option }) => option),
    correct_option_index: nextCorrectIndex,
  };
}

function removeAnswers(question) {
  const nextQuestion = { ...question };
  if (CHOICE_QUESTION_TYPES.has(question.question_type)) {
    delete nextQuestion.correct_option_index;
    return nextQuestion;
  }
  if (ANSWER_QUESTION_TYPES.has(question.question_type)) {
    delete nextQuestion.correct_answer;
    return nextQuestion;
  }
  if (question.question_type === "matching") {
    return {
      ...nextQuestion,
      matching_pairs: (Array.isArray(question.matching_pairs) ? question.matching_pairs : [])
        .map((pair) => ({ left: pair.left })),
    };
  }
  return nextQuestion;
}

export function prepareTextExportQuiz(quiz, {
  includeAnswers = true,
  includeExplanations = true,
  shuffleOptions = false,
  random = Math.random,
} = {}) {
  const snapshot = cloneExportQuiz(quiz);
  snapshot.questions = (Array.isArray(snapshot.questions) ? snapshot.questions : []).map((question) => {
    let preparedQuestion = { ...question };
    if (!includeExplanations) {
      delete preparedQuestion.explanation;
    }
    if (shuffleOptions) {
      preparedQuestion = shuffleSingleChoiceOptions(preparedQuestion, random);
    }
    if (!includeAnswers) {
      preparedQuestion = removeAnswers(preparedQuestion);
    }
    return preparedQuestion;
  });
  return snapshot;
}

export function serializeQuizAsJson(quiz, options = {}) {
  return JSON.stringify(prepareTextExportQuiz(quiz, options), null, 2);
}

function escapeMarkdown(value) {
  return String(value ?? "").replace(/[\\`*_[\]<>#|]/gu, "\\$&");
}

function getChoiceAnswer(question) {
  if (!Number.isInteger(question.correct_option_index)) {
    return "";
  }
  return question.options?.[question.correct_option_index]?.text ?? "";
}

function renderMarkdownQuestion(question, index, { includeAnswers }) {
  const lines = [`## Вопрос ${index + 1}`, "", escapeMarkdown(question.prompt), ""];
  if (CHOICE_QUESTION_TYPES.has(question.question_type)) {
    question.options.forEach((option, optionIndex) => {
      lines.push(`${optionIndex + 1}. ${escapeMarkdown(option.text)}`);
    });
  } else if (question.question_type === "matching") {
    question.matching_pairs.forEach((pair) => {
      lines.push(pair.right === undefined
        ? `- ${escapeMarkdown(pair.left)}`
        : `- ${escapeMarkdown(pair.left)} — ${escapeMarkdown(pair.right)}`);
    });
  }
  if (includeAnswers && CHOICE_QUESTION_TYPES.has(question.question_type)) {
    lines.push("", `**Правильный ответ:** ${escapeMarkdown(getChoiceAnswer(question))}`);
  } else if (includeAnswers && ANSWER_QUESTION_TYPES.has(question.question_type)) {
    lines.push("", `**Правильный ответ:** ${escapeMarkdown(question.correct_answer)}`);
  }
  if (question.explanation?.text) {
    lines.push("", `**Пояснение:** ${escapeMarkdown(question.explanation.text)}`);
  }
  lines.push("");
  return lines;
}

export function serializeQuizAsMarkdown(quiz, options = {}) {
  const includeAnswers = options.includeAnswers !== false;
  const snapshot = prepareTextExportQuiz(quiz, options);
  const lines = [`# ${escapeMarkdown(snapshot.title)}`, ""];
  snapshot.questions.forEach((question, index) => {
    lines.push(...renderMarkdownQuestion(question, index, { includeAnswers }));
  });
  return lines.join("\n").trimEnd() + "\n";
}

function escapeCsv(value) {
  const text = String(value ?? "");
  return /[",\r\n]/u.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function getCsvAnswer(question) {
  if (CHOICE_QUESTION_TYPES.has(question.question_type)) {
    return getChoiceAnswer(question);
  }
  return ANSWER_QUESTION_TYPES.has(question.question_type) ? question.correct_answer ?? "" : "";
}

function renderCsvRow(question) {
  const isChoice = CHOICE_QUESTION_TYPES.has(question.question_type);
  const options = isChoice ? question.options.map((option) => option.text).slice(0, MAX_CSV_OPTIONS) : [];
  while (options.length < MAX_CSV_OPTIONS) {
    options.push("");
  }
  return [
    question.prompt,
    isChoice ? "Multiple choice" : "Short answer",
    ...options,
    getCsvAnswer(question),
    "1",
    question.explanation?.text ?? "",
  ].map(escapeCsv).join(",");
}

export function serializeQuizAsCsv(quiz, {
  includeAnswers = true,
  shuffleOptions = false,
  random = Math.random,
} = {}) {
  const snapshot = prepareTextExportQuiz(quiz, {
    includeAnswers,
    includeExplanations: true,
    shuffleOptions,
    random,
  });
  const matchingQuestions = snapshot.questions.filter((question) => question.question_type === "matching");
  const rows = snapshot.questions
    .filter((question) => question.question_type !== "matching")
    .map(renderCsvRow);
  const header = [
    "Question",
    "Question Type",
    ...Array.from({ length: MAX_CSV_OPTIONS }, (_, index) => `Option ${index + 1}`),
    "Correct Answer",
    "Points",
    "Feedback",
  ].join(",");
  return {
    content: [header, ...rows].join("\r\n") + "\r\n",
    warning_count: matchingQuestions.length,
    skipped_matching_count: matchingQuestions.length,
  };
}
