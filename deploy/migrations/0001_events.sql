-- 0001_events.sql — 网页原始作答事件（不含任何身份信息）
--
-- 设计口径（docs/REVISION_CONTRACT.md 第 10 节）：
--   网页只产生「原始作答事件」，判分/掌握/FSRS 一律在本地权威侧完成。
--   这里保存的是服务端重判后的客观题结果（regraded_correct），
--   开放题为 NULL（必须由本地 grade-open 判定），永远不以客户端 correct 为准。
--
-- 幂等：UNIQUE(session, qid) + INSERT OR IGNORE，重复提交同一题不产生新行。
--
-- 应用方式：
--   npx wrangler d1 execute nihongo80 --remote --file=./migrations/0001_events.sql
--   （本地开发：去掉 --remote）

CREATE TABLE IF NOT EXISTS events (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  client_ts         TEXT,             -- 客户端提交时间（ISO 8601，原样保留）
  server_ts         TEXT NOT NULL,    -- Worker 收到请求的时间（UTC ISO 8601）
  day               INTEGER NOT NULL, -- 1..150
  session           TEXT NOT NULL,    -- 形如 session-YYYYMMDD-NNN
  qid               TEXT NOT NULL,
  answer            TEXT,             -- 原始作答文本（不做任何判分前的清洗）
  hinted            INTEGER NOT NULL DEFAULT 0,  -- 0/1，含 revealed_before_submit 的逻辑或
  revealed          INTEGER NOT NULL DEFAULT 0,  -- 0/1，提交前是否已看答案
  seconds           INTEGER,          -- 该题耗时；未知为 NULL
  capability        TEXT,             -- 来自 answer-key.json（可空）
  regraded_correct  INTEGER,          -- 1/0；开放题或无法重判时为 NULL
  payload_hash      TEXT,             -- 事件规范化 JSON 的 SHA-256（完整性/去重辅助）
  UNIQUE(session, qid)
);

-- 按天聚合（cloud_sync 拉取后按 day/session 聚合）
CREATE INDEX IF NOT EXISTS idx_events_day ON events(day);

-- 增量拉取游标（GET /api/events?since=<id>）
CREATE INDEX IF NOT EXISTS idx_events_id ON events(id);
