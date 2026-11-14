"""驗證組合器隔離單項錯誤與保留缺值。"""

import types

import monitor_backend


def test_reader_failure_does_not_drop_other_metrics(monkeypatch):
    module = monitor_backend.module("collector.host_reader")
    reader = module.HostReader()

    def fail():
        raise OSError("permission denied")

    reader._cpu = types.SimpleNamespace(read=fail)
    reader._memory = types.SimpleNamespace(
        read=lambda: {"memory_usage_percent": 0}
    )
    reader._network = types.SimpleNamespace(
        read=lambda: {"network_upload_bytes_per_second": float("nan")}
    )
    reader._gpu = types.SimpleNamespace(
        read=lambda: {"gpu_status": "unsupported"}
    )
    reader._disk = types.SimpleNamespace(
        read=lambda: {"disk_io_status": "warming_up"}
    )
    result = reader.read()
    assert result["cpu_usage_percent"] is None
    assert result["memory_usage_percent"] == 0
    assert result["network_upload_bytes_per_second"] is None
    assert result["gpu_status"] == "unsupported"
