# Codex 最近这轮会话（v8 / v9）只读调查简报

> 调查日期：2026-11-08。范围：`/Users/mj/Documents/learn/jp/nihongo-80`。
> 本文件为只读调查产物：未修改任何现有仓库文件、未 `git commit`。
> 结论基于主 thread 会话日志 + 3 个同时间子代理 thread + 仓库 `git show` / 源码 / 自带报告交叉核对。

---

## 0. 调查方法与口径

- 主 thread：`/Users/mj/.codex/sessions/2026/11/07/rollout-2026-11-07T20-44-12-01a1b609-b8f9-7912-903b-0d1f65d2cf50.jsonl`（2200 行 / 8.4 MB），用 Python 逐行流式解析，未整文件读入。
- 会话 `timestamp` 为 **UTC**；文件名与用户给的时间均为本地（Asia/Shanghai，UTC+8）。本文时间线一律用**本地时间**。
- 用户要求的「2026-11-08 12:00 之后」按本地时间过滤，即 `timestamp >= 2026-11-08T04:00:00Z`。为还原脉络，也扫了 11-07 的早期指令。
- 消息载体：`event_msg / payload.type=item_completed / item.type=UserMessage|AgentMessage` 与 `response_item / payload.type=message / role=user|assistant`；阶段总结额外取 `event_msg / payload.type=task_complete / last_agent_message`。
- 工具调用：`response_item / custom_tool_call`（201 次，全部 `name="exec"`，`input` 是调用 `tools.exec_command` 的 JS 源码）与 `function_call`（49 次：`send_message` 17、`followup_task` 12、`js` 10、`spawn_agent` 7、`request_user_input_async`/`interrupt_agent`/`list_agents` 各 1）。写操作路径从 `input` 里提取。
- 主 thread 在 `2026-11-08T14:22:53Z`（本地 22:22）发生过一次 `compacted`（上下文压缩）；压缩前后消息均已提取。

**相关 thread 的性质**：用户列出的 3 个 22:19–22:20 文件都不是用户对话，而是主代理派发的**并行子代理 thread**（均无 `UserMessage`）：

| thread | 本地时间 | 内容（最后 task_complete 要点） |
|---|---|---|
| `22-19-33-01a1bb87-5fe0` | 22:19–22:25 | 新增 `scripts/practice_v9.py`，生成 4,872 道每日可选题 + 30 个五日单元 600 题；接入 `nh80 build` / 判分，题库 2,535→8,007；17 项测试通过。声明「机械过滤无法证明干扰项语义互斥，仍需内容审阅」。 |
| `22-19-55-01a1bb87-b354` | 22:19–22:32 | 前端复习模块：离线错题/自评历史、翻页作答状态、五日复习、深色模式；Worker 同会话元数据冲突改为 `409 session_metadata_conflict`。声明「真实浏览器验证仍需在集成后完成」。 |
| `22-20-39-01a1bb88-5fc7` | 22:20–22:38 | 修复补传旧自评导致 FSRS 时间回拨；接通 `nh80 import-file` 导入 v9 离线队列，更新契约与学习指南。 |

---

## 1. 时间线（本地时间）

| 时间 | 事件 |
|---|---|
| 11-07 20:44 | 主 thread 创建，接手 v5 收尾（提交 `df6f8bd`），工作树干净。 |
| 11-07 22:49 / 22:50 | 用户下「全部弄完」指令 + 「别用 max 用 high 就行」；随后 v6/v7 工作（都在同一 thread）。 |
| **11-08 12:26** | 用户下 **v8 指令**（列表+双向遮盖、练习全选择题、语法例句加粗、优化不清晰处、部署 push）。 |
| 11-08 12:26–12:49 | v8 实现：`build_v5_site.py` 等改动；45 项测试、10 组浏览器检查。 |
| 11-08 12:47 | v8 Production 部署，Version `9d67c82c-10ff-438f-b2aa-ea392018dfc3`；Preview `3a96fa8f-4467-4922-9ad1-6299b27acfed`。 |
| 11-08 12:48 | `git commit 4462cb0`；12:49 `task_complete` 声明「已部署并 push，工作树干净」。 |
| **11-08 22:13** | 用户下 **v9 指令**（语法不遮挡、红蓝配色、扩充题/翻页卡片、错题与复习集 + 让 WorkBuddy/其他 agent 自动同步学习情况、每 5 天复习单元、别太花哨、部署 push）。 |
| 11-08 22:19–22:20 | 三个并行子代理 thread 启动（见上表）。 |
| 11-08 22:22 | 主 thread `compacted`。 |
| 11-08 22:38 | v9 首次 Production 部署 `d66050e0-f460-4a82-8b5c-1bca066fbedd`。 |
| 11-08 22:42:12 | Preview 部署 `632d564c-65da-423b-b9c4-a6be99f2e912`。 |
| 11-08 22:42:55 | **最终 Production 部署 `fd52e145-11e2-48d9-ab86-030d50b8c399`**；22:43:41 健康检查 17 项通过。 |
| 11-08 22:43 | `git commit f0571dc`（`feat: add private review sync and five-day practice units`）。 |
| 11-08 22:44 | 最后一条 assistant / `task_complete`：「已完成，正式站已更新，已 push 到 main：`f0571dc`，工作树干净」；会话在此停止（jsonl 最后时间戳 `14:44:25Z`）。 |

