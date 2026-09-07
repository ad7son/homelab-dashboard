from __future__ import annotations

from pathlib import Path

import pytest
import sqlite3

from app.db.metrics_database import (
    CURRENT_SCHEMA_VERSION,
    ENV_METRICS_DB_PATH,
    DuplicateMetricSampleError,
    MetricSampleRecord,
    UnsupportedSchemaVersionError,
    connect_metrics_database,
    count_metric_samples,
    default_metrics_db_path,
    fetch_metric_sample,
    get_journal_mode,
    get_schema_version,
    insert_metric_sample,
    resolve_metrics_db_path,
)

PRODUCTION_DB_PATH = Path("/srv/a7las/data/metrics.db")


def _sample(
    timestamp_ms: int,
    *,
    cpu_temperature_celsius: float | None = 42.5,
    network_download_bytes_per_second: float | None = 1024.0,
    network_upload_bytes_per_second: float | None = 512.0,
) -> MetricSampleRecord:
    return MetricSampleRecord(
        timestamp_ms=timestamp_ms,
        cpu_usage_percent=18.5,
        cpu_temperature_celsius=cpu_temperature_celsius,
        memory_usage_percent=41.0,
        network_download_bytes_per_second=network_download_bytes_per_second,
        network_upload_bytes_per_second=network_upload_bytes_per_second,
    )


def test_new_db_initializes_successfully(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    connection = connect_metrics_database(db_path)
    try:
        assert db_path.exists()
        assert get_schema_version(connection) == CURRENT_SCHEMA_VERSION
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='metric_samples'"
        ).fetchall()
        assert len(tables) == 1
    finally:
        connection.close()


def test_initialization_is_idempotent_and_preserves_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    connection = connect_metrics_database(db_path)
    try:
        insert_metric_sample(connection, _sample(1_700_000_000_000))
        assert count_metric_samples(connection) == 1
    finally:
        connection.close()

    connection = connect_metrics_database(db_path)
    try:
        assert get_schema_version(connection) == CURRENT_SCHEMA_VERSION
        assert count_metric_samples(connection) == 1
        stored = fetch_metric_sample(connection, 1_700_000_000_000)
        assert stored is not None
        assert stored.cpu_usage_percent == 18.5
    finally:
        connection.close()


def test_insert_stores_required_values(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        sample = _sample(1_700_000_000_100)
        insert_metric_sample(connection, sample)
        stored = fetch_metric_sample(connection, sample.timestamp_ms)
        assert stored == sample
    finally:
        connection.close()


def test_optional_none_values_are_stored_as_sql_null(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        sample = _sample(
            1_700_000_000_200,
            cpu_temperature_celsius=None,
            network_download_bytes_per_second=None,
            network_upload_bytes_per_second=None,
        )
        insert_metric_sample(connection, sample)
        stored = fetch_metric_sample(connection, sample.timestamp_ms)
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


def test_duplicate_timestamp_is_not_silently_overwritten(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        first = _sample(1_700_000_000_300, cpu_temperature_celsius=40.0)
        insert_metric_sample(connection, first)

        duplicate = MetricSampleRecord(
            timestamp_ms=first.timestamp_ms,
            cpu_usage_percent=99.0,
            cpu_temperature_celsius=99.0,
            memory_usage_percent=99.0,
            network_download_bytes_per_second=1.0,
            network_upload_bytes_per_second=2.0,
        )
        with pytest.raises(DuplicateMetricSampleError):
            insert_metric_sample(connection, duplicate)

        stored = fetch_metric_sample(connection, first.timestamp_ms)
        assert stored == first
        assert count_metric_samples(connection) == 1
    finally:
        connection.close()


def test_wal_mode_is_enabled(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        assert get_journal_mode(connection) == "wal"
    finally:
        connection.close()


def test_path_override_via_env_variable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_db = tmp_path / "env-metrics.db"
    monkeypatch.setenv(ENV_METRICS_DB_PATH, str(env_db))

    resolved = resolve_metrics_db_path()
    assert resolved == env_db.resolve()

    connection = connect_metrics_database()
    try:
        assert env_db.exists()
        assert get_schema_version(connection) == CURRENT_SCHEMA_VERSION
    finally:
        connection.close()


def test_default_and_test_paths_never_use_production_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ENV_METRICS_DB_PATH, raising=False)

    default_path = default_metrics_db_path().resolve()
    assert default_path != PRODUCTION_DB_PATH.resolve()
    assert default_path.name == "metrics.db"
    assert default_path.parent.name == "data"

    test_db = tmp_path / "metrics.db"
    resolved = resolve_metrics_db_path(test_db)
    assert resolved == test_db.resolve()
    assert resolved != PRODUCTION_DB_PATH.resolve()


def test_unsupported_schema_version_fails(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    connection = sqlite3.connect(str(db_path))
    try:
        connection.execute("PRAGMA user_version = 99")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(UnsupportedSchemaVersionError):
        connect_metrics_database(db_path)
