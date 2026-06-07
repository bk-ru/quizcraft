const TIMING_KEY = "quizcraft:gen-timing";
const MAX_SAMPLES = 20;
const DEFAULT_MS_PER_CHAR = 8;

function readSamples(storage) {
  try {
    const raw = storage?.getItem(TIMING_KEY);
    if (typeof raw !== "string" || !raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_e) {
    return [];
  }
}

function writeSamples(storage, samples) {
  try {
    storage?.setItem(TIMING_KEY, JSON.stringify(samples));
  } catch (_e) {
    /* Локальное хранилище недоступно; деградируем без ошибки */
  }
}

export function createGenTiming(storage = (typeof window !== "undefined" ? window.localStorage : null)) {
  function estimateTotalMs(charCount) {
    if (charCount <= 0) {
      return null;
    }
    const samples = readSamples(storage);
    const msPerChar = samples.length > 0
      ? samples.reduce((sum, sample) => sum + sample.ms / sample.chars, 0) / samples.length
      : DEFAULT_MS_PER_CHAR;
    return Math.max(1000, msPerChar * charCount);
  }

  function record(charCount, elapsedMs) {
    if (charCount <= 0 || elapsedMs <= 0) {
      return;
    }
    const samples = readSamples(storage);
    samples.push({ chars: charCount, ms: elapsedMs });
    writeSamples(storage, samples.slice(-MAX_SAMPLES));
  }

  function estimateRemainingMs(charCount, elapsedMs) {
    const samples = readSamples(storage);
    if (samples.length === 0 || charCount <= 0) {
      return null;
    }
    const msPerChar = samples.reduce((sum, s) => sum + s.ms / s.chars, 0) / samples.length;
    const totalEstimated = msPerChar * charCount;
    const remaining = totalEstimated - elapsedMs;
    return remaining > 0 ? remaining : null;
  }

  return { record, estimateRemainingMs, estimateTotalMs };
}
