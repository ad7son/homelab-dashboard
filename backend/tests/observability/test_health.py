"""以可控時間驗證排程逾時、請求型功能與重啟後狀態。"""

import pytest

from app.observability import health
from app.observability import models
from app.observability import storage


def project(mode="scheduled"):
    return models.ProjectDefinition(
        id="alpha",
        name="Alpha",
        features=(
            models.FeatureDefinition(
                id="job",
                name="Job",
                mode=mode,
                stale_after_seconds=15 if mode == "scheduled" else None,
            ),
        ),
    )


def report(store, now, mode="scheduled"):
    return health.reports([project(mode)], now, store).projects[0].features[0]


def emit(store, at, outcome, **fields):
    store.append(
        models.Event(
            timestamp_ms=at,
            project_id="alpha",
            feature_id="job",
            outcome=outcome,
            message=outcome,
            **fields,
        )
    )


def test_registered_but_never_executed_scheduled_work_expires():
    store = storage.EventStore()
    store.register([project()], 1000)
    assert report(store, 1000).status == "unknown"
    assert report(store, 16000).status == "unknown"
    assert report(store, 16001).status == "issues"
    assert report(store, 16001).duration_ms is None


def test_unknown_heartbeats_do_not_reset_last_success_deadline():
    store = storage.EventStore()
    emit(store, 1000, "success")
    emit(store, 17000, "unknown")
    assert report(store, 17000).status == "issues"
    assert report(store, 17000).last_success_at_ms == 1000


def test_fail_recover_and_reopen_keep_evidence_consistent():
    store = storage.EventStore()
    emit(store, 1000, "success")
    emit(
        store,
        2000,
        "failure",
        error=models.EventError(type="OSError", message="denied"),
    )
    result = report(storage.EventStore(), 2500)
    assert result.status == "issues"
    assert result.error.type == "OSError"
    assert result.raw_data["last_event"]["outcome"] == "failure"
    assert result.last_success_at_ms == 1000
    emit(store, 3000, "success")
    result = report(storage.EventStore(), 3500)
    assert result.status == "healthy"
    assert result.error is None
    assert result.last_success_at_ms == 3000


def test_request_feature_does_not_expire_without_requests():
    store = storage.EventStore()
    store.register([project("request")], 0)
    assert report(store, 999999, "request").status == "unknown"
    emit(store, 1000, "success")
    assert report(store, 999999, "request").status == "healthy"
    emit(store, 999999, "failure")
    assert report(store, 1000000, "request").status == "issues"


def test_unavailable_hardware_is_not_zero_or_success():
    store = storage.EventStore()
    emit(store, 1000, "unavailable")
    result = report(store, 999999)
    assert result.status == "unavailable"
    assert result.last_success_at_ms is None


def test_registration_does_not_reset_evidence_after_restart():
    store = storage.EventStore()
    store.register([project()], 1000)
    emit(store, 2000, "success")
    store.register([project()], 90000)
    assert report(store, 90000).status == "issues"
    assert store.snapshot()["alpha", "job"]["first_seen_at_ms"] == 1000


def test_future_success_is_reported_as_clock_issue():
    store = storage.EventStore()
    emit(store, 30000, "success")
    assert report(store, 1000).status == "issues"


@pytest.mark.parametrize(
    "mode,deadline",
    [
        ("scheduled", None),
        ("request", 15),
        ("scheduled", 0),
        ("scheduled", float("inf")),
    ],
)
def test_invalid_feature_contract_rejected(mode, deadline):
    with pytest.raises(ValueError):
        models.FeatureDefinition(
            id="job", name="Job", mode=mode, stale_after_seconds=deadline
        )


def test_report_history_is_bounded_by_snapshot_event_id(monkeypatch):
    store = storage.EventStore()
    emit(store, 1000, "success")
    snapshot = store.snapshot()
    emit(store, 2000, "failure")
    monkeypatch.setattr(store, "snapshot", lambda: snapshot)
    result = report(store, 1500)
    assert result.status == "healthy"
    assert [event["outcome"] for event in result.raw_data["recent_events"]] == [
        "success"
    ]
