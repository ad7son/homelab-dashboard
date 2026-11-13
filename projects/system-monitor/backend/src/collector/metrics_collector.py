"""背景程序入口：python -m src.collector.metrics_collector。

只組裝服務、取得程序鎖及處理停止訊號；不直接操作硬體、SQL 或診斷檔。
"""
import logging
import signal
import sys
import threading
from ..bootstrap import get_runtime
from ..core.logging import configure_logging
from ..infrastructure.process_lock import CollectorProcessLock, CollectorLockError
from .runner import run_collector_loop

logger = logging.getLogger("a7las.metrics_collector")


def main(argv=None) -> int:
    del argv  # 保留既有 CLI 呼叫形式，尚未增加額外參數。
    configure_logging()
    runtime = get_runtime()
    settings = runtime.settings
    stop_event = threading.Event()

    def shutdown(signum, _frame):
        logger.info("Received signal %s; shutting down collector", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    logger.info("A7LAS metrics collector starting")
    logger.info("Resolved metrics database path: %s", settings.database_path)
    logger.info("Collection interval: %s seconds", settings.collection_interval_seconds)
    lock = CollectorProcessLock(settings.database_path)
    try:
        lock.acquire()
    except CollectorLockError:
        logger.error("Unable to acquire collector lock", exc_info=True)
        return 1
    try:
        runtime.repository.initialize()
        run_collector_loop(stop_event, runtime.collection,
            interval_seconds=settings.collection_interval_seconds,
            maintenance_interval_seconds=settings.maintenance_interval_seconds)
        logger.info("A7LAS metrics collector stopped")
        return 0
    except Exception:
        logger.exception("Metrics collector failed during startup or run")
        return 1
    finally:
        lock.release()


if __name__ == "__main__":
    sys.exit(main())
