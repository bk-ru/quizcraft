/* ════════════════════════════════════════════════════════════════
   Мок-«бэкенд» QuizCraft. Имитирует конвейер генерации с этапами,
   живым журналом и стримом вопросов — без сети, чтобы мокап
   можно было открыть локально и потыкать.
   Типы вопросов соответствуют формату QuizCraft:
   single_choice, true_false, fill_blank, short_answer, matching.
   ════════════════════════════════════════════════════════════════ */

const TOPICS = [
  "архитектуру модулей",
  "паттерны проектирования",
  "временную сложность алгоритмов",
  "семантику HTTP",
  "конкурентность и блокировки",
  "управление состоянием в UI",
  "доступность форм",
  "стратегии кэширования",
  "регулярные выражения",
  "потоковую обработку данных",
];

const STEMS = [
  "В чём ключевое отличие {a} от {b}?",
  "Что произойдёт, если применить {a} к {b}?",
  "Какой вариант лучше всего описывает {a}?",
  "Какое утверждение о {a} является верным?",
  "Какая характеристика отличает {a} от {b}?",
  "В каком случае предпочтительно использовать {a}?",
  "Какой из подходов оптимален для {a}?",
];

const WORDS = ["алгоритма", "протокола", "паттерна", "стратегии", "API", "хука", "событийной модели", "контракта", "хранилища", "пайплайна"];
const QUESTION_BANK_URL = "./data/example-questions.json";
const QUESTION_TYPES = ["single_choice", "true_false", "fill_blank", "short_answer", "matching"];

let questionBankPromise = null;

export function preloadMockQuestions() {
  questionBankPromise ||= loadQuestionBank();
  return questionBankPromise;
}

function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function sleep(ms, signal) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => { clearTimeout(t); reject(new DOMException("aborted", "AbortError")); });
  });
}

function makeStem() {
  return pick(STEMS).replace("{a}", pick(WORDS)).replace("{b}", pick(WORDS));
}

