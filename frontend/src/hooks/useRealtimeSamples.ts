import { useCallback, useState } from 'react';
import type { RealtimeSample } from '../types/realtime';
import type { Overview } from '../types/system';

export const REALTIME_WINDOW_MS = 5 * 60 * 1000;
export const MAX_REALTIME_SAMPLES = 120;

export function overviewToRealtimeSample(
  overview: Overview,
  timestamp: number,
): RealtimeSample {
  return {
    timestamp,
    cpuUsagePercent: overview.cpu.usage_percent,
    cpuTemperatureCelsius: overview.cpu.temperature,
    memoryUsagePercent: overview.memory.usage_percent,
    networkDownloadBytesPerSecond: overview.network.download_rate,
    networkUploadBytesPerSecond: overview.network.upload_rate,
  };
}

export function pruneRealtimeSamples(
  samples: RealtimeSample[],
  now: number,
): RealtimeSample[] {
  const cutoff = now - REALTIME_WINDOW_MS;
  let pruned = samples.filter((sample) => sample.timestamp >= cutoff);

  if (pruned.length > MAX_REALTIME_SAMPLES) {
    pruned = pruned.slice(pruned.length - MAX_REALTIME_SAMPLES);
  }

  return pruned;
}

interface UseRealtimeSamplesResult {
  samples: RealtimeSample[];
  appendSample: (overview: Overview, timestamp: number) => void;
}

export function useRealtimeSamples(): UseRealtimeSamplesResult {
  const [samples, setSamples] = useState<RealtimeSample[]>([]);

  const appendSample = useCallback((overview: Overview, timestamp: number) => {
    setSamples((previous) => {
      const next = [...previous, overviewToRealtimeSample(overview, timestamp)];
      return pruneRealtimeSamples(next, timestamp);
    });
  }, []);

  return {
    samples,
    appendSample,
  };
}
