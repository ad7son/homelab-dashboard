"""Read-only systemd unit inspection for A7LAS service monitoring.

Invokes only ``systemctl show`` with a fixed property list. No start/stop/
restart/enable/disable/mask support and no sudo.

systemctl is never executed at import time; callers must invoke the reader.
"""

from __future__ import annotations

import logging
import subprocess
import time
from typing import Callable, Mapping, Optional, Sequence

from app.config.monitored_services import MONITORED_SERVICES, MonitoredServiceConfig
from app.services.service_monitoring import (
    ServiceMonitorResult,
    ServiceStatus,
    build_service_monitor_result,
    normalize_main_pid,
    normalize_service_status,
    unknown_service_result,
)

logger = logging.getLogger("a7las.systemd_service_reader")

SYSTEMCTL_TIMEOUT_SECONDS = 3

_SYSTEMCTL_SHOW_PROPERTIES: tuple[str, ...] = (
    "LoadState",
    "ActiveState",
    "SubState",
    "Description",
    "MainPID",
    "ActiveEnterTimestampMonotonic",
)

SystemctlShowRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
MonotonicUsClock = Callable[[], int]
WallClockMs = Callable[[], int]


def parse_systemctl_show_output(text: str) -> dict[str, str]:
    """
    Parse ``systemctl show`` KEY=VALUE lines.

    Splits each valid line on the first '=' only. Malformed lines are ignored.
    """
    properties: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip("\r")
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not key:
            continue
        properties[key] = value
    return properties


def parse_main_pid_property(raw: Optional[str]) -> Optional[int]:
    """Parse MainPID property text; invalid/empty/zero -> None."""
    if raw is None:
        return None
    token = raw.strip()
    if not token:
        return None
    try:
        return normalize_main_pid(int(token))
    except ValueError:
        return None


def parse_monotonic_us_property(raw: Optional[str]) -> Optional[int]:
    """Parse ActiveEnterTimestampMonotonic (microseconds); invalid/zero -> None."""
    if raw is None:
        return None
    token = raw.strip()
    if not token:
        return None
    try:
        value = int(token)
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


def compute_uptime_seconds(
    active_enter_monotonic_us: Optional[int],
    current_monotonic_us: int,
) -> Optional[float]:
    """Uptime from systemd monotonic enter timestamp; never negative."""
    if active_enter_monotonic_us is None or active_enter_monotonic_us <= 0:
        return None
    delta_us = current_monotonic_us - active_enter_monotonic_us
    if delta_us < 0:
        return None
    return delta_us / 1_000_000.0


def compute_started_at_timestamp_ms(
    *,
    wall_clock_ms: int,
    uptime_seconds: Optional[float],
) -> Optional[int]:
    if uptime_seconds is None:
        return None
    return int(wall_clock_ms - (uptime_seconds * 1000.0))


def _build_systemctl_show_argv(unit: str) -> list[str]:
    """Fixed show-only argv. Unit is a single argument; never a verb."""
    argv = ["systemctl", "show", unit, "--no-pager"]
    for property_name in _SYSTEMCTL_SHOW_PROPERTIES:
        argv.append(f"--property={property_name}")
    return argv


