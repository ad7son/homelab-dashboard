"""Linux NVIDIA 指令與 AMD sysfs 讀取；其他平台明確標示不支援。"""

from __future__ import annotations

import csv
import logging
import math
import pathlib
import platform
import re
import subprocess

_logger = logging.getLogger(__name__)


def _usage(raw: str) -> float | None:
    """解析百分比；N/A、非有限數與超出範圍讀值回傳 None。"""
    try:
        value = float(raw.strip())
    except ValueError:
        return None
    return value if math.isfinite(value) and 0 <= value <= 100 else None


class GpuReader:
    """啟動時識別 GPU，後續只讀使用率，不重新探測裝置名稱。"""

    def __init__(self, timeout_seconds: float = 2.0) -> None:
        """建立指令 timeout 與空裝置清單，不讀硬體。"""
        self._timeout_seconds = timeout_seconds
        self._nvidia_names: list[str] = []
        self._amd_paths: list[pathlib.Path] = []
        self._supported = platform.system() == "Linux"

    def _nvidia(self, fields: str) -> list[list[str]]:
        """執行固定用途的 NVIDIA 查詢；逾時或不可用時回傳空清單。"""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    f"--query-gpu={fields}",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired, UnicodeError):
            _logger.debug("NVIDIA query unavailable", exc_info=True)
            return []
        if result.returncode != 0:
            _logger.debug("NVIDIA query failed: %s", result.stderr.strip())
            return []
        return list(
            csv.reader(result.stdout.splitlines(), skipinitialspace=True)
        )

    def read_info(self) -> dict[str, str | int | None]:
        """識別 NVIDIA 與 AMD；多裝置名稱串列顯示，動態值使用有效最大使用率。"""
        self._nvidia_names = []
        self._amd_paths = []
        if self._supported:
            self._nvidia_names = [
                row[0].strip()
                for row in self._nvidia("name")
                if row and row[0].strip()
            ]
            for card in sorted(pathlib.Path("/sys/class/drm").glob("card*")):
                if not re.fullmatch(r"card\d+", card.name):
                    continue
                try:
                    device = card / "device"
                    if (device / "vendor").read_text().strip() == "0x1002":
                        self._amd_paths.append(device / "gpu_busy_percent")
                except OSError:
                    _logger.debug("AMD identity unavailable", exc_info=True)
        names = self._nvidia_names + [
            f"AMD {path.parent.parent.name}" for path in self._amd_paths
        ]
        return {
            "gpu_name": ", ".join(names) or None,
            "gpu_device_count": len(names),
        }

    def read(self) -> dict[str, str | float]:
        """回傳最大有效使用率；不支援、無裝置與有效零使用率分開表達。"""
        if not self._supported:
            return {"gpu_status": "unsupported"}
        values = []
        if self._nvidia_names:
            for row in self._nvidia("utilization.gpu"):
                if row:
                    value = _usage(row[0])
                    if value is not None:
                        values.append(value)
        for path in self._amd_paths:
            try:
                value = _usage(path.read_text())
            except (OSError, UnicodeError):
                _logger.warning(
                    "AMD usage unavailable: %s", path, exc_info=True
                )
                continue
            if value is not None:
                values.append(value)
        if not values:
            return {"gpu_status": "unavailable"}
        return {"gpu_status": "available", "gpu_usage_percent": max(values)}
