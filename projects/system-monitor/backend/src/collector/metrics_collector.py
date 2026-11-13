"""背景程序入口：python -m src.collector.metrics_collector。

只組裝服務、取得程序鎖及處理停止訊號；不直接操作硬體、SQL 或診斷檔。
"""

from __future__ import annotations

from collections.abc import Sequence
import logging
import signal
import sys
import threading
import types

from .. import bootstrap
from ..core import logging as core_logging
from ..infrastructure import process_lock
from . import runner

_logger = logging.getLogger("a7las.metrics_collector")


def main(argv: Sequence[str] | None = None) -> int:
    """啟動獨立採集程序，註冊停止訊號並管理程序鎖。

    Args:
        argv: 保留的 CLI 引數介面，目前不解析額外參數。

    Returns:
        正常停止為 0；取得鎖或受保護的啟動／執行階段失敗為 1。

    Raises:
        OSError: 進入執行邊界前讀取設定失敗。
        RuntimeError: 無法解析平台預設資料庫位置。
        ValueError: 由非主執行緒呼叫而無法註冊訊號。
    """
    del argv  # 保留既有 CLI 呼叫形式，尚未增加額外參數。
    core_logging.configure_logging()
    runtime = bootstrap.get_runtime()
    settings = runtime.settings
    stop_event = threading.Event()

    def shutdown(signum: int, _frame: types.FrameType | None) -> None:
        """設定停止事件，讓背景等待可立即被喚醒。

        Args:
            signum: 收到的作業系統訊號編號。
            _frame: 訊號處理器規定的堆疊框架，此處不使用。
        """
        del _frame  # 訊號處理器介面要求此參數，本實作不讀取堆疊。
        _logger.info("Received signal %s; shutting down collector", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    _logger.info("A7LAS metrics collector starting")
    _logger.info("Resolved metrics database path: %s", settings.database_path)
    _logger.info(
        "Collection interval: %s seconds", settings.collection_interval_seconds
    )
    lock = process_lock.CollectorProcessLock(settings.database_path)
    try:
        lock.acquire()
    except process_lock.CollectorLockError:
        _logger.error("Unable to acquire collector lock", exc_info=True)
        return 1
    try:
        runtime.repository.initialize()
        runner.run_collector_loop(
            stop_event,
            runtime.collection,
            interval_seconds=settings.collection_interval_seconds,
            maintenance_interval_seconds=settings.maintenance_interval_seconds,
        )
        _logger.info("A7LAS metrics collector stopped")
        return 0
    except Exception:
        _logger.exception("Metrics collector failed during startup or run")
        return 1
    finally:
        lock.release()


if __name__ == "__main__":
    sys.exit(main())
