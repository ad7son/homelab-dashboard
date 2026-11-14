-- 主機基本資訊只保留目前版本，每次採集器啟動時更新。
CREATE TABLE IF NOT EXISTS host_info (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    updated_at_ms INTEGER NOT NULL,
    cpu_physical_cores INTEGER,
    cpu_logical_cores INTEGER,
    memory_total_bytes INTEGER,
    gpu_name TEXT,
    gpu_device_count INTEGER,
    network_interface TEXT,
    network_ip_address TEXT
);

-- NULL 表示缺值；有效的零使用率或零流量不得轉成 NULL。
CREATE TABLE IF NOT EXISTS host_metrics (
    timestamp_ms INTEGER PRIMARY KEY CHECK (timestamp_ms >= 0),
    cpu_usage_percent REAL,
    cpu_frequency_mhz REAL,
    cpu_temperature_celsius REAL,
    cpu_load_1 REAL,
    cpu_load_5 REAL,
    cpu_load_15 REAL,
    memory_used_bytes INTEGER,
    memory_available_bytes INTEGER,
    memory_usage_percent REAL,
    swap_total_bytes INTEGER,
    swap_used_bytes INTEGER,
    swap_usage_percent REAL,
    network_download_bytes_per_second REAL,
    network_upload_bytes_per_second REAL,
    gpu_status TEXT NOT NULL CHECK (
        gpu_status IN ('available', 'unavailable', 'unsupported')
    ),
    gpu_usage_percent REAL,
    disk_io_status TEXT NOT NULL CHECK (
        disk_io_status IN ('available', 'warming_up', 'unavailable')
    ),
    disk_read_bytes_per_second REAL,
    disk_write_bytes_per_second REAL
);
