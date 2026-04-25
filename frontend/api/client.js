export class QuizCraftApiError extends Error {
  constructor(message, { status = null, payload = null } = {}) {
    super(message);
    this.name = "QuizCraftApiError";
    this.status = status;
    this.payload = payload;
  }
}

const DEFAULT_TIMEOUTS = Object.freeze({
  health: 5000,
  upload: 30000,
  generate: 120000,
  quizEditor: 15000,
});

function resolveTimeout(overrides, role) {
  const value = overrides?.[role];
  if (Number.isFinite(value) && value > 0) {
    return value;
  }
  return DEFAULT_TIMEOUTS[role];
}

export class QuizCraftApiClient {
  constructor({ baseUrl, fetchImpl, timeouts } = {}) {
    const nativeFetch = typeof globalThis.fetch === "function"
      ? globalThis.fetch.bind(globalThis)
      : null;
    const resolvedFetch = typeof fetchImpl === "function" ? fetchImpl : nativeFetch;
    if (typeof resolvedFetch !== "function") {
      throw new Error("fetch implementation is required");
    }
    this._fetch = resolvedFetch;
    this._baseUrl = baseUrl.replace(/\/+$/, "");
    this._timeouts = Object.freeze({
      health: resolveTimeout(timeouts, "health"),
      upload: resolveTimeout(timeouts, "upload"),
      generate: resolveTimeout(timeouts, "generate"),
      quizEditor: resolveTimeout(timeouts, "quizEditor"),
    });
  }

  get timeouts() {
    return this._timeouts;
  }

  getBackendHealth() {
    return this._request("/health", { timeoutMs: this._timeouts.health });
  }

  getProviderHealth() {
    return this._request("/health/lm-studio", { timeoutMs: this._timeouts.health });
  }

  getGenerationSettings() {
    return this._request("/generation/settings", { timeoutMs: this._timeouts.health });
  }

  getExportFormats() {
    return this._request("/export/formats", { timeoutMs: this._timeouts.health });
  }

  putGenerationSettings(payload) {
    return this._request("/generation/settings", {
      method: "PUT",
      json: payload,
      timeoutMs: this._timeouts.quizEditor,
    });
  }

  uploadDocument({ filename, mediaType, content, signal } = {}) {
    if (typeof filename !== "string" || !filename.trim()) {
      throw new Error("filename is required");
    }

    const resolvedMediaType = typeof mediaType === "string" && mediaType.trim()
      ? mediaType.trim()
      : "application/octet-stream";
    const query = new URLSearchParams({ filename: filename.trim() });

    return this._request(`/documents?${query.toString()}`, {
      method: "POST",
      headers: {
        "Content-Type": resolvedMediaType,
      },
      body: content,
      timeoutMs: this._timeouts.upload,
      signal,
    });
  }

  generateQuiz(documentId, payload, { signal } = {}) {
    return this._request(`/documents/${encodeURIComponent(documentId)}/generate`, {
      method: "POST",
      json: payload,
      timeoutMs: this._timeouts.generate,
      signal,
    });
  }

  getQuiz(quizId) {
    return this._request(`/quizzes/${encodeURIComponent(quizId)}`, {
      timeoutMs: this._timeouts.quizEditor,
    });
  }

  updateQuiz(quizId, payload) {
    return this._request(`/quizzes/${encodeURIComponent(quizId)}`, {
      method: "PUT",
      json: payload,
      timeoutMs: this._timeouts.quizEditor,
    });
  }

  regenerateQuestion(quizId, questionId, payload = {}) {
    const resolvedQuizId = typeof quizId === "string" ? quizId.trim() : "";
    const resolvedQuestionId = typeof questionId === "string" ? questionId.trim() : "";
    if (!resolvedQuizId) {
      throw new Error("quizId is required");
    }
    if (!resolvedQuestionId) {
      throw new Error("questionId is required");
    }

    return this._request(
      `/quizzes/${encodeURIComponent(resolvedQuizId)}/questions/${encodeURIComponent(resolvedQuestionId)}/regenerate`,
      {
        method: "POST",
        json: payload ?? {},
        timeoutMs: this._timeouts.generate,
      },
    );
  }

  async _request(path, { method = "GET", headers = {}, body, json, timeoutMs, signal } = {}) {
    const controller = new AbortController();
    const effectiveTimeout = Number.isFinite(timeoutMs) && timeoutMs > 0
      ? timeoutMs
      : this._timeouts.quizEditor;
    const timeoutId = window.setTimeout(() => controller.abort(), effectiveTimeout);

    const externalAbortHandler = () => controller.abort();
    if (signal) {
      if (signal.aborted) {
        controller.abort();
      } else if (typeof signal.addEventListener === "function") {
        signal.addEventListener("abort", externalAbortHandler, { once: true });
      }
    }

    try {
      const response = await this._fetch(`${this._baseUrl}${path}`, {
        method,
        headers: {
          Accept: "application/json",
          ...headers,
          ...(json === undefined ? {} : { "Content-Type": "application/json" }),
        },
        body: json === undefined ? body : JSON.stringify(json),
        signal: controller.signal,
      });

      const payload = await this._readJson(response);
      if (!response.ok) {
        const message = payload?.error?.message ?? `HTTP ${response.status}`;
        throw new QuizCraftApiError(message, { status: response.status, payload });
      }

      return payload;
    } catch (error) {
      if (error?.name === "AbortError") {
        if (signal?.aborted) {
          throw new QuizCraftApiError("Запрос отменён пользователем.", { status: 0 });
        }
        throw new QuizCraftApiError(
          `Превышено время ожидания ответа backend (${effectiveTimeout} мс).`,
          { status: 408 },
        );
      }
      if (error instanceof QuizCraftApiError) {
        throw error;
      }
      throw new QuizCraftApiError(error instanceof Error ? error.message : "Network request failed");
    } finally {
      window.clearTimeout(timeoutId);
      if (signal && typeof signal.removeEventListener === "function") {
        signal.removeEventListener("abort", externalAbortHandler);
      }
    }
  }

  async _readJson(response) {
    const text = await response.text();
    if (!text) {
      return {};
    }

    try {
      return JSON.parse(text);
    } catch (error) {
      throw new QuizCraftApiError("Backend returned invalid JSON", {
        status: response.status,
        payload: text,
      });
    }
  }
}
