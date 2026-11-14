"""單執行緒定時採集；不補採、不重疊，清理不在啟動時執行。"""

from __future__ import annotations

import logging
import math
import sqlite3
import threading
import time

from .. import config
from ..database import connection
from ..database import repository
from . import host_reader

_logger = logging.getLogger(__name__)


def run(
    settings: config.Settings,
    stop_event: threading.Event,
    *,
    once: bool = False,
) -> None:
    """初始化、更新基本資訊，立即採集，再依單調時間安排後續輪次。

    Args:
        settings: 採集與保留設定。
        stop_event: 可中斷等待的停止事件。
        once: True 時只採集一次，供診斷或開發使用。

    啟動初始化失敗向外傳遞；單輪寫入與清理失敗記錄後繼續。
    retention_days=None 不執行清理。預設首次清理在運行滿 24 小時後。
    """
    connection.initialize(
        settings.database_path, settings.sqlite_timeout_seconds
    )
    store = repository.HostRepository(
        settings.database_path, settings.sqlite_timeout_seconds
    )
    reader = host_reader.HostReader(settings.gpu_timeout_seconds)
    store.update_info(reader.read_info())
    next_sample = time.monotonic()
    next_cleanup = next_sample + settings.cleanup_interval_seconds
    while not stop_event.is_set():
        try:
            store.insert(reader.read())
        # 隔離單輪錯誤；單次診斷模式需向外回報失敗。
        except Exception:  # pylint: disable=broad-exception-caught
            _logger.exception("Metrics collection failed")
            if once:
                raise
        if once:
            return
        now = time.monotonic()
        if settings.retention_days is not None and now >= next_cleanup:
            cutoff = (
                int(time.time() * 1000) - settings.retention_days * 86_400_000
            )
            try:
                count = store.delete_before(cutoff)
                _logger.info("Deleted %s expired metric rows", count)
            except sqlite3.Error:
                _logger.exception(
                    "Retention cleanup failed; collection continues"
                )
            next_cleanup = time.monotonic() + settings.cleanup_interval_seconds
        next_sample += settings.collection_interval_seconds
        now = time.monotonic()
        if next_sample < now:
            # 超時則跨過已錯過的排程點，不快速連續寫入補造樣本。
            skipped = (
                math.floor(
                    (now - next_sample) / settings.collection_interval_seconds
                )
                + 1
            )
            next_sample += skipped * settings.collection_interval_seconds
        stop_event.wait(max(0, next_sample - time.monotonic()))
