"""累計磁碟計數器適配器；單調時鐘、實例鎖與最短間隔保護速率計算。"""
import threading
import time
import psutil
from ...domain.metrics import DiskIoInfo

class DiskIoReader:
    def __init__(self, interval_seconds=1):
        self._interval = interval_seconds
        self._previous = None
        self._latest = DiskIoInfo(status="warming_up")
        self._lock = threading.Lock()

    def read(self) -> DiskIoInfo:
        """首次、計數器重設或讀取中斷後重新建立基準，不顯示錯誤尖峰。"""
        with self._lock:
            now = time.monotonic()
            if self._previous is not None and now - self._previous[0] < self._interval:
                return self._latest
            try:
                counters = psutil.disk_io_counters(nowrap=True)
            except (OSError, AttributeError, NotImplementedError, RuntimeError):
                counters = None
            if counters is None:
                self._previous = None
                self._latest = DiskIoInfo()
                return self._latest

            current = (now, counters.read_bytes, counters.write_bytes)
            if self._previous is None:
                self._latest = DiskIoInfo(status="warming_up")
            else:
                elapsed = now - self._previous[0]
                read_delta = counters.read_bytes - self._previous[1]
                write_delta = counters.write_bytes - self._previous[2]
                if read_delta < 0 or write_delta < 0:
                    self._latest = DiskIoInfo(status="warming_up")
                else:
                    self._latest = DiskIoInfo(
                        status="available",
                        read_bytes_per_second=read_delta / elapsed,
                        write_bytes_per_second=write_delta / elapsed,
                    )
            self._previous = current
            return self._latest
