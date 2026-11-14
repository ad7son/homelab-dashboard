import type { RealtimeSample } from '../types/realtime';

export const RECENT_AVERAGE_WINDOW_MS = 30_000;

export function averageRecentMetric(
  samples: RealtimeSample[],
  key: keyof RealtimeSample,
  windowMs: number = RECENT_AVERAGE_WINDOW_MS,
  now = Date.now(),
): number | null {
  if (samples.length === 0) {
    return null;
  }

  const cutoff = now - windowMs;

  let sum = 0;
  let count = 0;

  for (const sample of samples) {
    if (sample.timestamp < cutoff) {
      continue;
    }

    const value = sample[key];
    if (typeof value === 'number' && Number.isFinite(value)) {
      sum += value;
      count += 1;
    }
  }

  if (count === 0) {
    return null;
  }

  return sum / count;
}
