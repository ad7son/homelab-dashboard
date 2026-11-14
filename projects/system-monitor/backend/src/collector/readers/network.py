"""啟動時選定 IPv4 介面，之後只讀該介面的流量計數。"""

from __future__ import annotations

import socket
import time

import psutil

_EXCLUDED_PREFIXES = ("lo", "docker", "veth", "br-", "tailscale", "utun")


class NetworkReader:
    """固定介面及單調時間的網路速率讀取器。

    執行期間不重新選介面；介面消失時回報缺值，需重啟才能重新選取。
    """

    def __init__(self) -> None:
        """建立空介面與空計數基準。"""
        self._interface: str | None = None
        self._previous: tuple[float, int, int] | None = None

    def read_info(self) -> dict[str, str | None]:
        """選擇啟用且有 IPv4 的實體候選介面，優先累計流量最高者。"""
        addresses = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        counters = psutil.net_io_counters(pernic=True)
        candidates = []
        for name, entries in addresses.items():
            if name.lower().startswith(_EXCLUDED_PREFIXES):
                continue
            if name not in stats or not stats[name].isup:
                continue
            for entry in entries:
                if (
                    entry.family == socket.AF_INET
                    and not entry.address.startswith("127.")
                ):
                    counter = counters.get(name)
                    traffic = (
                        counter.bytes_recv + counter.bytes_sent
                        if counter
                        else 0
                    )
                    candidates.append((traffic, name, entry.address))
                    break
        self._previous = None
        if not candidates:
            self._interface = None
            return {"network_interface": None, "network_ip_address": None}
        _, self._interface, address = max(candidates)
        return {
            "network_interface": self._interface,
            "network_ip_address": address,
        }

    def read(self) -> dict[str, float | None]:
        """計算 bytes/s；首次、失敗恢復、計數重設時保留缺值。"""
        try:
            counter = psutil.net_io_counters(pernic=True).get(self._interface)
        except (OSError, RuntimeError):
            self._previous = None
            raise
        if counter is None:
            self._previous = None
            return {}
        current = (time.monotonic(), counter.bytes_recv, counter.bytes_sent)
        previous, self._previous = self._previous, current
        if previous is None:
            return {}
        elapsed = current[0] - previous[0]
        if elapsed <= 0:
            return {}
        download = current[1] - previous[1]
        upload = current[2] - previous[2]
        return {
            "network_download_bytes_per_second": (
                download / elapsed if download >= 0 else None
            ),
            "network_upload_bytes_per_second": (
                upload / elapsed if upload >= 0 else None
            ),
        }
