# HANDOFF — 交接给 Codex（v5，2026-11-07）

> 这份文档的目的是：让一个**没有参与过本项目**的 agent，在 10 分钟内搞清楚
> 这是什么、现在在哪、怎么跑、哪些是真做了、哪些是假的，然后独立 review → 修 → 部署 → push。
>
> 文档里的数字都是 2026-11-07 实跑核对过的。凡是我没验证的，会写「未核实」。

---

## 1. 项目是什么

**一句话**：彦祖的私人日语学校。0 基础 → N3，**150 天 × 每天 60 分钟**，网页给资源，AI 会话当家教。

**学习者画像（决定课程设计，不要改）**

- 中文母语，**朝鲜族**，韩语母语级。语法结构（语序、助词、活用、敬语）可正迁移，所以语法不是难点。
- 假名学过一阵，有印象但不熟练 → Day 1 诊断 + 弱项卡，不重学清音。
- 真正的瓶颈是**词汇量 + 句子产出**。课程重心必须在词和造句，不在讲语法。
- 所以每条语法都带 `ko_equiv`（韩语对应形式）和 `ko_diff`（差异），词卡带 `ko_hanja`（朝鲜语汉字音）。

**三个组件的分工（这是产品定义，改之前先确认）**

| 组件 | 负责 | 不负责 |
|---|---|---|
| 网页 `web/day-NNN.html` | 当天的资源包：复习 / 新词 / 语法 / 句子 / 练习；可离线、可打印 | 不教学、不复述、不做仪表盘 |
| 每日会话（任意 agent） | 发链接 → 答疑 → 抽查 → 改句子 → 写日报 | 不重复网页内容、不直接写数据库 |
| 主会话（每周 1–2 次） | 读日报 + 状态 → 调难度 → 写周计划 | 不逐日上课 |

**明确的非目标**：不做 Live2D 式动画、不做社区、不做多用户、不做题库平台。这是单人自用系统。

---

## 2. 仓库与线上

| 项 | 值 |
|---|---|
| Git | `https://github.com/zoomc/nihongo-80.git` |
| 分支 | `main`（HEAD `195baed`，工作树干净） |
| 本地根 | `/Users/mj/Documents/learn/jp/nihongo-80` |
| Production | `https://nihongo80.cmjfire.workers.dev` |
| Preview | `https://nihongo80-preview.cmjfire.workers.dev` |
| 健康检查 | `GET /api/health` → `{"status":"ok","features":{"db":true,"sync":true}}`（实测通过） |
| 运行时 | Python 3（无第三方依赖）、Node/npx（wrangler）、Cloudflare Workers + D1 |
| D1 | 库名 `nihongo80`，id `9845dbf3-a470-4718-b474-b96e7b0e6223`（在 `deploy/wrangler.jsonc`） |
| Secret | `NH80_SYNC_KEY` 已设在 Worker；值只在本机 `deploy/.sync-key`（已 gitignore，**不在仓库里**） |

⚠️ Codex 接手时如果拿不到 Cloudflare 凭据，`wrangler deploy` 会失败。这时**不要伪造部署结果**，把「本地已通过、线上待部署」写清楚交给彦祖。

---

## 3. 五分钟跑起来

```bash
git clone https://github.com/zoomc/nihongo-80.git
cd nihongo-80

# 1) 建库 + 生成 150 天课程 + 生成 150 个页面（约 10–20 秒）
python3 scripts/nh80.py init

# 2) 校验（应为 ok:true, 150 天, 2700/276/620, 45 个听力日）
python3 scripts/nh80.py validate

# 3) 测试（19 项）
python3 -m unittest discover -s tests -p "test_v5.py"

# 4) 本地看页面
python3 -m http.server 8099 -d web
# http://127.0.0.1:8099/day-001.html
```

`data/state.db`、`STATE.md`、`days/`、`tasks/`、`inbox/` 都在 `.gitignore` 里，clone 后是空的，必须跑 `init` 和 `session_v5.py` 才会生成。**这是有意的**：学习状态不入库。

---

## 4. 目录地图

