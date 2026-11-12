"""歷史資料格式：資料庫與採集器共用不可變樣本，API 使用驗證模型。

儲存樣本保留 dataclass，回應保留 Pydantic，避免搬移時改變驗證與序列化行為。
新指標允許 None，既有歷史資料不得補成假造的零值。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


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


class HistoricalMetricSample(BaseModel):
    timestamp_ms: int
    cpu_usage_percent: float
    cpu_temperature_celsius: Optional[float]
    memory_usage_percent: float
    network_download_bytes_per_second: Optional[float]
    network_upload_bytes_per_second: Optional[float]
    gpu_usage_percent: Optional[float] = None
    disk_read_bytes_per_second: Optional[float] = None
    disk_write_bytes_per_second: Optional[float] = None


class HistoricalMetricsResponse(BaseModel):
    range: HistoryRange
    start_timestamp_ms: int
    end_timestamp_ms: int
    samples: List[HistoricalMetricSample]
