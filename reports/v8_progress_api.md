# v8 进度 API 交付报告（`/api/progress`）

> 日期：2026-11-09
> 范围：**服务端**（Cloudflare Worker 新路由 + D1 迁移）+ **agent 侧**（CLI + skill + `AGENTS.md`）。
> **不含前端**：`web/`、`build_v5_site.py`、`study_ui.py`、`practice_v9.py`、`quiz_v5.py`、`nh80.py`、`release_guard.py`、`tests/test_v5.py`、`tests/test_v7.py`、`README.md`、`HANDOFF.md`、`CONTRACTS.md`、`tests/test_worker_access.mjs` 一律未改（主控并行重构前端）。
> 链路：页面「完成」按钮 → `POST /api/progress` 云端自报快照 → 任何 agent 用 `X-NH80-Key` 经 skill/CLI 读取 → 生成当天家教会话的复习重点。

---

## 0. 诚实边界（先读，别跳）

- **云端进度是学习者自报的当天快照，不是掌握判定的权威。** `questions[].correct` 与 `accuracy` 由客户端自算，服务端**不重判、不采信**，整份数据以 `self_reported=1` 标注（列 + payload + GET item 三处一致）。
- **唯一权威是本机 `data/state.db`**，只经 `python3 scripts/nh80.py finish-day` 写入（事务 + `audit_log`）。agent 只读云端，**永不回写** `sessions` / `fsrs_cards` / `passed`，不调用 `finish-day` 去「确认」云端结果，不据 `accuracy` 说「已达标 / 已掌握」。
- 自评只排复习优先级，不是客观能力测试。
- 全程**不打印、不写入密钥**；**不引入任何付费服务**；Workers Free 超额只报错、不自动扣费。

---

## 1. 新增 / 修改文件清单

| 文件 | 动作 | 说明 |
|---|---|---|
| `deploy/migrations/0005_progress.sql` | 新增 | `study_progress` 表 + `idx_progress_server_ts` 索引，全语句 `IF NOT EXISTS` 幂等 |
| `deploy/worker/src/index.ts` | **只新增** | 入口加 `/api/progress` 独立分支；新增 `handleProgress()` / `handleGetProgress()` 及辅助函数。**未改动** `/api/events`、`/api/reviews`、`/api/study`、`/api/study-plan` 的任何一行行为 |
| `scripts/progress_read.py` | 新增 | 纯标准库 CLI（只读） |
| `skills/nh80-progress/SKILL.md` | 新增 | 仓库内真源 |
| `.workbuddy/skills/nh80-progress/SKILL.md` | 新增（拷贝） | 项目级，clone 后可用 |
| `~/.workbuddy/skills/nh80-progress/SKILL.md` | 新增（拷贝） | 用户级，WorkBuddy 本机立即可用 |
| `AGENTS.md` | **只追加**一节 | 「通过 skill 读取学习进度」+ 给 Claude Code / Codex 的一句话提示词；原有内容一字未改 |
| `tests/test_progress_api.mjs` | 新增 | 12 项断言，esbuild 打包真 Worker + `node:sqlite` 内存 D1 |
| `reports/v8_progress_api.md` | 新增 | 本报告 |

三份 `SKILL.md` 经 `md5` 校验完全一致（`b5b73d9b535c5cd4e82d6eba25df5288`）。
未执行 `git commit`；`deploy/node_modules/` 保留未删。

---

## 2. D1 表结构（`deploy/migrations/0005_progress.sql`）

```sql
CREATE TABLE IF NOT EXISTS study_progress (
  day            INTEGER PRIMARY KEY CHECK(day BETWEEN 1 AND 150),
  server_ts      TEXT NOT NULL,        -- Worker 收到时刻（UTC ISO 8601），权威时间戳
  completed_at   TEXT,                 -- 客户端点「完成」时刻，截断 40 字符，仅参考
  payload        TEXT NOT NULL,        -- 规范化完整 JSON（白名单字段，含 self_reported:1）
  accuracy       REAL,                 -- 0..1 客户端自算，仅展示、非权威
  self_reported  INTEGER NOT NULL DEFAULT 1  -- 恒为 1：自报快照标记
);
CREATE INDEX IF NOT EXISTS idx_progress_server_ts ON study_progress(server_ts DESC);
```

