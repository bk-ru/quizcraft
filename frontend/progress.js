import { normalizeWorkflowStage } from "./stage-flow.js";

const GENERATION_PROGRESS_ORDER = ["upload", "parse", "generate", "persist"];
const BACKEND_STEP_TO_PROGRESS_STEP = Object.freeze({
  parse: "parse",
  generate: "generate",
  repair: "generate",
  persist: "persist",
});
const BACKEND_STATUS_TO_PROGRESS_STATE = Object.freeze({
  queued: "pending",
  running: "active",
  done: "done",
  failed: "failed",
});
const BACKEND_STATUS_EVENT_KEYS = Object.freeze([
  "generation_status",
  "pipeline_status",
  "pipeline_events",
]);
const SUCCESSFUL_GENERATION_EVIDENCE = Object.freeze([
  Object.freeze({ step: "generate", status: "done" }),
  Object.freeze({ step: "persist", status: "done" }),
]);
const PROGRESS_SUCCESS_AUTOHIDE_MS = 900;
const PROGRESS_FAILURE_AUTOHIDE_MS = 2400;
const PROGRESS_PERCENT_BY_STATE = Object.freeze({
  upload: Object.freeze({ pending: 0, active: 8, done: 25, failed: 8 }),
  parse: Object.freeze({ pending: 25, active: 36, done: 50, failed: 36 }),
  generate: Object.freeze({ pending: 50, active: 68, done: 84, failed: 68 }),
  persist: Object.freeze({ pending: 84, active: 92, done: 100, failed: 92 }),
});