```
nihongo-80/
├── AGENTS.md                 旧版（v3/v4，80 天）agent 总入口 ← 已过时，看 HANDOFF.md
├── CONTRACTS.md              v4 数据契约（ID 规范、真源规则、FSRS 门控）—— 大部分仍适用
├── README.md                 项目说明（开头是 v5 口径）
├── STATE.md                  当前天/卡点/下一步（脚本生成，gitignore）
│
├── knowledge/seeds/          ★ 内容真源，JSONL，人可改
│   ├── vocabulary.jsonl      2700 词
│   ├── grammar.jsonl         276 语法
│   ├── kanji.jsonl           620 汉字
│   ├── sentences.jsonl       1500 句翻译练习（每天 10 句）
│   ├── questions.jsonl       945 题（v4 遗产，v5 网页不直接用，见 §11）
│   └── materials.jsonl       95 篇素材（54 读 + 41 听，audio_kind 全为 tts）
│
├── curriculum/curriculum.json  ★ 150 天课程（生成物，勿手改）
├── scripts/
│   ├── nh80.py               ★ CLI 总入口：init/build/validate/start-day/finish-day/gate/pull-cloud…
│   ├── curriculum_v5.py      ★ 150 天排课（每天新词/语法/汉字/听力日/时间块）
│   ├── build_v5_site.py      ★ 生成 web/（HTML + JSON + CSS + JS 全在这里）
│   ├── session_v5.py         ★ 会话协议：state/brief/report/task/daily
│   ├── core.py               数据库 schema、导入、导出、审计
│   ├── learning.py           FSRS、掌握门控、评分
│   ├── cloud_sync.py         Worker 事件拉取（pull-cloud）
│   ├── deploy_cloudflare.sh  部署脚本（production / preview）
│   ├── prep_v5.py            OpenJLPT → 待翻译骨架（一次性，产物在 data/build/）
│   ├── audit_content.py      内容审计（高危/中危/低危）
│   ├── build_site.py         ⚠️ v4 遗留 3771 行，会生成 80 天旧站，别跑
│   └── curriculum.py         ⚠️ v4 遗留 1484 行，别改
│
├── web/                      ★ 部署产物（生成物，勿手改）
│   ├── day-001.html … day-150.html
│   ├── data/day-NNN.json     页面数据（vocab/grammar/sentences/quiz/review）
│   ├── assets/app.css|app.js ⚠️ 由 build_v5_site.py 写入，直接改会被覆盖
│   ├── index.html            150 天索引
│   └── 404.html
│
├── deploy/
│   ├── wrangler.jsonc        Worker 配置（assets → ../web，D1 绑定）
│   ├── worker/src/index.ts   425 行：静态资源 + /api/health + /api/events（GET/POST）
│   └── migrations/0001_events.sql
│
├── tests/test_v5.py          19 项验收（唯一的测试文件）
├── archive/tests_v4/         v4 的 6 个测试文件，已归档，不跑
├── docs/
│   ├── v5/00_OVERVIEW.md     设计总览
│   ├── v5/01_WEB_DESIGN.md   网页设计（含遮盖、响应式）
│   ├── v5/02_SESSION_PROTOCOL.md  会话协议
│   ├── v5/03_TEACHING_PLAN.md     13 条教学机制
│   ├── v5/04_ROADMAP.md      实施路线
│   └── DAILY_SESSION.md / CLOUDFLARE.md / VALIDATION.md（v3/v4 时期，部分过时）
├── reports/
│   ├── v5_review.md          第一次独立复审（4.4/10，列了 3 个 P0）
│   └── v5_review_after.md    第二次复审（**报告写的是修复前状态**，见 §11 说明）
├── research/                 教材/学习科学/来源登记（不是听力落地清单）
├── plan/ days/ tasks/ inbox/ 会话协议目录（gitignore，运行时生成）
└── config/ student/ sessions/ agents/   v4 遗留的角色与档案
```

---

## 5. 内容规模（实测）

