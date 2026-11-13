"""僅由程序入口設定日誌；平台掛載時沿用平台既有的日誌配置。"""
import logging


def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
