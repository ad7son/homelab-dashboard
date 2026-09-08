from __future__ import annotations

import subprocess
from typing import Callable, Mapping, Sequence

import pytest

from app.config.monitored_services import MONITORED_SERVICES, MonitoredServiceConfig
from app.services.service_monitoring import ServiceStatus
from app.services.systemd_service_reader import (
    SYSTEMCTL_TIMEOUT_SECONDS,
    _build_systemctl_show_argv,
    compute_started_at_timestamp_ms,
    compute_uptime_seconds,
    parse_main_pid_property,
    parse_systemctl_show_output,
    read_monitored_services,
    read_service_status,
)

_NGINX = MonitoredServiceConfig(
    key="nginx",
    display_name="Nginx",
    unit="nginx.service",
    required=True,
)


def _show_output(**properties: str) -> str:
    return "\n".join(f"{key}={value}" for key, value in properties.items()) + "\n"


def _ok_runner(stdout: str) -> Callable[[Sequence[str]], subprocess.CompletedProcess[str]]:
    def runner(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        assert argv[0] == "systemctl"
        assert argv[1] == "show"
        assert "--no-pager" in argv
        return subprocess.CompletedProcess(
            args=list(argv),
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    return runner


def _failing_runner(
    error: BaseException,
) -> Callable[[Sequence[str]], subprocess.CompletedProcess[str]]:
    def runner(_argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        raise error

    return runner


def test_systemctl_timeout_constant() -> None:
    assert SYSTEMCTL_TIMEOUT_SECONDS == 3


def test_systemctl_show_argv_is_show_only() -> None:
    argv = _build_systemctl_show_argv("nginx.service")
    assert argv[:4] == ["systemctl", "show", "nginx.service", "--no-pager"]
    assert all(not arg.startswith("--property=") or " " not in arg for arg in argv)
    joined = " ".join(argv)
    for verb in ("start", "stop", "restart", "enable", "disable", "mask", "unmask"):
        assert f" {verb}" not in f" {joined} "
        assert f"systemctl {verb}" not in joined


def test_parse_normal_key_value() -> None:
    props = parse_systemctl_show_output(
        _show_output(
            LoadState="loaded",
            ActiveState="active",
            SubState="running",
        )
    )
    assert props["LoadState"] == "loaded"
    assert props["ActiveState"] == "active"
    assert props["SubState"] == "running"


def test_parse_preserves_equals_in_value() -> None:
    props = parse_systemctl_show_output("Description=a=b=c\n")
    assert props["Description"] == "a=b=c"


def test_parse_empty_values_and_malformed_lines() -> None:
    text = "\n".join(
        [
            "LoadState=loaded",
            "Description=",
            "this-is-not-valid",
            "=no-key",
            "ActiveState=inactive",
        ]
    )
    props = parse_systemctl_show_output(text)
    assert props["LoadState"] == "loaded"
    assert props["Description"] == ""
    assert props["ActiveState"] == "inactive"
    assert "this-is-not-valid" not in props
    assert "" not in props


def test_parse_property_order_does_not_matter() -> None:
    first = parse_systemctl_show_output(
        "ActiveState=active\nLoadState=loaded\nMainPID=9\n"
    )
    second = parse_systemctl_show_output(
        "MainPID=9\nLoadState=loaded\nActiveState=active\n"
    )
    assert first == second


def test_read_active_service_with_uptime() -> None:
    enter_us = 1_000_000
    now_us = 4_000_000
    wall_ms = 2_000_000_000_000
    stdout = _show_output(
        LoadState="loaded",
        ActiveState="active",
        SubState="running",
        Description="A high performance web server",
        MainPID="1234",
        ActiveEnterTimestampMonotonic=str(enter_us),
    )

    result = read_service_status(
        _NGINX,
        runner=_ok_runner(stdout),
        monotonic_us=lambda: now_us,
        wall_clock_ms=lambda: wall_ms,
    )

    assert result.status is ServiceStatus.ACTIVE
    assert result.load_state == "loaded"
    assert result.active_state == "active"
    assert result.sub_state == "running"
    assert result.description == "A high performance web server"
    assert result.display_name == "Nginx"
    assert result.main_pid == 1234
    assert result.uptime_seconds == 3.0
    assert result.started_at_timestamp_ms == wall_ms - 3000


def test_read_active_exited_remains_active() -> None:
    stdout = _show_output(
        LoadState="loaded",
        ActiveState="active",
        SubState="exited",
        Description="oneshot helper",
        MainPID="0",
        ActiveEnterTimestampMonotonic="5000000",
    )
    result = read_service_status(
        _NGINX,
        runner=_ok_runner(stdout),
        monotonic_us=lambda: 8_000_000,
        wall_clock_ms=lambda: 1_000,
    )
    assert result.status is ServiceStatus.ACTIVE
    assert result.sub_state == "exited"
    assert result.main_pid is None
    assert result.uptime_seconds == 3.0


def test_read_inactive_clears_uptime() -> None:
    stdout = _show_output(
        LoadState="loaded",
        ActiveState="inactive",
        SubState="dead",
        Description="stopped",
        MainPID="0",
        ActiveEnterTimestampMonotonic="999999",
    )
    result = read_service_status(
        _NGINX,
        runner=_ok_runner(stdout),
        monotonic_us=lambda: 10_000_000,
        wall_clock_ms=lambda: 5_000,
    )
    assert result.status is ServiceStatus.INACTIVE
    assert result.uptime_seconds is None
    assert result.started_at_timestamp_ms is None


def test_read_failed_clears_uptime() -> None:
    stdout = _show_output(
        LoadState="loaded",
        ActiveState="failed",
        SubState="failed",
        Description="broken",
        MainPID="0",
        ActiveEnterTimestampMonotonic="111",
    )
    result = read_service_status(
        _NGINX,
        runner=_ok_runner(stdout),
        monotonic_us=lambda: 10_000_000,
        wall_clock_ms=lambda: 5_000,
    )
    assert result.status is ServiceStatus.FAILED
    assert result.uptime_seconds is None
    assert result.started_at_timestamp_ms is None


def test_read_not_found_is_unavailable_not_unknown() -> None:
    stdout = _show_output(
        LoadState="not-found",
        ActiveState="inactive",
        SubState="dead",
        Description="",
        MainPID="0",
        ActiveEnterTimestampMonotonic="0",
    )
    result = read_service_status(
        _NGINX,
        runner=_ok_runner(stdout),
        monotonic_us=lambda: 1,
        wall_clock_ms=lambda: 1,
    )
    assert result.status is ServiceStatus.UNAVAILABLE
    assert result.load_state == "not-found"
    assert result.main_pid is None
    assert result.uptime_seconds is None
    assert result.description is None


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError("systemctl"),
        subprocess.TimeoutExpired(cmd=["systemctl"], timeout=3),
        OSError("boom"),
    ],
)
def test_query_exceptions_become_unknown(error: BaseException) -> None:
    result = read_service_status(
        _NGINX,
        runner=_failing_runner(error),
        monotonic_us=lambda: 1,
        wall_clock_ms=lambda: 1,
    )
    assert result.status is ServiceStatus.UNKNOWN
    assert result.key == "nginx"
    assert result.unit == "nginx.service"
    assert result.load_state is None
    assert result.active_state is None
    assert result.sub_state is None
    assert result.description is None
    assert result.main_pid is None
    assert result.uptime_seconds is None
    assert result.started_at_timestamp_ms is None


def test_nonzero_exit_becomes_unknown() -> None:
    def runner(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=list(argv),
            returncode=1,
            stdout="",
            stderr="failed",
        )

    result = read_service_status(
        _NGINX,
        runner=runner,
        monotonic_us=lambda: 1,
        wall_clock_ms=lambda: 1,
    )
    assert result.status is ServiceStatus.UNKNOWN


def test_insufficient_state_output_becomes_unknown() -> None:
    result = read_service_status(
        _NGINX,
        runner=_ok_runner("Description=only\n"),
        monotonic_us=lambda: 1,
        wall_clock_ms=lambda: 1,
    )
    assert result.status is ServiceStatus.UNKNOWN


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1234", 1234),
        ("0", None),
        ("", None),
        ("abc", None),
        (None, None),
    ],
)
def test_parse_main_pid_property(raw: str | None, expected: int | None) -> None:
    assert parse_main_pid_property(raw) == expected


