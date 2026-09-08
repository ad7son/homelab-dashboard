from __future__ import annotations

import pytest

from app.config import MONITORED_SERVICES, MonitoredServiceConfig
from app.config.monitored_services import MONITORED_SERVICES as DIRECT_SERVICES


def test_exactly_five_monitored_services() -> None:
    assert len(MONITORED_SERVICES) == 5
    assert MONITORED_SERVICES is DIRECT_SERVICES


def test_monitored_service_order() -> None:
    assert [service.key for service in MONITORED_SERVICES] == [
        "nginx",
        "a7las-backend",
        "metrics-collector",
        "ssh",
        "tailscale",
    ]


def test_monitored_service_keys_and_units_are_unique() -> None:
    keys = [service.key for service in MONITORED_SERVICES]
    units = [service.unit for service in MONITORED_SERVICES]
    assert len(keys) == len(set(keys))
    assert len(units) == len(set(units))


def test_monitored_service_display_names_and_required() -> None:
    for service in MONITORED_SERVICES:
        assert isinstance(service, MonitoredServiceConfig)
        assert service.display_name.strip()
        assert service.required is True
        assert service.unit.endswith(".service")


def test_monitored_service_expected_units() -> None:
    by_key = {service.key: service for service in MONITORED_SERVICES}
    assert by_key["nginx"].unit == "nginx.service"
    assert by_key["a7las-backend"].unit == "homelab-dashboard.service"
    assert by_key["metrics-collector"].unit == "a7las-metrics-collector.service"
    assert by_key["ssh"].unit == "ssh.service"
    assert by_key["tailscale"].unit == "tailscaled.service"


def test_monitored_service_configs_are_immutable() -> None:
    service = MONITORED_SERVICES[0]
    with pytest.raises(Exception):
        service.key = "mutated"  # type: ignore[misc]
    with pytest.raises(Exception):
        MONITORED_SERVICES[0] = MonitoredServiceConfig(  # type: ignore[index]
            key="x",
            display_name="X",
            unit="x.service",
            required=True,
        )
