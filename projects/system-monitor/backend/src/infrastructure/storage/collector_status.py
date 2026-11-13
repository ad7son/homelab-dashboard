"""採集器將最近一次結果原子寫入旁檔，資料庫寫入失敗時仍盡可能保留錯誤。

旁檔不代表程序目前仍活著；健康檢查必須同時確認資料庫最新樣本的時間。
診斷紀錄本身失敗不應終止原有採集迴圈，失敗時交由日誌保留原因。
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import pathlib
import tempfile
import time
import traceback
from typing import Any

from ...domain import history

_logger = logging.getLogger("a7las.collector_status")


def status_path(db_path: pathlib.Path) -> pathlib.Path:
    """回傳指定資料庫相鄰的 .collector-status.json 路徑，不建立檔案。"""
    return pathlib.Path(f"{db_path}.collector-status.json")


def record_collector_result(
    db_path: pathlib.Path,
    *,
    sample: history.MetricSampleRecord | None = None,
    error: Exception | None = None,
) -> None:
    """原子更新最近採集結果；失敗時盡可能保留前次成功資訊。

    Args:
        db_path: 對應歷史資料庫路徑，不直接操作資料庫。
        sample: 已成功寫入的樣本；失敗時為 None。
        error: 本次嘗試的原始例外；成功時為 None。

    診斷儲存本身的失敗會記錄於日誌而不向外傳遞，避免掩蓋原始採集錯誤。
    暫存檔與目標檔位於同一目錄，透過 os.replace 避免讀者看到半份 JSON。
    """
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
            "last_success_at_ms": (
                sample.timestamp_ms
                if sample
                else previous.get("last_success_at_ms")
            ),
            "latest_sample": (
                dataclasses.asdict(sample)
                if sample
                else previous.get("latest_sample")
            ),
            "error": (
                None
                if error is None
                else {
                    "type": type(error).__name__,
                    "message": str(error),
                    "traceback": "".join(traceback.format_exception(error)),
                }
            ),
        }
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=".collector-status-",
            delete=False,
        ) as handle:
            temporary = pathlib.Path(handle.name)
            json.dump(result, handle, ensure_ascii=False, allow_nan=False)
        os.replace(temporary, destination)
    except Exception:
        _logger.exception("Unable to record collector diagnostics")
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                _logger.exception(
                    "Unable to remove temporary collector diagnostics"
                )


def read_collector_status(
    db_path: pathlib.Path,
) -> tuple[dict[str, Any] | None, str | None]:
    """讀取最近採集結果，區分缺檔與無法讀取。

    Args:
        db_path: 對應歷史資料庫路徑。

    Returns:
        (紀錄或 None, 錯誤原因或 None) 的 tuple。缺檔為 (None, None)，
        JSON 損壞、格式錯誤或存取失敗為 (None, 錯誤原因)，不假造成功紀錄。
    """
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
    """與指定資料庫相鄰的原子 JSON 診斷紀錄儲存介面。

    Attributes:
        path: 此實例使用的資料庫路徑，不是已開啟的連線。
    """

    def __init__(self, database_path: pathlib.Path) -> None:
        """綁定旁檔所屬的資料庫位置，不立即讀寫檔案。

        Args:
            database_path: 產生診斷旁檔路徑的資料庫位置。
        """
        self.path = database_path

    def read(self) -> tuple[dict[str, Any] | None, str | None]:
        """回傳 (診斷紀錄, 讀取錯誤)；缺檔時兩者均為 None。"""
        return read_collector_status(self.path)

    def record(
        self,
        *,
        sample: history.MetricSampleRecord | None = None,
        error: Exception | None = None,
    ) -> None:
        """記錄一次採集結果；診斷寫入失敗只記錄日誌。

        Args:
            sample: 已持久化的成功樣本；失敗時為 None。
            error: 原始失敗例外；成功時為 None。
        """
        record_collector_result(self.path, sample=sample, error=error)
