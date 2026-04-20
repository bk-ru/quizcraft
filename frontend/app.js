import { QuizCraftApiClient, QuizCraftApiError } from "./api/client.js";

const config = window.QuizCraftConfig ?? {};
const backendBaseUrl = typeof config.backendBaseUrl === "string" && config.backendBaseUrl.trim()
  ? config.backendBaseUrl.trim()
  : "http://127.0.0.1:8000";
const requestTimeoutMs = Number.isFinite(config.requestTimeoutMs) ? config.requestTimeoutMs : 8000;

const client = new QuizCraftApiClient({
  baseUrl: backendBaseUrl,
  requestTimeoutMs,
});

const statusMap = {
  ok: "ok",
  available: "ok",
  unavailable: "warn",
};

function setTextContent(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function setStatus(surface, text, tone) {
  const container = document.querySelector(`[data-status-surface="${surface}"]`);
  const target = document.getElementById(`${surface}-status-text`);
  if (target) {
    target.textContent = text;
  }
  if (container) {
    if (tone) {
      container.dataset.statusTone = tone;
    } else {
      delete container.dataset.statusTone;
    }
  }
}

function setLogMessage(text, tone) {
  const element = document.getElementById("shell-log-message");
  if (!element) {
    return;
  }
  element.textContent = text;
  if (tone) {
    element.dataset.statusTone = tone;
  } else {
    delete element.dataset.statusTone;
  }
}

function describeError(error) {
  if (error instanceof QuizCraftApiError) {
    return `${error.status ?? "network"}: ${error.message}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Неизвестная ошибка";
}

async function bootstrapShell() {
  setTextContent("backend-base-url", backendBaseUrl);
  setTextContent("request-timeout", `${requestTimeoutMs} мс`);

  try {
    const [backendHealth, providerHealth] = await Promise.all([
      client.getBackendHealth(),
      client.getProviderHealth(),
    ]);

    setStatus(
      "backend",
      `Доступен · модель ${backendHealth.default_model}`,
      statusMap[backendHealth.status] ?? "ok",
    );
    setStatus(
      "provider",
      `${providerHealth.status} · ${providerHealth.message}`,
      statusMap[providerHealth.status] ?? "warn",
    );
    setLogMessage("Shell успешно связался с backend health endpoint-ами.", "ok");
  } catch (error) {
    setStatus("backend", "Проверка не удалась", "bad");
    setStatus("provider", "Проверка не удалась", "bad");
    setLogMessage(`Shell не смог получить health-статус: ${describeError(error)}`, "bad");
  }
}

bootstrapShell();
