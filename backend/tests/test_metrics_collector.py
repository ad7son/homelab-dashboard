from __future__ import annotations

from pathlib import Path
from threading import Event, Thread

import pytest

from app.collector.metrics_collector import (
    COLLECTION_INTERVAL_SECONDS,
    MAINTENANCE_INTERVAL_SECONDS,
    RAW_RETENTION_MS,
    CollectorLockError,
    CollectorProcessLock,
    collect_once,
    run_collect_iteration,
    run_collector_loop,
    run_retention_cleanup,
)
from app.db.metrics_database import (
    DuplicateMetricSampleError,
    MetricSampleRecord,
    connect_metrics_database,
    count_metric_samples,
    fetch_metric_sample,
    insert_metric_sample,
)
from app.schemas.cpu import CpuInfo
from app.schemas.memory import MemoryInfo, SwapInfo
from app.schemas.network import NetworkInfo


def _cpu(
    usage: float = 12.5,
    temperature: float | None = 55.0,
) -> CpuInfo:
    return CpuInfo(
        usage_percent=usage,
        physical_cores=4,
        logical_cores=8,
        frequency=3200.0,
        temperature=temperature,
        load_average=None,
    )


def _memory(usage: float = 40.0) -> MemoryInfo:
    return MemoryInfo(
        total=32_000_000_000,
        used=12_800_000_000,
        available=19_200_000_000,
        usage_percent=usage,
        swap=SwapInfo(total=0, used=0, usage_percent=0.0),
    )


def _network(
    download: float | None = 2048.0,
    upload: float | None = 1024.0,
) -> NetworkInfo:
    return NetworkInfo(
        interface="eth0",
        ip_address="192.168.1.10",
        download_rate=download,
        upload_rate=upload,
    )


def test_collection_interval_constant() -> None:
    assert COLLECTION_INTERVAL_SECONDS == 30
    assert RAW_RETENTION_MS == 7 * 24 * 60 * 60 * 1000
    assert MAINTENANCE_INTERVAL_SECONDS == 60 * 60