| 类型 | 总数 | 分级 | 备注 |
|---|---|---|---|
| 词汇 | **2700** | N5 673 / N4 614 / N3 1413 | 每天 9–22 个，常规日均 19.7，听力日均 14 |
| 语法 | **276** | N5 64 / N4 86 / N3 126 | 每条含接续、2 例句、易错、`ko_equiv`/`ko_diff` |
| 汉字 | **620** | N5 95 / N4 155 / N3 370 | 含音读/训读/`ko_hanja`/`zh_trap` |
| 句子 | **1500** | 每天 10 句 | 7 中→日 + 3 日→中，全部来自当天新词/语法例句（实测 offday = 0） |
| 题目 | 945 | — | v4 题库；v5 网页**不用**（见 §11-P1-3） |
| 素材 | 95 | 54 读 / 41 听 | **全部 TTS，0 条 `audio_url`，0 条带题目，无 jlpt 字段** |

数据骨架来自 **OpenJLPT（CC-BY-SA-4.0）**，中文释义/翻译/韩语对照由分批 subagent 生成，`review_status` 为 `ai_draft`。页面页脚和 README 都有署名。**没有人工逐条审校**，文档里也不许写成已审校。

已有序列号：`V0001–V2700`、`G0001–G0276`、`K0001–K0620`、`S0001–S1500`、`Q0001–Q0945`、`M0001–M0095`。

---

## 6. 构建链路（唯一入口，别绕）

```
python3 scripts/nh80.py init|build
   └─ curriculum_v5.build()          → 生成 150 天数据
      └─ core.import_curriculum()   → 写入 data/state.db
      └─ build_v5_site.main()       → 写 web/*.html、web/data/*.json、web/assets/*
```

- **不要**单独跑 `scripts/build_site.py`：它是 v4 生成器（80 天、含 n3-mock），会把 `web/` 覆盖成旧站。
- **不要**手改 `web/` 下任何文件：下次 build 全没了。改 `build_v5_site.py` 里的 `CSS` / `JS` 常量。
- **不要**手改 `curriculum/curriculum.json`：改 `curriculum_v5.py` 后重跑。
- `data/build/` 是翻译中间产物（已 gitignore），重跑 `prep_v5.py` 可再生成，但**已合并进 seeds，不需要再跑**。

---

## 7. 网页

### 结构

常规日 5 块（页面实际分钟合计 45）：

| 块 | 分钟 | 内容 |
|---|---|---|
| ① 今日复习 | 12 | 到期项，正面遮中文，三档自评 |
| ② 新词 | 14 | 词卡：词形/假名/🔊/中文/韩语汉字音/例句；底部汉字条 |
| ③ 语法 | 7 | 句型 → 接续 → 例句 → 韩语对照 → 易错 |
| ④ 句子输出 | 6 | 10 句，7 中→日 + 3 日→中，本地草稿 |
| ⑤ 练习 | 6 | 6 题，点选即时判分 |

听力日（Day 47 起，`day % 7 ∈ {1,3,5}`，共 45 天）多一块「⑥ 听力」8 分钟 —— **顺序在练习之后，这是已知缺陷**（见 §11-P0-1）。

### 遮盖背诵（核心交互）

- 全局四态：关 → 中文 → 日语 → 双向（按钮 `#modeBtn`）。
- 单卡四态：全显 → 遮中 → 遮日 → 双向（每卡 `.eye`，`data-mode`）。
- 点模糊块临时揭开 3 秒；偏好存 `localStorage`（`nh80.v5.mode`）。
- 实测四态循环正常（Chrome headless 点击验证）。

### 响应式

- `<640px` 单列；`640–1024` 居中；`>1024` 两栏（左侧目录 + 右侧内容）。
- 375 / 1280 两种宽度实测均无横向滚动。

### 判分与上报

- 题目在 **build 时按当天新词/汉字/语法生成** 6 题，答案只以 FNV-1a 哈希写进页面（`h` / `oh`），页面无明文答案。
- 「今天学完了」时 `POST /api/events`，只发原始作答（`qid/answer/hinted/seconds`），不发 `correct`。
- 判分权威在本地（`state.db`）；云端只存事件。**v5 的合成题号云端无法重判**（无 answer-key），见 §11。

---

## 8. 会话协议（不用父子会话 API）

WorkBuddy 没有「子会话向父会话汇报」的机制，所以用**文件当接口**，任何能读文件 + 跑 Python 的 agent 都能接手。

