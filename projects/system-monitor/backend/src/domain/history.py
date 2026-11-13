"""歷史樣本與時間範圍的內部定義；空值與不可變樣本保留既有語意。"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

@dataclass(frozen=True)
class MetricSampleRecord:
    timestamp_ms: int
    cpu_usage_percent: float
    cpu_temperature_celsius: Optional[float]
    memory_usage_percent: float
    network_download_bytes_per_second: Optional[float]
    network_upload_bytes_per_second: Optional[float]
    gpu_usage_percent: Optional[float] = None
    disk_read_bytes_per_second: Optional[float] = None
    disk_write_bytes_per_second: Optional[float] = None

class HistoryRange(str, Enum):
    M15 = "15m"
    H1 = "1h"
    H24 = "24h"
    D7 = "7d"

@dataclass(frozen=True)
class HistoricalMetrics:
    range: HistoryRange
    start_timestamp_ms: int
    end_timestamp_ms: int
    samples: list[MetricSampleRecord]
