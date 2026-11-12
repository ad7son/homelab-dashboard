from __future__ import annotations

from monitor_backend import module as monitor_module

import pytest
from fastapi.testclient import TestClient

from app.config import A7LAS_VERSION
from app.main import app
readers = monitor_module('machine.readers')

client = TestClient(app)


def test_health_returns_ok_and_version(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"overview": False}

    def _should_not_run() -> None:
        called["overview"] = True
        raise AssertionError("platform health must not collect project metrics")

    monkeypatch.setattr(readers, "get_overview", _should_not_run)

    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": A7LAS_VERSION}
    assert A7LAS_VERSION == "0.5.0-dev"
    assert called["overview"] is False
