export type HistoricalRange = '15m' | '1h' | '24h' | '7d';

export const HISTORICAL_RANGES: HistoricalRange[] = ['15m', '1h', '24h', '7d'];

export interface HistoricalMetricSample {
  timestamp_ms: number;
  cpu_usage_percent: number;
  cpu_temperature_celsius: number | null;
  memory_usage_percent: number;
  network_download_bytes_per_second: number | null;
  network_upload_bytes_per_second: number | null;
}

export interface HistoricalMetricsResponse {
  range: HistoricalRange;
  start_timestamp_ms: number;
  end_timestamp_ms: number;
  samples: HistoricalMetricSample[];
}
