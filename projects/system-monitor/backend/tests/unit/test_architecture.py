"""保護已確認的依賴方向，避免後續又把 I/O 混回規則或 HTTP 層。"""

import ast
from concurrent import futures
import pathlib
import threading
import time

import monitor_backend

ROOT = pathlib.Path(monitor_backend.module("plugin").__file__).parent


def test_domain_and_services_do_not_import_transport_or_storage_implementations():
    forbidden = {
        "fastapi",
        "pydantic",
        "psutil",
        "sqlite3",
        "infrastructure",
        "api",
        "bootstrap",
    }
    for folder in ("domain", "services"):
        for path in (ROOT / folder).glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    assert (node.module or "").split(".")[0] not in forbidden, (
                        path,
                        node.module,
                    )
                elif isinstance(node, ast.Import):
                    assert all(
                        alias.name.split(".")[0] not in forbidden
                        for alias in node.names
                    ), path


def test_sql_execution_is_confined_to_database_and_repository_modules():
    for path in ROOT.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr
                in {"execute", "executemany", "executescript"}
            ):
                relative = path.relative_to(ROOT).parts
                assert relative[:2] in {
                    ("infrastructure", "database"),
                    ("infrastructure", "repositories"),
                }, path


def test_bootstrap_shares_instances_without_initializing_storage(tmp_path):
    bootstrap = monitor_backend.module("bootstrap")
    first = bootstrap.get_runtime(tmp_path / "first.db")
    second = bootstrap.get_runtime(tmp_path / "second.db")
    assert bootstrap.get_runtime(tmp_path / "first.db") is first
    assert first is not second
    assert (
        first.overview.source is first.health.source is first.collection.source
    )
    assert (
        first.history.repository
        is first.health.repository
        is first.collection.repository
    )
    assert not first.settings.database_path.exists()
    assert not second.settings.database_path.exists()


def test_simultaneous_first_requests_share_one_runtime(tmp_path, monkeypatch):
    """lru_cache 本身不保證首次並行呼叫只建構一次，取樣狀態必須另有保護。"""

    bootstrap = monitor_backend.module("bootstrap")
    original = bootstrap.services_overview.OverviewService
    starts, constructed = threading.Barrier(8), []

    def slow_constructor(source):
        constructed.append(source)
        time.sleep(0.02)
        return original(source)

    monkeypatch.setattr(
        bootstrap.services_overview, "OverviewService", slow_constructor
    )

    def request(_):
        starts.wait()
        return bootstrap.get_runtime(tmp_path / "concurrent.db")

    with futures.ThreadPoolExecutor(max_workers=8) as pool:
        runtimes = list(pool.map(request, range(8)))
    assert len(constructed) == 1
    assert all(runtime is runtimes[0] for runtime in runtimes)
