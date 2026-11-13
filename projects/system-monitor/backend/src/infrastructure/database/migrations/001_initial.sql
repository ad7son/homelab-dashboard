-- v1 原始指標；v2 指標由下一份遷移新增，舊樣本維持 NULL。
CREATE TABLE IF NOT EXISTS metric_samples (
    timestamp_ms INTEGER PRIMARY KEY,
    cpu_usage_percent REAL NOT NULL,
    cpu_temperature_celsius REAL,
    memory_usage_percent REAL NOT NULL,
    network_download_bytes_per_second REAL,
    network_upload_bytes_per_second REAL
);
