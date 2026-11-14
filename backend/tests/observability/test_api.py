"""驗證跨專案登記與平台 API，不依賴 System Monitor 硬體採集。"""

import sys

import pytest
from fastapi import testclient

from app import main
from app.modules import manifest
from app.observability import models
from app.observability import storage
from tests import test_module_loader


@pytest.fixture(autouse=True)
def isolated_project_modules():
    before = set(sys.modules)
    yield
    for name in set(sys.modules) - before:
        if name.startswith("_a7las_project_"):
            del sys.modules[name]


_PLUGIN = test_module_loader.STATUS_PLUGIN + """
from app.observability import models

def get_health_features():
    return (models.FeatureDefinition(id='query', name='Query', mode='request'),)
"""


def test_new_project_automatically_appears_in_platform_health(tmp_path):
    test_module_loader._write_project(
        tmp_path, "alpha", test_module_loader._manifest(), _PLUGIN
    )
    test_module_loader._write_project(
        tmp_path,
        "beta",
        test_module_loader._manifest(
            id="beta",
            name="Beta",
            pythonPackage="src",
            routeBase="/beta",
            apiPrefix="/api/beta",
        ),
        test_module_loader.STATUS_PLUGIN,
    )
    app = main.create_app(tmp_path)
    with testclient.TestClient(app) as client:
        overview = client.get("/api/project-health")
        assert overview.status_code == 200
        assert [item["project_id"] for item in overview.json()["projects"]] == [
            "alpha",
            "beta",
        ]
        assert overview.json()["projects"][1]["features"] == []
        initial = client.get("/api/project-health/alpha").json()
        assert initial["features"][0]["status"] == "unknown"
        storage.EventStore().append(
            models.Event(
                timestamp_ms=initial["checked_at_ms"],
                project_id="alpha",
                feature_id="query",
                outcome="success",
                message="done",
                context={"value": 0},
            )
        )
        result = client.get("/api/project-health/alpha").json()
        assert result["features"][0]["status"] == "healthy"
        assert (
            result["features"][0]["raw_data"]["last_event"]["context"]["value"]
            == 0
        )
        assert client.get("/api/project-health/missing").status_code == 404
        assert (
            client.get("/api/logs?project_id=alpha&feature_id=query").json()[
                "events"
            ][0]["message"]
            == "done"
        )
        assert client.get("/api/logs?limit=101").status_code == 422
        assert client.get("/api/health").status_code == 200


@pytest.mark.parametrize(
    "declaration",
    [
        "get_health_features = 1",
        "def get_health_features():\n    return [{'id': 'query', 'name': 'Q', 'mode': 'scheduled'}]",
        "def get_health_features():\n    return [models.FeatureDefinition(id='query', name='Q', mode='request')]*2",
    ],
)
def test_invalid_feature_declarations_reject_project(tmp_path, declaration):
    source = (
        test_module_loader.STATUS_PLUGIN
        + "\nfrom app.observability import models\n"
        + declaration
    )
    test_module_loader._write_project(
        tmp_path, "alpha", test_module_loader._manifest(), source
    )
    with pytest.raises(manifest.ProjectModuleError, match="alpha"):
        main.create_app(tmp_path)


def test_corrupt_store_returns_503_instead_of_fake_unknown(
    tmp_path, monkeypatch
):
    path = tmp_path / "corrupt.db"
    path.write_text("not sqlite")
    monkeypatch.setenv("A7LAS_OBSERVABILITY_DB_PATH", str(path))
    client = testclient.TestClient(main.create_app(tmp_path / "empty"))
    assert client.get("/api/project-health").status_code == 503
    assert client.get("/api/logs").status_code == 503


@pytest.mark.parametrize(
    "prefix",
    [
        "/api/project-health",
        "/api/project-health/alpha",
        "/api/logs",
        "/api/logs/search",
    ],
)
def test_observability_api_namespaces_are_reserved(tmp_path, prefix):
    test_module_loader._write_project(
        tmp_path,
        "alpha",
        test_module_loader._manifest(apiPrefix=prefix),
        test_module_loader.STATUS_PLUGIN,
    )
    with pytest.raises(manifest.ProjectModuleError, match="reserved"):
        main.create_app(tmp_path)


def test_missing_store_reports_unavailable_without_creating_file(
    tmp_path, monkeypatch
):
    path = tmp_path / "missing.db"
    monkeypatch.setenv("A7LAS_OBSERVABILITY_DB_PATH", str(path))
    client = testclient.TestClient(main.create_app(tmp_path / "empty"))
    assert client.get("/api/project-health").status_code == 503
    assert client.get("/api/logs").status_code == 503
    assert not path.exists()
