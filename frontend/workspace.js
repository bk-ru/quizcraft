const WORKSPACE_STAGES = Object.freeze({
  setup: "setup",
  generating: "generation",
  result: "result",
});

export function createWorkspaceController({
  root,
  stageFlow,
  bodyElement = document.body,
  documentRef = document,
} = {}) {
  let activeModal = null;
  let restoreFocus = null;

  function activateState(state, options = {}) {
    const stage = WORKSPACE_STAGES[state] ?? WORKSPACE_STAGES.setup;
    root?.setAttribute("data-workspace-state", state in WORKSPACE_STAGES ? state : "setup");
    return stageFlow.activateStage(stage, options);
  }

  function closeModal() {
    if (!activeModal) {
      return false;
    }
    activeModal.hidden = true;
    activeModal.setAttribute("aria-hidden", "true");
    bodyElement.classList.remove("workspace-modal-open");
    const focusTarget = restoreFocus;
    activeModal = null;
    restoreFocus = null;
    focusTarget?.focus({ preventScroll: true });
    return true;
  }

  function openModal(name) {
    const modal = root?.querySelector(`[data-workspace-modal="${name}"]`);
    if (!(modal instanceof HTMLElement)) {
      return false;
    }
    closeModal();
    restoreFocus = documentRef.activeElement instanceof HTMLElement
      ? documentRef.activeElement
      : null;
    activeModal = modal;
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    bodyElement.classList.add("workspace-modal-open");
    modal.querySelector("[data-workspace-modal-close]")?.focus();
    return true;
  }

  function register() {
    root?.addEventListener("click", (event) => {
      const closeButton = event.target instanceof Element
        ? event.target.closest("[data-workspace-modal-close]")
        : null;
      if (closeButton || event.target === activeModal) {
        closeModal();
      }
    });
    documentRef.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeModal();
      }
    });
  }

  return {
    activateState,
    closeModal,
    openModal,
    register,
  };
}
