# v8 进度云同步架构方案（只读调查 + 出方案）

> 调查日期：2026-11-09。范围：`/Users/mj/Documents/learn/jp/nihongo-80`。
> **本文件是只读调查产物**：未修改任何现有仓库文件、未执行 `nh80 build`、未改任何 DB、未 `git commit`、未部署。
> 仅新增本报告一份。所有结论以仓库现有源码为准，关键位置标注 `文件:行号`。
> 目标：把「页面只留一个完成按钮 → 把当天学习情况保存到云端 → 任何 agent 通过一个 skill 读取」做成可落地、零额外扣费风险、零法律风险的架构。

---

## 0. 现状调查结论（先对齐事实）

### 0.1 现有云端通道（Worker + D1）

| 位置 | 事实 |
|---|---|
| `deploy/worker/src/index.ts:451` | 路由白名单 `["/api/events","/api/reviews","/api/study","/api/study-plan"]`，先 `rejectCrossOrigin` + `preflight`（`:67-94`），再分发。 |
| `:197-291` | `POST /api/events`：**需要 `X-NH80-Key`**（`:199-201`），逐题原始事件、服务端按 `/data/grade/day-NNN.json` 的 SHA-256 重判（`:118-132,249-257`）、`INSERT OR IGNORE` 追加（`:276-280`）、`db.batch` 提交（`:282-285`）。`study_sessions` 元数据不可变、冲突 409（`:262-270`）。 |
| `:301-333` | `GET /api/events`：**需要 `X-NH80-Key`**，按 `id>since` 增量拉取，给本地 `cloud_sync.py` / `study_sync.py` 重判用。 |
| `:341-347` | `authenticate()` 统一鉴权：`constantTimeEqual` 比对 `env.NH80_SYNC_KEY`，未配→503 `no_key`，错→401。`/api/reviews`、`/api/study`、`/api/study-plan` 都走它（`:359-433`）。 |
| 常量 `:45-48` | `MAX_RESULTS=40`、`MAX_BODY_BYTES=64KB`、`MAX_ANSWER_CHARS=2000`。 |
| `deploy/wrangler.jsonc:34` | `run_worker_first: ["/","/api/*","/health"]`——静态资源绕过 Worker，不计请求额度。 |
| `:37-45 / :47-72` | 两个独立 D1：`nihongo80`（production）、`nihongo80-preview`（preview），各自 `migrations_dir: "migrations"`；`observability:false`（`:46/:71`）。无 KV / R2 / AI / DO / cron / 自定义域名。 |
| `deploy/migrations/0003` | `sync_budget(id TEXT PRIMARY KEY, used INTEGER)`——**预算表**。 |
| `deploy/migrations/0004:11-22` | `budget_event`/`budget_rating` 触发器：`AFTER INSERT` 时按 UTC 日 `1000`、累计 `20000` 计数，超额 `RAISE(ABORT)` 回滚整批；`databaseError()`（`:335-339`）映射 `429 daily_budget/storage_budget`。 |
| `d1_migrations` 表 | wrangler 内置迁移追踪表。本地 `.wrangler` 实测结构 `(id, name, applied_at)`，已记录 `0001/0002/0003`；`wrangler d1 migrations apply` 靠它按文件名去重、只跑未应用的。 |

### 0.2 现有「口令」链路（用户要去掉的东西）

- `scripts/study_ui.py:29` 定义 `KEY='nh80.v5.access'`；`:61` `post()` 从 `sessionStorage` 读它作 `X-NH80-Key`，无口令直接抛错；`:62-68` `flush()` 无口令不发送；`:83` `init()` 向 `#studySync` 注入「学习口令输入框 + 同步 + 导出」。
- `scripts/build_v5_site.py:314-319` `sync()` 同样要求 `sessionStorage[STORE+'access']`；`:322` 口令来自 `#accessKey`；`:329-349` `#finish`（文案「保存本次作答」）先写 `localStorage` pending，再 `sync(payload)` POST `/api/events`。
- 结论：**网页 POST 口令 = `NH80_SYNC_KEY` 本身**，它既用于公开页面写、又用于 CLI 读（`scripts/nh80.py:866-870` 从 `deploy/.sync-key` 读同一个值）。要求用户手填到公开页面，等于把读密钥暴露给浏览器历史/肩窥，且用户明确嫌烦。去掉口令 = 公开页面写不再带 `X-NH80-Key`。

### 0.3 本机权威状态（不能动的真源）

- `scripts/nh80.py:63-72` `completion_counts()` 只认 `sessions.status='finished' AND passed=1`。
- `:764-823` `cmd_finish_day()`：`passed = acc≥0.70 AND 必做题集合齐全 AND (choice 模式或 output_confirmed)`（`:792-794`），写 `sessions` / `daily_summary` / `audit_log`。
- `:75-109` `_gate()` 是 `learning.gate` 的次日编排（blocked/deferred），不是完成判定本身。
- `AGENTS.md:13,43`、`CONTRACTS.md:283`：**状态只经 `nh80.py` 写入；不信客户端 `correct`；网页保存只说明云端收到，权威完成仍在本地导入后计算**。
- `STATE.md`、`days/day-NNN/report.md` 是本机生成/人工记录文档（`.gitignore` 忽略）。

### 0.4 前序产物与 skill 平台

