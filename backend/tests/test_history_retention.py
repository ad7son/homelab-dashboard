from __future__ import annotations

from pathlib import Path

from app.db.metrics_database import (
    MetricSampleRecord,
    connect_metrics_database,
    count_metric_samples,
    delete_metric_samples_before,
    fetch_metric_sample,
    insert_metric_sample,
)


def _sample(
    timestamp_ms: int,
    *,
    cpu_temperature_celsius: float | None = 40.0,
    network_download_bytes_per_second: float | None = 100.0,
) -> MetricSampleRecord:
    return MetricSampleRecord(
        timestamp_ms=timestamp_ms,
        cpu_usage_percent=10.0,
        cpu_temperature_celsius=cpu_temperature_celsius,
        memory_usage_percent=50.0,
        network_download_bytes_per_second=network_download_bytes_per_second,
        network_upload_bytes_per_second=50.0,
    )


def test_delete_metric_samples_before_removes_older_rows(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        insert_metric_sample(connection, _sample(1_000))
        insert_metric_sample(connection, _sample(2_000))
        insert_metric_sample(connection, _sample(3_000))

        deleted = delete_metric_samples_before(connection, 2_500)
        assert deleted == 2
        assert count_metric_samples(connection) == 1
        assert fetch_metric_sample(connection, 3_000) is not None
        assert fetch_metric_sample(connection, 1_000) is None
        assert fetch_metric_sample(connection, 2_000) is None
    finally:
        connection.close()


def test_delete_metric_samples_before_keeps_exact_cutoff(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        insert_metric_sample(connection, _sample(1_000))
        insert_metric_sample(connection, _sample(2_000))
        insert_metric_sample(connection, _sample(3_000))

        deleted = delete_metric_samples_before(connection, 2_000)
        assert deleted == 1
        assert count_metric_samples(connection) == 2
        assert fetch_metric_sample(connection, 2_000) is not None
        assert fetch_metric_sample(connection, 3_000) is not None
    finally:
        connection.close()


def test_delete_metric_samples_before_empty_db(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        deleted = delete_metric_samples_before(connection, 1_000_000)
        assert deleted == 0
        assert count_metric_samples(connection) == 0
    finally:
        connection.close()


def test_delete_metric_samples_before_ignores_optional_nulls(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        insert_metric_sample(
            connection,
            _sample(
                500,
                cpu_temperature_celsius=None,
                network_download_bytes_per_second=None,
            ),
        )
        insert_metric_sample(connection, _sample(1_500))

        deleted = delete_metric_samples_before(connection, 1_000)
        assert deleted == 1
        assert count_metric_samples(connection) == 1
        remaining = fetch_metric_sample(connection, 1_500)
        assert remaining is not None
    finally:
        connection.close()
