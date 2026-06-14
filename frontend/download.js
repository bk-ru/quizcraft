import { describeError } from "./validation-errors.js";

const EXPORT_FORMATS = Object.freeze({
  docx: {
    extension: "docx",
    label: "DOCX",
    accept: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  },
  pptx: {
    extension: "pptx",
    label: "PPTX",
    accept: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  },
});

export function createExportFileStem(title, fallback = "quiz") {
  const rawTitle = typeof title === "string" ? title : "";
  const rawFallback = typeof fallback === "string" ? fallback : "quiz";
  const normalized = rawTitle.normalize("NFKC")
    .replace(/[^\p{L}\p{N}\s]+/gu, "")
    .trim()
    .replace(/\s+/g, "_")
    .replace(/_+/g, "_");
  if (normalized) {
    return normalized;
  }
  return rawFallback.normalize("NFKC")
    .replace(/[^\p{L}\p{N}\s]+/gu, "")
    .trim()
    .replace(/\s+/g, "_")
    .replace(/_+/g, "_") || "quiz";
}

export function triggerFileDownload(blob, suggestedName, windowRef = window, documentRef = document) {
  const url = windowRef.URL.createObjectURL(blob);
  const anchor = documentRef.createElement("a");
  anchor.href = url;
  anchor.download = suggestedName;
  documentRef.body.append(anchor);
  anchor.click();
  anchor.remove();
  windowRef.URL.revokeObjectURL(url);
}

export function triggerJsonDownload(blob, suggestedName, windowRef = window, documentRef = document) {
  triggerFileDownload(blob, suggestedName, windowRef, documentRef);
}

export function createQuizExporter({
  backendBaseUrl,
  client,
  editorState,
  getSuggestedName = null,
  showToast,
}, windowRef = window, fetchImpl = globalThis.fetch?.bind(globalThis)) {
  async function exportQuiz(format) {
    if (!editorState.lastGeneratedQuizId) {
      showToast("Сначала сгенерируйте или загрузите квиз.", "warn");
      return false;
    }
    try {
      const exportFormat = resolveExportFormat(format);
      const formatConfig = EXPORT_FORMATS[exportFormat];
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
          `${backendBaseUrl}/quizzes/${encodeURIComponent(editorState.lastGeneratedQuizId)}/export/${exportFormat}`,
          { headers: { Accept: formatConfig.accept }, signal: exportController.signal },
        );
      } finally {
        windowRef.clearTimeout(exportTimeoutId);
      }
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const blob = await response.blob();
      const fileStem = createExportFileStem(
        typeof getSuggestedName === "function" ? getSuggestedName() : "",
        editorState.lastGeneratedQuizId,
      );
      triggerFileDownload(blob, `${fileStem}.${formatConfig.extension}`, windowRef);
      showToast(`${formatConfig.label}-файл квиза скачан.`, "ok");
      return true;
    } catch (error) {
      showToast(`Не удалось скачать ${describeExportFormat(format)}: ${describeError(error)}`, "bad");
      return false;
    }
  }

  return {
    exportQuiz,
    exportQuizAsDocx: () => exportQuiz("docx"),
    exportQuizAsPptx: () => exportQuiz("pptx"),
  };
}

function resolveExportFormat(format) {
  const exportFormat = typeof format === "string" ? format.trim().toLowerCase() : "";
  if (!Object.hasOwn(EXPORT_FORMATS, exportFormat)) {
    throw new Error(`unsupported export format: ${format}`);
  }
  return exportFormat;
}

function describeExportFormat(format) {
  const exportFormat = typeof format === "string" ? format.trim().toLowerCase() : "";
  return EXPORT_FORMATS[exportFormat]?.label ?? "файл";
}
