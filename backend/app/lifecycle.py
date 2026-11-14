"""依序啟動專案生命週期，並在關閉或啟動失敗時反向釋放。"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sqlite3
import time
from collections.abc import AsyncIterator

import fastapi

from app import config
from app.plugins import loader
from app.plugins import manifest
from app.observability import events
from app.observability import storage

_logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI) -> AsyncIterator[None]:
    """執行每個專案的選用 lifespan，一個專案只啟動一次。

    註冊順序沿用專案排序；AsyncExitStack 確保後續專案啟動失敗時，
    已啟動的專案仍會退出。未提供 lifespan 的專案不受影響。
    """
    async with contextlib.AsyncExitStack() as stack:
        stack.enter_context(
            events.capture_logs(
                namespaces=getattr(app.state, "project_log_namespaces", ()),
            )
        )
        try:
            storage.EventStore().register(
                getattr(app.state, "health_projects", ()),
                int(time.time() * 1000),
            )
        except (OSError, sqlite3.Error):
            _logger.exception("Cannot initialize shared event storage")
        await stack.enter_async_context(_event_maintenance())
        for project_id, factory in getattr(app.state, "project_lifespans", ()):
            await stack.enter_async_context(
                _enter_project(project_id, factory, app)
            )
        yield


@contextlib.asynccontextmanager
async def _enter_project(
    project_id: str, factory: loader.Lifespan, app: fastapi.FastAPI
) -> AsyncIterator[None]:
    """讓生命週期例外帶有專案識別碼，並保留原始例外鏈。"""
    try:
        async with factory(app):
            yield
    except manifest.ProjectModuleError:
        raise
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise manifest.ProjectModuleError(
            f"project '{project_id}': lifespan failed ({exc})"
        ) from exc


@contextlib.asynccontextmanager
async def _event_maintenance() -> AsyncIterator[None]:
    """持有清理排程，停止或啟動失敗時喚醒並回收背景工作。"""
    stop = asyncio.Event()
    task = asyncio.create_task(_cleanup_events(stop))
    try:
        yield
    finally:
        stop.set()
        await task


async def _cleanup_events(stop: asyncio.Event) -> None:
    """完整間隔後才清理；故障保留紀錄並等待下一個排程。"""
    while not stop.is_set():
        try:
            await asyncio.wait_for(
                stop.wait(), config.EVENT_CLEANUP_INTERVAL_SECONDS
            )
        except TimeoutError:
            try:
                storage.cleanup_expired(int(time.time() * 1000))
            except (OSError, sqlite3.Error, ValueError):
                _logger.exception("Event cleanup failed")
