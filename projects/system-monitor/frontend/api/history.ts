import projectManifest from '../../project.json';
import { ApiError, requestJson } from './client';

export type HistoricalRange = '15m' | '1h' | '24h' | '7d';

export const HISTORICAL_RANGES: HistoricalRange[] = ['15m', '1h', '24h', '7d'];

export interface HistoricalMetricSample {
  timestamp_ms: number;
  cpu_usage_percent: number | null;
  cpu_temperature_celsius: number | null;
  memory_usage_percent: number | null;
  network_download_bytes_per_second: number | null;
  network_upload_bytes_per_second: number | null;
  gpu_usage_percent: number | null;
  disk_read_bytes_per_second: number | null;
  disk_write_bytes_per_second: number | null;
}

export interface HistoricalMetricsResponse {
  range: HistoricalRange | null;
  start_ms: number;
  end_ms: number;
  interval_seconds: number;
  samples: HistoricalMetricSample[];
}

export async function getHistory(range: HistoricalRange, signal?: AbortSignal): Promise<HistoricalMetricsResponse> {
  try {
    const response = await requestJson(`${projectManifest.apiPrefix}/history?range=${encodeURIComponent(range)}`, { signal, timeoutMs: 15000 });
    return parseHistory(response);
  } catch (error) {
    if (error instanceof ApiError && error.status === 503) {
      throw new ApiError('尚無可用的監測資料，請確認採集器與資料庫是否正常。', 503);
    }
    throw error;
  }
}

/** 缺值保留 null；錯誤結構在進入圖表之前拒絕。 */
export function parseHistory(value: unknown): HistoricalMetricsResponse {
  const body = value as HistoricalMetricsResponse | null;
  const fields = [
    'cpu_usage_percent', 'cpu_temperature_celsius', 'memory_usage_percent',
    'network_download_bytes_per_second', 'network_upload_bytes_per_second',
    'gpu_usage_percent', 'disk_read_bytes_per_second', 'disk_write_bytes_per_second',
  ] as const;
  if (!body || typeof body !== 'object' ||
      !(body.range === null || HISTORICAL_RANGES.includes(body.range)) ||
      !Number.isFinite(body.start_ms) || !Number.isFinite(body.end_ms) ||
      body.start_ms < 0 || body.end_ms < body.start_ms ||
      !Number.isFinite(body.interval_seconds) || body.interval_seconds <= 0 ||
      !Array.isArray(body.samples) || !body.samples.every((sample) =>
        sample && typeof sample === 'object' && Number.isFinite(sample.timestamp_ms) &&
        sample.timestamp_ms >= 0 && fields.every((key) =>
          sample[key] === null || (typeof sample[key] === 'number' && Number.isFinite(sample[key]))))) {
    throw new ApiError('歷史資料回應格式不正確');
  }
  return body;
}
