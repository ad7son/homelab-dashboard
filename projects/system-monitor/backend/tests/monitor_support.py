"""既有行為測試的建構工具；透過新服務與 Repository 執行，不保留舊生產模組。"""
from pathlib import Path
from types import SimpleNamespace
from monitor_backend import module


def repository(path=None):
    config = module('core.config')
    return module('infrastructure.repositories.metrics_repository').SQLiteMetricsRepository(config.resolve_metrics_db_path(path))


def get_historical_metrics(history_range, *, db_path=None, now_ms=None, clock_ms=None, read_only=False):
    service = module('services.history').HistoryService(repository(db_path), clock=(lambda: clock_ms() / 1000) if clock_ms else None)
    return service.get_historical_metrics(history_range, now_ms=now_ms, read_only=read_only)


def latest_metric_sample(path=None):
    return repository(path).latest()


def collection_service(path, **options):
    runtime = module('bootstrap').get_runtime(path)
    source = SimpleNamespace(**{
        name: options.get(name + '_reader', getattr(runtime.source, name))
        for name in ['cpu', 'memory', 'network', 'gpu', 'disk_io']
    })
    return module('services.collection').CollectionService(source, runtime.repository, runtime.status,
        retention_ms=options.get('retention_ms', runtime.settings.retention_ms), clock=options.get('clock'))


def collect_once(connection, **options):
    path = connection.execute('PRAGMA database_list').fetchone()[2]
    return collection_service(path, **options).collect_once()


def run_collect_iteration(path, **options):
    return collection_service(path, **options).collect_once()


def run_retention_cleanup(path, **options):
    return collection_service(path, **options).cleanup()


def run_collector_loop(stop_event, *, db_path=None, retention_cleanup=None, **options):
    service = collection_service(db_path, **options)
    scheduling = {key: options[key] for key in ['interval_seconds', 'maintenance_interval_seconds', 'monotonic_clock'] if key in options}
    cleanup = (lambda: retention_cleanup(Path(db_path))) if retention_cleanup else None
    return module('collector.runner').run_collector_loop(stop_event, service, retention_cleanup=cleanup, **scheduling)
