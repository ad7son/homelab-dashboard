"""內部健康檢查結果，不依賴 HTTP、Pydantic 或儲存技術。"""
from dataclasses import dataclass
from typing import Any, Literal

FeatureStatus = Literal["healthy", "issues", "unavailable", "unknown"]


@dataclass(frozen=True)
class FeatureError:
    type: str
    message: str
    traceback: str | None = None


@dataclass(frozen=True, kw_only=True)
class FeatureHealth:
    id: str
    name: str
    description: str
    criteria: str
    status: FeatureStatus
    message: str
    checked_at_ms: int
    last_success_at_ms: int | None = None
    duration_ms: int
    source: str
    raw_data: Any = None
    error: FeatureError | None = None


@dataclass(frozen=True)
class ProjectHealthReport:
    project_id: str
    project_name: str
    checked_at_ms: int
    features: list[FeatureHealth]
