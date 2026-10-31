export interface SystemInfo {
  hostname: string;
  operating_system: string;
  os_version: string | null;
  kernel: string;
  architecture: string;
  uptime: number;
}

export interface LoadAverage {
  load_1: number;
  load_5: number;
  load_15: number;
}

export interface CpuInfo {
  usage_percent: number;
  physical_cores: number;
  logical_cores: number;
  frequency: number | null;
  temperature: number | null;
  load_average: LoadAverage | null;
}

export interface SwapInfo {
  total: number;
  used: number;
  usage_percent: number;
}

export interface MemoryInfo {
  total: number;
  used: number;
  available: number;
  usage_percent: number;
  swap: SwapInfo;
}

export interface DiskInfo {
  device: string | null;
  mount_point: string;
  filesystem_type: string;
  total_bytes: number;
  used_bytes: number;
  free_bytes: number;
  usage_percent: number;
}

export interface NetworkInfo {
  interface: string | null;
  ip_address: string | null;
  download_rate: number | null;
  upload_rate: number | null;
}

export interface Overview {
  system: SystemInfo;
  cpu: CpuInfo;
  memory: MemoryInfo;
  disks: DiskInfo[];
  network: NetworkInfo;
}

export type ConnectionStatus = 'online' | 'unstable' | 'offline';
