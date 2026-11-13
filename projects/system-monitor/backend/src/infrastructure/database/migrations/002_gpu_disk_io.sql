-- nullable 欄位保留升級前的缺值，不能以 0 補舊資料。
-- GPU 單位為百分比，磁碟讀寫單位為 bytes/s；零值與 NULL 意義不同。
-- 每條 ALTER 由 migration_runner 檢查欄位是否存在，整組失敗時回滾。
ALTER TABLE metric_samples ADD COLUMN gpu_usage_percent REAL;
ALTER TABLE metric_samples ADD COLUMN disk_read_bytes_per_second REAL;
ALTER TABLE metric_samples ADD COLUMN disk_write_bytes_per_second REAL;
