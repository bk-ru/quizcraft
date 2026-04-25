function isEditableTarget(target) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  if (target.isContentEditable) {
    return true;
  }
  const tag = target.tagName;
  if (tag === "INPUT") {
    const type = (target.getAttribute("type") || "text").toLowerCase();
    const nonEditableTypes = new Set([
      "button",
      "submit",
      "reset",
      "checkbox",
      "radio",
      "file",
      "range",
      "color",
    ]);
    return !nonEditableTypes.has(type);
  }
  return tag === "TEXTAREA" || tag === "SELECT";
}

function isPrimaryModifier(event) {
  return Boolean(event.metaKey) !== Boolean(event.ctrlKey);
}

export function createKeyboardShortcuts({
  generationForm,
  generationFlow,
  quizEditor,
  editorState,
  toastController,
  documentRef = (typeof document !== "undefined" ? document : null),
} = {}) {
  function handleKeyDown(event) {
    if (!event || typeof event.key !== "string") {
      return;
    }
    const key = event.key.toLowerCase();
    const target = event.target;

    if (key === "escape") {
      if (generationFlow && typeof generationFlow.cancelGeneration === "function") {
        const didCancel = generationFlow.cancelGeneration();
        if (didCancel) {
          event.preventDefault();
          return;
        }
      }
      if (quizEditor && typeof quizEditor.cancelActiveRegeneration === "function") {
        const didCancelRegen = quizEditor.cancelActiveRegeneration();
        if (didCancelRegen) {
          event.preventDefault();
          return;
        }
      }
      if (toastController && typeof toastController.dismissAllToasts === "function") {
        toastController.dismissAllToasts();
      }
      return;
    }

    if (key === "s" && isPrimaryModifier(event) && !event.altKey) {
      if (
        editorState
        && editorState.loadedQuiz
        && editorState.isDirty
        && quizEditor
        && typeof quizEditor.submitQuizEdits === "function"
      ) {
        event.preventDefault();
        quizEditor.submitQuizEdits();
      }
      return;
    }

    if (key === "enter" && isPrimaryModifier(event) && !event.altKey) {
      if (!generationForm) {
        return;
      }
      if (isEditableTarget(target) && target instanceof HTMLElement && !generationForm.contains(target)) {
        return;
      }
      event.preventDefault();
      if (typeof generationForm.requestSubmit === "function") {
        generationForm.requestSubmit();
      } else {
        generationForm.submit();
      }
    }
  }

  function register() {
    if (!documentRef || typeof documentRef.addEventListener !== "function") {
      return () => {};
    }
    documentRef.addEventListener("keydown", handleKeyDown);
    return () => documentRef.removeEventListener("keydown", handleKeyDown);
  }

  return { register, handleKeyDown };
}