```
STATE.md                      主会话/每日会话的唯一入口（脚本生成）
plan/week-NN.md               周计划（主会话写）
days/day-NNN/brief.md         当天任务书（脚本生成，不含答案）
days/day-NNN/report.md        当天日报（会话写，摘要 ≤5 行）
tasks/open/day-NNN-tutor.md   任务卡（YAML front matter，可 claim）
tasks/claimed/  tasks/done/
inbox/to-main.md              子会话 → 主会话
```

```bash
python3 scripts/session_v5.py state                      # 刷新 STATE.md
python3 scripts/session_v5.py brief  --day 61 --force    # 生成任务书（必须 --force，见 §11）
python3 scripts/session_v5.py report --day 61 --force    # 生成日报模板
python3 scripts/session_v5.py task new --day 61
python3 scripts/session_v5.py task claim day-061-tutor --owner codex
python3 scripts/session_v5.py task done  day-061-tutor --owner codex
python3 scripts/session_v5.py daily --day 61             # 一键：brief + STATE + 链接
```

每日会话流程：读 `STATE.md` + `brief.md` → **先发页面链接等学生看完** → 答疑 → 抽查 3 个旧词（造句）→ 用今天语法造 2 句 → 逐句改 10 句翻译 → 写 `report.md` → `finish-day` → `task done`。

---

## 9. 部署

```bash
bash scripts/deploy_cloudflare.sh production   # 或 preview
```

脚本会：`nh80 build` → `npm install`（deploy/）→ `wrangler deploy`。首次或换机器需要 `wrangler login`。

D1 migration 已应用（`events` 表 + 2 个索引），**不用重跑**；如果重建库才需要：

```bash
cd deploy && npx wrangler d1 execute nihongo80 --remote --file migrations/0001_events.sql
```

---

## 10. 已完成（有证据，不是文档嘴说的）

| 项 | 证据 |
|---|---|
| 150 天课程覆盖全部内容 | `validate` → `days:150, totals:{v:2700,g:276,k:620}, listening_days:45, errors:0` |
| 每天时间块合计 60 | `validate` 校验 `blocks[].min` 求和（会报错） |
| 无重复排课 | validate 用 set 查重 |
| 语法按先修拓扑排课 | `curriculum_v5.py` 有 `visit()` 拓扑排序 + 同日依赖检查 |
| 150 个页面 + 151 个 JSON + index + 404 | `ls web/*.html | wc -l` = 153 |
| 遮盖四态 | Chrome headless 实测 `#modeBtn` / `.eye` 循环 |
| 移动/PC 响应式 | 375 / 1280 无横向滚动 |
| 练习按当天出题 + 哈希判分 | `web/data/day-NNN.json` 的 `quiz[].h/oh`，无 `answer` 字段 |
| 会话协议可跑 | `session_v5.py state/brief/report/task` 实测；`tasks/` 目录已生成 |
| 19 项测试全绿 | `Ran 19 tests ... OK` |
| 线上可访问 | production 200，`/api/health` db+sync ok |
| Worker 事件接口 | `/api/events` POST 入库、GET 需 `X-NH80-Key`，v4 时期实测通过 |
| 仪表盘已删 | 每日页无 heatmap/radar/时间块明细/回传码面板（`grep` 只在 `404.html` 命中「回传码」） |

---

## 11. 已知问题（这一节最重要，请当成你的 review 起点）

> `reports/v5_review_after.md` 写的是**修复前**的状态：它列的 4 个问题（brief 题号、遮盖二态、6 条内容错误、句子脱节）中，后三个已修，第一个改为「网页内按当天内容生成题目」。**但那份报告本身没更新**，别照抄它的结论。

### P0 — 会直接影响学习效果

**P0-1 听力块是半成品（最严重）**

