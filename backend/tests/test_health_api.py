from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import A7LAS_VERSION
from app.main import app
from system_monitor.services import services_service
from system_monitor.services.service_monitoring import ServiceMonitorResult

client = TestClient(app)


def test_health_returns_ok_and_version(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"services": False}

    def _should_not_run() -> list[ServiceMonitorResult]:
        called["services"] = True
        raise AssertionError("health must not read monitored services")

    monkeypatch.setattr(services_service, "read_monitored_services", _should_not_run)

    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": A7LAS_VERSION}
    assert A7LAS_VERSION == "0.5.0-dev"
    assert called["services"] is False
