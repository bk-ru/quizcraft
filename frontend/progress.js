import { normalizeWorkflowStage } from "./stage-flow.js";

const STEPPER_ORDER = ["setup", "generation", "result", "edit"];
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

export function createProgressController({ stepper, generationProgressPanel, stageFlow }, windowRef = window) {
  let progressAutoHideTimeoutId = null;

  function clearProgressAutoHide() {
    if (progressAutoHideTimeoutId !== null) {
      windowRef.clearTimeout(progressAutoHideTimeoutId);
      progressAutoHideTimeoutId = null;
    }
  }

  function setStepState(step, state) {
    if (!stepper) {
      return;
    }
    const target = stepper.querySelector(`.step[data-step="${step}"]`);
    if (!target) {
      return;
    }
    if (state) {
      target.dataset.state = state;
    } else {
      delete target.dataset.state;
    }
    if (state === "active") {
      target.setAttribute("aria-current", "step");
    } else {
      target.removeAttribute("aria-current");
    }
  }

  function advanceStepper(stageName, options = {}) {
    const normalizedStageName = normalizeWorkflowStage(stageName);
    const activeIndex = STEPPER_ORDER.indexOf(normalizedStageName);
    if (activeIndex < 0 || !stepper) {
      return;
    }
    const activeState = options && options.state === "failed" ? "failed" : "active";
    for (const [index, step] of STEPPER_ORDER.entries()) {
      if (index < activeIndex) {
        setStepState(step, "done");
      } else if (index === activeIndex) {
        setStepState(step, activeState);
      } else {
        setStepState(step, null);
      }
    }
    if (stageFlow && typeof stageFlow.activateStage === "function") {
      stageFlow.activateStage(normalizedStageName, { focus: Boolean(options.focus) });
    }
  }

  function markStepperFailed(stageName) {
    advanceStepper(stageName, { state: "failed" });
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
    const existing = generationProgressPanel.querySelector("[data-generation-skeletons]");
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
    const target = generationProgressPanel.querySelector(`.progress-step[data-step="${step}"]`);
    if (!target) {
      return;
    }
    target.dataset.state = state;
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
      } else if (progressState === "active" || !generationProgressPanel.dataset.currentStep) {
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
    advanceStepper,
    markStepperFailed,
    startGenerationProgress,
    advanceGenerationProgress,
    completeGenerationProgress,
    applyBackendGenerationStatusEvidence,
    completeGenerationProgressWithBackendEvidence,
    failGenerationProgress,
    cancelGenerationProgress,
  };
}