async function loadQuestionBank() {
  try {
    const response = await fetch(QUESTION_BANK_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return normalizeQuestionBank(await response.json());
  } catch (error) {
    console.warn("Не удалось загрузить data/example-questions.json, используется генератор мока.", error);
    return null;
  }
}

function normalizeQuestionBank(payload) {
  const source = Array.isArray(payload) ? { questions: payload } : payload;
  if (!source || typeof source !== "object") throw new Error("JSON должен быть объектом или массивом вопросов");

  const questions = Array.isArray(source.questions)
    ? source.questions.map(normalizeQuestion).filter(Boolean)
    : [];
  if (!questions.length) throw new Error("В JSON нет массива questions");

  return {
    title: typeof source.title === "string" && source.title.trim() ? source.title.trim() : "",
    questions,
  };
}

function normalizeQuestion(input, index) {
  if (!input || typeof input !== "object") return null;
  const type = QUESTION_TYPES.includes(input.type) ? input.type : "single_choice";
  const base = {
    id: String(input.id || `demo-q-${index + 1}`),
    type,
    text: String(input.text || input.question || `Вопрос ${index + 1}`),
    explanation: typeof input.explanation === "string" ? input.explanation : "",
    difficulty: typeof input.difficulty === "string" ? input.difficulty : "mixed",
  };

  if (type === "matching") {
    return { ...base, pairs: normalizePairs(input), options: [] };
  }

  return { ...base, options: normalizeOptions(input, type) };
}

function normalizeOptions(input, type) {
  let options = Array.isArray(input.options) ? input.options : [];
  if (type === "true_false" && !options.length) {
    const correctTrue = Boolean(input.correct);
    options = [
      { text: "Истина", correct: correctTrue },
      { text: "Ложь", correct: !correctTrue },
    ];
  }

  const normalized = options.map((option, index) => {
    if (typeof option === "string") {
      return { id: String.fromCharCode(97 + index), text: option, correct: false };
    }
    return {
      id: String(option?.id || String.fromCharCode(97 + index)),
      text: String(option?.text || option?.label || `Вариант ${index + 1}`),
      correct: Boolean(option?.correct),
    };
  });

  if (!normalized.length && input.answer) {
    normalized.push({ id: "a", text: String(input.answer), correct: true });
  }
  if (!normalized.length) {
    normalized.push({ id: "a", text: "Ответ", correct: true });
  }
  if (!normalized.some(option => option.correct)) normalized[0].correct = true;
  if (type === "single_choice" || type === "true_false") {
    let found = false;
    normalized.forEach((option) => {
      if (option.correct && !found) found = true;
      else option.correct = false;
    });
  }
  return normalized;
}

function normalizePairs(input) {
  if (Array.isArray(input.pairs) && input.pairs.length) {
    return input.pairs.map((pair, index) => ({
      id: String(pair?.id || `pair-${index + 1}`),
      left: String(pair?.left || pair?.prompt || `Элемент ${index + 1}`),
      right: String(pair?.right || pair?.answer || `Соответствие ${index + 1}`),
    }));
  }

  if (Array.isArray(input.options) && input.options.length) {
    return input.options.map((option, index) => {
      const raw = typeof option === "string" ? option : option?.text || "";
      const parts = String(raw).split("↔").map(part => part.trim());
      return {
        id: String(option?.id || `pair-${index + 1}`),
        left: parts[0] || `Элемент ${index + 1}`,
        right: parts[1] || `Соответствие ${index + 1}`,
      };
    });
  }

  return [
    { id: "pair-1", left: "Понятие", right: "Определение" },
    { id: "pair-2", left: "Процесс", right: "Результат" },
  ];
}

function cloneQuestion(question) {
  return JSON.parse(JSON.stringify(question));
}

function getScriptedQuestions(questionBank, settings) {
  if (!questionBank?.questions?.length) return [];
  const requested = Math.max(1, Math.min(Number(settings.count) || questionBank.questions.length, questionBank.questions.length));
  return questionBank.questions.slice(0, requested).map(cloneQuestion);
}

function pickScriptedQuestion(questionBank, currentQuestion) {
  const candidates = questionBank?.questions?.filter(question =>
    question.type === currentQuestion.type && question.id !== currentQuestion.id
  ) || [];
  if (!candidates.length) return null;
  return cloneQuestion(pick(candidates));
}

function makeQuestion(_i, settings) {
  const type = pick(settings.types);
  const id   = crypto.randomUUID();
  const text = makeStem();

  if (type === "true_false") {
    const correctTrue = Math.random() > 0.5;
    return {
      id, type, text,
      options: [
        { id: "a", text: "Истина", correct: correctTrue },
        { id: "b", text: "Ложь",   correct: !correctTrue },
      ],
      explanation: settings.explanations ? "Утверждение проверяется по определению из исходного документа." : "",
      difficulty: settings.difficulty === "mixed" ? pick(["easy","medium","hard"]) : settings.difficulty,
    };
  }

  if (type === "short_answer") {
    return {
      id, type, text,
      options: [{ id: "a", text: pick(WORDS), correct: true }],
      explanation: settings.explanations ? "Краткий ответ извлечён из исходного текста." : "",
      difficulty: settings.difficulty,
    };
  }

  if (type === "fill_blank") {
    const masked = text.replace(/\b\S{5,}\b/, "_____");
    return {
      id, type, text: masked,
      options: [{ id: "a", text: pick(WORDS), correct: true }],
      explanation: settings.explanations ? "Пропущенное слово восстановлено по контексту." : "",
      difficulty: settings.difficulty,
    };
  }

  if (type === "matching") {
    const pairs = [["A", "1"], ["B", "2"], ["C", "3"], ["D", "4"]];
    return {
      id, type, text,
      options: pairs.map(([k, v], i) => ({ id: String.fromCharCode(97 + i), text: `${k} ↔ ${v}`, correct: true })),
      explanation: settings.explanations ? "Сопоставление выводится из связей в источнике." : "",
      difficulty: settings.difficulty,
    };
  }

  // single_choice (один правильный из нескольких)
  const options = ["a","b","c","d"].map((id, i) => ({
    id, text: `Вариант ответа № ${i + 1}, описывающий ${pick(WORDS)}`, correct: false,
  }));
  options[Math.floor(Math.random() * options.length)].correct = true;

  return {
    id, type, text, options,
    explanation: settings.explanations
      ? `Правильный вариант следует из ${pick(TOPICS)}, упомянутой в исходном документе.`
      : "",
    difficulty: settings.difficulty === "mixed" ? pick(["easy","medium","hard"]) : settings.difficulty,
  };
}

export async function mockGenerate({ source, settings, signal, onStage, onLog, onQuestion, onStart }) {
  onStage("upload", 4);
  onLog(`Источник: ${source.kind === "upload" ? source.file?.name : "вставленный текст"}`);
  await sleep(420, signal);

  onStage("parse", 14);
  onLog("Извлечение текста и нормализация Юникода");
  await sleep(640, signal);
  onLog("Удалены повторяющиеся пробелы и таблицы", "ok");

  onStage("chunk", 26);
  const chunks = settings.rag ? 8 : 3;
  onLog(`Документ разбит на ${chunks} блоков по ~512 токенов`);
  if (settings.rag) onLog("Построен FAISS-индекс, dim=384", "tag");
  await sleep(540, signal);

  onStage("model", 30);
  onLog(`Стартует ${settings.model}, температура 0.4`, "tag");
  await sleep(400, signal);

  const questionBank = await preloadMockQuestions();
  const scriptedQuestions = getScriptedQuestions(questionBank, settings);
  const totalQ = scriptedQuestions.length || settings.count;
  if (scriptedQuestions.length) {
    onLog(`Загружено вопросов из JSON: ${scriptedQuestions.length}`, "ok");
  } else {
    onLog("JSON с вопросами не найден или пуст, используется генератор мока", "warn");
  }
  onStart?.(totalQ);

  const quiz = {
    id: crypto.randomUUID(),
    title: deriveTitle(source, questionBank),
    createdAt: Date.now(),
    settings: { ...settings },
    questions: [],
  };

  for (let i = 0; i < totalQ; i++) {
    await sleep(360 + Math.random() * 380, signal);
    const q = scriptedQuestions[i] ? cloneQuestion(scriptedQuestions[i]) : makeQuestion(i, settings);
    quiz.questions.push(q);
    const pct = 30 + Math.round((i + 1) / totalQ * 60);
    onStage("model", pct);
    onLog(`Вопрос ${i + 1}: «${q.text.slice(0, 56)}…»`);
    onQuestion?.(q, i, totalQ);
  }

  onStage("assemble", 95);
  onLog("Дедупликация и валидация JSON-схемы", "tag");
  await sleep(420, signal);
  onLog("Все ответы валидны, квиз собран", "ok");
  onStage("assemble", 100);

  return quiz;
}

export async function mockRegenerateQuestion({ q, settings, signal }) {
  await sleep(700 + Math.random() * 600, signal);
  const questionBank = await preloadMockQuestions();
  const scriptedQuestion = pickScriptedQuestion(questionBank, q);
  if (scriptedQuestion) return scriptedQuestion;
  return makeQuestion(0, { ...settings, types: [q.type] });
}

function deriveTitle(source, questionBank) {
  if (source.kind === "upload" && source.file) {
    return source.file.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  }
  if (questionBank?.title) return questionBank.title;
  return "Квиз по вставленному тексту";
}
