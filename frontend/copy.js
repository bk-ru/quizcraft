const EMPTY_VALUE_MARKERS = Object.freeze(new Set([
  "",
  "Ещё нет",
  "Ещё не загружен",
  "Ещё нет результата",
]));

function resolveSourceText(sourceElement) {
  if (!sourceElement) {
    return "";
  }
  const datasetValue = sourceElement.dataset?.copyValue;
  if (typeof datasetValue === "string" && datasetValue.trim()) {
    return datasetValue.trim();
  }
  const raw = typeof sourceElement.textContent === "string" ? sourceElement.textContent.trim() : "";
  return raw;
}

function isCopyable(value) {
  if (typeof value !== "string") {
    return false;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return false;
  }
  return !EMPTY_VALUE_MARKERS.has(trimmed);
}

export function createCopyButtonController({
  rootElement,
  clipboard = (typeof navigator !== "undefined" ? navigator.clipboard : null),
  showToast = null,
  documentRef = (typeof document !== "undefined" ? document : null),
} = {}) {
  const root = rootElement || documentRef;

  async function copyFromSource(sourceId) {
    if (!root || typeof root.querySelector !== "function") {
      return false;
    }
    const source = documentRef ? documentRef.getElementById(sourceId) : null;
    const value = resolveSourceText(source);
    if (!isCopyable(value)) {
      if (typeof showToast === "function") {
        showToast("Пока нечего копировать — значение ещё не получено.", "warn");
      }
      return false;
    }
    try {
      if (clipboard && typeof clipboard.writeText === "function") {
        await clipboard.writeText(value);
      } else {
        throw new Error("Clipboard API недоступен в этом браузере.");
      }
      if (typeof showToast === "function") {
        showToast(`Скопировано: ${value}`, "ok");
      }
      return true;
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      if (typeof showToast === "function") {
        showToast(`Не удалось скопировать: ${reason}`, "bad");
      }
      return false;
    }
  }

  function handleClick(event) {
    const target = event.target instanceof Element
      ? event.target.closest("[data-copy-for]")
      : null;
    if (!target) {
      return;
    }
    const sourceId = target.getAttribute("data-copy-for");
    if (!sourceId) {
      return;
    }
    event.preventDefault();
    copyFromSource(sourceId);
  }

  function register() {
    if (!root || typeof root.addEventListener !== "function") {
      return () => {};
    }
    root.addEventListener("click", handleClick);
    return () => root.removeEventListener("click", handleClick);
  }

  return { register, copyFromSource, handleClick };
}