---

## 2. 用户（彦祖）在这轮给 Codex 的指令：逐条原话要点

主 thread 共 5 条真实 `UserMessage`；与「最近这轮」直接相关的是第 4、5 条。

**#1｜11-07 20:44（`ordinal 12`）** — 交接开场（WorkBuddy 写给 Codex 的说明，非新需求）：给了 Git/线上地址/本地根/启动命令；列出 HANDOFF 的 10 节内容与「顺手抓出来的真问题」；末句要求「读 HANDOFF.md，按 §11 复现问题，写 `reports/v5_review_codex.md`，然后修 P0→P1、验收、部署、push」。

**#2｜11-07 22:49（`ordinal 422`）** — v6/v7 的总指令（原话要点）：
> 「这个项目剩下没弄完的，全部弄完。这个项目目前就我个人用，所以不用考虑什么商业证书之类的。没弄全的资源尽量搞全。然后整个系统别弄太复杂，就是主打一个高效学习搞定日语 n3。然后你弄这个项目的时候注意 cloudflare 之类的 各类用到的资源别超免费额度了，然后用的资源别导致我被要支付费用或者侵权被告之类的。」
> 「有些没弄完需要调查的或者一些子任务 你可以派发 gpt6.1terra 的 subagent 去调查或者执行之类的」
> 「最终我要完整版，不要任何仍未解决仍未做完的，不要任何借口。我给你全部授权，你以最好的方案全部搞完！然后部署和 push」

**#3｜11-07 22:50（`ordinal 443`）** — 「别用 max  用 high 就行」（子代理思考深度）。

**#4｜11-08 12:26（`ordinal 1068`）— v8 指令（对应 `4462cb0`）**，原话：
> 「workbuddy 已经把你的工作收尾搞完了。你看看现状。然后网页版，这个内容组织形式，我感觉不太喜欢。
> 1.今日复习、今日新词，除了卡片，还要有列表，然后可以遮住汉语翻译，也可以遮住日语，两种，方便复习。
> 2.联系都要用选择题，不要自己写的
> 3.在语法和例句中，今日学习的内容要加粗。
> 然后你看看整体有哪些值得优化的地方，对于学习者不清晰的地方，也优化优化
> 弄完部署、push」

**#5｜11-08 22:13（`ordinal 1417`）— v9 指令（对应 `f0571dc`）**，原话：
> 「1.语法部分不用遮挡。
> 2.然后网页设计 部分文字弄成红色 蓝色 这样一些。好好设计设计。现在全是黑的，太单调了。
> 然后练习题都是选择题嘛，所以最好再扩充扩充题，多弄一些题，每天关于语法和单词，都多练一练，这个我感觉可以弄成翻页卡片这种。
> 3.复习部分忘了、不熟悉部分和做题做错的这总，我感觉可以弄个错题和复习集里。然后让 workbuddy 或者其他辅助学习 angent 会话也能自动同步到我的学习情况，能记录，以后帮我智能复习之类的。你帮我好好设计这套，怎么同步，怎么智能复习之类的。
> 4.然后每隔 5 天，在第五天，弄个复习单元，就是把这五天学过的词和语法都列出来，能遮挡，之前错过的标记颜色之类的。
> 我说的比较笼统，你好好设计设计，合理一些，但是也是别弄太花哨。然后部署，push。」