设计要点：

- **按 `day` 幂等覆盖**：`INSERT ... ON CONFLICT(day) DO UPDATE SET ...=excluded...`。同一天无论写多少次只保留一行，**全表最多 150 行，永不追加历史**。
- **`payload` 存完整 JSON**：避免几十个列；另把 `day` / `accuracy` / `server_ts` 提列便于按天与按时间查询。`?day=N` 走主键，`?latest=1&limit=N` 走 `server_ts` 索引。
- **不碰既有表**：文件内无任何 `ALTER TABLE`，单独 `d1 execute` 不会重放 0002/0004 的无 `IF NOT EXISTS` 的 `ALTER`。
- **两库各执行一次 `--remote`**（`-y` 是非交互环境跳过 wrangler 确认所必需）：

```sh
cd deploy
npx wrangler d1 execute nihongo80 --remote -y --file=./migrations/0005_progress.sql
npx wrangler d1 execute nihongo80-preview --remote --env preview -y --file=./migrations/0005_progress.sql
```

两库实测输出均为 `Processed 2 queries` / `Executed 2 queries`（production `3 rows read, 3 rows written`，preview 同），`success`。

验证（两库均返回表 + 索引两行，`COUNT(*)=0`）：

```sh
npx wrangler d1 execute nihongo80 --remote --config wrangler.jsonc --json \
  --command="SELECT name,type FROM sqlite_master WHERE name IN ('study_progress','idx_progress_server_ts') ORDER BY name"
# -> [{"name":"idx_progress_server_ts","type":"index"},{"name":"study_progress","type":"table"}]
```

---

## 3. API 契约

### 3.1 `POST /api/progress`（页面「完成」按钮，**无用户口令、不带 `X-NH80-Key`**）

请求（字段名固定，页面照此 POST）：

```json
{
  "v": 1, "day": 47, "completed_at": "2026-11-08T23:50:00+08:00",
  "required_ids": ["V0001"], "extra_ids": ["V0002"], "grammar_ids": ["G0001"],
  "questions": [{"qid":"Q-001-K0-xxx","answer":"ニチ","correct":true,"hinted":false,"revealed":false,"seconds":8}],
  "accuracy": 0.83,
  "self_rating": {"V0001":"good","G0001":"hard"},
  "wrong_summary": [{"qid":"Q-001-K0-xxx","knowledge_ids":["V0001"]}],
  "review_summary": ["V0001","G0001"],
  "note": ""
}
```

响应 `200`：`{"ok":true,"day":47,"saved":true}`（严格三字段）。

**写入安全逐条对照**：

| # | 要求 | 实现 |
|---|---|---|
| 1 | `Origin` 白名单 | `progressOrigin()`：存在时须为 production / preview / `http://127.0.0.1:*` / `http://localhost:*`（用 `new URL()` 解析后比 `protocol+hostname`，防前缀绕过），否则 `403 cross_origin`；`Origin` 缺失时允许，但强制 `content-type: application/json` 且走全套强限制（便于 curl/CLI 冒烟） |
| 2 | 体量 ≤64KB 双检 | `content-length` 头 >65536 或非数字 → `413`；`request.text()` 后按 `TextEncoder` 字节长度 >65536 → `413`。复用现有 `MAX_BODY_BYTES` |
| 2 | 字段白名单 | `parseProgressBody()` 只取 `v/day/completed_at/required_ids/extra_ids/grammar_ids/questions/accuracy/self_rating/wrong_summary/review_summary/note`，**未知字段一律丢弃**；`day` 严格 1..150；`questions` ≤60 条；`answer` ≤2000、`qid` ≤48、`note` ≤2000、各 id 数组 ≤200 项、`self_rating` ≤200 项 |
| 3 | 幂等覆盖 | 主键 UPSERT，见 §2；表 ≤150 行 |
| 4 | 限流 | 复用 `sync_budget` 表：`progress_day:<UTC日>` 全局 500/日、`progress_ip:<UTC日>:<sha256(ip+salt)前12位>` 每 IP 50/日。UPSERT 计数行（不追加行数），超限 `429 ip_write_budget` / `daily_write_budget`；IP 只存哈希不落明文 |
| 5 | 不采信 `correct` | `questions[].correct` 原样保留但不参与任何判定；存储列 `self_reported=1`、payload 内 `self_reported:1`、GET item 内 `self_reported:1`。文档与 skill 均写明「云端自报 / 本机 SQLite `finish-day` 才是掌握权威」 |

