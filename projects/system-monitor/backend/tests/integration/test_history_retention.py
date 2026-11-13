"""驗證保留政策只刪除嚴格早於截止時間的樣本。"""

from __future__ import annotations

import pathlib

import monitor_backend

database_connection = monitor_backend.module(
    "infrastructure.database.connection"
)
metrics_repository = monitor_backend.module(
    "infrastructure.repositories.metrics_repository"
)


domain_history = monitor_backend.module("domain.history")


def _sample(
    timestamp_ms: int,
    *,
    cpu_temperature_celsius: float | None = 40.0,
    network_download_bytes_per_second: float | None = 100.0,
) -> domain_history.MetricSampleRecord:
    """建立指定 Unix 毫秒時間的樣本，以驗證保留期間的精確邊界。"""
    return domain_history.MetricSampleRecord(
        timestamp_ms=timestamp_ms,
        cpu_usage_percent=10.0,
        cpu_temperature_celsius=cpu_temperature_celsius,
        memory_usage_percent=50.0,
        network_download_bytes_per_second=network_download_bytes_per_second,
        network_upload_bytes_per_second=50.0,
    )


def test_delete_metric_samples_before_removes_older_rows(
    tmp_path: pathlib.Path,
) -> None:
    connection = database_connection.connect_metrics_database(
        tmp_path / "metrics.db"
    )
    try:
        metrics_repository.insert_metric_sample(connection, _sample(1_000))
        metrics_repository.insert_metric_sample(connection, _sample(2_000))
        metrics_repository.insert_metric_sample(connection, _sample(3_000))

        deleted = metrics_repository.delete_metric_samples_before(
            connection, 2_500
        )
        assert deleted == 2
        assert metrics_repository.count_metric_samples(connection) == 1
        assert (
            metrics_repository.fetch_metric_sample(connection, 3_000)
            is not None
        )
        assert metrics_repository.fetch_metric_sample(connection, 1_000) is None
        assert metrics_repository.fetch_metric_sample(connection, 2_000) is None
    finally:
        connection.close()


def test_delete_metric_samples_before_keeps_exact_cutoff(
    tmp_path: pathlib.Path,
) -> None:
    connection = database_connection.connect_metrics_database(
        tmp_path / "metrics.db"
    )
    try:
        metrics_repository.insert_metric_sample(connection, _sample(1_000))
        metrics_repository.insert_metric_sample(connection, _sample(2_000))
        metrics_repository.insert_metric_sample(connection, _sample(3_000))

        deleted = metrics_repository.delete_metric_samples_before(
            connection, 2_000
        )
        assert deleted == 1
        assert metrics_repository.count_metric_samples(connection) == 2
        assert (
            metrics_repository.fetch_metric_sample(connection, 2_000)
            is not None
        )
        assert (
            metrics_repository.fetch_metric_sample(connection, 3_000)
            is not None
        )
    finally:
        connection.close()


def test_delete_metric_samples_before_empty_db(tmp_path: pathlib.Path) -> None:
    connection = database_connection.connect_metrics_database(
        tmp_path / "metrics.db"
    )
    try:
        deleted = metrics_repository.delete_metric_samples_before(
            connection, 1_000_000
        )
        assert deleted == 0
        assert metrics_repository.count_metric_samples(connection) == 0
    finally:
        connection.close()


def test_delete_metric_samples_before_ignores_optional_nulls(
    tmp_path: pathlib.Path,
) -> None:
    connection = database_connection.connect_metrics_database(
        tmp_path / "metrics.db"
    )
    try:
        metrics_repository.insert_metric_sample(
            connection,
            _sample(
                500,
                cpu_temperature_celsius=None,
                network_download_bytes_per_second=None,
            ),
        )
        metrics_repository.insert_metric_sample(connection, _sample(1_500))

        deleted = metrics_repository.delete_metric_samples_before(
            connection, 1_000
        )
        assert deleted == 1
        assert metrics_repository.count_metric_samples(connection) == 1
        remaining = metrics_repository.fetch_metric_sample(connection, 1_500)
        assert remaining is not None
    finally:
        connection.close()
