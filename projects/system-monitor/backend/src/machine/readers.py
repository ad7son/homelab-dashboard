"""一般主機採集函式；每項可單獨呼叫，供 API、採集器及健康檢查重用。

合併檔案不合併取樣狀態：CPU 預熱、網路基準與磁碟鎖仍各自管理。
此處不操作資料庫、不建立背景排程，也不判定功能健康狀態。
"""
import os
import threading
import time
from typing import Dict, Optional, Union

import psutil

from .models import CpuInfo, LoadAverage, MemoryInfo, SwapInfo, NetworkInfo, DiskIoInfo, Overview
from .gpu import get_gpu_info


# ── CPU：預熱後讀取使用率，選用感測器失敗時回傳 None ──

_cpu_primed = False


def _ensure_cpu_primed() -> None:
    """首次使用先建立 CPU 使用率基準，避免直接採用尚未預熱的讀值。"""
    global _cpu_primed
    if not _cpu_primed:
        psutil.cpu_percent(interval=0.1)
        _cpu_primed = True


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


def get_cpu_info() -> CpuInfo:
    """取得 CPU 使用率、核心數與可用的附加資訊，不讀取其他資源。"""
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


# ── 記憶體：直接讀取容量、使用率與 Swap ──

def get_memory_info() -> MemoryInfo:
    """取得實體記憶體與 Swap，保留 psutil 原本的容量與百分比定義。"""
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return MemoryInfo(
        total=vm.total,
        used=vm.used,
        available=vm.available,
        usage_percent=vm.percent,
        swap=SwapInfo(
            total=swap.total,
            used=swap.used,
            usage_percent=swap.percent,
        ),
    )


# ── 網路：保留前次介面與累計流量以計算速率 ──

_previous_sample: Optional[Dict[str, Union[str, float, int]]] = None

_EXCLUDED_PREFIXES = ("lo", "docker", "veth", "br-", "tailscale", "utun")
_EXCLUDED_EXACT = frozenset({"lo0"})


def _is_excluded_interface(name: str) -> bool:
    lower = name.lower()
    if lower in _EXCLUDED_EXACT:
        return True
    return any(lower.startswith(prefix) for prefix in _EXCLUDED_PREFIXES)


def _get_interface_ipv4(name: str) -> Optional[str]:
    addrs = psutil.net_if_addrs().get(name, [])
    for addr in addrs:
        if addr.family.name == "AF_INET":
            return addr.address
    return None


def _select_primary_interface(counters: dict) -> Optional[str]:
    """從可用 IPv4 介面選出累計流量最高者，維持目前主要介面的選取規則。"""
    candidates = []

    for name, stats in counters.items():
        if _is_excluded_interface(name):
            continue
        if stats.bytes_recv == 0 and stats.bytes_sent == 0:
            continue
        ip = _get_interface_ipv4(name)
        if ip is None or ip.startswith("127."):
            continue
        candidates.append((name, stats.bytes_recv + stats.bytes_sent))

    if not candidates:
        for name in counters:
            if not _is_excluded_interface(name):
                ip = _get_interface_ipv4(name)
                if ip and not ip.startswith("127."):
                    return name
        return None

    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0]


def get_network_info() -> NetworkInfo:
    """比較同一介面的前後累計流量；首次取樣、介面切換或計數器重設時不回傳假速率。"""
    global _previous_sample

    counters = psutil.net_io_counters(pernic=True)
    interface = _select_primary_interface(counters)

    download_rate: Optional[float] = None
    upload_rate: Optional[float] = None
    ip_address: Optional[str] = None

    if interface and interface in counters:
        ip_address = _get_interface_ipv4(interface)
        current_recv = counters[interface].bytes_recv
        current_sent = counters[interface].bytes_sent
        now = time.time()

        if _previous_sample is not None and _previous_sample.get("interface") == interface:
            elapsed = now - float(_previous_sample["timestamp"])
            if elapsed > 0:
                download_rate = (current_recv - int(_previous_sample["bytes_recv"])) / elapsed
                upload_rate = (current_sent - int(_previous_sample["bytes_sent"])) / elapsed
                if download_rate < 0:
                    download_rate = None
                if upload_rate < 0:
                    upload_rate = None

        _previous_sample = {
            "interface": interface,
            "bytes_recv": current_recv,
            "bytes_sent": current_sent,
            "timestamp": now,
        }

    return NetworkInfo(
        interface=interface,
        ip_address=ip_address,
        download_rate=download_rate,
        upload_rate=upload_rate,
    )


# ── Disk I/O：使用獨立狀態與鎖管理磁碟取樣 ──

MIN_SAMPLE_INTERVAL_SECONDS = 1
_disk_io_lock = threading.Lock()
_disk_io_previous: tuple[float, int, int] | None = None
_disk_io_latest = DiskIoInfo(status="warming_up")


def get_disk_io_info() -> DiskIoInfo:
    """首次、計數器重設或讀取中斷後重新建立基準，不顯示錯誤尖峰。"""
    global _disk_io_previous, _disk_io_latest
    with _disk_io_lock:
        now = time.monotonic()
        if _disk_io_previous is not None and now - _disk_io_previous[0] < MIN_SAMPLE_INTERVAL_SECONDS:
            return _disk_io_latest
        try:
            counters = psutil.disk_io_counters(nowrap=True)
        except (OSError, AttributeError, NotImplementedError, RuntimeError):
            counters = None
        if counters is None:
            _disk_io_previous = None
            _disk_io_latest = DiskIoInfo()
            return _disk_io_latest

        current = (now, counters.read_bytes, counters.write_bytes)
        if _disk_io_previous is None:
            _disk_io_latest = DiskIoInfo(status="warming_up")
        else:
            elapsed = now - _disk_io_previous[0]
            read_delta = counters.read_bytes - _disk_io_previous[1]
            write_delta = counters.write_bytes - _disk_io_previous[2]
            if read_delta < 0 or write_delta < 0:
                _disk_io_latest = DiskIoInfo(status="warming_up")
            else:
                _disk_io_latest = DiskIoInfo(
                    status="available",
                    read_bytes_per_second=read_delta / elapsed,
                    write_bytes_per_second=write_delta / elapsed,
                )
        _disk_io_previous = current
        return _disk_io_latest


# ── 總覽：只有呼叫此函式時才組合全部五項資訊 ──

def get_overview() -> Overview:
    """組合前端使用的五項即時資料；各讀取函式仍可由採集器單獨使用。"""
    return Overview(
        cpu=get_cpu_info(),
        memory=get_memory_info(),
        network=get_network_info(),
        gpu=get_gpu_info(),
        disk_io=get_disk_io_info(),
    )
