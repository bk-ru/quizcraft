export class QuizCraftApiError extends Error {
  constructor(message, { status = null, payload = null } = {}) {
    super(message);
    this.name = "QuizCraftApiError";
    this.status = status;
    this.payload = payload;
  }
}

export class QuizCraftApiClient {
  constructor({ baseUrl, fetchImpl, requestTimeoutMs = 8000 }) {
    const nativeFetch = typeof globalThis.fetch === "function"
      ? globalThis.fetch.bind(globalThis)
      : null;
    const resolvedFetch = typeof fetchImpl === "function" ? fetchImpl : nativeFetch;
    if (typeof resolvedFetch !== "function") {
      throw new Error("fetch implementation is required");
    }
    this._fetch = resolvedFetch;
    this._baseUrl = baseUrl.replace(/\/+$/, "");
    this._requestTimeoutMs = requestTimeoutMs;
  }

  getBackendHealth() {
    return this._request("/health");
  }

  getProviderHealth() {
    return this._request("/health/lm-studio");
  }

  uploadDocument({ filename, mediaType, content }) {
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
    });
  }

  generateQuiz(documentId, payload) {
    return this._request(`/documents/${encodeURIComponent(documentId)}/generate`, {
      method: "POST",
      json: payload,
    });
  }

  getQuiz(quizId) {
    return this._request(`/quizzes/${encodeURIComponent(quizId)}`);
  }

  updateQuiz(quizId, payload) {
    return this._request(`/quizzes/${encodeURIComponent(quizId)}`, {
      method: "PUT",
      json: payload,
    });
  }

  async _request(path, { method = "GET", headers = {}, body, json } = {}) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), this._requestTimeoutMs);

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
        throw new QuizCraftApiError("Request timed out", { status: 408 });
      }
      if (error instanceof QuizCraftApiError) {
        throw error;
      }
      throw new QuizCraftApiError(error instanceof Error ? error.message : "Network request failed");
    } finally {
      window.clearTimeout(timeoutId);
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
