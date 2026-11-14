"""驗證共用格式、交易狀態、跨寫入者與 logging 整合。"""

import concurrent.futures
import json
import logging
import sqlite3
import os
import subprocess
import sys
import pathlib

import pytest

from app.observability import config
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


def test_event_and_state_are_persisted_and_reopenable():
    first = storage.EventStore()
    event_id = first.append(entry(context={"value": 0, "missing": None}))
    second = storage.EventStore()
    state = second.snapshot()["alpha", "job"]
    assert state["last_event_id"] == event_id
    assert state["last_success_at_ms"] == 1000
    latest = second.recent(project_id="alpha")[0]
    assert latest["schema_version"] == 1
    assert latest["context"] == {"value": 0, "missing": None}


def test_out_of_order_event_does_not_replace_newer_result():
    store = storage.EventStore()
    store.append(entry(3000, "failure"))
    store.append(entry(2000, "success"))
    state = store.snapshot()["alpha", "job"]
    assert state["last_event_at_ms"] == 3000
    assert state["last_success_at_ms"] == 2000
    assert json.loads(state["payload_json"])["outcome"] == "failure"


def test_plain_error_log_is_not_an_execution_failure():
    store = storage.EventStore()
    store.append(entry(outcome=None, level="ERROR", event="log"))
    assert store.snapshot() == {}
    assert store.recent()[0]["level"] == "ERROR"


def test_cleanup_preserves_health_evidence_and_success_time():
    store = storage.EventStore()
    store.append(entry())
    store.append(entry(2000, "failure"))
    assert store.delete_before(2000) == 1
    assert store.delete_before(3000) == 1
    assert store.recent() == []
    state = storage.EventStore().snapshot()["alpha", "job"]
    assert state["last_success_at_ms"] == 1000
    assert json.loads(state["payload_json"])["outcome"] == "failure"


def test_cursor_filters_and_limits():
    store = storage.EventStore()
    for index in range(5):
        store.append(entry(index, level="INFO" if index % 2 else "ERROR"))
    first = store.recent(project_id="alpha", feature_id="job", limit=2)
    second = store.recent(before_id=first[-1]["id"], limit=2)
    assert {row["id"] for row in first}.isdisjoint(row["id"] for row in second)
    assert len(store.recent(level="ERROR")) == 3
    assert store.recent(project_id="missing") == []
    with pytest.raises(ValueError):
        store.recent(limit=101)


def test_concurrent_writers_do_not_lose_records():
    store = storage.EventStore()
    store.initialize()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(
            pool.map(
                lambda index: storage.EventStore().append(entry(index)),
                range(20),
            )
        )
    assert len(store.recent()) == 20
    assert store.snapshot()["alpha", "job"]["last_event_at_ms"] == 19


def test_missing_read_only_store_does_not_create_file(tmp_path):
    path = tmp_path / "absent.db"
    store = storage.EventStore(path)
    assert store.snapshot() == {}
    assert store.recent() == []
    assert not path.exists()


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


def test_default_path_and_environment_override(tmp_path, monkeypatch):
    monkeypatch.delenv("A7LAS_OBSERVABILITY_DB_PATH")
    assert config.database_path().parts[-3:] == (
        "data",
        "platform",
        "observability.db",
    )
    monkeypatch.setenv(
        "A7LAS_OBSERVABILITY_DB_PATH", str(tmp_path / "other.db")
    )
    assert config.database_path() == tmp_path / "other.db"


def test_independent_process_writes_same_store():
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(
        pathlib.Path(config.__file__).resolve().parents[2]
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
