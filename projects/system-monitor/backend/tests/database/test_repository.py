"""驗證真實 SQLite 的一致讀取、缺值、時間邊界與彙整。"""

import sqlite3

import pytest

import monitor_backend


def test_info_upsert_and_latest_keep_zero_and_null(store, info, sample):
    assert store.get_latest() is None
    store.update_info(info)
    assert store.get_latest() is None
    store.insert(sample)
    newer = dict(sample, timestamp_ms=6000, cpu_usage_percent=10)
    store.insert(newer)
    store.update_info(dict(info, network_ip_address="192.0.2.2"))
    latest = store.get_latest()
    assert latest["timestamp_ms"] == 6000
    assert latest["network_ip_address"] == "192.0.2.2"
    rows = store.get_history(3000, 6000)
    assert [row["timestamp_ms"] for row in rows] == [3000, 6000]
    assert rows[0]["cpu_usage_percent"] == 0
    assert rows[0]["network_download_bytes_per_second"] == 0
    assert rows[0]["gpu_usage_percent"] is None


def test_duplicate_timestamp_does_not_overwrite(store, sample):
    store.insert(sample)
    with pytest.raises(sqlite3.IntegrityError):
        store.insert(dict(sample, cpu_usage_percent=99))
    assert store.get_history(0, 9000)[0]["cpu_usage_percent"] == 0


def test_cleanup_strict_boundary_preserves_info(store, info, sample):
    store.update_info(info)
    for timestamp in (1000, 3000, 6000):
        store.insert(dict(sample, timestamp_ms=timestamp))
    assert store.delete_before(3000) == 1
    assert [r["timestamp_ms"] for r in store.get_history(0, 9000)] == [
        3000,
        6000,
    ]
    assert store.get_latest()["cpu_physical_cores"] == 4


def test_bucket_averages_ignore_null_and_do_not_fill_gaps(store, sample):
    for timestamp, value in ((3001, 0), (4000, None), (5000, 60), (12000, 90)):
        store.insert(
            dict(sample, timestamp_ms=timestamp, cpu_usage_percent=value)
        )
    rows = store.get_history(3001, 12000, 3000)
    assert [row["timestamp_ms"] for row in rows] == [3000, 12000]
    assert [row["cpu_usage_percent"] for row in rows] == [30, 90]
    assert all(row["gpu_usage_percent"] is None for row in rows)


@pytest.mark.parametrize(
    "start,end,bucket", [(-1, 0, 0), (5, 4, 0), (0, 1, -1)]
)
def test_invalid_history_window_rejected(store, start, end, bucket):
    with pytest.raises(ValueError):
        store.get_history(start, end, bucket)


def test_missing_read_only_database_is_not_created(tmp_path):
    repository = monitor_backend.module("database.repository")
    path = tmp_path / "absent.db"
    with pytest.raises(sqlite3.OperationalError):
        repository.HostRepository(path).get_latest()
    assert not path.exists()
