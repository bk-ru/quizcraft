const DIALOG_VALUE_CONFIRM = "confirm";
const DIALOG_VALUE_CANCEL = "cancel";

function describeNode(node) {
  if (!node) {
    return "modal";
  }
  return typeof node.id === "string" && node.id ? `#${node.id}` : node.tagName ?? "modal";
}

export function createConfirmModal({
  modalRegion,
  documentRef = (typeof document !== "undefined" ? document : null),
  windowRef = (typeof window !== "undefined" ? window : null),
} = {}) {
  if (!modalRegion || !documentRef) {
    return {
      confirm: () => Promise.resolve(false),
    };
  }

  let activeDialog = null;
  let activeRestoreFocus = null;

  function ensureDialogClosed() {
    if (activeDialog instanceof HTMLDialogElement && activeDialog.open) {
      activeDialog.close(DIALOG_VALUE_CANCEL);
    }
  }

  function buildDialog({ title, body, confirmLabel, cancelLabel, tone }) {
    const dialog = documentRef.createElement("dialog");
    dialog.className = "confirm-modal";
    dialog.dataset.tone = tone === "bad" ? "bad" : (tone === "warn" ? "warn" : "info");
    dialog.setAttribute("aria-labelledby", "confirm-modal-title");
    dialog.setAttribute("aria-describedby", "confirm-modal-body");

    const heading = documentRef.createElement("h2");
    heading.id = "confirm-modal-title";
    heading.className = "confirm-modal-title";
    heading.textContent = title;

    const message = documentRef.createElement("p");
    message.id = "confirm-modal-body";
    message.className = "confirm-modal-body";
    message.textContent = body;

    const actions = documentRef.createElement("div");
    actions.className = "confirm-modal-actions";

    const cancelButton = documentRef.createElement("button");
    cancelButton.type = "button";
    cancelButton.className = "ghost-action confirm-modal-cancel";
    cancelButton.textContent = cancelLabel;
    cancelButton.dataset.modalAction = DIALOG_VALUE_CANCEL;

    const confirmButton = documentRef.createElement("button");
    confirmButton.type = "button";
    confirmButton.className = "primary-action confirm-modal-confirm";
    confirmButton.textContent = confirmLabel;
    confirmButton.dataset.modalAction = DIALOG_VALUE_CONFIRM;

    actions.append(cancelButton, confirmButton);
    dialog.append(heading, message, actions);

    return { dialog, confirmButton, cancelButton };
  }

  function confirm({
    title,
    body,
    confirmLabel = "Подтвердить",
    cancelLabel = "Отмена",
    tone = "warn",
  } = {}) {
    if (!title || !body) {
      return Promise.resolve(false);
    }

    ensureDialogClosed();

    const { dialog, confirmButton, cancelButton } = buildDialog({
      title,
      body,
      confirmLabel,
      cancelLabel,
      tone,
    });

    modalRegion.append(dialog);
    activeDialog = dialog;
    activeRestoreFocus = documentRef.activeElement instanceof HTMLElement
      ? documentRef.activeElement
      : null;

    return new Promise((resolve) => {
      let settled = false;

      const cleanup = (value) => {
        if (settled) {
          return;
        }
        settled = true;
        confirmButton.removeEventListener("click", onConfirm);
        cancelButton.removeEventListener("click", onCancel);
        dialog.removeEventListener("cancel", onDialogCancel);
        dialog.removeEventListener("close", onDialogClose);
        dialog.removeEventListener("click", onBackdropClick);
        if (dialog.open) {
          dialog.close(value);
        }
        if (dialog.parentNode) {
          dialog.parentNode.removeChild(dialog);
        }
        if (activeDialog === dialog) {
          activeDialog = null;
        }
        const restore = activeRestoreFocus;
        activeRestoreFocus = null;
        if (restore && typeof restore.focus === "function") {
          try {
            restore.focus({ preventScroll: true });
          } catch (_error) {
            try {
              restore.focus();
            } catch (_inner) {
              /* element may have been removed; ignore */
            }
          }
        }
        resolve(value === DIALOG_VALUE_CONFIRM);
      };

      const onConfirm = () => cleanup(DIALOG_VALUE_CONFIRM);
      const onCancel = () => cleanup(DIALOG_VALUE_CANCEL);
      const onDialogCancel = (event) => {
        event.preventDefault();
        cleanup(DIALOG_VALUE_CANCEL);
      };
      const onDialogClose = () => cleanup(dialog.returnValue || DIALOG_VALUE_CANCEL);
      const onBackdropClick = (event) => {
        if (event.target === dialog) {
          cleanup(DIALOG_VALUE_CANCEL);
        }
      };

      confirmButton.addEventListener("click", onConfirm);
      cancelButton.addEventListener("click", onCancel);
      dialog.addEventListener("cancel", onDialogCancel);
      dialog.addEventListener("close", onDialogClose);
      dialog.addEventListener("click", onBackdropClick);

      try {
        if (typeof dialog.showModal === "function") {
          dialog.showModal();
        } else {
          dialog.setAttribute("open", "");
        }
      } catch (error) {
        cleanup(DIALOG_VALUE_CANCEL);
        return;
      }

      const focusTarget = tone === "bad" ? cancelButton : confirmButton;
      if (windowRef && typeof windowRef.requestAnimationFrame === "function") {
        windowRef.requestAnimationFrame(() => focusTarget.focus());
      } else {
        focusTarget.focus();
      }
    });
  }

  function dismissActive(reason = DIALOG_VALUE_CANCEL) {
    if (activeDialog instanceof HTMLDialogElement && activeDialog.open) {
      activeDialog.close(reason);
      return true;
    }
    return false;
  }

  function isActive() {
    return activeDialog instanceof HTMLDialogElement && activeDialog.open;
  }

  return { confirm, dismissActive, isActive, describe: () => describeNode(activeDialog) };
}

export const CONFIRM_MODAL_VALUES = Object.freeze({
  CONFIRM: DIALOG_VALUE_CONFIRM,
  CANCEL: DIALOG_VALUE_CANCEL,
});
