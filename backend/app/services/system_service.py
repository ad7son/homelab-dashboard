from typing import Dict, Optional

import platform
import socket
import time

import psutil

from app.schemas.system import SystemInfo

_static_cache: Optional[Dict[str, Optional[str]]] = None


def _get_static_info() -> Dict[str, Optional[str]]:
    global _static_cache
    if _static_cache is None:
        uname = platform.uname()
        _static_cache = {
            "hostname": socket.gethostname(),
            "operating_system": uname.system,
            "os_version": uname.release or None,
            "kernel": uname.version,
            "architecture": uname.machine,
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
