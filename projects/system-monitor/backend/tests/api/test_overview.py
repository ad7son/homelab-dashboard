"""以正式平台掛載驗證新舊前綴，API 僅查資料庫。"""

import pytest
from fastapi import testclient

from app import main
import monitor_backend


@pytest.mark.parametrize("prefix", ["/api", "/api/system-monitor"])
def test_overview_reads_database_without_hardware(
    store, info, sample, monkeypatch, prefix
):
    store.update_info(info)
    store.insert(sample)

    def forbidden(*args):
        raise AssertionError("API must not read hardware")

    reader = monitor_backend.module("collector.host_reader")
    monkeypatch.setattr(reader.HostReader, "__init__", forbidden)
    response = testclient.TestClient(main.app).get(prefix + "/overview")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"info", "metrics"}
    assert data["metrics"]["timestamp_ms"] == 3000
    assert data["metrics"]["cpu_usage_percent"] == 0
    assert data["metrics"]["gpu_usage_percent"] is None
    assert data["info"]["memory_total_bytes"] == 1024


def test_empty_database_returns_503(store):
    response = testclient.TestClient(main.app).get(
        "/api/system-monitor/overview"
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "No host metrics collected yet"


def test_missing_database_returns_503_without_creating(tmp_path, monkeypatch):
    path = tmp_path / "missing.db"
    monkeypatch.setenv("A7LAS_METRICS_DB_PATH", str(path))
    response = testclient.TestClient(main.app).get(
        "/api/system-monitor/overview"
    )
    assert response.status_code == 503
    assert not path.exists()


def test_feature_health_remains_removed(store):
    client = testclient.TestClient(main.app)
    for prefix in ("/api", "/api/system-monitor"):
        assert client.get(prefix + "/feature-health").status_code == 404
    assert client.get("/api/health").status_code == 200
