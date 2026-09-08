"""Domain models and pure helpers for read-only systemd service monitoring.

Phase 5 Batch 1 establishes architecture only:
- no subprocess / systemctl execution
- no HTTP endpoints
- no service control actions

Future readers must remain inspect-only. Do not add start/stop/restart/
enable/disable/mask abstractions here.

Architectural rules preserved for later batches:
- One service query failure maps to that service's status=unknown; it must
  not require the entire multi-service listing to fail.
- Backend /api/health (future) means the FastAPI process can serve requests;
  it is independent of whether every monitored unit is healthy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.config.monitored_services import MonitoredServiceConfig


class ServiceStatus(str, Enum):
    """Normalized A7LAS service status (distinct from raw systemd states)."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ServiceMonitorResult:
    """
    Internal/domain result for one monitored unit.

    Not a public Pydantic API schema. Raw systemd properties are preserved
    separately from the normalized `status`.

    Uptime fields are meaningful only when status == active; otherwise None.
    MainPID 0 from systemd should be normalized to None before construction
    (see normalize_main_pid).
    """

    key: str
    display_name: str
    unit: str
    required: bool
    status: ServiceStatus
    load_state: Optional[str] = None
    active_state: Optional[str] = None
    sub_state: Optional[str] = None
    description: Optional[str] = None
    main_pid: Optional[int] = None
    uptime_seconds: Optional[float] = None
    started_at_timestamp_ms: Optional[int] = None


def normalize_service_status(
    load_state: Optional[str],
    active_state: Optional[str],
) -> ServiceStatus:
    """
    Map raw systemd LoadState/ActiveState strings to ServiceStatus.

    Normalization depends on LoadState/ActiveState, not SubState.
    Unexpected or insufficient values yield unknown.
    """
    load = _normalize_state_token(load_state)
    active = _normalize_state_token(active_state)

    if not load:
        return ServiceStatus.UNKNOWN

    # Unit known not to exist — prefer unavailable over unknown/failed.
    if load == "not-found":
        return ServiceStatus.UNAVAILABLE

    if load == "loaded":
        if active == "active":
            return ServiceStatus.ACTIVE
        if active == "inactive":
            return ServiceStatus.INACTIVE
        if active == "failed":
            return ServiceStatus.FAILED
        return ServiceStatus.UNKNOWN

    return ServiceStatus.UNKNOWN


def normalize_main_pid(main_pid: Optional[int]) -> Optional[int]:
    """Treat missing or systemd MainPID=0 as no meaningful application PID."""
    if main_pid is None or main_pid == 0:
        return None
    return int(main_pid)


def build_service_monitor_result(
    config: MonitoredServiceConfig,
    *,
    status: ServiceStatus,
    load_state: Optional[str] = None,
    active_state: Optional[str] = None,
    sub_state: Optional[str] = None,
    description: Optional[str] = None,
    main_pid: Optional[int] = None,
    uptime_seconds: Optional[float] = None,
    started_at_timestamp_ms: Optional[int] = None,
) -> ServiceMonitorResult:
    """
    Build a domain result from central config plus observed/raw fields.

    Enforces uptime/start-time semantics: only active status may carry values.
    """
    pid = normalize_main_pid(main_pid)
    if status is ServiceStatus.ACTIVE:
        uptime = uptime_seconds
        started_at = started_at_timestamp_ms
    else:
        uptime = None
        started_at = None

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
        main_pid=pid,
        uptime_seconds=uptime,
        started_at_timestamp_ms=started_at,
    )


def unknown_service_result(
    config: MonitoredServiceConfig,
    *,
    load_state: Optional[str] = None,
    active_state: Optional[str] = None,
    sub_state: Optional[str] = None,
    description: Optional[str] = None,
) -> ServiceMonitorResult:
    """
    Represent an individual unit query failure / uncertainty.

    Future multi-service readers should return this for one failing unit
    instead of aborting the entire listing.
    """
    return build_service_monitor_result(
        config,
        status=ServiceStatus.UNKNOWN,
        load_state=load_state,
        active_state=active_state,
        sub_state=sub_state,
        description=description,
    )


def _normalize_state_token(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()
