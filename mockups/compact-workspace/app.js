/* ════════════════════════════════════════════════════════════════
   QuizCraft prototype — поведение
   Ванильный ES module, без зависимостей. Мокает API генерации,
   реализует ввод, прогресс, инлайн-редактор, экспорт и плей-режим.
   ════════════════════════════════════════════════════════════════ */

import { mockGenerate, mockRegenerateQuestion, preloadMockQuestions } from "./mock-api.js?v=20260617-json-data";

/* ─── Question types catalog (как в исходном репозитории) ─────── */
const TYPE_LABELS = {
  single_choice: "Множественный выбор",
  true_false:    "Истина / Ложь",
  fill_blank:    "Заполните пробел",
  short_answer:  "Краткий ответ",
  matching:      "Соответствие",
};
const TYPE_ORDER = ["single_choice", "true_false", "fill_blank", "short_answer", "matching"];

/* ─── State ──────────────────────────────────────────── */
const state = {
  source:        { kind: "paste", file: null, text: "" },
  settings: {
    count:         10,
    difficulty:    "mixed",
    language:      "ru",
    model:         "qwen2.5-14b",
    generationMode:"auto",
    temperature:   0.2,
    lmStudio:      { host: "", port: "1234" },
    types:         new Set(["single_choice"]),
    explanations:  false,
    rag:           false,
    cite:          false,
  },
  generation:    { running: false, controller: null, startedAt: 0 },
  quiz:          null,           // { id, title, version, last_edited_at, createdAt, settings, questions: [...] }
  history:       [],
  undoStack:     [],
  exportFormat:  "json",
  regenerating:  new Map(),
};

const DEMO_TEXT_URL = "./data/example-text.json";
const DEFAULT_EXAMPLE_TEXT = `Фотосинтез — процесс, при котором растения используют энергию света для преобразования углекислого газа и воды в органические вещества. Основной пигмент, участвующий в поглощении света, называется хлорофилл. Световая фаза проходит на мембранах тилакоидов, где образуются АТФ и НАДФН. В темновой фазе, или цикле Кальвина, углекислый газ фиксируется и превращается в сахара. Этот процесс важен для экосистем, потому что растения создают органическое вещество и выделяют кислород.`;
const demoText = {
  title: "Пример текста",
  text: DEFAULT_EXAMPLE_TEXT,
  loaded: false,
};

async function loadDemoText() {
  try {
    const response = await fetch(DEMO_TEXT_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const text = typeof payload === "string" ? payload : payload?.text;
    if (typeof text !== "string" || !text.trim()) throw new Error("В JSON нет поля text");
    demoText.title = typeof payload?.title === "string" && payload.title.trim() ? payload.title.trim() : "Пример текста";
    demoText.text = text.trim();
    demoText.loaded = true;
  } catch (error) {
    console.warn("Не удалось загрузить data/example-text.json, используется встроенный пример.", error);
  }
}

/* ─── DOM helpers ────────────────────────────────────── */
const $  = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const setText = (sel, text) => { const node = $(sel); if (node) node.textContent = text; };
const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (v === true) node.setAttribute(k, "");
    else if (v !== false && v != null) node.setAttribute(k, v);
  }
  for (const kid of kids) if (kid != null) node.append(kid.nodeType ? kid : document.createTextNode(kid));
  return node;
};

/* ─── Toast ──────────────────────────────────────────── */
function toast(text, { kind = "info", ttl = 3200 } = {}) {
  const region = $("#toasts");
  const node = el("div", { class: "toast", "data-kind": kind }, text);
  region.append(node);
  setTimeout(() => { node.classList.add("is-out"); node.addEventListener("animationend", () => node.remove(), { once: true }); }, ttl);
}

/* ─── Theme ──────────────────────────────────────────── */
function setupTheme() {
  const stored = localStorage.getItem("qc.theme");
  if (stored) document.documentElement.dataset.theme = stored;
  $("#theme-toggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("qc.theme", next);
  });
}

/* ─── Sidebar ───────────────────────────────────────── */
function setupSidebar() {
  const sb = $("#sidebar");
  const stored = localStorage.getItem("qc.sidebar.collapsed");
  if (stored === "true") sb.dataset.collapsed = "true";

  $("#sidebar-toggle").addEventListener("click", () => {
    const next = sb.dataset.collapsed !== "true";
    sb.dataset.collapsed = String(next);
    localStorage.setItem("qc.sidebar.collapsed", String(next));
  });

  // Mobile open/close
  const scrim = el("div", { class: "sidebar-scrim", onclick: () => document.body.dataset.sidebarOpen = "false" });
  const menuBtn = el("button", { class: "mobile-menu-btn", "aria-label": "Меню",
    onclick: () => document.body.dataset.sidebarOpen = "true" },
    el("svg", { viewBox: "0 0 24 24", width: "20", height: "20", fill: "none", stroke: "currentColor", "stroke-width": "1.8", html: '<path d="M3 6h18M3 12h18M3 18h18"/>' }),
  );
  document.body.append(scrim, menuBtn);

  // New quiz button + nav
  $("#new-quiz").addEventListener("click", () => {
    state.quiz = null;
    state.undoStack = [];
    showSection("workbench");
    setActiveNav("create");
    document.body.dataset.sidebarOpen = "false";
  });

  $$(".nav-item").forEach(b => b.addEventListener("click", () => {
    const route = b.dataset.route;
    setActiveNav(route);
    if (route === "create") {
      showSection("workbench");
    } else if (route === "history") {
      // прокрутим к секции истории в сайдбаре — она там же
      $(".sidebar-section-label")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (route === "settings") {
      openModal("modal-status");
    }
    document.body.dataset.sidebarOpen = "false";
  }));

  $(".brand[data-action='home']")?.addEventListener("click", (e) => { e.preventDefault(); $("#new-quiz").click(); });
}

function setActiveNav(name) {
  $$(".nav-item").forEach(b => b.classList.toggle("is-active", b.dataset.route === name));
}

/* ─── Tabs (paste | upload) ──────────────────────────── */
function setupTabs() {
  const tabs = $$(".tab");
  const indicator = $(".tab-indicator");
  if (!tabs.length || !indicator) return;

  function moveIndicator(target) {
    const r = target.getBoundingClientRect();
    const parent = target.parentElement.getBoundingClientRect();
    indicator.style.width = `${r.width}px`;
    indicator.style.transform = `translateX(${r.left - parent.left - 4}px)`;
  }

  function select(name) {
    tabs.forEach(t => {
      const on = t.dataset.tab === name;
      t.setAttribute("aria-selected", on ? "true" : "false");
      if (on) moveIndicator(t);
    });
    $$(".tab-panel").forEach(p => p.hidden = p.dataset.panel !== name);
    state.source.kind = name;
    refreshGenerateAvailability();
  }

  tabs.forEach(t => t.addEventListener("click", () => select(t.dataset.tab)));
  requestAnimationFrame(() => moveIndicator(tabs[0]));
  window.addEventListener("resize", () => {
    const active = tabs.find(t => t.getAttribute("aria-selected") === "true");
    if (active) moveIndicator(active);
  });
}

/* ─── File input + dropzone ──────────────────────────── */
function setupFileInput() {
  const zone = $("#dropzone");
  const input = $("#file-input");
  const preview = $("#file-preview");
  const overlay = $("#drop-overlay");
  if (!input) return;

  function attachFile(file) {
    if (!file) return;
    const ok = /\.(txt|docx|pdf)$/i.test(file.name);
    if (!ok) { toast("Поддерживаются только TXT, DOCX, PDF", { kind: "warn" }); return; }
    if (file.size > 10 * 1024 * 1024) { toast("Файл больше 10 МБ", { kind: "bad" }); return; }
    state.source.file = file;
    state.source.kind = "paste";
    $("#file-name").textContent = file.name;
    const kb = (file.size / 1024).toFixed(1);
    const words = Math.round(file.size / 6.5);
    $("#file-stats").textContent = `${kb} КБ · ~${words.toLocaleString("ru")} слов`;
    $("#doc-file-pill-name").textContent = file.name;
    $("#doc-file-pill").hidden = false;
    preview.hidden = false;
    updateDocumentMetrics();
    refreshEstimate();
    refreshGenerateAvailability();
  }

  zone?.addEventListener("click", () => input.click());
  zone?.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  input.addEventListener("change", () => attachFile(input.files[0]));
  $("#file-remove").addEventListener("click", (e) => {
    e.stopPropagation();
    state.source.file = null; preview.hidden = true; input.value = "";
    $("#doc-file-pill").hidden = true;
    updateDocumentMetrics();
    refreshGenerateAvailability();
  });
  $("#doc-file-remove")?.addEventListener("click", () => $("#file-remove").click());

  let depth = 0;
  window.addEventListener("dragenter", (e) => {
    if (!e.dataTransfer.types.includes("Files")) return;
    depth++; overlay?.classList.add("is-on");
  });
  window.addEventListener("dragover", (e) => { e.preventDefault(); });
  window.addEventListener("dragleave", () => { depth = Math.max(0, depth - 1); if (!depth) overlay?.classList.remove("is-on"); });
  window.addEventListener("drop", (e) => {
    e.preventDefault(); depth = 0; overlay?.classList.remove("is-on");
    attachFile(e.dataTransfer.files?.[0]);
  });

  zone?.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("is-dragover"); });
  zone?.addEventListener("dragleave", () => zone.classList.remove("is-dragover"));
  zone?.addEventListener("drop", () => zone.classList.remove("is-dragover"));
}

