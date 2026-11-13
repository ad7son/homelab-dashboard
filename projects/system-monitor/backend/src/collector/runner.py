"""背景迴圈只管理排程與錯誤邊界，採集和保留政策交給 CollectionService。"""
import logging
import threading
import time
from ..services.collection import CollectionService
from ..services.exceptions import DuplicateMetricSampleError

logger = logging.getLogger("a7las.metrics_collector")


def _safe_retention_cleanup(cleanup):
    try:
        cleanup()
    except Exception:
        logger.exception("Retention cleanup failed; continuing collection")


def run_collector_loop(stop_event: threading.Event, service: CollectionService, *, interval_seconds=30,
                       maintenance_interval_seconds=3600, monotonic_clock=time.monotonic,
                       retention_cleanup=None):
    """先清理、立即採集、再等待；單調時鐘安排維護，stop_event 可即時喚醒停止。"""
    cleanup = retention_cleanup or service.cleanup
    _safe_retention_cleanup(cleanup)
    next_maintenance_at = monotonic_clock() + maintenance_interval_seconds
    while not stop_event.is_set():
        if monotonic_clock() >= next_maintenance_at:
            _safe_retention_cleanup(cleanup)
            next_maintenance_at = monotonic_clock() + maintenance_interval_seconds
        try:
            sample = service.collect_once()
            logger.debug("Stored metric sample timestamp_ms=%s", sample.timestamp_ms)
        except DuplicateMetricSampleError:
            logger.warning("Duplicate metric sample timestamp; skipping without overwrite", exc_info=True)
        except Exception:
            logger.exception("Metrics collection iteration failed; will retry")
        if stop_event.wait(interval_seconds):
            break