- `reports/codex_v8_investigation.md:136`：**仓库内没有任何 `SKILL.md` / skills 目录**；`:213` `generated-key.json` 明文答案表已入公开库。
- `reports/v8_simplify_plan.md:619-634` 已论证：给 `events` 加字段会触发 `session_metadata_conflict` 409、并要同步改 `cloud_sync.py` / `study_sync.py` / `test_worker_access.mjs`；`:628-634` 论证删口令 UI 后两条 POST 路径都会失效。
- 实测：`~/.workbuddy/skills/` 存在，skill 以 `SKILL.md` 的 YAML frontmatter（`name/version/description/description_zh/...`）+ `description` 语义触发；项目级 `.workbuddy/` **当前不存在**。
- 实测：`deploy/.sync-key`（32B）已被 `.gitignore:21` 排除，`git ls-files` 为空；`deploy/worker/src/generated-key.json` **被 `git ls-files` 确认跟踪**。
- `web/sw.js:1`：`C='nh80-v5.1-e03c5bd29321'`，network-first + 离线回退，且 **`pathname.startsWith('/api/')` 直接放行不拦截**。

---

## 1. 页面无口令的写入鉴权

### 1.1 核心判断

纯前端公开页面**无法做真正的身份鉴权**：任何能放在公开 JS/HTML 里的令牌都可被枚举，`NH80_SYNC_KEY` 绝不能下放到页面。因此本方案不追求「证明写者是本人」，而追求两件可证明的事：

1. **写入量有硬上界**（刷不动 D1 存储 / 额度）——靠「按 day 幂等覆盖 + 请求体/字段上限 + 每 IP/每日限流」；
2. **脏数据不污染权威状态**——靠「云端进度标注为自报、非权威；agent 只读、不回写本机 SQLite」。

同源/Origin/Referer 校验只作第一层「挡浏览器跨站与无意刷」，明确承认它挡不住 `curl` 伪造；真正的防线是 1.2 的固定拓扑。

### 1.2 具体机制（逐条对应需求）

新端点 `POST /api/progress` 加入 `index.ts:451` 的路由数组，复用 `rejectCrossOrigin` / `preflight` / `jsonResponse`，**不复用 `authenticate()`**（读才用）。

| 层 | 机制 | 实现要点 | 挡住什么 |
|---|---|---|---|
| L1 同源 | `rejectCrossOrigin(request,url)`（`:67-74`）：`Origin` 存在且 ≠ `url.origin` → 403 `cross_origin`；`Referer` 存在时其 origin 也必须同源 | 复用现有函数，零新增逻辑 | 浏览器跨站表单/CSRF、多数普通爬虫；伪造头挡不住（承认） |
| L1 预检 | `preflight()`（`:81-94`）：`OPTIONS` 只允许同源，`Access-Control-Allow-Methods: GET, POST, OPTIONS` | 把 `/api/progress` 纳入 `:451` 数组即可 | 跨站预检 |
| L2 体量 | `MAX_BODY_BYTES` 对 progress 单独设 **32KB**（比 events 的 64KB 更紧）；`content-type: application/json`；`strictInt(day,1,150)`（`:154-158`）；`questions` 数组 ≤60、单 `qid` ≤48 且 `^[A-Za-z0-9_.:-]{1,48}$`、单 `answer` ≤2000 字符、`note` ≤2000 字符、各 id 数组 ≤200 且 `^[VGK]\d{4}$` | 与 `parseResults()`（`:172-195`）同构，独立 `parseProgress()` | 超大 body / 字段膨胀型刷写 |
| L3 幂等覆盖 | `study_progress` 以 `day` 为主键，`INSERT ... ON CONFLICT(day) DO UPDATE SET ...=excluded...`。**同一天无论写多少次只 UPDATE 一行，表最大 150 行** | 见 §2 SQL | 「追加型刷爆存储」被根除 |
| L4 每 IP/每日限流 | Worker 读 `CF-Connecting-IP`（本地 dev 回退 `local`），`key='progress_ip:'+UTC日期+':'+sha256(ip+'|'+NH80_SYNC_KEY).slice(0,12)`；`INSERT INTO sync_budget(id,used) VALUES(?,1) ON CONFLICT(id) DO UPDATE SET used=used+1`，取回 `used`，> **40** → 429 `ip_write_budget`。IP 只存哈希、不落明文 | **复用 `sync_budget`（0003）表，不新建表**；计数行本身 UPSERT 不追加 | 单 IP 高频刷；行数 = 当日独立 IP 数，极小 |
| L4 每日全局限流 | `key='progress_day:'+UTC日期`，同样 UPSERT，> **500** → 429 `daily_write_budget` | 同一张 `sync_budget` 表 | 分布式刷；兜底 |
| L5 预算表复用 | 可选 `budget_progress` 触发器（§2 给出），与 `0004:11-22` 同口径写 `sync_budget` 的日/累计计数；因按 day 覆盖，INSERT 仅每 day 首次触发（≤150 次/库），边际消耗可忽略，主要价值是口径统一 | 标为**可选**，非必需 | 与既有预算口径对齐 |
| L6 平台兜底 | Workers Free / D1 Free 超额 **fail-closed**（详见 1.3） | 无需代码 | 任何漏网流量 |

`server_ts`（Worker 收到时刻）为权威时间戳；`completed_at`/`client_ts` 仅作客户端参考并截断长度。`payload_hash = SHA-256(规范化 body)` 可选，用于「内容未变则跳过写入」进一步省写。

### 1.3 为什么不产生账单（明确论证）

实测/政策（2026-11，Cloudflare 官方文档与多来源一致）：

