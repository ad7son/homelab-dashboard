"""API 可以替換應用服務，不需要替換硬體模組或破壞公開回應格式。"""
from fastapi.testclient import TestClient
from app.main import app
from monitor_backend import module


def test_both_prefixes_use_overridden_service_and_preserve_schema():
    dependency = module('api.dependencies').get_overview_service
    models = module('domain.metrics')
    class Service:
        def get_overview(self):
            return models.Overview(
                models.CpuInfo(0, 4, 8, None, None, None),
                models.MemoryInfo(100, 50, 50, 50, models.SwapInfo(0, 0, 0)),
                models.NetworkInfo('test0', None, 0, 0),
                models.GpuInfo(status='unsupported'), models.DiskIoInfo(status='warming_up'),
            )
    app.dependency_overrides[dependency] = Service
    try:
        client = TestClient(app)
        for prefix in ('/api', '/api/system-monitor'):
            response = client.get(prefix + '/overview')
            assert response.status_code == 200
            data = response.json()
            assert set(data) == {'cpu', 'memory', 'network', 'gpu', 'disk_io'}
            assert data['cpu']['usage_percent'] == 0
            assert data['network']['interface'] == 'test0'
            assert data['disk_io']['read_bytes_per_second'] is None
    finally:
        app.dependency_overrides.pop(dependency, None)
