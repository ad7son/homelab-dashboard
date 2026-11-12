export const MONITORING_METRICS = [
  { value: 'cpu', label: 'CPU Usage' },
  { value: 'temperature', label: 'CPU Temperature' },
  { value: 'memory', label: 'Memory Usage' },
  { value: 'gpu', label: 'GPU Usage' },
  { value: 'disk_io', label: 'Disk I/O' },
  { value: 'network', label: 'Network Traffic' },
] as const;

export type MonitoringMetric = typeof MONITORING_METRICS[number]['value'];

