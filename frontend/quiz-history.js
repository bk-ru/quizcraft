const STORAGE_KEY = "quizcraft:recent-quizzes";
const MAX_ENTRIES = 10;

function readRawEntries(storage) {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (typeof raw !== "string" || !raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_error) {
    return [];
  }
}

function writeRawEntries(storage, entries) {
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch (_error) {
    /* localStorage unavailable (private mode, full, etc.) — degrade silently. */
  }
}

function normalizeEntry(entry) {
  if (!entry || typeof entry !== "object") {
    return null;
  }
  const quizId = typeof entry.quiz_id === "string" ? entry.quiz_id.trim() : "";
  if (!quizId) {
    return null;
  }
  const title = typeof entry.title === "string" ? entry.title.trim() : "";
  const timestamp = typeof entry.timestamp === "string" && entry.timestamp
    ? entry.timestamp
    : new Date().toISOString();
  const language = typeof entry.language === "string" && entry.language.trim()
    ? entry.language.trim()
    : null;
  const normalized = { quiz_id: quizId, title, timestamp };
  if (language) {
    normalized.language = language;
  }
  return normalized;
}

export function createQuizHistory({
  storage = (typeof window !== "undefined" ? window.localStorage : null),
  datalistElement = null,
  documentRef = (typeof document !== "undefined" ? document : null),
} = {}) {
  const storageRef = storage ?? null;

  function loadQuizHistory() {
    if (!storageRef) {
      return [];
    }
    const entries = readRawEntries(storageRef)
      .map(normalizeEntry)
      .filter((entry) => entry !== null);
    return entries.slice(0, MAX_ENTRIES);
  }

  function renderHistoryDatalist() {
    if (!datalistElement || !documentRef) {
      return;
    }
    const entries = loadQuizHistory();
    const options = entries.map((entry) => {
      const option = documentRef.createElement("option");
      option.value = entry.quiz_id;
      option.textContent = entry.title
        ? `${entry.title} — ${entry.quiz_id}`
        : entry.quiz_id;
      return option;
    });
    datalistElement.replaceChildren(...options);
  }

  function saveQuizToHistory({ quiz_id, title, language } = {}) {
    if (!storageRef) {
      return loadQuizHistory();
    }
    const candidate = normalizeEntry({
      quiz_id,
      title,
      language,
      timestamp: new Date().toISOString(),
    });
    if (!candidate) {
      return loadQuizHistory();
    }
    const existing = loadQuizHistory().filter((entry) => entry.quiz_id !== candidate.quiz_id);
    const next = [candidate, ...existing].slice(0, MAX_ENTRIES);
    writeRawEntries(storageRef, next);
    renderHistoryDatalist();
    return next;
  }

  function findLanguageByQuizId(quizId) {
    const normalizedId = typeof quizId === "string" ? quizId.trim() : "";
    if (!normalizedId) {
      return null;
    }
    const match = loadQuizHistory().find((entry) => entry.quiz_id === normalizedId);
    return match && typeof match.language === "string" && match.language ? match.language : null;
  }

  function removeQuizFromHistory(quizId) {
    if (!storageRef) {
      return loadQuizHistory();
    }
    const normalizedId = typeof quizId === "string" ? quizId.trim() : "";
    if (!normalizedId) {
      return loadQuizHistory();
    }
    const next = loadQuizHistory().filter((entry) => entry.quiz_id !== normalizedId);
    writeRawEntries(storageRef, next);
    renderHistoryDatalist();
    return next;
  }

  function clearQuizHistory() {
    if (!storageRef) {
      return;
    }
    try {
      storageRef.removeItem(STORAGE_KEY);
    } catch (_error) {
      /* ignore */
    }
    renderHistoryDatalist();
  }

  return {
    loadQuizHistory,
    saveQuizToHistory,
    removeQuizFromHistory,
    clearQuizHistory,
    renderHistoryDatalist,
    findLanguageByQuizId,
  };
}

export const QUIZ_HISTORY_STORAGE_KEY = STORAGE_KEY;
export const QUIZ_HISTORY_MAX_ENTRIES = MAX_ENTRIES;
