from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class ServiceStatusValue(str, Enum):
    """Public API service status strings (mirrors domain ServiceStatus values)."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class MonitoredService(BaseModel):
    key: str
    display_name: str
    unit: str
    required: bool
    status: ServiceStatusValue
    load_state: Optional[str] = None
    active_state: Optional[str] = None
    sub_state: Optional[str] = None
    description: Optional[str] = None
    main_pid: Optional[int] = None
    uptime_seconds: Optional[float] = None
    started_at_timestamp_ms: Optional[int] = None


class ServicesSummary(BaseModel):
    total: int
    active: int
    inactive: int
    failed: int
    unavailable: int
    unknown: int


class ServicesResponse(BaseModel):
    summary: ServicesSummary
    services: List[MonitoredService]
