export function createToastController(toastRegion, windowRef = window, documentRef = document) {
  function showToast(message, tone = "ok", duration = 4200) {
    if (!toastRegion || typeof message !== "string" || !message.trim()) {
      return;
    }
    const toast = documentRef.createElement("div");
    toast.className = "toast";
    toast.setAttribute("role", "status");
    if (tone) {
      toast.dataset.tone = tone;
    }

    const dot = documentRef.createElement("span");
    dot.className = "toast-dot";
    dot.setAttribute("aria-hidden", "true");

    const body = documentRef.createElement("span");
    body.className = "toast-body";
    body.textContent = message;

    const close = documentRef.createElement("button");
    close.className = "toast-close";
    close.type = "button";
    close.setAttribute("aria-label", "Закрыть уведомление");
    close.textContent = "×";
    close.addEventListener("click", () => toast.remove());

    toast.append(dot, body, close);
    toastRegion.append(toast);

    if (Number.isFinite(duration) && duration > 0) {
      windowRef.setTimeout(() => {
        toast.remove();
      }, duration);
    }
  }

  return { showToast };
}