/* ─── Paste area metrics ─────────────────────────────── */
function setupPasteMetrics() {
  const ta = $("#paste-area");
  const w = $("#paste-words"); const c = $("#paste-chars");
  ta.addEventListener("input", () => {
    const txt = ta.value;
    state.source.text = txt;
    const words = txt.trim() ? txt.trim().split(/\s+/).length : 0;
    const chars = txt.length;
    w.textContent = `${words.toLocaleString("ru")} слов`;
    c.textContent = `${chars.toLocaleString("ru")} символов`;
    updateDocumentMetrics();
    refreshEstimate();
    refreshGenerateAvailability();
  });
}

function setupSourceToolbar() {
  $("#doc-clear-button")?.addEventListener("click", () => {
    state.source.file = null;
    state.source.text = "";
    $("#paste-area").value = "";
    $("#file-input").value = "";
    $("#file-preview").hidden = true;
    $("#doc-file-pill").hidden = true;
    $("#paste-words").textContent = "0 слов";
    $("#paste-chars").textContent = "0 символов";
    updateDocumentMetrics();
    refreshGenerateAvailability();
    toast("Ввод очищен");
  });

  $("#doc-example-button")?.addEventListener("click", () => {
    state.source.kind = "paste";
    state.source.text = demoText.text;
    $("#paste-area").value = demoText.text;
    $("#paste-area").dispatchEvent(new Event("input", { bubbles: true }));
    toast(demoText.loaded ? "Вставлен пример из JSON" : "Вставлен встроенный пример", { kind: "ok" });
  });

  updateDocumentMetrics();
}

function updateDocumentMetrics() {
  const chars = state.source.text?.length || 0;
  const words = state.source.text?.trim() ? state.source.text.trim().split(/\s+/).length : 0;
  const file = state.source.file;
  const charCount = $("#char-count");
  if (charCount) {
    charCount.textContent = file
      ? `${file.name} · ${(file.size / 1024).toFixed(1)} КБ`
      : `${chars.toLocaleString("ru")} символов · ${words.toLocaleString("ru")} слов`;
  }
  const hint = $("#doc-length-hint");
  if (!hint) return;
  if (file) {
    hint.hidden = false;
    hint.textContent = "Файл будет использоваться вместо вставленного текста.";
  } else if (chars > 0 && chars < 300) {
    hint.hidden = false;
    hint.textContent = "Для качественной генерации лучше добавить ещё текста.";
  } else {
    hint.hidden = true;
  }
}

/* ─── Settings: count, segments, selects, types ──────── */
function setupSettings() {
  const count = $("#count");
  const countInput = $("#count-input");

  function syncCount(val) {
    val = Math.max(3, Math.min(50, Math.round(+val || 10)));
    state.settings.count = val;
    if (count.value !== String(val)) count.value = val;
    if (countInput.value !== String(val)) countInput.value = val;
    refreshEstimate();
  }
  count.addEventListener("input", () => syncCount(count.value));
  countInput.addEventListener("input", () => {
    // во время ввода сохраняем как есть, чтобы не мешать удалению
    if (countInput.value === "") return;
    syncCount(countInput.value);
  });
  countInput.addEventListener("blur", () => { if (!countInput.value) syncCount(10); });

  $$(".seg-btn[data-difficulty]").forEach(b => b.addEventListener("click", () => {
    state.settings.difficulty = b.dataset.difficulty;
    $$(".seg-btn[data-difficulty]").forEach(x => { x.classList.toggle("is-on", x === b); x.setAttribute("aria-checked", x === b ? "true" : "false"); });
  }));

  $("#lang").addEventListener("change", (e) => { state.settings.language = e.target.value; });
  $("#model")?.addEventListener("change", (e) => {
    state.settings.model = e.target.value;
    $("#status-model").textContent = e.target.value;
    $("#quiz-model-name") && ($("#quiz-model-name").textContent = e.target.value);
    refreshEstimate();
  });

  $$(".chip[data-type]").forEach(c => c.addEventListener("click", () => {
    const t = c.dataset.type;
    if (state.settings.types.has(t)) {
      if (state.settings.types.size === 1) { toast("Выберите хотя бы один тип вопросов", { kind: "warn" }); return; }
      state.settings.types.delete(t);
    } else {
      state.settings.types.add(t);
    }
    c.classList.toggle("is-on");
    c.setAttribute("aria-pressed", c.classList.contains("is-on") ? "true" : "false");
    refreshEstimate();
  }));

  $("#opt-explanations")?.addEventListener("change", (e) => { state.settings.explanations = e.target.checked; refreshEstimate(); });
  $("#opt-rag")?.addEventListener("change", (e) => { state.settings.rag = e.target.checked; refreshEstimate(); });
  $("#opt-cite")?.addEventListener("change", (e) => { state.settings.cite = e.target.checked; });

  $("#generation-mode")?.addEventListener("change", (e) => {
    state.settings.generationMode = e.target.value;
    state.settings.rag = e.target.value === "rag";
    const ragToggle = $("#opt-rag");
    if (ragToggle) ragToggle.checked = state.settings.rag;
    refreshEstimate();
  });

  $("#generation-temperature")?.addEventListener("input", (e) => {
    state.settings.temperature = Number(e.target.value);
    $("#generation-temperature-value").textContent = Number(e.target.value).toFixed(1);
  });

  $("#apply-lm-studio-connection")?.addEventListener("click", () => {
    state.settings.lmStudio.host = $("#lm-studio-host").value.trim();
    state.settings.lmStudio.port = $("#lm-studio-port").value.trim() || "1234";
    const status = $("#lm-studio-connection-status");
    if (status) {
      status.hidden = false;
      status.textContent = `Макет: сохранено ${state.settings.lmStudio.host || "127.0.0.1"}:${state.settings.lmStudio.port}`;
    }
    toast("Параметры LM Studio применены в макете", { kind: "ok" });
  });
}

