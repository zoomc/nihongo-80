# 验收报告：已通过什么、还差什么

生成时间：2026-11-06。所有结论来自**实际运行**，不是文档推断。
复现：**`python3 tests/test_all.py`**（19 项，约 5.9 秒，在独立临时目录执行，不污染真实档案）。
原始演练日志见 `reports/e2e-day1-3.md`。

## 1. 已通过的自动化测试

```
Ran 19 tests in 5.9s — OK
```

| 组 | 测试 | 验证内容 |
|---|---|---|
| A 静态 | `test_01_db_and_fts` | 877 条种子入库、FTS5 表存在、4983 条关系边 |
| | `test_01b_framework_delivery` | v2 框架：分级兑现（P4 N3≥40 / P3 N4≥20）、去模板化（distinct_objectives≥70）、80 天 `can_do`/`focus` 齐全 |
| | `test_02_keyword_relation_semantic` | 关键词命中 食べる、关系检索有结果、语义检索明确 `enabled:false` |
| | `test_03_80_days_complete` | 80 个 day md + 80 个 HTML 均存在且非空、每天 60 分钟、≥5 题 |
| | `test_04_prerequisites_and_no_spoilers` | 先修/超纲/覆盖率 0 错误、评估日历唯一、Day1 诊断 8 题 |
| | `test_05_external_materials_have_no_body` | 外部索引素材不含正文（版权） |
| B 引擎 | `test_01_fsrs_official_and_deterministic` | 官方 21 参数、retention 0.9、fuzzing off、同输入同 due |
| | `test_02_one_correct_is_not_mastered` | 一次答对 `mastered=0`、凑齐条件才 =1、遗忘退回 |
| | `test_03_error_remedy_mapping` | 9 类错误各有不同补救 |
| C 流程 | `test_01_start_day1` ~ `test_10_new_session_prompt` | 见下表 Day 1–3 端到端 |

### 1.1 v2 新增验收项（全部 PASS，19/19）

以下为 v2 相对 v1 新增的验收项，数据来自 `python3 scripts/nh80.py validate`、
`python3 tests/test_all.py` 与 `curriculum/curriculum.json` 实测；方法依据 `research/nh80_framework.md`
（自研 NH80 高频压缩习得法，课程不照抄教材课序）。

| v2 新增验收项 | 真实通过数据 | 命令 / 证据 |
|---|---|---|
| **分级兑现**：N3 集中 P4、N4 集中 P3 引入，不再用 100% 覆盖率掩盖偏科 | `level_delivery = {P1 N5:99, P2 N5:145, P3 N4:111, P4 N3:130}`；P4 N3=130 ≥ 40、P3 N4=111 ≥ 20；5 类覆盖率 100%（260/85/140/332/60 全 used） | `validate` → `level_delivery`；`test_01b_framework_delivery` |
| **去模板化**：场景 / 目标 / 评分 / 完成条件不再 80 天同一套话 | `teaching_design = {distinct_scene:78, distinct_can_do:77, distinct_objectives:80, distinct_rubric:66, distinct_theme:80}` | `validate` → `teaching_design` |
| **Can-do / focus 字段**：每天有可观察任务与能力侧重 | 80/80 天 `can_do` / `focus` / `scene_tag` 齐全 | `test_01b_framework_delivery` 的 `all(d.get("can_do") and d.get("focus"))`；`curriculum.json` |
| **Day 1 不超纲任务**：从零基础起步、不轮到超纲 Can-do | Day 1 `scene_tag=初次见面`、`can_do=用「N は N です」向对方介绍自己并确认对方姓名`、`assessment=diagnostic`、8 道零基础诊断题 | `test_04_prerequisites_and_no_spoilers`；`curriculum.json` `days[0]` |

`validate` 本次：`error_count=0`、`warnings=[]`；`tests/test_all.py`：`Ran 19 tests in 5.9s — OK`
（新增 `test_01b_framework_delivery`，共 19 项）。

## 2. 十条验收标准逐条对照

