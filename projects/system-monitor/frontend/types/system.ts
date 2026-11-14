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

export type ConnectionStatus = 'online' | 'stale' | 'unstable' | 'offline';
