"""API 可以替換應用服務，不需要替換硬體模組或破壞公開回應格式。"""

from fastapi import testclient

from app import main
import monitor_backend


def test_both_prefixes_use_overridden_service_and_preserve_schema():
    dependency = monitor_backend.module("api.dependencies").get_overview_service
    models = monitor_backend.module("domain.metrics")

    class Service:
        """回傳固定快照的服務替身，供驗證兩個前綴共用依賴覆寫。"""

        def get_overview(self):
            """回傳有效零值與選用缺值並存的快照。"""
            return models.Overview(
                models.CpuInfo(0, 4, 8, None, None, None),
                models.MemoryInfo(100, 50, 50, 50, models.SwapInfo(0, 0, 0)),
                models.NetworkInfo("test0", None, 0, 0),
                models.GpuInfo(status="unsupported"),
                models.DiskIoInfo(status="warming_up"),
            )

    main.app.dependency_overrides[dependency] = Service
    try:
        client = testclient.TestClient(main.app)
        for prefix in ("/api", "/api/system-monitor"):
            response = client.get(prefix + "/overview")
            assert response.status_code == 200
            data = response.json()
            assert set(data) == {"cpu", "memory", "network", "gpu", "disk_io"}
            assert data["cpu"]["usage_percent"] == 0
            assert data["network"]["interface"] == "test0"
            assert data["disk_io"]["read_bytes_per_second"] is None
    finally:
        main.app.dependency_overrides.pop(dependency, None)
