"""psutil CPU 適配器：實例保留預熱狀態，選用感測器失敗時回報 None。"""
import os
import threading
from typing import Optional
import psutil
from ...domain.metrics import CpuInfo, LoadAverage

def _get_cpu_temperature() -> Optional[float]:
    """讀取可用溫度；感測器不存在或作業系統拒絕讀取時維持 None。"""
    if not hasattr(psutil, "sensors_temperatures"):
        return None
    try:
        temps = psutil.sensors_temperatures()
    except (AttributeError, NotImplementedError, OSError):
        return None
    if not temps:
        return None
    for sensor_name in ("coretemp", "cpu_thermal", "k10temp", "zenpower"):
        if sensor_name in temps and temps[sensor_name]:
            return temps[sensor_name][0].current
    for entries in temps.values():
        if entries:
            return entries[0].current
    return None


def _get_cpu_frequency() -> Optional[float]:
    """頻率屬選用資訊，讀取失敗不應中斷 CPU 使用率回報。"""
    try:
        freq = psutil.cpu_freq()
    except (AttributeError, NotImplementedError, OSError):
        return None
    if freq is None or freq.current is None:
        return None
    return freq.current


def _get_load_average() -> Optional[LoadAverage]:
    """讀取作業系統負載；沒有此介面的平台回傳 None。"""
    try:
        load_1, load_5, load_15 = os.getloadavg()
    except (AttributeError, OSError):
        return None
    return LoadAverage(load_1=load_1, load_5=load_5, load_15=load_15)

class CpuReader:
    def __init__(self):
        self._primed = False
        self._lock = threading.Lock()

    def read(self) -> CpuInfo:
        """取得 CPU 使用率、核心數與可用的附加資訊，不讀取其他資源。"""
        with self._lock:
            if not self._primed:
                psutil.cpu_percent(interval=0.1)
                self._primed = True
        usage_percent = psutil.cpu_percent(interval=None)
        physical_cores = psutil.cpu_count(logical=False) or 0
        logical_cores = psutil.cpu_count(logical=True) or 0

        return CpuInfo(
            usage_percent=usage_percent,
            physical_cores=physical_cores,
            logical_cores=logical_cores,
            frequency=_get_cpu_frequency(),
            temperature=_get_cpu_temperature(),
            load_average=_get_load_average(),
        )
