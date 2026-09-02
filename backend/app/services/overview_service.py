from app.schemas.overview import Overview
from app.services import cpu_service, disk_service, memory_service, network_service, system_service


def get_overview() -> Overview:
    return Overview(
        system=system_service.get_system_info(),
        cpu=cpu_service.get_cpu_info(),
        memory=memory_service.get_memory_info(),
        disks=disk_service.get_disk_info(),
        network=network_service.get_network_info(),
    )
