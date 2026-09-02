from typing import Dict, List, Optional

import psutil

from app.schemas.disk import DiskInfo

_SKIP_FSTYPES = frozenset(
    {
        "devfs",
        "autofs",
        "proc",
        "sysfs",
        "tmpfs",
        "devtmpfs",
        "squashfs",
        "overlay",
        "fusectl",
        "cgroup",
        "cgroup2",
        "mqueue",
        "debugfs",
        "tracefs",
        "securityfs",
        "pstore",
        "bpf",
        "hugetlbfs",
    }
)


def _should_skip_partition(fstype: str, mountpoint: str) -> bool:
    if fstype in _SKIP_FSTYPES:
        return True
    if mountpoint.startswith("/dev") or mountpoint.startswith("/proc"):
        return True
    if mountpoint.startswith("/sys"):
        return True
    return False


def get_disk_info() -> List[DiskInfo]:
    disks: List[DiskInfo] = []

    for partition in psutil.disk_partitions(all=False):
        if _should_skip_partition(partition.fstype, partition.mountpoint):
            continue
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except (PermissionError, OSError):
            continue

        disks.append(
            DiskInfo(
                device=partition.device or None,
                mount_point=partition.mountpoint,
                filesystem_type=partition.fstype,
                total_bytes=usage.total,
                used_bytes=usage.used,
                free_bytes=usage.free,
                usage_percent=usage.percent,
            )
        )

    return disks
