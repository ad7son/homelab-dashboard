from __future__ import annotations

from app.config.monitored_services import MonitoredServiceConfig
from app.services.service_monitoring import (
    ServiceMonitorResult,
    ServiceStatus,
    build_service_monitor_result,
    normalize_main_pid,
    normalize_service_status,
    unknown_service_result,
)

_CONFIG = MonitoredServiceConfig(
    key="nginx",
    display_name="Nginx",
    unit="nginx.service",
    required=True,
)


def test_normalize_loaded_active() -> None:
    assert (
        normalize_service_status("loaded", "active") is ServiceStatus.ACTIVE
    )


def test_normalize_loaded_inactive() -> None:
    assert (
        normalize_service_status("loaded", "inactive") is ServiceStatus.INACTIVE
    )


def test_normalize_loaded_failed() -> None:
    assert (
        normalize_service_status("loaded", "failed") is ServiceStatus.FAILED
    )


def test_normalize_not_found_inactive_is_unavailable() -> None:
    assert (
        normalize_service_status("not-found", "inactive")
        is ServiceStatus.UNAVAILABLE
    )


def test_normalize_not_found_failed_is_unavailable() -> None:
    assert (
        normalize_service_status("not-found", "failed")
        is ServiceStatus.UNAVAILABLE
    )


def test_normalize_unexpected_load_state_is_unknown() -> None:
    assert (
        normalize_service_status("masked", "inactive") is ServiceStatus.UNKNOWN
    )


def test_normalize_missing_or_empty_states_are_unknown() -> None:
    assert normalize_service_status(None, "active") is ServiceStatus.UNKNOWN
    assert normalize_service_status("", "active") is ServiceStatus.UNKNOWN
    assert normalize_service_status("loaded", None) is ServiceStatus.UNKNOWN
    assert normalize_service_status("loaded", "") is ServiceStatus.UNKNOWN
    assert normalize_service_status(None, None) is ServiceStatus.UNKNOWN


def test_normalize_is_case_insensitive_and_trims() -> None:
    assert (
        normalize_service_status(" Loaded ", " ACTIVE ") is ServiceStatus.ACTIVE
    )


def test_normalize_does_not_depend_on_sub_state() -> None:
    # SubState is display/debug only; ActiveState drives normalization.
    assert (
        normalize_service_status("loaded", "active") is ServiceStatus.ACTIVE
    )
    active_running = build_service_monitor_result(
        _CONFIG,
        status=ServiceStatus.ACTIVE,
        load_state="loaded",
        active_state="active",
        sub_state="running",
    )
    active_exited = build_service_monitor_result(
        _CONFIG,
        status=ServiceStatus.ACTIVE,
        load_state="loaded",
        active_state="active",
        sub_state="exited",
    )
    assert active_running.status is ServiceStatus.ACTIVE
    assert active_exited.status is ServiceStatus.ACTIVE
    assert active_running.sub_state == "running"
    assert active_exited.sub_state == "exited"


def test_inactive_and_failed_clear_uptime_fields() -> None:
    inactive = build_service_monitor_result(
        _CONFIG,
        status=ServiceStatus.INACTIVE,
        load_state="loaded",
        active_state="inactive",
        sub_state="dead",
        uptime_seconds=12.0,
        started_at_timestamp_ms=1_700_000_000_000,
        main_pid=0,
    )
    failed = build_service_monitor_result(
        _CONFIG,
        status=ServiceStatus.FAILED,
        load_state="loaded",
        active_state="failed",
        sub_state="failed",
        uptime_seconds=99.0,
        started_at_timestamp_ms=1,
        main_pid=1234,
    )

    assert inactive.uptime_seconds is None
    assert inactive.started_at_timestamp_ms is None
    assert inactive.main_pid is None
    assert failed.uptime_seconds is None
    assert failed.started_at_timestamp_ms is None
    assert failed.main_pid == 1234


def test_unavailable_preserves_raw_load_state() -> None:
    result = build_service_monitor_result(
        _CONFIG,
        status=ServiceStatus.UNAVAILABLE,
        load_state="not-found",
        active_state="inactive",
        sub_state="dead",
        uptime_seconds=5.0,
    )
    assert result.status is ServiceStatus.UNAVAILABLE
    assert result.load_state == "not-found"
    assert result.uptime_seconds is None
    assert result.started_at_timestamp_ms is None


def test_unknown_represents_individual_query_failure() -> None:
    result = unknown_service_result(_CONFIG)
    assert isinstance(result, ServiceMonitorResult)
    assert result.status is ServiceStatus.UNKNOWN
    assert result.key == "nginx"
    assert result.unit == "nginx.service"
    assert result.uptime_seconds is None
    assert result.main_pid is None
    assert result.description is None


def test_active_may_carry_uptime_and_optional_description() -> None:
    result = build_service_monitor_result(
        _CONFIG,
        status=ServiceStatus.ACTIVE,
        load_state="loaded",
        active_state="active",
        sub_state="running",
        description="A high performance web server",
        main_pid=42,
        uptime_seconds=3600.5,
        started_at_timestamp_ms=1_700_000_000_000,
    )
    assert result.description == "A high performance web server"
    assert result.display_name == "Nginx"
    assert result.main_pid == 42
    assert result.uptime_seconds == 3600.5
    assert result.started_at_timestamp_ms == 1_700_000_000_000


def test_normalize_main_pid_zero_is_none() -> None:
    assert normalize_main_pid(0) is None
    assert normalize_main_pid(None) is None
    assert normalize_main_pid(1) == 1