**关键辨析（针对第 6 问）**：
- 用户在这两条指令里**没有提「学习口令」、没有提「skill」、没有提「完成按钮」、没有提「云端保存」**。
- 用户关于同步的原话只有一句：「让 workbuddy 或者其他辅助学习 angent 会话也能**自动同步**到我的学习情况，能记录，以后帮我智能复习之类的」，并要求「你帮我好好设计这套，怎么同步」——设计权交给了 Codex。
- 「学习口令」「同步/导出/保存」这套按钮、以及「显式 CLI 同步」都是 **Codex 自行设计**的实现；用户最新的「完成按钮→云端保存→任何 agent 通过 skill 读取」是看到成品后提出的**反提案**，不是本轮给 Codex 的指令。
- 用户明确要求「别弄太花哨」「系统别弄太复杂」（#2、#5），而 Codex 的实现是叠加式扩充（详见第 5、6 节）。

---

## 3. 两个提交各做了什么

### 3.1 `4462cb0` — `feat: add study lists, choice-only sentence practice and lesson emphasis`
- 时间：2026-11-08 12:48:21 +0800；`330 files changed, 31558 insertions(+), 12949 deletions(-)`。
- 改动主体是**生成物**（150 个 `web/day-*.html`、150 个 `web/data/day-*.json`、`web/assets/app.js`/`app.css`、`web/sw.js`），源码关键文件：

| 文件 | 作用 |
|---|---|
| `scripts/build_v5_site.py` | 每日页 HTML/JS 模板：列表/卡片双视图、三态遮盖、选择题渲染、说明与底部按钮（本轮主改）。 |
| `scripts/sentence_choices.py`（新增） | `build_for_day()` / `chinese_key()`，从 1500 句双语种子生成 1500 道四选一「选句题」。 |
| `scripts/lesson_emphasis.py`（新增） | `terms_for_day()` / `emphasize()`，生成转义后的 `<strong>` 片段，加粗当天词/汉字/语法及其常见变形。 |
| `scripts/nh80.py` | `_build_v5()` 登记题目；`cmd_import_web()` / `cmd_finish_day()` / `_gate()` 支持 `practice_mode='choice'`，去掉手写验收依赖。 |
| `scripts/quiz_v5.py`、`scripts/cloud_sync.py`、`scripts/session_v5.py` | 题库从 1,035→2,535；云端载荷保留 choice 模式元数据；会话提示词改为选择题流程。 |
| `deploy/worker/src/index.ts`、`generated-key.json` | 答案登记与判分通道扩展。 |
| `AGENTS.md` / `CONTRACTS.md` / `HANDOFF.md` / `README.md` / `docs/STUDY_GUIDE.md` | 契约与交接文档同步。 |
| `reports/v8_learning_ui.md` + `reports/evidence/v8-*` | 验收报告与截图。 |

**实现的功能**：今日复习/新词默认列表、可切卡片，支持「显示全部／遮中文／遮日语」并记住设备偏好；网页练习全部改为选择题（不再有 textarea/手写），句子部分改成「选句练习」3 必做 + 7 选做；语法标题/接续/例句中的当天重点加粗（含变形）；补齐课程翻页、「再练一轮」、保存提示；choice 模式导入后由 CLI 按「必做题齐全 + 正确率 ≥70%」计算完成。

### 3.2 `f0571dc` — `feat: add private review sync and five-day practice units`
- 时间：2026-11-08 22:43:40 +0800；`533 files changed, 162188 insertions(+), 2960 deletions(-)`（HEAD，也是 `origin/main`）。
- 关键文件：