- 实际内容：1 段 TTS 朗读的 2 句文本（`duration_sec` 约 26 秒），**没有 3 道题**，只有一个「播放（TTS）」按钮 + 折叠脚本。
- 45 个听力日只用了 **32 篇**素材，其中 5 篇各重复 3 次。
- `materials.jsonl` 95 条：`audio_kind` 全是 `tts`，`audio_url` 0 条，带题目 0 条，`jlpt` 字段全为 `null`。
- 页面把听力排在「⑤ 练习」之后，编号「⑥」，与设计（听力是第 ④ 块）不一致。
- 课程 `blocks` 写「1 段 60–90 秒 + 3 题」，与实际的 26 秒 0 题不符。
- 文档写「Day 46 起」，实际第一个听力日是 **Day 47**（`day % 7 ∈ {1,3,5}`）。
- 复现：`python3 -c "import json;print(json.load(open('web/data/day-047.json'))['listening_material'])"`；或看 `web/day-047.html` 的 `#listening`。
- 修的方向：接真音频源（Irodori / JLPT 样题，注意许可）或至少给听力补 3 道题 + 扩到 60–90 秒；淘汰重复素材；把顺序调到语法后、练习前。

**P0-2 每天的主题是 15 个场景轮转，与内容不对齐**

- `theme` 只有 15 种，每 15 天循环一次；因为标题后面拼了语法，看起来 150 条都不同。
- 实例：Day 46 主题「问候与自我介绍」，当天语法是 `あげる / くれる / もらう`；Day 47 主题「家人与朋友」，语法是 `〜てくれる / 〜てもらう`。
- 影响：`can_do`、`scene` 与词汇/语法/句子脱节；会话按 `can_do` 组织时会对不上素材。
- 复现：`python3 -c "import json;c=json.load(open('curriculum/curriculum.json'));print(len({d['theme'].split('｜')[0] for d in c['days']}))"` → 15。
- 修的方向：按语法/词汇聚类重新命名场景，或干脆去掉主题、只留 can-do。

**P0-3 三处时间口径互不一致**

| 来源 | 常规日 | 听力日 |
|---|---|---|
| `docs/v5/01_WEB_DESIGN.md` | 42 分钟 | 42 分钟 |
| `curriculum.json` blocks | 60（含会话 21） | 60（含会话 21） |
| 页面 `<h2>` 分钟 | **45** | **47** |

- `validate` 只校验 curriculum 内部求和 = 60，不校验页面与文档。
- 修的方向：定一个口径（建议：网页 42 + 会话 18 = 60），然后让 build 用同一份数据渲染，测试断言三者一致。

### P1 — 影响体验/维护

**P1-1 brief / report 有缓存，课程改了不刷新**

- `session_v5.py brief()` 里 `if p.exists() and not force: return p`。
- 实测：重建课程后 `daily --day 1` 仍显示「新词 18」，页面是 9；只有 `brief --day 1 --force` 才变 9。
- 修的方向：`daily` 默认 force；或把 curriculum 的 mtime/hash 写进 brief 头部做失效判断。

**P1-2 每日词量与设计不符**

- 设计：常规日 16、听力日 11。
- 实际：常规日均 **19.7**（最少 9、最多 22），听力日 **14**。
- 影响：60 分钟里 14 分钟新词块塞 20 个词，复习量还会随天数上涨，后期必然超时。
- 复现：`python3 -c "import json,statistics;c=json.load(open('curriculum/curriculum.json'));print(statistics.mean([len(d['new_vocab_ids']) for d in c['days']]))"`。

**P1-3 945 道题基本是死数据**

- `build_v5_site.py:507` 读了 `questions`，但之后没有使用；v5 页面用 `build_quiz()` 现场生成 6 题。
- 后果：云端 `/api/events` 没有 v5 合成题号的答案，无法重判，只能当日志。
- 修的方向：要么让页面用题库（需要按天建 question_ids 并校验对齐），要么删掉题库、云端只记事件。**不要两边都留一半**。

**P1-4 韩语对照覆盖不全**

- 语法 276 条：`ko_equiv` / `ko_diff` 全覆盖（已补 96 条旧的）。
- 词汇 2700 条：**1839 条没有 `ko_hanja`**（68%），只有 861 条有。
- 38 条词汇没有例句（页面会空一块）。
- 修的方向：`ko_hanja` 只对漢語词必填，和語词可空但要显式标「无直接对应」；38 条缺例句的优先补。

**P1-5 AI 草稿无人审**

- 全部 `review_status: ai_draft`。第二轮复审抽样发现 6 处硬错误（已修：V0505 例句、V1827 词性、G0071 释义、K0336/K0383/K0597 读音）。
- 2700 条里仍可能有漏网。凡发现就改 seeds + 重跑 build，不要只改页面。
- 诚实要求：README/页面不许把 `ai_draft` 写成「已审校」。

