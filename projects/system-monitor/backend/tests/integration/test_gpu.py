"""使用模擬驅動輸出與暫存 sysfs，驗證讀不到與真正 0% 的差異。"""

from monitor_backend import module as monitor_module

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

gpu = monitor_module('infrastructure.metrics.gpu')


@pytest.fixture(autouse=True)
def isolate_gpu(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    global gpu_reader
    gpu_reader = gpu.GpuReader(drm_root=tmp_path)
    monkeypatch.setattr(gpu.platform, "system", lambda: "Linux")
    monkeypatch.setattr(gpu.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout=""))


@pytest.mark.parametrize("raw", ["N/A", "[Not Supported]", "NaN", "inf", "-1", "101", ""])
def test_invalid_utilization_is_unavailable(raw: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gpu.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout=f"NVIDIA Test, {raw}\n"))
    result = gpu_reader.read()
    assert result.status == "unavailable"
    assert result.usage_percent is None


def test_nvidia_idle_is_real_zero_and_command_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(argv, **kwargs):
        assert argv == ["nvidia-smi", "--query-gpu=name,utilization.gpu", "--format=csv,noheader,nounits"]
        assert kwargs["shell"] is False
        assert kwargs["timeout"] == 2
        return SimpleNamespace(returncode=0, stdout="NVIDIA Test, 0\n")

    monkeypatch.setattr(gpu.subprocess, "run", run)
    result = gpu_reader.read()
    assert result.status == "available"
    assert result.usage_percent == 0
    assert result.name == "NVIDIA Test"


def test_multiple_gpus_select_busiest_valid_device(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gpu.subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=0, stdout='"NVIDIA, first", 10\nNVIDIA second, 80\nNVIDIA third, N/A\n',
    ))
    result = gpu_reader.read()
    assert result.usage_percent == 80
    assert result.name == "NVIDIA second"
    assert result.device_count == 3


@pytest.mark.parametrize("failure", [FileNotFoundError(), PermissionError(), subprocess.TimeoutExpired("nvidia-smi", 2)])
def test_driver_errors_do_not_escape(failure: Exception, monkeypatch: pytest.MonkeyPatch) -> None:
    def run(*args, **kwargs):
        raise failure

    monkeypatch.setattr(gpu.subprocess, "run", run)
    assert gpu_reader.read().usage_percent is None


def test_nonzero_exit_does_not_trust_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gpu.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout="NVIDIA Test, 90"))
    assert gpu_reader.read().usage_percent is None


def test_macos_does_not_probe_linux_drivers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gpu.platform, "system", lambda: "Darwin")
    def unexpected(*args, **kwargs):
        pytest.fail("macOS must not run GPU probes")

    monkeypatch.setattr(gpu.subprocess, "run", unexpected)
    result = gpu_reader.read()
    assert result.status == "unsupported"
    assert result.usage_percent is None


def test_amd_sysfs_and_connector_filter(tmp_path: Path) -> None:
    for name in ("card0", "card0-HDMI-A-1"):
        device = tmp_path / name / "device"
        device.mkdir(parents=True)
        (device / "vendor").write_text("0x1002\n")
        (device / "gpu_busy_percent").write_text("42\n")
    result = gpu_reader.read()
    assert result.name == "AMD card0"
    assert result.usage_percent == 42
    assert result.device_count == 1


def test_missing_or_invalid_amd_usage_is_unavailable(tmp_path: Path) -> None:
    device = tmp_path / "card0" / "device"
    device.mkdir(parents=True)
    (device / "vendor").write_text("0x1002")
    assert gpu_reader.read().usage_percent is None


def test_gpu_cache_expires_and_caches_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [0.0]
    calls = []
    monkeypatch.setattr(gpu.time, "monotonic", lambda: clock[0])
    def run(*args, **kwargs):
        calls.append(1)
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(gpu.subprocess, "run", run)
    gpu_reader.read()
    clock[0] = 2
    gpu_reader.read()
    assert len(calls) == 1
    clock[0] = 4
    gpu_reader.read()
    assert len(calls) == 2

