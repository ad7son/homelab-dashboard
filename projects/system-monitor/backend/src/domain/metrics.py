"""內部主機快照，不依賴 HTTP、Pydantic 或儲存技術。"""
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class LoadAverage:
    load_1: float
    load_5: float
    load_15: float


@dataclass(frozen=True)
class CpuInfo:
    usage_percent: float
    physical_cores: int
    logical_cores: int
    frequency: Optional[float]
    temperature: Optional[float]
    load_average: Optional[LoadAverage]


@dataclass(frozen=True)
class SwapInfo:
    total: int
    used: int
    usage_percent: float


@dataclass(frozen=True)
class MemoryInfo:
    total: int
    used: int
    available: int
    usage_percent: float
    swap: SwapInfo


@dataclass(frozen=True)
class NetworkInfo:
    interface: Optional[str]
    ip_address: Optional[str]
    download_rate: Optional[float]
    upload_rate: Optional[float]


@dataclass(frozen=True)
class GpuInfo:
    status: Literal["available", "unavailable", "unsupported"] = "unavailable"
    usage_percent: float | None = None
    name: str | None = None
    device_count: int = 0


@dataclass(frozen=True)
class DiskIoInfo:
    status: Literal["available", "warming_up", "unavailable"] = "unavailable"
    read_bytes_per_second: float | None = None
    write_bytes_per_second: float | None = None


@dataclass(frozen=True)
class Overview:
    cpu: CpuInfo
    memory: MemoryInfo
    network: NetworkInfo
    gpu: GpuInfo
    disk_io: DiskIoInfo