**P1-6 STATE.md 显示「P0 P0」**

- `session_v5.py state()` 里 phase 拼接重复。小 bug，一行改掉。

### P2 — 清理项

- `AGENTS.md` 还是 v3/v4 的 80 天流程（review 10 / new 20 / interaction 15 / quiz 10 / feedback 5），与 v5 的 5 块结构冲突。**新 agent 若照它执行会跑错**（本次已在开头加了指向本文件的提示，但正文仍是旧的）。
- `scripts/build_site.py`（3771 行）+ `scripts/curriculum.py`（1484 行）+ `archive/tests_v4/` 是 v4 遗产，误跑会覆盖 `web/`。
- `docs/` 下 `DAILY_SESSION.md`、`VALIDATION.md`、`REDESIGN_PLAN.md`、`TECH_DESIGN.md` 是 v3/v4 口径（80 天、回传码），与 v5 不一致。
- `web/404.html` 仍提到「回传码」。
- `index.html` 把 150 个链接平铺，没有按阶段/周分组。
- `.gitignore` 里 `data/build/` 重复了两行。
- 听力资源调研**没有落地成果**：`research/` 只有早期来源登记（Irodori / Marugoto / NHK / Erin 的许可判断），没有 v5 的「52–78 段精听从哪来」清单。这一块等于没做。

---

## 12. 建议的接手顺序（review → fix → deploy → push）

### Step 1 独立 review（不改代码）

按 §11 逐条复现，另外自己找：

- 抽 30 条词（跨 N5/N4/N3）：释义是否准确、假名是否匹配、例句中文是否自然、`ko_hanja` 是否乱填。
- 抽 15 条语法：接续对不对、`common_errors[].wrong` 是否**真的不合法**（不许把正确日语判错）、`ko_equiv` 是否合理。
- 抽 10 个汉字：音读/训读、`zh_trap` 是否正确。
- 抽 5 天页面（1/47/100/150）：块是否齐、分钟是否合理、遮盖是否四态、判分是否正确、有无明文答案。
- 跑 `validate` + 19 项测试，确认基线。
- 写 `reports/v5_review_codex.md`，给 PASS/FAIL + 证据（文件:行号、命令输出）。

### Step 2 修（按优先级）

1. **P0-1 听力**：这是最影响学习效果的。至少做到：3 道题 + 60 秒以上 + 不重复素材 + 顺序调对。接真音频要逐源核许可，核不到就保持 TTS 但把「60–90 秒」的文案改成事实。
2. **P0-2 主题/场景**：重新命名或删掉，别让 `can_do` 指向不存在的场景。
3. **P0-3 时间口径**：定一份数据源，三处渲染/校验同一份。
4. **P1-1 brief 刷新**：`daily` 默认 force。
5. **P1-2 词量**：压到设计值（常规 16 / 听力 11），否则 60 分钟站不住。
6. 其余 P1/P2 按你自己判断，能顺手清就清。

### Step 3 验收（必须自己跑，不许只看文档）

```bash
python3 scripts/nh80.py init
python3 scripts/nh80.py validate        # 期望 ok:true, 0 error
python3 -m unittest discover -s tests -p "test_v5.py"   # 期望全绿
```

再起 `http.server` 用 headless Chrome 测 375 和 1280：5/6 块齐全、遮盖四态、判分正确、无横向滚动、无 console error、无明文答案。

新加的断言要写进 `tests/test_v5.py`，别只写在报告里。

### Step 4 部署 + push

```bash
bash scripts/deploy_cloudflare.sh production
curl -fsS https://nihongo80.cmjfire.workers.dev/api/health
curl -s -o /dev/null -w "%{http_code}\n" https://nihongo80.cmjfire.workers.dev/day-047.html
git add -A && git commit && git push origin main
```

**验收标准（缺一不可）**

- [ ] `validate` 0 error，150 天，2700/276/620
- [ ] 19+N 项测试全绿
- [ ] 线上 `/day-001.html`、`/day-047.html`、`/day-150.html` 均 200
- [ ] 页面无明文答案；遮盖四态可用；375/1280 无横向滚动
- [ ] 报告里明确写「哪些没修」，不许把未修的写成已修

