"""主機即時資料格式；集中型別與欄位驗證，不執行任何硬體讀取。

null 代表來源未提供資訊，與真實的 0%／0 B/s 不同。
API、背景採集器與健康檢查共用相同模型，避免欄位定義分歧。
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field


# CPU 與可選的溫度、頻率、負載資訊
class LoadAverage(BaseModel):
    load_1: float
    load_5: float
    load_15: float


class CpuInfo(BaseModel):
    usage_percent: float
    physical_cores: int
    logical_cores: int
    frequency: Optional[float]
    temperature: Optional[float]
    load_average: Optional[LoadAverage]


# 記憶體與 Swap
class SwapInfo(BaseModel):
    total: int
    used: int
    usage_percent: float


class MemoryInfo(BaseModel):
    total: int
    used: int
    available: int
    usage_percent: float
    swap: SwapInfo


# 主要網路介面與速率
class NetworkInfo(BaseModel):
    interface: Optional[str]
    ip_address: Optional[str]
    download_rate: Optional[float]
    upload_rate: Optional[float]


# GPU：無讀值與真正閒置的零值分開表示
class GpuInfo(BaseModel):
    status: Literal["available", "unavailable", "unsupported"] = "unavailable"
    usage_percent: float | None = Field(default=None, ge=0, le=100)
    name: str | None = None
    device_count: int = 0


# Disk I/O：首次取樣沒有速率
class DiskIoInfo(BaseModel):
    status: Literal["available", "warming_up", "unavailable"] = "unavailable"
    read_bytes_per_second: float | None = Field(default=None, ge=0)
    write_bytes_per_second: float | None = Field(default=None, ge=0)


# 前端即時總覽的完整回應
class Overview(BaseModel):
    cpu: CpuInfo
    memory: MemoryInfo
    network: NetworkInfo
    gpu: GpuInfo
    disk_io: DiskIoInfo
