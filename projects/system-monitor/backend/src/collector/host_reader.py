"""組合 readers/，將每項讀取隔離為可獨立失敗的一次主機採集。"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable
from typing import Any

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

    def _read_safely(
        self, read: Callable[[], dict[str, Any]]
    ) -> dict[str, Any]:
        """隔離單項硬體錯誤，保留其他讀取器結果並記錄堆疊。"""
        try:
            return {
                key: (
                    None
                    if isinstance(value, float) and not math.isfinite(value)
                    else value
                )
                for key, value in read().items()
            }
        # 工作隔離邊界：記錄原始例外後繼續或回傳失敗退出碼。
        except Exception:  # pylint: disable=broad-exception-caught
            _logger.exception("Host reader failed: %s", read.__qualname__)
            return {}

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
        return info

    def read(self) -> dict[str, Any]:
        """依序組合動態值；時間戳為輪次開始時間，缺值不補零。"""
        sample = dict.fromkeys(repository.METRIC_COLUMNS)
        sample.update(
            timestamp_ms=int(time.time() * 1000),
            gpu_status="unavailable",
            disk_io_status="unavailable",
        )
        for read in (
            self._cpu.read,
            self._memory.read,
            self._network.read,
            self._gpu.read,
            self._disk.read,
        ):
            sample.update(self._read_safely(read))
        return sample