export function createProgressController(
  { generationProgressPanel, stageFlow },
  windowRef = window,
) {
  let progressAutoHideTimeoutId = null;

  function clearProgressAutoHide() {
    if (progressAutoHideTimeoutId !== null) {
      windowRef.clearTimeout(progressAutoHideTimeoutId);
      progressAutoHideTimeoutId = null;
    }
  }

  function activateWorkflowStage(
    stageName,
    { focus = false, state = null } = {},
  ) {
    const normalizedStageName = normalizeWorkflowStage(stageName);
    if (stageFlow && typeof stageFlow.activateStage === "function") {
      stageFlow.activateStage(normalizedStageName, { focus: Boolean(focus) });
    }
    if (stageFlow?.root?.dataset) {
      if (state === "failed") {
        stageFlow.root.dataset.failedStage = normalizedStageName;
      } else if (stageFlow.root.dataset.failedStage === normalizedStageName) {
        delete stageFlow.root.dataset.failedStage;
      }
    }
    return normalizedStageName;
  }

  function markWorkflowStageFailed(stageName) {
    return activateWorkflowStage(stageName, { state: "failed", focus: true });
  }

  function setGenerationProgressVisible(visible) {
    if (!generationProgressPanel) {
      return;
    }
    if (visible) {
      generationProgressPanel.hidden = false;
      generationProgressPanel.dataset.visible = "true";
    } else {
      generationProgressPanel.hidden = true;
      delete generationProgressPanel.dataset.visible;
    }
  }

  function ensureGenerationSkeletons() {
    if (!generationProgressPanel) {
      return null;
    }
    const existing = generationProgressPanel.querySelector(
      "[data-generation-skeletons]",
    );
    if (existing) {
      return existing;
    }
    const documentRef = generationProgressPanel.ownerDocument;
    if (!documentRef) {
      return null;
    }
    const stream = documentRef.createElement("div");
    stream.className = "generation-skeleton-stream";
    stream.setAttribute("data-generation-skeletons", "true");
    stream.setAttribute("aria-hidden", "true");
    for (let index = 0; index < 2; index += 1) {
      const card = documentRef.createElement("div");
      card.className = "generation-skeleton-card";
      for (const modifier of ["title", "wide", "short"]) {
        const bar = documentRef.createElement("span");
        bar.className = `generation-skeleton-bar generation-skeleton-bar--${modifier}`;
        card.append(bar);
      }
      stream.append(card);
    }
    generationProgressPanel.append(stream);
    return stream;
  }

  function setGenerationSkeletonsVisible(visible) {
    const skeletons = visible
      ? ensureGenerationSkeletons()
      : generationProgressPanel?.querySelector("[data-generation-skeletons]");
    if (skeletons) {
      skeletons.hidden = !visible;
    }
  }

  function setGenerationProgressStepState(step, state) {
    if (!generationProgressPanel) {
      return;
    }
    const target = generationProgressPanel.querySelector(
      `.progress-step[data-step="${step}"]`,
    );
    if (!target) {
      return;
    }
    target.dataset.state = state;
    const percentage = PROGRESS_PERCENT_BY_STATE[step]?.[state];
    if (Number.isFinite(percentage)) {
      const progressFill = generationProgressPanel.querySelector(".generation-progress-fill");
      const progressPercent = generationProgressPanel.querySelector(".generation-progress-percent");
      if (progressFill) {
        progressFill.style.width = `${percentage}%`;
      }
      if (progressPercent) {
        progressPercent.textContent = `${percentage}%`;
      }
    }
  }

  function resetGenerationProgress() {
    if (!generationProgressPanel) {
      return;
    }
    for (const step of GENERATION_PROGRESS_ORDER) {
      setGenerationProgressStepState(step, "pending");
    }
    generationProgressPanel.dataset.currentStep = "";
    delete generationProgressPanel.dataset.backendStep;
    delete generationProgressPanel.dataset.backendStatus;
    setGenerationSkeletonsVisible(false);
  }

  function startGenerationProgress() {
    if (!generationProgressPanel) {
      return;
    }
    clearProgressAutoHide();
    resetGenerationProgress();
    setGenerationProgressVisible(true);
    setGenerationSkeletonsVisible(true);
    setGenerationProgressStepState("upload", "active");
    generationProgressPanel.dataset.currentStep = "upload";
  }

  function advanceGenerationProgress(completedStep, nextStep) {
    if (!generationProgressPanel) {
      return;
    }
    if (completedStep) {
      setGenerationProgressStepState(completedStep, "done");
    }
    if (nextStep) {
      setGenerationProgressStepState(nextStep, "active");
      generationProgressPanel.dataset.currentStep = nextStep;
    } else {
      generationProgressPanel.dataset.currentStep = "";
    }
  }

  function completeGenerationProgress() {
    if (!generationProgressPanel) {
      return;
    }
    for (const step of GENERATION_PROGRESS_ORDER) {
      setGenerationProgressStepState(step, "done");
    }
    setGenerationSkeletonsVisible(false);
    generationProgressPanel.dataset.currentStep = "done";
    clearProgressAutoHide();
    progressAutoHideTimeoutId = windowRef.setTimeout(() => {
      setGenerationProgressVisible(false);
      progressAutoHideTimeoutId = null;
    }, PROGRESS_SUCCESS_AUTOHIDE_MS);
  }

  function getBackendStep(event) {
    if (!event || typeof event !== "object") {
      return "";
    }
    const value = event.step ?? event.phase ?? event.name;
    return typeof value === "string" ? value : "";
  }

  function getBackendStatus(event) {
    if (!event || typeof event !== "object") {
      return "";
    }
    const value = event.status ?? event.state;
    return typeof value === "string" ? value : "";
  }

  function normalizeBackendEvidence(source) {
    if (!source || typeof source !== "object") {
      return [];
    }
    if (Array.isArray(source)) {
      return source;
    }
    for (const key of BACKEND_STATUS_EVENT_KEYS) {
      const value = source[key];
      if (Array.isArray(value)) {
        return value;
      }
      if (value && typeof value === "object") {
        return [value];
      }
    }
    if (getBackendStep(source) && getBackendStatus(source)) {
      return [source];
    }
    return [];
  }

  function applyBackendGenerationStatusEvidence(source) {
    if (!generationProgressPanel) {
      return false;
    }
    const events = normalizeBackendEvidence(source);
    if (events.length === 0) {
      return false;
    }

    let applied = false;
    for (const event of events) {
      const backendStep = getBackendStep(event);
      const backendStatus = getBackendStatus(event);
      const progressStep = BACKEND_STEP_TO_PROGRESS_STEP[backendStep];
      const progressState = BACKEND_STATUS_TO_PROGRESS_STATE[backendStatus];
      if (!progressStep || !progressState) {
        continue;
      }

      setGenerationProgressVisible(true);
      setGenerationProgressStepState(progressStep, progressState);
      generationProgressPanel.dataset.backendStep = backendStep;
      generationProgressPanel.dataset.backendStatus = backendStatus;
      if (backendStatus === "failed") {
        generationProgressPanel.dataset.currentStep = "failed";
      } else if (backendStatus === "done" && backendStep === "persist") {
        generationProgressPanel.dataset.currentStep = "done";
      } else if (
        progressState === "active" ||
        !generationProgressPanel.dataset.currentStep
      ) {
        generationProgressPanel.dataset.currentStep = progressStep;
      }
      applied = true;
    }
    return applied;
  }

  function completeGenerationProgressWithBackendEvidence(generationPayload) {
    const applied = applyBackendGenerationStatusEvidence(generationPayload);
    if (!applied) {
      applyBackendGenerationStatusEvidence(SUCCESSFUL_GENERATION_EVIDENCE);
    }
    completeGenerationProgress();
  }

  function failGenerationProgress(failedStep) {
    if (!generationProgressPanel) {
      return;
    }
    if (failedStep) {
      setGenerationProgressStepState(failedStep, "failed");
      generationProgressPanel.dataset.currentStep = "failed";
    }
    setGenerationSkeletonsVisible(false);
    clearProgressAutoHide();
    progressAutoHideTimeoutId = windowRef.setTimeout(() => {
      setGenerationProgressVisible(false);
      progressAutoHideTimeoutId = null;
    }, PROGRESS_FAILURE_AUTOHIDE_MS);
  }

  function cancelGenerationProgress() {
    if (!generationProgressPanel) {
      return;
    }
    clearProgressAutoHide();
    resetGenerationProgress();
    setGenerationProgressVisible(false);
  }

  return {
    activateWorkflowStage,
    markWorkflowStageFailed,
    startGenerationProgress,
    advanceGenerationProgress,
    completeGenerationProgress,
    applyBackendGenerationStatusEvidence,
    completeGenerationProgressWithBackendEvidence,
    failGenerationProgress,
    cancelGenerationProgress,
  };
}
