"""共用事件 SQLite 的持久化、交易與查詢。"""

import concurrent.futures
import json

import pytest

from app.observability import storage
from tests.observability.test_events import entry


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


def test_retention_policy_only_deletes_expired_events(monkeypatch):
    from app import config

    monkeypatch.setattr(config, "EVENT_RETENTION_DAYS", 1)
    store = storage.EventStore()
    store.append(entry(1000))
    store.append(entry(2000, "failure"))
    assert storage.cleanup_expired(86_401_500) == 1
    assert len(store.recent()) == 1
    state = store.snapshot()["alpha", "job"]
    assert state["last_success_at_ms"] == 1000
    assert json.loads(state["payload_json"])["outcome"] == "failure"


@pytest.mark.parametrize("days", [0, -1, True, 1.5, "7"])
def test_invalid_retention_does_not_delete_events(monkeypatch, days):
    from app import config

    monkeypatch.setattr(config, "EVENT_RETENTION_DAYS", days)
    store = storage.EventStore()
    store.append(entry())
    with pytest.raises(ValueError, match="EVENT_RETENTION_DAYS"):
        storage.cleanup_expired(10**12)
    assert len(store.recent()) == 1


def test_unlimited_retention_does_not_create_storage(monkeypatch):
    from app import config

    monkeypatch.setattr(config, "EVENT_RETENTION_DAYS", None)
    path = storage.EventStore().path
    assert storage.cleanup_expired(10**12) == 0
    assert not path.exists()
