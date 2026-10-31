export type ServiceStatus =
  | 'active'
  | 'inactive'
  | 'failed'
  | 'unavailable'
  | 'unknown';

export interface MonitoredService {
  key: string;
  display_name: string;
  unit: string;
  required: boolean;
  status: ServiceStatus;
  load_state: string | null;
  active_state: string | null;
  sub_state: string | null;
  description: string | null;
  main_pid: number | null;
  uptime_seconds: number | null;
  started_at_timestamp_ms: number | null;
}

export interface ServicesSummary {
  total: number;
  active: number;
  inactive: number;
  failed: number;
  unavailable: number;
  unknown: number;
}

export interface ServicesResponse {
  summary: ServicesSummary;
  services: MonitoredService[];
}
