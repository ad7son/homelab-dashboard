"""採集器 CLI：python -m src.collector；匯入時不執行採集。"""

from __future__ import annotations

import argparse
import logging
import pathlib
import signal
import sys
import threading

from .. import config
from . import process
from . import runner


def _watch_parent(stop_event: threading.Event) -> None:
    """管理者關閉 pipe 或異常退出時，通知採集迴圈停止。"""
    try:
        sys.stdin.buffer.read(1)
    finally:
        stop_event.set()


def main() -> int:
    """配置日誌及停止訊號並執行採集器；啟動失敗回傳非零退出碼。"""
    parser = argparse.ArgumentParser(
        description="Collect host metrics into SQLite"
    )
    parser.add_argument(
        "--once", action="store_true", help="Collect one sample and exit"
    )
    parser.add_argument(
        "--parent-watch", action="store_true", help=argparse.SUPPRESS
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    stop_event = threading.Event()

    def stop(signum: int, frame: object) -> None:
        del signum, frame
        stop_event.set()

    if args.parent_watch:
        # 只有 plugin 管理的子程序監聽 stdin；獨立 CLI 不受終端機 EOF 影響。
        threading.Thread(
            target=_watch_parent, args=(stop_event,), daemon=True
        ).start()
    previous = {}
    try:
        settings = config.Settings.from_environment()
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, stop)
        lock_path = pathlib.Path(str(settings.database_path) + ".lock")
        with process.process_lock(lock_path):
            logging.getLogger(__name__).info(
                "Collector started: %s", settings.database_path
            )
            runner.run(settings, stop_event, once=args.once)
    except process.CollectorInUseError:
        logging.getLogger(__name__).info("Another collector is already running")
        return 2
    # 工作隔離邊界：記錄原始例外後繼續或回傳失敗退出碼。
    except Exception:  # pylint: disable=broad-exception-caught
        logging.getLogger(__name__).exception("Collector stopped with an error")
        return 1
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
