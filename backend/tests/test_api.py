import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def api_client() -> TestClient:
    return client


def test_system_returns_200(api_client: TestClient) -> None:
    response = api_client.get("/api/system")
    assert response.status_code == 200
    data = response.json()
    assert "hostname" in data
    assert "uptime" in data
    assert data["uptime"] > 0


def test_cpu_returns_200(api_client: TestClient) -> None:
    response = api_client.get("/api/cpu")
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["usage_percent"] <= 100
    assert data["physical_cores"] > 0
    assert data["logical_cores"] > 0


def test_memory_returns_200(api_client: TestClient) -> None:
    response = api_client.get("/api/memory")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert "swap" in data


def test_disks_returns_200(api_client: TestClient) -> None:
    response = api_client.get("/api/disks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for disk in data:
        assert "mount_point" in disk
        assert "total_bytes" in disk
        assert "usage_percent" in disk


def test_network_returns_200(api_client: TestClient) -> None:
    response = api_client.get("/api/network")
    assert response.status_code == 200
    data = response.json()
    assert "download_rate" in data
    assert "upload_rate" in data


def test_overview_returns_200(api_client: TestClient) -> None:
    response = api_client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert "system" in data
    assert "cpu" in data
    assert "memory" in data
    assert "disks" in data
    assert "network" in data


def test_overview_cpu_percent_valid(api_client: TestClient) -> None:
    response = api_client.get("/api/overview")
    cpu = response.json()["cpu"]
    assert 0 <= cpu["usage_percent"] <= 100


def test_overview_memory_total_positive(api_client: TestClient) -> None:
    response = api_client.get("/api/overview")
    memory = response.json()["memory"]
    assert memory["total"] > 0


def test_network_rates_after_second_sample(api_client: TestClient) -> None:
    api_client.get("/api/network")
    response = api_client.get("/api/network")
    data = response.json()
    if data["interface"] is not None:
        assert data["download_rate"] is not None or data["upload_rate"] is not None or (
            data["download_rate"] == 0 and data["upload_rate"] == 0
        )
