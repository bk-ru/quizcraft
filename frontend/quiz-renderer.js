const GENERATION_MODE_LABELS = Object.freeze({
  rag: "RAG (поиск по документу)",
  direct: "Прямая",
  single_question_regen: "Регенерация одного вопроса",
});

export function describeGenerationMode(promptVersion) {
  if (typeof promptVersion !== "string" || !promptVersion.trim()) {
    return "Не указан";
  }
  const trimmed = promptVersion.trim().toLowerCase();
  for (const [prefix, label] of Object.entries(GENERATION_MODE_LABELS)) {
    if (trimmed.startsWith(`${prefix}-`) || trimmed === prefix) {
      return label;
    }
  }
  return "Не указан";
}

export function createQuizRenderer({
  resultPanel,
  resultStateBadge,
  questionList,
  setTextContent,
  setExportAvailability,
  advanceStepper,
}, documentRef = document) {
  function setResultState(text, tone, badgeText) {
    const element = documentRef.getElementById("result-status");
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
      resultStateBadge.dataset.tone = tone || "muted";
    }
  }

  function clearQuizResult() {
    setTextContent("quiz-title", "Ещё нет результата");
    setTextContent("quiz-question-count", "0");
    setTextContent("quiz-generation-mode", "Ещё нет результата");
    setTextContent("quiz-model-name", "Ещё нет результата");
    setTextContent("quiz-prompt-version", "Ещё нет результата");
    if (questionList) {
      questionList.replaceChildren();
    }
  }

  function buildQuestionCard(question, index) {
    const item = documentRef.createElement("li");
    item.className = "question-card";

    const heading = documentRef.createElement("div");
    heading.className = "question-card-header";

    const indexBadge = documentRef.createElement("span");
    indexBadge.className = "question-index";
    indexBadge.textContent = `Вопрос ${index + 1}`;

    const prompt = documentRef.createElement("h4");
    prompt.className = "question-prompt";
    prompt.textContent = question.prompt ?? `Вопрос ${index + 1}`;

    heading.append(indexBadge, prompt);
    item.append(heading);

    const optionList = documentRef.createElement("ol");
    optionList.className = "option-list";

    for (const [optionIndex, option] of (question.options ?? []).entries()) {
      const optionItem = documentRef.createElement("li");
      optionItem.className = "option-item";

      const label = documentRef.createElement("span");
      label.className = "option-label";
      label.textContent = option.text ?? "";
      optionItem.append(label);

      if (optionIndex === question.correct_option_index) {
        optionItem.dataset.correct = "true";
        const correctBadge = documentRef.createElement("span");
        correctBadge.className = "option-badge";
        correctBadge.textContent = "Верный ответ";
        optionItem.append(correctBadge);
      }

      optionList.append(optionItem);
    }

    item.append(optionList);

    if (question.explanation?.text) {
      const explanation = documentRef.createElement("p");
      explanation.className = "question-explanation";
      explanation.textContent = `Пояснение: ${question.explanation.text}`;
      item.append(explanation);
    }

    return item;
  }

  function renderQuizResult(generationPayload) {
    const quiz = generationPayload.quiz ?? {};
    const questions = Array.isArray(quiz.questions) ? quiz.questions : [];

    setTextContent("quiz-title", quiz.title ?? "Без названия");
    setTextContent("quiz-question-count", String(questions.length));
    setTextContent("quiz-generation-mode", describeGenerationMode(generationPayload.prompt_version));
    setTextContent("quiz-model-name", generationPayload.model_name ?? "Не указана");
    setTextContent("quiz-prompt-version", generationPayload.prompt_version ?? "Не указана");

    if (questionList) {
      questionList.replaceChildren(...questions.map((question, index) => buildQuestionCard(question, index)));
    }

    setResultState("Результат готов. Квиз отображён ниже.", "ok", "Результат готов");
    setExportAvailability(generationPayload.quiz_id ?? quiz.quiz_id ?? null);
    advanceStepper("review");
  }

  return { setResultState, clearQuizResult, renderQuizResult };
}
