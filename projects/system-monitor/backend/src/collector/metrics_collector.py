"""獨立歷史採集器：管理排程、程序鎖、維護與正常停止。

啟動方式：
    python -m src.collector.metrics_collector
"""

from __future__ import annotations

import logging
import signal
import sqlite3
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from .status import record_collector_result
from ..history.database import DuplicateMetricSampleError, connect_metrics_database, delete_metric_samples_before, insert_metric_sample, resolve_metrics_db_path
from ..history.models import MetricSampleRecord
from ..machine.models import CpuInfo, MemoryInfo, NetworkInfo, GpuInfo, DiskIoInfo
from ..machine.readers import get_cpu_info, get_memory_info, get_network_info, get_disk_io_info
from ..machine.gpu import get_gpu_info

COLLECTION_INTERVAL_SECONDS = 30
RAW_RETENTION_MS = 7 * 24 * 60 * 60 * 1000
MAINTENANCE_INTERVAL_SECONDS = 60 * 60

logger = logging.getLogger("a7las.metrics_collector")

CpuReader = Callable[[], CpuInfo]
MemoryReader = Callable[[], MemoryInfo]
NetworkReader = Callable[[], NetworkInfo]
GpuReader = Callable[[], GpuInfo]
DiskIoReader = Callable[[], DiskIoInfo]
Clock = Callable[[], float]
MonotonicClock = Callable[[], float]
RetentionCleanup = Callable[[Path], Optional[int]]


def _load_fcntl():
    """取得程序鎖時才載入 fcntl，避免其他平台僅匯入模組就失敗。"""
    import fcntl

    return fcntl


class CollectorLockError(RuntimeError):
    """無法取得採集器程序鎖時回報。"""


class CollectorProcessLock:
    """對資料庫旁的鎖檔取得非阻塞排他鎖，防止兩個採集器同時寫入。"""

    def __init__(self, db_path: Path) -> None:
        self.lock_path = Path(f"{db_path}.collector.lock")
        self._file = None

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.lock_path, "a+", encoding="utf-8")
        try:
            lock = _load_fcntl()
            lock.flock(handle.fileno(), lock.LOCK_EX | lock.LOCK_NB)
        except ModuleNotFoundError as exc:
            handle.close()
            raise CollectorLockError(
                "Collector file locking requires Linux fcntl.flock"
            ) from exc
        except BlockingIOError as exc:
            handle.close()
            raise CollectorLockError(
                f"Another metrics collector appears to be running "
                f"(lock file: {self.lock_path})"
            ) from exc
        self._file = handle

    def release(self) -> None:
        if self._file is None:
            return
        try:
            lock = _load_fcntl()
            lock.flock(self._file.fileno(), lock.LOCK_UN)
        finally:
            self._file.close()
            self._file = None

    def __enter__(self) -> "CollectorProcessLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


def collect_once(
    connection: sqlite3.Connection,
    *,
    cpu_reader: CpuReader = get_cpu_info,
    memory_reader: MemoryReader = get_memory_info,
    network_reader: NetworkReader = get_network_info,
    gpu_reader: GpuReader = get_gpu_info,
    disk_io_reader: DiskIoReader = get_disk_io_info,
    clock: Clock = time.time,
) -> MetricSampleRecord:
    """取得各項主機指標並寫入一筆樣本；首次取樣缺值維持 None。"""
    cpu = cpu_reader()
    memory = memory_reader()
    network = network_reader()
    gpu = gpu_reader()
    disk_io = disk_io_reader()
    timestamp_ms = int(clock() * 1000)

    sample = MetricSampleRecord(
        timestamp_ms=timestamp_ms,
        cpu_usage_percent=float(cpu.usage_percent),
        cpu_temperature_celsius=cpu.temperature,
        memory_usage_percent=float(memory.usage_percent),
        network_download_bytes_per_second=network.download_rate,
        network_upload_bytes_per_second=network.upload_rate,
        gpu_usage_percent=gpu.usage_percent,
        disk_read_bytes_per_second=disk_io.read_bytes_per_second,
        disk_write_bytes_per_second=disk_io.write_bytes_per_second,
    )
    insert_metric_sample(connection, sample)
    return sample


def run_collect_iteration(
    db_path: Path,
    *,
    cpu_reader: CpuReader = get_cpu_info,
    memory_reader: MemoryReader = get_memory_info,
    network_reader: NetworkReader = get_network_info,
    gpu_reader: GpuReader = get_gpu_info,
    disk_io_reader: DiskIoReader = get_disk_io_info,
    clock: Clock = time.time,
) -> MetricSampleRecord:
    """每次採集使用短生命週期連線，記錄成功或失敗後確實關閉連線。"""
    connection = None
    try:
        connection = connect_metrics_database(db_path)
        sample = collect_once(
            connection,
            cpu_reader=cpu_reader,
            memory_reader=memory_reader,
            network_reader=network_reader,
            gpu_reader=gpu_reader,
            disk_io_reader=disk_io_reader,
            clock=clock,
        )
        record_collector_result(db_path, sample=sample)
        return sample
    except Exception as exc:
        record_collector_result(db_path, error=exc)
        raise
    finally:
        if connection is not None:
            connection.close()


