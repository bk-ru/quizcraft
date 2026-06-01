import { triggerFileDownload } from "./download.js";
import { validateEditableQuiz } from "./question-shape.js";
import {
  serializeQuizAsCsv,
  serializeQuizAsJson,
  serializeQuizAsMarkdown,
} from "./text-export.js";

const FORMAT_CONFIG = Object.freeze({
  json: { label: "JSON", extension: "json", mediaType: "application/json;charset=utf-8", transport: "local" },
  markdown: { label: "Markdown", extension: "md", mediaType: "text/markdown;charset=utf-8", transport: "local" },
  csv: { label: "CSV", extension: "csv", mediaType: "text/csv;charset=utf-8", transport: "local" },
  docx: { label: "DOCX", extension: "docx", transport: "server" },
  pptx: { label: "PPTX", extension: "pptx", transport: "server" },
});

function normalizeFormat(format) {
  const normalized = typeof format === "string" ? format.trim().toLowerCase() : "";
  return normalized === "md" ? "markdown" : normalized;
}

function getAvailableFormats(payload) {
  const formats = Array.isArray(payload?.formats) ? payload.formats : [];
  return [...new Set(
    formats
      .map((item) => normalizeFormat(item?.format))
      .filter((format) => Object.hasOwn(FORMAT_CONFIG, format)),
  )];
}

function describeError(error) {
  return error instanceof Error && error.message ? error.message : "неизвестная ошибка";
}

function getSelectedFormat(form) {
  const selected = form.querySelector('input[name="export-format"]:checked');
  return normalizeFormat(selected?.value);
}

function createCheckbox(documentRef, { name, label, checked = false }) {
  const wrapper = documentRef.createElement("label");
  wrapper.className = "export-option";
  const input = documentRef.createElement("input");
  input.type = "checkbox";
  input.name = name;
  input.checked = checked;
  const text = documentRef.createElement("span");
  text.textContent = label;
  wrapper.append(input, text);
  return { wrapper, input };
}

