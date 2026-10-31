"""Tests for project manifest validation and router registration.

Fixtures are temporary packages. They do not use the Home Lab monitoring code.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.modules.loader as loader_module
from app.modules.loader import (
    default_projects_root,
    default_repository_root,
    discover_project_manifests,
    register_project_routers,
)
from app.modules.manifest import ProjectModuleError

STATUS_PLUGIN = """
from fastapi import APIRouter

def build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/status")
    def read_status() -> dict[str, bool]:
        return {"ok": True}

    return router
"""

NESTED_PLUGIN = """
from fastapi import APIRouter

def build_router() -> APIRouter:
    parent = APIRouter()
    child = APIRouter()

    @child.get("/overview")
    def read_overview() -> dict[str, str]:
        return {"source": "nested"}

    parent.include_router(child)
    return parent
"""

ESCAPE_PLUGIN = """
from fastapi import APIRouter

def build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/../health")
    def read_health() -> dict[str, bool]:
        return {"ok": False}

    return router
"""


@pytest.fixture
def isolated_imports():
    path_before = list(sys.path)
    modules_before = set(sys.modules)
    try:
        yield
    finally:
        for name in list(sys.modules):
            if name not in modules_before:
                del sys.modules[name]
        sys.path[:] = path_before


def test_repository_root_uses_loader_parents() -> None:
    loader_file = Path(loader_module.__file__).resolve()
    assert loader_file.parents[0].name == "modules"
    assert loader_file.parents[1].name == "app"
    assert loader_file.parents[2].name == "backend"
    assert loader_file.parents[3] == default_repository_root()
    assert (default_repository_root() / "backend" / "app" / "main.py").is_file()
    assert default_projects_root() == default_repository_root() / "projects"


def test_repository_root_ignores_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert default_repository_root() == Path(loader_module.__file__).resolve().parents[3]


def test_missing_projects_root_discovers_nothing(tmp_path: Path) -> None:
    missing = tmp_path / "projects"
    assert discover_project_manifests(missing) == []
    app = FastAPI()
    before = list(app.routes)
    assert register_project_routers(app, missing) == []
    assert list(app.routes) == before


def test_valid_manifest_mounts_router_at_api_prefix(
    tmp_path: Path,
    isolated_imports: None,
) -> None:
    _write_project(tmp_path, "alpha", _manifest(), STATUS_PLUGIN)
    app = FastAPI()

    mounted = register_project_routers(app, tmp_path)

    assert [item.id for item in mounted] == ["alpha"]
    response = TestClient(app).get("/api/alpha/status")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_nested_plugin_router_stays_under_api_prefix(
    tmp_path: Path,
    isolated_imports: None,
) -> None:
    _write_project(tmp_path, "alpha", _manifest(), NESTED_PLUGIN)
    app = FastAPI()
    register_project_routers(app, tmp_path)

    response = TestClient(app).get("/api/alpha/overview")
    assert response.status_code == 200
    assert response.json() == {"source": "nested"}


def test_schema_version_must_be_1(tmp_path: Path) -> None:
    _write_project(tmp_path, "alpha", _manifest(schemaVersion=2))
    with pytest.raises(ProjectModuleError, match=r"schemaVersion: must be 1"):
        discover_project_manifests(tmp_path)


def test_id_must_match_directory_name(tmp_path: Path) -> None:
    _write_project(tmp_path, "alpha", _manifest(id="beta"))
    with pytest.raises(ProjectModuleError, match="does not match project directory name"):
        discover_project_manifests(tmp_path)


@pytest.mark.parametrize("package_name", ["system-monitor", "123abc", "System", "class"])
def test_invalid_python_package_is_rejected(tmp_path: Path, package_name: str) -> None:
    _write_project(tmp_path, "alpha", _manifest(pythonPackage=package_name))
    with pytest.raises(ProjectModuleError, match="pythonPackage"):
        discover_project_manifests(tmp_path)


@pytest.mark.parametrize(
    "route_base",
    ["system-monitor", "/", "/settings", "/settings/profile", "/alpha/../secret", "/alpha/%2e%2e"],
)
def test_invalid_route_base_is_rejected(tmp_path: Path, route_base: str) -> None:
    _write_project(tmp_path, "alpha", _manifest(routeBase=route_base))
    with pytest.raises(ProjectModuleError, match="routeBase"):
        discover_project_manifests(tmp_path)


@pytest.mark.parametrize(
    "api_prefix",
    ["/api", "/api/", "api/alpha", "/overview", "/api/health", "/api/health/live", "/api/../health"],
)
def test_invalid_api_prefix_is_rejected(tmp_path: Path, api_prefix: str) -> None:
    _write_project(tmp_path, "alpha", _manifest(apiPrefix=api_prefix))
    with pytest.raises(ProjectModuleError, match="apiPrefix"):
        discover_project_manifests(tmp_path)


@pytest.mark.parametrize("nav_path", ["/services", "../services", "services/../../etc"])
def test_invalid_nav_path_is_rejected(tmp_path: Path, nav_path: str) -> None:
    payload = _manifest()
    payload["nav"]["items"][0]["path"] = nav_path
    _write_project(tmp_path, "alpha", payload)
    with pytest.raises(ProjectModuleError, match="path"):
        discover_project_manifests(tmp_path)


def test_invalid_icon_is_rejected(tmp_path: Path) -> None:
    payload = _manifest()
    payload["nav"]["items"][0]["icon"] = "settings"
    _write_project(tmp_path, "alpha", payload)
    with pytest.raises(ProjectModuleError, match="icon"):
        discover_project_manifests(tmp_path)


def test_duplicate_route_base_is_rejected(tmp_path: Path) -> None:
    _write_project(tmp_path, "alpha", _manifest())
    _write_project(
        tmp_path,
        "beta",
        _manifest(
            id="beta",
            pythonPackage="proj_beta",
            routeBase="/alpha",
            apiPrefix="/api/beta",
        ),
    )
    with pytest.raises(ProjectModuleError, match="duplicate routeBase '/alpha'"):
        discover_project_manifests(tmp_path)


def test_duplicate_api_prefix_is_rejected(tmp_path: Path) -> None:
    _write_project(tmp_path, "alpha", _manifest())
    _write_project(
        tmp_path,
        "beta",
        _manifest(
            id="beta",
            pythonPackage="proj_beta",
            routeBase="/beta",
            apiPrefix="/api/alpha",
        ),
    )
    with pytest.raises(ProjectModuleError, match="duplicate apiPrefix '/api/alpha'"):
        discover_project_manifests(tmp_path)


def test_directory_without_project_json_is_skipped(tmp_path: Path) -> None:
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "readme.txt").write_text("not a project", encoding="utf-8")
    _write_project(tmp_path, "alpha", _manifest())

    discovered = discover_project_manifests(tmp_path)

    assert [item.id for item in discovered] == ["alpha"]


def test_disabled_project_is_validated_but_not_registered(
    tmp_path: Path,
    isolated_imports: None,
) -> None:
    _write_project(tmp_path, "alpha", _manifest(enabled=False))
    app = FastAPI()
    before = list(app.routes)

    assert discover_project_manifests(tmp_path) == []
    assert register_project_routers(app, tmp_path) == []
    assert list(app.routes) == before
    assert TestClient(app).get("/api/alpha/status").status_code == 404


def test_disabled_project_with_invalid_manifest_still_fails(tmp_path: Path) -> None:
    _write_project(tmp_path, "alpha", _manifest(enabled=False, schemaVersion=2))
    with pytest.raises(ProjectModuleError, match=r"schemaVersion: must be 1"):
        discover_project_manifests(tmp_path)


def test_missing_plugin_file_is_rejected(
    tmp_path: Path,
    isolated_imports: None,
) -> None:
    _write_project(tmp_path, "alpha", _manifest())
    app = FastAPI()
    before = list(app.routes)

    with pytest.raises(ProjectModuleError, match="missing plugin.py"):
        register_project_routers(app, tmp_path)

    assert list(app.routes) == before


def test_duplicate_method_and_path_is_rejected_without_mounting(
    tmp_path: Path,
    isolated_imports: None,
) -> None:
    _write_project(
        tmp_path,
        "team",
        _manifest(
            id="team",
            pythonPackage="proj_team",
            routeBase="/team",
            apiPrefix="/api/team",
        ),
        _route_plugin("/alpha/ping"),
    )
    _write_project(
        tmp_path,
        "team-alpha",
        _manifest(
            id="team-alpha",
            pythonPackage="proj_team_alpha",
            routeBase="/team-alpha",
            apiPrefix="/api/team/alpha",
        ),
        _route_plugin("/ping"),
    )
    app = FastAPI()
    before = list(app.routes)

    with pytest.raises(ProjectModuleError, match="duplicate route GET /api/team/alpha/ping"):
        register_project_routers(app, tmp_path)

    assert list(app.routes) == before
    client = TestClient(app)
    assert client.get("/api/team/alpha/ping").status_code == 404


def test_invalid_sibling_does_not_partially_register(
    tmp_path: Path,
    isolated_imports: None,
) -> None:
    _write_project(tmp_path, "alpha", _manifest(), STATUS_PLUGIN)
    _write_project(tmp_path, "beta", _manifest(id="beta", schemaVersion=2))
    app = _app_with_health()
    before = list(app.routes)

    with pytest.raises(ProjectModuleError, match=r"schemaVersion: must be 1"):
        register_project_routers(app, tmp_path)

    assert list(app.routes) == before
    client = TestClient(app)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/alpha/status").status_code == 404
    assert not _package_loaded("proj_alpha")


def test_plugin_failure_rolls_back_earlier_import(
    tmp_path: Path,
    isolated_imports: None,
) -> None:
    _write_project(tmp_path, "alpha", _manifest(), STATUS_PLUGIN)
    _write_project(
        tmp_path,
        "beta",
        _manifest(
            id="beta",
            pythonPackage="proj_beta",
            routeBase="/beta",
            apiPrefix="/api/beta",
        ),
    )
    app = FastAPI()
    before = list(app.routes)

    with pytest.raises(ProjectModuleError, match="missing plugin.py"):
        register_project_routers(app, tmp_path)

    assert list(app.routes) == before
    assert not _package_loaded("proj_alpha")


def test_route_that_escapes_api_prefix_is_rejected(
    tmp_path: Path,
    isolated_imports: None,
) -> None:
    _write_project(tmp_path, "alpha", _manifest(), ESCAPE_PLUGIN)
    app = _app_with_health()
    before = list(app.routes)

    with pytest.raises(ProjectModuleError, match="escapes apiPrefix"):
        register_project_routers(app, tmp_path)

    assert list(app.routes) == before
    assert TestClient(app).get("/api/health").json() == {"status": "ok"}


def test_enabled_projects_are_sorted_by_nav_order(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        "zeta",
        _manifest(id="zeta", pythonPackage="proj_zeta", routeBase="/zeta", apiPrefix="/api/zeta"),
    )
    payload = _manifest(
        id="alpha",
        pythonPackage="proj_alpha",
        routeBase="/alpha",
        apiPrefix="/api/alpha",
    )
    payload["nav"]["order"] = 30
    _write_project(tmp_path, "alpha", payload)
    early = _manifest(
        id="early",
        pythonPackage="proj_early",
        routeBase="/early",
        apiPrefix="/api/early",
    )
    early["nav"]["order"] = 5
    _write_project(tmp_path, "early", early)

    discovered = discover_project_manifests(tmp_path)

    assert [item.id for item in discovered] == ["early", "zeta", "alpha"]


def _app_with_health() -> FastAPI:
    app = FastAPI()

    @app.get("/api/health")
    def read_health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _package_loaded(package: str) -> bool:
    prefix = package + "."
    return any(name == package or name.startswith(prefix) for name in sys.modules)


def _manifest(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schemaVersion": 1,
        "id": "alpha",
        "name": "Alpha",
        "description": "Example project",
        "pythonPackage": "proj_alpha",
        "routeBase": "/alpha",
        "apiPrefix": "/api/alpha",
        "enabled": True,
        "nav": {
            "section": "Infrastructure",
            "order": 10,
            "items": [
                {
                    "path": "",
                    "label": "Alpha",
                    "icon": "server",
                    "end": True,
                    "documentTitle": "Alpha",
                }
            ],
        },
    }
    payload.update(overrides)
    return payload


def _write_project(
    root: Path,
    folder: str,
    manifest: dict[str, object],
    plugin_source: str | None = None,
) -> None:
    project_dir = root / folder
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "project.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    if plugin_source is None:
        return
    package = manifest["pythonPackage"]
    if not isinstance(package, str):
        raise AssertionError("pythonPackage must be a string when writing a plugin")
    package_dir = project_dir / "backend" / package
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "plugin.py").write_text(plugin_source, encoding="utf-8")


def _mounted_http_paths(app: FastAPI) -> list[str]:
    """Flatten FastAPI's included routers into method-free full paths."""
    paths: list[str] = []

    def walk(route: object, prefix: str) -> None:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if isinstance(path, str) and methods:
            paths.append(f"{prefix}{path}")
            return
        include = getattr(route, "include_context", None)
        next_prefix = prefix
        if include is not None:
            extra = getattr(include, "prefix", "") or ""
            next_prefix = f"{prefix}{extra}"
        original = getattr(route, "original_router", None)
        children = getattr(original, "routes", None) if original is not None else None
        if not children:
            return
        for child in children:
            walk(child, next_prefix)

    for route in app.routes:
        walk(route, "")
    return paths


