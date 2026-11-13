"""Ubuntu GPU 適配器：有界 NVIDIA 指令與 AMD sysfs；不安裝驅動或使用 shell。

每個實例持有快取與鎖；不支援平台及無有效讀值時維持原有空值語意。
"""

from __future__ import annotations

import csv
import math
import pathlib
import platform
import re
import subprocess
import threading
import time

from ...domain import metrics


def _parse_usage(raw: str) -> float | None:
    """拒絕 N/A、NaN、無限值與超出範圍的讀值，不以零值替代。"""
    try:
        value = float(raw.strip())
    except ValueError:
        return None
    return value if math.isfinite(value) and 0 <= value <= 100 else None


def _read_nvidia(timeout_seconds: float) -> list[tuple[str, float | None]]:
    """以有界 nvidia-smi 指令取得 GPU 名稱與使用率，不使用 shell。

    Args:
        timeout_seconds: 子程序最長執行秒數。

    Returns:
        (名稱, 百分比或 None) 的裝置清單；指令不可用、逾時或失敗時為空清單。
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
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


def _read_amd(drm_root: pathlib.Path) -> list[tuple[str, float | None]]:
    """讀取 AMD sysfs 使用率，排除 DRM 連接埠與不可讀裝置。

    Args:
        drm_root: DRM 根目錄，通常為 /sys/class/drm；測試可改用暫存目錄。

    Returns:
        (名稱, 百分比或 None) 的裝置清單；未提供讀值檔的裝置略過。
    """
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
    """在 Linux 探測 NVIDIA／AMD，並快取結果的 GPU 採集器。"""

    def __init__(
        self,
        cache_seconds: float = 3,
        timeout_seconds: float = 2,
        drm_root: pathlib.Path = pathlib.Path("/sys/class/drm"),
    ) -> None:
        """建立 GPU 快取與指令設定，不立即啟動硬體探測。

        Args:
            cache_seconds: 成功與失敗結果的快取秒數。
            timeout_seconds: 單次 nvidia-smi 逾時秒數。
            drm_root: AMD DRM sysfs 目錄，測試可替換。
        """
        self._cache_seconds = cache_seconds
        self._timeout = timeout_seconds
        self._drm_root = drm_root
        self._cached: tuple[float, metrics.GpuInfo] | None = None
        self._lock = threading.Lock()

    def read(self) -> metrics.GpuInfo:
        """回傳有效使用率最高的 GPU；非 Linux 平台直接回報 unsupported。

        實例鎖與快取避免多個請求同時啟動大量 nvidia-smi。來源失敗也快取；
        無有效讀值維持 None，不能將缺值當成 0% 閒置。
        """
        if platform.system() != "Linux":
            return metrics.GpuInfo(status="unsupported")
        with self._lock:
            now = time.monotonic()
            if (
                self._cached is not None
                and now - self._cached[0] < self._cache_seconds
            ):
                return self._cached[1]
            devices = _read_nvidia(self._timeout) + _read_amd(self._drm_root)
            valid = [
                (name, usage) for name, usage in devices if usage is not None
            ]
            if valid:
                name, usage = max(valid, key=lambda device: device[1])
                info = metrics.GpuInfo(
                    status="available",
                    name=name,
                    usage_percent=usage,
                    device_count=len(devices),
                )
            else:
                info = metrics.GpuInfo(device_count=len(devices))
            self._cached = (time.monotonic(), info)
            return info