`content-type` 缺失 → `400 bad_content_type`；非 GET/POST → `405`；未绑 D1 → `503 no_db`；D1 异常 → `databaseError()`（`503 db_error` / `429 daily_budget|storage_budget`）。

### 3.2 `GET /api/progress`（**必须 `X-NH80-Key`**）

- 复用现有 `authenticate()`：缺/错 key → `401 unauthorized`；未配 secret → `503 no_key`；常量时间比较用现有 `constantTimeEqual()`。
- `?day=N` → 主键查单天；`?latest=1&limit=7` → `ORDER BY server_ts DESC, day DESC LIMIT ?`（默认 7，上限 150）；两者皆无 → `400 bad_query`；`day` 优先。
- 响应 `{"ok":true,"items":[...]}`，无数据 `items: []`。`item` = payload 展开的白名单全字段 + `server_ts`（列，权威）+ `self_reported`（列）+ `day`（列）。
- 全部响应 `cache-control: no-store`，带 `vary: Origin`；CORS 头只对白名单 Origin 回显，绝不用 `*`。

### 3.3 与既有路由共存

`/api/progress` 在入口 `fetch()` 用**独立分支**处理，未加入 `:451` 的既有路由数组。原因：现有 `rejectCrossOrigin()` 只认同源，而进度写入需同时允许 production 与 preview 两个源；独立分支可自定义 Origin 白名单，且**完全不改** `/api/events` 等同源校验与行为。回归测试已断言 `POST /api/events` 无 key 仍 `401` 且不触碰 D1。

---

## 4. 鉴权与额度论证

### 4.1 刻意的不对称

| | 写入 POST | 读取 GET |
|---|---|---|
| 口令 | 无（用户零操作） | 必须 `X-NH80-Key` |
| 代价 | 任何人可写 → 由「自报非权威 + agent 以本机为准」化解 | 学习进度不公开可读 |
| 防护 | Origin 白名单 + 64KB 双检 + 字段白名单 + 按 day 幂等覆盖 + 双层限流 | 常量时间比较 + `no-store`，SW 不缓存 `/api/` |

页面 POST 不需要口令，是用户明确要求（去掉手填 `NH80_SYNC_KEY` 的摩擦）；读取收紧保证隐私。

### 4.2 Workers Free 额度核算（超额只报错、不自动扣费）

| Free 限额 | 本方案占用 | 结论 |
|---|---|---|
| 10 个 D1 库 | 已用 2（production / preview），未新建库 | 远低于上限 |
| 10 万行写/天 | 单次 POST ≈ 3 行写（2 个限流 UPSERT + 1 个主表 UPSERT）；全局上限 500 次/天 → ≤1500 行写/天 | 约 1.5%，可忽略 |
| 5M 行读/天 | 单次 POST 2 行读（限流 SELECT）；CLI 读取 ≤7 行（limit 上限 150） | 可忽略 |
| 5GB 存储 | `study_progress` ≤150 行，单行 payload 实测约 1KB（上限 64KB）→ <1MB；限流计数行每天每键一行、UPSERT 不追加 | 可忽略 |
| 10 万请求/天 | 500 次 POST/天封顶 + 少量 GET | 可忽略 |

叠加既有 `0004_study.sql` 的 `sync_budget` 触发器硬闸门（events/ratings 1000/日、20000 总）作兜底。两层新限流（每 IP 50/日、全局 500/日）比用户举例的「同一天 50 次」略宽松，是为容忍同日多次重试与多设备；仍远低于额度，防「追加型刷爆」的核心是**按 day 覆盖 + 限流**双保险。

