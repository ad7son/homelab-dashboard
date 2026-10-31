"""Platform startup when projects are missing, invalid, or fail to load."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.manifest import ProjectModuleError
from tests.test_module_loader import STATUS_PLUGIN, _manifest, _write_project

BROKEN_PLUGIN = """
from fastapi import APIRouter

def build_router() -> APIRouter:
    raise RuntimeError("plugin exploded")
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


def test_health_remains_available_without_projects(tmp_path: Path) -> None:
    application = create_app(tmp_path / "missing-projects")
    client = TestClient(application)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert client.get("/api/overview").status_code == 404


def test_invalid_manifest_refuses_startup(tmp_path: Path) -> None:
    project = tmp_path / "broken"
    project.mkdir()
    (project / "project.json").write_text("{", encoding="utf-8")
    with pytest.raises(ProjectModuleError, match="invalid JSON"):
        create_app(tmp_path)


def test_invalid_plugin_does_not_leave_a_usable_partial_app(
    tmp_path: Path,
    isolated_imports: None,
) -> None:
    _write_project(tmp_path, "alpha", _manifest(), STATUS_PLUGIN)
    _write_project(
        tmp_path,
        "beta",
        _manifest(
            id="beta",
            name="Beta",
            pythonPackage="proj_beta",
            routeBase="/beta",
            apiPrefix="/api/beta",
        ),
        BROKEN_PLUGIN,
    )
    with pytest.raises(ProjectModuleError, match="plugin exploded"):
        create_app(tmp_path)

    healthy = create_app(tmp_path / "empty")
    client = TestClient(healthy)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/alpha/status").status_code == 404
