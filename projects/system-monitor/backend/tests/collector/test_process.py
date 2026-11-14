"""以模擬子程序驗證 plugin 管理，不啟動採集器或開發服務。"""

import asyncio
import io
import types

import pytest

import monitor_backend


class Child:
    """以 pipe 關閉模擬正常退出，可另外模擬無回應或崩潰。"""

    def __init__(self, *, responds=True):
        self.pid = 12345
        self.returncode = None
        self.exited = asyncio.Event()
        self.responds = responds
        self.killed = False
        self.closed = False
        self.stdin = types.SimpleNamespace(close=self.close)

    def close(self):
        self.closed = True
        if self.responds:
            self.finish(0)

    def finish(self, code):
        self.returncode = code
        self.exited.set()

    def kill(self):
        self.killed = True
        self.finish(-9)

    async def wait(self):
        await self.exited.wait()
        return self.returncode


def test_child_uses_shared_python_path_and_is_reaped_on_stop(
    tmp_path, monkeypatch
):
    process = monitor_backend.module("collector.process")
    config = monitor_backend.module("config")

    async def scenario():
        stop = asyncio.Event()
        child = Child()
        spawned = asyncio.Event()
        seen = {}

        async def spawn(*command, **options):
            seen.update(command=command, options=options)
            spawned.set()
            return child

        monkeypatch.setattr(process.asyncio, "create_subprocess_exec", spawn)
        settings = config.Settings(tmp_path / "test.db")
        task = asyncio.create_task(process._run_child(settings, stop))
        await spawned.wait()
        stop.set()
        await asyncio.wait_for(task, 1)
        assert child.closed and child.returncode == 0
        assert not child.killed
        assert seen["command"][1:] == ("-m", "src.collector", "--parent-watch")
        assert seen["options"]["env"]["A7LAS_METRICS_DB_PATH"] == str(
            settings.database_path
        )
        assert (seen["options"]["cwd"] / "src" / "collector").is_dir()

    asyncio.run(scenario())


def test_unresponsive_child_is_killed_and_waited(tmp_path, monkeypatch):
    process = monitor_backend.module("collector.process")
    config = monitor_backend.module("config")

    async def scenario():
        stop = asyncio.Event()
        child = Child(responds=False)

        async def spawn(*args, **kwargs):
            stop.set()
            return child

        monkeypatch.setattr(process.asyncio, "create_subprocess_exec", spawn)
        monkeypatch.setattr(process, "_SHUTDOWN_TIMEOUT_SECONDS", 0.01)
        await process._run_child(config.Settings(tmp_path / "test.db"), stop)
        assert child.killed
        assert child.exited.is_set()

    asyncio.run(scenario())


def test_two_workers_have_one_manager_and_standby_takes_over(
    tmp_path, monkeypatch
):
    process = monitor_backend.module("collector.process")
    config = monitor_backend.module("config")

    async def scenario():
        first_stop, second_stop = asyncio.Event(), asyncio.Event()
        first_started, second_started = asyncio.Event(), asyncio.Event()
        active = [0]
        peak = [0]

        async def child(settings, stop):
            active[0] += 1
            peak[0] = max(peak[0], active[0])
            (first_started if stop is first_stop else second_started).set()
            try:
                await stop.wait()
            finally:
                active[0] -= 1

        monkeypatch.setattr(process, "_run_child", child)
        monkeypatch.setattr(process, "_RETRY_SECONDS", 0.01)
        settings = config.Settings(tmp_path / "shared.db")
        first = asyncio.create_task(process.supervise(settings, first_stop))
        await first_started.wait()
        second = asyncio.create_task(process.supervise(settings, second_stop))
        await asyncio.sleep(0.03)
        assert not second_started.is_set()
        first_stop.set()
        await first
        await asyncio.wait_for(second_started.wait(), 1)
        second_stop.set()
        await second
        assert peak[0] == 1
        assert active[0] == 0

    asyncio.run(scenario())


def test_child_failure_retries_without_stopping_api(tmp_path, monkeypatch):
    process = monitor_backend.module("collector.process")
    config = monitor_backend.module("config")

    async def scenario():
        stop = asyncio.Event()
        attempts = []

        async def child(settings, stopping):
            attempts.append(settings.database_path)
            if len(attempts) == 1:
                raise OSError("spawn failed")
            stopping.set()

        monkeypatch.setattr(process, "_run_child", child)
        monkeypatch.setattr(process, "_RETRY_SECONDS", 0.01)
        settings = config.Settings(tmp_path / "test.db")
        await process.supervise(settings, stop)
        assert attempts == [settings.database_path] * 2

    asyncio.run(scenario())


def test_plugin_shutdown_waits_for_supervisor(monkeypatch):
    plugin = monitor_backend.module("plugin")
    stopped = []

    async def fake_supervise(settings, stop):
        await stop.wait()
        stopped.append(True)

    monkeypatch.setattr(plugin.process, "supervise", fake_supervise)

    async def scenario():
        async with plugin.lifespan(None):
            assert stopped == []
        assert stopped == [True]

    asyncio.run(scenario())


def test_parent_pipe_eof_stops_collector(monkeypatch):
    cli = monitor_backend.module("collector.__main__")
    stop = types.SimpleNamespace(set=lambda: calls.append("stopped"))
    calls = []
    monkeypatch.setattr(
        cli.sys, "stdin", types.SimpleNamespace(buffer=io.BytesIO(b""))
    )
    cli._watch_parent(stop)
    assert calls == ["stopped"]


def test_cancelled_child_manager_still_reaps_process(tmp_path, monkeypatch):
    process = monitor_backend.module("collector.process")
    config = monitor_backend.module("config")

    async def scenario():
        child = Child()
        started = asyncio.Event()

        async def spawn(*args, **kwargs):
            started.set()
            return child

        monkeypatch.setattr(process.asyncio, "create_subprocess_exec", spawn)
        task = asyncio.create_task(
            process._run_child(
                config.Settings(tmp_path / "test.db"), asyncio.Event()
            )
        )
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert child.closed
        assert child.returncode == 0

    asyncio.run(scenario())
