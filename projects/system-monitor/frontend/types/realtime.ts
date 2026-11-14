export interface RealtimeSample {
  timestamp: number;
  cpuUsagePercent: number | null;
  cpuTemperatureCelsius: number | null;
  memoryUsagePercent: number | null;
  networkDownloadBytesPerSecond: number | null;
  networkUploadBytesPerSecond: number | null;
  gpuUsagePercent: number | null;
  diskReadBytesPerSecond: number | null;
  diskWriteBytesPerSecond: number | null;
}
