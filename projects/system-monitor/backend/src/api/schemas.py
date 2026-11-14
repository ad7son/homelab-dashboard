"""HTTP 回應模型；數值單位直接標記於欄位名稱，None 表示不可用。"""

from __future__ import annotations

from typing import Literal

import pydantic


class HostInfo(pydantic.BaseModel):
    """目前基本資訊，僅於採集器啟動時更新；容量單位為 bytes。"""

    updated_at_ms: int
    cpu_physical_cores: int | None
    cpu_logical_cores: int | None
    memory_total_bytes: int | None
    gpu_name: str | None
    gpu_device_count: int | None
    network_interface: str | None
    network_ip_address: str | None


class HistorySample(pydantic.BaseModel):
    """原始或時間桶平均指標；速率為 bytes/s，溫度為攝氏度。"""

    timestamp_ms: int
    cpu_usage_percent: float | None
    cpu_temperature_celsius: float | None
    memory_usage_percent: float | None
    network_download_bytes_per_second: float | None
    network_upload_bytes_per_second: float | None
    gpu_usage_percent: float | None
    disk_read_bytes_per_second: float | None
    disk_write_bytes_per_second: float | None


class HostMetrics(HistorySample):
    """最近一輪的完整動態資訊；CPU 頻率為 MHz，load 為系統平均負載。"""

    cpu_frequency_mhz: float | None
    cpu_load_1: float | None
    cpu_load_5: float | None
    cpu_load_15: float | None
    memory_used_bytes: int | None
    memory_available_bytes: int | None
    swap_total_bytes: int | None
    swap_used_bytes: int | None
    swap_usage_percent: float | None
    gpu_status: Literal["available", "unavailable", "unsupported"]
    disk_io_status: Literal["available", "warming_up", "unavailable"]


class Overview(pydantic.BaseModel):
    """基本資訊與最新指標；資料可能過期，取樣時間不得改成請求時間。"""

    info: HostInfo
    metrics: HostMetrics


class History(pydantic.BaseModel):
    """歷史視窗、實際彙整間隔與樣本；不補造空時間桶。"""

    range: str | None
    start_ms: int
    end_ms: int
    interval_seconds: float
    samples: list[HistorySample]
