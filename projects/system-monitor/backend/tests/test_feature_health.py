"""以受控來源驗證健康判定，不依賴測試主機是否具備特定硬體。"""

from monitor_backend import module as monitor_module
import json
import time

import pytest
from fastapi.testclient import TestClient
from app.main import app
connect_metrics_database = monitor_module('history.database').connect_metrics_database
insert_metric_sample = monitor_module('history.database').insert_metric_sample
MetricSampleRecord = monitor_module('history.models').MetricSampleRecord
health = monitor_module('health.checks')
record_collector_result = monitor_module('collector.status').record_collector_result
status_path = monitor_module('collector.status').status_path


@pytest.fixture
def sources(monkeypatch, tmp_path):
    path = tmp_path / 'metrics.db'
    monkeypatch.setenv('A7LAS_METRICS_DB_PATH', str(path))
    health._cached = None
    health._last_success.clear()
    values = {
        'cpu': {'usage_percent': 0, 'physical_cores': 4, 'logical_cores': 8, 'temperature': None},
        'memory': {'total': 100, 'used': 50, 'available': 50, 'usage_percent': 50},
        'gpu': {'status': 'unsupported', 'device_count': 0},
        'disk-io': {'status': 'available', 'read_bytes_per_second': 0, 'write_bytes_per_second': 0},
        'network': {'interface': 'eth0', 'download_rate': 0, 'upload_rate': 0},
    }
    for module, method, key in [
        (health.readers, 'get_cpu_info', 'cpu'),
        (health.readers, 'get_memory_info', 'memory'),
        (health.gpu, 'get_gpu_info', 'gpu'),
        (health.readers, 'get_disk_io_info', 'disk-io'),
        (health.readers, 'get_network_info', 'network'),
    ]:
        monkeypatch.setattr(module, method, lambda key=key: values[key])
    connection = connect_metrics_database(path)
    sample = MetricSampleRecord(int(time.time() * 1000), 0, None, 50, 0, 0)
    insert_metric_sample(connection, sample)
    connection.close()
    record_collector_result(path, sample=sample)
    yield values, path, sample
    health._cached = None
    health._last_success.clear()


def report():
    return {feature.id: feature for feature in health.get_feature_health(force=True).features}


def test_idle_values_and_missing_gpu_are_not_failures(sources):
    result = report()
    assert len(result) == 7
    assert result['cpu'].status == result['disk-io'].status == result['network'].status == 'healthy'
    assert result['gpu'].status == 'unavailable'
    assert result['history-write'].status == result['history-query'].status == 'healthy'
    assert result['cpu'].raw_data['usage_percent'] == 0


def test_first_sample_is_unknown(sources):
    values, _, _ = sources
    values['disk-io'] = {'status': 'warming_up'}
    values['network'].update(download_rate=None, upload_rate=None)
    result = report()
    assert result['disk-io'].status == result['network'].status == 'unknown'


def test_reader_failure_is_isolated_and_preserves_traceback(sources, monkeypatch):
    def fail():
        raise PermissionError('CPU permission denied')
    monkeypatch.setattr(health.readers, 'get_cpu_info', fail)
    result = report()
    assert result['cpu'].status == 'issues'
    assert result['memory'].status == 'healthy'
    assert result['cpu'].error.message == 'CPU permission denied'
    assert 'PermissionError' in result['cpu'].error.traceback


def test_invalid_values_remain_visible_and_json_safe(sources):
    values, _, _ = sources
    values['cpu']['usage_percent'] = float('nan')
    result = report()
    assert result['cpu'].status == 'issues'
    assert result['cpu'].raw_data['usage_percent'] == 'nan'
    json.dumps(health.get_feature_health().model_dump(), allow_nan=False)


def test_last_success_survives_later_failure(sources):
    first = report()['cpu']
    sources[0]['cpu']['usage_percent'] = -1
    second = report()['cpu']
    assert second.status == 'issues'
    assert second.last_success_at_ms == first.checked_at_ms