- **Workers Free**：100,000 请求/日（UTC 重置）、10ms CPU/请求、50 subrequest/请求；超额请求**失败**（Error 1027），不是计费。
- **D1 Free**：5,000,000 rows read/日、100,000 rows written/日、5GB 总存储（每库 500MB）、Free 10 个库；官方口径「**Free plan queries stop when daily read or write limits are exceeded**」「存储满则阻止 insert / schema / index」——即**拒绝服务，不扣费**。
- **关键**：从 Free 升级到 Workers Paid（$5/月起）或开通 R2/KV/Queues 等付费产品，**必须人工在 Dashboard 主动操作**；脚本、`wrangler deploy`、`d1 migrations apply` 都不会自动升级。`wrangler.jsonc` 明确 `observability:false`、无任何付费绑定，`deploy_cloudflare.sh` 不升级套餐。
- 本方案**不新增任何云产品**：不建第三个 D1（仍是 2 个，远低于 10）、不引入 KV/R2/Queues/AI/Durable Objects/自定义域名/cron、不启用 D1 read replication、不加 `run_worker_first` 范围（静态资源继续绕过 Worker 不计请求）。
- 本方案把本站占用压到极低：`study_progress` ≤150 行、每 IP/每日 ≤40 次、每日全局 ≤500 次写，叠加既有 `sync_budget` 的 1000/日、20000 总硬闸门（0004 触发器）。
- **法律风险**：数据是用户自己产生的学习记录，不含第三方个人信息、不含受限教材正文（内容许可已由 `DATA_LICENSES.md` / `CONTRACTS.md:294` 约束，受限内容只链接原站）；不新增外部数据源、不做公开个人信息处理。IP 仅哈希截断用于限流、不留存明文。

**唯一非零影响**：Free 额度是**账户级共享**，同账号其他项目耗尽额度会连带让本站报错；以及被刷时限流会返回 429/503 导致当天保存失败——但都只是**报错/拒绝**，不是账单、不是扣费、不是升级。

---

## 2. 数据模型（D1 SQL）

### 2.1 设计原则

- **一张主表 `study_progress`，按 `day` 唯一**（`day` 作 `PRIMARY KEY` 即等价 `UNIQUE(day)`），语义是「当天完成快照」，**覆盖而非追加**。
- 不定长内容（题目、id 列表、错题/复习集、备注）放 **JSON 列**：列数远低于 D1 上限 100 列（`developers.cloudflare.com/d1/platform/limits/`），单行远低于 2MB。
- **不改动 `events` 表任何列**：避免触发 `index.ts:259-264` 的 `session_metadata_conflict` 409、`test_worker_access.mjs`、`cloud_sync.py` / `study_sync.py::_validate_event` 的连锁改动。
- 与 `d1_migrations` 兼容：文件名 `0005_progress.sql`，仅用 `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`（**幂等**）；0002/0004 含无 `IF NOT EXISTS` 的 `ALTER TABLE ... ADD COLUMN`，必须靠 `d1_migrations` 保证只跑一次，绝不可手动 `d1 execute` 重放。

### 2.2 `deploy/migrations/0005_progress.sql`

```sql
-- 0005_progress.sql — 当天学习完成快照（学习者自报，非权威）
-- 幂等：day 为主键，POST /api/progress 用 UPSERT 覆盖；全表最多 150 行。
-- 应用方式（两库分别、各跑一次；wrangler 用 d1_migrations 去重）：
--   npx wrangler d1 migrations apply nihongo80 --remote --config wrangler.jsonc
--   npx wrangler d1 migrations apply nihongo80-preview --remote --env preview --config wrangler.jsonc
-- 本地开发：去掉 --remote（会自动补齐本地尚未应用的 0004/0005）。

CREATE TABLE IF NOT EXISTS study_progress (
  day             INTEGER PRIMARY KEY CHECK(day BETWEEN 1 AND 150),  -- 幂等 UNIQUE：按 day 覆盖
  -- 时间 / 关联
  completed_at    TEXT NOT NULL,        -- 客户端点「完成」时刻（ISO 8601，截断 40 字符，仅参考）
  server_ts       TEXT NOT NULL,        -- Worker 收到时刻（UTC ISO 8601），权威时间戳
  client_ts       TEXT,                 -- 客户端原始时间戳（截断 40 字符，可空）
  session         TEXT,                 -- 关联既有 events.session（可空，便于追溯，不强制一致）
  -- 当天范围
  required_ids    TEXT NOT NULL DEFAULT '[]',  -- JSON array: 必学词 id，"V####"
  extra_ids       TEXT NOT NULL DEFAULT '[]',  -- JSON array: 拓展词 id
  grammar_ids     TEXT NOT NULL DEFAULT '[]',  -- JSON array: 新语法 id，"G####"
  -- 作答明细（每题 qid / 作答 / 是否正确 / 是否提示 / 是否看答案 / 用时）
  questions       TEXT NOT NULL DEFAULT '[]',  -- JSON array: {qid,answer,correct,hinted,revealed,seconds}
  attempted       INTEGER,              -- 已作答题数
  total           INTEGER,              -- 当天必做题总数
  accuracy        REAL,                 -- 0..1 客户端自算，仅展示；权威正确率由本机 cmd_finish_day 重算
  -- 自评（忘了 / 模糊 / 记住了）
  self_rating     TEXT CHECK(self_rating IN ('again','hard','good') OR self_rating IS NULL),
  -- 错题与复习集摘要
  wrong_summary   TEXT NOT NULL DEFAULT '[]',  -- JSON array: {qid,knowledge_ids,error_type}
  review_summary  TEXT NOT NULL DEFAULT '[]',  -- JSON array: {kid,reason,due,stage}
  -- 会话备注
  note            TEXT,                 -- 自由文本（≤2000 字符）
  -- 完整性 / 版本
  payload_hash    TEXT,                 -- SHA-256(规范化 body)，可选：内容未变可跳过写入
  source          TEXT NOT NULL DEFAULT 'web',
  v               INTEGER NOT NULL DEFAULT 1
);

-- agent 端 ?latest=1 用 server_ts 取最近一次完成；?day=N 走主键。
CREATE INDEX IF NOT EXISTS idx_progress_server_ts ON study_progress(server_ts DESC);
CREATE INDEX IF NOT EXISTS idx_progress_session   ON study_progress(session);

-- 【可选】与 0004 预算口径对齐的触发器。因按 day 覆盖，INSERT 仅每 day 首次发生
-- （全库 ≤150 次），边际消耗可忽略；主要价值是让「进度写入」也纳入 sync_budget 统
-- 一日/累计计数。若追求最小改动可不建，改由 Worker 侧限流计数（§1.2 L4）承担。
-- CREATE TRIGGER IF NOT EXISTS budget_progress AFTER INSERT ON study_progress BEGIN
--   INSERT OR IGNORE INTO sync_budget(id,used) VALUES(substr(NEW.server_ts,1,10),0),('total',0);
--   SELECT CASE WHEN (SELECT used FROM sync_budget WHERE id=substr(NEW.server_ts,1,10)) >= 1000 THEN RAISE(ABORT,'daily_budget') END;
--   SELECT CASE WHEN (SELECT used FROM sync_budget WHERE id='total') >= 20000 THEN RAISE(ABORT,'storage_budget') END;
--   UPDATE sync_budget SET used=used+1 WHERE id IN (substr(NEW.server_ts,1,10),'total');
-- END;
```

