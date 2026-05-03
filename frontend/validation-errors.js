import { QuizCraftApiError } from "./api/client.js";

export function describeError(error) {
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
  question_count: "Количество вопросов",
  language: "Язык квиза",
  difficulty: "Сложность",
  quiz_type: "Типы вопросов",
  quiz_types: "Типы вопросов",
  generation_mode: "Режим генерации",
  quiz: "Квиз",
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
        text: `текст варианта ${optionNumber}`,
        option_id: `идентификатор варианта ${optionNumber}`,
      };
      const optionLabel = optionLabels[optionSub] ?? `вариант ${optionNumber} (${optionSub})`;
      return `Вопрос ${questionNumber}: ${optionLabel}`;
    }

    const questionLabels = {
      "": "данные вопроса",
      prompt: "текст вопроса",
      correct_option_index: "номер правильного варианта",
      "explanation.text": "текст пояснения",
      explanation: "пояснение",
      question_id: "идентификатор вопроса",
      options: "список вариантов",
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

export function describeValidationError(error) {
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
