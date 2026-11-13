"""背景迴圈只管理排程與錯誤邊界，採集和保留政策交給 CollectionService。"""

from __future__ import annotations

from collections.abc import Callable
import logging
import threading
import time

from ..services import collection
from ..services import exceptions

_logger = logging.getLogger("a7las.metrics_collector")


def _safe_retention_cleanup(cleanup: Callable[[], int]) -> None:
    """執行一次保留政策清理；隔離並記錄錯誤，讓採集流程持續。"""
    try:
        cleanup()
    except Exception:
        _logger.exception("Retention cleanup failed; continuing collection")


def run_collector_loop(
    stop_event: threading.Event,
    service: collection.CollectionService,
    *,
    interval_seconds: float = 30,
    maintenance_interval_seconds: float = 3600,
    monotonic_clock: Callable[[], float] = time.monotonic,
    retention_cleanup: Callable[[], int] | None = None,
) -> None:
    """執行可中斷的採集迴圈，隔離單次採集與清理失敗。

    Args:
        stop_event: 設定後停止；等待間隔可由此事件立即喚醒。
        service: 執行一次採集與保留政策的服務。
        interval_seconds: 每次嘗試完成後的等待秒數，不是固定起始時間差。
        maintenance_interval_seconds: 兩次清理的最短排程間隔，單位秒。
        monotonic_clock: 回傳單調秒數的時鐘，只用於維護排程。
        retention_cleanup: 額外注入的無參數清理函式；None 時使用 service.cleanup。

    啟動時先清理，再立即採集；不為失敗樣本補造資料，也不覆蓋重複時間戳。
    """
    cleanup = retention_cleanup or service.cleanup
    _safe_retention_cleanup(cleanup)
    next_maintenance_at = monotonic_clock() + maintenance_interval_seconds
    while not stop_event.is_set():
        if monotonic_clock() >= next_maintenance_at:
            _safe_retention_cleanup(cleanup)
            next_maintenance_at = (
                monotonic_clock() + maintenance_interval_seconds
            )
        try:
            sample = service.collect_once()
            _logger.debug(
                "Stored metric sample timestamp_ms=%s", sample.timestamp_ms
            )
        except exceptions.DuplicateMetricSampleError:
            _logger.warning(
                "Duplicate metric sample timestamp; skipping without overwrite",
                exc_info=True,
            )
        except Exception:
            _logger.exception("Metrics collection iteration failed; will retry")
        if stop_event.wait(interval_seconds):
            break