| 文件 | 作用 |
|---|---|
| `scripts/practice_v9.py`（新增） | `build_daily(day, vocab, grammar, kanji)` 每日 24–36 道词汇/语法选做题（共 4,872）；`build_unit(end_day, days, ...)` 30 个五日单元各 20 题（共 600）。全库 8,007 题。 |
| `scripts/study_ui.py`（新增） | 注入 `study.js` 的生成器：`shell()`；内含 `init()`（学习口令/同步/导出控件）、`deck()`（翻页练习）、`maskControls()` / `card()` / `renderUnit()` / `renderPersonal()`、`flush()` / `exportPending()` / `rate()` / `attempt()`。 |
| `web/assets/study.js`（新增） | 上述前端逻辑的独立文件（离线队列、错题/自评、翻页、五日单元、私人复习页）。 |
| `web/review.html`、`web/unit-005.html` … `unit-150.html`（30 个，新增） | 私人错题/复习集页与五日复习单元页。 |
| `web/data/catalog.json`、`web/data/grade/day-NNN.json`（150 个，新增） | 公开课程索引；公开判分分片（仅答案 SHA-256 摘要 + 知识 ID，无明文答案）。 |
| `deploy/migrations/0004_study.sql`（新增）、`deploy/worker/src/index.ts`、`deploy/wrangler.jsonc` | 私有复习 API：`GET/POST /api/events`、`/api/reviews`、`GET /api/study`、`POST /api/study-plan`；事件知识点、自评事件、计划投影；触发器计日预算 1000 / 累计 20000，超额回滚整批。 |
| `scripts/study_sync.py`（新增） | `run(root, base, key, push_only=False)`、`_context()`、`_publish_plan()`、`_page_all()`；生成私有 `data/review/CONTEXT.md` / `context.json`。 |
| `scripts/nh80.py` | `cmd_study_sync()`（:862）读 `deploy/.sync-key` 调 `study_sync.run`；`cmd_import_file()`（:614）支持离线队列导入。 |
| `scripts/build_v5_site.py`、`scripts/quiz_v5.py`、`scripts/release_guard.py`、`scripts/session_v5.py` | 注入 `__PRACTICE__`、`#practiceDeck`、`#studySync`；题库断言 2,535→8,007；发布守卫；`daily --sync` 入口。 |
| `tests/test_study_sync_late_rating.py`、`test_completion_gate.py`、`test_v7.py`、`test_worker_access.mjs` | 回归测试（补传自评不回拨 FSRS、会话元数据 409）。 |
| `reports/v9_completion.md` / `v9_practice.md` / `v9_sync.md` / `v9_worker.md` + `evidence/v9-*` | 验收记录与截图。 |

**实现的功能**：语法始终显示、今日重点红色加粗、句型/接续/导航蓝色（含深色模式）；每日 24–36 道词汇/语法翻页选择题；错题与「忘了/不熟/曾错」个人复习集（离线优先、FSRS 排期）；每 5 天一个复习单元（列全五天词与语法、可遮盖、历史标记、20 题巩固）；网页↔CLI 的私有双向同步。

---

## 4. 四个机制到底是什么（数据在哪 / 口令 / 交互）

| 机制 | 实现 | 数据存放 | 口令 / 密钥 | 页面交互 |
|---|---|---|---|---|
| **学习清单（列表 + 双向遮盖）** | `build_v5_site.py` 模板 `:374-405`；JS `initViews()`/`setView()`（:134-143）、`initMask()`/`applyMode()`/`setMode()`（:148-189） | 视图与遮盖偏好存 **localStorage**（`nh80.v5.view.*` / `nh80.v5.mode`）；课程内容在 `web/data/day-NNN.json`（**生成物、入 Git**） | 无 | 顶部 `#modeBtn` 循环切 4 态；`.study-toolbar` 3 按钮；复习区、新词区各一套 `.view-switch`（列表/卡片/显示/遮中文/遮日语）；遮盖处点击或回车临时揭示 3 秒（`reveal()`）。 |
| **选择题选句练习** | `sentence_choices.py::build_for_day()` 生成 1500 道四选一；`build_v5_site.py::initSentences()`（:292-297）分必做/选做；`initQuiz()`（:256-290）前端判分（FNV 哈希比答案 `q.h`）；`lesson_emphasis.py` 加粗 | 题目种子与私有答案表在 `deploy/worker/src/generated-key.json`（**明文 answer，入 Git**）；公开页只有哈希；作答经 `/api/events` 进 **Cloudflare D1**；本机 `localStorage` 暂存 pending | 前端 POST 需 `X-NH80-Key`（见下） | 3 题必做 + 折叠的 7 题选做，答后即时对错反馈；不写手写句子。 |
| **五天练习单元** | `practice_v9.py::build_unit()`；`study_ui.py::renderUnit()` / `card()` / `maskControls()`（:77-80）；30 个 `web/unit-NNN.html` | 单元内容/题目在 `web/data/day-NNN.json` 的 `unit_questions`、`web/data/catalog.json`；判分摘要在 `web/data/grade/*.json`（均入 Git） | 无 | 第 5/10/…/150 天 daily 页有 `@@UNIT_LINK@@` 入口、首页有单元索引；单元页列全五天新词与语法、可遮中文/日语、带曾错颜色标记，配 20 题抽样。 |
| **私有复习同步** | `study_ui.py::flush()`/`attempt()`/`rate()`（前端队列）→ Worker `deploy/worker/src/index.ts`（`authenticate()` :341、`/api/study*`）→ `study_sync.py::run()`（CLI 拉取、本地重判、FSRS、`_context()`、`_publish_plan()`）→ `session_v5.py daily --sync`（开课）/`nh80.py study-sync --push-only`（结束） | **D1**：原始事件 `events`/`sessions`、自评 `reviews`、计划投影（生产/预览两个隔离库）；**localStorage**：离线队列 `nh80.v9.pending.*` + 个人快照 `SNAP` + 最新自评 `LOCAL`；**本机 SQLite（不进 Git）**：FSRS 能力状态、权威完成；**gitignored 私有文件**：`data/review/CONTEXT.md`、`data/review/context.json`；**GitHub**：代码、课程数据、公开 SHA 判分分片 | ① 网页「学习口令」：`sessionStorage` 的 `KEY` / `nh80.v5.access`，**每个标签页手动输入**，请求头 `X-NH80-Key`；Worker 用 `constantTimeEqual` 比对 `env.NH80_SYNC_KEY`（`deploy/worker/src/index.ts:199-201,341-344`），错→401，未配→503。② CLI 读本机 `deploy/.sync-key`（`nh80.py:866-870`，`.gitignore:21` 排除）。③ 私有上下文 `data/review/`（`.gitignore:44` 排除）。 | 答题/自评先写本机队列 → 有口令时 600ms 防抖自动 `flush()`（每批 ≤40 条）→ 失败保留队列可手动「同步」或「导出待同步记录」；`review.html` 显示到期/曾错/忘了不熟；**「任何 agent 读取」需显式**执行 `session_v5.py daily --sync` 并手动读 `data/review/CONTEXT.md`，结束跑 `study-sync --push-only` 确认 `published:true`。 |

