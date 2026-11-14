"""驗證共用格式、交易狀態、跨寫入者與 logging 整合。"""

import logging
import sqlite3
import os
import subprocess
import sys
import pathlib

import pytest

from app import config
from app.observability import events
from app.observability import models
from app.observability import storage


def entry(timestamp=1000, outcome="success", **fields):
    return models.Event(
        timestamp_ms=timestamp,
        project_id="alpha",
        feature_id="job",
        outcome=outcome,
        message="result",
        **fields,
    )


def test_execution_records_duration_and_original_error():
    with events.execution("alpha", "job"):
        pass
    with pytest.raises(RuntimeError, match="failure"):
        with events.execution("alpha", "job", context={"range": "1h"}):
            raise RuntimeError("failure")
    records = storage.EventStore().recent()
    assert records[0]["outcome"] == "failure"
    assert records[0]["duration_ms"] >= 0
    assert records[0]["error"]["type"] == "RuntimeError"
    assert "raise RuntimeError" in records[0]["error"]["traceback"]
    assert records[1]["outcome"] == "success"


def test_storage_failure_does_not_change_business_outcome(monkeypatch):
    def broken(self, event):
        raise sqlite3.OperationalError("full")

    monkeypatch.setattr(storage.EventStore, "append", broken)
    with events.execution("alpha", "job"):
        pass
    with pytest.raises(ValueError, match="original"):
        with events.execution("alpha", "job"):
            raise ValueError("original")


def test_standard_logs_use_same_format_without_double_writing():
    logger = logging.getLogger("project_namespace.module")
    old_level = logging.getLogger().level
    with events.capture_logs(namespaces=(("project_namespace", "alpha"),)):
        logger.warning("value=%s", 0)
        events.record("alpha", "job", outcome="success", message="done")
    assert logging.getLogger().level == old_level
    records = storage.EventStore().recent(project_id="alpha")
    assert len(records) == 2
    plain = next(record for record in records if record["event"] == "log")
    assert plain["message"] == "value=0"
    assert plain["outcome"] is None
    assert plain["source"].startswith("project_namespace.module:")


def test_independent_process_writes_same_store():
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(
        pathlib.Path(config.__file__).resolve().parents[1]
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.observability import events; events.record('alpha', 'job', outcome='success', message='child completed')",
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert storage.EventStore().recent()[0]["message"] == "child completed"
    assert (
        storage.EventStore().snapshot()["alpha", "job"]["last_success_at_ms"]
        is not None
    )
