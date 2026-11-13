"""以受控來源驗證健康判定，不依賴測試主機是否具備特定硬體。"""

from collections.abc import Iterator
import contextlib
import json
import pathlib
import sqlite3
import time
import types
from typing import Any, NamedTuple

from fastapi import testclient
import pytest

from app import main
import monitor_backend
import monitor_support

database_connection = monitor_backend.module(
    "infrastructure.database.connection"
)
metrics_repository = monitor_backend.module(
    "infrastructure.repositories.metrics_repository"
)
domain_history = monitor_backend.module("domain.history")

collector_status = monitor_backend.module(
    "infrastructure.storage.collector_status"
)


class HealthContext(NamedTuple):
    """單一測試的採集證據、暫存資料庫及健康服務。

    Attributes:
        values: 各資源的可調整原始證據。
        path: 暫存資料庫路徑。
        sample: 初始已持久化的歷史樣本。
        service: 共用本測試證據的健康服務，不與其他測試共用。
    """

    values: dict[str, Any]
    path: pathlib.Path
    sample: Any
    service: Any


@pytest.fixture
def sources(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> Iterator[HealthContext]:
    """以暫存資料庫及可調整證據建立健康情境，結束時恢復 API 依賴。"""
    path = tmp_path / "metrics.db"
    monkeypatch.setenv("A7LAS_METRICS_DB_PATH", str(path))
    values = {
        "cpu": {
            "usage_percent": 0,
            "physical_cores": 4,
            "logical_cores": 8,
            "temperature": None,
        },
        "memory": {
            "total": 100,
            "used": 50,
            "available": 50,
            "usage_percent": 50,
        },
        "gpu": {"status": "unsupported", "device_count": 0},
        "disk-io": {
            "status": "available",
            "read_bytes_per_second": 0,
            "write_bytes_per_second": 0,
        },
        "network": {"interface": "eth0", "download_rate": 0, "upload_rate": 0},
    }
    source = types.SimpleNamespace(
        **{
            name.replace("-", "_"): (lambda name=name: values[name])
            for name in values
        }
    )
    runtime = monitor_backend.module("bootstrap").get_runtime(path)
    health = monitor_backend.module("services.health").HealthService(
        source,
        runtime.repository,
        runtime.status,
        runtime.history,
        runtime.settings,
    )
    dependency = monitor_backend.module("api.dependencies").get_health_service
    main.app.dependency_overrides[dependency] = lambda: health
    connection = database_connection.connect_metrics_database(path)
    sample = domain_history.MetricSampleRecord(
        int(time.time() * 1000), 0, None, 50, 0, 0
    )
    metrics_repository.insert_metric_sample(connection, sample)
    connection.close()
    collector_status.record_collector_result(path, sample=sample)
    try:
        yield HealthContext(values, path, sample, health)
    finally:
        main.app.dependency_overrides.pop(dependency, None)


def report(sources: HealthContext) -> dict[str, Any]:
    """回傳以功能識別碼索引的強制更新報告，仍使用來源本身的快取。"""
    return {
        feature.id: feature
        for feature in sources.service.get_feature_health(force=True).features
    }


def test_idle_values_and_missing_gpu_are_not_failures(sources):
    result = report(sources)
    assert len(result) == 7
    assert (
        result["cpu"].status
        == result["disk-io"].status
        == result["network"].status
        == "healthy"
    )
    assert result["gpu"].status == "unavailable"
    assert (
        result["history-write"].status
        == result["history-query"].status
        == "healthy"
    )
    assert result["cpu"].raw_data["usage_percent"] == 0


def test_first_sample_is_unknown(sources):
    values = sources.values
    values["disk-io"] = {"status": "warming_up"}
    values["network"].update(download_rate=None, upload_rate=None)
    result = report(sources)
    assert result["disk-io"].status == result["network"].status == "unknown"


def test_reader_failure_is_isolated_and_preserves_traceback(
    sources, monkeypatch
):
    def fail():
        raise PermissionError("CPU permission denied")

    monkeypatch.setattr(sources.service.source, "cpu", fail)
    result = report(sources)
    assert result["cpu"].status == "issues"
    assert result["memory"].status == "healthy"
    assert result["cpu"].error.message == "CPU permission denied"
    assert "PermissionError" in result["cpu"].error.traceback


def test_invalid_values_remain_visible_andjson_safe(sources):
    values = sources.values
    values["cpu"]["usage_percent"] = float("nan")
    result = report(sources)
    assert result["cpu"].status == "issues"
    assert result["cpu"].raw_data["usage_percent"] == "nan"
    json.dumps(
        monitor_backend.module("domain.serialization").to_dict(
            sources.service.get_feature_health()
        ),
        allow_nan=False,
    )


def test_last_success_survives_later_failure(sources):
    first = report(sources)["cpu"]
    sources.values["cpu"]["usage_percent"] = -1
    second = report(sources)["cpu"]
    assert second.status == "issues"
    assert second.last_success_at_ms == first.checked_at_ms


def test_stopped_writer_does_not_break_query(sources, monkeypatch):
    sample = sources.sample
    monkeypatch.setattr(
        sources.service, "clock", lambda: (sample.timestamp_ms + 90_001) / 1000
    )
    result = report(sources)
    assert result["history-write"].status == "issues"
    assert result["history-query"].status == "healthy"


def test_failed_write_preserves_actual_error_even_with_fresh_sample(sources):
    path = sources.path
    sample = sources.sample
    collector_status.record_collector_result(path, error=OSError("disk full"))
    result = report(sources)["history-write"]
    assert result.status == "issues"
    assert result.last_success_at_ms == sample.timestamp_ms
    assert result.error.message == "disk full"
    assert result.raw_data["collector"]["error"]["type"] == "OSError"


def test_missing_database_not_created_by_health_probe(sources):
    path = sources.path
    path.unlink()
    result = report(sources)
    assert (
        result["history-write"].status
        == result["history-query"].status
        == "issues"
    )
    assert not path.exists()


def test_empty_database_query_works_but_writer_is_unhealthy(sources):
    path = sources.path
    connection = database_connection.connect_metrics_database(path)
    connection.execute("DELETE FROM metric_samples")
    connection.commit()
    connection.close()
    result = report(sources)
    assert result["history-write"].status == "issues"
    assert result["history-query"].status == "healthy"
    assert result["history-query"].raw_data["samples"] == []


def test_cache_and_forced_refresh(sources):
    first = sources.service.get_feature_health(force=True)
    sources.values["cpu"]["usage_percent"] = -1
    assert sources.service.get_feature_health() is first
    assert report(sources)["cpu"].status == "issues"


@pytest.mark.parametrize("prefix", ["/api/system-monitor", "/api"])
def test_endpoint_returns_actual_snapshot(sources, prefix):
    response = testclient.TestClient(main.app).get(
        prefix + "/feature-health?force=true"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "system-monitor"
    assert len(data["features"]) == 7
    assert data["features"][0]["raw_data"]["usage_percent"] == 0
    assert data["features"][0]["checked_at_ms"] == data["checked_at_ms"]


def test_bad_schema_is_reported_without_migration(sources):
    path = sources.path
    connection = database_connection.connect_metrics_database(path)
    connection.execute("PRAGMA user_version=1")
    connection.close()
    result = report(sources)
    assert (
        result["history-write"].status
        == result["history-query"].status
        == "issues"
    )
    with contextlib.closing(sqlite3.connect(path)) as connection, connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1


def test_collector_records_failures_and_recovers(sources, monkeypatch):
    path = sources.path
    sample = sources.sample

    def fail():
        raise OSError("read failed")

    service = monitor_support.collection_service(
        path, cpu_reader=fail, clock=lambda: (sample.timestamp_ms + 1000) / 1000
    )
    with pytest.raises(OSError, match="read failed"):
        service.collect_once()
    saved = json.loads(collector_status.status_path(path).read_text())
    assert saved["last_success_at_ms"] == sample.timestamp_ms
    assert "read failed" in saved["error"]["traceback"]
    monkeypatch.setattr(
        service.source,
        "cpu",
        lambda: types.SimpleNamespace(usage_percent=0, temperature=None),
    )
    service.collect_once()
    assert (
        json.loads(collector_status.status_path(path).read_text())["error"]
        is None
    )


@pytest.mark.parametrize("content", ["not json", "[]"])
def test_broken_collector_status_keeps_database_evidence(sources, content):
    """旁檔損壞時保留讀取原因，最新成功樣本仍取自真實資料庫。"""
    path = sources.path
    sample = sources.sample
    collector_status.status_path(path).write_text(content)
    result = report(sources)["history-write"]
    assert result.raw_data["collector"] is None
    assert result.raw_data["collector_status_error"] is not None
    assert result.raw_data["latest_sample_at_ms"] == sample.timestamp_ms
    assert result.status == "healthy"
