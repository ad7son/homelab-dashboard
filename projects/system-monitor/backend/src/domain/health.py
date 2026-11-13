"""內部健康檢查結果，不依賴 HTTP、Pydantic 或儲存技術。"""

from __future__ import annotations

import dataclasses
from typing import Any, Literal, TypeAlias

FeatureStatus: TypeAlias = Literal[
    "healthy", "issues", "unavailable", "unknown"
]


@dataclasses.dataclass(frozen=True)
class FeatureError:
    """單項功能檢查失敗所保留的原始錯誤。

    Attributes:
        type: 原始例外的型別名稱。
        message: 使用者可閱讀的結果或錯誤摘要。
        traceback: 原始錯誤堆疊；沒有堆疊時為 None。
    """

    type: str
    message: str
    traceback: str | None = None


@dataclasses.dataclass(frozen=True, kw_only=True)
class FeatureHealth:
    """單項功能的狀態、判定依據及同次檢查證據。

    Attributes:
        id: 功能的穩定識別碼。
        name: 顯示名稱。
        description: 此功能執行的工作。
        criteria: 功能健康狀態的判定依據。
        status: healthy、issues、unavailable 或 unknown，表示功能採集健康。
        message: 使用者可閱讀的結果或錯誤摘要。
        checked_at_ms: 本次檢查的 Unix 毫秒時間戳。
        last_success_at_ms: 最近一次已知成功的 Unix 毫秒時間戳；尚無成功紀錄時為 None。
        duration_ms: 單項檢查耗時，單位毫秒，以單調時鐘計算。
        source: 採集或查詢來源，供診斷畫面定位實作。
        raw_data: 與本次判定相同的完整證據；非有限浮點數轉為可閱讀字串。
        error: 本次檢查的原始錯誤；無錯誤時為 None。
    """

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


@dataclasses.dataclass(frozen=True)
class ProjectHealthReport:
    """單一專案所有受監測功能的健康報告。

    Attributes:
        project_id: project.json 中的專案識別碼。
        project_name: project.json 中的專案顯示名稱。
        checked_at_ms: 本次檢查的 Unix 毫秒時間戳。
        features: 依顯示順序排列的功能檢查結果。
    """

    project_id: str
    project_name: str
    checked_at_ms: int
    features: list[FeatureHealth]
