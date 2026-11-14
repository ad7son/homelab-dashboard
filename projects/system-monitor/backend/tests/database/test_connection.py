"""驗證連線關閉、交易回滾、WAL 與重複初始化。"""

import sqlite3

import pytest

import monitor_backend


def test_connection_closes_and_rolls_back(store):
    connection = monitor_backend.module("database.connection")
    with pytest.raises(RuntimeError):
        with connection.connect(store.path) as database:
            database.execute(
                "INSERT INTO host_info (id, updated_at_ms) VALUES (1, 1)"
            )
            raise RuntimeError("abort")
    with pytest.raises(sqlite3.ProgrammingError):
        database.execute("SELECT 1")
    with connection.connect(store.path) as check:
        assert (
            check.execute("SELECT COUNT(*) FROM host_info").fetchone()[0] == 0
        )
        assert check.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_initialization_is_idempotent_and_does_not_clear(store, sample):
    connection = monitor_backend.module("database.connection")
    store.insert(sample)
    connection.initialize(store.path)
    assert len(store.get_history(0, 9000)) == 1