def run_retention_cleanup(
    db_path: Path,
    *,
    clock: Clock = time.time,
    retention_ms: int = RAW_RETENTION_MS,
) -> int:
    """以實際時間計算保留期限並呼叫資料庫刪除。

    保留天數屬採集政策，放在這裡；SQL 與交易交由 database.py。"""
    cutoff_timestamp_ms = int(clock() * 1000) - int(retention_ms)
    connection = connect_metrics_database(db_path)
    try:
        deleted = delete_metric_samples_before(connection, cutoff_timestamp_ms)
    finally:
        connection.close()

    if deleted:
        logger.info(
            "Retention cleanup deleted %s sample(s) older than timestamp_ms=%s",
            deleted,
            cutoff_timestamp_ms,
        )
    else:
        logger.debug(
            "Retention cleanup found no samples older than timestamp_ms=%s",
            cutoff_timestamp_ms,
        )
    return deleted


def _safe_retention_cleanup(
    db_path: Path,
    *,
    cleanup: RetentionCleanup,
) -> None:
    """在背景程序邊界捕捉清理失敗，避免維護作業中止持續採集。"""
    try:
        cleanup(db_path)
    except Exception:
        logger.exception("Retention cleanup failed; continuing collection")


def run_collector_loop(
    stop_event: threading.Event,
    *,
    db_path: Optional[Path] = None,
    interval_seconds: float = COLLECTION_INTERVAL_SECONDS,
    maintenance_interval_seconds: float = MAINTENANCE_INTERVAL_SECONDS,
    cpu_reader: CpuReader = get_cpu_info,
    memory_reader: MemoryReader = get_memory_info,
    network_reader: NetworkReader = get_network_info,
    gpu_reader: GpuReader = get_gpu_info,
    disk_io_reader: DiskIoReader = get_disk_io_info,
    clock: Clock = time.time,
    monotonic_clock: MonotonicClock = time.monotonic,
    retention_cleanup: Optional[RetentionCleanup] = None,
) -> None:
    """啟動先清理、立即採集，再等待下一次取樣；維護排程使用單調時鐘。

    廣泛例外捕捉限於背景執行邊界，單次失敗記錄後仍可繼續採集。"""
    resolved_path = resolve_metrics_db_path(db_path)
    cleanup = retention_cleanup or (
        lambda path: run_retention_cleanup(path, clock=clock)
    )

    # Startup maintenance before the first collection.
    _safe_retention_cleanup(resolved_path, cleanup=cleanup)
    next_maintenance_at = monotonic_clock() + maintenance_interval_seconds

    while not stop_event.is_set():
        if monotonic_clock() >= next_maintenance_at:
            _safe_retention_cleanup(resolved_path, cleanup=cleanup)
            next_maintenance_at = monotonic_clock() + maintenance_interval_seconds

        try:
            sample = run_collect_iteration(
                resolved_path,
                cpu_reader=cpu_reader,
                memory_reader=memory_reader,
                network_reader=network_reader,
                gpu_reader=gpu_reader,
                disk_io_reader=disk_io_reader,
                clock=clock,
            )
            logger.debug(
                "Stored metric sample timestamp_ms=%s",
                sample.timestamp_ms,
            )
        except DuplicateMetricSampleError:
            logger.warning(
                "Duplicate metric sample timestamp; skipping without overwrite",
                exc_info=True,
            )
        except Exception:
            logger.exception("Metrics collection iteration failed; will retry")

        if stop_event.wait(interval_seconds):
            break


def main(argv: Optional[list[str]] = None) -> int:
    del argv  # Reserved for future CLI flags.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    db_path = resolve_metrics_db_path()
    stop_event = threading.Event()

    def _request_shutdown(signum: int, _frame) -> None:
        logger.info("Received signal %s; shutting down collector", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _request_shutdown)
    signal.signal(signal.SIGTERM, _request_shutdown)

    logger.info("A7LAS metrics collector starting")
    logger.info("Resolved metrics database path: %s", db_path)
    logger.info("Collection interval: %s seconds", COLLECTION_INTERVAL_SECONDS)
    logger.info(
        "Raw retention: %s days; maintenance interval: %s seconds",
        RAW_RETENTION_MS // (24 * 60 * 60 * 1000),
        MAINTENANCE_INTERVAL_SECONDS,
    )

    lock = CollectorProcessLock(db_path)
    try:
        lock.acquire()
    except CollectorLockError:
        logger.error("Unable to acquire collector lock", exc_info=True)
        return 1

    try:
        # Initialize/validate schema before entering the loop.
        connection = connect_metrics_database(db_path)
        connection.close()

        run_collector_loop(stop_event, db_path=db_path)
        logger.info("A7LAS metrics collector stopped")
        return 0
    except Exception:
        logger.exception("Metrics collector failed during startup or run")
        return 1
    finally:
        lock.release()


if __name__ == "__main__":
    sys.exit(main())
