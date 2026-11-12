"""驗證累計計數器轉速率、冷啟動、短間隔共用及讀取中斷後的恢復。"""

from monitor_backend import module as monitor_module

from types import SimpleNamespace

import pytest

DiskIoInfo = monitor_module('machine.models').DiskIoInfo
readers = monitor_module('machine.readers')


@pytest.fixture
def sampling(monkeypatch: pytest.MonkeyPatch):
    state = {"now": 0.0, "read": 1000, "write": 2000, "missing": False, "error": None}
    monkeypatch.setattr(readers, "_disk_io_previous", None)
    monkeypatch.setattr(readers, "_disk_io_latest", DiskIoInfo(status="warming_up"))
    monkeypatch.setattr(readers.time, "monotonic", lambda: state["now"])

    def counters(**kwargs):
        assert kwargs == {"nowrap": True}
        if state["error"]:
            raise state["error"]
        if state["missing"]:
            return None
        return SimpleNamespace(read_bytes=state["read"], write_bytes=state["write"])

    monkeypatch.setattr(readers.psutil, "disk_io_counters", counters)
    return state


def test_first_sample_is_not_zero(sampling) -> None:
    result = readers.get_disk_io_info()
    assert result.status == "warming_up"
    assert result.read_bytes_per_second is None
    assert result.write_bytes_per_second is None


def test_rates_use_elapsed_seconds(sampling) -> None:
    readers.get_disk_io_info()
    sampling.update(now=2.0, read=3048, write=6096)
    result = readers.get_disk_io_info()
    assert result.status == "available"
    assert result.read_bytes_per_second == 1024
    assert result.write_bytes_per_second == 2048


def test_idle_is_real_zero(sampling) -> None:
    readers.get_disk_io_info()
    sampling["now"] = 3
    result = readers.get_disk_io_info()
    assert result.status == "available"
    assert result.read_bytes_per_second == result.write_bytes_per_second == 0


def test_rapid_requests_share_sample(sampling) -> None:
    first = readers.get_disk_io_info()
    sampling.update(now=0.2, read=10000)
    assert readers.get_disk_io_info() is first
    sampling["now"] = 3
    assert readers.get_disk_io_info().read_bytes_per_second == 3000


def test_reset_counter_primes_instead_of_negative_rate(sampling) -> None:
    readers.get_disk_io_info()
    sampling.update(now=3, read=0, write=0)
    result = readers.get_disk_io_info()
    assert result.status == "warming_up"
    assert result.read_bytes_per_second is None
    sampling.update(now=6, read=300, write=600)
    assert readers.get_disk_io_info().read_bytes_per_second == 100


@pytest.mark.parametrize("error", [OSError(), NotImplementedError(), RuntimeError()])
def test_read_failure_and_recovery(sampling, error) -> None:
    readers.get_disk_io_info()
    sampling.update(now=3, error=error)
    assert readers.get_disk_io_info().status == "unavailable"
    sampling.update(now=6, error=None)
    assert readers.get_disk_io_info().status == "warming_up"


def test_missing_counters_are_unavailable(sampling) -> None:
    sampling["missing"] = True
    result = readers.get_disk_io_info()
    assert result.status == "unavailable"
    assert result.read_bytes_per_second is None

