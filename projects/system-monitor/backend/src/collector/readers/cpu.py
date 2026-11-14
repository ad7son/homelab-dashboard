"""CPU 基本資訊與非阻塞使用率取樣。"""

from __future__ import annotations

import logging
import os

import psutil

_logger = logging.getLogger(__name__)


class CpuReader:
    """由單一採集執行緒持有的 CPU 計數基準。"""

    def __init__(self) -> None:
        """建立未預熱狀態，不讀取硬體。"""
        self._primed = False

    def read_info(self) -> dict[str, int | None]:
        """讀取實體與邏輯核心數；psutil 無法識別時保留 None。"""
        return {
            "cpu_physical_cores": psutil.cpu_count(logical=False),
            "cpu_logical_cores": psutil.cpu_count(logical=True),
        }

    def read(self) -> dict[str, float | None]:
        """回傳 CPU 動態值；首次只建立使用率基準，使用率為 None。

        頻率、溫度和平均負載獨立容錯，不使可用的使用率遺失。
        """
        usage = psutil.cpu_percent(interval=None)
        if not self._primed:
            self._primed = True
            usage = None
        values = {"cpu_usage_percent": usage}
        try:
            frequency = psutil.cpu_freq()
            values["cpu_frequency_mhz"] = (
                frequency.current if frequency else None
            )
        except (OSError, NotImplementedError, AttributeError):
            _logger.debug("CPU frequency unavailable", exc_info=True)
        try:
            loads = os.getloadavg()
            values.update(
                zip(("cpu_load_1", "cpu_load_5", "cpu_load_15"), loads)
            )
        except (OSError, AttributeError):
            _logger.debug("Load average unavailable", exc_info=True)
        try:
            sensors = getattr(psutil, "sensors_temperatures", lambda: {})()
            for name in ("coretemp", "cpu_thermal", "k10temp", "zenpower"):
                if sensors.get(name):
                    values["cpu_temperature_celsius"] = sensors[name][0].current
                    break
            else:
                entries = [
                    entry for group in sensors.values() for entry in group
                ]
                if entries:
                    values["cpu_temperature_celsius"] = entries[0].current
        except (OSError, NotImplementedError, AttributeError):
            _logger.debug("CPU temperature unavailable", exc_info=True)
        return values
