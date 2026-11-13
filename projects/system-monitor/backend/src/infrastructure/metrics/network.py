"""主要網路介面與累計流量適配器；同一實例序列化取樣避免互相覆蓋。"""

from __future__ import annotations

from collections.abc import Mapping
import threading
import time
from typing import Any

import psutil

from ...domain import metrics

_EXCLUDED_PREFIXES = ("lo", "docker", "veth", "br-", "tailscale", "utun")
_EXCLUDED_EXACT = frozenset({"lo0"})


def _is_excluded_interface(name: str) -> bool:
    """判定介面是否屬於回環、容器橋接或已排除的 VPN 類型。"""
    lower = name.lower()
    if lower in _EXCLUDED_EXACT:
        return True
    return any(lower.startswith(prefix) for prefix in _EXCLUDED_PREFIXES)


def _get_interface_ipv4(name: str) -> str | None:
    """回傳指定介面第一個 IPv4 位址；沒有 IPv4 時為 None。"""
    addrs = psutil.net_if_addrs().get(name, [])
    for addr in addrs:
        if addr.family.name == "AF_INET":
            return addr.address
    return None


def _select_primary_interface(counters: Mapping[str, Any]) -> str | None:
    """從可用 IPv4 介面選出累計流量最高者。

    Args:
        counters: 介面名稱對應 psutil 計數器，需提供 bytes_recv、bytes_sent。

    Returns:
        排除回環與指定虛擬介面後的主要介面名稱；尚無流量時選第一個
        非回環 IPv4 介面，沒有候選時回傳 None。
    """
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


class NetworkReader:
    """保留前次主要介面計數，並以鎖保護取樣的網路採集器。"""

    def __init__(self) -> None:
        """建立網路計數基準與鎖，不立即選取介面。"""
        self._previous: dict[str, str | int | float] | None = None
        self._lock = threading.Lock()

    def read(self) -> metrics.NetworkInfo:
        """回傳主要介面流量快照，並序列化整個基準比較與更新流程。

        單位為 bytes/s；首次、介面切換或計數器重設時可能沒有速率。
        此來源沿用系統 Unix 時鐘，時間未前進時不計算速率。

        Raises:
            OSError: 作業系統無法提供介面或累計流量資訊。
        """
        with self._lock:
            return self._read()

    def _read(self) -> metrics.NetworkInfo:
        """比較同一介面的前後累計流量；首次取樣、介面切換或計數器重設時不回傳假速率。"""

        counters = psutil.net_io_counters(pernic=True)
        interface = _select_primary_interface(counters)

        download_rate: float | None = None
        upload_rate: float | None = None
        ip_address: str | None = None

        if interface and interface in counters:
            ip_address = _get_interface_ipv4(interface)
            current_recv = counters[interface].bytes_recv
            current_sent = counters[interface].bytes_sent
            now = time.time()

            if (
                self._previous is not None
                and self._previous.get("interface") == interface
            ):
                elapsed = now - float(self._previous["timestamp"])
                if elapsed > 0:
                    download_rate = (
                        current_recv - int(self._previous["bytes_recv"])
                    ) / elapsed
                    upload_rate = (
                        current_sent - int(self._previous["bytes_sent"])
                    ) / elapsed
                    if download_rate < 0:
                        download_rate = None
                    if upload_rate < 0:
                        upload_rate = None

            self._previous = {
                "interface": interface,
                "bytes_recv": current_recv,
                "bytes_sent": current_sent,
                "timestamp": now,
            }

        return metrics.NetworkInfo(
            interface=interface,
            ip_address=ip_address,
            download_rate=download_rate,
            upload_rate=upload_rate,
        )