export function createExportModal({
  modalRegion,
  client,
  editorState,
  getQuizSnapshot,
  saveQuiz,
  serverExporter,
  showToast = () => {},
  documentRef = (typeof document !== "undefined" ? document : null),
  windowRef = (typeof window !== "undefined" ? window : null),
  random = Math.random,
} = {}) {
  let activeDialog = null;
  let restoreFocus = null;

  function restoreTriggerFocus() {
    const target = restoreFocus;
    restoreFocus = null;
    if (!target || typeof target.focus !== "function") {
      return;
    }
    try {
      target.focus({ preventScroll: true });
    } catch (_error) {
      target.focus();
    }
  }

  function removeDialog(dialog) {
    if (dialog?.parentNode) {
      dialog.parentNode.removeChild(dialog);
    }
    if (activeDialog === dialog) {
      activeDialog = null;
      restoreTriggerFocus();
    }
  }

  function close() {
    if (!activeDialog) {
      return false;
    }
    const dialog = activeDialog;
    if (dialog.open) {
      dialog.close();
    }
    removeDialog(dialog);
    return true;
  }

  function getOptions(form) {
    return {
      includeAnswers: form.elements.namedItem("include-answers")?.checked !== false,
      includeExplanations: form.elements.namedItem("include-explanations")?.checked !== false,
      shuffleOptions: form.elements.namedItem("shuffle-options")?.checked === true,
      random,
    };
  }

  function getValidatedSnapshot() {
    const quiz = getQuizSnapshot();
    const errors = validateEditableQuiz(quiz);
    if (errors.length > 0) {
      throw new Error(`Исправьте структуру квиза:\n${errors.join("\n")}`);
    }
    return quiz;
  }

  function downloadLocalExport(format, quiz, options) {
    const config = FORMAT_CONFIG[format];
    let content;
    let warningCount = 0;
    if (format === "json") {
      content = serializeQuizAsJson(quiz, options);
    } else if (format === "markdown") {
      content = serializeQuizAsMarkdown(quiz, options);
    } else if (format === "csv") {
      const result = serializeQuizAsCsv(quiz, options);
      content = result.content;
      warningCount = result.warning_count;
    } else {
      throw new Error(`Неподдерживаемый локальный формат: ${format}`);
    }
    const blob = new Blob([content], { type: config.mediaType });
    triggerFileDownload(blob, `${quiz.quiz_id ?? "quiz"}.${config.extension}`, windowRef, documentRef);
    return warningCount;
  }

  function updateCompositionState(form, message) {
    const format = getSelectedFormat(form);
    const config = FORMAT_CONFIG[format];
    const includeAnswers = form.elements.namedItem("include-answers");
    const includeExplanations = form.elements.namedItem("include-explanations");
    const shuffleOptions = form.elements.namedItem("shuffle-options");
    const serverOnly = config?.transport === "server";
    if (includeAnswers) {
      includeAnswers.disabled = serverOnly;
    }
    if (includeExplanations) {
      includeExplanations.disabled = serverOnly || format === "csv";
    }
    if (shuffleOptions) {
      shuffleOptions.disabled = serverOnly;
    }
    message.textContent = serverOnly
      ? "Для DOCX и PPTX используются серверные настройки экспорта."
      : format === "csv"
        ? "CSV пропускает вопросы на сопоставление и сообщает их количество после скачивания."
        : "Настройте состав локального файла.";
  }

  async function executeExport(form, status) {
    const format = getSelectedFormat(form);
    const config = FORMAT_CONFIG[format];
    if (!config) {
      throw new Error("Выберите формат экспорта.");
    }
    let quiz = getValidatedSnapshot();
    if (editorState.isDirty) {
      if (typeof saveQuiz !== "function") {
        throw new Error("Сохранение изменений перед экспортом недоступно.");
      }
      status.textContent = "Сохраняем изменения перед экспортом…";
      const persistedQuiz = await saveQuiz();
      if (!persistedQuiz) {
        throw new Error("Не удалось сохранить изменения перед экспортом.");
      }
      quiz = getValidatedSnapshot();
    }
    status.textContent = "Готовим файл…";
    if (config.transport === "server") {
      if (typeof serverExporter?.exportQuiz !== "function") {
        throw new Error(`Серверная загрузка ${config.label} недоступна.`);
      }
      const downloaded = await serverExporter.exportQuiz(format);
      if (!downloaded) {
        throw new Error(`Не удалось скачать ${config.label}.`);
      }
    } else {
      const warningCount = downloadLocalExport(format, quiz, getOptions(form));
      if (warningCount > 0) {
        showToast(`Файл скачан. Пропущено вопросов matching: ${warningCount}.`, "warn");
      } else {
        showToast(`${config.label}-файл квиза скачан.`, "ok");
      }
    }
    close();
  }

  function buildDialog(availableFormats, requestedFormat) {
    const dialog = documentRef.createElement("dialog");
    dialog.className = "quiz-export-modal";
    dialog.setAttribute("aria-labelledby", "quiz-export-title");
    const heading = documentRef.createElement("div");
    heading.className = "quiz-export-heading";
    const title = documentRef.createElement("h2");
    title.id = "quiz-export-title";
    title.textContent = "Экспорт квиза";
    const closeButton = documentRef.createElement("button");
    closeButton.type = "button";
    closeButton.className = "quiz-export-close";
    closeButton.textContent = "×";
    closeButton.setAttribute("aria-label", "Закрыть экспорт");
    closeButton.title = "Закрыть экспорт";
    heading.append(title, closeButton);

    const form = documentRef.createElement("form");
    form.className = "quiz-export-form";
    const formatGroup = documentRef.createElement("fieldset");
    formatGroup.className = "export-format-grid";
    const formatLegend = documentRef.createElement("legend");
    formatLegend.textContent = "Формат файла";
    formatGroup.append(formatLegend);
    const initialFormat = availableFormats.includes(requestedFormat) ? requestedFormat : availableFormats[0];
    availableFormats.forEach((format) => {
      const config = FORMAT_CONFIG[format];
      const label = documentRef.createElement("label");
      label.className = "export-format-option";
      const input = documentRef.createElement("input");
      input.type = "radio";
      input.name = "export-format";
      input.value = format;
      input.checked = format === initialFormat;
      const text = documentRef.createElement("span");
      text.textContent = config.label;
      label.append(input, text);
      formatGroup.append(label);
    });

    const composition = documentRef.createElement("fieldset");
    composition.className = "export-composition";
    const compositionLegend = documentRef.createElement("legend");
    compositionLegend.textContent = "Состав файла";
    const answers = createCheckbox(documentRef, { name: "include-answers", label: "Добавить ответы", checked: true });
    const explanations = createCheckbox(documentRef, { name: "include-explanations", label: "Добавить пояснения", checked: true });
    const shuffle = createCheckbox(documentRef, { name: "shuffle-options", label: "Перемешать варианты ответа" });
    composition.append(compositionLegend, answers.wrapper, explanations.wrapper, shuffle.wrapper);

    const compositionMessage = documentRef.createElement("p");
    compositionMessage.className = "field-hint export-composition-message";
    const saveNotice = documentRef.createElement("p");
    saveNotice.className = "export-save-notice";
    saveNotice.textContent = "Есть несохранённые изменения. Перед экспортом они будут сохранены.";
    saveNotice.hidden = !editorState.isDirty;
    const status = documentRef.createElement("p");
    status.className = "export-modal-status";
    status.setAttribute("aria-live", "polite");
    const actions = documentRef.createElement("div");
    actions.className = "form-actions export-modal-actions";
    const cancelButton = documentRef.createElement("button");
    cancelButton.type = "button";
    cancelButton.className = "ghost-action";
    cancelButton.textContent = "Отмена";
    const exportButton = documentRef.createElement("button");
    exportButton.type = "submit";
    exportButton.className = "primary-action";
    exportButton.textContent = editorState.isDirty ? "Сохранить и скачать" : "Скачать";
    actions.append(cancelButton, exportButton);
    form.append(formatGroup, composition, compositionMessage, saveNotice, status, actions);
    dialog.append(heading, form);
    updateCompositionState(form, compositionMessage);

    formatGroup.addEventListener("change", () => updateCompositionState(form, compositionMessage));
    closeButton.addEventListener("click", close);
    cancelButton.addEventListener("click", close);
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      close();
    });
    dialog.addEventListener("close", () => removeDialog(dialog));
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        close();
      }
    });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      exportButton.disabled = true;
      try {
        await executeExport(form, status);
      } catch (error) {
        status.textContent = describeError(error);
        showToast(`Не удалось экспортировать квиз: ${describeError(error)}`, "bad");
        exportButton.disabled = false;
      }
    });
    return { dialog, form };
  }

  async function open(event) {
    event?.preventDefault();
    close();
    if (!modalRegion || !documentRef || !client || typeof getQuizSnapshot !== "function") {
      showToast("Экспорт сейчас недоступен.", "bad");
      return false;
    }
    const requestedFormat = normalizeFormat(event?.currentTarget?.dataset?.exportFormat ?? "json");
    try {
      const payload = await client.getExportFormats();
      const availableFormats = getAvailableFormats(payload);
      if (availableFormats.length === 0) {
        throw new Error("Backend не сообщил доступные форматы экспорта.");
      }
      getValidatedSnapshot();
      const { dialog, form } = buildDialog(availableFormats, requestedFormat);
      restoreFocus = typeof documentRef.activeElement?.focus === "function" ? documentRef.activeElement : null;
      modalRegion.append(dialog);
      activeDialog = dialog;
      try {
        if (typeof dialog.showModal === "function") {
          dialog.showModal();
        } else {
          dialog.setAttribute("open", "");
        }
      } catch (error) {
        removeDialog(dialog);
        throw error;
      }
      form.querySelector('input[name="export-format"]:checked')?.focus();
      return true;
    } catch (error) {
      showToast(`Не удалось открыть экспорт: ${describeError(error)}`, "bad");
      return false;
    }
  }

  return { open, close, isActive: () => Boolean(activeDialog?.open) };
}
