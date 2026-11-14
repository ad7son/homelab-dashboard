"""依序啟動專案生命週期，並在關閉或啟動失敗時反向釋放。"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator, Callable
from typing import AsyncContextManager

import fastapi

from app.modules import manifest
from app.observability import events

Lifespan = Callable[[fastapi.FastAPI], AsyncContextManager[None]]


@contextlib.asynccontextmanager
async def project_lifespan(app: fastapi.FastAPI) -> AsyncIterator[None]:
    """執行每個專案的選用 lifespan，一個專案只啟動一次。

    註冊順序沿用專案排序；AsyncExitStack 確保後續專案啟動失敗時，
    已啟動的專案仍會退出。未提供 lifespan 的專案不受影響。
    """
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(
            events.lifespan(
                getattr(app.state, "health_projects", ()),
                getattr(app.state, "project_log_namespaces", ()),
            )
        )
        for project_id, factory in getattr(app.state, "project_lifespans", ()):
            await stack.enter_async_context(
                _enter_project(project_id, factory, app)
            )
        yield


@contextlib.asynccontextmanager
async def _enter_project(
    project_id: str, factory: Lifespan, app: fastapi.FastAPI
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
