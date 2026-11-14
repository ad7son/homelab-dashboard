"""以可控時鐘驗證排程、每日清理與錯誤恢復，不等待真實時間。"""

import types

import pytest

import monitor_backend


@pytest.mark.parametrize(
    "retention_days,expected_cleanups", [(30, 1), (None, 0)]
)
def test_cleanup_waits_full_interval_and_info_is_read_once(
    tmp_path, monkeypatch, info, sample, retention_days, expected_cleanups
):
    runner = monitor_backend.module("collector.runner")
    config = monitor_backend.module("config")
    now = [0.0]
    calls = {"info": 0, "reads": [], "cleanup": []}

    class Reader:
        def __init__(self, timeout):
            pass

        def read_info(self):
            calls["info"] += 1
            return info

        def read(self):
            calls["reads"].append(now[0])
            return dict(sample, timestamp_ms=int(now[0] * 1000))

    class Stop:
        def is_set(self):
            return now[0] > 12

        def wait(self, seconds):
            now[0] += seconds

    original = runner.repository.HostRepository.delete_before

    def cleanup(self, cutoff):
        calls["cleanup"].append((now[0], cutoff))
        return original(self, cutoff)

    monkeypatch.setattr(runner.host_reader, "HostReader", Reader)
    monkeypatch.setattr(runner.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(
        runner.repository.HostRepository, "delete_before", cleanup
    )
    settings = config.Settings(
        tmp_path / "test.db",
        retention_days=retention_days,
        cleanup_interval_seconds=10,
    )
    runner.run(settings, Stop())
    assert calls["info"] == 1
    assert calls["reads"] == [0, 3, 6, 9, 12]
    assert len(calls["cleanup"]) == expected_cleanups
    if calls["cleanup"]:
        assert calls["cleanup"][0][0] >= 10


def test_overrun_skips_missed_slots_and_failure_recovers(
    tmp_path, monkeypatch, info, sample
):
    runner = monitor_backend.module("collector.runner")
    config = monitor_backend.module("config")
    now, reads = [0.0], []

    def read():
        reads.append(now[0])
        if len(reads) == 1:
            now[0] += 8
            raise OSError("source failed")
        return dict(sample, timestamp_ms=int(now[0] * 1000))

    monkeypatch.setattr(
        runner.host_reader,
        "HostReader",
        lambda timeout: types.SimpleNamespace(
            read_info=lambda: info, read=read
        ),
    )
    monkeypatch.setattr(runner.time, "monotonic", lambda: now[0])

    class Stop:
        def is_set(self):
            return len(reads) >= 3

        def wait(self, seconds):
            now[0] += seconds

    path = tmp_path / "test.db"
    runner.run(config.Settings(path), Stop())
    assert reads == [0, 9, 12]
    rows = runner.repository.HostRepository(path).get_history(0, 20000)
    assert [row["timestamp_ms"] for row in rows] == [9000, 12000]
