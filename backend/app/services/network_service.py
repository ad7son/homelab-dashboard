from typing import Dict, Optional, Union

import time

import psutil

from app.schemas.network import NetworkInfo

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
