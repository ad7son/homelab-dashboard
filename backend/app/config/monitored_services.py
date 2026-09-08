"""Central configuration for V1 read-only systemd service monitoring.

Unit names are defined only here so readers/APIs do not scatter literals.
`required` means the unit is expected in the official Home Lab deployment;
it does not mean one missing/failed unit fails the entire services listing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class MonitoredServiceConfig:
    """Immutable monitored-service definition for A7LAS V1."""

    key: str
    display_name: str
    unit: str
    required: bool


MONITORED_SERVICES: Tuple[MonitoredServiceConfig, ...] = (
    MonitoredServiceConfig(
        key="nginx",
        display_name="Nginx",
        unit="nginx.service",
        required=True,
    ),
    MonitoredServiceConfig(
        key="a7las-backend",
        display_name="A7LAS Backend",
        unit="homelab-dashboard.service",
        required=True,
    ),
    MonitoredServiceConfig(
        key="metrics-collector",
        display_name="Metrics Collector",
        unit="a7las-metrics-collector.service",
        required=True,
    ),
    MonitoredServiceConfig(
        key="ssh",
        display_name="SSH",
        unit="ssh.service",
        required=True,
    ),
    MonitoredServiceConfig(
        key="tailscale",
        display_name="Tailscale",
        unit="tailscaled.service",
        required=True,
    ),
)
