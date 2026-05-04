import { describeError } from "./validation-errors.js";

const EXPORT_FORMATS = Object.freeze({
  json: {
    extension: "json",
    label: "JSON",
    accept: "application/json",
  },
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
  markdown: {
    extension: "md",
    label: "Markdown",
    accept: "text/markdown",
  },
  csv: {
    extension: "csv",
    label: "CSV",
    accept: "text/csv",
  },
});

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
  showToast,
}, windowRef = window, fetchImpl = globalThis.fetch?.bind(globalThis)) {
  async function exportQuiz(format) {
    if (!editorState.lastGeneratedQuizId) {
      showToast("Сначала сгенерируйте или загрузите квиз.", "warn");
      return;
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
      triggerFileDownload(blob, `${editorState.lastGeneratedQuizId}.${formatConfig.extension}`, windowRef);
      showToast(`${formatConfig.label}-файл квиза скачан.`, "ok");
    } catch (error) {
      showToast(`Не удалось скачать ${describeExportFormat(format)}: ${describeError(error)}`, "bad");
    }
  }

  return {
    exportQuiz,
    exportQuizAsJson: () => exportQuiz("json"),
    exportQuizAsDocx: () => exportQuiz("docx"),
    exportQuizAsPptx: () => exportQuiz("pptx"),
    exportQuizAsMarkdown: () => exportQuiz("markdown"),
    exportQuizAsCsv: () => exportQuiz("csv"),
  };
}

export function createJsonExporter(options, windowRef = window, fetchImpl = globalThis.fetch?.bind(globalThis)) {
  const exporter = createQuizExporter(options, windowRef, fetchImpl);
  return { exportQuizAsJson: exporter.exportQuizAsJson };
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
