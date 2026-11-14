"""根據功能宣告及事件快照判定健康；不執行硬體讀取或主動探測。"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from app.observability import models
from app.observability import storage


def _feature(
    definition: models.FeatureDefinition,
    state: dict[str, Any] | None,
    checked_at_ms: int,
) -> models.FeatureHealth:
    """同一份持久化事件同時決定狀態、說明與原始證據。"""
    state = state or {}
    payload = state.get("payload_json")
    event = (
        models.Event.model_validate(json.loads(payload)) if payload else None
    )
    success = state.get("last_success_at_ms")
    first_seen = state.get("first_seen_at_ms", checked_at_ms)
    anchor = success if success is not None else first_seen
    status, message = "unknown", "尚無執行結果，不代表功能已通過檢查"
    if event is not None:
        status = {
            "success": "healthy",
            "failure": "issues",
            "unavailable": "unavailable",
            "unknown": "unknown",
        }[event.outcome]
        message = event.message
    if definition.mode == "scheduled" and status != "unavailable":
        if anchor > checked_at_ms + 5000:
            status, message = "issues", "回報時間超前，請確認主機時鐘"
        elif checked_at_ms - anchor > definition.stale_after_seconds * 1000:
            status, message = (
                "issues",
                f"超過 {definition.stale_after_seconds:g} 秒沒有成功回報",
            )
    criteria = (
        f"最近一次執行結果，且須在 {definition.stale_after_seconds:g} 秒內成功回報"
        if definition.mode == "scheduled"
        else "依最近一次實際請求結果判定；沒有請求不算異常，不代表已主動探測"
    )
    return models.FeatureHealth(
        id=definition.id,
        name=definition.name,
        description=definition.description,
        criteria=criteria,
        status=status,
        message=message,
        checked_at_ms=checked_at_ms,
        last_success_at_ms=success,
        duration_ms=event.duration_ms if event else None,
        source=event.source if event else "platform event log",
        raw_data={
            "definition": definition.model_dump(mode="json"),
            "first_seen_at_ms": state.get("first_seen_at_ms"),
            "last_event_id": state.get("last_event_id"),
            "last_event": event.model_dump(mode="json") if event else None,
            "last_success_at_ms": success,
        },
        error=event.error if event and event.outcome == "failure" else None,
    )


def reports(
    projects: Sequence[models.ProjectDefinition],
    now_ms: int,
    store: storage.EventStore | None = None,
) -> models.HealthOverview:
    """以單一資料庫快照與判定時間組成所有專案報告。"""
    store = store or storage.EventStore()
    states = store.snapshot()
    projects_reports = []
    for project in projects:
        features = []
        for definition in project.features:
            feature = _feature(
                definition, states.get((project.id, definition.id)), now_ms
            )
            event_id = feature.raw_data["last_event_id"]
            # 查詢不得混入快照之後才寫入的事件，以免診斷證據與狀態錯置。
            feature.raw_data["recent_events"] = (
                store.recent(
                    project_id=project.id,
                    feature_id=definition.id,
                    before_id=event_id + 1,
                    limit=5,
                )
                if event_id is not None
                else []
            )
            features.append(feature)
        projects_reports.append(
            models.ProjectHealthReport(
                project_id=project.id,
                project_name=project.name,
                checked_at_ms=now_ms,
                features=features,
            )
        )
    return models.HealthOverview(
        checked_at_ms=now_ms, projects=projects_reports
    )