def test_stopped_writer_does_not_break_query(sources, monkeypatch):
    _, _, sample = sources
    monkeypatch.setattr(health.time, 'time', lambda: (sample.timestamp_ms + 90_001) / 1000)
    result = report()
    assert result['history-write'].status == 'issues'
    assert result['history-query'].status == 'healthy'


def test_failed_write_preserves_actual_error_even_with_fresh_sample(sources):
    _, path, sample = sources
    record_collector_result(path, error=OSError('disk full'))
    result = report()['history-write']
    assert result.status == 'issues'
    assert result.last_success_at_ms == sample.timestamp_ms
    assert result.error.message == 'disk full'
    assert result.raw_data['collector']['error']['type'] == 'OSError'


def test_missing_database_not_created_by_health_probe(sources):
    _, path, _ = sources
    path.unlink()
    result = report()
    assert result['history-write'].status == result['history-query'].status == 'issues'
    assert not path.exists()


def test_empty_database_query_works_but_writer_is_unhealthy(sources):
    _, path, _ = sources
    connection = connect_metrics_database(path)
    connection.execute('DELETE FROM metric_samples')
    connection.commit()
    connection.close()
    result = report()
    assert result['history-write'].status == 'issues'
    assert result['history-query'].status == 'healthy'
    assert result['history-query'].raw_data['samples'] == []


def test_cache_and_forced_refresh(sources):
    first = health.get_feature_health(force=True)
    sources[0]['cpu']['usage_percent'] = -1
    assert health.get_feature_health() is first
    assert report()['cpu'].status == 'issues'


@pytest.mark.parametrize('prefix', ['/api/system-monitor', '/api'])
def test_endpoint_returns_actual_snapshot(sources, prefix):
    response = TestClient(app).get(prefix + '/feature-health?force=true')
    assert response.status_code == 200
    data = response.json()
    assert data['project_id'] == 'system-monitor'
    assert len(data['features']) == 7
    assert data['features'][0]['raw_data']['usage_percent'] == 0
    assert data['features'][0]['checked_at_ms'] == data['checked_at_ms']


def test_bad_schema_is_reported_without_migration(sources):
    _, path, _ = sources
    connection = connect_metrics_database(path)
    connection.execute('PRAGMA user_version=1')
    connection.close()
    result = report()
    assert result['history-write'].status == result['history-query'].status == 'issues'
    import sqlite3
    with sqlite3.connect(path) as connection:
        assert connection.execute('PRAGMA user_version').fetchone()[0] == 1


def test_collector_records_failures_and_recovers(sources, monkeypatch):
    metrics_collector = monitor_module('collector.metrics_collector')
    _, path, sample = sources
    def fail(*args, **kwargs):
        raise OSError('read failed')
    monkeypatch.setattr(metrics_collector, 'collect_once', fail)
    with pytest.raises(OSError, match='read failed'):
        metrics_collector.run_collect_iteration(path)
    saved = json.loads(status_path(path).read_text())
    assert saved['last_success_at_ms'] == sample.timestamp_ms
    assert 'read failed' in saved['error']['traceback']
    monkeypatch.setattr(metrics_collector, 'collect_once', lambda *args, **kwargs: sample)
    metrics_collector.run_collect_iteration(path)
    assert json.loads(status_path(path).read_text())['error'] is None


@pytest.mark.parametrize('content', ['not json', '[]'])
def test_broken_collector_status_keeps_database_evidence(sources, content):
    """旁檔損壞時保留讀取原因，最新成功樣本仍取自真實資料庫。"""
    _, path, sample = sources
    status_path(path).write_text(content)
    result = report()['history-write']
    assert result.raw_data['collector'] is None
    assert result.raw_data['collector_status_error'] is not None
    assert result.raw_data['latest_sample_at_ms'] == sample.timestamp_ms
    assert result.status == 'healthy'
