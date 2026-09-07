"""Independent A7LAS historical metrics collector.

Run with:
    python -m app.collector.metrics_collector
"""

from __future__ import annotations

import fcntl
import logging
import signal
import sqlite3
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from app.db.metrics_database import (
    DuplicateMetricSampleError,
    MetricSampleRecord,
    connect_metrics_database,
    insert_metric_sample,
    resolve_metrics_db_path,
)
from app.schemas.cpu import CpuInfo
from app.schemas.memory import MemoryInfo
from app.schemas.network import NetworkInfo
from app.services.cpu_service import get_cpu_info
from app.services.memory_service import get_memory_info
from app.services.network_service import get_network_info

COLLECTION_INTERVAL_SECONDS = 30

logger = logging.getLogger("a7las.metrics_collector")

CpuReader = Callable[[], CpuInfo]
MemoryReader = Callable[[], MemoryInfo]
NetworkReader = Callable[[], NetworkInfo]
Clock = Callable[[], float]


class CollectorLockError(RuntimeError):
    """Raised when another collector already holds the process lock."""


class CollectorProcessLock:
    """Exclusive non-blocking flock for a single collector writer per database."""

    def __init__(self, db_path: Path) -> None:
        self.lock_path = Path(f"{db_path}.collector.lock")
        self._file = None

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.lock_path, "a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
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
            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
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
    clock: Clock = time.time,
) -> MetricSampleRecord:
    """Collect one historical sample and persist it."""
    cpu = cpu_reader()
    memory = memory_reader()
    network = network_reader()
    timestamp_ms = int(clock() * 1000)

    sample = MetricSampleRecord(
        timestamp_ms=timestamp_ms,
        cpu_usage_percent=float(cpu.usage_percent),
        cpu_temperature_celsius=cpu.temperature,
        memory_usage_percent=float(memory.usage_percent),
        network_download_bytes_per_second=network.download_rate,
        network_upload_bytes_per_second=network.upload_rate,
    )
    insert_metric_sample(connection, sample)
    return sample


def run_collect_iteration(
    db_path: Path,
    *,
    cpu_reader: CpuReader = get_cpu_info,
    memory_reader: MemoryReader = get_memory_info,
    network_reader: NetworkReader = get_network_info,
    clock: Clock = time.time,
) -> MetricSampleRecord:
    """Open a short-lived DB connection and collect/store one sample."""
    connection = connect_metrics_database(db_path)
    try:
        return collect_once(
            connection,
            cpu_reader=cpu_reader,
            memory_reader=memory_reader,
            network_reader=network_reader,
            clock=clock,
        )
    finally:
        connection.close()


def run_collector_loop(
    stop_event: threading.Event,
    *,
    db_path: Optional[Path] = None,
    interval_seconds: float = COLLECTION_INTERVAL_SECONDS,
    cpu_reader: CpuReader = get_cpu_info,
    memory_reader: MemoryReader = get_memory_info,
    network_reader: NetworkReader = get_network_info,
    clock: Clock = time.time,
) -> None:
    """
    Collect immediately, then wait approximately interval_seconds between samples.

    Broad Exception handling is intentionally limited to this daemon boundary.
    """
    resolved_path = resolve_metrics_db_path(db_path)

    while not stop_event.is_set():
        try:
            sample = run_collect_iteration(
                resolved_path,
                cpu_reader=cpu_reader,
                memory_reader=memory_reader,
                network_reader=network_reader,
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
