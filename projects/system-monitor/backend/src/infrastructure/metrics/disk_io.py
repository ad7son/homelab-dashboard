"""累計磁碟計數器適配器；單調時鐘、實例鎖與最短間隔保護速率計算。"""

from __future__ import annotations

import threading
import time

import psutil

from ...domain import metrics


class DiskIoReader:
    """保留前次磁碟計數及最近速率的採集器。"""

    def __init__(self, interval_seconds: float = 1) -> None:
        """建立磁碟取樣狀態，不立即讀取計數器。

        Args:
            interval_seconds: 正數最短取樣間隔；間隔內共用最近結果，單位秒。
        """
        self._interval = interval_seconds
        self._previous: tuple[float, int, int] | None = None
        self._latest = metrics.DiskIoInfo(status="warming_up")
        self._lock = threading.Lock()

    def read(self) -> metrics.DiskIoInfo:
        """回傳全機磁碟每秒讀寫 bytes，並保護取樣基準不被並行覆蓋。

        首次與計數器重設時為 warming_up，讀取失敗時為 unavailable。
        失敗會清除基準；恢復後需重新取得兩次樣本，避免出現錯誤尖峰。
        """
        with self._lock:
            now = time.monotonic()
            if (
                self._previous is not None
                and now - self._previous[0] < self._interval
            ):
                return self._latest
            try:
                counters = psutil.disk_io_counters(nowrap=True)
            except (OSError, AttributeError, NotImplementedError, RuntimeError):
                counters = None
            if counters is None:
                self._previous = None
                self._latest = metrics.DiskIoInfo()
                return self._latest

            current = (now, counters.read_bytes, counters.write_bytes)
            if self._previous is None:
                self._latest = metrics.DiskIoInfo(status="warming_up")
            else:
                elapsed = now - self._previous[0]
                read_delta = counters.read_bytes - self._previous[1]
                write_delta = counters.write_bytes - self._previous[2]
                if read_delta < 0 or write_delta < 0:
                    self._latest = metrics.DiskIoInfo(status="warming_up")
                else:
                    self._latest = metrics.DiskIoInfo(
                        status="available",
                        read_bytes_per_second=read_delta / elapsed,
                        write_bytes_per_second=write_delta / elapsed,
                    )
            self._previous = current
            return self._latest
