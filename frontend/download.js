import { describeError } from "./validation-errors.js";

export function triggerJsonDownload(blob, suggestedName, windowRef = window, documentRef = document) {
  const url = windowRef.URL.createObjectURL(blob);
  const anchor = documentRef.createElement("a");
  anchor.href = url;
  anchor.download = suggestedName;
  documentRef.body.append(anchor);
  anchor.click();
  anchor.remove();
  windowRef.URL.revokeObjectURL(url);
}

export function createJsonExporter({
  backendBaseUrl,
  client,
  editorState,
  showToast,
}, windowRef = window, fetchImpl = globalThis.fetch?.bind(globalThis)) {
  async function exportQuizAsJson() {
    if (!editorState.lastGeneratedQuizId) {
      showToast("Сначала сгенерируйте или загрузите квиз.", "warn");
      return;
    }
    try {
      if (typeof fetchImpl !== "function") {
        throw new Error("fetch implementation is required");
      }
      const exportController = new AbortController();
      const exportTimeoutId = windowRef.setTimeout(
        () => exportController.abort(),
        client.timeouts.quizEditor,
      );
      let response;
      try {
        response = await fetchImpl(
          `${backendBaseUrl}/quizzes/${encodeURIComponent(editorState.lastGeneratedQuizId)}/export/json`,
          { headers: { Accept: "application/json" }, signal: exportController.signal },
        );
      } finally {
        windowRef.clearTimeout(exportTimeoutId);
      }
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const blob = await response.blob();
      triggerJsonDownload(blob, `${editorState.lastGeneratedQuizId}.json`, windowRef);
      showToast("JSON-файл квиза скачан.", "ok");
    } catch (error) {
      showToast(`Не удалось скачать JSON: ${describeError(error)}`, "bad");
    }
  }

  return { exportQuizAsJson };
}
