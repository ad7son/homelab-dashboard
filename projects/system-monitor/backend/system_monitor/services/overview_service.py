from system_monitor.schemas.overview import Overview
from system_monitor.services import cpu_service, disk_service, memory_service, network_service, system_service
from system_monitor.services.gpu_service import get_gpu_info
from system_monitor.services.disk_io_service import get_disk_io_info


def get_overview() -> Overview:
    return Overview(
        system=system_service.get_system_info(),
        cpu=cpu_service.get_cpu_info(),
        memory=memory_service.get_memory_info(),
        disks=disk_service.get_disk_info(),
        network=network_service.get_network_info(),
        gpu=get_gpu_info(),
        disk_io=get_disk_io_info(),
    )
