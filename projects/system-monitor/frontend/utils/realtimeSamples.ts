export interface RealtimeSample {
  timestamp: number;
  cpuUsagePercent: number | null;
  cpuTemperatureCelsius: number | null;
  memoryUsagePercent: number | null;
  networkDownloadBytesPerSecond: number | null;
  networkUploadBytesPerSecond: number | null;
  gpuUsagePercent: number | null;
  diskReadBytesPerSecond: number | null;
  diskWriteBytesPerSecond: number | null;
}

import type { Overview } from '../api/overview';

export const REALTIME_WINDOW_MS = 5 * 60 * 1000;
export const MAX_REALTIME_SAMPLES = 120;

export function overviewToRealtimeSample(
  overview: Overview,
  timestamp: number = overview.timestamp_ms,
): RealtimeSample {
  return {
    timestamp,
    cpuUsagePercent: overview.cpu.usage_percent,
    cpuTemperatureCelsius: overview.cpu.temperature,
    memoryUsagePercent: overview.memory.usage_percent,
    networkDownloadBytesPerSecond: overview.network.download_rate,
    networkUploadBytesPerSecond: overview.network.upload_rate,
    gpuUsagePercent: overview.gpu?.usage_percent ?? null,
    diskReadBytesPerSecond: overview.disk_io?.read_bytes_per_second ?? null,
    diskWriteBytesPerSecond: overview.disk_io?.write_bytes_per_second ?? null,
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


/** 同一資料庫樣本只加入一次；不以請求時間補造圖表點。 */
export function mergeRealtimeSample(
  previous: RealtimeSample[], overview: Overview, now = Date.now(),
): RealtimeSample[] {
  const retained = pruneRealtimeSamples(previous, now);
  const latest = retained.at(-1);
  if (overview.timestamp_ms < now - REALTIME_WINDOW_MS ||
      (latest && overview.timestamp_ms <= latest.timestamp)) return retained;
  return pruneRealtimeSamples([...retained, overviewToRealtimeSample(overview)], now);
}
