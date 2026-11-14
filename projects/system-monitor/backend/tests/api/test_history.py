"""驗證歷史 API 的固定區間、自訂邊界與輸出上限。"""

import pytest
from fastapi import testclient

from app import main
import monitor_backend


@pytest.mark.parametrize(
    "range_name,bucket", [("15m", 3), ("1h", 3), ("24h", 300), ("7d", 1800)]
)
def test_fixed_ranges_and_empty_results(store, range_name, bucket):
    response = testclient.TestClient(main.app).get(
        "/api/system-monitor/history", params={"range": range_name}
    )
    assert response.status_code == 200
    assert response.json()["samples"] == []
    assert response.json()["interval_seconds"] == bucket


def test_custom_window_includes_both_boundaries(store, sample):
    for timestamp in (2999, 3000, 6000, 6001):
        store.insert(dict(sample, timestamp_ms=timestamp))
    response = testclient.TestClient(main.app).get(
        "/api/history?start_ms=3000&end_ms=6000"
    )
    assert response.status_code == 200
    assert response.json()["range"] is None
    assert [r["timestamp_ms"] for r in response.json()["samples"]] == [
        3000,
        6000,
    ]


@pytest.mark.parametrize(
    "query",
    [
        "range=bad",
        "start_ms=1",
        "end_ms=1",
        "start_ms=5&end_ms=4",
        "start_ms=-1&end_ms=2",
        "start_ms=0&end_ms=604800001",
    ],
)
def test_invalid_parameters_return_422(store, query):
    assert (
        testclient.TestClient(main.app).get("/api/history?" + query).status_code
        == 422
    )


def test_custom_long_window_is_aggregated(store, sample):
    for timestamp in range(0, 6_006_000, 3000):
        store.insert(dict(sample, timestamp_ms=timestamp))
    response = testclient.TestClient(main.app).get(
        "/api/history?start_ms=0&end_ms=6006000"
    )
    assert response.status_code == 200
    assert response.json()["interval_seconds"] > 3
    assert len(response.json()["samples"]) <= 2000


def test_missing_database_is_not_created(tmp_path, monkeypatch):
    path = tmp_path / "absent.db"
    monkeypatch.setenv("A7LAS_METRICS_DB_PATH", str(path))
    assert (
        testclient.TestClient(main.app).get("/api/history").status_code == 503
    )
    assert not path.exists()
