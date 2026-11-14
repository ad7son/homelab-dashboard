"""透過磁碟累計計數與單調時鐘計算全機讀寫速度。"""

from __future__ import annotations

import time

import psutil


class DiskIoReader:
    """由採集器單執行緒持有的磁碟計數基準。"""

    def __init__(self) -> None:
        """建立空基準，不讀硬體。"""
        self._previous: tuple[float, int, int] | None = None

    def read(self) -> dict[str, str | float]:
        """回傳 bytes/s 與狀態；讀取失敗會清除基準，避免恢復後假尖峰。"""
        try:
            counter = psutil.disk_io_counters(nowrap=True)
        except (OSError, RuntimeError, NotImplementedError):
            self._previous = None
            raise
        if counter is None:
            self._previous = None
            return {"disk_io_status": "unavailable"}
        current = (time.monotonic(), counter.read_bytes, counter.write_bytes)
        previous, self._previous = self._previous, current
        if previous is None:
            return {"disk_io_status": "warming_up"}
        elapsed = current[0] - previous[0]
        read_delta, write_delta = (
            current[1] - previous[1],
            current[2] - previous[2],
        )
        if elapsed <= 0 or read_delta < 0 or write_delta < 0:
            return {"disk_io_status": "warming_up"}
        return {
            "disk_io_status": "available",
            "disk_read_bytes_per_second": read_delta / elapsed,
            "disk_write_bytes_per_second": write_delta / elapsed,
        }
