/** Loudness of one audio frame (bytes centred on 128, as AnalyserNode gives them), from 0 to 1. */
export function rmsLevel(samples: Uint8Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (const s of samples) {
    const v = (s - 128) / 128;
    sum += v * v;
  }
  return Math.sqrt(sum / samples.length);
}

/** Follows the level up quickly and down slowly, so that the light does not flicker. */
export function smoothLevel(previous: number, level: number, attack = 0.6, release = 0.12): number {
  return previous + (level - previous) * (level > previous ? attack : release);
}

/** Level 0..1 to a bulb brightness 1..255. `sensitivity` amplifies quiet sources (1 = as is). */
export function levelToBrightness(level: number, sensitivity: number, minBrightness = 5): number {
  const scaled = Math.min(1, Math.max(0, level * sensitivity));
  return Math.round(minBrightness + scaled * (255 - minBrightness));
}

/**
 * Spots beats: a level clearly above its recent average, not too soon after the previous beat.
 * Call it once per frame with the (already amplified) level and the time in ms.
 */
export function createBeatDetector(minGapMs = 180, ratio = 1.3, floor = 0.08): (level: number, now: number) => boolean {
  let average = 0;
  let lastBeat = Number.NEGATIVE_INFINITY;
  return (level, now) => {
    const beat = level > floor && level > average * ratio && now - lastBeat >= minGapMs;
    average += (level - average) * 0.05;
    if (beat) lastBeat = now;
    return beat;
  };
}
