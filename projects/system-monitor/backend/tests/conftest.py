"""共用暫存 SQLite 與可控樣本；不存取開發者的真實資料庫。"""

import pytest

import monitor_backend


@pytest.fixture
def store(tmp_path, monkeypatch):
    path = tmp_path / "metrics.db"
    monkeypatch.setenv("A7LAS_METRICS_DB_PATH", str(path))
    monitor_backend.module("database.connection").initialize(path)
    return monitor_backend.module("database.repository").HostRepository(path)


@pytest.fixture
def info():
    repository = monitor_backend.module("database.repository")
    result = dict.fromkeys(repository.INFO_COLUMNS)
    result.update(
        updated_at_ms=1000,
        cpu_physical_cores=4,
        cpu_logical_cores=8,
        memory_total_bytes=1024,
        gpu_name="Test GPU",
        gpu_device_count=1,
        network_interface="eth0",
        network_ip_address="192.0.2.1",
    )
    return result


@pytest.fixture
def sample():
    repository = monitor_backend.module("database.repository")
    result = dict.fromkeys(repository.METRIC_COLUMNS)
    result.update(
        timestamp_ms=3000,
        cpu_usage_percent=0,
        memory_usage_percent=25,
        gpu_status="unsupported",
        disk_io_status="warming_up",
        network_download_bytes_per_second=0,
    )
    return result
