"""將作業系統的累計磁碟讀寫 bytes 換算為兩次取樣間的平均速率。

資料為 psutil 回報的全機磁碟合計，不是磁碟容量、測速結果或單一專案 I/O。
使用單調時鐘避免校時影響；鎖與最短取樣間隔讓多個客戶端共用同一組讀值。
"""

import threading
import time

import psutil

from system_monitor.schemas.disk_io import DiskIoInfo

MIN_SAMPLE_INTERVAL_SECONDS = 1
_lock = threading.Lock()
_previous: tuple[float, int, int] | None = None
_latest = DiskIoInfo(status="warming_up")


def get_disk_io_info() -> DiskIoInfo:
    """首次、計數器重設或讀取中斷後重新建立基準，不顯示錯誤尖峰。"""
    global _previous, _latest
    with _lock:
        now = time.monotonic()
        if _previous is not None and now - _previous[0] < MIN_SAMPLE_INTERVAL_SECONDS:
            return _latest
        try:
            counters = psutil.disk_io_counters(nowrap=True)
        except (OSError, AttributeError, NotImplementedError, RuntimeError):
            counters = None
        if counters is None:
            _previous = None
            _latest = DiskIoInfo()
            return _latest

        current = (now, counters.read_bytes, counters.write_bytes)
        if _previous is None:
            _latest = DiskIoInfo(status="warming_up")
        else:
            elapsed = now - _previous[0]
            read_delta = counters.read_bytes - _previous[1]
            write_delta = counters.write_bytes - _previous[2]
            if read_delta < 0 or write_delta < 0:
                _latest = DiskIoInfo(status="warming_up")
            else:
                _latest = DiskIoInfo(
                    status="available",
                    read_bytes_per_second=read_delta / elapsed,
                    write_bytes_per_second=write_delta / elapsed,
                )
        _previous = current
        return _latest

