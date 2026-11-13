"""以暫存資料庫驗證建表、版本、WAL、唯一時間戳與路徑解析。"""

from __future__ import annotations

import pathlib
import sqlite3

import pytest

from app.modules import loader
import monitor_backend

migration_runner = monitor_backend.module(
    "infrastructure.database.migration_runner"
)
core_config = monitor_backend.module("core.config")
services_exceptions = monitor_backend.module("services.exceptions")

database_connection = monitor_backend.module(
    "infrastructure.database.connection"
)
metrics_repository = monitor_backend.module(
    "infrastructure.repositories.metrics_repository"
)


domain_history = monitor_backend.module("domain.history")

PRODUCTION_DB_PATH = pathlib.Path("/srv/a7las/data/metrics.db")


def _sample(
    timestamp_ms: int,
    *,
    cpu_temperature_celsius: float | None = 42.5,
    network_download_bytes_per_second: float | None = 1024.0,
    network_upload_bytes_per_second: float | None = 512.0,
) -> domain_history.MetricSampleRecord:
    """建立固定有效指標的樣本；時間戳為 Unix 毫秒，None 應儲存為 NULL。"""
    return domain_history.MetricSampleRecord(
        timestamp_ms=timestamp_ms,
        cpu_usage_percent=18.5,
        cpu_temperature_celsius=cpu_temperature_celsius,
        memory_usage_percent=41.0,
        network_download_bytes_per_second=network_download_bytes_per_second,
        network_upload_bytes_per_second=network_upload_bytes_per_second,
    )


def test_new_db_initializes_successfully(tmp_path: pathlib.Path) -> None:
    db_path = tmp_path / "metrics.db"
    connection = database_connection.connect_metrics_database(db_path)
    try:
        assert db_path.exists()
        assert (
            database_connection.get_schema_version(connection)
            == migration_runner.CURRENT_SCHEMA_VERSION
        )
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='metric_samples'"
        ).fetchall()
        assert len(tables) == 1
    finally:
        connection.close()


def test_initialization_is_idempotent_and_preserves_rows(
    tmp_path: pathlib.Path,
) -> None:
    db_path = tmp_path / "metrics.db"
    connection = database_connection.connect_metrics_database(db_path)
    try:
        metrics_repository.insert_metric_sample(
            connection, _sample(1_700_000_000_000)
        )
        assert metrics_repository.count_metric_samples(connection) == 1
    finally:
        connection.close()

    connection = database_connection.connect_metrics_database(db_path)
    try:
        assert (
            database_connection.get_schema_version(connection)
            == migration_runner.CURRENT_SCHEMA_VERSION
        )
        assert metrics_repository.count_metric_samples(connection) == 1
        stored = metrics_repository.fetch_metric_sample(
            connection, 1_700_000_000_000
        )
        assert stored is not None
        assert stored.cpu_usage_percent == 18.5
    finally:
        connection.close()


def test_insert_stores_required_values(tmp_path: pathlib.Path) -> None:
    connection = database_connection.connect_metrics_database(
        tmp_path / "metrics.db"
    )
    try:
        sample = _sample(1_700_000_000_100)
        metrics_repository.insert_metric_sample(connection, sample)
        stored = metrics_repository.fetch_metric_sample(
            connection, sample.timestamp_ms
        )
        assert stored == sample
    finally:
        connection.close()


def test_optional_none_values_are_stored_as_sql_null(
    tmp_path: pathlib.Path,
) -> None:
    connection = database_connection.connect_metrics_database(
        tmp_path / "metrics.db"
    )
    try:
        sample = _sample(
            1_700_000_000_200,
            cpu_temperature_celsius=None,
            network_download_bytes_per_second=None,
            network_upload_bytes_per_second=None,
        )
        metrics_repository.insert_metric_sample(connection, sample)
        stored = metrics_repository.fetch_metric_sample(
            connection, sample.timestamp_ms
        )
        assert stored is not None
        assert stored.cpu_temperature_celsius is None
        assert stored.network_download_bytes_per_second is None
        assert stored.network_upload_bytes_per_second is None

        row = connection.execute(
            """
            SELECT
                cpu_temperature_celsius,
                network_download_bytes_per_second,
                network_upload_bytes_per_second
            FROM metric_samples
            WHERE timestamp_ms = ?
            """,
            (sample.timestamp_ms,),
        ).fetchone()
        assert row["cpu_temperature_celsius"] is None
        assert row["network_download_bytes_per_second"] is None
        assert row["network_upload_bytes_per_second"] is None
    finally:
        connection.close()


def test_duplicate_timestamp_is_not_silently_overwritten(
    tmp_path: pathlib.Path,
) -> None:
    connection = database_connection.connect_metrics_database(
        tmp_path / "metrics.db"
    )
    try:
        first = _sample(1_700_000_000_300, cpu_temperature_celsius=40.0)
        metrics_repository.insert_metric_sample(connection, first)

        duplicate = domain_history.MetricSampleRecord(
            timestamp_ms=first.timestamp_ms,
            cpu_usage_percent=99.0,
            cpu_temperature_celsius=99.0,
            memory_usage_percent=99.0,
            network_download_bytes_per_second=1.0,
            network_upload_bytes_per_second=2.0,
        )
        with pytest.raises(services_exceptions.DuplicateMetricSampleError):
            metrics_repository.insert_metric_sample(connection, duplicate)

        stored = metrics_repository.fetch_metric_sample(
            connection, first.timestamp_ms
        )
        assert stored == first
        assert metrics_repository.count_metric_samples(connection) == 1
    finally:
        connection.close()


def test_wal_mode_is_enabled(tmp_path: pathlib.Path) -> None:
    connection = database_connection.connect_metrics_database(
        tmp_path / "metrics.db"
    )
    try:
        assert database_connection.get_journal_mode(connection) == "wal"
    finally:
        connection.close()


def test_path_override_via_env_variable(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_db = tmp_path / "env-metrics.db"
    monkeypatch.setenv(core_config.ENV_METRICS_DB_PATH, str(env_db))

    resolved = core_config.resolve_metrics_db_path()
    assert resolved == env_db.resolve()

    connection = database_connection.connect_metrics_database()
    try:
        assert env_db.exists()
        assert (
            database_connection.get_schema_version(connection)
            == migration_runner.CURRENT_SCHEMA_VERSION
        )
    finally:
        connection.close()


def test_default_and_test_paths_never_use_production_path(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(core_config.ENV_METRICS_DB_PATH, raising=False)

    default_path = core_config.default_metrics_db_path().resolve()
    repository_root = loader.default_repository_root()
    assert (
        default_path
        == (repository_root / "backend" / "data" / "metrics.db").resolve()
    )
    assert (repository_root / "backend" / "app" / "main.py").is_file()
    assert default_path != PRODUCTION_DB_PATH.resolve()
    assert default_path.name == "metrics.db"
    assert default_path.parent.name == "data"

    test_db = tmp_path / "metrics.db"
    resolved = core_config.resolve_metrics_db_path(test_db)
    assert resolved == test_db.resolve()
    assert resolved != PRODUCTION_DB_PATH.resolve()


def test_unsupported_schema_version_fails(tmp_path: pathlib.Path) -> None:
    db_path = tmp_path / "metrics.db"
    connection = sqlite3.connect(str(db_path))
    try:
        connection.execute("PRAGMA user_version = 99")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(migration_runner.UnsupportedSchemaVersionError):
        database_connection.connect_metrics_database(db_path)
