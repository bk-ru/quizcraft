const AUTO_VALUE = "";

const PROFILE_LABELS = Object.freeze({
  fast: "Быстрый",
  balanced: "Сбалансированный",
  strict: "Строгий",
});

function humanizeProfile(name) {
  if (typeof name !== "string" || !name.trim()) {
    return "";
  }
  const lookup = PROFILE_LABELS[name];
  if (lookup) {
    return `${lookup} (${name})`;
  }
  return name;
}

function buildOption(documentRef, value, label) {
  const option = documentRef.createElement("option");
  option.value = value;
  option.textContent = label;
  return option;
}

export function createGenerationSettingsController({
  client,
  modelSelect,
  profileSelect,
  setLogMessage,
  documentRef = (typeof document !== "undefined" ? document : null),
} = {}) {
  const state = {
    defaultModel: null,
    defaultProfile: null,
    availableModels: [],
    availableProfiles: [],
    savedModel: null,
    savedProfile: null,
    loaded: false,
  };

  function populateModelSelect() {
    if (!modelSelect || !documentRef) {
      return;
    }
    const defaultLabel = state.defaultModel
      ? `Авто (${state.defaultModel})`
      : "Авто";
    const options = [buildOption(documentRef, AUTO_VALUE, defaultLabel)];
    for (const model of state.availableModels) {
      options.push(buildOption(documentRef, model, model));
    }
    modelSelect.replaceChildren(...options);
    modelSelect.value = state.savedModel && state.availableModels.includes(state.savedModel)
      ? state.savedModel
      : AUTO_VALUE;
    modelSelect.disabled = state.availableModels.length === 0;
  }

  function populateProfileSelect() {
    if (!profileSelect || !documentRef) {
      return;
    }
    const defaultLabel = state.defaultProfile
      ? `Авто (${humanizeProfile(state.defaultProfile)})`
      : "Авто";
    const options = [buildOption(documentRef, AUTO_VALUE, defaultLabel)];
    for (const profile of state.availableProfiles) {
      options.push(buildOption(documentRef, profile, humanizeProfile(profile)));
    }
    profileSelect.replaceChildren(...options);
    profileSelect.value = state.savedProfile && state.availableProfiles.includes(state.savedProfile)
      ? state.savedProfile
      : AUTO_VALUE;
    profileSelect.disabled = state.availableProfiles.length === 0;
  }

  async function loadSettings() {
    if (!client || typeof client.getGenerationSettings !== "function") {
      return state;
    }
    try {
      const response = await client.getGenerationSettings();
      state.availableModels = Array.isArray(response?.available_models)
        ? response.available_models.filter((value) => typeof value === "string" && value)
        : [];
      state.availableProfiles = Array.isArray(response?.available_profiles)
        ? response.available_profiles.filter((value) => typeof value === "string" && value)
        : [];
      state.defaultModel = typeof response?.default_model === "string" ? response.default_model : null;
      state.defaultProfile = typeof response?.default_profile === "string" ? response.default_profile : null;
      const saved = response?.settings ?? null;
      state.savedModel = typeof saved?.model_name === "string" ? saved.model_name : null;
      state.savedProfile = typeof saved?.profile_name === "string" ? saved.profile_name : null;
      state.loaded = true;
      populateModelSelect();
      populateProfileSelect();
    } catch (error) {
      state.loaded = false;
      if (typeof setLogMessage === "function") {
        const reason = error instanceof Error ? error.message : String(error);
        setLogMessage(`Не удалось загрузить справочник моделей и профилей: ${reason}`, "warn");
      }
    }
    return state;
  }

  function getGenerationOverrides() {
    const overrides = {};
    if (modelSelect && typeof modelSelect.value === "string" && modelSelect.value.trim()) {
      overrides.model_name = modelSelect.value.trim();
    }
    if (profileSelect && typeof profileSelect.value === "string" && profileSelect.value.trim()) {
      overrides.profile_name = profileSelect.value.trim();
    }
    return overrides;
  }

  return {
    loadSettings,
    getGenerationOverrides,
    populateModelSelect,
    populateProfileSelect,
  };
}

export const GENERATION_SETTINGS_AUTO_VALUE = AUTO_VALUE;
