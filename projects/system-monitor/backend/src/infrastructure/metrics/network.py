"""主要網路介面與累計流量適配器；同一實例序列化取樣避免互相覆蓋。"""
import threading
import time
from typing import Optional
import psutil
from ...domain.metrics import NetworkInfo

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

class NetworkReader:
    def __init__(self):
        self._previous = None
        self._lock = threading.Lock()

    def read(self):
        with self._lock:
            return self._read()

    def _read(self) -> NetworkInfo:
        """比較同一介面的前後累計流量；首次取樣、介面切換或計數器重設時不回傳假速率。"""

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

            if self._previous is not None and self._previous.get("interface") == interface:
                elapsed = now - float(self._previous["timestamp"])
                if elapsed > 0:
                    download_rate = (current_recv - int(self._previous["bytes_recv"])) / elapsed
                    upload_rate = (current_sent - int(self._previous["bytes_sent"])) / elapsed
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

        return NetworkInfo(
            interface=interface,
            ip_address=ip_address,
            download_rate=download_rate,
            upload_rate=upload_rate,
        )