| # | 标准 | 结果 | 证据 / 命令 |
|---|---|---|---|
| 1 | 根据真实资源构建可检索知识库 | **PASS** | `config/sources.json` 80 条（67 OK / 4 PARTIAL / 1 FAIL / 7 UNVERIFIED）；877 条种子入 SQLite、4983 条关系边，`search`/`relation` 实测命中；`research/source_registry.md` |
| 2 | 能看到全部 80 天详细课程计划 | **PASS** | `curriculum/day-001.md`…`day-080.md` + `curriculum.json` + `roadmap.md` + `coverage_report.md`；`validate` 0 错误、5 类知识点覆盖率 100% |
| 3 | Day 1 可以真正启动互动教学 | **PASS** | `python3 scripts/nh80.py start-day 1` 输出 briefing（主题/场景/8 道诊断题/60 分钟块）；`new_session_prompt.py 1` 输出可粘贴到新建会话的提示词；`web/day-001.html` |
| 4 | 能接受学生回答并批改 | **PASS** | `answer` 客观题自动判分 + 归因；开放题 `--pending` 挂起，AI 用 `grade-open` 按 rubric 补录；`TestC.test_02` |
| 5 | 错误持久化到学习档案 | **PASS** | `mistakes` 表 + `student/mistakes.json` 镜像 + `audit_log`；`TestC.test_03` |
| 6 | 能安排下一次复习 | **PASS** | 官方 FSRS 写 `fsrs_cards.due` + `review_tasks` 补救；`TestC.test_05` |
| 7 | 次日 Agent 能读到上一日记录 | **PASS** | `daily_summary` + `start-day 2` briefing 含 "Day 1 完成" 与旧知识复习池；`new_session_prompt.py` 只读查询 state.db；`TestC.test_04` |
| 8 | 计划能根据成绩调整 | **PASS** | `adjust --day N` 写 `plan_adjustments` + 定向补救任务；明确「只调动态任务，不降测验难度」；`TestC.test_07` |
| 9 | 每周生成真实学习报告 | **PASS** | `report --week 1` 从 attempts/fsrs_cards/knowledge_state 生成；**无数据的第 12 周如实输出「无任何已判分作答」**；`TestC.test_08` |
| 10 | 关闭会话重新打开状态不丢 | **PASS** | 每次 CLI 都是新进程/新连接；两次 `status` 数据一致；`backup`/`restore`/`audit` 可用；`TestC.test_09` |

额外验证：网页回传码 `NH80R1.*` 导入**幂等**（重复导入被跳过）、未知题目 id 被拒绝、
开放题网页自评被挂起等 AI 判定（`TestC.test_06`）。

## 3. 人工验收流程（可直接复制）

```bash
cd /Users/mj/Documents/learn/jp/nihongo-80

# 0) 空环境从头构建
python3 scripts/nh80.py init                 # 期望 validation=true, errors=0
python3 scripts/nh80.py validate            # 期望 error_count=0
python3 scripts/nh80.py status              # 期望 knowledge_total=485, attempts=0

# 1) Day 1 真实启动（把输出整段贴进新建 WorkBuddy 会话）
python3 scripts/nh80.py start-day 1
python3 scripts/new_session_prompt.py 1

# 2) 打开当天页面（PC 或手机同一局域网）
python3 -m http.server 8080 -d web          # http://localhost:8080/day-001.html

# 3) 在会话里让学生作答，把结果写回
python3 scripts/nh80.py answer --day 1 --q Q0181 --answer "は"
python3 scripts/nh80.py answer --day 1 --q Q0182 --answer "だ" --error-type particle
python3 scripts/nh80.py grade-open --q Q0187 --correct 1

# 4) 网页练习后，复制 NH80R1 回传码导入
python3 scripts/nh80.py import-web-result 'NH80R1.<粘贴>'

# 5) 收尾 + 次日 + 周报 + 备份
python3 scripts/nh80.py finish-day 1 --minutes 58
python3 scripts/nh80.py start-day 2          # 检查含「上一日总结」
python3 scripts/nh80.py adjust --day 7
python3 scripts/nh80.py report --week 1
python3 scripts/nh80.py backup

# 6) 全量回归
python3 tests/test_all.py
```

Cloudflare 上线（**已实际执行，2026-11-06**）：

```bash
cd deploy && npm install --no-audit --no-fund
cd .. && CI=1 bash scripts/deploy_cloudflare.sh preview
      CI=1 bash scripts/deploy_cloudflare.sh production
# 线上：https://nihongo80.cmjfire.workers.dev
```

