CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_ms INTEGER NOT NULL,
    project_id TEXT NOT NULL,
    feature_id TEXT,
    level TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_feature_id
    ON events (project_id, feature_id, id DESC);
CREATE INDEX IF NOT EXISTS events_timestamp ON events (timestamp_ms);

-- 最新狀態獨立保存，刪除過期事件不會遺失最近成功時間與最新執行結果。
CREATE TABLE IF NOT EXISTS feature_state (
    project_id TEXT NOT NULL,
    feature_id TEXT NOT NULL,
    first_seen_at_ms INTEGER NOT NULL,
    last_event_at_ms INTEGER,
    last_event_id INTEGER,
    last_success_at_ms INTEGER,
    payload_json TEXT,
    PRIMARY KEY (project_id, feature_id)
);