### 2.3 限流计数键约定（复用 `sync_budget`，不新建表）

| `sync_budget.id` | 含义 | 上限 | 写方式 |
|---|---|---|---|
| `progress_ip:<UTC日>:<ip哈希12>` | 每 IP 每日写次数 | 40 | `INSERT ... ON CONFLICT(id) DO UPDATE SET used=used+1` |
| `progress_day:<UTC日>` | 全局每日写次数 | 500 | 同上 |

两者都是「每天每键一行、UPSERT 不追加」，行数有界；IP 只存 `sha256(ip|salt)` 前 12 位，salt 用 `NH80_SYNC_KEY`，不落明文。

### 2.4 两库都要应用

- `wrangler.jsonc:37-45`（production `nihongo80`）与 `:47-72`（preview `nihongo80-preview`）是**两个独立 D1**，`release_guard.py:24-30` 会拒绝两环境共用一个 `database_id` 的回退。
- 新迁移必须对**两库各 `--remote` apply 一次**（命令见 SQL 注释；preview 走 `--env preview`）。`d1_migrations` 表按文件名记录，重复执行安全。
- 本地 miniflare 目前只到 `0003`（实测），本地 `dev` 前会自动补 `0004/0005`；注意 0004 的 `ALTER TABLE ADD COLUMN knowledge_ids` 在无 `IF NOT EXISTS` 下重放会报错，务必走 `migrations apply` 而非手工 `execute`。

### 2.5 字段 → 智能复习能力映射

`day / completed_at / server_ts` → 定位与新鲜度；`required_ids / extra_ids / grammar_ids` → 当天回顾范围；`questions[].correct/hinted/revealed` → 逐题薄弱点；`self_rating` → 忘了/模糊/记住了优先级；`wrong_summary / review_summary` → 错题与复习集；`note` → 会话备注；`accuracy` 仅展示（非权威）。

---

## 3. API 契约

### 3.1 三个端点总览与鉴权差异

| 端点 | 方法 | 谁调用 | 鉴权 |
|---|---|---|---|
| `/api/progress` | POST | 公开网页「完成」按钮 | **无用户口令**：同源 Origin/Referer + 体量上限 + 按 day 幂等覆盖 + 每 IP/每日限流（§1.2）。**不带 `X-NH80-Key`** |
| `/api/progress?day=N` | GET | agent / skill CLI | **`X-NH80-Key` = `NH80_SYNC_KEY`**（复用 `authenticate()`，`constantTimeEqual`），否则 401/503 |
| `/api/progress?latest=1` | GET | agent / skill CLI | 同上 |

### 3.2 `POST /api/progress`（请求样例）

```json
{
  "v": 1,
  "day": 12,
  "session": "web-12-6f1c...",
  "client_ts": "2026-11-09T10:00:00+08:00",
  "completed_at": "2026-11-09T10:32:11+08:00",
  "required_ids": ["V0001","V0002"],
  "extra_ids": ["V0101"],
  "grammar_ids": ["G0012"],
  "questions": [
    {"qid":"Q-012-K0-529a","answer":"ニチ","correct":true, "hinted":false,"revealed":false,"seconds":7},
    {"qid":"Q-012-G-f4b0","answer":"…或…","correct":false,"hinted":true, "revealed":false,"seconds":21}
  ],
  "attempted": 6,
  "total": 6,
  "accuracy": 0.83,
  "self_rating": "hard",
  "wrong_summary": [{"qid":"Q-012-G-f4b0","knowledge_ids":["G0012"],"error_type":"usage"}],
  "review_summary": [{"kid":"V0002","reason":"曾答错","due":null,"stage":null}],
  "note": "「〜か」表示 or 的用法还不太稳"
}
```

响应 `200`：

```json
{"ok":true,"day":12,"upserted":true,"server_ts":"2026-11-09T02:32:15.123Z","skipped":false}
```

（`skipped:true` 表示 `payload_hash` 与库内一致、未发生写入。）

### 3.3 `GET /api/progress?day=N` / `?latest=1`

请求头：`X-NH80-Key: <NH80_SYNC_KEY>`（值来自 `deploy/.sync-key`），`Accept: application/json`。

`?day=12` 响应 `200`：

```json
{"ok":true,"progress":{"day":12,"completed_at":"...","server_ts":"...","required_ids":"[\"V0001\",\"V0002\"]","questions":"[...]","accuracy":0.83,"self_rating":"hard","wrong_summary":"[...]","review_summary":"[...]","note":"...","source":"web","v":1}}
```

