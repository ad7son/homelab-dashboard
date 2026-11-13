"""僅由程序入口設定日誌；平台掛載時沿用平台既有的日誌配置。"""

from __future__ import annotations

import logging


def configure_logging() -> None:
    """設定獨立採集器的 INFO 日誌；平台匯入此模組時不會執行。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
