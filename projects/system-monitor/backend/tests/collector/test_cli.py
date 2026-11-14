"""驗證同資料庫程序鎖的互斥與釋放。"""

import pytest

import monitor_backend


def test_lock_prevents_duplicate_and_releases(tmp_path):
    cli = monitor_backend.module("collector.process")
    path = tmp_path / "collector.lock"
    with cli.process_lock(path):
        with pytest.raises(RuntimeError):
            with cli.process_lock(path):
                pytest.fail("second collector must not start")
    with cli.process_lock(path):
        assert path.exists()
