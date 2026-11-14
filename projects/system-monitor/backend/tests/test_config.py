"""驗證開發者設定與環境路徑覆寫。"""

import pathlib

import pytest

import monitor_backend


@pytest.mark.parametrize("days", [0, -1, 1.5, True, "30"])
def test_invalid_retention_rejected(tmp_path, days):
    config = monitor_backend.module("config")
    with pytest.raises(ValueError):
        config.Settings(tmp_path / "db", retention_days=days)


@pytest.mark.parametrize("seconds", [0, -1, float("inf"), float("nan")])
def test_invalid_interval_rejected(tmp_path, seconds):
    config = monitor_backend.module("config")
    with pytest.raises(ValueError):
        config.Settings(tmp_path / "db", collection_interval_seconds=seconds)


def test_defaults_and_permanent_retention(tmp_path, monkeypatch):
    config = monitor_backend.module("config")
    monkeypatch.setenv("A7LAS_METRICS_DB_PATH", str(tmp_path / "custom.db"))
    settings = config.Settings.from_environment()
    assert settings.database_path == tmp_path / "custom.db"
    assert settings.collection_interval_seconds == 3
    assert settings.cleanup_interval_seconds == 86400
    assert (
        config.Settings(
            settings.database_path, retention_days=None
        ).retention_days
        is None
    )
    root = pathlib.Path(config.__file__).resolve().parents[4]
    assert (
        config.default_database_path()
        == root / "data/system-monitor/metrics.db"
    )


def test_default_path_ignores_working_directory(tmp_path, monkeypatch):
    config = monitor_backend.module("config")
    root = pathlib.Path(config.__file__).resolve().parents[4]
    monkeypatch.delenv("A7LAS_METRICS_DB_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    assert config.Settings.from_environment().database_path == (
        root / "data/system-monitor/metrics.db"
    )
