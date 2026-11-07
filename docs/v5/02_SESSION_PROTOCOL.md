# 会话协议：文件即接口，任何 agent 都能接手

## 1. 为什么不用「父子会话」

WorkBuddy 目前没有跨会话的上下文继承，也没有「子会话向父会话发消息」的通道。硬造一个只会在换 agent 时崩掉。

v5 的做法：**把编排放在文件系统里**。

- 文件是唯一跨会话、跨 agent、跨天的接口。
- 数值状态在 `state.db`（机器权威），意图状态在 `STATE.md`（人和 agent 都能读）。
- 任何能读文件、能跑 `python3 scripts/nh80.py` 的 agent（WorkBuddy、Claude Code、Codex、Cursor、甚至 cron + API）都能当主会话或每日会话。

## 2. 目录结构

```
nihongo-80/
├── STATE.md                      # 唯一入口，脚本生成，只读
├── plan/
│   ├── 150-day.md                # 总计划（阶段、里程碑）
│   └── week-03.md                # 周计划（主会话写，子会话读）
├── days/
│   └── day-061/
│       ├── brief.md              # 当天任务书（脚本生成）
│       ├── report.md             # 当天日报（子会话写）
│       └── notes.md              # 学生自己的笔记（可选）
├── tasks/
│   ├── open/
│   │   ├── day-061-tutor.md      # 待领取
│   │   └── week-04-plan.md
│   ├── claimed/                  # 已被领取（带 owner）
│   └── done/
├── inbox/
│   ├── to-main.md                # 子会话 → 主会话（追加写）
│   └── to-tutor.md               # 主会话 → 子会话（每次覆盖）
├── students/
│   └── profile.md                # 学习者画像（朝鲜语母语、假名弱项、偏好）
├── sessions/
│   └── day-061-brief.md          # v4 已有，保留给 CLI 输出
└── data/state.db                 # 唯一数值真源
```

## 3. STATE.md 模板

由 `nh80 state --write` 生成，**不要手改**。

```markdown
# 学习状态

- 更新：2026-11-07T11:40+08:00（nh80 state 生成）
- 当前：Day 61 / 150（P3 N3 前半）
- 今日：days/day-061/brief.md ｜ 42 分钟 ｜ 听力日
- 本周目标：～うちに / ～最中に 能各造 3 句；に/で 错率降到 10% 以下
- 昨日：正确率 78%（32/41）｜新词 16｜复习 63 张｜未完成：句子 2 句
- 卡点 Top3：1) に/で 2) てある 3) 即時応答
- 待主会话决策：听力材料是否换更慢的一档
- 学生下一步：先打开页面，学完再进会话
```

读取顺序永远是：`STATE.md` → `days/day-NNN/brief.md` → `tasks/open/*.md`。

## 4. 任务卡（跨 agent 的分发单元）

一张卡 = 一个 md 文件，YAML front matter 是机器可读部分。

```markdown
---
id: day-061-tutor
role: tutor                 # planner | tutor | reviewer
day: 61
owner: null                 # workbuddy | claude-code | codex | human
status: open                # open | claimed | done | blocked
depends_on: [day-060-report]
inputs:
  - STATE.md
  - days/day-061/brief.md
  - data/state.db
outputs:
  - days/day-061/report.md
acceptance:
  - 6 块全部完成或明确记录未完成原因
  - 报告含「摘要」段，≤5 行
created_at: 2026-11-07T08:00:00+08:00
claimed_at: null
done_at: null
---

## 今日任务

按 `brief.md` 教 Day 61；先发页面链接，等学生看完再答疑。
重点：～うちに 的「状态变化前」语感；学生容易和 ～間に 混。

## 禁止

- 不改 `plan/`、不改 `STATE.md`、不改 seeds。
- 不把答案写进 `brief.md`。
```

### CLI

```bash
nh80 task list                      # 列 open/claimed
nh80 task new --role tutor --day 61 # 生成 day-061-tutor.md
nh80 task claim day-061-tutor --owner claude-code
nh80 task done  day-061-tutor --owner claude-code
nh80 task block day-061-tutor --reason "缺少听力音频"
```

`claim` 用 `O_CREAT|O_EXCL` 建 `.lock`，12 小时内重复领取直接拒绝，避免两个 agent 同时教一天。

## 5. 主会话（每周 1 次，30 分钟）

职责：**只做规划、诊断、调难度，不教课**。

