"""Compose public /api/services payload from domain service monitoring results."""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from app.schemas.services import (
    MonitoredService,
    ServicesResponse,
    ServicesSummary,
    ServiceStatusValue,
)
from app.services.service_monitoring import ServiceMonitorResult, ServiceStatus
from app.services.systemd_service_reader import read_monitored_services

MonitoredServicesReader = Callable[..., list[ServiceMonitorResult]]


def get_services_response(
    *,
    reader: Optional[MonitoredServicesReader] = None,
) -> ServicesResponse:
    """
    Read monitored services and build the public API response.

    Per-service systemd query failures are already isolated by the reader as
    status=unknown and remain HTTP-success monitoring data.
    """
    read = reader or read_monitored_services
    results = read()
    services = [to_monitored_service_schema(result) for result in results]
    return ServicesResponse(
        summary=build_services_summary(services),
        services=services,
    )


def to_monitored_service_schema(result: ServiceMonitorResult) -> MonitoredService:
    return MonitoredService(
        key=result.key,
        display_name=result.display_name,
        unit=result.unit,
        required=result.required,
        status=ServiceStatusValue(result.status.value),
        load_state=result.load_state,
        active_state=result.active_state,
        sub_state=result.sub_state,
        description=result.description,
        main_pid=result.main_pid,
        uptime_seconds=result.uptime_seconds,
        started_at_timestamp_ms=result.started_at_timestamp_ms,
    )


def build_services_summary(
    services: Sequence[MonitoredService],
) -> ServicesSummary:
    counts = {
        ServiceStatus.ACTIVE.value: 0,
        ServiceStatus.INACTIVE.value: 0,
        ServiceStatus.FAILED.value: 0,
        ServiceStatus.UNAVAILABLE.value: 0,
        ServiceStatus.UNKNOWN.value: 0,
    }
    for service in services:
        counts[service.status.value] += 1

    return ServicesSummary(
        total=len(services),
        active=counts[ServiceStatus.ACTIVE.value],
        inactive=counts[ServiceStatus.INACTIVE.value],
        failed=counts[ServiceStatus.FAILED.value],
        unavailable=counts[ServiceStatus.UNAVAILABLE.value],
        unknown=counts[ServiceStatus.UNKNOWN.value],
    )
