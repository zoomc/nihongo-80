# Nihongo 80 · 项目总入口（AGENTS.md）

> ⚠️ **本文件是 v3/v4（80 天）时期的流程，已与当前 v5（150 天）不一致。**
> 现在请**先读根目录 `HANDOFF.md`**（v5 的目录地图、构建链路、已知缺陷、验收标准）。
> 本文件仍适用的只有：§0 状态真源规则、§2 唯一写入通道、§3 禁止事项、§6 角色速查。
> 已过时、**不要照做**的：§4 的 80 天时间块（review 10 / new 20 / interaction 15 / quiz 10 / feedback 5）、
> §5 的回传码流程（v5 网页改为自动上报原始事件）。

任何新会话 / 子 Agent 打开本项目，**先按本文件执行**，再开始任何教学或改文件动作。

项目根（ROOT）：`/Users/mj/Documents/learn/jp/nihongo-80`。
以下路径若无特别说明均相对 ROOT；命令一律在 ROOT 下执行（绝对路径见 `docs/DAILY_SESSION.md` 与 `new_session_prompt.py` 生成的提示词）。

## 0. 先认清一个事实（不可协商）

- 每天在 WorkBuddy 开的是**全新独立会话**；平台**不**把每日结构化教学状态自动从上一日传递到下一日。
- 子 Agent 默认**干净启动**；平台记忆是「模型自动抽取 + 提示词注入 + 每晚批量生成」的模糊背景，**不能**承载 FSRS 的 `D/S/R/due`、掌握门控计数、`error_type` 等精确数值，官方自己也要求「重要判断前先核验」。
- 因此：**状态唯一真源是项目文件**；AI 每次会话**从文件读**、把变更**交给脚本写回**。
- 依据：`CONTRACTS.md` §0 / §14、`research/platform_capabilities.md` §6。
- **禁止宣称**「已实现自动状态传递 / 自动续课 / 自动调度教学」。定时任务的语义只是「到点自动发起一次任务」，是否读到昨日状态完全取决于提示词是否显式要求读文件；文档未承诺自动注入。

## 1. 打开项目后按顺序先读

1. `AGENTS.md`（本文件）
2. `CONTRACTS.md` —— 重点 §0 真源规则、§10 回传码、§11 掌握状态机、§12 错误类型与补救、§13 FSRS、§14 禁止事项
3. `research/learning_science.md` —— §0 统一状态结构、§2 主动回忆、§3 提取练习（一次答对 ≠ 掌握）、§4 交错练习只用于易混语法/助词/变形、§8 掌握阈值
4. `research/platform_capabilities.md` —— §6 设计结论、§6.2 只能人工启动的环节、§6.4 程序/AI 分工
5. 角色文件：`agents/teacher.md`（每日必读）；当天 `assessment != none` 时加读 `agents/examiner.md`；复习环节参照 `agents/reviewer.md`；周度审计/调计划用 `agents/director.md`
6. 当天数据：`curriculum/curriculum.json`（`days[day=N]`）、`student/*.json`、`data/state.db`（只读查询）、`web/data/day-NNN.json`（可选页面数据）
7. `docs/DAILY_SESSION.md`（人工闭环、故障处理、备份恢复）
8. `research/nh80_framework.md`（§3 八条原则 → 可执行实现）—— 课程编排的**方法依据**（课程不照抄任何教材课序）

**v2 每日教学锚定（可执行，方法依据 `research/nh80_framework.md`）**：会话主体必须先读取
`curriculum/curriculum.json` 里当天的 `can_do` / `focus` / `scene_tag`，并以 `can_do` 为当天
**独立输出任务**来组织 60 分钟教学；不得用 80 天共用的模板句替代当天任务。

**v3 每日教学锚定（可执行，依据 `docs/REDESIGN_PLAN.md` §3 / §7 与 `research/textbook_lesson_pattern.md`）**：
每日教学按**页面 8 区块顺序**组织——**先给 3 句当天能用的话**（`lesson_core`），再依次
词 → 语法（中文接续 / 易错 / 韩语对照）→ 例句 / 会话 → 练习（先想后看答案，含示范句）→
今日复习（`review_plan` 具体词表 + 三档自评）；系统信息（能力目标 / 时间块 / 图表 / 编号 /
诊断标签 / 术语）只放页尾，不进正文。页面「今日复习」的**三档自评由程序排期**：
`learning.apply_review_rating` 只改 FSRS 的 `due`，不写 `attempts`、不改 `stage`、不判 `mastered`；
**AI 不得据自评宣称「已掌握」**，掌握仍按 `CONTRACTS.md` §11 门控由脚本判定。

## 2. 状态真源与唯一写入通道

