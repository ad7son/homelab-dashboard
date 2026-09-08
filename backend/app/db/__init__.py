"""Historical metrics database package."""

from app.db.metrics_database import (
    CURRENT_SCHEMA_VERSION,
    ENV_METRICS_DB_PATH,
    DuplicateMetricSampleError,
    MetricSampleRecord,
    UnsupportedSchemaVersionError,
    connect_metrics_database,
    count_metric_samples,
    default_metrics_db_path,
    delete_metric_samples_before,
    fetch_metric_sample,
    get_journal_mode,
    get_schema_version,
    initialize_metrics_database,
    insert_metric_sample,
    read_metric_samples,
    resolve_metrics_db_path,
)

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "ENV_METRICS_DB_PATH",
    "DuplicateMetricSampleError",
    "MetricSampleRecord",
    "UnsupportedSchemaVersionError",
    "connect_metrics_database",
    "count_metric_samples",
    "default_metrics_db_path",
    "delete_metric_samples_before",
    "fetch_metric_sample",
    "get_journal_mode",
    "get_schema_version",
    "initialize_metrics_database",
    "insert_metric_sample",
    "read_metric_samples",
    "resolve_metrics_db_path",
]
