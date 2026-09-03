from typing import Dict, Optional

import os
import platform
import socket
import time

import psutil

from app.schemas.system import SystemInfo

_static_cache: Optional[Dict[str, Optional[str]]] = None

_OS_RELEASE_PATH = "/etc/os-release"


def _parse_os_release(path: str) -> Dict[str, str]:
    """Parse a subset of /etc/os-release into a dict."""
    result: Dict[str, str] = {}
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                # Strip optional quotes
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                result[key] = value
    except (OSError, IOError):
        pass
    return result


def _get_static_info() -> Dict[str, Optional[str]]:
    global _static_cache
    if _static_cache is None:
        hostname = socket.gethostname()
        architecture = platform.machine()
        kernel = platform.release()

        # Default fallback (works on macOS and any system without /etc/os-release)
        operating_system: Optional[str] = platform.system()
        os_version: Optional[str] = None

        # When /etc/os-release exists, use its NAME and VERSION fields
        if os.path.isfile(_OS_RELEASE_PATH):
            osr = _parse_os_release(_OS_RELEASE_PATH)
            if "NAME" in osr:
                operating_system = osr["NAME"]
            os_version = osr.get("VERSION") or None

        _static_cache = {
            "hostname": hostname,
            "operating_system": operating_system,
            "os_version": os_version,
            "kernel": kernel,
            "architecture": architecture,
        }
    return _static_cache


def get_system_info() -> SystemInfo:
    static = _get_static_info()
    uptime = time.time() - psutil.boot_time()
    return SystemInfo(
        hostname=static["hostname"],
        operating_system=static["operating_system"],
        os_version=static.get("os_version"),
        kernel=static["kernel"],
        architecture=static["architecture"],
        uptime=uptime,
    )