`wrangler.jsonc` 保持 `observability:false`，无 KV / R2 / Queues / Workers AI / DO / cron / 自定义域名 / 任何付费绑定；`wrangler deploy` 不会升级套餐。

---

## 5. 端到端实测（命令与输出）

### 5.1 环境与迁移

```
node v22.22.2 / wrangler 4.158.0
production /api/health -> {"status":"ok","features":{"db":true,"sync":true}}
preview    /api/health -> {"status":"ok","features":{"db":true,"sync":true}}
两库 0005 应用 -> "Executed 2 queries"，表与索引存在，COUNT(*)=0
```

### 5.2 部署 Worker 到 preview（仅 preview，为端到端）

```
cd deploy && npx wrangler deploy --config wrangler.jsonc --env preview
-> "No updated asset files to upload. Proceeding with deployment..."
-> Uploaded nihongo80-preview, Current Version ID: 83900d84-dff2-47c7-b774-316fb2cbc1a0
```

`web/` 当时 `git status` 为 0 改动，静态资源**零上传**，对主控前端无影响。

### 5.3 真实 POST Day 149 → CLI 读回

POST（不带 key，带 preview `Origin` 与 `content-type`）：

```
POST /api/progress -> 200 {"ok":true,"day":149,"saved":true}
```

CLI 人类可读（节选）：

```
# Day 149 学习进度（云端自报 · 非权威）
- 完成时间：2026-11-09T10:00:00+08:00（server_ts：2026-11-08T16:52:41.694Z）
- 自报正确率：0.9（客户端自算；权威以本机 finish-day 为准）
- 数据标记：self_reported=1（服务端不采信客户端 correct 为权威）
- 错题（1 条）：Q-149-K0-e2e → V0149
- 自评：V0149：hard / G0149：again
- 复习重点（供当天家教会话）：
  1. 错题优先：V0149
  2. 自评 again/hard 优先：V0149、G0149
  3. 当天新词/语法回顾：V0149、V0150、G0149
（数据来源：云端自报 / 本机 SQLite 权威；不据此推进完成或判掌握）
```

`--json` 返回完整 `{"ok":true,"items":[{...全部字段..., "self_reported":1, "server_ts":"..."}]}`；`--latest 1 --json` 同样读回 Day 149。真实无 key GET → `401 {"ok":false,"reason":"unauthorized"}`。

> 实测发现：Cloudflare 对 urllib 默认 UA（`Python-urllib/*`）返回 `403 Error 1010`；CLI 已显式设 `User-Agent: nh80-progress-read/1`，实测 `200`，无需伪装浏览器。

### 5.4 清理（两库都清，保持干净）

```sh
npx wrangler d1 execute nihongo80 --remote -y \
  --command="DELETE FROM study_progress WHERE day=149; DELETE FROM sync_budget WHERE id LIKE 'progress_%'"
npx wrangler d1 execute nihongo80-preview --remote --env preview -y \
  --command="DELETE FROM study_progress WHERE day=149; DELETE FROM sync_budget WHERE id LIKE 'progress_%'"
```

**production 未写入任何假数据**，只做了 `SELECT` 只读 check（表存在、行数 0）。最终两库只读校验均为：

```
{"progress_rows": 0, "budget_rows": 0, "progress_objects": 2}
```

### 5.5 单元测试（实跑）

```
node tests/test_progress_api.mjs
PASS: POST without Origin accepted (content-type guard + strong limits)
PASS: invalid day rejected with 400
PASS: oversized body rejected with 413 (both content-length and actual length)
PASS: GET without X-NH80-Key denied with 401
PASS: GET with key reads back full item (server_ts + self_reported)
PASS: ?latest=1&limit=7 reads back the saved snapshot
PASS: same-day POST overwrites (row count stays 1, no append)
PASS: unknown fields dropped (whitelist enforced)
PASS: Origin allowlist (production / loopback accepted, cross-site 403)
PASS: POST without content-type rejected
PASS: existing /api/events auth unchanged (still 401 before DB)
PASS: per-IP daily write budget (50) enforced with 429
ALL PASS: /api/progress contract

node tests/test_worker_access.mjs   # 回归
PASS: unauthenticated writes denied before database access
PASS: authenticated check probes D1 without writing
PASS: session metadata conflict is rejected; append and duplicate remain idempotent

python3 scripts/progress_read.py --help   # 正常输出 usage
```

