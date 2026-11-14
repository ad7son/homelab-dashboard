"""平台共用健康報告與事件查詢，不放在 System Monitor 專案內。"""

from __future__ import annotations

import sqlite3
import time
from typing import Literal

import fastapi
import pydantic

from app import config

from app.observability import health
from app.observability import models
from app.observability import storage

router = fastapi.APIRouter()


class HealthResponse(pydantic.BaseModel):
    """平台存活查詢的回應，不代表各專案功能正常。"""

    status: str
    version: str


@router.get("/health", response_model=HealthResponse, tags=["health"])
def read_status() -> HealthResponse:
    """回報平台存活狀態與版本，不操作專案硬體或事件資料庫。"""
    return HealthResponse(status="ok", version=config.A7LAS_VERSION)


@router.get(
    "/project-health",
    response_model=models.HealthOverview,
    tags=["observability"],
)
def read_health(request: fastapi.Request) -> models.HealthOverview:
    """回傳目前啟用專案的健康狀態；每次依持久化證據重新判定。"""
    if not storage.EventStore().path.exists():
        raise fastapi.HTTPException(503, "Shared event storage unavailable")
    try:
        return health.reports(
            getattr(request.app.state, "health_projects", ()),
            int(time.time() * 1000),
        )
    except (OSError, sqlite3.Error) as exc:
        raise fastapi.HTTPException(
            503, "Shared event storage unavailable"
        ) from exc


@router.get(
    "/project-health/{project_id}",
    response_model=models.ProjectHealthReport,
    tags=["observability"],
)
def read_project(
    project_id: str, request: fastapi.Request
) -> models.ProjectHealthReport:
    """查詢單一專案；未啟用或不存在的專案回傳 404。"""
    projects = getattr(request.app.state, "health_projects", ())
    if not any(project.id == project_id for project in projects):
        raise fastapi.HTTPException(404, "Project not found")
    for report in read_health(request).projects:
        if report.project_id == project_id:
            return report
    raise fastapi.HTTPException(404, "Project not found")


@router.get("/logs", tags=["observability"])
def read_logs(
    project_id: str | None = None,
    feature_id: str | None = None,
    level: (
        Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | None
    ) = None,
    before_id: int | None = fastapi.Query(None, ge=1),
    limit: int = fastapi.Query(50, ge=1, le=100),
) -> dict:
    """依游標查詢事件；僅讀取資料，沒有事件時回傳空清單。"""
    if not storage.EventStore().path.exists():
        raise fastapi.HTTPException(503, "Shared event storage unavailable")
    try:
        entries = storage.EventStore().recent(
            project_id=project_id,
            feature_id=feature_id,
            level=level,
            before_id=before_id,
            limit=limit,
        )
    except (OSError, sqlite3.Error) as exc:
        raise fastapi.HTTPException(
            503, "Shared event storage unavailable"
        ) from exc
    return {
        "events": entries,
        "next_before_id": entries[-1]["id"] if len(entries) == limit else None,
    }