/* ─── Estimate — только время ────────────────────────── */
function refreshEstimate() {
  const baseTok = 250;
  const perQ    = state.settings.explanations ? 220 : 140;
  const ragMul  = state.settings.rag || state.settings.generationMode === "rag" ? 1.4 : 1.0;
  const tempMul = state.settings.temperature > 0.6 ? 1.08 : 1.0;
  const tokens  = Math.round((baseTok + state.settings.count * perQ) * ragMul * tempMul);
  const speed   = state.settings.model === "gpt-4o-mini" ? 95 : 38;
  const secs    = Math.max(8, Math.round(tokens / speed));
  $("#est-time").textContent = secs < 60 ? `~ ${secs} сек` : `~ ${Math.round(secs / 60)} мин ${secs % 60} сек`;
}

function refreshGenerateAvailability() {
  const s = state.source;
  const ok = !!s.file || (s.text?.trim().length ?? 0) >= 80;
  $("#generate-btn").disabled = !ok;
}

/* ─── Generation flow ────────────────────────────────── */
function setupGeneration() {
  $("#generate-btn").addEventListener("click", () => startGeneration());
  $("#cancel-btn").addEventListener("click", () => {
    state.generation.controller?.abort();
    toast("Генерация отменена", { kind: "warn" });
    showSection("workbench");
  });
  $("#back-btn").addEventListener("click", () => { showSection("workbench"); setActiveNav("create"); });
}

function showSection(name) {
  for (const id of ["workbench", "status", "result"]) {
    $(`#${id}`).hidden = id !== name;
  }
  if (name === "status" || name === "result") $("#hero").style.display = "none";
  else $("#hero").style.display = "";
}

function logLine(text, kind = "") {
  const log = $("#journal-log");
  const time = new Date().toLocaleTimeString("ru", { hour12: false });
  const line = el("div", {},
    el("span", { class: "log-time" }, `[${time}] `),
    el("span", { class: kind ? `log-${kind}` : "" }, text),
  );
  log.append(line);
  log.scrollTop = log.scrollHeight;
  $("#journal-count").textContent = `${log.children.length} строк`;
}

