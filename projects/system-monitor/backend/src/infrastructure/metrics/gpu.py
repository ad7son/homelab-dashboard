"""Ubuntu GPU 適配器：有界 NVIDIA 指令與 AMD sysfs；不安裝驅動或使用 shell。

每個實例持有快取與鎖；不支援平台及無有效讀值時維持原有空值語意。
"""
import csv
import math
import platform
import re
import subprocess
import threading
import time
from pathlib import Path
from ...domain.metrics import GpuInfo

def _parse_usage(raw: str) -> float | None:
    """拒絕 N/A、NaN、無限值與超出範圍的讀值，不以零值替代。"""
    try:
        value = float(raw.strip())
    except ValueError:
        return None
    return value if math.isfinite(value) and 0 <= value <= 100 else None


def _read_nvidia(timeout_seconds) -> list[tuple[str, float | None]]:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
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


def _read_amd(drm_root) -> list[tuple[str, float | None]]:
    devices = []
    try:
        cards = sorted(drm_root.glob("card[0-9]*"))
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

class GpuReader:
    def __init__(self, cache_seconds=3, timeout_seconds=2, drm_root=Path("/sys/class/drm")):
        self._cache_seconds = cache_seconds
        self._timeout = timeout_seconds
        self._drm_root = drm_root
        self._cached = None
        self._lock = threading.Lock()

    def read(self) -> GpuInfo:
        """回傳有有效讀值的 GPU 中使用率最高者，避免多卡平均掩蓋忙碌裝置。

        程序內共用三秒快取與鎖，避免多個瀏覽器同時啟動大量 nvidia-smi。
        快取包含失敗結果，兩秒逾時後仍能保留其他主機監控功能。
        """
        if platform.system() != "Linux":
            return GpuInfo(status="unsupported")
        with self._lock:
            now = time.monotonic()
            if self._cached is not None and now - self._cached[0] < self._cache_seconds:
                return self._cached[1]
            devices = _read_nvidia(self._timeout) + _read_amd(self._drm_root)
            valid = [(name, usage) for name, usage in devices if usage is not None]
            if valid:
                name, usage = max(valid, key=lambda device: device[1])
                info = GpuInfo(status="available", name=name, usage_percent=usage, device_count=len(devices))
            else:
                info = GpuInfo(device_count=len(devices))
            self._cached = (time.monotonic(), info)
            return info
