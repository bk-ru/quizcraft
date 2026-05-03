const TIMING_KEY = "quizcraft:gen-timing";
const MAX_SAMPLES = 20;

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
    /* localStorage unavailable — degrade silently */
  }
}

export function createGenTiming(storage = (typeof window !== "undefined" ? window.localStorage : null)) {
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

  return { record, estimateRemainingMs };
}