---

## 13. 陷阱清单（会浪费你时间的那些）

| 陷阱 | 后果 | 正确做法 |
|---|---|---|
| 直接改 `web/assets/app.js` 或 `web/*.html` | 下次 build 被覆盖 | 改 `build_v5_site.py` 的 `CSS`/`JS` 常量 |
| 跑 `scripts/build_site.py` | `web/` 被覆盖成 80 天 v4 站 | 只用 `nh80.py build` |
| 手改 `curriculum.json` | 下次 build 丢失 | 改 `curriculum_v5.py` |
| 不跑 `init` 就 build | `state.db` 不存在，导出失败 | 先 `nh80.py init` |
| 忘记 `--force` 生成 brief | 任务书与页面不一致 | `brief --day N --force` |
| 以为 `questions.jsonl` 在页面里用 | 找不到对应关系 | v5 页面自造 6 题 |
| 以为云端能重判 v5 答案 | `/api/events` 只有事件 | 本地 `state.db` 才是权威 |
| 以为 `materials` 有真人录音 | 全是 TTS | 页面已标 `tts`，别写「真人录音」 |
| 把 `ai_draft` 写成 `verified` | 违反 `CONTRACTS.md` §2 | 保持 `ai_draft` |
| 提交 `deploy/.sync-key` / `state.db` | 泄密/污染 | 已在 gitignore，别 -f |

---

## 14. 文档索引

| 想知道什么 | 看哪 |
|---|---|
| 为什么这么设计、目标与取舍 | `docs/v5/00_OVERVIEW.md` |
| 网页 5 块、遮盖、响应式 | `docs/v5/01_WEB_DESIGN.md` |
| 会话协议、任务卡格式 | `docs/v5/02_SESSION_PROTOCOL.md` |
| 13 条教学机制（教材怎么抄） | `docs/v5/03_TEACHING_PLAN.md` |
| 分阶段路线 | `docs/v5/04_ROADMAP.md` |
| ID/字段/真源/FSRS 契约 | `CONTRACTS.md` |
| 两轮复审原始报告 | `reports/v5_review.md`、`reports/v5_review_after.md`（后者是修复前状态） |
| 教材与来源登记 | `research/*.md` |
| 部署细节 | `docs/CLOUDFLARE.md`（v4 时期，D1/secret 部分仍适用） |

---

## 15. 给 Codex 的开场提示词（可直接粘）

```
你在 /Users/mj/Documents/learn/jp/nihongo-80，接手一个 150 天日语学习系统（0 基础 → N3）。
先读 HANDOFF.md 全文，再读 docs/v5/00_OVERVIEW.md 和 CONTRACTS.md 的 §0/§2。

规则：
1. 不要相信文档说的“已实现”，一切以代码和实跑为准。
2. 不要改 web/ 下任何文件（生成物）；改 scripts/build_v5_site.py。
3. 不要跑 scripts/build_site.py（v4 遗产，会覆盖站点）。
4. 不要手改 curriculum.json / data/state.db / student/*.json。
5. 学习状态与密钥不入库；不要提交 deploy/.sync-key。
6. 内容保持 review_status: ai_draft，不许标 verified。

任务：
A. 按 HANDOFF.md §11 逐条复现已知问题，另外自己抽查 30 词 / 15 语法 / 10 汉字 / 5 天页面。
B. 写 reports/v5_review_codex.md：PASS/FAIL + 证据（文件:行号、命令输出），按 P0/P1/P2 分级。
C. 按 P0 → P1 修复，每修一项补测试到 tests/test_v5.py。
D. 验收：nh80 validate 0 error；测试全绿；headless Chrome 测 375/1280、遮盖四态、判分、无明文答案。
E. 部署 production 并 curl 验证，然后 commit + push origin main。
F. 最后如实报告：修了什么、没修什么、线上版本号。不许把未修的写成已修。
```

---

_交接人：德华（WorkBuddy）｜2026-11-07 20:40 +08:00_
_基线：`main@195baed`，`validate` 0 error，19 项测试全绿，production 在线_
