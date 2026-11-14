"""採集器程序鎖與生命週期管理；不讀取硬體，也不建立監測資料表。"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import pathlib
import sys
from collections.abc import Iterator

from .. import config

_logger = logging.getLogger(__name__)
_RETRY_SECONDS = 3.0
_SHUTDOWN_TIMEOUT_SECONDS = 5.0


class CollectorInUseError(RuntimeError):
    """同一路徑的程序鎖已由其他程序持有。"""


@contextlib.contextmanager
def process_lock(path: pathlib.Path) -> Iterator[None]:
    """持有 OS 非阻塞鎖；程序結束自動釋放，不刪鎖檔以避免 inode 競態。

    Raises:
        CollectorInUseError: 已有其他程序持鎖。
        OSError: 無法建立或開啟鎖檔。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as lock_file:
        if os.name == "nt":
            # 平台專用模組必須延遲匯入。
            import msvcrt  # pylint: disable=import-outside-toplevel,import-error

            if path.stat().st_size == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            lock_file.seek(0)
            try:
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise CollectorInUseError("Collector lock is held") from exc
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            # 平台專用模組必須延遲匯入。
            import fcntl  # pylint: disable=import-outside-toplevel

            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise CollectorInUseError("Collector lock is held") from exc
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


async def supervise(settings: config.Settings, stop: asyncio.Event) -> None:
    """選出單一 worker 管理採集器；退出後可由其他 worker 接手。

    管理鎖與實際採集鎖分開，避免 standby worker 不斷建立失敗子程序。
    單獨啟動的 CLI 仍由實際採集鎖保護。程序失敗時記錄並延遲重試，
    不中止既有歷史 API；啟動 API 不等待第一筆樣本。
    """
    lock_path = pathlib.Path(str(settings.database_path) + ".supervisor.lock")
    while not stop.is_set():
        try:
            with process_lock(lock_path):
                if not stop.is_set():
                    await _run_child(settings, stop)
        except CollectorInUseError:
            pass  # 其他 API worker 是管理者，本 worker 等待接手。
        except OSError:
            _logger.exception("Cannot start collector; will retry")
        if not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=_RETRY_SECONDS)
            except TimeoutError:
                pass


async def _run_child(settings: config.Settings, stop: asyncio.Event) -> None:
    """啟動一個子程序，等待停止或意外退出，最後回收程序及等待任務。"""
    environment = dict(os.environ)
    environment["A7LAS_METRICS_DB_PATH"] = str(settings.database_path)
    child = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "src.collector",
        "--parent-watch",
        cwd=pathlib.Path(__file__).resolve().parents[2],
        env=environment,
        stdin=asyncio.subprocess.PIPE,
    )
    _logger.info("Started collector pid=%s", child.pid)
    exited = asyncio.create_task(child.wait())
    stopping = asyncio.create_task(stop.wait())
    try:
        await asyncio.wait(
            (exited, stopping), return_when=asyncio.FIRST_COMPLETED
        )
        if exited.done() and not stop.is_set():
            _logger.warning(
                "Collector exited with code %s; will retry", child.returncode
            )
    finally:
        # EOF 通知採集器停止；API 異常退出關閉 pipe 時也有相同效果。
        if child.stdin is not None:
            child.stdin.close()
        try:
            await asyncio.wait_for(
                asyncio.shield(exited), _SHUTDOWN_TIMEOUT_SECONDS
            )
        except TimeoutError:
            _logger.warning(
                "Collector did not stop in time; killing pid=%s", child.pid
            )
            with contextlib.suppress(ProcessLookupError):
                child.kill()
            await exited
        finally:
            stopping.cancel()
            await asyncio.gather(stopping, return_exceptions=True)
