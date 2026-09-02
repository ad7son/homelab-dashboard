import os
from typing import Optional

import psutil

from app.schemas.cpu import CpuInfo, LoadAverage

_cpu_primed = False


def _ensure_cpu_primed() -> None:
    global _cpu_primed
    if not _cpu_primed:
        psutil.cpu_percent(interval=0.1)
        _cpu_primed = True


def _get_cpu_temperature() -> Optional[float]:
    if not hasattr(psutil, "sensors_temperatures"):
        return None
    try:
        temps = psutil.sensors_temperatures()
    except (AttributeError, NotImplementedError):
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
    try:
        freq = psutil.cpu_freq()
    except (AttributeError, NotImplementedError):
        return None
    if freq is None or freq.current is None:
        return None
    return freq.current


def _get_load_average() -> Optional[LoadAverage]:
    try:
        load_1, load_5, load_15 = os.getloadavg()
    except (AttributeError, OSError):
        return None
    return LoadAverage(load_1=load_1, load_5=load_5, load_15=load_15)


def get_cpu_info() -> CpuInfo:
    _ensure_cpu_primed()
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
