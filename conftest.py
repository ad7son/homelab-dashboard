"""讓根目錄測試可以取得各專案的測試工具，不把多個 backend/app 放進 sys.path。

平台程式仍由 pytest.ini 的 backend 路徑載入；專案程式由平台載入器隔離。
"""
import sys

import pytest
from pathlib import Path


def pytest_configure(config: object) -> None:
    del config
    projects = Path(__file__).resolve().parent / "projects"
    if not projects.is_dir():
        return
    for project in sorted(projects.iterdir()):
        tests = project / "backend" / "tests"
        if (project / "project.json").is_file() and tests.is_dir():
            entry = str(tests.resolve())
            if entry not in sys.path:
                sys.path.insert(0, entry)


@pytest.fixture(autouse=True)
def isolated_event_storage(tmp_path, monkeypatch):
    """所有測試只寫暫存共用事件庫，避免測試污染開發者的健康報告。"""
    monkeypatch.setenv("A7LAS_OBSERVABILITY_DB_PATH", str(tmp_path / "observability.db"))
