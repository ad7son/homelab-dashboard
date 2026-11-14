"""跨專案事件格式、功能宣告與健康回應模型。"""

from __future__ import annotations

from typing import Any, Literal

import pydantic

Identifier = pydantic.constr(pattern=r"^[a-z][a-z0-9_-]*$", max_length=100)
Outcome = Literal["success", "failure", "unavailable", "unknown"]


class FeatureDefinition(pydantic.BaseModel):
    """plugin 宣告的功能；定期工作需要最大成功回報間隔。"""

    model_config = pydantic.ConfigDict(frozen=True, extra="forbid")
    id: Identifier
    name: str = pydantic.Field(min_length=1)
    description: str = ""
    mode: Literal["scheduled", "request"]
    stale_after_seconds: float | None = pydantic.Field(
        default=None, gt=0, allow_inf_nan=False
    )

    @pydantic.model_validator(mode="after")
    def validate_schedule(self) -> FeatureDefinition:
        """只有 scheduled 功能能設定時效門檻，且不可省略。"""
        if (self.mode == "scheduled") != (self.stale_after_seconds is not None):
            raise ValueError(
                "scheduled features require a deadline; "
                "request features must omit it"
            )
        return self


class ProjectDefinition(pydantic.BaseModel):
    """目前啟用專案的功能集合，由平台 manifest 與 plugin 組成。"""

    model_config = pydantic.ConfigDict(frozen=True, extra="forbid")
    id: Identifier
    name: str
    features: tuple[FeatureDefinition, ...]

    @pydantic.model_validator(mode="after")
    def validate_unique_features(self) -> ProjectDefinition:
        """拒絕同專案重複功能識別碼。"""
        ids = [feature.id for feature in self.features]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate health feature id")
        return self


class EventError(pydantic.BaseModel):
    """可序列化的原始例外，不保存例外物件本身。"""

    type: str
    message: str
    traceback: str | None = None


class Event(pydantic.BaseModel):
    """統一事件格式；只有明確 outcome 的執行結果參與健康判定。"""

    schema_version: Literal[1] = 1
    timestamp_ms: int = pydantic.Field(ge=0)
    project_id: Identifier
    feature_id: Identifier | None = None
    event: str = "log"
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    outcome: Outcome | None = None
    message: str
    duration_ms: float | None = pydantic.Field(
        default=None, ge=0, allow_inf_nan=False
    )
    source: str = ""
    error: EventError | None = None
    context: dict[str, Any] = pydantic.Field(default_factory=dict)


class FeatureHealth(pydantic.BaseModel):
    """由功能定義與持久化事件判定的健康狀態，沒有事件時不產生假成功。"""

    id: str
    name: str
    description: str
    criteria: str
    status: Literal["healthy", "issues", "unavailable", "unknown"]
    message: str
    checked_at_ms: int
    last_success_at_ms: int | None
    duration_ms: float | None
    source: str
    raw_data: dict[str, Any]
    error: EventError | None


class ProjectHealthReport(pydantic.BaseModel):
    """同次查詢的專案功能快照。"""

    project_id: str
    project_name: str
    checked_at_ms: int
    features: list[FeatureHealth]


class HealthOverview(pydantic.BaseModel):
    """所有啟用專案的健康報告，共用同一個判定時間。"""

    checked_at_ms: int
    projects: list[ProjectHealthReport]
