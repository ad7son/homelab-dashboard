"""Project Showcase registration and info API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import app.main as platform_main
from app.modules.loader import default_projects_root, discover_project_manifests
from project_showcase.api.showcase import router as showcase_router
from project_showcase.plugin import build_router
from project_showcase.schemas.showcase import ShowcaseInfo

client = TestClient(platform_main.app)


def test_both_enabled_projects_are_discovered() -> None:
    manifests = discover_project_manifests(default_projects_root())
    assert [item.id for item in manifests] == ["system-monitor", "project-showcase"]
    showcase = manifests[1]
    assert showcase.route_base == "/project-showcase"
    assert showcase.api_prefix == "/api/project-showcase"
    assert showcase.legacy_api_prefix is None
    assert showcase.legacy_route_bases == []


def test_plugin_route_stays_relative() -> None:
    first = build_router()
    second = build_router()
    assert first is not second
    paths = [
        route.path
        for route in showcase_router.routes
        if isinstance(getattr(route, "path", None), str)
    ]
    assert paths == ["/info"]


def test_showcase_info_returns_manifest_identity() -> None:
    response = client.get("/api/project-showcase/info")
    assert response.status_code == 200
    parsed = ShowcaseInfo.model_validate(response.json())
    assert parsed.id == "project-showcase"
    assert parsed.name == "Project Showcase"
    assert parsed.status == "ok"
    assert parsed.message == "Project module loaded successfully"
    assert parsed.description != ""


def test_showcase_coexists_with_monitor_and_health() -> None:
    info = client.get("/api/project-showcase/info")
    health = client.get("/api/health")
    overview = client.get("/api/overview")
    namespaced = client.get("/api/system-monitor/overview")
    assert info.status_code == 200
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert overview.status_code == 200
    assert namespaced.status_code == 200
    assert client.get("/api/project-showcase/health").status_code == 404


def test_main_does_not_statically_register_showcase() -> None:
    source = Path(platform_main.__file__).read_text(encoding="utf-8")
    assert "project_showcase" not in source
    assert "project-showcase" not in source