def test_run_retention_cleanup_deletes_older_than_seven_days(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    now_seconds = 2_000_000_000.0
    now_ms = int(now_seconds * 1000)
    cutoff = now_ms - RAW_RETENTION_MS

    connection = connect_metrics_database(db_path)
    try:
        insert_metric_sample(
            connection,
            MetricSampleRecord(
                timestamp_ms=cutoff - 1,
                cpu_usage_percent=1.0,
                cpu_temperature_celsius=None,
                memory_usage_percent=1.0,
                network_download_bytes_per_second=None,
                network_upload_bytes_per_second=None,
            ),
        )
        insert_metric_sample(
            connection,
            MetricSampleRecord(
                timestamp_ms=cutoff,
                cpu_usage_percent=2.0,
                cpu_temperature_celsius=None,
                memory_usage_percent=2.0,
                network_download_bytes_per_second=None,
                network_upload_bytes_per_second=None,
            ),
        )
        insert_metric_sample(
            connection,
            MetricSampleRecord(
                timestamp_ms=now_ms,
                cpu_usage_percent=3.0,
                cpu_temperature_celsius=None,
                memory_usage_percent=3.0,
                network_download_bytes_per_second=None,
                network_upload_bytes_per_second=None,
            ),
        )
    finally:
        connection.close()

    deleted = run_retention_cleanup(db_path, clock=lambda: now_seconds)
    assert deleted == 1

    connection = connect_metrics_database(db_path)
    try:
        assert count_metric_samples(connection) == 2
        assert fetch_metric_sample(connection, cutoff - 1) is None
        assert fetch_metric_sample(connection, cutoff) is not None
        assert fetch_metric_sample(connection, now_ms) is not None
    finally:
        connection.close()


def test_collect_once_stores_one_row(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        sample = collect_once(
            connection,
            cpu_reader=lambda: _cpu(),
            memory_reader=lambda: _memory(),
            network_reader=lambda: _network(),
            clock=lambda: 1_700_000_000.5,
        )
        assert sample.timestamp_ms == 1_700_000_000_500
        assert count_metric_samples(connection) == 1
        stored = fetch_metric_sample(connection, sample.timestamp_ms)
        assert stored == sample
        assert stored is not None
        assert stored.cpu_usage_percent == 12.5
        assert stored.memory_usage_percent == 40.0
        assert stored.network_download_bytes_per_second == 2048.0
        assert stored.network_upload_bytes_per_second == 1024.0
    finally:
        connection.close()


def test_collect_once_preserves_optional_nulls(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        sample = collect_once(
            connection,
            cpu_reader=lambda: _cpu(temperature=None),
            memory_reader=lambda: _memory(),
            network_reader=lambda: _network(download=None, upload=None),
            clock=lambda: 1_700_000_001.0,
        )
        stored = fetch_metric_sample(connection, sample.timestamp_ms)
        assert stored is not None
        assert stored.cpu_temperature_celsius is None
        assert stored.network_download_bytes_per_second is None
        assert stored.network_upload_bytes_per_second is None
    finally:
        connection.close()


def test_run_collect_iteration_initializes_db(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    assert not db_path.exists()

    sample = run_collect_iteration(
        db_path,
        cpu_reader=lambda: _cpu(),
        memory_reader=lambda: _memory(),
        network_reader=lambda: _network(),
        clock=lambda: 1_700_000_002.0,
    )
    assert db_path.exists()
    assert sample.timestamp_ms == 1_700_000_002_000

    connection = connect_metrics_database(db_path)
    try:
        assert count_metric_samples(connection) == 1
    finally:
        connection.close()


def test_failed_iteration_does_not_prevent_later_success(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    stop_event = Event()
    calls = {"n": 0}
    timestamps = iter([1_700_000_039.0, 1_700_000_040.0])

    def flaky_cpu() -> CpuInfo:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("temporary collection failure")
        stop_event.set()
        return _cpu(usage=22.0)

    run_collector_loop(
        stop_event,
        db_path=db_path,
        interval_seconds=0.01,
        maintenance_interval_seconds=10_000,
        cpu_reader=flaky_cpu,
        memory_reader=lambda: _memory(),
        network_reader=lambda: _network(),
        clock=lambda: next(timestamps),
        monotonic_clock=lambda: 0.0,
    )

    connection = connect_metrics_database(db_path)
    try:
        assert count_metric_samples(connection) == 1
        stored = fetch_metric_sample(connection, 1_700_000_040_000)
        assert stored is not None
        assert stored.cpu_usage_percent == 22.0
    finally:
        connection.close()


def test_duplicate_timestamp_does_not_overwrite(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        first = MetricSampleRecord(
            timestamp_ms=1_700_000_050_000,
            cpu_usage_percent=10.0,
            cpu_temperature_celsius=40.0,
            memory_usage_percent=30.0,
            network_download_bytes_per_second=100.0,
            network_upload_bytes_per_second=50.0,
        )
        insert_metric_sample(connection, first)

        with pytest.raises(DuplicateMetricSampleError):
            collect_once(
                connection,
                cpu_reader=lambda: _cpu(usage=99.0, temperature=99.0),
                memory_reader=lambda: _memory(usage=99.0),
                network_reader=lambda: _network(download=9.0, upload=9.0),
                clock=lambda: 1_700_000_050.0,
            )

        stored = fetch_metric_sample(connection, first.timestamp_ms)
        assert stored == first
        assert count_metric_samples(connection) == 1
    finally:
        connection.close()


def test_process_lock_exclusive_and_releasable(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    first = CollectorProcessLock(db_path)
    second = CollectorProcessLock(db_path)

    first.acquire()
    try:
        with pytest.raises(CollectorLockError):
            second.acquire()
    finally:
        first.release()

    second.acquire()
    second.release()


def test_stop_event_exits_loop_without_full_interval(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    stop_event = Event()
    started = Event()

    def cpu_reader() -> CpuInfo:
        started.set()
        stop_event.set()
        return _cpu()

    def run() -> None:
        run_collector_loop(
            stop_event,
            db_path=db_path,
            interval_seconds=30,
            cpu_reader=cpu_reader,
            memory_reader=lambda: _memory(),
            network_reader=lambda: _network(download=None, upload=None),
            clock=lambda: 1_700_000_060.0,
        )

    thread = Thread(target=run)
    thread.start()
    assert started.wait(timeout=2.0)
    thread.join(timeout=2.0)
    assert not thread.is_alive()

    connection = connect_metrics_database(db_path)
    try:
        assert count_metric_samples(connection) == 1
    finally:
        connection.close()


def test_startup_maintenance_runs_before_collection(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    stop_event = Event()
    cleanup_calls: list[Path] = []
    collect_after_cleanup = {"ok": False}

    def cleanup(path: Path) -> int:
        cleanup_calls.append(path)
        return 0

    def cpu_reader() -> CpuInfo:
        collect_after_cleanup["ok"] = len(cleanup_calls) >= 1
        stop_event.set()
        return _cpu()

    run_collector_loop(
        stop_event,
        db_path=db_path,
        interval_seconds=0.01,
        maintenance_interval_seconds=10_000,
        cpu_reader=cpu_reader,
        memory_reader=lambda: _memory(),
        network_reader=lambda: _network(),
        clock=lambda: 1_700_000_070.0,
        monotonic_clock=lambda: 0.0,
        retention_cleanup=cleanup,
    )

    assert len(cleanup_calls) == 1
    assert collect_after_cleanup["ok"] is True


def test_maintenance_not_run_every_collection_iteration(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    stop_event = Event()
    cleanup_calls = {"n": 0}
    collections = {"n": 0}
    timestamps = iter([1_700_000_080.0, 1_700_000_081.0, 1_700_000_082.0])

    def cleanup(_path: Path) -> int:
        cleanup_calls["n"] += 1
        return 0

    def cpu_reader() -> CpuInfo:
        collections["n"] += 1
        if collections["n"] >= 3:
            stop_event.set()
        return _cpu()

    run_collector_loop(
        stop_event,
        db_path=db_path,
        interval_seconds=0.01,
        maintenance_interval_seconds=10_000,
        cpu_reader=cpu_reader,
        memory_reader=lambda: _memory(),
        network_reader=lambda: _network(),
        clock=lambda: next(timestamps),
        monotonic_clock=lambda: 0.0,
        retention_cleanup=cleanup,
    )

    assert collections["n"] == 3
    assert cleanup_calls["n"] == 1


def test_maintenance_runs_again_after_interval(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    stop_event = Event()
    cleanup_calls = {"n": 0}
    collections = {"n": 0}
    mono = {"t": 0.0}
    timestamps = iter([1_700_000_090.0, 1_700_000_091.0])

    def cleanup(_path: Path) -> int:
        cleanup_calls["n"] += 1
        return 0

    def cpu_reader() -> CpuInfo:
        collections["n"] += 1
        if collections["n"] == 1:
            # After first collection wait, advance past maintenance interval.
            mono["t"] = 100.0
        else:
            stop_event.set()
        return _cpu()

    run_collector_loop(
        stop_event,
        db_path=db_path,
        interval_seconds=0.01,
        maintenance_interval_seconds=50.0,
        cpu_reader=cpu_reader,
        memory_reader=lambda: _memory(),
        network_reader=lambda: _network(),
        clock=lambda: next(timestamps),
        monotonic_clock=lambda: mono["t"],
        retention_cleanup=cleanup,
    )

    assert collections["n"] == 2
    assert cleanup_calls["n"] == 2


def test_cleanup_failure_does_not_prevent_collection(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    stop_event = Event()

    def cleanup(_path: Path) -> int:
        raise RuntimeError("cleanup boom")

    def cpu_reader() -> CpuInfo:
        stop_event.set()
        return _cpu(usage=44.0)

    run_collector_loop(
        stop_event,
        db_path=db_path,
        interval_seconds=0.01,
        maintenance_interval_seconds=10_000,
        cpu_reader=cpu_reader,
        memory_reader=lambda: _memory(),
        network_reader=lambda: _network(),
        clock=lambda: 1_700_000_100.0,
        monotonic_clock=lambda: 0.0,
        retention_cleanup=cleanup,
    )

    connection = connect_metrics_database(db_path)
    try:
        assert count_metric_samples(connection) == 1
        stored = fetch_metric_sample(connection, 1_700_000_100_000)
        assert stored is not None
        assert stored.cpu_usage_percent == 44.0
    finally:
        connection.close()
