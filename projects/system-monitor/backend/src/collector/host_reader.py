"""組合 readers/，將每項讀取隔離為可獨立失敗的一次主機採集。"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable
from typing import Any

from app.observability import events

from ..database import repository
from .readers import cpu
from .readers import disk_io
from .readers import gpu
from .readers import memory
from .readers import network

_logger = logging.getLogger(__name__)


class HostReader:
    """持有五個 Reader；僅供採集器的單一執行緒使用。"""

    def __init__(self, gpu_timeout_seconds: float = 2.0) -> None:
        """建立五個讀取器，不讀硬體，也不建立資料庫。"""
        self._cpu = cpu.CpuReader()
        self._memory = memory.MemoryReader()
        self._network = network.NetworkReader()
        self._gpu = gpu.GpuReader(gpu_timeout_seconds)
        self._disk = disk_io.DiskIoReader()
        self._network_interface: str | None = None

    def _read_safely(
        self, read: Callable[[], dict[str, Any]], feature_id: str | None = None
    ) -> dict[str, Any]:
        """隔離單項硬體錯誤，保留其他讀取器結果並記錄堆疊。"""
        started = time.perf_counter()
        try:
            result = {
                key: (
                    None
                    if isinstance(value, float) and not math.isfinite(value)
                    else value
                )
                for key, value in read().items()
            }
        # 工作隔離邊界：記錄原始例外後繼續或回傳失敗退出碼。
        except Exception as exc:  # pylint: disable=broad-exception-caught
            if feature_id:
                events.record(
                    "system-monitor",
                    feature_id,
                    outcome="failure",
                    message="硬體讀取失敗",
                    error=exc,
                    source=read.__module__ + "." + read.__qualname__,
                    duration_ms=(time.perf_counter() - started) * 1000,
                )
            _logger.exception("Host reader failed: %s", read.__qualname__)
            return {}
        if feature_id:
            outcome, message = self._result(feature_id, result)
            events.record(
                "system-monitor",
                feature_id,
                outcome=outcome,
                message=message,
                source=read.__module__ + "." + read.__qualname__,
                context=result,
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        return result

    def _result(
        self, feature_id: str, values: dict[str, Any]
    ) -> tuple[str, str]:
        """把來源明確狀態轉為事件結果；平台負責時效與最終健康判定。"""
        keys_by_feature = {
            "cpu": ("cpu_usage_percent",),
            "memory": ("memory_usage_percent",),
            "gpu": ("gpu_usage_percent",),
            "network": (
                "network_download_bytes_per_second",
                "network_upload_bytes_per_second",
            ),
            "disk-io": (
                "disk_read_bytes_per_second",
                "disk_write_bytes_per_second",
            ),
        }
        state = values.get(
            "gpu_status" if feature_id == "gpu" else "disk_io_status"
        )
        states = {
            "unsupported": ("unavailable", "平台不支援此硬體監測"),
            "unavailable": ("unavailable", "目前沒有可用的硬體來源"),
            "warming_up": ("unknown", "正在建立速率基準"),
        }
        if feature_id in {"gpu", "disk-io"} and state in states:
            return states[state]
        if feature_id == "network" and self._network_interface is None:
            return "unavailable", "啟動時沒有可用的網路介面"
        keys = keys_by_feature[feature_id]
        if any(values.get(key) is None for key in keys):
            return "unknown", "等待有效取樣或來源恢復"
        invalid = any(
            not isinstance(values[key], (int, float)) or values[key] < 0
            for key in keys
        )
        if invalid or (
            feature_id in {"cpu", "memory", "gpu"} and values[keys[0]] > 100
        ):
            return "failure", "來源回傳無效的指標"
        return "success", "已取得有效指標，零使用率與零流量亦屬正常"

    def read_info(self) -> dict[str, Any]:
        """組合啟動時的基本資訊；僅由 runner 在啟動時呼叫一次。"""
        info = dict.fromkeys(repository.INFO_COLUMNS)
        info["updated_at_ms"] = int(time.time() * 1000)
        for read in (
            self._cpu.read_info,
            self._memory.read_info,
            self._network.read_info,
            self._gpu.read_info,
        ):
            info.update(self._read_safely(read))
        self._network_interface = info.get("network_interface")
        return info

    def read(self) -> dict[str, Any]:
        """依序組合動態值；時間戳為輪次開始時間，缺值不補零。"""
        sample = dict.fromkeys(repository.METRIC_COLUMNS)
        sample.update(
            timestamp_ms=int(time.time() * 1000),
            gpu_status="unavailable",
            disk_io_status="unavailable",
        )
        for feature_id, read in (
            ("cpu", self._cpu.read),
            ("memory", self._memory.read),
            ("network", self._network.read),
            ("gpu", self._gpu.read),
            ("disk-io", self._disk.read),
        ):
            sample.update(self._read_safely(read, feature_id))
        return sample
