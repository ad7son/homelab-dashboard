-- nullable 欄位保留升級前的缺值，不能以 0 補舊資料。
ALTER TABLE metric_samples ADD COLUMN gpu_usage_percent REAL;
ALTER TABLE metric_samples ADD COLUMN disk_read_bytes_per_second REAL;
ALTER TABLE metric_samples ADD COLUMN disk_write_bytes_per_second REAL;
