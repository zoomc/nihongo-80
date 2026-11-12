---
name: nh80-progress
description: "开始或继续 Nihongo-80 日语课（0 基础→N3，120 天，中文母语/朝鲜族学习者）：新会话第一步跑 `python3 nihongo-80/scripts/today.py`，拿到今天该学 Day N、上次卡点、今日词/语法/汉字与页面链接，再按 TODAY.md 带课；也用于读云端「完成」快照整理复习重点。只要用户提到「开始学日语 / 今天学什么 / 今天开始上课 / 继续上次 / 学到第几天 / 日语学习进度 / 复习建议 / 错题 / 忘了哪些词 / N3 日语课 / nihongo progress」——即使没点名本 skill 也必须用。注意云端进度是学习者自报、非掌握权威，权威完成以本机 SQLite finish-day 为准。"
---

# nh80-progress · 日语学习进度与每日开课

## 何时使用

- **开课型**（最常见）：「开始学日语」「今天学什么」「继续上课」「接着上次」「日语课走起」「Day N 学完了吗」——先跑 `today.py` 定位，再当老师带课。
- **查询型**：「今天学了什么」「学到第几天了」「日语学习进度」「复习建议」「错了哪些词」「忘了哪些词」「nihongo progress」。
- **接续型**：每日家教会话开始前需要拿到当天的复习上下文时。

两类都从下一节「今天该学哪天」开始，不要靠猜、不要问用户学到哪了。

## 最重要的边界（先读，别跳）

- 云端 `study_progress` 是网页「完成」按钮**自报的当天快照**：`questions[].correct` 与 `accuracy` 由客户端自算，服务端不重判、整份标 `self_reported=1`。
- **唯一掌握权威是本机 `data/state.db`**，只经 `python3 scripts/nh80.py finish-day` 写入（事务 + audit_log）。
- agent 只读云端，**永不回写** `sessions` / `fsrs_cards` / `passed`，不调用 `finish-day` 去「确认」云端结果。
- 不得据 `accuracy` 说「已达标 / 已掌握」；自评只排复习优先级，不是客观能力测试。
- 结论一律附「数据来源：云端自报 / 本机权威」与 `server_ts`，并交叉核对 `STATE.md`。

## 密钥怎么读

- 默认：`<repo>/deploy/.sync-key`（gitignore，不入库）。`progress_read.py` 会自动读取，**禁止显示、打印、写入任何输出或报告**。
- 也可 `--key` 或环境变量 `NH80_SYNC_KEY`。
- `GET /api/progress` 必须 `X-NH80-Key`；`POST /api/progress`（页面完成按钮）不需要口令，但带 Origin 白名单、64KB 体量上限、按 day 幂等覆盖与限流。

## 先判断「今天该学哪天」（推荐顺序）

在 `progress_read.py` 之前先跑：

```sh
python3 scripts/today.py            # 在 nihongo-80/ 里跑
python3 nihongo-80/scripts/today.py # 在工作区根 /Users/mj/Documents/learn/jp 里跑
python3 scripts/today.py --offline  # 云端不通时
python3 scripts/today.py --json     # 给程序解析
```

脚本用 `__file__` 定位仓库根，与当前目录无关；`TODAY.md` 始终写在 `nihongo-80/` 下。

它合并本机 `data/state.db` 的 finish-day 与云端 `study_progress`，输出：今天 Day N / 总天数、
已完成天数、上次正确率与卡点、今天必学词与语法、页面链接、会话流程。**这是新会话唯一入口**，
不要靠猜或问用户。云端只是自报快照，权威仍是本机 finish-day；`TODAY.md` 里已写明这一点。

## 跑哪条命令

脚本在 `<repo>/scripts/progress_read.py`（纯标准库，任何能跑 Python 3 的 agent 都能用，不装依赖、不改文件）：

```sh
python3 scripts/progress_read.py --latest          # 最近 7 天（默认）
python3 scripts/progress_read.py --latest 3        # 最近 3 天
python3 scripts/progress_read.py --day 47          # 指定 Day
python3 scripts/progress_read.py --day 47 --json   # 原样 JSON，供程序解析
python3 scripts/progress_read.py --latest --base https://nihongo80-preview.cmjfire.workers.dev
```

- 默认 base：`https://nihongo80.cmjfire.workers.dev`（真实数据在 production）。
- 退出码：`0` 成功 / `2` 参数或密钥缺失 / `3` 网络或 HTTP 错误（401/503，只打印 `reason`，不打印凭据）/ `4` 无数据。
- `--help` 可查看全部参数。

## 输出字段含义

| 字段 | 含义 |
|---|---|
| `day` | 当天编号 1..120；当前课程同日覆盖不追加 |
| `completed_at` | 客户端点「完成」时刻（ISO 8601，截断 40 字符，仅参考） |
| `server_ts` | Worker 收到时刻（UTC ISO 8601），权威时间戳 |
| `accuracy` | 客户端自算 0..1，**仅展示、非权威** |
| `required_ids` / `extra_ids` / `grammar_ids` | 当天必学词 / 拓展词 / 新语法 id |
| `questions[]` | 逐题自报：`qid` / `answer` / `correct` / `hinted` / `revealed` / `seconds`；`correct` 非权威 |
| `self_rating` | `{id: again\|hard\|good}` 自评，只用于排复习优先级 |
| `wrong_summary[]` | 错题摘要 `{qid, knowledge_ids}` |
| `review_summary[]` | 建议复习的 id 列表 |
| `note` | 自由文本备注（≤2000 字符） |
| `self_reported` | 恒为 1：自报快照标记 |
| `v` | 契约版本 1 |

`--json` 输出服务端原样结构：`{"ok":true,"items":[...]}`。

## 把进度转成当天家教会话的复习重点

按优先级组织会话：

1. **错题优先**：`wrong_summary[].knowledge_ids` 去重，加上 `questions[]` 里 `correct=false` / `hinted` / `revealed` 的题，先讲错因与选句错因。
2. **自评 again/hard 优先**：`self_rating` 中值为 `again` / `hard` 的 id 优先复现、口头造句。
3. **当天新词/语法**：`required_ids` + `extra_ids` + `grammar_ids` 做回顾与独立造句。
4. `review_summary` 作为补充队列；`accuracy` 只展示并标注「自报」，不得据此说达标。

## 主会话 / 每日会话文件协议

- `STATE.md`：由 `scripts/session_v5.py state` 生成的只读镜像（勿手改），记录当前 Day、今日页面、Can-do、本日摘要。用它交叉核对云端 `day` 是否对得上，以及 `server_ts` 新鲜度。
- `days/day-NNN/report.md`：当天日报，人工记录、不自动覆盖。复习结论可写这里，但**不得**据此推进完成或判掌握。
- 每日会话开始：`python3 scripts/session_v5.py daily --sync --day N`；页面提交只代表原始作答保存，权威完成由 `python3 scripts/nh80.py finish-day` 计算（必做题完整性 + 70% 正确率门控）。
- 跨会话只能显式读文件；平台记忆不传递精确状态。云端进度只是弱信号，不能替代 `data/state.db`。

## 诚实边界（必须写进任何对外结论）

- 「云端进度为自报快照，非掌握权威；本机 SQLite `finish-day` 才是掌握权威」。
- 不打印、不写入密钥。
- 不引入付费服务；Workers Free 超额只报错不自动扣费。
