from __future__ import annotations

from typing import Optional

import pytest
from fastapi.testclient import TestClient

from app.config import A7LAS_VERSION
from app.config.monitored_services import MONITORED_SERVICES
from app.main import app
from app.services.service_monitoring import ServiceMonitorResult, ServiceStatus
from app.services import services_service

client = TestClient(app)


def _result(
    index: int,
    status: ServiceStatus,
    *,
    load_state: Optional[str] = "loaded",
    active_state: Optional[str] = None,
    sub_state: Optional[str] = None,
    description: Optional[str] = "unit description",
    main_pid: Optional[int] = 100,
    uptime_seconds: Optional[float] = 12.5,
    started_at_timestamp_ms: Optional[int] = 1_700_000_000_000,
) -> ServiceMonitorResult:
    config = MONITORED_SERVICES[index]
    if active_state is None:
        active_state = status.value if status is not ServiceStatus.UNAVAILABLE else "inactive"
    if status is not ServiceStatus.ACTIVE:
        uptime_seconds = None
        started_at_timestamp_ms = None
        if status in (ServiceStatus.UNAVAILABLE, ServiceStatus.UNKNOWN, ServiceStatus.INACTIVE):
            main_pid = None
    return ServiceMonitorResult(
        key=config.key,
        display_name=config.display_name,
        unit=config.unit,
        required=config.required,
        status=status,
        load_state=load_state,
        active_state=active_state,
        sub_state=sub_state,
        description=description,
        main_pid=main_pid,
        uptime_seconds=uptime_seconds,
        started_at_timestamp_ms=started_at_timestamp_ms,
    )


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


def test_services_all_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        services_service,
        "read_monitored_services",
        lambda: [_result(i, ServiceStatus.ACTIVE, sub_state="running") for i in range(5)],
    )

    response = client.get("/api/services")
    assert response.status_code == 200
    data = response.json()

    assert data["summary"] == {
        "total": 5,
        "active": 5,
        "inactive": 0,
        "failed": 0,
        "unavailable": 0,
        "unknown": 0,
    }
    assert [service["key"] for service in data["services"]] == [
        "nginx",
        "a7las-backend",
        "metrics-collector",
        "ssh",
        "tailscale",
    ]
    assert all(service["status"] == "active" for service in data["services"])
    assert "ServiceStatus" not in response.text


def test_services_mixed_states_remain_http_200(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        services_service,
        "read_monitored_services",
        lambda: [
            _result(0, ServiceStatus.ACTIVE, sub_state="running"),
            _result(1, ServiceStatus.ACTIVE, sub_state="exited", main_pid=None),
            _result(2, ServiceStatus.FAILED, active_state="failed", sub_state="failed"),
            _result(3, ServiceStatus.INACTIVE, active_state="inactive", sub_state="dead"),
            _result(
                4,
                ServiceStatus.UNKNOWN,
                load_state=None,
                active_state=None,
                sub_state=None,
                description=None,
            ),
        ],
    )

    response = client.get("/api/services")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == {
        "total": 5,
        "active": 2,
        "inactive": 1,
        "failed": 1,
        "unavailable": 0,
        "unknown": 1,
    }
    assert [service["status"] for service in data["services"]] == [
        "active",
        "active",
        "failed",
        "inactive",
        "unknown",
    ]


def test_services_unavailable_serialized_distinctly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        services_service,
        "read_monitored_services",
        lambda: [
            _result(0, ServiceStatus.ACTIVE),
            _result(
                1,
                ServiceStatus.UNAVAILABLE,
                load_state="not-found",
                active_state="inactive",
                sub_state="dead",
                description=None,
            ),
            _result(2, ServiceStatus.ACTIVE),
            _result(3, ServiceStatus.ACTIVE),
            _result(4, ServiceStatus.ACTIVE),
        ],
    )

    response = client.get("/api/services")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["unavailable"] == 1
    assert data["summary"]["unknown"] == 0
    assert data["services"][1]["status"] == "unavailable"
    assert data["services"][1]["load_state"] == "not-found"


def test_services_optional_fields_serialize_as_json_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        services_service,
        "read_monitored_services",
        lambda: [
            _result(
                0,
                ServiceStatus.INACTIVE,
                active_state="inactive",
                sub_state="dead",
                description=None,
                main_pid=None,
                uptime_seconds=None,
                started_at_timestamp_ms=None,
            ),
            *[_result(i, ServiceStatus.ACTIVE) for i in range(1, 5)],
        ],
    )

    response = client.get("/api/services")
    assert response.status_code == 200
    service = response.json()["services"][0]
    assert service["description"] is None
    assert service["main_pid"] is None
    assert service["uptime_seconds"] is None
    assert service["started_at_timestamp_ms"] is None
