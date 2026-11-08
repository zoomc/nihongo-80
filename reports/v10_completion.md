# v10 完成报告 · 页面只留内容 + 完成按钮进度链路

日期：2026-11-08。用户要求：先读 Codex 会话与线上页面调查，再按 4 点重构，最后部署并 push。全部完成。

## 1. 调查结论

三路只读调查（报告均已入库）：

| 报告 | 结论 |
|---|---|
| `reports/codex_v8_investigation.md` | Codex 两轮：`4462cb0`（v8 列表/双遮盖/全选择题）、`f0571dc`（v9 翻页题卡/五日单元/私有同步）。用户抱怨的每个元素都能定位到具体函数；并发现 `generated-key.json` 明文答案误入公开仓库、口令双轨、SW 缓存不含 HTML 三项风险 |
| `reports/v8_simplify_plan.md` | 顶部 14 个控件、4 块题目、例句无假名与发音、底部 6 个按钮的精确行号；给出合并题算法与 SW 风险 |
| `reports/v8_progress_sync_plan.md` + `reports/v8_progress_api.md` | 无口令写入 + 密钥读取的鉴权、D1 表、API 契约、skill 落地路径与端到端实测 |

线上 `day-001.html` 与本地逐字节一致，抱怨属实。

## 2. 四项要求逐条落地

### ① 顶部与底部清空

删掉 `header.top`（含 `modeBtn`、分钟数）、`nav.toc`、`.study-toolbar`、提示文案、四个站点外链、`.view-switch`、复习卡片视图、口令输入框、同步/导出/保存/再练/课程翻页/署名行。每日页不再加载 `study.js`。

现在页面只有：极简 `Day 001 · 主题` 标题 + 4 个内容块 + 底部一个「完成」按钮。150 页全量断言杂项为 0。

### ② 练习合成一整块

`merge_questions()`：以 `curriculum.question_ids` 为必做骨架，按 `knowledge_ids` 去重（每点最多 2 题）吸收选句/综合/词法练习，再用 `coverage_question()` 补齐未覆盖的当天新词（**含选学拓展**）与新语法。

| 指标 | 实测 |
|---|---|
| 题量 | 32–47 题/天，平均 43.1 |
| 覆盖 | 150 天全部覆盖 `new_vocab_ids ∪ new_grammar_ids`，缺口 0 |
| 重复 | 每个知识点最多 2 题 |
| 安全 | 恰好 4 选项、`h ∈ oh`、qid 唯一、无 `answer`/`rationale`、无明文答案 |
| 形式 | 一整块直接列出，无翻页、无「选句/综合小测/再练 n 题」分段 |

听力日音频与脚本并入练习块，3 道听力题也在同一块。

### ③ 小日语文字与发音

中文正上方加 `.kana-line` 小假名，日文汉字 `<ruby>` 注音；每条例句独立「朗读例句」按钮（`speechSynthesis`, `ja-JP`），每个词也可朗读。构建期用当天词表最长匹配生成读音提示，文案明确写「读音提示」，不冒充逐字转写。浏览器实测 ruby 18–31 个、发音按钮 16–25 个/页。

### ④ 完成 → 云端 → 任何 agent

- `POST /api/progress`：页面无需口令，写 D1 `study_progress`（`day` 主键幂等覆盖，全表 ≤150 行）。服务端靠 Origin 白名单、64KB 体上限、字段白名单、每 IP/日限流兜底；现有 `/api/events` 等路由一行未动。
- `GET /api/progress?day=N|latest=1`：必须 `X-NH80-Key`；未授权 401。
- 数据为**自报快照**（`self_reported=1`），客户端 `correct` 不重判、不作掌握依据；本机 `data/state.db`（`finish-day`）仍是唯一权威。
- `scripts/progress_read.py`：纯标准库 CLI，`--latest` / `--day N` / `--json`，密钥自动读 `deploy/.sync-key` 且不打印。
- `skills/nh80-progress/SKILL.md`：仓库内 + 项目级 `.workbuddy/skills/` + 用户级 `~/.workbuddy/skills/` 三份；`AGENTS.md` 追加给 Claude Code / Codex 的一句话提示词。

**零扣费 / 零侵权核实**：Workers Free 含 10 个 D1 库、5M 行读/天、10 万行写/天、5GB 存储，超额只报错不自动计费；未新增付费绑定、未升级套餐、未下载转存第三方音频。

