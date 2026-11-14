"""驗證選用 plugin 生命週期、排序、回滾與相容前綴不重複啟動。"""

import pytest
from fastapi import testclient

from app import main
from app.plugins import manifest
from tests.plugins import test_loader

_PLUGIN = test_loader.STATUS_PLUGIN + """
import contextlib

@contextlib.asynccontextmanager
async def lifespan(app):
    app.state.events.append(__package__ + ':start')
    try:
        yield
    finally:
        app.state.events.append(__package__ + ':stop')
"""


def test_optional_lifespans_start_once_and_stop_in_reverse_order(tmp_path):
    test_loader._write_project(
        tmp_path, "alpha", test_loader._manifest(), _PLUGIN
    )
    test_loader._write_project(
        tmp_path,
        "system-monitor",
        test_loader._manifest(
            id="system-monitor",
            name="System Monitor",
            pythonPackage="src",
            routeBase="/system-monitor",
            apiPrefix="/api/system-monitor",
            legacyApiPrefix="/api",
        ),
        _PLUGIN,
    )
    application = main.create_app(tmp_path)
    application.state.events = []
    assert application.state.events == []
    with testclient.TestClient(application) as client:
        starts = list(application.state.events)
        assert len(starts) == 2
        assert all(event.endswith(":start") for event in starts)
        assert client.get("/api/status").status_code == 200
        assert client.get("/api/system-monitor/status").status_code == 200
    expected_stops = [
        event.replace(":start", ":stop") for event in reversed(starts)
    ]
    assert application.state.events == starts + expected_stops


def test_later_startup_failure_unwinds_started_projects(tmp_path):
    test_loader._write_project(
        tmp_path, "alpha", test_loader._manifest(), _PLUGIN
    )
    broken = test_loader.STATUS_PLUGIN + """
import contextlib

@contextlib.asynccontextmanager
async def lifespan(app):
    raise OSError('startup rejected')
    yield
"""
    test_loader._write_project(
        tmp_path,
        "beta",
        test_loader._manifest(
            id="beta",
            name="Beta",
            pythonPackage="src",
            routeBase="/beta",
            apiPrefix="/api/beta",
        ),
        broken,
    )
    application = main.create_app(tmp_path)
    application.state.events = []
    with pytest.raises(
        manifest.ProjectModuleError, match="beta.*startup rejected"
    ):
        with testclient.TestClient(application):
            pytest.fail("Application must not start")
    assert len(application.state.events) == 2
    assert application.state.events[0].endswith(":start")
    assert application.state.events[1].endswith(":stop")


def test_noncallable_lifespan_is_rejected_before_mount(tmp_path):
    test_loader._write_project(
        tmp_path,
        "alpha",
        test_loader._manifest(),
        test_loader.STATUS_PLUGIN + "\nlifespan = 123\n",
    )
    with pytest.raises(
        manifest.ProjectModuleError, match="alpha.*lifespan must be callable"
    ):
        main.create_app(tmp_path)


def test_router_only_project_needs_no_lifecycle(tmp_path):
    test_loader._write_project(
        tmp_path,
        "alpha",
        test_loader._manifest(),
        test_loader.STATUS_PLUGIN,
    )
    with testclient.TestClient(main.create_app(tmp_path)) as client:
        assert client.get("/api/alpha/status").status_code == 200


def test_cleanup_waits_for_full_interval_and_stops_without_startup_deletion(
    monkeypatch,
):
    import asyncio
    from app import config
    from app import lifecycle
    from app.observability import storage

    calls = []
    stop = asyncio.Event()

    async def wait_once(awaitable, timeout):
        awaitable.close()
        calls.append(("wait", timeout))
        stop.set()
        raise TimeoutError

    monkeypatch.setattr(lifecycle.asyncio, "wait_for", wait_once)
    monkeypatch.setattr(
        storage, "cleanup_expired", lambda now: calls.append(("cleanup", now))
    )
    asyncio.run(lifecycle._cleanup_events(stop))
    assert calls[0] == ("wait", config.EVENT_CLEANUP_INTERVAL_SECONDS)
    assert calls[1][0] == "cleanup"
    assert len(calls) == 2


def test_event_capture_survives_project_shutdown_and_maintenance_is_released(
    tmp_path,
):
    import asyncio
    import contextlib
    from app import lifecycle
    from app.observability import events
    from app.observability import storage

    @contextlib.asynccontextmanager
    async def project(app):
        events.record("alpha", "job", outcome="success", message="started")
        try:
            yield
        finally:
            events.record("alpha", "job", outcome="success", message="stopped")

    async def run():
        application = main.create_app(tmp_path)
        application.state.project_lifespans = (("alpha", project),)
        tasks_before = asyncio.all_tasks()
        async with lifecycle.lifespan(application):
            assert storage.EventStore().recent()[0]["message"] == "started"
        assert asyncio.all_tasks() == tasks_before
        assert storage.EventStore().recent()[0]["message"] == "stopped"
        assert not any(
            isinstance(handler, events.EventHandler)
            for handler in events.logging.getLogger().handlers
        )

    asyncio.run(run())