def _default_systemctl_show_runner(
    argv: Sequence[str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        capture_output=True,
        text=True,
        timeout=SYSTEMCTL_TIMEOUT_SECONDS,
        check=False,
        shell=False,
    )


def _default_monotonic_us() -> int:
    return int(time.clock_gettime(time.CLOCK_MONOTONIC) * 1_000_000)


def _default_wall_clock_ms() -> int:
    return int(time.time() * 1000)


def _run_systemctl_show(
    unit: str,
    *,
    runner: SystemctlShowRunner,
) -> subprocess.CompletedProcess[str]:
    """Narrow internal boundary: execute systemctl show for one unit only."""
    return runner(_build_systemctl_show_argv(unit))


def _optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def read_service_status(
    config: MonitoredServiceConfig,
    *,
    runner: Optional[SystemctlShowRunner] = None,
    monotonic_us: Optional[MonotonicUsClock] = None,
    wall_clock_ms: Optional[WallClockMs] = None,
) -> ServiceMonitorResult:
    """
    Read one monitored unit via ``systemctl show``.

    Query/runtime failures return status=unknown for this unit only.
    LoadState=not-found is a successful observation -> unavailable.
    """
    show_runner = runner or _default_systemctl_show_runner
    mono_clock = monotonic_us or _default_monotonic_us
    wall_clock = wall_clock_ms or _default_wall_clock_ms

    try:
        completed = _run_systemctl_show(config.unit, runner=show_runner)
    except FileNotFoundError:
        logger.warning(
            "systemctl not found while querying unit=%s",
            config.unit,
        )
        return unknown_service_result(config)
    except subprocess.TimeoutExpired:
        logger.warning(
            "systemctl show timed out for unit=%s (timeout=%ss)",
            config.unit,
            SYSTEMCTL_TIMEOUT_SECONDS,
        )
        return unknown_service_result(config)
    except OSError:
        logger.warning(
            "systemctl show OS error for unit=%s",
            config.unit,
            exc_info=True,
        )
        return unknown_service_result(config)

    if completed.returncode != 0:
        logger.warning(
            "systemctl show failed for unit=%s returncode=%s",
            config.unit,
            completed.returncode,
        )
        return unknown_service_result(config)

    properties = parse_systemctl_show_output(completed.stdout or "")
    return _result_from_properties(
        config,
        properties,
        current_monotonic_us=mono_clock(),
        current_wall_clock_ms=wall_clock(),
    )


def _result_from_properties(
    config: MonitoredServiceConfig,
    properties: Mapping[str, str],
    *,
    current_monotonic_us: int,
    current_wall_clock_ms: int,
) -> ServiceMonitorResult:
    load_state = properties.get("LoadState")
    active_state = properties.get("ActiveState")
    sub_state = properties.get("SubState")

    # Preserve raw strings (including empty) when the key was present;
    # missing keys stay None for normalization as insufficient.
    raw_load = load_state if "LoadState" in properties else None
    raw_active = active_state if "ActiveState" in properties else None
    raw_sub = sub_state if "SubState" in properties else None

    status = normalize_service_status(raw_load, raw_active)
    description = _optional_text(properties.get("Description"))
    main_pid = parse_main_pid_property(properties.get("MainPID"))

    uptime_seconds: Optional[float] = None
    started_at_timestamp_ms: Optional[int] = None
    if status is ServiceStatus.ACTIVE:
        enter_us = parse_monotonic_us_property(
            properties.get("ActiveEnterTimestampMonotonic")
        )
        uptime_seconds = compute_uptime_seconds(enter_us, current_monotonic_us)
        started_at_timestamp_ms = compute_started_at_timestamp_ms(
            wall_clock_ms=current_wall_clock_ms,
            uptime_seconds=uptime_seconds,
        )

    return build_service_monitor_result(
        config,
        status=status,
        load_state=raw_load,
        active_state=raw_active,
        sub_state=raw_sub,
        description=description,
        main_pid=main_pid,
        uptime_seconds=uptime_seconds,
        started_at_timestamp_ms=started_at_timestamp_ms,
    )


def read_monitored_services(
    *,
    runner: Optional[SystemctlShowRunner] = None,
    monotonic_us: Optional[MonotonicUsClock] = None,
    wall_clock_ms: Optional[WallClockMs] = None,
    configs: Sequence[MonitoredServiceConfig] = MONITORED_SERVICES,
) -> list[ServiceMonitorResult]:
    """
    Read all configured monitored services in central config order.

    One unit failure becomes unknown and does not abort the rest.
    """
    results: list[ServiceMonitorResult] = []
    for config in configs:
        try:
            results.append(
                read_service_status(
                    config,
                    runner=runner,
                    monotonic_us=monotonic_us,
                    wall_clock_ms=wall_clock_ms,
                )
            )
        except Exception:
            logger.exception(
                "Unexpected failure reading monitored unit=%s",
                config.unit,
            )
            results.append(unknown_service_result(config))
    return results
