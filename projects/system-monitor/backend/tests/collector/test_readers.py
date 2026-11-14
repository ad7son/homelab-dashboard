"""使用模擬 OS 回應驗證速率與 GPU 邊界，無需真實硬體。"""

import types

import pytest

import monitor_backend


@pytest.mark.parametrize(
    "module_name,reader_name,counter_name,field_a,field_b",
    [
        (
            "disk_io",
            "DiskIoReader",
            "disk_io_counters",
            "read_bytes",
            "write_bytes",
        ),
        (
            "network",
            "NetworkReader",
            "net_io_counters",
            "bytes_recv",
            "bytes_sent",
        ),
    ],
)
def test_rate_warmup_zero_reset_and_failure(
    monkeypatch, module_name, reader_name, counter_name, field_a, field_b
):
    module = monitor_backend.module("collector.readers." + module_name)
    reader = getattr(module, reader_name)()
    if module_name == "network":
        reader._interface = "eth0"
    now = [0]
    counts = [100, 200]
    broken = [False]

    def counter(**kwargs):
        if broken[0]:
            raise OSError("denied")
        result = types.SimpleNamespace(
            **{field_a: counts[0], field_b: counts[1]}
        )
        return {"eth0": result} if module_name == "network" else result

    monkeypatch.setattr(module.psutil, counter_name, counter)
    monkeypatch.setattr(module.time, "monotonic", lambda: now[0])
    first = reader.read()
    assert all(not isinstance(value, float) for value in first.values())
    now[0] = 3
    result = reader.read()
    rate_values = [
        value for key, value in result.items() if key.endswith("per_second")
    ]
    assert rate_values == [0, 0]
    now[0] = 6
    counts[:] = [10, 20]
    result = reader.read()
    assert all(
        value is None
        for key, value in result.items()
        if key.endswith("per_second")
    )
    broken[0] = True
    with pytest.raises(OSError):
        reader.read()
    broken[0], now[0] = False, 9
    result = reader.read()
    assert all(
        value is None
        for key, value in result.items()
        if key.endswith("per_second")
    )


def test_swap_failure_keeps_memory(monkeypatch):
    module = monitor_backend.module("collector.readers.memory")
    monkeypatch.setattr(
        module.psutil,
        "virtual_memory",
        lambda: types.SimpleNamespace(used=50, available=50, percent=50),
    )

    def fail():
        raise OSError("swap denied")

    monkeypatch.setattr(module.psutil, "swap_memory", fail)
    assert module.MemoryReader().read() == {
        "memory_used_bytes": 50,
        "memory_available_bytes": 50,
        "memory_usage_percent": 50,
    }


def test_cpu_first_sample_is_unknown_then_zero_is_valid(monkeypatch):
    module = monitor_backend.module("collector.readers.cpu")
    monkeypatch.setattr(module.psutil, "cpu_percent", lambda **kwargs: 0)
    monkeypatch.setattr(module.psutil, "cpu_freq", lambda: None)
    monkeypatch.setattr(
        module.psutil, "sensors_temperatures", lambda: {}, raising=False
    )
    monkeypatch.setattr(module.os, "getloadavg", lambda: (0, 0, 0))
    reader = module.CpuReader()
    assert reader.read()["cpu_usage_percent"] is None
    assert reader.read()["cpu_usage_percent"] == 0


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("0", 0),
        ("100", 100),
        ("N/A", None),
        ("NaN", None),
        ("inf", None),
        ("101", None),
        ("-1", None),
    ],
)
def test_gpu_percent_validation(raw, expected):
    module = monitor_backend.module("collector.readers.gpu")
    assert module._usage(raw) == expected


def test_gpu_unsupported_does_not_run_commands(monkeypatch):
    module = monitor_backend.module("collector.readers.gpu")
    monkeypatch.setattr(module.platform, "system", lambda: "Darwin")
    reader = module.GpuReader()
    assert reader.read_info()["gpu_device_count"] == 0
    assert reader.read() == {"gpu_status": "unsupported"}


def test_nvidia_valid_zero_and_unavailable(monkeypatch):
    module = monitor_backend.module("collector.readers.gpu")
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    reader = module.GpuReader()
    reader._nvidia_names = ["GPU"]
    monkeypatch.setattr(reader, "_nvidia", lambda fields: [["0"]])
    assert reader.read() == {"gpu_status": "available", "gpu_usage_percent": 0}
    monkeypatch.setattr(reader, "_nvidia", lambda fields: [["N/A"]])
    assert reader.read() == {"gpu_status": "unavailable"}