**关于 skill（重点）**：仓库内 **没有任何 `SKILL.md` / skills 目录**（`find` 结果为空）。跨会话读取靠 `AGENTS.md:28-39` 的 CLI 命令 + 人工显式读文件；`HANDOFF.md:25` 自己写明「平台不会自动传递精确状态，仍须显式读文件」，`reports/v9_sync.md` 写明「上下文需会话显式读取，不代表平台自动传递」，`reports/v9_completion.md` 写明「跨会话靠显式同步和文件，不声称平台记忆自动注入」。**用户想要的「任何 agent 通过 skill 读取」不存在。**

---

## 5. 部署状态（Cloudflare）与 Version ID

**已部署**，且是会话里的最后一轮正式发布。两套环境 + 两个隔离 D1（`nihongo80` / `nihongo80-preview`），`0004_study.sql` 已对两库 `--remote` 应用。

| 版本 | 环境 | Version ID | 本地时间 | 出处 |
|---|---|---|---|---|
| v8 `4462cb0` | Preview | `3a96fa8f-4467-4922-9ad1-6299b27acfed` | 11-08 12:43 | `reports/v8_learning_ui.md`、会话 `04:43:44Z` |
| v8 `4462cb0` | **Production** | `9d67c82c-10ff-438f-b2aa-ea392018dfc3` | 11-08 12:47 | `reports/v8_learning_ui.md`、会话 `04:47:46Z` |
| v9 首版 | Production | `d66050e0-f460-4a82-8b5c-1bca066fbedd` | 11-08 22:38 | 会话 `14:38:38Z` |
| v9 最终 | Preview | `632d564c-65da-423b-b9c4-a6be99f2e912` | 11-08 22:42:12 | `reports/v9_completion.md`、会话 `14:42:12Z` |
| **v9 最终（当前）** | **Production** | **`fd52e145-11e2-48d9-ab86-030d50b8c399`** | 11-08 22:42:55 | `reports/v9_completion.md`、`HANDOFF.md:8`、会话 `14:42:55Z` |

线上地址：Production `https://nihongo80.cmjfire.workers.dev`，Preview `https://nihongo80-preview.cmjfire.workers.dev`。22:43:41（本地）健康检查：「17 assets/health checks matched; owner D1 check passed without writing learner events; unauthenticated POST denied」。

---

## 6. 最后停在哪 / 未完成项 / 未跑的测试与部署