## 4. 本次开发实际修掉的真实缺陷（记录，不掩饰）

| # | 缺陷 | 修复 |
|---|---|---|
| 1 | `grammar` 表 12 列却写了 13 个占位符，init 失败 | 对齐列数 |
| 2 | 测试用 `--root` 时去临时目录找 `build_site.py` | 代码从脚本自身目录定位，数据才在 `--root` |
| 3 | `_fsrs_review` 把 `sqlite3.Row` 传给 `int()` 导致答错即崩 | 改为按列名取 reps/lapses |
| 4 | `relation` 模式丢掉查询种子，结构化检索恒为空 | seeds 合并 query + keyword 结果 |
| 5 | 周报用累计数据判断「本周有无学习」，空周被写成有数据 | 改按周窗口统计 |
| 6 | 前 5 天只有 1–2 道题，且素材全是「仅索引」外部页无正文 | 素材按 level 分级选原创正文；补 32 道零基础题；加「每天≥5 题」强校验 |
| 7 | 种子 `source_ids=["S001"]` 虚构引用 IRODORI | 全部改 `S000`（项目原创整理），外部索引按 URL 映射真实 SID |
| 8 | NHK NEWS WEB EASY 被误标成原创 | 追加独立外部来源 `S079`，标 PARTIAL |
| 9 | 来源合并重复运行会丢来源 / SID 漂移 | 复用已有 `extra:*` 条目，三次运行稳定 80 条 |
| 10 | 自然语言意图查询 FTS 召回为 0 | 加零依赖中文意图别名表，实测 0→3 / 0→8；语义检索仍明确未启用 |
| 11 | 上线后 `/day-NNN.html` 被 Cloudflare 默认 307 到无扩展名路径，影响 SW 预缓存 | `html_handling: "none"` + Worker 转发 `/` → `/index.html`；preview 验证后推 production |

## 5. 剩余限制与未完成事项（如实列出）

1. **Cloudflare 已上线，但用默认 `*.workers.dev` 域名**：未绑定自定义域名；
   重新部署仍依赖本机 wrangler OAuth 登录态（本次用已有登录态完成，未新建 Token）。
   PWA 首次安装需后台预缓存 167 个资源，实测约 15 秒后激活，不阻塞页面使用。
   部署与线上验证细节见 `docs/CLOUDFLARE.md` 第 4 节与本报告第 6 节。
2. **未创建任何定时自动化任务**：每日会话必须人工新建并粘贴提示词。
   平台定时任务不会注入上次结构化状态；CLI 循环任务 3 天过期且不补跑。
3. **80 天课程是程序化组装**（`review_status=generated`），不是 80 篇人工精修教材。
   Day 1–3 经端到端演练验证，Day 1–5 有手写基础题；其余按真实种子可运行但未逐课人工精修。
4. **知识种子未逐条对照 JMdict / KANJIDIC**：14 条标 `needs_review`（v1 为 6 条； chiefly 汉字训读与 N3 语感）；
   `verified` 表示人工整理后自检通过，**不等于权威词典认证**。
5. **语义检索未启用**：精确词形够用，自然语言意图靠可编辑别名表兜底；
   真实缺口与升级触发阈值（连续 ≥10 次真实失败样本）写在 `docs/TECH_DESIGN.md` 第 2 节。
6. **TTS 依赖浏览器**：iOS/Android 首次需手势解锁；Windows 常无日语语音；
   部分 Chromium 走在线合成。一律降级为「假名读音 + 跟读」，不保证发音质量。
7. **无语音识别与口语自动评分**：听力靠听写/选择题，口语产出靠 AI 按 rubric 评价文字。
8. **官方样题未做成完整模拟卷**：JLPT 官方 N3 样题只作题型与能力对齐、只存索引；
   完整模拟考试为可选时段，当前题库全部为原创模拟题。
9. **分数口径**：本地正确率是过程性指标，**不是** JLPT 标准分，不预测真实考试成绩。
10. **可理解输入只做选材启发式**（生词率 5–10% / level 分级），不宣称验证 Krashen 的 i+1 理论。
11. **Erin 主站访问失败、NHK Lesson 主页返回不完整、EDRDG 文档 wiki 已关闭**：
    详见 `research/source_registry.md` 与 `research/platform_capabilities.md` 的未核实清单，均未编造内容。
