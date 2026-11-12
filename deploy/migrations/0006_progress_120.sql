-- Course editions assign different content to the same day number.
CREATE TABLE IF NOT EXISTS study_progress_120 (
  day INTEGER PRIMARY KEY CHECK(day BETWEEN 1 AND 120),
  server_ts TEXT NOT NULL,
  completed_at TEXT,
  payload TEXT NOT NULL,
  accuracy REAL,
  self_reported INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_progress_120_server_ts ON study_progress_120(server_ts DESC);
