import type { RealtimeSample } from '../../types/realtime';

/** Gap larger than ~2 polling intervals inserts a chart-only break. */
export const CHART_GAP_THRESHOLD_MS = 7000;

export interface ChartPoint {
  timestamp: number;
  cpuUsagePercent: number | null;
  cpuTemperatureCelsius: number | null;
  memoryUsagePercent: number | null;
  networkDownloadBytesPerSecond: number | null;
  networkUploadBytesPerSecond: number | null;
}

export function toChartPoints(samples: RealtimeSample[]): ChartPoint[] {
  if (samples.length === 0) {
    return [];
  }

  const points: ChartPoint[] = [];

  for (let index = 0; index < samples.length; index += 1) {
    const sample = samples[index];

    if (index > 0) {
      const previous = samples[index - 1];
      if (sample.timestamp - previous.timestamp > CHART_GAP_THRESHOLD_MS) {
        points.push({
          timestamp: previous.timestamp + 1,
          cpuUsagePercent: null,
          cpuTemperatureCelsius: null,
          memoryUsagePercent: null,
          networkDownloadBytesPerSecond: null,
          networkUploadBytesPerSecond: null,
        });
      }
    }

    points.push({
      timestamp: sample.timestamp,
      cpuUsagePercent: sample.cpuUsagePercent,
      cpuTemperatureCelsius: sample.cpuTemperatureCelsius,
      memoryUsagePercent: sample.memoryUsagePercent,
      networkDownloadBytesPerSecond: sample.networkDownloadBytesPerSecond,
      networkUploadBytesPerSecond: sample.networkUploadBytesPerSecond,
    });
  }

  return points;
}

export function formatChartAxisTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

export function formatChartTooltipTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

export function hasValidSeriesValues(
  samples: RealtimeSample[],
  key: keyof RealtimeSample,
): boolean {
  return samples.some((sample) => {
    const value = sample[key];
    return typeof value === 'number' && !Number.isNaN(value);
  });
}