---

## 6. agent 侧用法（skill / CLI）

### 6.1 三处 skill（同一份）

- `skills/nh80-progress/SKILL.md`（仓库真源）
- `.workbuddy/skills/nh80-progress/SKILL.md`（项目级）
- `~/.workbuddy/skills/nh80-progress/SKILL.md`（用户级，WorkBuddy 本机立即可用）

front matter：`name: nh80-progress` + `description`（含触发词「日语学习进度 / 今天学了什么 / nihongo progress」等，声明「即使没点名也要用」及自报非权威）。

### 6.2 CLI 一行用法

```sh
python3 scripts/progress_read.py --latest        # 最近 7 天，人类可读摘要
python3 scripts/progress_read.py --day 47 --json # 指定 Day，原样 JSON
python3 scripts/progress_read.py --latest --base https://nihongo80-preview.cmjfire.workers.dev
```

默认 base = production；密钥默认读 `deploy/.sync-key`（也可 `--key` / `NH80_SYNC_KEY`），**不打印**。退出码 `0/2/3/4`。

### 6.3 复习重点映射（skill 正文）

1. **错题优先**：`wrong_summary[].knowledge_ids` + `questions[]` 中 `correct=false` / `hinted` / `revealed` 的题。
2. **自评 again/hard 优先**：`self_rating` 中 `again` / `hard` 的 id。
3. **当天新词/语法**：`required_ids` + `extra_ids` + `grammar_ids` 回顾与独立造句。
4. `review_summary` 补充队列；`accuracy` 只展示并标注「自报」。

### 6.4 文件协议

- `STATE.md`（`session_v5.py state` 生成的只读镜像）：交叉核对云端 `day` 与 `server_ts` 新鲜度。
- `days/day-NNN/report.md`：人工日报，复习结论写这里，但**不得据此推进完成或判掌握**。
- `AGENTS.md` 新增一节给出给 Claude Code / Codex 的一句话提示词；跨会话只能显式读文件，平台记忆不传递精确状态。

---

## 7. 三个需要注意的点

1. **production Worker 尚未部署新路由**。为遵守「别写 production 假数据、只做只读 check」，本次只把 Worker 部署到 **preview**（Version `83900d84`）做端到端；production 仅执行了迁移与只读校验。CLI 默认 `--base` 是 production，**主控统一部署 production Worker 后 skill 默认路径才可用**；在此之前验证请用 `--base https://nihongo80-preview.cmjfire.workers.dev`。
2. **迁移用 `d1 execute --file` 单文件执行，未写入 `d1_migrations` 表**。主控后续若跑 `npx wrangler d1 migrations apply ... --remote`，0005 会被再执行一次；但文件内全为 `CREATE TABLE/INDEX IF NOT EXISTS`，**幂等安全**，不会重放 0002/0004 的 `ALTER`。
3. **写入公开、读取要密钥是刻意的不对称，且云端自报非权威**。任何人都可 POST（无口令），靠 Origin 白名单 + 64KB 双检 + 字段白名单 + 按 day 幂等覆盖 + 双层限流兜底；GET 必须 `X-NH80-Key`。所有云端结论都要标「自报 / 本机 SQLite `finish-day` 权威」，agent 只读不回写；密钥不打印、不入库、不引入付费服务。

---

## 8. 未做 / 纪律

- 未改任何前端文件、未 `git commit`、未删 `deploy/node_modules/`、未打印或写入密钥、未引入付费绑定、未开 observability、未升级套餐。
- 未写 production 假数据；production 全程只读 check。
- 端到端测试行与限流计数行已从两库清除，最终 `progress_rows=0 / budget_rows=0`。