def _route_plugin(path: str) -> str:
    return f"""
from fastapi import APIRouter

def build_router() -> APIRouter:
    router = APIRouter()

    @router.get({path!r})
    def read_ping() -> dict[str, bool]:
        return {{"ok": True}}

    return router
"""


def test_only_system_monitor_may_use_legacy_api_root(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        "beta",
        _manifest(
            id="beta",
            pythonPackage="proj_beta",
            routeBase="/beta",
            apiPrefix="/api/beta",
            legacyApiPrefix="/api",
        ),
    )
    with pytest.raises(ProjectModuleError, match="system-monitor"):
        discover_project_manifests(tmp_path)


def test_legacy_api_prefix_cannot_claim_platform_health(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        "alpha",
        _manifest(legacyApiPrefix="/api/health"),
    )
    with pytest.raises(ProjectModuleError, match="health"):
        discover_project_manifests(tmp_path)


def test_legacy_route_cannot_overlap_route_base(tmp_path: Path) -> None:
    _write_project(tmp_path, "alpha", _manifest(legacyRouteBases=["/alpha"]))
    with pytest.raises(ProjectModuleError, match="overlaps"):
        discover_project_manifests(tmp_path)


def test_legacy_api_prefix_cannot_duplicate_another_project(tmp_path: Path) -> None:
    _write_project(tmp_path, "alpha", _manifest())
    _write_project(
        tmp_path,
        "beta",
        _manifest(
            id="beta",
            pythonPackage="proj_beta",
            routeBase="/beta",
            apiPrefix="/api/beta",
            legacyApiPrefix="/api/alpha",
        ),
    )
    with pytest.raises(ProjectModuleError, match="duplicate legacyApiPrefix '/api/alpha'"):
        discover_project_manifests(tmp_path)


def test_system_monitor_legacy_api_prefix_mounts_both_paths(
    tmp_path: Path,
    isolated_imports: None,
) -> None:
    _write_project(
        tmp_path,
        "system-monitor",
        _manifest(
            id="system-monitor",
            name="Home Lab",
            pythonPackage="proj_legacy_monitor",
            routeBase="/system-monitor",
            apiPrefix="/api/system-monitor",
            legacyApiPrefix="/api",
            legacyRouteBases=["/homelab"],
        ),
        STATUS_PLUGIN,
    )
    app = FastAPI()
    mounted = register_project_routers(app, tmp_path)

    assert [item.id for item in mounted] == ["system-monitor"]
    client = TestClient(app)
    assert client.get("/api/status").json() == {"ok": True}
    assert client.get("/api/system-monitor/status").json() == {"ok": True}
    paths = _mounted_http_paths(app)
    assert paths.count("/api/status") == 1
    assert paths.count("/api/system-monitor/status") == 1