1. 读 `STATE.md`。
2. 读过去 7 天的 `report.md`，**只读「摘要」段**（控制上下文）。
3. 跑 `nh80 report --week` 拿真实数值（正确率、到期量、错题分布）。
4. 做三个判断：
   - 进度：落后 / 正常 / 超前 → 调整下周新词数与语法条数。
   - 卡点：连续 3 天同一错因 → 下周插一个 15 分钟专项。
   - 复习债：到期积压 > 120 张 → 下周设 1 个「只复习」日。
5. 写 `plan/week-NN.md`（目标、每天主题、专项、周末测）。
6. 生成 7 张 tutor 任务卡（`nh80 task new`）。
7. 写 `inbox/to-tutor.md`（本周注意事项，每次覆盖）。
8. 跑 `nh80 state --write` 刷新 `STATE.md`。
9. 清空 `inbox/to-main.md`（已读的移进 `archive/`）。

## 6. 每日会话（每天 60 分钟，其中会话 18 分钟）

1. 读 `STATE.md` + `days/day-061/brief.md` + 任务卡。
2. **先发页面链接**，等学生看完（不要一上来就讲课）。
3. 答疑：只回答学生问的，不主动复述页面。
4. 考核：
   - 复习抽查 3 个旧词（造句，不是认读）。
   - 语法：让学生用今天句型造 2 句，现场改。
   - 听力日：放音频，问 2 个细节题。
5. 批改网页上的 10 句翻译（逐句，指出错因类型）。
6. 写 `days/day-061/report.md`（模板见下）。
7. 跑 `nh80 finish-day 61`（写库、算完成度）。
8. 跑 `nh80 task done day-061-tutor`。

### report.md 模板

```markdown
# Day 061 日报

## 摘要（≤5 行，主会话只读这段）
- 完成：6/6 块｜练习 4/6｜复习 63 张
- 真正学会：～うちに 能造 3 句，2 句正确
- 仍然卡：に/で 混用 3 次；即時応答反应慢
- 明日建议：に/で 加 5 分钟专项

## 教学记录
- 学生问到的 3 个问题 + 回答要点
- 语法讲解里我补充的、页面上没有的内容

## 错题与错因
| 题 | 学生答案 | 正确答案 | 错因 |
|---|---|---|---|

## 句子批改
| # | 学生译文 | 修改 | 错因 |
|---|---|---|---|

## 需要主会话决策
- 无 / 具体问题
```

## 7. 跨 agent 接入

### Claude Code / Codex / Cursor

把下面这段放进它们的项目说明或首条消息：

```
你是 Nihongo 80 的每日 tutor。工作目录：<repo>。
开始前按顺序读：STATE.md → days/day-<N>/brief.md → tasks/open/day-<N>-tutor.md。
先发页面链接，等学生看完再答疑；不要复述页面内容。
结束时写 days/day-<N>/report.md（含「摘要」≤5 行），然后运行：
  python3 scripts/nh80.py finish-day <N>
  python3 scripts/nh80.py task done day-<N>-tutor --owner <你的名字>
不要修改 plan/、STATE.md、knowledge/seeds/。
```

### WorkBuddy

- 主会话：置顶一个会话，每周日让它读 `plan/` 和 `report.md`，按第 5 节流程走。
- 每日会话：每天新建，第一条消息粘 `nh80 brief --day N` 的输出（或直接让它读文件）。
- 定时：automation 每天 07:00 跑 `nh80 daily`，生成 brief + STATE，并把链接发给你。

### 其他

只要能读文件 + 跑 Python 就行。没有 SDK 依赖，没有账号绑定。

## 8. 一致性规则

| 风险 | 规则 |
|---|---|
| 两个 agent 同时教一天 | `task claim` 文件锁，12 小时租约 |
| 计划与状态不一致 | `STATE.md` 由脚本生成；计划改动只写 `plan/`，跑 `nh80 state --write` 刷新 |
| 子会话越权改计划 | brief 与任务卡里明确禁止；CI 校验 `plan/` 只能由 planner 任务改 |
| 日报缺失导致主会话瞎猜 | `nh80 finish-day` 检查 report 是否存在，缺失标 incomplete |
| 上下文太长 | 主会话只读「摘要」，不读全文 |
| 换 agent 丢记忆 | 所有必要信息在 STATE.md + brief.md + report.md，聊天记录不是依赖 |

## 9. 最小可用版本（先跑起来）

第一版只需要 4 个命令和 3 个文件：

- 命令：`nh80 daily`、`nh80 brief --day N`、`nh80 finish-day N`、`nh80 task claim/done`
- 文件：`STATE.md`、`days/day-N/brief.md`、`days/day-N/report.md`

任务卡和 `inbox/` 可以第二阶段再加，不阻塞每天学习。
