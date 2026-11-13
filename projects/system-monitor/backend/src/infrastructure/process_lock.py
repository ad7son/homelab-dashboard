"""採集器程序鎖；API 與應用服務不依賴 fcntl。"""
from pathlib import Path

def _load_fcntl():
    """取得程序鎖時才載入 fcntl，避免其他平台僅匯入模組就失敗。"""
    import fcntl

    return fcntl


class CollectorLockError(RuntimeError):
    """無法取得採集器程序鎖時回報。"""


class CollectorProcessLock:
    """對資料庫旁的鎖檔取得非阻塞排他鎖，防止兩個採集器同時寫入。"""

    def __init__(self, db_path: Path) -> None:
        self.lock_path = Path(f"{db_path}.collector.lock")
        self._file = None

    def acquire(self) -> None:
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
        self._file = handle

    def release(self) -> None:
        if self._file is None:
            return
        try:
            lock = _load_fcntl()
            lock.flock(self._file.fileno(), lock.LOCK_UN)
        finally:
            self._file.close()
            self._file = None

    def __enter__(self) -> "CollectorProcessLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
