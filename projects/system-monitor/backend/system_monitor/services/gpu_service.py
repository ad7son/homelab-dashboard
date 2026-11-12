"""Ubuntu 優先的唯讀 GPU 採集，不安裝驅動、不要求 sudo，也不執行 shell。

NVIDIA 使用驅動附帶的 nvidia-smi；AMD 使用 amdgpu 的 sysfs 使用率。
其他平台或不支援的硬體回傳無資料，不能因此讓整份 overview 失敗。

驅動介面依據：
https://docs.nvidia.com/deploy/nvidia-smi/
https://kernel.org/doc/html/latest/gpu/amdgpu/thermal.html
"""

import csv
import math
import platform
import re
import subprocess
import threading
import time
from pathlib import Path

from system_monitor.schemas.gpu import GpuInfo

DRM_ROOT = Path("/sys/class/drm")
GPU_QUERY_TIMEOUT_SECONDS = 2
GPU_CACHE_SECONDS = 3
_lock = threading.Lock()
_cached: tuple[float, GpuInfo] | None = None


def _parse_usage(raw: str) -> float | None:
    """拒絕 N/A、NaN、無限值與超出範圍的讀值，不以零值替代。"""
    try:
        value = float(raw.strip())
    except ValueError:
        return None
    return value if math.isfinite(value) and 0 <= value <= 100 else None


def _read_nvidia() -> list[tuple[str, float | None]]:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=GPU_QUERY_TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return []
    if result.returncode != 0:
        return []
    devices = []
    for row in csv.reader(result.stdout.splitlines(), skipinitialspace=True):
        if len(row) == 2 and row[0].strip():
            devices.append((row[0].strip(), _parse_usage(row[1])))
    return devices


def _read_amd() -> list[tuple[str, float | None]]:
    devices = []
    try:
        cards = sorted(DRM_ROOT.glob("card[0-9]*"))
    except OSError:
        return []
    for card in cards:
        # 排除 card0-HDMI-A-1 等連接埠，只採集實際 GPU 裝置一次。
        if not re.fullmatch(r"card\d+", card.name):
            continue
        try:
            device = card / "device"
            if (device / "vendor").read_text().strip().lower() != "0x1002":
                continue
            usage = _parse_usage((device / "gpu_busy_percent").read_text())
        except (OSError, UnicodeError):
            continue
        devices.append((f"AMD {card.name}", usage))
    return devices


def get_gpu_info() -> GpuInfo:
    """回傳有有效讀值的 GPU 中使用率最高者，避免多卡平均掩蓋忙碌裝置。

    程序內共用三秒快取與鎖，避免多個瀏覽器同時啟動大量 nvidia-smi。
    快取包含失敗結果，兩秒逾時後仍能保留其他主機監控功能。
    """
    global _cached
    if platform.system() != "Linux":
        return GpuInfo(status="unsupported")
    with _lock:
        now = time.monotonic()
        if _cached is not None and now - _cached[0] < GPU_CACHE_SECONDS:
            return _cached[1]
        devices = _read_nvidia() + _read_amd()
        valid = [(name, usage) for name, usage in devices if usage is not None]
        if valid:
            name, usage = max(valid, key=lambda device: device[1])
            info = GpuInfo(status="available", name=name, usage_percent=usage, device_count=len(devices))
        else:
            info = GpuInfo(device_count=len(devices))
        _cached = (time.monotonic(), info)
        return info

