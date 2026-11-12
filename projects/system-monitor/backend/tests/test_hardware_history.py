"""GPU／磁碟 I/O 的資料庫升級、採集、聚合及 API 回歸測試。"""

from monitor_backend import module as monitor_module

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
collect_once = monitor_module('collector.metrics_collector').collect_once
connect_metrics_database = monitor_module('history.database').connect_metrics_database
fetch_metric_sample = monitor_module('history.database').fetch_metric_sample
get_schema_version = monitor_module('history.database').get_schema_version
initialize_metrics_database = monitor_module('history.database').initialize_metrics_database
insert_metric_sample = monitor_module('history.database').insert_metric_sample
MetricSampleRecord = monitor_module('history.models').MetricSampleRecord
DiskIoInfo = monitor_module('machine.models').DiskIoInfo
GpuInfo = monitor_module('machine.models').GpuInfo
HistoryRange = monitor_module('history.models').HistoryRange
aggregate_metric_samples = monitor_module('history.query').aggregate_metric_samples
get_historical_metrics = monitor_module('history.query').get_historical_metrics


@pytest.fixture
def v1_database(tmp_path: Path) -> Path:
    path = tmp_path / "v1.db"
    with sqlite3.connect(path) as connection:
        connection.execute("""CREATE TABLE metric_samples (
            timestamp_ms INTEGER PRIMARY KEY, cpu_usage_percent REAL NOT NULL,
            cpu_temperature_celsius REAL, memory_usage_percent REAL NOT NULL,
            network_download_bytes_per_second REAL, network_upload_bytes_per_second REAL
        )""")
        connection.execute("INSERT INTO metric_samples VALUES (1000, 10, 40, 50, 100, 200)")
        connection.execute("PRAGMA user_version = 1")
    return path


def sample(timestamp: int, gpu=None, read=None, write=None) -> MetricSampleRecord:
    return MetricSampleRecord(timestamp, 10, None, 50, None, None, gpu, read, write)


def test_v1_upgrade_preserves_old_data_and_is_repeatable(v1_database: Path) -> None:
    for _ in range(2):
        connection = connect_metrics_database(v1_database)
        try:
            assert get_schema_version(connection) == 2
            row = fetch_metric_sample(connection, 1000)
            assert row.cpu_usage_percent == 10
            assert row.network_upload_bytes_per_second == 200
            assert row.gpu_usage_percent is None
            assert row.disk_read_bytes_per_second is None
            assert row.disk_write_bytes_per_second is None
        finally:
            connection.close()


def test_concurrent_upgrade_does_not_add_columns_twice(v1_database: Path) -> None:
    def open_database(_):
        connection = connect_metrics_database(v1_database)
        try:
            return get_schema_version(connection)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(open_database, range(2))) == [2, 2]


def test_failed_upgrade_rolls_back_columns_and_version(v1_database: Path) -> None:
    connection = sqlite3.connect(v1_database)
    attempts = []
    def authorize(action, *args):
        if action == sqlite3.SQLITE_ALTER_TABLE:
            attempts.append(1)
            if len(attempts) == 2:
                return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    try:
        connection.set_authorizer(authorize)
        with pytest.raises(sqlite3.DatabaseError):
            initialize_metrics_database(connection)
        connection.set_authorizer(None)
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert "gpu_usage_percent" not in {
            row[1] for row in connection.execute("PRAGMA table_info(metric_samples)")
        }
    finally:
        connection.close()


def test_collector_persists_zero_and_missing_values(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "collector.db")
    try:
        for timestamp, gpu, read in [(1, 0, 0), (2, None, None)]:
            collect_once(
                connection,
                cpu_reader=lambda: SimpleNamespace(usage_percent=10, temperature=None),
                memory_reader=lambda: SimpleNamespace(usage_percent=50),
                network_reader=lambda: SimpleNamespace(download_rate=None, upload_rate=None),
                gpu_reader=lambda: GpuInfo(usage_percent=gpu),
                disk_io_reader=lambda: DiskIoInfo(read_bytes_per_second=read),
                clock=lambda: timestamp,
            )
            row = fetch_metric_sample(connection, timestamp * 1000)
            assert row.gpu_usage_percent == gpu
            assert row.disk_read_bytes_per_second == read
            assert row.disk_write_bytes_per_second is None
    finally:
        connection.close()


def test_aggregation_ignores_missing_but_counts_real_zero() -> None:
    records = [sample(0), sample(30_000, 0, 0, 0), sample(60_000, 80, 1024, 2048)]
    result = aggregate_metric_samples(records, 300_000)[0]
    assert result.gpu_usage_percent == 40
    assert result.disk_read_bytes_per_second == 512
    assert result.disk_write_bytes_per_second == 1024
    empty = aggregate_metric_samples([sample(0), sample(30_000)], 300_000)[0]
    assert empty.gpu_usage_percent is None
    assert empty.disk_read_bytes_per_second is None


@pytest.mark.parametrize("history_range", list(HistoryRange))
def test_all_history_ranges_expose_new_metrics(tmp_path: Path, history_range: HistoryRange) -> None:
    path = tmp_path / "history.db"
    connection = connect_metrics_database(path)
    try:
        insert_metric_sample(connection, sample(600_000, 25, 1024, 2048))
    finally:
        connection.close()
    result = get_historical_metrics(history_range, db_path=path, now_ms=660_000)
    assert result.samples[0].gpu_usage_percent == 25
    assert result.samples[0].disk_read_bytes_per_second == 1024
    assert result.samples[0].disk_write_bytes_per_second == 2048


def test_history_api_upgrades_v1_and_keeps_missing_values(v1_database: Path, monkeypatch) -> None:
    monkeypatch.setenv("A7LAS_METRICS_DB_PATH", str(v1_database))
    monkeypatch.setattr(monitor_module("history.query").time, "time", lambda: 2)
    response = TestClient(app).get("/api/system-monitor/history", params={"range": "15m"})
    assert response.status_code == 200
    row = response.json()["samples"][0]
    assert row["cpu_usage_percent"] == 10
    assert row["gpu_usage_percent"] is None
    assert row["disk_read_bytes_per_second"] is None
    assert row["disk_write_bytes_per_second"] is None



def test_wal_configuration_retries_only_busy_errors(monkeypatch):
    import sqlite3
    database = monitor_module('history.database')

    class Connection:
        calls = 0
        def execute(self, statement):
            if statement != 'PRAGMA journal_mode = WAL':
                return
            self.calls += 1
            if self.calls == 1:
                error = sqlite3.OperationalError('database is locked')
                error.sqlite_errorcode = sqlite3.SQLITE_BUSY
                raise error

    monkeypatch.setattr(database.time, 'sleep', lambda _: None)
    connection = Connection()
    database._configure_connection(connection)
    assert connection.calls == 2


def test_wal_configuration_does_not_hide_other_errors():
    import sqlite3
    database = monitor_module('history.database')

    class Connection:
        def execute(self, statement):
            if statement == 'PRAGMA journal_mode = WAL':
                raise sqlite3.OperationalError('disk I/O error')

    with pytest.raises(sqlite3.OperationalError, match='disk I/O error'):
        database._configure_connection(Connection())
