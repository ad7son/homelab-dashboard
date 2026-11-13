"""主機即時資料格式；集中型別與欄位驗證，不執行任何硬體讀取。

null 代表來源未提供資訊，與真實的 0%／0 B/s 不同。
服務與採集器使用 domain/metrics.py 的快照；此處只負責 HTTP 邊界驗證。
"""

from __future__ import annotations

from typing import Literal

import pydantic


# CPU 與可選的溫度、頻率、負載資訊
class LoadAverage(pydantic.BaseModel):
    """主機最近 1、5、15 分鐘的平均負載。

    Attributes:
        load_1: 最近 1 分鐘的系統平均負載，並非 CPU 使用百分比。
        load_5: 最近 5 分鐘的系統平均負載。
        load_15: 最近 15 分鐘的系統平均負載。
    """

    load_1: float
    load_5: float
    load_15: float


class CpuInfo(pydantic.BaseModel):
    """CPU 使用率、核心數與可用的附加資訊。

    Attributes:
        usage_percent: 使用率百分比；零值表示有效的閒置或未使用狀態。
        physical_cores: 實體核心數；無法取得時為 0，由健康規則判定異常。
        logical_cores: 邏輯核心數；無法取得時為 0。
        frequency: 目前 CPU 頻率，單位 MHz；來源未提供時為 None。
        temperature: CPU 溫度，單位攝氏度；來源未提供時為 None。
        load_average: 系統平均負載；平台不支援時為 None。
    """

    usage_percent: float
    physical_cores: int
    logical_cores: int
    frequency: float | None
    temperature: float | None
    load_average: LoadAverage | None


# 記憶體與 Swap
class SwapInfo(pydantic.BaseModel):
    """Swap 空間的容量及使用率。

    Attributes:
        total: 總容量，單位 bytes。
        used: psutil 定義的已用容量，單位 bytes。
        usage_percent: 使用率百分比；零值表示有效的閒置或未使用狀態。
    """

    total: int
    used: int
    usage_percent: float


class MemoryInfo(pydantic.BaseModel):
    """主機實體記憶體與 Swap 快照。

    Attributes:
        total: 總容量，單位 bytes。
        used: psutil 定義的已用容量，單位 bytes。
        available: 可供應用程式使用的容量，單位 bytes，不保證與 used 相加等於 total。
        usage_percent: 使用率百分比；零值表示有效的閒置或未使用狀態。
        swap: Swap 容量與使用率快照。
    """

    total: int
    used: int
    available: int
    usage_percent: float
    swap: SwapInfo


# 主要網路介面與速率
class NetworkInfo(pydantic.BaseModel):
    """主要網路介面與相鄰取樣之間的平均傳輸速率。

    Attributes:
        interface: 主要網路介面名稱；沒有適用介面時為 None。
        ip_address: 主要介面的 IPv4 位址；未取得時為 None。
        download_rate: 每秒接收 bytes；首次、介面切換或計數器重設時可能為 None。
        upload_rate: 每秒傳送 bytes；首次、介面切換或計數器重設時可能為 None。
    """

    interface: str | None
    ip_address: str | None
    download_rate: float | None
    upload_rate: float | None


# GPU：無讀值與真正閒置的零值分開表示
class GpuInfo(pydantic.BaseModel):
    """支援裝置中有效使用率最高的 GPU 快照。

    Attributes:
        status: available、unavailable 或 unsupported；不可用不代表使用率為零。
        usage_percent: 使用率百分比；0 代表有效的閒置讀值，None 代表無讀值。
        name: 顯示名稱。
        device_count: 已取得裝置項目的數量，不等同有效讀值數量。
    """

    status: Literal["available", "unavailable", "unsupported"] = "unavailable"
    usage_percent: float | None = pydantic.Field(default=None, ge=0, le=100)
    name: str | None = None
    device_count: int = 0


# Disk I/O：首次取樣沒有速率
class DiskIoInfo(pydantic.BaseModel):
    """全機磁碟累計計數器換算出的平均讀寫速率。

    Attributes:
        status: available、warming_up 或 unavailable；首次取樣為 warming_up。
        read_bytes_per_second: 全機磁碟每秒讀取 bytes；尚無有效取樣時為 None。
        write_bytes_per_second: 全機磁碟每秒寫入 bytes；尚無有效取樣時為 None。
    """

    status: Literal["available", "warming_up", "unavailable"] = "unavailable"
    read_bytes_per_second: float | None = pydantic.Field(default=None, ge=0)
    write_bytes_per_second: float | None = pydantic.Field(default=None, ge=0)


# 前端即時總覽的完整回應
class Overview(pydantic.BaseModel):
    """提供前端總覽的一組主機資源快照。

    Attributes:
        cpu: CPU 採集結果。
        memory: 記憶體與 Swap 採集結果。
        network: 主要網路介面採集結果。
        gpu: GPU 採集結果。
        disk_io: 全機磁碟 I/O 採集結果。
    """

    cpu: CpuInfo
    memory: MemoryInfo
    network: NetworkInfo
    gpu: GpuInfo
    disk_io: DiskIoInfo