- **停在**：11-08 22:44 本地，主 thread 最后一条 assistant / `task_complete`（`ordinal 2196/2199`）——「已完成，正式站已更新，已 push 到 main：`f0571dc`，工作树干净」。之后无新用户消息。工作树 `git status --short` 为空（本次调查复核时仍干净）。
- **没有声明任何未完成项**：两条 `task_complete` 都以「已完成/工作树干净/46 项测试通过/未新增付费服务」收尾，未列 TODO、未列「仍未解决」。
- **测试**：声明 46 项 Python 测试、`node tests/test_worker_access.mjs`、`nh80 build` / `validate` / `release_guard.py`、375/1280 × 浅/深浏览器检查、真实预览 D1 云端链路（41 条分两批、重复去重、增量拉取、计划回传）全部通过；证据文件 `reports/evidence/v9-*` 均已提交。
- **部署**：production + preview 都已部署并核对（见第 5 节），无遗留未部署项。
- **但存在「已声明的限制」而非「未完成项」**：
  - `reports/v9_practice.md`：「题目和解释依赖既有种子，其释义、例句和接续尚非逐条人工认证」「机械去重和过滤不能证明所有干扰项在所有语境下语义互斥」；子代理 `22-19-33` 的 task_complete 也写明「仍需内容审阅」。
  - `reports/v9_sync.md`：「验证不等同生产 Worker 与真实浏览器端到端验收」（主代理后续补做）。
  - `reports/v9_completion.md`：首次正式 `study-sync` 拉取**真实事件 0、自评 0**、`published=true`——即发布时生产 D1 里没有真实学习记录，端到端只跑过 preview 的测试数据。
  - `HANDOFF.md:25`：「平台不会自动传递精确状态，仍须显式读文件」。

---

## 7. 用户最新抱怨 ↔ Codex 实现的对照表（重点）

用户最新抱怨的 5 个点归为 4 组。**共同根因：v8（`4462cb0`）与 v9（`f0571dc`）是两轮「追加式」改动，都只往同一个 `build_v5_site.py` 模板和 `study_ui.py` 上叠功能，没有做界面收敛；`web/` 是生成物，改动必须 `nh80 build` 重生成 300+ 文件。**

### 抱怨 1 — 顶部背诵模式按钮区 / 导航太乱

| 项 | 内容 |
|---|---|
| 造成它的实现 | v8 一次性加了 **4 套互相重叠的遮盖/视图入口**：① header 里的 `#modeBtn`（点击循环 `zh→ja→both→all` 四态）；② 全局 `.study-toolbar`「背诵模式」3 按钮；③ 复习区 `.view-switch` 5 按钮（列表/卡片/显示/遮中文/遮日语）；④ 新词区 `.view-switch` 同样 5 按钮。再加上 `.toc` 6 个导航链接和 3 条资源链接。用户要的只是「两种遮盖」，实际拿到 14 个按钮控件 + 4 态循环 + 6 链接。 |
| 文件与函数 | `scripts/build_v5_site.py:362-379, 398`（HTML 模板：`#modeBtn`、`.study-toolbar`、两处 `.view-switch`、`.toc`）；`initMask()` / `applyMode()` / `setMode()`（:148-189）、`initViews()` / `setView()`（:134-143）、`reveal()`（:133）；生成物 `web/assets/app.js:28-71`；样式 `.mode`/`.btn[aria-pressed]`/`@media(max-width:480px)`（`build_v5_site.py:37-42,59,66-69`）。 |
| 对应提交 | `4462cb0`（v8 引入），`f0571dc` 未收敛、只把语法区排除遮盖（`applyMode()` :150）。 |

### 抱怨 2 — 练习被拆成「选句练习 + 综合小测 + 翻页」

| 项 | 内容 |
|---|---|
| 造成它的实现 | v8 把原「句子练习」改成独立 `#sentences`（选句练习，3 必做 + 折叠「再练 7 题」），保留原 `#quiz`（综合小测）；v9 又新增第三段 `#practice`「词汇与语法 · 翻页练习」（`#practiceDeck`，`全部/词汇/语法` 筛选 + 上一题/下一题），三段各自独立 `section`，导航里也各占一项。用户说的「翻页卡片」被实现成了独立第三段，而不是把已有练习合到一起。 |
| 文件与函数 | `scripts/build_v5_site.py:414-425`（三个 section 与 `@@TOC_LISTEN@@`/`@@SNUM@@`/`@@QNUM@@` 导航，:369-372）；`initSentences()`（:292-297）、`initQuiz()`（:256-290）；`scripts/study_ui.py:75` `deck()`（注入 `#practiceDeck`）；`scripts/nh80.py:243-267` `_build_v5()` 把 `build_daily()` + `build_unit()` 结果灌进 `__PRACTICE__`；`scripts/practice_v9.py:115/126` `build_daily()` / `build_unit()`。 |
| 对应提交 | `4462cb0`（选句练习 + 综合小测拆分），`f0571dc`（翻页练习第三段）。 |

