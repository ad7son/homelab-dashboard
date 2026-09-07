from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


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


class HistoricalMetricsResponse(BaseModel):
    range: HistoryRange
    start_timestamp_ms: int
    end_timestamp_ms: int
    samples: List[HistoricalMetricSample]
