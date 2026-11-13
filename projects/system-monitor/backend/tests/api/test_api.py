"""驗證真實主機總覽 API；選用感測器失敗不應影響其他 CPU 資訊。"""

from fastapi import testclient
import psutil
import pytest

from app import main

# 此檔共用輕量 API 用戶端；資料庫與服務狀態由各測試 fixture 隔離。
_client = testclient.TestClient(main.app)


@pytest.fixture
def api_client() -> testclient.TestClient:
    return _client


# 經由總覽取得 CPU 資訊。


def test_overview_cpu_has_valid_usage_and_cores(
    api_client: testclient.TestClient,
) -> None:
    response = api_client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()["cpu"]
    assert 0 <= data["usage_percent"] <= 100
    assert data["physical_cores"] > 0
    assert data["logical_cores"] > 0


def test_cpu_temperature_null_when_sensors_raise_oserror(
    api_client: testclient.TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """作業系統拒絕讀取溫度時，總覽仍應回應成功並保留溫度缺值。"""

    def raise_oserror() -> None:
        raise OSError("Permission denied")

    monkeypatch.setattr(
        psutil, "sensors_temperatures", raise_oserror, raising=False
    )

    response = api_client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()["cpu"]
    assert data["temperature"] is None
    assert 0 <= data["usage_percent"] <= 100


def test_cpu_frequency_null_when_cpu_freq_raises_oserror(
    api_client: testclient.TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """作業系統拒絕讀取頻率時，總覽仍應回應成功並保留頻率缺值。"""

    def raise_oserror() -> None:
        raise OSError("Permission denied")

    monkeypatch.setattr(psutil, "cpu_freq", raise_oserror)

    response = api_client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()["cpu"]
    assert data["frequency"] is None
    assert 0 <= data["usage_percent"] <= 100


# 經由總覽取得記憶體資訊。


def test_overview_memory_includes_swap(
    api_client: testclient.TestClient,
) -> None:
    response = api_client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()["memory"]
    assert data["total"] > 0
    assert "swap" in data


# 經由總覽取得網路資訊。


def test_overview_network_includes_rates(
    api_client: testclient.TestClient,
) -> None:
    response = api_client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()["network"]
    assert "download_rate" in data
    assert "upload_rate" in data


# 總覽端點。


def test_overview_returns_200(api_client: testclient.TestClient) -> None:
    response = api_client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "memory" in data
    assert "network" in data
    assert "gpu" in data
    assert "disk_io" in data
    assert set(data) == {"cpu", "memory", "network", "gpu", "disk_io"}


def test_overview_cpu_percent_valid(api_client: testclient.TestClient) -> None:
    response = api_client.get("/api/overview")
    cpu = response.json()["cpu"]
    assert 0 <= cpu["usage_percent"] <= 100


def test_overview_memory_total_positive(
    api_client: testclient.TestClient,
) -> None:
    response = api_client.get("/api/overview")
    memory = response.json()["memory"]
    assert memory["total"] > 0


def test_network_rates_after_second_sample(
    api_client: testclient.TestClient,
) -> None:
    api_client.get("/api/overview")
    response = api_client.get("/api/overview")
    data = response.json()["network"]
    if data["interface"] is not None:
        assert (
            data["download_rate"] is not None
            or data["upload_rate"] is not None
            or (data["download_rate"] == 0 and data["upload_rate"] == 0)
        )
