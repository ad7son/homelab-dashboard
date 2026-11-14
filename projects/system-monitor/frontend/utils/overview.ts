import type { Overview } from '../types/system';

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error('主機資訊回應格式不正確');
  }
  return value as Record<string, unknown>;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function stringOrNull(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

/** API 的 info/metrics 轉為畫面使用的結構，不將缺值補成零。 */
export function parseOverview(value: unknown): Overview {
  const response = record(value);
  const info = record(response.info);
  const metrics = record(response.metrics);
  const timestamp = numberOrNull(metrics.timestamp_ms);
  const infoTimestamp = numberOrNull(info.updated_at_ms);
  if (timestamp === null || timestamp < 0 || infoTimestamp === null) {
    throw new Error('主機資訊缺少有效的取樣時間');
  }
  if (!['available', 'unavailable', 'unsupported'].includes(String(metrics.gpu_status)) ||
      !['available', 'warming_up', 'unavailable'].includes(String(metrics.disk_io_status))) {
    throw new Error('主機資訊包含無效的裝置狀態');
  }
  const loads = [metrics.cpu_load_1, metrics.cpu_load_5, metrics.cpu_load_15].map(numberOrNull);
  return {
    timestamp_ms: timestamp,
    info_updated_at_ms: infoTimestamp,
    cpu: {
      usage_percent: numberOrNull(metrics.cpu_usage_percent),
      physical_cores: numberOrNull(info.cpu_physical_cores),
      logical_cores: numberOrNull(info.cpu_logical_cores),
      frequency: numberOrNull(metrics.cpu_frequency_mhz),
      temperature: numberOrNull(metrics.cpu_temperature_celsius),
      load_average: loads.every((load) => load !== null)
        ? { load_1: loads[0]!, load_5: loads[1]!, load_15: loads[2]! }
        : null,
    },
    memory: {
      total: numberOrNull(info.memory_total_bytes),
      used: numberOrNull(metrics.memory_used_bytes),
      available: numberOrNull(metrics.memory_available_bytes),
      usage_percent: numberOrNull(metrics.memory_usage_percent),
      swap: {
        total: numberOrNull(metrics.swap_total_bytes),
        used: numberOrNull(metrics.swap_used_bytes),
        usage_percent: numberOrNull(metrics.swap_usage_percent),
      },
    },
    network: {
      interface: stringOrNull(info.network_interface),
      ip_address: stringOrNull(info.network_ip_address),
      download_rate: numberOrNull(metrics.network_download_bytes_per_second),
      upload_rate: numberOrNull(metrics.network_upload_bytes_per_second),
    },
    gpu: {
      status: metrics.gpu_status as Overview['gpu']['status'],
      name: stringOrNull(info.gpu_name),
      device_count: numberOrNull(info.gpu_device_count),
      usage_percent: numberOrNull(metrics.gpu_usage_percent),
    },
    disk_io: {
      status: metrics.disk_io_status as Overview['disk_io']['status'],
      read_bytes_per_second: numberOrNull(metrics.disk_read_bytes_per_second),
      write_bytes_per_second: numberOrNull(metrics.disk_write_bytes_per_second),
    },
  };
}

export const STALE_AFTER_MS = 15_000;

export function sampleStatus(timestamp: number, now = Date.now()): 'online' | 'stale' {
  return Math.abs(now - timestamp) > STALE_AFTER_MS ? 'stale' : 'online';
}
