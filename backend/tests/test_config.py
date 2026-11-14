"""平台設定與路徑解析測試。"""

import pathlib

from app import config


def test_default_path_and_environment_override(tmp_path, monkeypatch):
    monkeypatch.delenv("A7LAS_OBSERVABILITY_DB_PATH")
    assert config.event_database_path().parts[-3:] == (
        "data",
        "platform",
        "observability.db",
    )
    monkeypatch.setenv(
        "A7LAS_OBSERVABILITY_DB_PATH", str(tmp_path / "other.db")
    )
    assert config.event_database_path() == tmp_path / "other.db"


def test_default_event_path_is_repository_relative(tmp_path, monkeypatch):
    monkeypatch.delenv("A7LAS_OBSERVABILITY_DB_PATH")
    monkeypatch.chdir(tmp_path)
    repository = pathlib.Path(config.__file__).resolve().parents[2]
    assert config.event_database_path() == (
        repository / "data" / "platform" / "observability.db"
    )


def test_event_path_can_be_relative_to_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("A7LAS_OBSERVABILITY_DB_PATH", "custom/events.db")
    assert config.event_database_path() == tmp_path / "custom" / "events.db"
