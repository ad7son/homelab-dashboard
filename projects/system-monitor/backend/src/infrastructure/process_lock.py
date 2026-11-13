"""採集器程序鎖；API 與應用服務不依賴 fcntl。"""

from __future__ import annotations

import pathlib
import types
from typing import TextIO


def _load_fcntl() -> types.ModuleType:
    """取得程序鎖時才載入 fcntl，避免其他平台僅匯入模組就失敗。"""
    import fcntl

    return fcntl


class CollectorLockError(RuntimeError):
    """採集器程序鎖不可用或已被其他程序持有。"""


class CollectorProcessLock:
    """防止同一資料庫被多個採集器同時寫入的排他鎖。

    Attributes:
        lock_path: 與資料庫相鄰的程序鎖檔路徑。
    """

    def __init__(self, db_path: pathlib.Path) -> None:
        """建立資料庫旁的程序鎖描述，不取得鎖。

        Args:
            db_path: 需要保護的歷史資料庫位置。
        """
        self.lock_path = pathlib.Path(f"{db_path}.collector.lock")
        self._file: TextIO | None = None

    def acquire(self) -> None:
        """非阻塞取得排他鎖；鎖檔保留，鎖定由開啟的檔案描述元持有。

        Raises:
            CollectorLockError: 平台沒有 fcntl，或另一個程序已持有鎖。
            OSError: 無法建立鎖檔或發生其他作業系統錯誤。
        """
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.lock_path, "a+", encoding="utf-8")
        try:
            lock = _load_fcntl()
            lock.flock(handle.fileno(), lock.LOCK_EX | lock.LOCK_NB)
        except ModuleNotFoundError as exc:
            handle.close()
            raise CollectorLockError(
                "Collector file locking requires Linux fcntl.flock"
            ) from exc
        except BlockingIOError as exc:
            handle.close()
            raise CollectorLockError(
                f"Another metrics collector appears to be running "
                f"(lock file: {self.lock_path})"
            ) from exc
        except BaseException:
            # 清理後立即重拋，避免非預期鎖定錯誤遺留開啟的描述元。
            handle.close()
            raise
        self._file = handle

    def release(self) -> None:
        """釋放鎖並關閉描述元；未持有鎖時不做任何操作。"""
        if self._file is None:
            return
        try:
            lock = _load_fcntl()
            lock.flock(self._file.fileno(), lock.LOCK_UN)
        finally:
            self._file.close()
            self._file = None

    def __enter__(self) -> "CollectorProcessLock":
        """取得程序鎖並回傳此實例；取得失敗時向外傳遞例外。"""
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None:
        """釋放程序鎖，不抑制 with 區塊中的例外。"""
        del exc_type, exc, tb  # 情境管理器要求此介面；釋放鎖不依賴例外內容。
        self.release()