无数据：`200 {"ok":true,"progress":null,"day":12}`。
`?latest=1`：`ORDER BY server_ts DESC LIMIT 1`，响应同形（带 `progress` 或 `null`）。`day` 优先于 `latest`；两者皆无 → `400 bad_query`。

> JSON 列在 D1 里是 TEXT；Worker 读时可原样返回字符串由 CLI 解析，或 `JSON.parse` 后展开成对象返回给 skill（推荐后者，见 §4）。两者择一写进契约即可，不要混用。

### 3.4 错误码（沿用现有 `reason` 风格）

| status | reason | 触发 |
|---|---|---|
| 400 | `bad_json` / `bad_version` / `bad_day` / `bad_query` / `bad_questions` / `bad_ids` | 解析/校验失败 |
| 403 | `cross_origin` | `Origin`/`Referer` 非同源 |
| 405 | `method_not_allowed` | 非 GET/POST |
| 413 | `body_too_large` / `note_too_large` | 超过 32KB / 字段上限 |
| 401 | `unauthorized` | GET 缺/错 `X-NH80-Key` |
| 429 | `ip_write_budget` / `daily_write_budget` / `daily_budget` / `storage_budget` | L4 限流 / 既有预算触发器 |
| 503 | `no_key` / `no_db` / `db_error` | 未配密钥 / 未绑 D1 / D1 异常 |

响应统一 `cache-control: no-store`（`jsonResponse` `:54-63` 已有），`vary: Origin`。

### 3.5 与 `/api/events` 共存：**独立，不复用、不改动**

结论：**新增独立端点 + 独立表，与 `/api/events` 完全解耦**。理由：

1. `/api/events` 是**追加型逐题原始事件 + 服务端重判**（`INSERT OR IGNORE`、`UNIQUE(session,qid)`、`db.batch`），幂等靠 `session+qid` 而非 `day`；不同 `session` 可无限追加，**无法「按 day 覆盖」**，也就无法给出 §1.3 的「≤150 行」硬上界。
2. 去掉 `/api/events` 的口令会让匿名者污染 CLI 拉取与本地重判的数据源（`study_sync.py::_validate_event`、`cloud_sync.group_events`）；而给它加字段又会触发 `session_metadata_conflict` 409 与 `test_worker_access.mjs`（`reports/v8_simplify_plan.md:619-623,686`）。
3. 新表语义是「**当天完成快照（弱信号，给 agent 快速读）**」，`events` 语义是「**过程证据（给 CLI 重判、算权威完成）**」，职责正交。
4. **最小改动**：`index.ts` 只在 `:451` 数组加 `"/api/progress"`、新增 `handleProgress()` 分支；`authenticate()`、`handlePostEvents()`、`handleGetEvents()`、`loadAnswerKey()`、`databaseError()` 一行不改。

**保留 `/api/events` 的既有链路**（会话侧 CLI 注入 `deploy/.sync-key` 后同步、或离线队列 `import-file`），它仍是 `cmd_finish_day()` 权威判定的数据入口；新 `/api/progress` 不替代它。页面「完成」按钮只发 `/api/progress`（另保留本机 `localStorage` pending 兜底），**不再要求口令、也不再主动 POST `/api/events`**。

---

## 4. agent skill 落地

### 4.1 放置路径（一份真源 + 三处可用）

| 位置 | 作用 | 谁读 |
|---|---|---|
| **仓库内 `{repo}/skills/nh80-progress/SKILL.md`** | **唯一真源**，纯文本骨架，随 git 分发 | 任意 agent 经 `AGENTS.md` 指引 |
| **仓库内 `{repo}/.workbuddy/skills/nh80-progress/`**（`SKILL.md` 拷贝/软链 + `scripts/progress_read.py` 引用） | WorkBuddy 项目级，clone 后自动加载 | WorkBuddy |
| **`~/.workbuddy/skills/nh80-progress/`**（`SKILL.md` 拷贝 + 脚本路径指向仓库 `scripts/`） | WorkBuddy 用户级，**本机立即可用**，不依赖 clone | WorkBuddy |
| **仓库根 `AGENTS.md` 增一节** | 写明「读取学习进度时执行 `python3 scripts/progress_read.py ...`，详见 `skills/nh80-progress/SKILL.md`」 | Codex / Claude Code / 任何读 AGENTS.md 的 agent |

> 说明：`{repo}/.workbuddy/` 当前不存在（实测）。跨平台关键是**不依赖某平台专有目录**：三个 agent 都读 `AGENTS.md`（或 `CLAUDE.md` 指向它），因此把「入口命令」写进 `AGENTS.md` 是「任何 agent 都能用」的兜底；WorkBuddy 另有项目级/用户级 skill 自动语义触发。Claude Code 如需原生加载，可把同一份 `SKILL.md` 再软链到 `~/.claude/skills/nh80-progress/`。**脚本只放一份**：`{repo}/scripts/progress_read.py`，各 skill 用相对/可解析路径引用，避免漂移。

### 4.2 密钥从哪读

`deploy/.sync-key`（32B，`.gitignore:21` 已排除，**不入库**）。与 `nh80.py:848-850,866-870` 完全一致：

- 优先级：`--key-file` > 环境变量 `NH80_SYNC_KEY` > 默认 `<repo>/deploy/.sync-key`（`read_text().strip()`）。
- 绝不出现在命令行参数、stdout、日志、异常信息、报告输出里；`study_sync.py:33-35` 已有「异常不带 URL/正文/凭据」的范例，照抄。
- 默认 base：`https://nihongo80.cmjfire.workers.dev`（真实数据在 production）；`--base` 可切 preview `https://nihongo80-preview.cmjfire.workers.dev`。

