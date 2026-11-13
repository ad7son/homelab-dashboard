"""以替換來源及時鐘驗證背景採集、程序鎖、失敗恢復與清理排程。"""

from __future__ import annotations

import pathlib
import sys
import threading
import types

import pytest

import monitor_backend
import monitor_support

core_config = monitor_backend.module("core.config")


process_lock = monitor_backend.module("infrastructure.process_lock")

services_exceptions = monitor_backend.module("services.exceptions")
database_connection = monitor_backend.module(
    "infrastructure.database.connection"
)
metrics_repository = monitor_backend.module(
    "infrastructure.repositories.metrics_repository"
)


domain_history = monitor_backend.module("domain.history")
domain_metrics = monitor_backend.module("domain.metrics")


def test_process_lock_unexpected_failure_closes_descriptor(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """非 BUSY 的鎖定失敗也必須關閉檔案，同時保留原始例外。"""
    closed = []
    handle = types.SimpleNamespace(
        fileno=lambda: 1, close=lambda: closed.append(True)
    )

    def fail_lock(descriptor: int, operation: int) -> None:
        del descriptor, operation  # 替身只模擬失敗，不操作真實描述元。
        raise PermissionError("lock denied")

    monkeypatch.setattr(
        process_lock,
        "open",
        lambda *args, **kwargs: handle,
        raising=False,
    )
    monkeypatch.setattr(
        process_lock,
        "_load_fcntl",
        lambda: types.SimpleNamespace(LOCK_EX=1, LOCK_NB=2, flock=fail_lock),
    )
    lock = process_lock.CollectorProcessLock(tmp_path / "metrics.db")
    with pytest.raises(PermissionError, match="lock denied"):
        lock.acquire()
    assert closed == [True]


def _cpu(
    usage: float = 12.5,
    temperature: float | None = 55.0,
) -> domain_metrics.CpuInfo:
    """建立 CPU 百分比及可選攝氏溫度的來源快照。"""
    return domain_metrics.CpuInfo(
        usage_percent=usage,
        physical_cores=4,
        logical_cores=8,
        frequency=3200.0,
        temperature=temperature,
        load_average=None,
    )


def _memory(usage: float = 40.0) -> domain_metrics.MemoryInfo:
    """建立可替換使用率的記憶體來源，容量單位為 bytes。"""
    return domain_metrics.MemoryInfo(
        total=32_000_000_000,
        used=12_800_000_000,
        available=19_200_000_000,
        usage_percent=usage,
        swap=domain_metrics.SwapInfo(total=0, used=0, usage_percent=0.0),
    )


def _network(
    download: float | None = 2048.0,
    upload: float | None = 1024.0,
) -> domain_metrics.NetworkInfo:
    """建立可替換每秒速率的網路來源，None 代表尚無取樣基準。"""
    return domain_metrics.NetworkInfo(
        interface="eth0",
        ip_address="192.168.1.10",
        download_rate=download,
        upload_rate=upload,
    )


def test_collection_interval_constant() -> None:
    assert core_config.COLLECTION_INTERVAL_SECONDS == 30
    assert core_config.RAW_RETENTION_MS == 7 * 24 * 60 * 60 * 1000
    assert core_config.MAINTENANCE_INTERVAL_SECONDS == 60 * 60


def test_run_retention_cleanup_deletes_older_than_seven_days(
    tmp_path: pathlib.Path,
) -> None:
    db_path = tmp_path / "metrics.db"
    now_seconds = 2_000_000_000.0
    now_ms = int(now_seconds * 1000)
    cutoff = now_ms - core_config.RAW_RETENTION_MS

    connection = database_connection.connect_metrics_database(db_path)
    try:
        metrics_repository.insert_metric_sample(
            connection,
            domain_history.MetricSampleRecord(
                timestamp_ms=cutoff - 1,
                cpu_usage_percent=1.0,
                cpu_temperature_celsius=None,
                memory_usage_percent=1.0,
                network_download_bytes_per_second=None,
                network_upload_bytes_per_second=None,
            ),
        )
        metrics_repository.insert_metric_sample(
            connection,
            domain_history.MetricSampleRecord(
                timestamp_ms=cutoff,
                cpu_usage_percent=2.0,
                cpu_temperature_celsius=None,
                memory_usage_percent=2.0,
                network_download_bytes_per_second=None,
                network_upload_bytes_per_second=None,
            ),
        )
        metrics_repository.insert_metric_sample(
            connection,
            domain_history.MetricSampleRecord(
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

    deleted = monitor_support.run_retention_cleanup(
        db_path, clock=lambda: now_seconds
    )
    assert deleted == 1

    connection = database_connection.connect_metrics_database(db_path)
    try:
        assert metrics_repository.count_metric_samples(connection) == 2
        assert (
            metrics_repository.fetch_metric_sample(connection, cutoff - 1)
            is None
        )
        assert (
            metrics_repository.fetch_metric_sample(connection, cutoff)
            is not None
        )
        assert (
            metrics_repository.fetch_metric_sample(connection, now_ms)
            is not None
        )
    finally:
        connection.close()


def test_collect_once_stores_one_row(tmp_path: pathlib.Path) -> None:
    connection = database_connection.connect_metrics_database(
        tmp_path / "metrics.db"
    )
    try:
        sample = monitor_support.collect_once(
            connection,
            cpu_reader=lambda: _cpu(),
            memory_reader=lambda: _memory(),
            network_reader=lambda: _network(),
            clock=lambda: 1_700_000_000.5,
        )
        assert sample.timestamp_ms == 1_700_000_000_500
        assert metrics_repository.count_metric_samples(connection) == 1
        stored = metrics_repository.fetch_metric_sample(
            connection, sample.timestamp_ms
        )
        assert stored == sample
        assert stored is not None
        assert stored.cpu_usage_percent == 12.5
        assert stored.memory_usage_percent == 40.0
        assert stored.network_download_bytes_per_second == 2048.0
        assert stored.network_upload_bytes_per_second == 1024.0
    finally:
        connection.close()


def test_collect_once_preserves_optional_nulls(tmp_path: pathlib.Path) -> None:
    connection = database_connection.connect_metrics_database(
        tmp_path / "metrics.db"
    )
    try:
        sample = monitor_support.collect_once(
            connection,
            cpu_reader=lambda: _cpu(temperature=None),
            memory_reader=lambda: _memory(),
            network_reader=lambda: _network(download=None, upload=None),
            clock=lambda: 1_700_000_001.0,
        )
        stored = metrics_repository.fetch_metric_sample(
            connection, sample.timestamp_ms
        )
        assert stored is not None
        assert stored.cpu_temperature_celsius is None
        assert stored.network_download_bytes_per_second is None
        assert stored.network_upload_bytes_per_second is None
    finally:
        connection.close()


def test_run_collect_iteration_initializes_db(tmp_path: pathlib.Path) -> None:
    db_path = tmp_path / "metrics.db"
    assert not db_path.exists()

    sample = monitor_support.run_collect_iteration(
        db_path,
        cpu_reader=lambda: _cpu(),
        memory_reader=lambda: _memory(),
        network_reader=lambda: _network(),
        clock=lambda: 1_700_000_002.0,
    )
    assert db_path.exists()
    assert sample.timestamp_ms == 1_700_000_002_000

    connection = database_connection.connect_metrics_database(db_path)
    try:
        assert metrics_repository.count_metric_samples(connection) == 1
    finally:
        connection.close()


def test_failed_iteration_does_not_prevent_later_success(
    tmp_path: pathlib.Path,
) -> None:
    db_path = tmp_path / "metrics.db"
    stop_event = threading.Event()
    calls = {"n": 0}
    timestamps = iter([1_700_000_039.0, 1_700_000_040.0])

    def flaky_cpu() -> domain_metrics.CpuInfo:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("temporary collection failure")
        stop_event.set()
        return _cpu(usage=22.0)

    monitor_support.run_collector_loop(
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

    connection = database_connection.connect_metrics_database(db_path)
    try:
        assert metrics_repository.count_metric_samples(connection) == 1
        stored = metrics_repository.fetch_metric_sample(
            connection, 1_700_000_040_000
        )
        assert stored is not None
        assert stored.cpu_usage_percent == 22.0
    finally:
        connection.close()


def test_duplicate_timestamp_does_not_overwrite(tmp_path: pathlib.Path) -> None:
    connection = database_connection.connect_metrics_database(
        tmp_path / "metrics.db"
    )
    try:
        first = domain_history.MetricSampleRecord(
            timestamp_ms=1_700_000_050_000,
            cpu_usage_percent=10.0,
            cpu_temperature_celsius=40.0,
            memory_usage_percent=30.0,
            network_download_bytes_per_second=100.0,
            network_upload_bytes_per_second=50.0,
        )
        metrics_repository.insert_metric_sample(connection, first)

        with pytest.raises(services_exceptions.DuplicateMetricSampleError):
            monitor_support.collect_once(
                connection,
                cpu_reader=lambda: _cpu(usage=99.0, temperature=99.0),
                memory_reader=lambda: _memory(usage=99.0),
                network_reader=lambda: _network(download=9.0, upload=9.0),
                clock=lambda: 1_700_000_050.0,
            )

        stored = metrics_repository.fetch_metric_sample(
            connection, first.timestamp_ms
        )
        assert stored == first
        assert metrics_repository.count_metric_samples(connection) == 1
    finally:
        connection.close()


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="CollectorProcessLock uses Linux fcntl.flock",
)
def test_process_lock_exclusive_and_releasable(tmp_path: pathlib.Path) -> None:
    db_path = tmp_path / "metrics.db"
    first = process_lock.CollectorProcessLock(db_path)
    second = process_lock.CollectorProcessLock(db_path)

    first.acquire()
    try:
        with pytest.raises(process_lock.CollectorLockError):
            second.acquire()
    finally:
        first.release()

    second.acquire()
    second.release()


def test_stop_event_exits_loop_without_full_interval(
    tmp_path: pathlib.Path,
) -> None:
    db_path = tmp_path / "metrics.db"
    stop_event = threading.Event()
    started = threading.Event()

    def cpu_reader() -> domain_metrics.CpuInfo:
        started.set()
        stop_event.set()
        return _cpu()

    def run() -> None:
        monitor_support.run_collector_loop(
            stop_event,
            db_path=db_path,
            interval_seconds=30,
            cpu_reader=cpu_reader,
            memory_reader=lambda: _memory(),
            network_reader=lambda: _network(download=None, upload=None),
            clock=lambda: 1_700_000_060.0,
        )

    thread = threading.Thread(target=run)
    thread.start()
    assert started.wait(timeout=2.0)
    thread.join(timeout=2.0)
    assert not thread.is_alive()

    connection = database_connection.connect_metrics_database(db_path)
    try:
        assert metrics_repository.count_metric_samples(connection) == 1
    finally:
        connection.close()


def test_startup_maintenance_runs_before_collection(
    tmp_path: pathlib.Path,
) -> None:
    db_path = tmp_path / "metrics.db"
    stop_event = threading.Event()
    cleanup_calls: list[pathlib.Path] = []
    collect_after_cleanup = {"ok": False}

    def cleanup(path: pathlib.Path) -> int:
        cleanup_calls.append(path)
        return 0

    def cpu_reader() -> domain_metrics.CpuInfo:
        collect_after_cleanup["ok"] = len(cleanup_calls) >= 1
        stop_event.set()
        return _cpu()

    monitor_support.run_collector_loop(
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


def test_maintenance_not_run_every_collection_iteration(
    tmp_path: pathlib.Path,
) -> None:
    db_path = tmp_path / "metrics.db"
    stop_event = threading.Event()
    cleanup_calls = {"n": 0}
    collections = {"n": 0}
    timestamps = iter([1_700_000_080.0, 1_700_000_081.0, 1_700_000_082.0])

    def cleanup(_path: pathlib.Path) -> int:
        cleanup_calls["n"] += 1
        return 0

    def cpu_reader() -> domain_metrics.CpuInfo:
        collections["n"] += 1
        if collections["n"] >= 3:
            stop_event.set()
        return _cpu()

    monitor_support.run_collector_loop(
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


def test_maintenance_runs_again_after_interval(tmp_path: pathlib.Path) -> None:
    db_path = tmp_path / "metrics.db"
    stop_event = threading.Event()
    cleanup_calls = {"n": 0}
    collections = {"n": 0}
    mono = {"t": 0.0}
    timestamps = iter([1_700_000_090.0, 1_700_000_091.0])

    def cleanup(_path: pathlib.Path) -> int:
        cleanup_calls["n"] += 1
        return 0

    def cpu_reader() -> domain_metrics.CpuInfo:
        collections["n"] += 1
        if collections["n"] == 1:
            # 第一次採集後推進到維護間隔之外，驗證重新執行清理。
            mono["t"] = 100.0
        else:
            stop_event.set()
        return _cpu()

    monitor_support.run_collector_loop(
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


def test_cleanup_failure_does_not_prevent_collection(
    tmp_path: pathlib.Path,
) -> None:
    db_path = tmp_path / "metrics.db"
    stop_event = threading.Event()

    def cleanup(_path: pathlib.Path) -> int:
        raise RuntimeError("cleanup boom")

    def cpu_reader() -> domain_metrics.CpuInfo:
        stop_event.set()
        return _cpu(usage=44.0)

    monitor_support.run_collector_loop(
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

    connection = database_connection.connect_metrics_database(db_path)
    try:
        assert metrics_repository.count_metric_samples(connection) == 1
        stored = metrics_repository.fetch_metric_sample(
            connection, 1_700_000_100_000
        )
        assert stored is not None
        assert stored.cpu_usage_percent == 44.0
    finally:
        connection.close()
