export interface RealtimeSample {
  timestamp: number;
  cpuUsagePercent: number;
  cpuTemperatureCelsius: number | null;
  memoryUsagePercent: number;
  networkDownloadBytesPerSecond: number | null;
  networkUploadBytesPerSecond: number | null;
}