### 4.3 `scripts/progress_read.py` 接口设计（跨平台，仅标准库）

```
python3 scripts/progress_read.py [--day N | --latest] [--base URL]
                                 [--key-file PATH] [--json] [--timeout 15]
```

- 只发 **GET** `/api/progress?day=N` 或 `?latest=1`，头 `X-NH80-Key: <key>`、`Accept: application/json`；用 `urllib.request`，不写任何文件、不改任何状态。
- 默认输出**人类可读 Markdown 复习建议**（§4.5 模板），供 agent 直接注入家教会话；`--json` 输出原始 JSON 供 agent 自行解析。
- 退出码：`0` 成功 / `2` 参数或密钥缺失 / `3` 网络或 HTTP 错误（401/503 等，只打印 `reason`，不打印凭据）/ `4` `progress:null`（无数据）。
- 关键函数：`load_key() -> str`、`fetch(base, key, params) -> dict`、`render(progress) -> str`、`main(argv) -> int`。把 JSON 列 `json.loads` 后展开。

### 4.4 `SKILL.md` 完整结构（骨架）

```markdown
---
name: nh80-progress
version: 1.0.0
display_name: 日语学习进度读取
display_name_en: Nihongo Study Progress Reader
description: 读取 Nihongo-80 日语学习站云端「当天完成快照」，生成当天家教会话的复习建议。只要用户提到「今天学了什么 / 学到第几天 / 学习进度 / 复习建议 / 错题 / 忘了哪些词 / 继续上次 / 日语复习 / nh80 / 日语家教」——即使没点名这个 skill 也要用它。注意云端进度是学习者自报、非权威，权威完成以本机 SQLite 为准。
description_zh: （同上中文）
description_en: Reads the cloud study-progress snapshot for the Nihongo-80 site and turns it into a tutoring session's review plan. Use whenever the user asks about today's study, current day, progress, weak words/grammar, wrong answers, or resuming Japanese review.
---

# nh80-progress · 日语学习进度读取

## 何时用
用户问「今天学了什么 / 学到第几天 / 帮我复习 / 哪些词忘了 / 上次错哪了 / 继续日语家教」时自动触发。

## 数据性质（必读，别搞错）
- 云端 `study_progress` 是**网页「完成」按钮自报的当天快照**：`correct` / `accuracy` 是客户端自算，**非权威**。
- **权威完成**是本机 `data/state.db` 的 `sessions.status/passed/accuracy`（`scripts/nh80.py::cmd_finish_day`，条件：必做题齐全 + 正确率≥70%）。
- 本 skill **只读云端、不写本机、不推进课程、不判掌握**（`AGENTS.md:13,43`、`CONTRACTS.md:283`）。

## 读取步骤
1. 确认仓库根（`SKILL.md` 所在仓库），脚本在 `<repo>/scripts/progress_read.py`，密钥在 `<repo>/deploy/.sync-key`（不入库，勿显示）。
2. 默认取最近一天：`python3 scripts/progress_read.py --latest`
   指定某天：`python3 scripts/progress_read.py --day 12`
   机器解析：`--json`；切 preview：`--base https://nihongo80-preview.cmjfire.workers.dev`
3. 同时（只读）看本机 `STATE.md` 与 `days/day-NNN/report.md`：若云端 day 领先/落后本机，**提示先跑 `python3 scripts/nh80.py study-sync` 或 `import-file` 让本机权威状态追上，不擅自推进**。

## 输出模板（默认 Markdown）
（见本项目报告 §4.5；脚本 render() 已实现，agent 直接用其 stdout 即可）

## 转成当天家教会话的复习建议（规则）
1. `self_rating=again/hard` 的 kid → 最高优先，先回忆再给例句，不宣告掌握。
2. `wrong_summary[].knowledge_ids` 与 `review_summary[]` → 逐条纠错 + 复述，按 `reason` 归类。
3. 当天 `required_ids` / `grammar_ids` → 用当日新语法造句、新词做双向遮盖回忆。
4. `questions[].hinted/revealed=true` 的题 → 视为未独立答出，降低置信。
5. `accuracy` 只作展示并标注「自报」，**不得**据此说「已达标 / 已掌握」。
6. `note` 里的自述薄弱点 → 作为会话切入点。
7. 结尾附「数据来源：云端自报 / 本机权威」与 `server_ts`，并交叉核对 `STATE.md`。

## 约束
- 不引入第三方依赖（本机 python 为 externally-managed，标准库够用）。
- 不打印密钥、不写文件、不改 DB、不调 `/api/events` 写接口。
- 密钥缺失 → 提示用户检查 `deploy/.sync-key`，不要让用户把密钥贴进对话。
```

### 4.5 复习建议输出模板（`progress_read.py --latest` 默认 stdout）

```markdown
# Day 012 学习进度（云端自报 · 非权威）
- 完成：2026-11-09 10:32（server_ts 2026-11-09T02:32:15Z）
- 当天范围：必学词 12 · 拓展 3 · 新语法 2（G0012 …）
- 自报正确率：0.83（客户端自算；权威以本机 cmd_finish_day 为准）
- 自评：不熟 hard
- 错题 / 薄弱：G0012（usage）· V0002（曾答错）
- 复习集：V0002
- 备注：「〜か」表示 or 的用法还不太稳

## 今日家教会话建议
1. 先回忆自评「不熟」的 V0002 / G0012，用当日例句复述，不宣告掌握。
2. 错题 Q-012-G-f4b0 纠错后隔题再测；hinted 题按未独立答出处理。
3. 用 G0012 造两句，覆盖当天必学词。
4. 本机 STATE.md 当前 Day 001，与云端 Day 012 不一致 → 先跑
   `python3 scripts/nh80.py study-sync` / `import-file` 让本机权威状态追上，再继续。