async function startGeneration() {
  if (state.generation.running) return;
  state.generation.running = true;
  state.generation.startedAt = performance.now();
  state.generation.controller = new AbortController();

  showSection("status");

  const requestId = crypto.randomUUID();
  $("#last-request-id") && ($("#last-request-id").textContent = requestId);
  $("#last-document-id") && ($("#last-document-id").textContent = state.source.file ? `file:${state.source.file.name}` : "paste:local");
  $("#last-quiz-id") && ($("#last-quiz-id").textContent = "ожидаем результат");

  $("#progress-fill").style.width = "0%";
  $("#progress-pct").textContent = "0%";
  $("#status-elapsed").textContent = "0:00";
  $("#status-eta").textContent = `~ ${$("#est-time").textContent.replace("~ ", "")} осталось`;
  $("#status-questions").textContent = `0 / ${state.settings.count} вопросов`;
  $("#journal-log").innerHTML = "";
  $("#stream").innerHTML = "";
  $$(".stage").forEach(s => { s.classList.remove("is-active", "is-done"); });
  logLine("Принят запрос на генерацию", "tag");

  const elapsedTimer = setInterval(() => {
    const sec = Math.floor((performance.now() - state.generation.startedAt) / 1000);
    $("#status-elapsed").textContent = `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
  }, 250);

  try {
    const quiz = await mockGenerate({
      source:   state.source,
      settings: { ...state.settings, types: Array.from(state.settings.types) },
      signal:   state.generation.controller.signal,
      onStage:  (stage, pct) => {
        const order = ["upload", "parse", "chunk", "model", "assemble"];
        const idx = order.indexOf(stage);
        order.forEach((s, i) => {
          const node = $(`.stage[data-stage="${s}"]`);
          if (!node) return;
          node.classList.toggle("is-active", i === idx);
          node.classList.toggle("is-done", i < idx);
        });
        $("#progress-fill").style.width = `${pct}%`;
        $("#progress-pct").textContent = `${pct}%`;
      },
      onLog: (msg, kind) => logLine(msg, kind),
      onQuestion: (q, i, total) => {
        $("#status-questions").textContent = `${i + 1} / ${total} вопросов`;
        const skel = $$(".stream-card.is-loading")[0];
        if (skel) { skel.classList.remove("is-loading"); skel.replaceWith(renderQuestionPreview(q, i)); }
        else $("#stream").append(renderQuestionPreview(q, i));
        if (i + 1 < total) $("#stream").append(renderSkeletonCard());
      },
      onStart: (total) => {
        $("#status-questions").textContent = `0 / ${total} вопросов`;
        for (let i = 0; i < Math.min(2, total); i++) $("#stream").append(renderSkeletonCard());
      },
    });

    $$(".stage").forEach(s => s.classList.add("is-done"));
    $("#progress-fill").style.width = "100%";
    $("#progress-pct").textContent = "100%";
    logLine(`Квиз готов: ${quiz.questions.length} вопросов`, "ok");

    quiz.version = 1;
    quiz.last_edited_at = new Date().toISOString();
    quiz.questions.forEach(prepareQuestionOrigin);

    state.quiz = quiz;
    $("#last-quiz-id") && ($("#last-quiz-id").textContent = quiz.id);
    pushHistory(quiz);
    renderResult();
    showSection("result");
    toast("Квиз готов 🎉", { kind: "ok" });
  } catch (err) {
    if (err.name !== "AbortError") {
      logLine(`Ошибка: ${err.message}`, "warn");
      toast(`Ошибка генерации: ${err.message}`, { kind: "bad" });
    }
  } finally {
    clearInterval(elapsedTimer);
    state.generation.running = false;
    state.generation.controller = null;
  }
}

function renderSkeletonCard() {
  return el("div", { class: "stream-card is-loading" },
    el("div", { class: "skel skel-title" }),
    el("div", { class: "skel skel-line" }),
    el("div", { class: "skel skel-line" }),
    el("div", { class: "skel skel-line" }),
  );
}

function renderQuestionPreview(q, i) {
  return el("div", { class: "stream-card" },
    el("div", { class: "q-head" },
      el("span", { class: "q-num" }, String(i + 1)),
      el("span", { class: "q-type-pill" }, typeName(q.type)),
    ),
    el("div", { class: "q-text", style: "margin: 0; padding: 0; font-size: 1rem;" }, q.text),
  );
}

/* ─── Result / editor ────────────────────────────────── */
function pushUndo() {
  if (!state.quiz) return;
  state.undoStack.push(JSON.stringify(state.quiz));
  if (state.undoStack.length > 50) state.undoStack.shift();
  $("#undo-btn").disabled = false;
}

function setupResult() {
  $("#quiz-title").addEventListener("input", (e) => { state.quiz.title = e.target.value; markEdited(); });
  $("#quiz-title").addEventListener("focus", pushUndo);

  $("#undo-btn").addEventListener("click", () => {
    const prev = state.undoStack.pop();
    if (!prev) return;
    state.quiz = JSON.parse(prev);
    renderResult();
    $("#undo-btn").disabled = state.undoStack.length === 0;
  });

  $("#save-btn").addEventListener("click", () => {
    if (!state.quiz) return;
    state.quiz.version = (state.quiz.version || 1) + (state.quiz.questions.some(q => q._dirty) ? 1 : 0);
    state.quiz.last_edited_at = new Date().toISOString();
    // принимаем все правки — обновляем origin
    state.quiz.questions.forEach(prepareQuestionOrigin);
    pushHistory(state.quiz);
    renderResult();
    toast("Изменения сохранены", { kind: "ok" });
  });

  $("#export-btn").addEventListener("click", openExport);
  $("#preview-btn").addEventListener("click", openPreview);
  $("#regen-all-btn").addEventListener("click", () => startGeneration());
  $("#quiz-editor-loader")?.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!state.quiz) {
      toast("В макете пока нет сгенерированного квиза", { kind: "warn" });
      return;
    }
    renderResult();
    toast("Квиз загружен в редактор", { kind: "ok" });
  });
  $("#save-quiz-button")?.addEventListener("click", () => $("#save-btn").click());
  $$("[data-quick-export]").forEach((button) => {
    button.addEventListener("click", () => {
      state.exportFormat = button.dataset.quickExport;
      $$("#export-formats .export-fmt").forEach(x => x.classList.toggle("is-on", x.dataset.fmt === state.exportFormat));
      openExport();
    });
  });

  $("#add-question-btn").addEventListener("click", (event) => {
    event.stopPropagation();
    toggleAddQuestionMenu();
  });

  document.addEventListener("click", closeTypeMenus);
}

function typeName(t) { return TYPE_LABELS[t] || t; }

function renderTypeMenu(currentType, onPick, extraClass = "") {
  return el("div", { class: `type-menu ${extraClass}`.trim(), role: "menu" },
    ...TYPE_ORDER.map(type => el("button", {
      class: "type-menu-item" + (type === currentType ? " is-active" : ""),
      type: "button",
      role: "menuitem",
      onclick: (event) => {
        event.stopPropagation();
        closeTypeMenus();
        onPick(type);
      },
    },
      el("span", { class: "type-menu-dot", "aria-hidden": "true" }),
      el("span", {}, typeName(type)),
    )),
  );
}

function renderQuestionTypePicker(q) {
  const picker = el("div", { class: "q-type-picker" },
    el("button", {
      class: "q-type-pill q-type-button",
      type: "button",
      "aria-haspopup": "menu",
      onclick: (event) => {
        event.stopPropagation();
        closeTypeMenus(picker);
        picker.classList.toggle("is-open");
      },
    }, typeName(q.type), el("span", { class: "q-type-caret", "aria-hidden": "true" }, "⌄")),
    renderTypeMenu(q.type, type => changeQuestionType(q, type)),
  );
  return picker;
}

function closeTypeMenus(except = null) {
  $$(".q-type-picker.is-open, .result-foot.is-type-menu-open").forEach(node => {
    if (node !== except) node.classList.remove(node.classList.contains("result-foot") ? "is-type-menu-open" : "is-open");
  });
}

function toggleAddQuestionMenu() {
  const foot = $(".result-foot");
  if (!foot) return;
  let menu = foot.querySelector(".add-question-menu");
  if (!menu) {
    menu = renderTypeMenu(null, type => addQuestion(type), "add-question-menu");
    foot.append(menu);
  }
  const willOpen = !foot.classList.contains("is-type-menu-open");
  closeTypeMenus();
  foot.classList.toggle("is-type-menu-open", willOpen);
}

function defaultOptionsForType(type) {
  if (type === "true_false") {
    return [
      { id: "a", text: "Истина", correct: true },
      { id: "b", text: "Ложь", correct: false },
    ];
  }
  if (type === "fill_blank") {
    return [{ id: "a", text: "Правильный ответ", correct: true }];
  }
  if (type === "short_answer") {
    return [{ id: "a", text: "Краткий ответ", correct: true }];
  }
  if (type === "matching") {
    return [];
  }
  return ["a", "b", "c", "d"].map((id, index) => ({
    id,
    text: `Вариант ${index + 1}`,
    correct: index === 0,
  }));
}

function defaultPairsForMatching() {
  return [
    { id: crypto.randomUUID(), left: "Событийная модель", right: "Реакция на внешние действия" },
    { id: crypto.randomUUID(), left: "Потоковая модель", right: "Непрерывная обработка данных" },
    { id: crypto.randomUUID(), left: "Кэширование", right: "Повторное использование результата" },
    { id: crypto.randomUUID(), left: "API", right: "Контракт взаимодействия" },
  ];
}

function createQuestion(type) {
  const text = type === "fill_blank"
    ? "Новый вопрос с пропуском _____"
    : "Новый вопрос — отредактируйте его";
  const q = {
    id: crypto.randomUUID(),
    type,
    text,
    options: defaultOptionsForType(type),
    ...(type === "matching" ? { pairs: defaultPairsForMatching() } : {}),
    explanation: "",
  };
  q._origin = questionSnapshot(q);
  q._dirty = true;
  return q;
}

function addQuestion(type) {
  pushUndo();
  state.quiz.questions.push(createQuestion(type));
  markEdited();
  renderResult();
}

function changeQuestionType(q, type) {
  if (q.type === type || state.regenerating.has(q.id)) return;
  pushUndo();
  q.type = type;
  q.options = defaultOptionsForType(type);
  if (type === "matching") {
    q.pairs = defaultPairsForMatching();
  } else {
    delete q.pairs;
  }
  if (type === "fill_blank" && !q.text.includes("_____")) q.text = `${q.text} _____`;
  q._dirty = true;
  markEdited();
  renderResult();
}

function markEdited() {
  if (!state.quiz) return;
  state.quiz.last_edited_at = new Date().toISOString();
  $("#quiz-edited-pill").textContent = "несохранённые правки";
  $("#quiz-edited-pill").classList.add("meta-pill-dirty");
}

function questionSnapshot(q) {
  return JSON.stringify({ type: q.type, text: q.text, options: q.options, pairs: q.pairs, explanation: q.explanation });
}

function prepareQuestionOrigin(q) {
  if (q.type === "matching") ensureMatchingShape(q);
  q._origin = questionSnapshot(q);
  q._dirty = false;
}

function isQuestionDirty(q) {
  if (!q._origin) return false;
  return questionSnapshot(q) !== q._origin;
}

function renderResult() {
  const root = $("#questions");
  root.innerHTML = "";
  const q = state.quiz;
  if (!q) return;
  $("#quiz-title").value = q.title;
  $("#quiz-id-pill").textContent = `id: ${q.id.slice(0, 8)}`;
  $("#quiz-version-pill").textContent = `версия ${q.version || 1}`;
  $("#quiz-count-pill").textContent = `${q.questions.length} вопросов`;
  const edited = q.last_edited_at ? new Date(q.last_edited_at) : null;
  $("#quiz-edited-pill").textContent = edited ? `обновлено ${relTime(edited)}` : "обновлено только что";
  $("#quiz-edited-pill").classList.remove("meta-pill-dirty");
  setText("#result-state-badge", "Квиз готов к редактированию");
  setText("#result-status", "Проверьте вопросы, поправьте формулировки и выберите формат экспорта.");
  setText("#quiz-question-count", String(q.questions.length));
  const generationModeLabels = { auto: "Авто", direct: "Прямой", rag: "RAG" };
  setText("#quiz-generation-mode", generationModeLabels[state.settings.generationMode] || "Авто");
  setText("#quiz-model-name", state.settings.model);
  setText("#quiz-prompt-version", "registry:v2");
  setText("#editor-quiz-id", q.id);
  setText("#editor-document-id", state.source.file ? `file:${state.source.file.name}` : "paste:local");
  setText("#editor-quiz-version", `версия ${q.version || 1}`);
  setText("#editor-last-edited", edited ? edited.toLocaleString("ru") : "только что");
  setText("#quiz-editor-status", "Квиз загружен в визуальный редактор макета.");
  const quizIdInput = $("#quiz-id-input");
  if (quizIdInput) quizIdInput.value = q.id;

  q.questions.forEach((qq, i) => root.append(renderQuestionCard(qq, i)));
}

function relTime(date) {
  const s = Math.round((Date.now() - date.getTime()) / 1000);
  if (s < 60) return "только что";
  if (s < 3600) return `${Math.round(s / 60)} мин назад`;
  if (s < 86400) return `${Math.round(s / 3600)} ч назад`;
  return date.toLocaleString("ru");
}

function renderQuestionCard(q, i) {
  if (q.type === "matching") ensureMatchingShape(q);
  const isRegenerating = state.regenerating.has(q.id);
  const card = el("div", { class: "q-card" + (q._dirty ? " is-dirty" : "") + (isRegenerating ? " is-regenerating" : ""), "data-id": q.id });

  const moveControls = el("div", { class: "q-move-controls", "aria-label": "Порядок вопроса" },
    iconBtn("Переместить вверх", "", () => moveQuestion(q, -1), "q-act-move q-act-up", i === 0 || isRegenerating),
    iconBtn("Переместить вниз", "", () => moveQuestion(q, 1), "q-act-move q-act-down", i === state.quiz.questions.length - 1 || isRegenerating),
  );

  const head = el("div", { class: "q-head" },
    el("span", { class: "q-num" }, String(i + 1)),
    renderQuestionTypePicker(q),
    q._dirty ? el("span", { class: "q-edited-badge" }, "изменён") : null,
    el("div", { class: "q-actions" },
      isRegenerating
        ? iconBtn("Отменить перегенерацию", "", () => cancelRegenerate(q), "q-act-stop")
        : iconBtn("Перегенерировать", "M21 12a9 9 0 0 1-15 6.7L3 16 M3 21v-5h5 M3 12a9 9 0 0 1 15-6.7L21 8 M21 3v5h-5", () => regenerateOne(q), "q-act-regen"),
      iconBtn("Откатить к исходному", "M3 12a9 9 0 0 0 9 9 9 9 0 0 0 9-9 M3 12V8 M3 12h4", () => revertOne(q), "q-act-revert", !q._dirty || isRegenerating),
      iconBtn("Дублировать",      "M16 3H4a1 1 0 0 0-1 1v12 M9 7h11a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z", () => duplicate(q), "q-act-copy", isRegenerating),
      iconBtn("Удалить",          "M3 6h18 M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2 M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6", () => removeQ(q), "q-act-danger", isRegenerating),
    ),
  );

  const text = el("div", { class: "q-text", contenteditable: "true", spellcheck: "true" }, q.text);
  text.addEventListener("focus", pushUndo);
  text.addEventListener("input", () => { q.text = text.textContent; onQuestionEdited(q, card); });

  const opts = q.type === "matching" ? renderMatchingEditor(q, card) : renderOptionsEditor(q, card);

  card.append(head, moveControls, text, opts);
  const expl = renderExplanation(q, card);
  if (expl) card.append(expl);
  return card;
}

function renderExplanation(q, card) {

  const hasExpl = (typeof q.explanation === "string" && q.explanation.trim() !== "") || q._addingExpl;

  // нет пояснения → кнопка «добавить»
  if (!hasExpl) {
    return el("div", { class: "q-expl-tools" },
      el("button", {
        class: "q-expl-add",
        type: "button",
        onclick: () => {
          pushUndo();
          q._addingExpl = true;
          renderResult();
          $(`.q-card[data-id="${q.id}"] .q-expl-text`)?.focus();
        },
      }, "+ Добавить пояснение"),
    );
  }

  // есть пояснение → редактируемый блок с кнопкой удаления
  const explText = el("span", {
    class: "q-expl-text",
    contenteditable: "true",
    spellcheck: "true",
    oninput: (ev) => { q.explanation = ev.target.textContent; onQuestionEdited(q, card); },
  }, q.explanation || "");
  explText.addEventListener("focus", pushUndo);

  const remove = el("button", {
    class: "q-expl-remove",
    type: "button",
    "aria-label": "Удалить пояснение",
    title: "Удалить пояснение",
    onclick: (event) => {
      event.stopPropagation();
      pushUndo();
      q.explanation = "";
      delete q._addingExpl;
      onQuestionEdited(q, card);
      renderResult();
    },
  });

  return el("div", { class: "q-expl q-expl-editable" },
    el("div", { class: "q-expl-head" },
      el("span", { class: "q-expl-label" }, "Пояснение"),
      remove,
    ),
    explText,
  );
}

function renderOptionsEditor(q, card) {
  const opts = el("div", { class: "q-options" });
  q.options.forEach((opt) => {
    const o = el("div", { class: "q-opt" + (opt.correct ? " is-correct" : "") });
    const mark = el("span", { class: "q-opt-mark" }, opt.correct ? "✓" : opt.id.toUpperCase());
    const t = el("div", { class: "q-opt-text", contenteditable: "true", spellcheck: "true" }, opt.text);
    t.addEventListener("focus", pushUndo);
    t.addEventListener("input", () => { opt.text = t.textContent; onQuestionEdited(q, card); });
    const x = el("button", { class: "q-opt-remove", title: "Удалить вариант",
      onclick: (e) => { e.stopPropagation(); pushUndo(); q.options = q.options.filter(o => o.id !== opt.id); onQuestionEdited(q, card); renderResult(); } },
      "×",
    );
    o.addEventListener("click", (ev) => {
      if (ev.target.closest(".q-opt-text, .q-opt-remove")) return;
      pushUndo();
      if (q.type === "single_choice" || q.type === "true_false") {
        q.options.forEach(x => x.correct = false);
        opt.correct = true;
      } else {
        opt.correct = !opt.correct;
      }
      onQuestionEdited(q, card);
      renderResult();
    });
    o.append(mark, t, x);
    opts.append(o);
  });

  const add = el("button", { class: "q-opt-add",
    onclick: () => { pushUndo();
      const next = String.fromCharCode(97 + q.options.length);
      q.options.push({ id: next, text: "Новый вариант", correct: false });
      onQuestionEdited(q, card);
      renderResult();
    } }, "+ добавить вариант");
  opts.append(add);
  return opts;
}

function ensureMatchingShape(q) {
  if (!Array.isArray(q.pairs) || !q.pairs.length) {
    q.pairs = Array.isArray(q.options) && q.options.length
      ? q.options.map((option, index) => {
          const parts = String(option.text || "").split("↔").map(x => x.trim());
          return {
            id: option.id || crypto.randomUUID(),
            left: parts[0] || `Элемент ${index + 1}`,
            right: parts[1] || option.text || `Соответствие ${index + 1}`,
          };
        })
      : defaultPairsForMatching();
  }
  Reflect.deleteProperty(q, "distractors");
  q.options = [];
}

function renderMatchingEditor(q, card) {
  ensureMatchingShape(q);
  const rows = el("div", { class: "q-match-rows" });
  q.pairs.forEach((pair, index) => {
    const left = el("span", { class: "q-match-text", contenteditable: "true", spellcheck: "true", role: "textbox" }, pair.left);
    const right = el("span", { class: "q-match-text", contenteditable: "true", spellcheck: "true", role: "textbox" }, pair.right);
    left.addEventListener("focus", pushUndo);
    right.addEventListener("focus", pushUndo);
    left.addEventListener("input", () => { pair.left = left.textContent; onQuestionEdited(q, card); });
    right.addEventListener("input", () => { pair.right = right.textContent; onQuestionEdited(q, card); });
    rows.append(el("div", { class: "q-match-row", "data-pair-id": pair.id },
      el("div", { class: "q-match-cell q-match-left" },
        el("span", { class: "q-match-badge" }, String(index + 1)),
        left,
      ),
      el("span", { class: "q-match-link", "aria-hidden": "true" }, "↔"),
      el("div", { class: "q-match-cell q-match-right" },
        el("span", { class: "q-match-badge q-match-badge-alt" }, String.fromCharCode(65 + index)),
        right,
      ),
      el("button", {
        class: "q-match-remove",
        type: "button",
        "aria-label": "Удалить пару",
        onclick: (event) => {
          event.stopPropagation();
          pushUndo();
          q.pairs = q.pairs.filter(x => x.id !== pair.id);
          onQuestionEdited(q, card);
          renderResult();
        },
      }),
    ));
  });

  return el("div", { class: "q-matching" },
    el("div", { class: "q-match-grid-head", "aria-hidden": "true" },
      el("span", {}, "Левая часть"),
      el("span", {}),
      el("span", {}, "Правая часть"),
      el("span", {}),
    ),
    rows,
    el("div", { class: "q-match-tools" },
      el("button", {
        class: "q-match-add",
        type: "button",
        onclick: () => {
          pushUndo();
          q.pairs.push({ id: crypto.randomUUID(), left: "Новый элемент", right: "Новое соответствие" });
          onQuestionEdited(q, card);
          renderResult();
        },
      }, "+ Добавить пару"),
    ),
  );
}

function onQuestionEdited(q, card) {
  q._dirty = isQuestionDirty(q);
  card.classList.toggle("is-dirty", q._dirty);
  markEdited();
  // обновим бейдж "изменён" без полного рендера
  const head = card.querySelector(".q-head");
  let badge = head.querySelector(".q-edited-badge");
  if (q._dirty && !badge) {
    badge = el("span", { class: "q-edited-badge" }, "изменён");
    head.insertBefore(badge, head.querySelector(".q-actions"));
  } else if (!q._dirty && badge) {
    badge.remove();
  }
  // активируем кнопку revert
  const revertBtn = head.querySelector(".q-act-revert");
  if (revertBtn) revertBtn.disabled = !q._dirty;
}

function iconBtn(title, d, onClick, cls = "", disabled = false) {
  const symbol = cls.includes("q-act-up") ? "↑"
    : cls.includes("q-act-down") ? "↓"
    : cls.includes("q-act-stop") ? "■"
    : cls.includes("q-act-regen") ? "↻"
    : cls.includes("q-act-revert") ? "↶"
    : cls.includes("q-act-copy") ? "⧉"
    : cls.includes("q-act-danger") ? "×"
    : "•";
  const btn = el("button", { class: `q-act ${cls}`, title, "aria-label": title, onclick: onClick, ...(disabled ? { disabled: true } : {}) },
    symbol,
  );
  return btn;
}

async function regenerateOne(q) {
  if (state.regenerating.has(q.id)) {
    cancelRegenerate(q);
    return;
  }
  toast("Перегенерируем вопрос…");
  pushUndo();
  const controller = new AbortController();
  state.regenerating.set(q.id, controller);
  renderResult();
  try {
    const fresh = await mockRegenerateQuestion({ q, settings: state.settings, signal: controller.signal });
    delete q.pairs;
    Object.assign(q, fresh, { id: q.id });
    prepareQuestionOrigin(q);
    state.regenerating.delete(q.id);
    renderResult();
    const fresh_card = $(`.q-card[data-id="${q.id}"]`);
    fresh_card?.classList.add("is-fresh");
    setTimeout(() => fresh_card?.classList.remove("is-fresh"), 1500);
    toast("Готово", { kind: "ok" });
  } catch (e) {
    state.regenerating.delete(q.id);
    renderResult();
    if (e?.name === "AbortError") {
      toast("Перегенерация отменена");
      return;
    }
    toast("Не удалось перегенерировать", { kind: "bad" });
  }
}

function cancelRegenerate(q) {
  const controller = state.regenerating.get(q.id);
  controller?.abort();
}

function revertOne(q) {
  if (!q._origin) return;
  pushUndo();
  const origin = JSON.parse(q._origin);
  q.type = origin.type;
  q.text = origin.text;
  q.options = origin.options || [];
  if (origin.pairs) q.pairs = origin.pairs;
  else delete q.pairs;
  Reflect.deleteProperty(q, "distractors");
  q.explanation = origin.explanation;
  delete q._addingExpl;
  q._dirty = false;
  renderResult();
  toast("Вопрос откатан к исходному", { kind: "ok" });
}

function duplicate(q) {
  pushUndo();
  const copy = JSON.parse(JSON.stringify(q));
  copy.id = crypto.randomUUID();
  copy._dirty = true;
  const idx = state.quiz.questions.findIndex(x => x.id === q.id);
  state.quiz.questions.splice(idx + 1, 0, copy);
  markEdited();
  renderResult();
}

function moveQuestion(q, direction) {
  const idx = state.quiz.questions.findIndex(x => x.id === q.id);
  const next = idx + direction;
  if (idx < 0 || next < 0 || next >= state.quiz.questions.length) return;
  pushUndo();
  const [item] = state.quiz.questions.splice(idx, 1);
  state.quiz.questions.splice(next, 0, item);
  markEdited();
  renderResult();
  const moved = $(`.q-card[data-id="${q.id}"]`);
  moved?.classList.add("is-fresh");
  moved?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  setTimeout(() => moved?.classList.remove("is-fresh"), 900);
}

function removeQ(q) {
  pushUndo();
  state.quiz.questions = state.quiz.questions.filter(x => x.id !== q.id);
  markEdited();
  renderResult();
}

/* ─── History ────────────────────────────────────────── */
function pushHistory(quiz) {
  const stripped = {
    id:        quiz.id,
    title:     quiz.title,
    createdAt: quiz.createdAt,
    count:     quiz.questions.length,
    version:   quiz.version || 1,
  };
  state.history = [stripped, ...state.history.filter(x => x.id !== quiz.id)].slice(0, 20);
  localStorage.setItem("qc.history", JSON.stringify(state.history));
  // origin исключаем из сохранения чтобы не раздувать
  const slim = { ...quiz, questions: quiz.questions.map(q => { const { _origin, _dirty, _addingExpl, ...rest } = q; return rest; }) };
  localStorage.setItem(`qc.quiz.${quiz.id}`, JSON.stringify(slim));
  renderSidebarHistory();
}

function loadHistory() {
  try { state.history = JSON.parse(localStorage.getItem("qc.history") || "[]"); } catch { state.history = []; }
  renderSidebarHistory();
}

function renderSidebarHistory() {
  const list = $("#sidebar-history-list");
  const empty = $("#sidebar-history-empty");
  const cnt = $("#nav-history-count");
  list.innerHTML = "";
  if (!state.history.length) {
    empty.hidden = false;
    if (cnt) cnt.hidden = true;
    return;
  }
  empty.hidden = true;
  if (cnt) {
    cnt.hidden = false;
    cnt.textContent = String(state.history.length);
  }

  // группируем по дате
  const groups = { today: [], yesterday: [], older: [] };
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfYesterday = startOfToday - 86400000;
  state.history.forEach(h => {
    const t = new Date(h.createdAt).getTime();
    if (t >= startOfToday) groups.today.push(h);
    else if (t >= startOfYesterday) groups.yesterday.push(h);
    else groups.older.push(h);
  });

  const groupLabels = { today: "Сегодня", yesterday: "Вчера", older: "Раньше" };
  for (const key of ["today", "yesterday", "older"]) {
    if (!groups[key].length) continue;
    list.append(el("div", { class: "sidebar-history-group" }, groupLabels[key]));
    groups[key].forEach(h => {
      const active = state.quiz?.id === h.id;
      const item = el("button", { class: "sidebar-history-item" + (active ? " is-active" : ""),
        onclick: () => {
          const data = JSON.parse(localStorage.getItem(`qc.quiz.${h.id}`) || "null");
          if (data) {
            data.questions.forEach(prepareQuestionOrigin);
            state.quiz = data;
            renderResult();
            showSection("result");
            renderSidebarHistory();
            document.body.dataset.sidebarOpen = "false";
          }
        } },
        el("span", { class: "sidebar-history-title" }, h.title || "Безымянный квиз"),
        el("span", { class: "sidebar-history-sub" }, `${h.count} вопр. · v${h.version ?? 1}`),
      );
      list.append(item);
    });
  }
}

/* ─── Modal helpers ──────────────────────────────────── */
function openModal(id) {
  const m = $(`#${id}`);
  m.hidden = false;
  m.addEventListener("click", onModalClick);
  document.addEventListener("keydown", onModalEsc);
}
function closeModal(m) {
  m.hidden = true;
  m.removeEventListener("click", onModalClick);
  document.removeEventListener("keydown", onModalEsc);
}
function onModalClick(e) {
  if (e.target.closest("[data-close]")) closeModal(e.currentTarget);
}
function onModalEsc(e) {
  if (e.key === "Escape") $$(".modal:not([hidden])").forEach(closeModal);
}

/* ─── Status pill ────────────────────────────────────── */
function setupStatusPill() {
  $("#status-pill").addEventListener("click", () => openModal("modal-status"));
}

function setupVisualControls() {
  $("#retry-backend-button")?.addEventListener("click", (event) => {
    event.stopPropagation();
    setText("#backend-status-text", "готов");
    toast("Макет: сервер отвечает", { kind: "ok" });
  });
  $("#retry-provider-button")?.addEventListener("click", (event) => {
    event.stopPropagation();
    setText("#provider-status-text", "LM Studio");
    toast("Макет: провайдер доступен", { kind: "ok" });
  });
  $$("[data-check-service]").forEach((button) => {
    button.addEventListener("click", () => toast(`Макет: ${button.dataset.checkService === "backend" ? "сервер" : "провайдер"} проверен`, { kind: "ok" }));
  });
  $$(".copy-button[data-copy-for]").forEach((button) => {
    button.addEventListener("click", async () => {
      const value = $(`#${button.dataset.copyFor}`)?.textContent?.trim() || "";
      if (!value) return;
      try {
        await navigator.clipboard.writeText(value);
        toast("Скопировано", { kind: "ok" });
      } catch {
        toast("Визуальная кнопка копирования", { kind: "warn" });
      }
    });
  });
}

/* ─── Export modal ───────────────────────────────────── */
function setupExport() {
  $$("#export-formats .export-fmt").forEach(b => b.addEventListener("click", () => {
    $$("#export-formats .export-fmt").forEach(x => x.classList.toggle("is-on", x === b));
    state.exportFormat = b.dataset.fmt;
    refreshExportPreview();
  }));
  $$("#modal-export .toggle input").forEach(i => i.addEventListener("change", refreshExportPreview));
  $("#export-do-copy").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("#export-preview-body").textContent);
    toast("Скопировано в буфер", { kind: "ok" });
  });
  $("#export-do-download").addEventListener("click", () => {
    const text = $("#export-preview-body").textContent;
    const ext  = { json: "json", md: "md", docx: "doc", pptx: "ppt", csv: "csv" }[state.exportFormat] || "txt";
    const mime = { json: "application/json", md: "text/markdown", docx: "application/msword", pptx: "application/vnd.ms-powerpoint", csv: "text/csv" }[state.exportFormat] || "text/plain";
    const blob = new Blob([text], { type: mime });
    const u = URL.createObjectURL(blob);
    const a = el("a", { href: u, download: `${(state.quiz?.title || "quiz").replace(/\s+/g, "-")}.${ext}` });
    document.body.append(a); a.click(); a.remove(); URL.revokeObjectURL(u);
  });
}