| 内容 | 真源 | 谁能写 |
|---|---|---|
| 知识条目 | `knowledge/seeds/*.jsonl` | 人工编辑（本任务不改） |
| 80 天课程 | `curriculum/curriculum.json` | 生成脚本（本任务不创建） |
| 学习状态（FSRS、`attempts`、`stage`、`error_type`、日志） | `data/state.db`（SQLite） | **仅 `scripts/nh80.py`** |
| `student/*.json` | `export_state` 生成的只读镜像 | 禁止手改后当作状态变更 |
| 每日页面 `web/day-NNN.html` + `web/data/day-NNN.json` | 构建脚本生成 | **不持有状态** |
| 平台记忆 / 聊天上下文 | **不作状态** | 会话可随时关闭 |

**写状态一律经 `python3 scripts/nh80.py ...`（事务 + `audit_log`）。AI 只输出「评分 / 错误类别 / 讲解措辞」，不直接写任何数值，也不直接改 `data/state.db`、`student/*.json`。** 凡要落盘的状态数值，都由脚本写入，保证可审计、可回滚、可跨会话复用。

## 3. 禁止事项（违反即视为断链）

1. 不声称平台自动传递每日状态 / 自动调度教学；跨会话状态只来自文件。
2. 不把「读完页面 / 读完 AI 文本」记为完成；必须有 `attempts` 记录（经 `import-web-result` 写入）。
3. 不因进度落后降低测试难度；只能减内容、补基础、调任务。
4. 不因一次答对判掌握；五阶段与门控全部由脚本算（`CONTRACTS.md` §11）。
5. 不把外部受限教材正文写进仓库；不虚构调研结果，未核实一律标注。
6. 不引入向量数据库；检索用 SQLite FTS5 + 结构化关系。
7. 不手改 `student/*.json` 当作状态变更；不擅自改 `CONTRACTS.md`（任何模块改动前先改契约）。

## 4. 60 分钟预算

每天默认 **60 分钟**，结构来自 `curriculum.json` 的 `blocks`（`blocks[].min` 合计必须等于 `minutes`）：

| 块 | 分钟 | 内容 |
|---|---|---|
| review | 10 | FSRS 到期 + 主动回忆（先答后揭示） |
| new | 20 | 新词汇 / 语法 / 汉字，逐步讲解 + 情境 |
| interaction | 15 | 听 / 说 / 读互动，必须有学生独立输出 |
| quiz | 10 | 测验（先思考再揭示答案） |
| feedback | 5 | 反馈三要素（目标 / 当前 / 下一步）+ 写回 |

可随当天 `assessment` 动态调整，但**一周内听、说、读、写、词汇、语法各项能力都要训练到**；不能因为赶进度砍掉学生产出。同一天若叠加多个测试，合并为一个 `assessment`、总时长不超过 60 分钟（见 `agents/examiner.md`）。

## 5. 每日流程（人工启动，详见 `docs/DAILY_SESSION.md`）

1. 本地：`python3 scripts/nh80.py start-day N`
2. 本地：`python3 scripts/new_session_prompt.py N`，复制输出
3. WorkBuddy **新建独立会话**，粘贴开场提示词
4. （可选）打开当天页面做可视化、音频、练习、考试：
   **https://nihongo80.cmjfire.workers.dev/day-NNN.html**（手机 / PC 均已上线），或本地 `web/day-NNN.html`
5. 把页面回传码 `NH80R1.<...>` 交回会话，由 `python3 scripts/nh80.py import-web-result '<码>'` 写回
6. `python3 scripts/nh80.py finish-day N` 落盘
7. 次日**新会话**重新跑 1–2，从文件读到昨日记录

**没有任何一步由平台自动触发**：教学会话、`start-day`、`finish-day`、回传码交回都是人工。automation 仅可选加速，配置方法见 `docs/DAILY_SESSION.md`；本任务不创建任何自动化任务。

## 6. 角色速查

| 角色 | 文件 | 何时用 |
|---|---|---|
| 教学总监 | `agents/director.md` | 周度审计、维护档案、调 80 天计划、覆盖/难度分析、周报 |
| 每日教师 | `agents/teacher.md` | 每天会话主体（60 分钟教学） |
| 考官 | `agents/examiner.md` | 当天 `assessment != none` |
| 复习官 | `agents/reviewer.md` | 到期队列、五阶段、错误归因、补救 |

## 7. 断链 / 失败速查

- `data/state.db` 不存在或表未就绪：脚本会降级并明确提示；不要编造复习数据，先跑 `start-day N`。
- 会话中途关闭 / 断网：状态只在 `import-web-result` / `finish-day` 成功执行后才落盘；未落盘的作答不计数。重开会话从文件读，不靠聊天历史续。
- 回传码被拒：按 `CONTRACTS.md` §10 校验（结构 / 未知 qid / 重复导入），重新从页面复制，不手改码。
- 状态怀疑损坏：用 `data/backups/` 恢复，恢复后重新 `start-day N`；不靠平台记忆恢复。