（数据来源：云端自报 / 本机 SQLite 权威；不据此推进完成或判掌握）
```

---

## 5. 与现有完成门控的关系（避免两套状态打架）

### 5.1 明确分层，单向只读

| | 云端 `study_progress` | 本机 `data/state.db` |
|---|---|---|
| 语义 | 学习者**自报的当天完成快照**（弱信号） | **唯一权威**完成/FSRS/能力卡（`AGENTS.md:13`、`CONTRACTS.md:290`） |
| 写入方 | 公开页面 `POST /api/progress` | **只经 `python3 scripts/nh80.py ...`**（事务 + `audit_log`） |
| 内容 | day / 范围 / 逐题自报 / 自评 / 错题摘要 / 备注 | `sessions.status/passed/accuracy`、`attempts`、`fsrs_cards`、`daily_summary` |
| 谁判定完成 | **不判**（表里不存 `passed`/`status`） | `cmd_finish_day()`：`acc≥0.70` + 必做题齐全 + choice 模式（`nh80.py:792-794`） |
| agent 用法 | 读来生成**复习建议** | 权威结论，`STATE.md` / `report.md` 依它 |

### 5.2 不打架的硬规则（写进 `AGENTS.md` / `SKILL.md`）

1. **永不回写**：agent 读云端 progress 后，**不得**写 `data/state.db` 的 `sessions` / `fsrs_cards` / `passed`，不得调用 `cmd_finish_day` 去「确认」云端结果。
2. **不信客户端 correct**：云端 `questions[].correct` / `accuracy` 仅展示（`AGENTS.md:39,43`、`CONTRACTS.md:283`）；「达标/掌握」只认本机重判后的 `cmd_finish_day`。
3. **`STATE.md` / `days/day-NNN/report.md` 仍是本机权威文档**：agent 读云端只作**补充上下文**；若云端与本机不一致（如云端 Day 012、本机 Day 001），提示「先跑 `study-sync` / `import-file` 让本机追上」，**不擅自推进、不覆盖人工日报**（`HANDOFF.md:105`）。
4. **时间戳标注**：所有云端结论附 `server_ts` 与「自报/非权威」标签，避免与本机 `STATE.md` 的精确状态混淆（`HANDOFF.md:25` 已声明平台不自动传递精确状态）。
5. **过程证据链保留**：`/api/events` + `study_sync.run()` + `import-file` 继续负责把原始作答拉回本地重判、驱动 `cmd_finish_day`；新端点不替代它（§3.5）。
6. **自评只排期不判掌握**：`self_rating` 与 `review_summary` 用于复习优先级，不写 `correct`、不推进 FSRS 掌握（`CONTRACTS.md:290,293`）。

一句话：**一个管「权威判定」（本机，只经 CLI 写），一个管「快速读取与复习提示」（云端，agent 只读）**；数据单向从本机 CLI 侧产出证据、云端只提供轻量快照，不存在双主写入。

---

## 6. 风险清单

### 6.1 明文答案表 `generated-key.json` 已进公开仓库 —— 对本方案的影响

- 事实：`git ls-files` 确认 `deploy/worker/src/generated-key.json` **被跟踪**（671,937 字节、`answers` 8007 题明文 `answer`），随 `4462cb0` / `f0571dc` 提交（`reports/codex_v8_investigation.md:213`）。`release_guard.py:56-57` / `CONTRACTS.md:294` 只保证它**不打包进 Worker**，Worker 判分读的是公开 `web/data/grade/day-NNN.json` 的 SHA-256 摘要。
- **不影响写入鉴权**：新端点不依赖答案表、不引 `generated-key.json` 进 `index.ts`。
- **不影响账单/法律**：是自建题库产物、非第三方受限内容、非新增数据。
- **但削弱「防刷写入」的可信度**：任何人可从公开仓库枚举 `qid → answer`，构造「全对」的假进度 POST 到无口令的 `/api/progress`，agent 读到会**误导复习建议**。这正是 §5「云端必须标注自报/非权威、agent 以本机 SQLite 为准」的根本原因；也印证 `CONTRACTS.md:294` 已承认「公开分片可枚举、不用于防作弊」——本方案目标本就不是防作弊，而是**防超额 + 防脏数据污染权威状态**。
- 可选后续清理（**独立于本方案，本报告不执行**）：把 `generated-key.json` 移出 git 并加入 `.gitignore`；但 `nh80 build` 会重新生成它（`nh80.py:292`）、`tests/test_v7.py:169` 依赖它，需同步处理构建/测试，不能只删文件。

### 6.2 D1 / Workers Free 额度

- 额度：Workers 100k req/日、D1 5M read / 100k write 每日、5GB 存储、10 库；超额 **fail-closed**（Error 1027 / D1 queries stop / 429），**不自动扣费、不自动升级**（§1.3）。
- 账户级共享：同账号其他项目可能连带耗尽 → 本站当天保存失败（仅报错）。`sync_budget` 1000/日、20000 总（0004）+ 新限流 + ≤150 行覆盖把本站占用压到极低。
- 文档口径不一致：`HANDOFF.md:99` 写「1000 条/日、5000 条总」，而 `0004_study.sql:13-14,19-20` 是 **1000/日、20000 总**。以代码为准；实施时应顺手订正文档（本方案不改文件，仅提示）。
- `run_worker_first` 仅 `/`、`/api/*`、`/health`（`wrangler.jsonc:34`），静态资源绕过 Worker 不计请求；`observability:false`。

### 6.3 Service Worker 缓存（最容易漏的一项）

- `web/sw.js:1` `C='nh80-v5.1-e03c5bd29321'`：`fetch` 是 network-first + 离线回退，并**明确跳过 `/api/`** → `/api/progress` 的 GET/POST **不会被 SW 缓存**，天然安全。
- 但 `day-*.html` / `app.js` 无版本号，`sw.js` 的 `revision` 由 `build_v5_site.py:833` 用 `CSS+JS+study_ui.CSS+study_ui.JS+curriculum` 哈希生成，**HTML 模板不在哈希里**。若只改 HTML（删口令 UI、留完成按钮）而 JS/CSS 恰好抵消，`C` 不变 → `activate` 不删旧缓存 → 弱网/离线命中旧页面（仍要求口令、仍 POST `/api/events`），用户会看到「完成按钮没生效」。
- **必须**：bump `C`（把 HTML 模板纳入 `:833` 哈希输入，或显式改 `nh80-v5.2-<revision>`），否则前端改造「看起来没生效」。这是最小改动里最隐蔽的一项。

### 6.4 隐私（学习数据公开可读吗）

- **读取要密钥**：`GET /api/progress` 必须 `X-NH80-Key`（`authenticate()`），响应 `no-store`，SW 不缓存 → 学习进度**不公开可读**。
- **写入不要口令**：无口令 POST = 任何人可写（含伪造/投毒）。这是刻意的不对称：写入放开换取「用户零操作」，读取收紧保证隐私；代价由「自报非权威 + agent 以本机为准」化解。
- 静态公开资源 `web/data/catalog.json` / `grade/*.json` 不含个人进度（`CONTRACTS.md:289`）。
- 数据为用户自己的学习记录，无第三方个人信息；IP 仅哈希截断计数、不落明文；`deploy/.sync-key` / `data/review/` / `STATE.md` / `days/` 均已在 `.gitignore`，绝不入库、不进日志、不进 skill 输出。

### 6.5 最小改动原则下**必须保留**的现有代码

- `index.ts` 全部现有逻辑：`/api/health`、`POST/GET /api/events`、`/api/reviews`、`/api/study`、`/api/study-plan`、`rejectCrossOrigin/okOrigin/preflight`、`constantTimeEqual`、`loadAnswerKey/regrade`、`databaseError()`、`:451` 现有路由、`/` 转发与 ASSETS 回退。新增只加 `"/api/progress"` 分支 + `handleProgress()`。
- `migrations/0001~0004` 全部保留不改；新迁移只 `CREATE ... IF NOT EXISTS`，不动 `events` 列（避免 409 与测试连锁）。
- `wrangler.jsonc`：两库独立绑定、`run_worker_first`、`html_handling:"none"`、`observability:false` 全保留；不新增服务/绑定。
- `nh80.py`：`_gate()` / `cmd_finish_day()` / `completion_counts()` / `cmd_study_sync()` / `cmd_pull_cloud()` / `cmd_import_file()` 全保留——本机 SQLite 权威不可动。
- `study_sync.py` / `cloud_sync.py`：`_validate_event`、`EVENT_COLUMNS`、`study_sessions` 元数据冲突逻辑全保留（新端点不碰 events）。
- `build_v5_site.py`：`collectPayload()` 的 `results`/`practice_mode` 形状、`#finish` 的 `localStorage` pending 兜底、`STORE+'lastDay'`、`#restartPractice`、`__QUIZ__/__LISTEN__/__SENT__` 全保留；`study_ui.py` 的 `nh80.v9.pending.*` 离线队列与 `window.NHStudy` 全局保留。**只删口令输入框与口令校验分支**。
- `release_guard.py:24-30,53-57`（两库隔离、grade 分片、`generated-key.json` 不得进 index.ts）、`CONTRACTS.md` v8/v9 修订、`AGENTS.md:13,43`、`.gitignore` 全保留。

### 6.6 实施顺序（供落地参考，本方案不执行）

1. 写 `deploy/migrations/0005_progress.sql` → 两库 `migrations apply --remote`。
2. `index.ts` 加 `handleProgress()` + 路由分支 + `parseProgress()` + 限流（复用 `sync_budget`），`preflight` 若用自定义头再补 allow-headers。
3. 前端：`build_v5_site.py` / `study_ui.py` 删口令 UI，保留一个「完成」按钮 → `POST /api/progress`；**bump `sw.js` 的 `C`**；`nh80 build` 重生成。
4. 新增 `scripts/progress_read.py`、`skills/nh80-progress/SKILL.md`、仓库级/用户级 skill 拷贝，`AGENTS.md` 增一节。
5. 回归：`release_guard.py`、`tests/test_worker_access.mjs`（加 `/api/progress` 同源/鉴权/幂等/限流断言）、`test_v7.py`、`test_completion_gate.py`；`CONTRACTS.md` 补 v10 修订；订正 `HANDOFF.md:99` 的 5000→20000。

---

## 7. 一页速览

- **推荐机制**：公开页面「完成」按钮 `POST /api/progress` 用「同源 Origin/Referer + 32KB 体量上限 + 按 `day` 幂等覆盖（≤150 行）+ 每 IP/每日限流（复用 `sync_budget`）+ Free 层 fail-closed 兜底」替代手填口令；`GET` 仍要 `X-NH80-Key`。
- **账单/法律**：不新增任何付费产品、不升级套餐；超额只报错拒绝、不自动扣费；数据为自建自产、无第三方受限内容 → 额外扣费风险与法律风险均为零。
- **权威不打架**：云端 = 自报快照（agent 只读、生成复习建议）；本机 SQLite = 唯一权威完成（`cmd_finish_day`）；不回写、不信客户端 `correct`。