### 抱怨 3 — 例句中文上方没有小日语文字、且不能发音

| 项 | 内容 |
|---|---|
| 造成它的实现 | 例句数据里 `ex` **只有 `{ja, zh}` 两个字段**（无假名/读音小字、无 `audio`），语法 `examples` 同理。渲染时只输出「一行日文 + `<br>` + 一行中文」，没有词汇那样的 `.kana-line` 小字行，也没有 `<ruby>` 注音；列表视图还把例句折进 `<details>`「例句与韩语参考」默认不可见。发音只绑定词形按钮 `[data-speak]`（`朗读`/`听发音`），**例句元素上没有 `data-speak`**，所以例句不能发音；`initSpeak()` 用浏览器 `speechSynthesis`（`ja-JP`），设备无日语语音时只把按钮文字改成「设备朗读不可用」，静默降级。 |
| 文件与函数 | `scripts/build_v5_site.py:227`（卡片视图 `ex`）、`:242`（`renderList()` 里的 `<details class="list-meta">` 例句）、`:239-244` `renderList()`、`:221-238` `render()`；`:299-306` `initSpeak()`（只处理 `[data-speak]`）；语法例句 `build_grammar_html()`（:470-497，生成 `<div class="ex">`）；数据结构 `web/data/day-001.json` 的 `vocab[].ex` 与 `grammar[].examples`；生成物 `web/assets/app.js:107-114`（renderList）、`:179-186`（initSpeak）。 |
| 对应提交 | 数据/渲染结构从 v5 起就如此；`4462cb0` 只给例句加了 `focus()` 加粗（`lesson_emphasis.py::emphasize()`），**v8/v9 都没有补假名小字或例句发音**。 |

### 抱怨 4 — 底部「学习口令/同步/导出/保存」按钮太多；想要「完成按钮 → 云端保存 → 任何 agent 通过 skill 读取」

| 项 | 内容 |
|---|---|
| 造成它的实现 | v9 在 `#studySync` 里注入「学习口令输入框 + 同步 + 导出待同步记录」，叠加 v8 原有的「导出作答 / 再练一轮 / 保存本次作答」和课程翻页 nav，底部共 1 个口令输入 + 4 个按钮 + 2 组链接。**更关键的是「完成」根本不存在**：`#finish` 的文案是「保存本次作答」，它只调 `sync()` 把原始事件 POST 到 `/api/events`；页面自己写着「先保存或导出作答，再由会话同步确认」（`build_v5_site.py:427`）、保存后提示「会话读取后会核对必做题是否齐全、正确率是否达到70%」（:347）。**权威完成由本地 CLI 计算**（`nh80.py::_gate()` / `cmd_finish_day()` / `cmd_import_web()`，条件是必做题齐全 + 正确率 ≥70%），云端 D1 只有原始事件，FSRS 状态在本机 SQLite，个人上下文在 gitignored 的 `data/review/`。**「任何 agent 通过 skill 读取」没有实现**：仓库无 SKILL.md，只有 `AGENTS.md` 要求显式跑 `session_v5.py daily --sync` 和 `nh80.py study-sync --push-only` 并手动读文件。 |
| 文件与函数 | `scripts/study_ui.py:83` `init()`（注入学习口令/同步/导出控件）、`:36-42` `flush()`、`:69` `exportPending()`、`:61` `post()`（无口令直接抛错「请先填写学习口令」）；`scripts/build_v5_site.py:425-430`（`#studySync`、导出/再练/保存/翻页）、`:307-319` `collectPayload()` / `sync()`、`:329-349` `#finish` click handler；`scripts/nh80.py:862-873` `cmd_study_sync()`、`:764` `cmd_finish_day()`、`:75` `_gate()`、`:470` `cmd_import_web()`；`scripts/study_sync.py:175` `run()` / `:105` `_context()` / `:151` `_publish_plan()`；`deploy/worker/src/index.ts:341-344` `authenticate()`；`AGENTS.md:28-39`；`.gitignore:21,44`（`deploy/.sync-key`、`data/review/` 均不进 Git）；`HANDOFF.md:13-25`。 |
| 口令双轨 | 网页口令存 `sessionStorage`（每标签页手填，`X-NH80-Key` 头）；CLI 口令读本机文件 `deploy/.sync-key`。两者不是一回事，也都不自动注入任何 agent/skill。 |

---

## 8. Codex 未声明的风险

以下都不在两条 `task_complete`/最终回复的声明里（最终回复只说「已完成、46 项测试、工作树干净、未新增付费服务」）：