function openExport() {
  if (!state.quiz) return;
  refreshExportPreview();
  openModal("modal-export");
}

function refreshExportPreview() {
  if (!state.quiz) return;
  const opts = {
    answers: $("#opt-answers").checked,
    expl:    $("#opt-expl").checked,
    diff:    $("#opt-diff").checked,
    shuffle: $("#opt-shuffle").checked,
  };
  const text = serializeQuiz(state.quiz, state.exportFormat, opts);
  $("#export-preview-body").textContent = text;
  $("#export-size").textContent = `~ ${Math.max(1, Math.round(new Blob([text]).size / 1024))} КБ`;
}

function serializeQuiz(quiz, fmt, opts) {
  const qs = quiz.questions.map(q => {
    if (q.type === "matching") {
      ensureMatchingShape(q);
      return { ...q, pairs: q.pairs.slice() };
    }
    return opts.shuffle ? { ...q, options: shuffle(q.options) } : q;
  });

  if (fmt === "json") {
    const data = {
      id: quiz.id, title: quiz.title, version: quiz.version || 1,
      createdAt: quiz.createdAt, last_edited_at: quiz.last_edited_at,
      questions: qs.map(q => ({
        id: q.id, type: q.type, text: q.text,
        ...(q.type === "matching"
          ? { pairs: q.pairs.map(p => ({ id: p.id, left: p.left, right: p.right })) }
          : { options: q.options.map(o => ({ id: o.id, text: o.text, ...(opts.answers ? { correct: o.correct } : {}) })) }),
        ...(opts.expl && q.explanation ? { explanation: q.explanation } : {}),
        ...(opts.diff ? { difficulty: q.difficulty || "mixed" } : {}),
      })),
    };
    return JSON.stringify(data, null, 2);
  }

  if (fmt === "md") {
    let out = `# ${quiz.title}\n\n`;
    qs.forEach((q, i) => {
      out += `## ${i + 1}. ${q.text}\n\n`;
      if (q.type === "matching") {
        q.pairs.forEach((p, j) => { out += `- ${j + 1}. ${p.left} ↔ ${String.fromCharCode(65 + j)}. ${p.right}\n`; });
      } else {
        q.options.forEach((o) => {
          const mark = opts.answers && o.correct ? "**" : "";
          out += `- ${mark}${o.text}${mark}${opts.answers && o.correct ? "  ← правильный" : ""}\n`;
        });
      }
      if (opts.expl && q.explanation) out += `\n> ${q.explanation}\n`;
      if (opts.diff) out += `\n_сложность: ${q.difficulty || "mixed"}_\n`;
      out += "\n";
    });
    return out;
  }

  if (fmt === "csv") {
    const rows = [["question", "type", "option_1", "option_2", "option_3", "option_4", "correct_index", "matching_pairs", "explanation"]];
    qs.forEach(q => {
      const o = q.type === "matching" ? [] : q.options.map(x => x.text);
      const correctIndex = q.type === "matching" ? -1 : q.options.findIndex(x => x.correct);
      rows.push([
        csvCell(q.text), q.type, csvCell(o[0] || ""), csvCell(o[1] || ""), csvCell(o[2] || ""), csvCell(o[3] || ""),
        opts.answers && q.type !== "matching" ? String(correctIndex + 1) : "",
        q.type === "matching" ? csvCell(q.pairs.map(p => `${p.left} ↔ ${p.right}`).join("; ")) : "",
        opts.expl ? csvCell(q.explanation || "") : "",
      ]);
    });
    return rows.map(r => r.join(",")).join("\n");
  }

  if (fmt === "docx") {
    let out = `${quiz.title}\n${"=".repeat(quiz.title.length)}\n\n`;
    qs.forEach((q, i) => {
      out += `${i + 1}. ${q.text}\n`;
      if (q.type === "matching") {
        q.pairs.forEach((p, j) => { out += `   ${j + 1}) ${p.left} ↔ ${String.fromCharCode(65 + j)}) ${p.right}\n`; });
      } else {
        q.options.forEach((o, j) => { out += `   ${"abcd"[j]}) ${o.text}${opts.answers && o.correct ? " ✓" : ""}\n`; });
      }
      if (opts.expl && q.explanation) out += `   Пояснение: ${q.explanation}\n`;
      out += "\n";
    });
    return out;
  }

  if (fmt === "pptx") {
    let out = `${quiz.title}\n\n`;
    qs.forEach((q, i) => {
      out += `Слайд ${i + 1}: ${q.text}\n`;
      if (q.type === "matching") {
        q.pairs.forEach((p, j) => { out += `  ${j + 1}. ${p.left} ↔ ${String.fromCharCode(65 + j)}. ${p.right}\n`; });
      } else {
        q.options.forEach((o, j) => { out += `  ${j + 1}. ${o.text}${opts.answers && o.correct ? " ✓" : ""}\n`; });
      }
      if (opts.expl && q.explanation) out += `  Заметки: ${q.explanation}\n`;
      out += "\n";
    });
    return out;
  }

  return "";
}

