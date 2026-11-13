"""採集器將最近一次結果原子寫入旁檔，資料庫寫入失敗時仍盡可能保留錯誤。

旁檔不代表程序目前仍活著；健康檢查必須同時確認資料庫最新樣本的時間。
診斷紀錄本身失敗不應終止原有採集迴圈，失敗時交由日誌保留原因。
"""

import json
import logging
import os
import tempfile
import time
import traceback
from dataclasses import asdict
from pathlib import Path

from ...domain.history import MetricSampleRecord

logger = logging.getLogger("a7las.collector_status")


def status_path(db_path: Path) -> Path:
    return Path(f"{db_path}.collector-status.json")


def record_collector_result(db_path: Path, *, sample: MetricSampleRecord | None = None, error: Exception | None = None) -> None:
    temporary = None
    try:
        destination = status_path(db_path)
        previous = {}
        try:
            previous = json.loads(destination.read_text(encoding="utf-8"))
            if not isinstance(previous, dict):
                previous = {}
        except (OSError, ValueError):
            pass
        result = {
            "pid": os.getpid(),
            "last_attempt_at_ms": int(time.time() * 1000),
            "last_success_at_ms": sample.timestamp_ms if sample else previous.get("last_success_at_ms"),
            "latest_sample": asdict(sample) if sample else previous.get("latest_sample"),
            "error": None if error is None else {
                "type": type(error).__name__, "message": str(error),
                "traceback": "".join(traceback.format_exception(error)),
            },
        }
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent, prefix=".collector-status-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(result, handle, ensure_ascii=False, allow_nan=False)
        os.replace(temporary, destination)
    except Exception:
        logger.exception("Unable to record collector diagnostics")
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                logger.exception("Unable to remove temporary collector diagnostics")


def read_collector_status(db_path: Path) -> tuple[dict | None, str | None]:
    """讀取原子診斷旁檔；缺檔不假造狀態，損壞或權限錯誤保留原因。"""
    try:
        data = json.loads(status_path(db_path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("採集器診斷紀錄不是物件")
        return data, None
    except FileNotFoundError:
        return None, None
    except (OSError, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


class JsonCollectorStatusStore:
    """旁檔實作；路徑由組裝層傳入，應用服務只依賴讀寫介面。"""
    def __init__(self, database_path: Path):
        self.path = database_path

    def read(self):
        return read_collector_status(self.path)

    def record(self, *, sample=None, error=None):
        record_collector_result(self.path, sample=sample, error=error)