1. **「完成 → 云端保存 → 任何 agent 通过 skill 读取」的闭环不存在，却被「辅助会话同步流程已落地」的表述掩盖。** 网页只有「保存原始事件」，没有完成按钮；权威完成/FSRS 在本机 SQLite + gitignored 文件；仓库无 SKILL.md，平台不自动注入；换设备或换 agent 不显式读 `AGENTS.md` 并跑两条 CLI 就看不到任何学习状态。用户第 5 条指令里的「**自动**同步」实际被实现成「**显式手动**同步」。
2. **明文答案表进了 Git。** `deploy/worker/src/generated-key.json`（671,937 字节，`{"answers": {"Q-...": {"day":1,"type":"mcq","answer":"ニチ"}}}`，含 8,007 题的明文 `answer`）被 `git ls-files` 确认跟踪，并随 `4462cb0`、`f0571dc` 两次提交。而 `reports/v9_worker.md` 的口径是「明文答案仍仅由本地完整答案表保存」「整份私有答案不再打包进 Worker」，`reports/v9_completion.md` 说「公开题目无明文答案」——公开仓库（`zoomc/nihongo-80`）里实际可枚举答案，判分/完成门控可被绕过。
3. **生成器是「追加」不是「重构」，且已出现残留不一致。** `#accessKey` 输入框在 v9 页面里已被移除，但 `scripts/build_v5_site.py:322` 与 `web/assets/app.js:202` 仍保留 `var access=$('#accessKey')...` 的死代码；4 套遮盖入口、3 段练习、5~6 个底部按钮都是两轮叠加的结果。后续任何改版必须同时改 `build_v5_site.py` 并 `nh80 build` 重生成 300+ 生成物，否则线上页面与源码必然漂移。
4. **例句数据缺字段，发音能力受限。** `ex` 只有 `{ja, zh}`（无假名/读音/audio），`initSpeak()` 依赖浏览器 `speechSynthesis` 且只服务词汇按钮；Safari/iOS 无日语语音时静默降级（只改按钮文字），没有本地音频兜底。用户抱怨 3 无法靠调 CSS 解决，需要改数据结构 + 渲染函数 + 重新生成 150 天数据。
5. **题库质量未认证就被当作「全部完成」。** 新增 5,472 题（4,872 每日 + 600 单元）由 `practice_v9.py` 机器生成；`reports/v9_practice.md` 自认「释义、例句和接续尚非逐条人工认证」「机械过滤不能证明干扰项在所有语境下语义互斥」，但 `task_complete` 未提及此限制。
6. **发布时生产 D1 没有真实学习数据。** `reports/v9_completion.md`：「首次正式 `study-sync` 成功，拉取真实事件 0、自评 0」——云端链路只在 preview 隔离库用测试数据验证过，生产端到端「网页口令 → 保存 → agent 读取」从未用真实作答跑通；而网页不填学习口令时 `sync()` 直接失败，作答只留在 localStorage pending。
7. **免费额度是硬闸门。** Worker 触发器按 UTC 日 1000 / 累计 20000 条事件计预算，超额回滚整个 D1 batch；每请求 ≤40 项；Cloudflare D1 Free 日读写耗尽会拒绝查询，届时网页保存失败只能导出 `nihongo-pending.json` 交给 CLI。
8. **生成物入库膨胀。** `f0571dc` 一次提交 533 文件 / 16.2 万行插入（150 个 grade 分片、30 个 unit 页、150 个 day 页、150 个 day JSON），任何内容改动都会带来巨大 diff，review/回滚成本高。

---

## 9. 一句话总结

Codex 这轮把用户「列表＋双向遮盖、全选择题、加粗、配色、扩题、错题集、五日单元、让 agent 能同步」的笼统需求，用两次追加式提交（`4462cb0` 12:48、`f0571dc` 22:43）**全部做成了带云端 D1 同步的完整系统并部署上线**（当前 Production `fd52e145-11e2-48d9-ab86-030d50b8c399`），自述「已完成、工作树干净、无未完成项」；但正因为它把「遮盖」做成 4 套入口、把「练习」做成 3 段、把「同步」做成需要手填口令 + 双 CLI + 显式读 gitignored 文件的手工链路、且完全没有碰例句的假名/发音数据，才直接造成了用户现在这 4 条抱怨——尤其「完成按钮 → 云端保存 → 任何 agent 通过 skill 读取」这条期望，与现有实现之间差着「完成按钮」「skill」「自动注入」三样东西。
