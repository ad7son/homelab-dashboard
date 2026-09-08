from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.metrics_database import (
    ENV_METRICS_DB_PATH,
    MetricSampleRecord,
    connect_metrics_database,
    insert_metric_sample,
)
from app.main import app
from app.services import history_service

client = TestClient(app)


@pytest.fixture
def history_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "metrics.db"
    monkeypatch.setenv(ENV_METRICS_DB_PATH, str(db_path))
    return db_path


@pytest.mark.parametrize("range_value", ["15m", "1h", "24h", "7d"])
def test_history_ranges_return_200(history_db: Path, range_value: str) -> None:
    response = client.get(f"/api/history?range={range_value}")
    assert response.status_code == 200
    data = response.json()
    assert data["range"] == range_value
    assert "start_timestamp_ms" in data
    assert "end_timestamp_ms" in data
    assert isinstance(data["samples"], list)
    assert data["samples"] == []
    assert data["end_timestamp_ms"] >= data["start_timestamp_ms"]


def test_invalid_history_range_returns_422(history_db: Path) -> None:
    response = client.get("/api/history?range=3h")
    assert response.status_code == 422


def test_history_empty_db_returns_empty_samples(history_db: Path) -> None:
    response = client.get("/api/history?range=1h")
    assert response.status_code == 200
    assert response.json()["samples"] == []


def test_history_null_fields_serialize_as_json_null(
    history_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now_ms = 2_000_000_000_000
    monkeypatch.setattr(history_service.time, "time", lambda: now_ms / 1000)

    connection = connect_metrics_database(history_db)
    try:
        insert_metric_sample(
            connection,
            MetricSampleRecord(
                timestamp_ms=now_ms - 1_000,
                cpu_usage_percent=15.0,
                cpu_temperature_celsius=None,
                memory_usage_percent=33.0,
                network_download_bytes_per_second=None,
                network_upload_bytes_per_second=None,
            ),
        )
    finally:
        connection.close()

    response = client.get("/api/history?range=15m")
    assert response.status_code == 200
    samples = response.json()["samples"]
    assert len(samples) == 1
    assert samples[0]["cpu_temperature_celsius"] is None
    assert samples[0]["network_download_bytes_per_second"] is None
    assert samples[0]["network_upload_bytes_per_second"] is None


def test_history_db_failure_returns_503_without_raw_detail(
    history_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_db_error(*_args, **_kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(history_service, "connect_metrics_database", _raise_db_error)

    response = client.get("/api/history?range=15m")
    assert response.status_code == 503
    body = response.json()
    assert body["detail"] == "Historical metrics database unavailable"
    assert "disk I/O error" not in str(body)


def test_overview_still_works_with_history_env(history_db: Path) -> None:
    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "memory" in data


def test_history_24h_response_is_downsampled(
    history_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now_ms = 3_000_000_000_000
    monkeypatch.setattr(history_service.time, "time", lambda: now_ms / 1000)

    connection = connect_metrics_database(history_db)
    try:
        insert_metric_sample(
            connection,
            MetricSampleRecord(
                timestamp_ms=now_ms - 4 * 60 * 1000,
                cpu_usage_percent=10.0,
                cpu_temperature_celsius=None,
                memory_usage_percent=20.0,
                network_download_bytes_per_second=None,
                network_upload_bytes_per_second=None,
            ),
        )
        insert_metric_sample(
            connection,
            MetricSampleRecord(
                timestamp_ms=now_ms - 3 * 60 * 1000,
                cpu_usage_percent=30.0,
                cpu_temperature_celsius=None,
                memory_usage_percent=40.0,
                network_download_bytes_per_second=None,
                network_upload_bytes_per_second=None,
            ),
        )
    finally:
        connection.close()

    response = client.get("/api/history?range=24h")
    assert response.status_code == 200
    samples = response.json()["samples"]
    assert len(samples) == 1
    assert samples[0]["cpu_usage_percent"] == 20.0
    assert samples[0]["memory_usage_percent"] == 30.0


def test_history_7d_response_is_downsampled(
    history_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now_ms = 4_000_000_000_000
    monkeypatch.setattr(history_service.time, "time", lambda: now_ms / 1000)

    connection = connect_metrics_database(history_db)
    try:
        insert_metric_sample(
            connection,
            MetricSampleRecord(
                timestamp_ms=now_ms - 20 * 60 * 1000,
                cpu_usage_percent=10.0,
                cpu_temperature_celsius=None,
                memory_usage_percent=20.0,
                network_download_bytes_per_second=None,
                network_upload_bytes_per_second=None,
            ),
        )
        insert_metric_sample(
            connection,
            MetricSampleRecord(
                timestamp_ms=now_ms - 10 * 60 * 1000,
                cpu_usage_percent=30.0,
                cpu_temperature_celsius=None,
                memory_usage_percent=40.0,
                network_download_bytes_per_second=None,
                network_upload_bytes_per_second=None,
            ),
        )
        insert_metric_sample(
            connection,
            MetricSampleRecord(
                timestamp_ms=now_ms - 60_000,
                cpu_usage_percent=70.0,
                cpu_temperature_celsius=None,
                memory_usage_percent=80.0,
                network_download_bytes_per_second=None,
                network_upload_bytes_per_second=None,
            ),
        )
    finally:
        connection.close()

    response = client.get("/api/history?range=7d")
    assert response.status_code == 200
    samples = response.json()["samples"]
    assert len(samples) == 2
    assert samples[0]["cpu_usage_percent"] == 20.0
    assert samples[1]["cpu_usage_percent"] == 70.0


def test_history_1h_response_remains_raw(
    history_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now_ms = 5_000_000_000_000
    monkeypatch.setattr(history_service.time, "time", lambda: now_ms / 1000)

    connection = connect_metrics_database(history_db)
    try:
        for offset in (0, 30_000, 60_000):
            insert_metric_sample(
                connection,
                MetricSampleRecord(
                    timestamp_ms=now_ms - offset,
                    cpu_usage_percent=float(offset),
                    cpu_temperature_celsius=None,
                    memory_usage_percent=10.0,
                    network_download_bytes_per_second=None,
                    network_upload_bytes_per_second=None,
                ),
            )
    finally:
        connection.close()

    response = client.get("/api/history?range=1h")
    assert response.status_code == 200
    samples = response.json()["samples"]
    assert len(samples) == 3
    assert [sample["timestamp_ms"] for sample in samples] == [
        now_ms - 60_000,
        now_ms - 30_000,
        now_ms,
    ]