def test_uptime_helpers_reject_invalid_and_negative() -> None:
    assert compute_uptime_seconds(None, 100) is None
    assert compute_uptime_seconds(0, 100) is None
    assert compute_uptime_seconds(200, 100) is None
    assert compute_uptime_seconds(100, 100) == 0.0
    assert compute_started_at_timestamp_ms(wall_clock_ms=5_000, uptime_seconds=None) is None
    assert (
        compute_started_at_timestamp_ms(wall_clock_ms=5_000, uptime_seconds=1.5) == 3_500
    )


def test_read_monitored_services_all_success() -> None:
    by_unit: Mapping[str, str] = {
        config.unit: _show_output(
            LoadState="loaded",
            ActiveState="active",
            SubState="running",
            Description=f"desc-{config.key}",
            MainPID=str(1000 + index),
            ActiveEnterTimestampMonotonic="1000000",
        )
        for index, config in enumerate(MONITORED_SERVICES)
    }

    def runner(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        unit = argv[2]
        return subprocess.CompletedProcess(
            args=list(argv),
            returncode=0,
            stdout=by_unit[unit],
            stderr="",
        )

    results = read_monitored_services(
        runner=runner,
        monotonic_us=lambda: 2_000_000,
        wall_clock_ms=lambda: 10_000,
    )
    assert len(results) == 5
    assert [item.key for item in results] == [c.key for c in MONITORED_SERVICES]
    assert all(item.status is ServiceStatus.ACTIVE for item in results)
    assert results[0].main_pid == 1000
    assert results[0].uptime_seconds == 1.0


def test_read_monitored_services_isolates_one_failure() -> None:
    failing_unit = MONITORED_SERVICES[2].unit  # metrics-collector

    def runner(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        unit = argv[2]
        if unit == failing_unit:
            raise FileNotFoundError("systemctl")
        return subprocess.CompletedProcess(
            args=list(argv),
            returncode=0,
            stdout=_show_output(
                LoadState="loaded",
                ActiveState="inactive",
                SubState="dead",
                Description="ok",
                MainPID="0",
                ActiveEnterTimestampMonotonic="0",
            ),
            stderr="",
        )

    results = read_monitored_services(
        runner=runner,
        monotonic_us=lambda: 1,
        wall_clock_ms=lambda: 1,
    )
    assert len(results) == 5
    assert [item.key for item in results] == [c.key for c in MONITORED_SERVICES]
    assert results[2].status is ServiceStatus.UNKNOWN
    assert results[2].key == "metrics-collector"
    for index, item in enumerate(results):
        if index == 2:
            continue
        assert item.status is ServiceStatus.INACTIVE
