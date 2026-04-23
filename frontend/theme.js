const THEME_STORAGE_KEY = "quizcraft.theme";
const THEME_ORDER = ["auto", "light", "dark"];
const THEME_LABELS = { auto: "Авто", light: "Светлая", dark: "Тёмная" };

export function createThemeController({ themeToggleLabel }, windowRef = window, documentRef = document) {
  function resolveStoredTheme() {
    try {
      const stored = windowRef.localStorage.getItem(THEME_STORAGE_KEY);
      if (stored && THEME_ORDER.includes(stored)) {
        return stored;
      }
    } catch (error) {
      return "auto";
    }
    return "auto";
  }

  function applyTheme(theme) {
    const next = THEME_ORDER.includes(theme) ? theme : "auto";
    documentRef.documentElement.setAttribute("data-theme", next);
    if (themeToggleLabel) {
      themeToggleLabel.textContent = THEME_LABELS[next];
    }
    try {
      windowRef.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch (error) {
      return;
    }
  }

  function cycleTheme() {
    const current = documentRef.documentElement.getAttribute("data-theme") ?? "auto";
    const index = THEME_ORDER.indexOf(current);
    const next = THEME_ORDER[(index + 1) % THEME_ORDER.length];
    applyTheme(next);
  }

  return { applyTheme, cycleTheme, resolveStoredTheme };
}
