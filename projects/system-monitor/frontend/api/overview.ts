import projectManifest from '../../project.json';
import { ApiError, requestJson } from './client';

export interface LoadAverage {
  load_1: number;
  load_5: number;
  load_15: number;
}

export interface CpuInfo {
  usage_percent: number | null;
  physical_cores: number | null;
  logical_cores: number | null;
  frequency: number | null;
  temperature: number | null;
  load_average: LoadAverage | null;
}

export interface SwapInfo {
  total: number | null;
  used: number | null;
  usage_percent: number | null;
}

export interface MemoryInfo {
  total: number | null;
  used: number | null;
  available: number | null;
  usage_percent: number | null;
  swap: SwapInfo;
}

export interface NetworkInfo {
  interface: string | null;
  ip_address: string | null;
  download_rate: number | null;
  upload_rate: number | null;
}

/** 畫面資料模型；API 的 info/metrics 在請求邊界轉換。 */
export interface Overview {
  timestamp_ms: number;
  info_updated_at_ms: number;
  cpu: CpuInfo;
  memory: MemoryInfo;
  network: NetworkInfo;
  gpu: GpuInfo;
  disk_io: DiskIoInfo;
}

export interface GpuInfo {
  status: 'available' | 'unavailable' | 'unsupported';
  usage_percent: number | null;
  name: string | null;
  device_count: number | null;
}

export interface DiskIoInfo {
  status: 'available' | 'warming_up' | 'unavailable';
  read_bytes_per_second: number | null;
  write_bytes_per_second: number | null;
}



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


export async function getOverview(signal?: AbortSignal): Promise<Overview> {
  try {
    const response = await requestJson(`${projectManifest.apiPrefix}/overview`, { signal, timeoutMs: 5000 });
    return parseOverview(response);
  } catch (error) {
    if (error instanceof ApiError && error.status === 503) {
      throw new ApiError('尚無可用的監測資料，請確認採集器與資料庫是否正常。', 503);
    }
    throw error;
  }
}
