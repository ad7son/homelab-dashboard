"""專案自行回報的功能健康結果；每列的狀態與原始證據來自同一次檢查。"""

from typing import Any, Literal

from pydantic import BaseModel

FeatureStatus = Literal["healthy", "issues", "unavailable", "unknown"]


class FeatureError(BaseModel):
    type: str
    message: str
    traceback: str | None = None


class FeatureHealth(BaseModel):
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


class ProjectHealthReport(BaseModel):
    project_id: str
    project_name: str
    checked_at_ms: int
    features: list[FeatureHealth]
