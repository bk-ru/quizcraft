const STAGE_ALIASES = Object.freeze({
  upload: "setup",
  params: "setup",
  review: "result",
});

const DEFAULT_STAGE = "setup";

export function normalizeWorkflowStage(stageName) {
  const value = typeof stageName === "string" ? stageName.trim() : "";
  if (!value) {
    return DEFAULT_STAGE;
  }
  return STAGE_ALIASES[value] ?? value;
}

export function createStageFlowController({ root, documentRef = document } = {}) {
  const stageRoot = root ?? documentRef.querySelector("[data-stage-root]");

  function activateStage(stageName, { focus = false } = {}) {
    if (!stageRoot) {
      return normalizeWorkflowStage(stageName);
    }
    const activeStage = normalizeWorkflowStage(stageName);
    const stages = stageRoot.querySelectorAll("[data-workflow-stage]");
    let activeElement = null;
    for (const stage of stages) {
      const isActive = stage.dataset.workflowStage === activeStage;
      stage.hidden = !isActive;
      stage.dataset.active = String(isActive);
      if (isActive) {
        activeElement = stage;
      }
    }
    stageRoot.dataset.activeStage = activeStage;
    if (focus && activeElement instanceof HTMLElement) {
      activeElement.focus({ preventScroll: true });
    }
    return activeStage;
  }

  return {
    activateStage,
    normalizeStage: normalizeWorkflowStage,
  };
}