## 3. 顺手清掉的历史残留

- `deploy/worker/src/generated-key.json`（8007 题**明文答案**，Codex v9 误入公开仓库）：确认 Worker 只用公开哈希分片 `web/data/grade/day-*.json` 后，移出版本库并 gitignore；本地构建仍生成供测试。
- 学习口令双轨：`study_ui.py` 不再注入口令 UI、不再自动 POST `/api/events`，`flush()` 改纯本地合并。
- `wrangler.jsonc` 之外无新增云资源；D1 两库仍隔离，`release_guard.py` 继续强制校验。
- Service Worker 版本升到 `nh80-v10-*`，HTML 模板纳入 revision 哈希，避免只改模板时用户一直看到旧页面。
- `release_guard.py` 新增合并题契约校验（qid 唯一、4 选项、哈希一致、≤60 题）。

## 4. 验收（全部实跑）

| 项 | 结果 |
|---|---|
| `nh80.py validate` | 150 天 / 2700 词 / 276 语法 / 620 汉字 / 45 听力日 / **0 error** |
| Python 测试 | **59 项全绿**（含新增 13 项 v10 回归） |
| Worker 测试 | `test_worker_access.mjs` PASS；`test_progress_api.mjs` 12 项 ALL PASS（含 413/401/幂等/限流/Origin） |
| `release_guard.py` | `ok:true`，541 文件、48 MB、`paid_features:false`、两库隔离 |
| 浏览器 375 / 1280 | Day 1/47/150：4 块 + 完成按钮；局部遮挡互不干扰（新词遮中文时语法 0 遮挡，反之亦然）；判分正确；完成按钮 POST `/api/progress` 且字段齐全；无横向滚动、无 console 报错、无明文答案 |
| D1 迁移 | `0005_progress.sql` 两库均已应用，`study_progress` 表与索引存在 |

## 5. 部署与推送

| 项 | 值 |
|---|---|
| Production | `https://nihongo80.cmjfire.workers.dev`，Version `ffa3096d-7071-4211-a115-c0c5b6480901` |
| Preview | `https://nihongo80-preview.cmjfire.workers.dev`，Version `ca3eff19-8814-485b-93f4-9a20e085f6c0` |
| 健康检查 | 两环境 `{"status":"ok","features":{"db":true,"sync":true}}` |
| 逐路径 | `/`、Day 1/47/149/150、listening / resources / library / review、音频、grade 分片全 200；`answer-key.json` 404 |
| 字节一致 | `index.html`、Day 1/47/149、`app.js`、`app.css`、`data/day-047.json`、`sw.js` 本地与线上 SHA-256 全部 MATCH |
| 接口 | `GET /api/progress` 无 key → 401，带 key → 200；`/api/events` 旧鉴权不变 |
| 线上 UI | Day 47 杂项关键字 0 个，ruby 24 个 |

**端到端实测**：Chrome 375 打开 production `day-149.html` → 4 个内容块、45 题、34 个 ruby、24 个发音按钮、
无杂项、无横向滚动；点一题判分后点「完成」→ 按钮变「已完成」、状态「学习情况已保存，会话可读取。」
→ `python3 scripts/progress_read.py --day 149 --json` 读回 `day=149 / self_reported=1 / questions=1 / server_ts`
→ `--latest 3` 生成含「错题优先 K0613 + 当天新词/语法」的复习重点。测试数据随后从两库清除
（production `study_progress=0`、preview `study_progress=0`，限流计数归零）。

Git 提交与 push 见仓库 `git log -1`（工作树干净）。

## 6. 仍未做到（不粉饰）

1. 内容仍是 `ai_draft`，无日语/韩语教师逐条人工审校。
2. 每日精听是 Kokoro 合成音，不是真人；真人材料只外链或开放许可音频。
3. 页面「完成」是自报快照，**不等于** `finish-day` 的掌握判定；两套 qid 集合不同，文档已明确区分。
4. 39 道周测/阶段题不是官方模考，不换算 JLPT 分数。
5. 静态音频不支持服务端 Range（修它会把音频请求引入 Worker 额度，实测 0.56–0.62 MB 播放正常，故不引入）。
6. 旧 `/api/events`、`/api/reviews`、`/api/study` 路由保留给历史 CLI，每日页已不再调用；`review.html` 与五日单元页仍只在本机记录。
