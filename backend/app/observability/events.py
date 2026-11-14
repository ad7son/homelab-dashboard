"""專案共用事件介面與 Python logging 整合；紀錄故障不改變業務執行結果。"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sqlite3
import sys
import time
import traceback
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

from app.observability import config
from app.observability import models
from app.observability import storage

_logger = logging.getLogger(__name__)


def _error(exception: BaseException) -> models.EventError:
    """序列化例外與原始堆疊。"""
    return models.EventError(
        type=type(exception).__name__,
        message=str(exception),
        traceback="".join(traceback.format_exception(exception)),
    )


# 事件欄位保持明確具名，避免用無型別的任意 kwargs 隱藏共用契約。
def record(  # pylint: disable=too-many-arguments
    project_id: str,
    feature_id: str | None = None,
    *,
    outcome: models.Outcome | None = None,
    message: str,
    event: str = "execution.completed",
    level: str | None = None,
    duration_ms: float | None = None,
    source: str = "",
    error: BaseException | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """記錄標準事件；明確 outcome 才更新健康狀態，寫入故障只輸出警告。

    Args:
        project_id: manifest 專案識別碼。
        feature_id: plugin 宣告的功能識別碼；一般 log 可省略。
        outcome: 執行結果，與嚴重程度 level 分開。
        message: 給人閱讀的說明，不作為健康判定條件。
        event: 穩定事件類型。
        level: 日誌級別；未提供時 failure 使用 ERROR，其餘 INFO。
        duration_ms: 本次執行耗時，毫秒。
        source: 程式模組或操作來源。
        error: 原始例外，失敗時提供。
        context: 可 JSON 序列化的補充證據；不可寫入憑證或請求機密。
    """
    entry = models.Event(
        timestamp_ms=int(time.time() * 1000),
        project_id=project_id,
        feature_id=feature_id,
        outcome=outcome,
        message=message,
        event=event,
        level=level or ("ERROR" if outcome == "failure" else "INFO"),
        duration_ms=duration_ms,
        source=source,
        error=_error(error) if error is not None else None,
        context=context or {},
    )
    try:
        storage.EventStore().append(entry)
    except (OSError, sqlite3.Error, ValueError, TypeError):
        _logger.warning(
            "Event storage unavailable",
            exc_info=True,
            extra={"observability_persisted": True},
        )
    _logger.log(
        getattr(logging, entry.level),
        message,
        extra={
            "event_payload": entry.model_dump(mode="json"),
            "observability_persisted": True,
        },
    )


@contextlib.contextmanager
def execution(
    project_id: str,
    feature_id: str,
    *,
    context: dict[str, Any] | None = None,
    source: str = "",
) -> Iterator[None]:
    """為一次執行記錄成功或失敗及耗時，原始例外一律向外傳遞。"""
    started = time.perf_counter()
    try:
        yield
    except Exception as exc:  # pylint: disable=broad-exception-caught
        record(
            project_id,
            feature_id,
            outcome="failure",
            message="執行失敗",
            duration_ms=(time.perf_counter() - started) * 1000,
            error=exc,
            context=context,
            source=source,
        )
        raise
    record(
        project_id,
        feature_id,
        outcome="success",
        message="執行成功",
        duration_ms=(time.perf_counter() - started) * 1000,
        context=context,
        source=source,
    )


def _from_log(
    entry: logging.LogRecord,
    project_id: str,
    namespaces: Sequence[tuple[str, str]],
) -> models.Event:
    """將標準 Python log 正規化；無 outcome 的 ERROR 不冒充功能失敗。"""
    payload = getattr(entry, "event_payload", None)
    if payload is not None:
        return models.Event.model_validate(payload)
    for namespace, owner in namespaces:
        if entry.name == namespace or entry.name.startswith(namespace + "."):
            project_id = owner
            break
    level = (
        entry.levelname
        if entry.levelname in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        else "INFO"
    )
    return models.Event(
        timestamp_ms=int(entry.created * 1000),
        project_id=getattr(entry, "project_id", project_id),
        feature_id=getattr(entry, "feature_id", None),
        event="log",
        level=level,
        message=entry.getMessage(),
        source=f"{entry.name}:{entry.lineno}",
        error=(
            _error(entry.exc_info[1])
            if entry.exc_info and entry.exc_info[1]
            else None
        ),
    )


class JsonFormatter(logging.Formatter):
    """以相同事件格式輸出 console log。"""

    def __init__(
        self, project_id: str, namespaces: Sequence[tuple[str, str]]
    ) -> None:
        super().__init__()
        self._project_id, self._namespaces = project_id, namespaces

    # logging 覆寫保留標準參數名稱。
    # pylint: disable=redefined-outer-name
    def format(self, record: logging.LogRecord) -> str:
        """輸出單行 JSON，堆疊保留於 error 欄位。"""
        return _from_log(
            record, self._project_id, self._namespaces
        ).model_dump_json()


class EventHandler(logging.Handler):
    """集中保存標準 Python log；明確回報事件已寫入時不重複保存。"""

    def __init__(
        self, project_id: str, namespaces: Sequence[tuple[str, str]]
    ) -> None:
        super().__init__(level=logging.INFO)
        self._project_id, self._namespaces = project_id, namespaces

    # logging 覆寫保留標準參數名稱。
    # pylint: disable=redefined-outer-name
    def emit(self, record: logging.LogRecord) -> None:
        """保存一般紀錄，儲存故障直接寫 stderr，避免遞迴產生 log。"""
        if getattr(record, "observability_persisted", False):
            return
        try:
            storage.EventStore().append(
                _from_log(record, self._project_id, self._namespaces)
            )
            record.observability_persisted = True
        except (OSError, sqlite3.Error, ValueError, TypeError):
            sys.stderr.write("Error: shared event storage unavailable\n")


@contextlib.contextmanager
def capture_logs(
    project_id: str = "platform",
    namespaces: Sequence[tuple[str, str]] = (),
) -> Iterator[None]:
    """掛載共用 log handler 與 JSON formatter，退出時還原既有設定。"""
    root = logging.getLogger()
    old_level = root.level
    handler = EventHandler(project_id, namespaces)
    formatters = [(item, item.formatter) for item in root.handlers]
    formatter = JsonFormatter(project_id, namespaces)
    console = None
    if not any(
        isinstance(item, logging.StreamHandler) for item in root.handlers
    ):
        console = logging.StreamHandler()
        root.addHandler(console)
    for item in root.handlers:
        if isinstance(item, logging.StreamHandler):
            item.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(min(old_level, logging.INFO))
    try:
        yield
    finally:
        root.removeHandler(handler)
        handler.close()
        if console is not None:
            root.removeHandler(console)
            console.close()
        for item, previous in formatters:
            item.setFormatter(previous)
        root.setLevel(old_level)


async def _cleanup(stop: asyncio.Event) -> None:
    """每天刪除過期事件；不刪最新狀態，啟動時不執行。"""
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), config.CLEANUP_INTERVAL_SECONDS)
        except TimeoutError:
            days = config.EVENT_RETENTION_DAYS
            if days is None:
                continue
            if not isinstance(days, int) or isinstance(days, bool) or days <= 0:
                _logger.error("Invalid EVENT_RETENTION_DAYS; skipping cleanup")
                continue
            try:
                storage.EventStore().delete_before(
                    int(time.time() * 1000) - days * 86_400_000
                )
            except (OSError, sqlite3.Error):
                _logger.exception("Event cleanup failed")


@contextlib.asynccontextmanager
async def lifespan(
    projects: Sequence[models.ProjectDefinition],
    namespaces: Sequence[tuple[str, str]],
) -> AsyncIterator[None]:
    """平台啟動時登記功能並接管紀錄，專案退出後再釋放共用資源。"""
    with capture_logs(namespaces=namespaces):
        try:
            storage.EventStore().register(projects, int(time.time() * 1000))
        except (OSError, sqlite3.Error):
            _logger.exception("Cannot initialize shared event storage")
        stop = asyncio.Event()
        maintenance = asyncio.create_task(_cleanup(stop))
        try:
            yield
        finally:
            stop.set()
            await maintenance