12. **平台能力未核实项**：桌面端任意 cron、子 Agent 级上下文隔离、记忆的结构化字段 API 等，
    全部按「不可用」处理，不影响本项目（状态不依赖平台）。

---

## 6. 真实浏览器视觉验证（PC + 手机）

用本机 Chrome 无头模式对 `web/day-001.html` 实际渲染并截图检查，不是只看代码。

| 视口 | 方法 | 结果 |
|---|---|---|
| PC 1440×1000 | `--headless --screenshot` | 两列布局（左导航 + 右主区）、60 分钟时间块条、能力目标、三张可视化卡；文字清晰无重叠 |
| 手机 390×844 | Chrome DevTools Protocol `Emulation.setDeviceMetricsOverride`（DPR 2, mobile=true） | `innerWidth=390`、`documentElement.scrollWidth=390`、`body.scrollWidth=390` → **零横向溢出**；语音控件 4 个按钮中的第 4 个正确换行；底部 5 个操作按钮全部可见；单列折叠卡片、字号与触控目标正常 |

排查记录：直接用 `--window-size=390,844` 截出的图看起来「右侧被切」，
经 500px 对照图与 CDP 实测确认是 **headless Chrome 的最小窗口宽度限制导致截图裁剪**，
不是页面缺陷。以 CDP 真实 390 CSS 视口的测量值为准。

TTS 提示在无日语语音环境下显示「已显示假名读音，可手动播放或静音学习」，
即降级路径实际生效（截图可见），符合 `docs/CLOUDFLARE.md` 第 9 章的声明。

截图为临时验证产物，已清理；复现方法见上表。

---

## 7. 线上生产环境验证（2026-11-06 实际部署后）

| 项 | 结果 |
|---|---|
| Production | `https://nihongo80.cmjfire.workers.dev`（Worker `nihongo80`） |
| Preview | `https://nihongo80-preview.cmjfire.workers.dev`（Worker `nihongo80-preview`） |
| 上传资源 | 167 个静态文件，2.83 s |
| `/api/health` / `/health` | 200 `{"status":"ok"}`，部署脚本 health check 通过 |
| `/` | 200（index.html，80 天热力图） |
| `/day-001.html`、`/day-040.html`、`/day-080.html` | 200，**无 307 重定向** |
| `/data/day-001.json`、`/data/day-080.json` | 200，合法 JSON（day=1 / 8 题 / 6 词） |
| `/manifest.webmanifest`、`/sw.js`、`/icon.svg`、`/assets/app.css`、`/assets/app.js` | 200 |
| `/no-such-page` | 404（走 404.html） |
| 线上 PC 浏览器（1440×1000） | 标题正确，`innerWidth=1440 / scrollWidth=1440`，9 个内容区、76 个按钮 |
| 线上手机浏览器（CDP 390 CSS px, DPR2） | `innerWidth=390 / scrollWidth=390 / bodyScrollWidth=390`，`is-narrow` 生效，8 道题卡 |
| 线上答题闭环 | 点「提交答案」→「完成并生成回传码」→ 生成 `NH80R1.*`，解码 `v=1, day=1, source=web`，结构合法 |
| Console / 运行时异常 | **0 条** |
| Service Worker | 注册并完成激活：约 15 s 后 `active: activated`、`controller: true`、缓存 166 个资源；页面使用不依赖它，install 期间的等待不影响学习 |

**上线时修掉的真实缺陷**：首次部署 `/day-NNN.html` 返回 307 → `/day-NNN`
（Cloudflare Assets 默认 `html_handling` 规范化），会让 SW 预缓存与本地路径不一致。
已在 `wrangler.jsonc` 设 `html_handling: "none"`，并在 Worker 里把 `/` 显式转发到 `index.html`；
先在 preview 验证全部路径，再推 production。详见 `docs/CLOUDFLARE.md` 第 4.2 节。

**仍受限**：未绑定自定义域名；`workers.dev` 地址依赖 Cloudflare 免费额度；
线上 TTS 依旧取决于终端浏览器是否有 `ja-JP` 语音（实测无，降级提示正确显示）。
