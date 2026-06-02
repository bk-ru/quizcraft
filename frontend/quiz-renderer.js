const GENERATION_MODE_LABELS = Object.freeze({
  auto: "Авто",
  rag: "RAG (поиск по документу)",
  direct: "Прямая",
  single_question_regen: "Регенерация одного вопроса",
});
const QUESTION_TYPE_LABELS = Object.freeze({
  single_choice: "Множественный выбор",
  true_false: "Истина / Ложь",
  fill_blank: "Заполните пробел",
  short_answer: "Краткий ответ",
  matching: "Соответствие",
});

function normalizeGenerationWarnings(warnings) {
  if (!Array.isArray(warnings)) {
    return [];
  }
  return warnings.filter((warning) => typeof warning?.message === "string" && warning.message.trim());
}

function normalizeQualityStatus(value) {
  return typeof value === "string" && value.trim() ? value.trim().toLowerCase() : "ok";
}

function formatWarningSummary(warnings) {
  const firstWarning = warnings[0];
  if (!firstWarning) {
    return "Проверьте показанный квиз перед использованием.";
  }
  const recommendations = Array.isArray(firstWarning?.recommendations)
    ? firstWarning.recommendations.filter((item) => typeof item === "string" && item.trim())
    : [];
  return [firstWarning.message, ...recommendations].join(" ");
}

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
  activateWorkflowStage,
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
    setTextContent("quiz-id-pill", "id: ещё нет");
    setTextContent("quiz-version-pill", "версия —");
    setTextContent("quiz-count-pill", "0 вопросов");
    setTextContent("quiz-edited-pill", "обновлений нет");
    setTextContent("quiz-question-count", "0");
    setTextContent("quiz-generation-mode", "Ещё нет результата");
    setTextContent("quiz-model-name", "Ещё нет результата");
    setTextContent("quiz-prompt-version", "Ещё нет результата");
    const titleInput = documentRef.getElementById("quiz-title");
    if (titleInput instanceof HTMLInputElement) {
      titleInput.disabled = true;
    }
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
    indexBadge.textContent = `Вопрос ${index + 1} · ${QUESTION_TYPE_LABELS[question.question_type] ?? "Тип не указан"}`;

    const prompt = documentRef.createElement("h4");
    prompt.className = "question-prompt";
    prompt.textContent = question.prompt ?? `Вопрос ${index + 1}`;

    heading.append(indexBadge, prompt);
    item.append(heading);

    if (question.question_type === "fill_blank" || question.question_type === "short_answer") {
      const answer = documentRef.createElement("p");
      answer.className = "question-explanation";
      answer.textContent = `Ответ: ${question.correct_answer ?? "Не указан"}`;
      item.append(answer);
    } else if (question.question_type === "matching") {
      const pairList = documentRef.createElement("ol");
      pairList.className = "option-list";
      for (const pair of question.matching_pairs ?? []) {
        const pairItem = documentRef.createElement("li");
        pairItem.className = "option-item";
        pairItem.textContent = `${pair.left ?? ""} — ${pair.right ?? ""}`;
        pairList.append(pairItem);
      }
      item.append(pairList);
    } else {
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
    }

    if (question.explanation?.text) {
      const explanation = documentRef.createElement("p");
      explanation.className = "question-explanation";
      explanation.textContent = `Пояснение: ${question.explanation.text}`;
      item.append(explanation);
    }

    return item;
  }

  function renderQuizResult(generationPayload) {
    const qualityStatus = normalizeQualityStatus(generationPayload.quality_status);
    if (qualityStatus === "failed") {
      clearQuizResult();
      setResultState(
        "Результат не показан: квиз не прошёл безопасное восстановление.",
        "bad",
        "Результат недоступен",
      );
      setExportAvailability(null);
      activateWorkflowStage("result");
      return;
    }
    const quiz = generationPayload.quiz ?? {};
    const questions = Array.isArray(quiz.questions) ? quiz.questions : [];
    const warnings = normalizeGenerationWarnings(generationPayload.warnings);

    const title = quiz.title ?? "Без названия";
    const quizId = generationPayload.quiz_id ?? quiz.quiz_id ?? "";
    const version = Number.isInteger(quiz.version) ? quiz.version : null;
    setTextContent("quiz-title", title);
    setTextContent("quiz-id-pill", quizId ? "id: " + String(quizId).slice(0, 8) : "id: ещё нет");
    setTextContent("quiz-version-pill", version === null ? "версия —" : "версия " + String(version));
    setTextContent("quiz-count-pill", String(questions.length) + " вопросов");
    setTextContent("quiz-edited-pill", quiz.last_edited_at ? "обновлено" : "обновлено только что");
    setTextContent("quiz-question-count", String(questions.length));
    setTextContent("quiz-generation-mode", describeGenerationMode(generationPayload.prompt_version));
    setTextContent("quiz-model-name", generationPayload.model_name ?? "Не указана");
    setTextContent("quiz-prompt-version", generationPayload.prompt_version ?? "Не указана");
    const titleInput = documentRef.getElementById("quiz-title");
    if (titleInput instanceof HTMLInputElement) {
      titleInput.disabled = false;
    }

    if (questionList) {
      questionList.replaceChildren(...questions.map((question, index) => buildQuestionCard(question, index)));
    }

    if (warnings.length > 0 || qualityStatus === "recovered" || qualityStatus === "warning" || qualityStatus === "partial") {
      const warningMessage = warnings.length > 0
        ? formatWarningSummary(warnings)
        : "Квиз показан с предупреждениями. Проверьте результат перед использованием.";
      setResultState(
        warningMessage,
        "warn",
        "Результат частичный",
      );
    } else {
      setResultState("Результат готов. Квиз отображён ниже.", "ok", "Результат готов");
    }
    setExportAvailability(generationPayload.quiz_id ?? quiz.quiz_id ?? null);
    activateWorkflowStage("result");
  }

  return { setResultState, clearQuizResult, renderQuizResult };
}
