const STEPPER_ORDER = ["upload", "params", "generate", "review", "edit"];
const GENERATION_PROGRESS_ORDER = ["upload", "parse", "generate", "validate"];
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

  function advanceStepper(stageName) {
    const activeIndex = STEPPER_ORDER.indexOf(stageName);
    if (activeIndex < 0 || !stepper) {
      return;
    }
    for (const [index, step] of STEPPER_ORDER.entries()) {
      if (index < activeIndex) {
        setStepState(step, "done");
      } else if (index === activeIndex) {
        setStepState(step, "active");
      } else {
        setStepState(step, null);
      }
    }
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
    waitForProgressVisibility,
    startGenerationProgress,
    advanceGenerationProgress,
    completeGenerationProgress,
    failGenerationProgress,
  };
}
