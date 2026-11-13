"""歷史樣本與時間範圍的內部定義；空值與不可變樣本保留既有語意。"""

from __future__ import annotations

import dataclasses
import enum


@dataclasses.dataclass(frozen=True)
class MetricSampleRecord:
    """一次採集或降採樣所得的不可變歷史紀錄。

    Attributes:
        timestamp_ms: Unix 時間戳，單位毫秒。
        cpu_usage_percent: CPU 使用率百分比。
        cpu_temperature_celsius: CPU 攝氏溫度；不支援時為 None。
        memory_usage_percent: 記憶體使用率百分比。
        network_download_bytes_per_second: 每秒接收 bytes；缺少基準時為 None。
        network_upload_bytes_per_second: 每秒傳送 bytes；缺少基準時為 None。
        gpu_usage_percent: 有效 GPU 使用率百分比；無讀值或舊版樣本為 None。
        disk_read_bytes_per_second: 每秒磁碟讀取 bytes；無讀值或舊版樣本為 None。
        disk_write_bytes_per_second: 每秒磁碟寫入 bytes；無讀值或舊版樣本為 None。
    """

    timestamp_ms: int
    cpu_usage_percent: float
    cpu_temperature_celsius: float | None
    memory_usage_percent: float
    network_download_bytes_per_second: float | None
    network_upload_bytes_per_second: float | None
    gpu_usage_percent: float | None = None
    disk_read_bytes_per_second: float | None = None
    disk_write_bytes_per_second: float | None = None


class HistoryRange(str, enum.Enum):
    """歷史查詢支援的四種時間範圍。"""

    M15 = "15m"
    H1 = "1h"
    H24 = "24h"
    D7 = "7d"


@dataclasses.dataclass(frozen=True)
class HistoricalMetrics:
    """包含查詢時間窗及樣本的歷史查詢結果。

    Attributes:
        range: 查詢時間範圍：15m、1h、24h 或 7d。
        start_timestamp_ms: 包含在查詢內的起始 Unix 毫秒時間戳。
        end_timestamp_ms: 包含在查詢內的結束 Unix 毫秒時間戳。
        samples: 時間窗內的樣本；空清單表示查詢成功但沒有資料，不補造缺失時段。
    """

    range: HistoryRange
    start_timestamp_ms: int
    end_timestamp_ms: int
    samples: list[MetricSampleRecord]
