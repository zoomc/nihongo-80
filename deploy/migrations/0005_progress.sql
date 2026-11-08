-- 0005_progress.sql — 当天学习完成快照（学习者自报，非掌握权威）
--
-- 语义：网页「完成」按钮 POST /api/progress 写入的**自报快照**，供任意 agent
--   通过 GET /api/progress + skill 快速生成复习建议。它不是掌握判定依据：
--   权威完成/FSRS 仍只由本机 SQLite（python3 scripts/nh80.py finish-day）负责。
--   questions[].correct / accuracy 由客户端自算，服务端不重判、不采信，
--   整体以 self_reported=1 标注（见列与 payload）。
--
-- 幂等与有界：
--   day 为主键，POST 用 INSERT ... ON CONFLICT(day) DO UPDATE 覆盖；
--   同一天无论写多少次只保留一行，全表最多 150 行，永不追加历史。
--   所有语句带 IF NOT EXISTS，重复执行（两库各一次、或之后 migrations apply）安全。
--
-- 应用方式（两库分别、各跑一次；本文件只含幂等 DDL，可单独 d1 execute）：
--   npx wrangler d1 execute nihongo80 --remote --file=./migrations/0005_progress.sql
--   npx wrangler d1 execute nihongo80-preview --remote --env preview --file=./migrations/0005_progress.sql
--
-- 列设计：payload 存规范化后的完整 JSON（白名单字段，省去几十个列），
--   另把 day / accuracy / server_ts 提列便于按天与按时间查询。
--   注意：0002/0004 含无 IF NOT EXISTS 的 ALTER TABLE，切勿用本命令重放它们；
--   本文件不含任何 ALTER，单独执行不会触碰既有 events / study_sessions 等表。

CREATE TABLE IF NOT EXISTS study_progress (
  day            INTEGER PRIMARY KEY CHECK(day BETWEEN 1 AND 150),  -- 幂等覆盖键；1..150
  server_ts      TEXT NOT NULL,        -- Worker 收到请求时刻（UTC ISO 8601），权威时间戳
  completed_at   TEXT,                 -- 客户端点「完成」时刻（ISO 8601，截断 40 字符）
  payload        TEXT NOT NULL,        -- 规范化完整 JSON：v/day/范围/questions/accuracy/自评/错题/复习集/备注 + self_reported
  accuracy       REAL,                 -- 0..1 客户端自算，仅展示；非权威
  self_reported  INTEGER NOT NULL DEFAULT 1  -- 恒为 1：明确标注「自报快照，非掌握权威」
);

-- ?latest=1&limit=N 按 server_ts 倒序取最近完成；?day=N 直接走主键。
CREATE INDEX IF NOT EXISTS idx_progress_server_ts ON study_progress(server_ts DESC);
