import os
import platform
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import system_service

client = TestClient(app)


@pytest.fixture
def api_client() -> TestClient:
    return client


@pytest.fixture(autouse=True)
def _reset_system_cache() -> None:
    """Clear the cached static info so each test can mock independently."""
    system_service._static_cache = None


# ---------------------------------------------------------------------------
# System endpoint
# ---------------------------------------------------------------------------

def test_system_returns_200(api_client: TestClient) -> None:
    response = api_client.get("/api/system")
    assert response.status_code == 200
    data = response.json()
    assert "hostname" in data
    assert "uptime" in data
    assert data["uptime"] > 0
    assert isinstance(data["operating_system"], str)
    assert isinstance(data["kernel"], str)
    assert isinstance(data["architecture"], str)


def test_system_kernel_is_platform_release(api_client: TestClient) -> None:
    """kernel must equal platform.release(), not the verbose build string."""
    response = api_client.get("/api/system")
    data = response.json()
    assert data["kernel"] == platform.release()
    assert data["architecture"] == platform.machine()


def test_system_reads_os_release_when_present(api_client: TestClient) -> None:
    """When /etc/os-release exists, operating_system and os_version come from it."""
    fake_content = 'NAME="Ubuntu"\nVERSION="22.04.3 LTS (Jammy Jellyfish)"\nID=ubuntu\n'
    with patch("builtins.open", create=True) as mock_open, \
         patch.object(os.path, "isfile", side_effect=lambda p: p == "/etc/os-release"):
        mock_open.return_value.__enter__ = lambda s: __import__("io").StringIO(fake_content)
        mock_open.return_value.__exit__ = lambda s, *a: None
        response = api_client.get("/api/system")
    data = response.json()
    assert data["operating_system"] == "Ubuntu"
    assert data["os_version"] == "22.04.3 LTS (Jammy Jellyfish)"


def test_system_fallback_without_os_release(api_client: TestClient) -> None:
    """Without /etc/os-release, fall back to platform.system()."""
    with patch.object(os.path, "isfile", return_value=False):
        response = api_client.get("/api/system")
    data = response.json()
    assert data["operating_system"] == platform.system()


# ---------------------------------------------------------------------------
# CPU endpoint
# ---------------------------------------------------------------------------

def test_cpu_returns_200(api_client: TestClient) -> None:
    response = api_client.get("/api/cpu")
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["usage_percent"] <= 100
    assert data["physical_cores"] > 0
    assert data["logical_cores"] > 0


# ---------------------------------------------------------------------------
# Memory endpoint
# ---------------------------------------------------------------------------

def test_memory_returns_200(api_client: TestClient) -> None:
    response = api_client.get("/api/memory")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert "swap" in data


# ---------------------------------------------------------------------------
# Disks endpoint
# ---------------------------------------------------------------------------

def test_disks_returns_200(api_client: TestClient) -> None:
    response = api_client.get("/api/disks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for disk in data:
        assert "mount_point" in disk
        assert "total_bytes" in disk
        assert "usage_percent" in disk


# ---------------------------------------------------------------------------
# Network endpoint
# ---------------------------------------------------------------------------

def test_network_returns_200(api_client: TestClient) -> None:
    response = api_client.get("/api/network")
    assert response.status_code == 200
    data = response.json()
    assert "download_rate" in data
    assert "upload_rate" in data


# ---------------------------------------------------------------------------
# Overview endpoint
# ---------------------------------------------------------------------------

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
