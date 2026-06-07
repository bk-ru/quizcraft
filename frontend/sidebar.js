function formatHistoryTimestamp(value) {
  const timestamp = typeof value === "string" ? Date.parse(value) : Number.NaN;
  if (!Number.isFinite(timestamp)) {
    return "";
  }
  return new Intl.DateTimeFormat("ru", {
    day: "2-digit",
    month: "short",
  }).format(new Date(timestamp));
}

export function createSidebarController({
  sidebar,
  toggleButton,
  newQuizButton,
  historyList,
  statusCell,
  themeButton,
  historyStore,
  onNewQuiz,
  onSelectQuiz,
  onOpenStatus,
  onToggleTheme,
  documentRef = document,
} = {}) {
  function setCollapsed(collapsed) {
    if (!sidebar) {
      return false;
    }
    const next = Boolean(collapsed);
    sidebar.dataset.collapsed = String(next);
    if (toggleButton) {
      const label = next ? "Развернуть боковую панель" : "Свернуть боковую панель";
      toggleButton.setAttribute("aria-expanded", String(!next));
      toggleButton.setAttribute("aria-label", label);
      toggleButton.title = label;
    }
    return next;
  }

  function renderHistory() {
    if (!historyList || !historyStore || !documentRef) {
      return;
    }
    const entries = historyStore.loadQuizHistory();
    if (entries.length === 0) {
      const empty = documentRef.createElement("p");
      empty.className = "workspace-sidebar-empty";
      empty.textContent = "Сохранённые квизы появятся здесь.";
      historyList.replaceChildren(empty);
      return;
    }
    const buttons = entries.map((entry) => {
      const button = documentRef.createElement("button");
      button.type = "button";
      button.className = "workspace-sidebar-history-item";
      button.dataset.quizId = entry.quiz_id;

      const title = documentRef.createElement("span");
      title.className = "workspace-sidebar-history-title";
      title.textContent = entry.title || "Квиз без названия";

      const meta = documentRef.createElement("span");
      meta.className = "workspace-sidebar-history-meta";
      meta.textContent = formatHistoryTimestamp(entry.timestamp);

      button.append(title, meta);
      return button;
    });
    historyList.replaceChildren(...buttons);
  }

  function closeMobileSidebar() {
    if (typeof window === "undefined" || window.matchMedia("(max-width: 900px)").matches) {
      setCollapsed(true);
    }
  }

  function selectHistoryEntry(event) {
    const button = event.target instanceof Element
      ? event.target.closest("[data-quiz-id]")
      : null;
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }
    onSelectQuiz?.(button.dataset.quizId);
    closeMobileSidebar();
  }

  function register() {
    toggleButton?.addEventListener("click", () => {
      setCollapsed(sidebar?.dataset.collapsed !== "true");
    });
    newQuizButton?.addEventListener("click", async () => {
      const started = await onNewQuiz?.();
      if (started !== false) {
        closeMobileSidebar();
      }
    });
    historyList?.addEventListener("click", selectHistoryEntry);
    statusCell?.addEventListener("click", onOpenStatus);
    themeButton?.addEventListener("click", onToggleTheme);
    if (historyStore) {
      historyStore.subscribe(renderHistory);
    }
    renderHistory();
  }

  return {
    register,
    renderHistory,
    setCollapsed,
  };
}
