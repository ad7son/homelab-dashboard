"""SQLite persistence for A7LAS historical metric samples."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

CURRENT_SCHEMA_VERSION = 1
ENV_METRICS_DB_PATH = "A7LAS_METRICS_DB_PATH"
BUSY_TIMEOUT_MS = 5000

_CREATE_METRIC_SAMPLES_SQL = """
CREATE TABLE IF NOT EXISTS metric_samples (
    timestamp_ms INTEGER PRIMARY KEY,
    cpu_usage_percent REAL NOT NULL,
    cpu_temperature_celsius REAL,
    memory_usage_percent REAL NOT NULL,
    network_download_bytes_per_second REAL,
    network_upload_bytes_per_second REAL
)
"""

_INSERT_METRIC_SAMPLE_SQL = """
INSERT INTO metric_samples (
    timestamp_ms,
    cpu_usage_percent,
    cpu_temperature_celsius,
    memory_usage_percent,
    network_download_bytes_per_second,
    network_upload_bytes_per_second
) VALUES (?, ?, ?, ?, ?, ?)
"""


class UnsupportedSchemaVersionError(RuntimeError):
    """Raised when the metrics DB has an unsupported schema version."""


class DuplicateMetricSampleError(RuntimeError):
    """Raised when inserting a sample with an existing timestamp_ms."""


@dataclass(frozen=True)
class MetricSampleRecord:
    timestamp_ms: int
    cpu_usage_percent: float
    cpu_temperature_celsius: Optional[float]
    memory_usage_percent: float
    network_download_bytes_per_second: Optional[float]
    network_upload_bytes_per_second: Optional[float]


def default_metrics_db_path() -> Path:
    """Local development default: backend/data/metrics.db."""
    backend_root = Path(__file__).resolve().parents[2]
    return backend_root / "data" / "metrics.db"


def resolve_metrics_db_path(
    override: Optional[str | Path] = None,
) -> Path:
    """
    Resolve the metrics database path.

    Priority:
    1. explicit override argument
    2. A7LAS_METRICS_DB_PATH environment variable
    3. local development default under backend/data
    """
    if override is not None:
        return Path(override).expanduser().resolve()

    env_path = os.environ.get(ENV_METRICS_DB_PATH)
    if env_path:
        return Path(env_path).expanduser().resolve()

    return default_metrics_db_path().resolve()


def _get_user_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row is not None else 0


def _set_user_version(connection: sqlite3.Connection, version: int) -> None:
    # PRAGMA user_version cannot be parameterized.
    connection.execute(f"PRAGMA user_version = {int(version)}")


def _configure_connection(connection: sqlite3.Connection) -> None:
    connection.row_factory = sqlite3.Row
    connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    connection.execute("PRAGMA journal_mode = WAL")


def initialize_metrics_database(connection: sqlite3.Connection) -> None:
    """Create schema when needed. Idempotent for schema version 1."""
    version = _get_user_version(connection)

    if version == 0:
        connection.execute(_CREATE_METRIC_SAMPLES_SQL)
        _set_user_version(connection, CURRENT_SCHEMA_VERSION)
        connection.commit()
        return

    if version == CURRENT_SCHEMA_VERSION:
        # Existing v1 DB: leave schema and data intact.
        return

    raise UnsupportedSchemaVersionError(
        f"Unsupported metrics database schema version {version}; "
        f"expected {CURRENT_SCHEMA_VERSION} or uninitialized (0)."
    )


def connect_metrics_database(
    path: Optional[str | Path] = None,
) -> sqlite3.Connection:
    """Open a short-lived connection, configure SQLite, and initialize schema."""
    db_path = resolve_metrics_db_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path), timeout=BUSY_TIMEOUT_MS / 1000.0)
    try:
        _configure_connection(connection)
        initialize_metrics_database(connection)
    except Exception:
        connection.close()
        raise

    return connection


def insert_metric_sample(
    connection: sqlite3.Connection,
    sample: MetricSampleRecord,
) -> None:
    """Insert one metric sample. Duplicate timestamps are rejected."""
    try:
        with connection:
            connection.execute(
                _INSERT_METRIC_SAMPLE_SQL,
                (
                    sample.timestamp_ms,
                    sample.cpu_usage_percent,
                    sample.cpu_temperature_celsius,
                    sample.memory_usage_percent,
                    sample.network_download_bytes_per_second,
                    sample.network_upload_bytes_per_second,
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise DuplicateMetricSampleError(
            f"metric sample already exists for timestamp_ms={sample.timestamp_ms}"
        ) from exc


def get_schema_version(connection: sqlite3.Connection) -> int:
    """Return PRAGMA user_version."""
    return _get_user_version(connection)


def get_journal_mode(connection: sqlite3.Connection) -> str:
    """Return current journal mode (expected: wal)."""
    row = connection.execute("PRAGMA journal_mode").fetchone()
    return str(row[0]).lower()


def count_metric_samples(connection: sqlite3.Connection) -> int:
    """Minimal internal helper for tests."""
    row = connection.execute("SELECT COUNT(*) AS n FROM metric_samples").fetchone()
    return int(row["n"] if isinstance(row, sqlite3.Row) else row[0])


def fetch_metric_sample(
    connection: sqlite3.Connection,
    timestamp_ms: int,
) -> Optional[MetricSampleRecord]:
    """Minimal internal read helper for tests."""
    row = connection.execute(
        """
        SELECT
            timestamp_ms,
            cpu_usage_percent,
            cpu_temperature_celsius,
            memory_usage_percent,
            network_download_bytes_per_second,
            network_upload_bytes_per_second
        FROM metric_samples
        WHERE timestamp_ms = ?
        """,
        (timestamp_ms,),
    ).fetchone()

    if row is None:
        return None

    return _row_to_metric_sample(row)


def read_metric_samples(
    connection: sqlite3.Connection,
    start_timestamp_ms: int,
    end_timestamp_ms: int,
) -> list[MetricSampleRecord]:
    """
    Read samples in an inclusive timestamp window, ordered ascending.

    Range semantics (15m/1h/...) belong in the service layer, not here.
    """
    rows = connection.execute(
        """
        SELECT
            timestamp_ms,
            cpu_usage_percent,
            cpu_temperature_celsius,
            memory_usage_percent,
            network_download_bytes_per_second,
            network_upload_bytes_per_second
        FROM metric_samples
        WHERE timestamp_ms >= ?
          AND timestamp_ms <= ?
        ORDER BY timestamp_ms ASC
        """,
        (start_timestamp_ms, end_timestamp_ms),
    ).fetchall()

    return [_row_to_metric_sample(row) for row in rows]


def delete_metric_samples_before(
    connection: sqlite3.Connection,
    cutoff_timestamp_ms: int,
) -> int:
    """
    Delete samples strictly older than cutoff_timestamp_ms.

    Retention duration belongs in the caller; this layer only applies the cutoff.
    Rows at exactly the cutoff remain. Returns the number of deleted rows.
    """
    with connection:
        cursor = connection.execute(
            "DELETE FROM metric_samples WHERE timestamp_ms < ?",
            (int(cutoff_timestamp_ms),),
        )
    return int(cursor.rowcount)


def _row_to_metric_sample(row: sqlite3.Row) -> MetricSampleRecord:
    return MetricSampleRecord(
        timestamp_ms=int(row["timestamp_ms"]),
        cpu_usage_percent=float(row["cpu_usage_percent"]),
        cpu_temperature_celsius=(
            None
            if row["cpu_temperature_celsius"] is None
            else float(row["cpu_temperature_celsius"])
        ),
        memory_usage_percent=float(row["memory_usage_percent"]),
        network_download_bytes_per_second=(
            None
            if row["network_download_bytes_per_second"] is None
            else float(row["network_download_bytes_per_second"])
        ),
        network_upload_bytes_per_second=(
            None
            if row["network_upload_bytes_per_second"] is None
            else float(row["network_upload_bytes_per_second"])
        ),
    )