function csvCell(s) { return `"${String(s).replace(/"/g, '""')}"`; }
function shuffle(arr) { const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

/* ─── Preview / play mode ────────────────────────────── */
function setupPreview() {
  $("#preview-prev").addEventListener("click", () => { previewState.idx = Math.max(0, previewState.idx - 1); renderPreview(); });
  $("#preview-next").addEventListener("click", () => {
    if (previewState.idx < state.quiz.questions.length - 1) { previewState.idx++; renderPreview(); }
    else closeModal($("#modal-preview"));
  });
}
const previewState = { idx: 0, picks: {} };
function openPreview() {
  if (!state.quiz) return;
  previewState.idx = 0; previewState.picks = {};
  renderPreview();
  openModal("modal-preview");
}
function renderPreview() {
  const q = state.quiz.questions[previewState.idx];
  const root = $("#preview-body"); root.innerHTML = "";
  root.append(el("div", { class: "play-q-text" }, `${previewState.idx + 1}. ${q.text}`));
  if (q.type === "matching") {
    renderMatchingPreview(q, root);
    $("#preview-progress").textContent = `Вопрос ${previewState.idx + 1} / ${state.quiz.questions.length}`;
    $("#preview-next").textContent = previewState.idx === state.quiz.questions.length - 1 ? "Завершить" : "Дальше →";
    return;
  }
  const pick = previewState.picks[q.id];
  q.options.forEach((o) => {
    let cls = "play-opt";
    if (pick) {
      if (o.correct) cls += " is-correct";
      else if (pick === o.id) cls += " is-wrong";
    } else if (pick === o.id) cls += " is-picked";
    const b = el("button", { class: cls,
      onclick: () => { previewState.picks[q.id] = o.id; renderPreview(); } },
      el("span", { class: "play-opt-mark" }, o.id.toUpperCase()),
      el("span", {}, o.text),
    );
    root.append(b);
  });
  if (pick && q.explanation) {
    root.append(el("div", { class: "q-expl" }, el("span", { class: "q-expl-label" }, "Пояснение"), q.explanation));
  }
  $("#preview-progress").textContent = `Вопрос ${previewState.idx + 1} / ${state.quiz.questions.length}`;
  $("#preview-next").textContent = previewState.idx === state.quiz.questions.length - 1 ? "Завершить" : "Дальше →";
}

function renderMatchingPreview(q, root) {
  ensureMatchingShape(q);
  const rightItems = shuffle(q.pairs.map((pair, index) => ({ id: pair.id, text: pair.right, pairIndex: index })));
  const letters = new Map(rightItems.map((item, index) => [item.id, String.fromCharCode(65 + index)]));
  const picks = previewState.picks[q.id] || {};
  const rows = el("div", { class: "play-match" });
  q.pairs.forEach((pair, index) => {
    const select = el("select", {
      class: "play-match-pick",
      onchange: (event) => {
        previewState.picks[q.id] = { ...picks, [pair.id]: event.target.value };
        renderPreview();
      },
    },
      el("option", { value: "" }, "—"),
      ...rightItems.map(item => el("option", { value: item.id, ...(picks[pair.id] === item.id ? { selected: true } : {}) }, letters.get(item.id))),
    );
    rows.append(el("div", { class: "play-match-row" },
      el("span", { class: "q-match-badge" }, String(index + 1)),
      el("span", { class: "play-match-left" }, pair.left),
      select,
    ));
  });
  root.append(rows);
  root.append(el("div", { class: "play-match-bank" },
    ...rightItems.map(item => el("div", { class: "play-match-bank-item" },
      el("span", { class: "q-match-badge q-match-badge-alt" }, letters.get(item.id)),
      el("span", {}, item.text),
    )),
  ));
  const answered = q.pairs.every(pair => picks[pair.id]);
  if (answered) {
    const ok = q.pairs.every(pair => picks[pair.id] === pair.id);
    root.append(el("div", { class: `q-expl ${ok ? "play-match-ok" : "play-match-bad"}` },
      el("span", { class: "q-expl-label" }, ok ? "Верно" : "Проверьте"),
      ok ? "Все пары сопоставлены правильно." : "Некоторые соответствия выбраны неверно.",
    ));
  }
  if (answered && q.explanation) {
    root.append(el("div", { class: "q-expl" }, el("span", { class: "q-expl-label" }, "Пояснение"), q.explanation));
  }
}

/* ─── Boot ───────────────────────────────────────────── */
loadDemoText();
preloadMockQuestions();
setupTheme();
setupSidebar();
setupTabs();
setupFileInput();
setupPasteMetrics();
setupSourceToolbar();
setupSettings();
setupGeneration();
setupResult();
setupStatusPill();
setupVisualControls();
setupExport();
setupPreview();
refreshEstimate();
loadHistory();
