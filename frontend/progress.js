const STEPPER_ORDER = ["upload", "params", "review", "edit"];
const GENERATION_PROGRESS_ORDER = ["upload", "parse", "generate", "validate"];
const BACKEND_STEP_TO_PROGRESS_STEP = Object.freeze({
  parse: "parse",
  generate: "generate",
  repair: "generate",
  persist: "validate",
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
const PROGRESS_STEP_VISIBILITY_MS = 300;
const PROGRESS_SUCCESS_AUTOHIDE_MS = 900;
const PROGRESS_FAILURE_AUTOHIDE_MS = 2400;

export function createProgressController({ stepper, generationProgressPanel }, windowRef = window) {
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
  }

  function advanceStepper(stageName, options = {}) {
    const activeIndex = STEPPER_ORDER.indexOf(stageName);
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
  }

  function markStepperFailed(stageName) {
    advanceStepper(stageName, { state: "failed" });
  }

  function waitForProgressVisibility(ms = PROGRESS_STEP_VISIBILITY_MS) {
    return new Promise((resolve) => windowRef.setTimeout(resolve, ms));
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
  }

  function startGenerationProgress() {
    if (!generationProgressPanel) {
      return;
    }
    resetGenerationProgress();
    setGenerationProgressVisible(true);
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
    generationProgressPanel.dataset.currentStep = "done";
    windowRef.setTimeout(() => {
      setGenerationProgressVisible(false);
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
    setGenerationProgressVisible(true);
    for (const event of events) {
      const backendStep = getBackendStep(event);
      const backendStatus = getBackendStatus(event);
      const progressStep = BACKEND_STEP_TO_PROGRESS_STEP[backendStep];
      const progressState = BACKEND_STATUS_TO_PROGRESS_STATE[backendStatus];
      if (!progressStep || !progressState) {
        continue;
      }

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
    windowRef.setTimeout(() => {
      setGenerationProgressVisible(false);
    }, PROGRESS_FAILURE_AUTOHIDE_MS);
  }

  return {
    advanceStepper,
    markStepperFailed,
    waitForProgressVisibility,
    startGenerationProgress,
    advanceGenerationProgress,
    completeGenerationProgress,
    applyBackendGenerationStatusEvidence,
    completeGenerationProgressWithBackendEvidence,
    failGenerationProgress,
  };
}
