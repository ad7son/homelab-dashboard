import type { HistoricalMetricSample, HistoricalRange } from '../../types/history';
import type { RealtimeSample } from '../../types/realtime';

/** Gap larger than ~2 polling intervals inserts a chart-only break. */
export const REALTIME_CHART_GAP_THRESHOLD_MS = 7000;

/** Gap larger than ~2 raw collector intervals (15m / 1h history). */
export const HISTORY_CHART_GAP_THRESHOLD_MS = 65_000;

/** Gap larger than ~2 five-minute aggregation buckets (24h history). */
export const HISTORY_CHART_GAP_THRESHOLD_24H_MS = 11 * 60 * 1000;

/** Gap larger than ~2 thirty-minute aggregation buckets (7d history). */
export const HISTORY_CHART_GAP_THRESHOLD_7D_MS = 65 * 60 * 1000;

/** @deprecated Use REALTIME_CHART_GAP_THRESHOLD_MS */
export const CHART_GAP_THRESHOLD_MS = REALTIME_CHART_GAP_THRESHOLD_MS;

export function historyChartGapThresholdMs(range: HistoricalRange): number {
  switch (range) {
    case '24h':
      return HISTORY_CHART_GAP_THRESHOLD_24H_MS;
    case '7d':
      return HISTORY_CHART_GAP_THRESHOLD_7D_MS;
    case '15m':
    case '1h':
    default:
      return HISTORY_CHART_GAP_THRESHOLD_MS;
  }
}

export interface ChartPoint {
  timestamp: number;
  cpuUsagePercent: number | null;
  cpuTemperatureCelsius: number | null;
  memoryUsagePercent: number | null;
  networkDownloadBytesPerSecond: number | null;
  networkUploadBytesPerSecond: number | null;
}

function insertChartGaps(
  points: ChartPoint[],
  gapThresholdMs: number,
): ChartPoint[] {
  if (points.length === 0) {
    return [];
  }

  const result: ChartPoint[] = [];

  for (let index = 0; index < points.length; index += 1) {
    const point = points[index];

    if (index > 0) {
      const previous = points[index - 1];
      if (point.timestamp - previous.timestamp > gapThresholdMs) {
        result.push({
          timestamp: previous.timestamp + 1,
          cpuUsagePercent: null,
          cpuTemperatureCelsius: null,
          memoryUsagePercent: null,
          networkDownloadBytesPerSecond: null,
          networkUploadBytesPerSecond: null,
        });
      }
    }

    result.push(point);
  }

  return result;
}

export function toChartPoints(samples: RealtimeSample[]): ChartPoint[] {
  const points = samples.map((sample) => ({
    timestamp: sample.timestamp,
    cpuUsagePercent: sample.cpuUsagePercent,
    cpuTemperatureCelsius: sample.cpuTemperatureCelsius,
    memoryUsagePercent: sample.memoryUsagePercent,
    networkDownloadBytesPerSecond: sample.networkDownloadBytesPerSecond,
    networkUploadBytesPerSecond: sample.networkUploadBytesPerSecond,
  }));

  return insertChartGaps(points, REALTIME_CHART_GAP_THRESHOLD_MS);
}

export function historicalSamplesToChartPoints(
  samples: HistoricalMetricSample[],
  range: HistoricalRange,
): ChartPoint[] {
  const points = samples.map((sample) => ({
    timestamp: sample.timestamp_ms,
    cpuUsagePercent: sample.cpu_usage_percent,
    cpuTemperatureCelsius: sample.cpu_temperature_celsius,
    memoryUsagePercent: sample.memory_usage_percent,
    networkDownloadBytesPerSecond: sample.network_download_bytes_per_second,
    networkUploadBytesPerSecond: sample.network_upload_bytes_per_second,
  }));

  return insertChartGaps(points, historyChartGapThresholdMs(range));
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

export function formatHistoryAxisTime(
  timestamp: number,
  range: HistoricalRange,
): string {
  if (range === '7d') {
    return new Date(timestamp).toLocaleDateString([], {
      month: '2-digit',
      day: '2-digit',
    });
  }

  return formatChartAxisTime(timestamp);
}

export function formatHistoryTooltipTime(timestamp: number): string {
  return new Date(timestamp).toLocaleString([], {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

export function hasValidSeriesValues(
  samples: Array<RealtimeSample | ChartPoint>,
  key: keyof ChartPoint,
): boolean {
  return samples.some((sample) => {
    const value = sample[key as keyof typeof sample];
    return typeof value === 'number' && !Number.isNaN(value);
  });
}

export function hasValidHistoricalTemperature(
  samples: HistoricalMetricSample[],
): boolean {
  return samples.some(
    (sample) =>
      typeof sample.cpu_temperature_celsius === 'number' &&
      !Number.isNaN(sample.cpu_temperature_celsius),
  );
}
