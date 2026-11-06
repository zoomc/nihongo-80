# Nihongo 80 · 每日独立会话闭环（人工可执行）

> 本手册是**人工操作手册**：每天照第 1 节七步做一遍。
> 配套：`AGENTS.md`（总入口）、`CONTRACTS.md`（数据契约）、`agents/*.md`（角色规则）、
> `scripts/new_session_prompt.py`（生成开场提示词）。

## 0. 前提与诚实声明

- 每天在 **WorkBuddy 新建一个独立会话**做辅助教学，配合 Cloudflare / 本地每日页面（可视化 / 音频 / 练习 / 考试）。
- **平台不把每日结构化教学状态自动从上一日传递到下一日**；子 Agent 默认干净启动；平台记忆无法承载 FSRS 的 `D/S/R/due` 精确数值。
- 因此：**状态唯一真源是项目文件**（`data/state.db`），课程真源是 `curriculum/curriculum.json`，`student/*.json` 是只读镜像。AI 每次会话从文件读、把变更交给 `scripts/nh80.py` 写回。
- **本闭环没有任何一步由平台自动触发**：教学会话、`start-day`、`finish-day`、回传码交回都由人工启动。定时任务只是「到点自动发起一次任务」，不自动续上昨日状态（见第 4 节）。
- **本任务不创建任何自动化任务**；第 4 节只描述配置方法，供用户自行决定是否启用。
- 依据：`CONTRACTS.md` §0 / §10 / §14、`research/platform_capabilities.md` §6。

项目根（ROOT，绝对路径）：`/Users/mj/Documents/learn/jp/nihongo-80`
以下命令均在 ROOT 下执行。

---

## 1. 七步闭环（每天照做）

| 步 | 谁做 | 动作 | 产物 / 验收 |
|---|---|---|---|
| ① | 人工 · 本地终端 | `python3 scripts/nh80.py start-day N` | 初始化当日状态；刷新只读镜像 `student/*.json`；确认无报错 |
| ② | 人工 · 本地终端 | `python3 scripts/new_session_prompt.py N`，复制输出 | 一段开场提示词；若数据源未就绪会带「降级提示」 |
| ③ | 人工 · WorkBuddy | **新建独立会话**，粘贴第 ② 步提示词 | 会话按 `agents/teacher.md` 开始 60 分钟教学 |
| ④ | 人工 · 浏览器（可选） | 打开当天 Cloudflare 页面或本地 `web/day-NNN.html`，做可视化 / 音频 / 练习 / 考试 | 页面生成 `NH80R1.<base64url>` 回传码 |
| ⑤ | 人工 → 会话 | 把回传码原样交回会话，由会话运行 `python3 scripts/nh80.py import-web-result '<回传码>'` | 校验通过、写 `attempts`、触发 FSRS 排期；手写/篡改/重复的码会被拒绝 |
| ⑥ | 人工 → 会话 | `python3 scripts/nh80.py finish-day N` | 当日总结 / 进度 / `audit_log` 落盘 |
| ⑦ | 人工 · 次日 | 次日**新建独立会话**，重跑 ①② | `new_session_prompt.py N+1` 能读到昨日总结、到期复习、最近错题 |

> 第 ④ 步是可选环节：没有页面也能在会话内做文本练习并把结果走第 ⑤ / ⑥ 步写回。
> 第 ⑤ 步的「必须回写」命令与第 ⑥ 步命令，均已包含在 `new_session_prompt.py` 生成的提示词第 7 / 8 节。

### 每步细化与验收

**① start-day N**
- 作用：初始化 / 定位当日状态，产出会话 id（`session-YYYYMMDD-NNN`），刷新 `student/*.json` 只读镜像。
- 验收：命令退出码 0；`student/*.json` 存在且是当日快照。
- 若 `data/state.db` 不存在：先由该脚本创建 / 初始化（本手册不假定它一开始就存在）；不要手工建库。

**② new_session_prompt.py N**
- 只读 `curriculum/curriculum.json`、`student/*.json`、`data/state.db`（不存在则容错）、`sessions/`。
- 输出含：绝对路径清单、当天目标、60 分钟预算、到期复习、最近错题、上一日总结、必须调用的命令、结束时必须回写的命令。
- 若输出带「[降级提示]」：说明 `curriculum.json` 或 `state.db` 未就绪，**不要**把降级提示词当作完整教学依据；先解决依赖再重跑。
- 脚本不创建 `curriculum.json`、不编造数据（课程与种子库由别的任务生成）。

**③ 新建独立会话**
- 必须是**新会话**，不要在同一会话里「继续」昨天；平台不保证跨任务自动注入昨日状态。
- 提示词已写明「先读绝对路径清单」，让会话自己从文件取状态，而不是靠聊天历史 / 平台记忆。

**④ 打开当天页面（可选）**
- **已上线**：`https://nihongo80.cmjfire.workers.dev/day-NNN.html`（`NNN` 换当天三位数字，手机 / PC 直接开）；
  Preview 为 `https://nihongo80-preview.cmjfire.workers.dev/day-NNN.html`。
- 或本地 `web/day-NNN.html` + `web/data/day-NNN.json`（由构建脚本生成，页面不持有状态）。
- 页面 `answer` 只用于本地即时判分；答题结束后页面生成回传码（`CONTRACTS.md` §9 / §10）。

**⑤ 回传码写回**
- 回传码格式：`NH80R1.<base64url(json)>`，payload 含 `v/day/session/ts/results/minutes/source`。
- 命令：`python3 scripts/nh80.py import-web-result '<回传码>'`
- 校验：结构校验 + 未知 `qid` 拒绝 + 按 `session+qid` 幂等去重；触发 FSRS 排期（`CONTRACTS.md` §10 / §13）。
- 验收：命令报告导入条数；重复导入同一码应被拒绝而不是重复计数。

**⑥ finish-day N**
- 作用：把当日总结 / 进度 / `audit_log` 落盘，供次日新会话读取。
- 验收：命令退出码 0；`data/state.db` 有当日 `attempts`，`audit_log` 连续。
- **未执行此步，当日作答不计入可读状态**（平台不会替你保存）。

**⑦ 次日续接**
- 重新执行 ①②；`new_session_prompt.py N+1` 的「上一日总结 / 最近错题 / 到期复习」应从文件读到第 ⑥ 步写入的内容。
- 这就是「跨会话状态传递」的全部实现方式：**文件 + 脚本**，不是平台能力。

---

## 2. 哪些环节只能人工启动（明确清单）

依据 `research/platform_capabilities.md` §6.2：

| 环节 | 原因 |
|---|---|
| 首次创建 / 配置定时任务（填提示词、选工作空间、开「完全访问权限」、先「立即运行」试跑） | 文档给的创建方式全是人工 / 对话发起 |
| 保证本地定时任务可运行：电脑不关机、客户端不退出、登录态有效、授权文件夹已勾选 | 官方列明的中断 / 失败条件 |
| 不使用定时任务时的每日教学会话（本闭环基线） | 无自动触发器 |
| 定时任务失败后的重试 / 调整执行时间 / 补跑 | CLI「不补跑」；桌面端需手动重试 |
| 敏感操作 / 文件写入删除的二次确认 | 默认权限下无人值守会卡在「等待确认」 |
| 记忆的核验与纠错（把模糊记忆改成精确状态） | 官方建议「重要判断前先核验」 |
| FSRS 参数优化、状态文件校验与纠错、平行卷生成、单元解锁判定 | 自定义确定性逻辑，平台无对应自动机制 |
| 云端 / 本地任务来源切换、企业微信推送绑定 | 需人工在编辑窗口配置 |
| 回传码从页面复制并交回会话 | 人工搬运，平台不自动回传 |

**结论**：基线设计 =「人工启动 + 文件持久化」；自动化只是可选加速，不是平台保证。

---

## 3. 哪些环节可选设为 automation（只描述配置方法，不擅自创建）

> 本节仅说明**如果用户想启用**该怎么配。**本任务没有创建任何自动化任务**，也不会替用户开启。

### 3.1 桌面端 WorkBuddy「定时任务」

入口：左侧导航栏「定时任务」→ 新建（手动 / 从任务新建 / 从模版）。

按官方文档能做到最稳妥的配置：

```
来源     = 本地            （不能选云端沙箱：云端沙箱无法访问本机文件，读不到项目状态）
工作空间 = /Users/mj/Documents/learn/jp/nihongo-80
权限     = 完全访问权限    （否则无人值守时敏感操作会停在「等待确认」；开启需再次确认）
重复     = 每天 / 固定时间
提示词第 1 句 = 先读取 AGENTS.md、curriculum/curriculum.json、student/*.json、
                 data/state.db，按 scripts/nh80.py / new_session_prompt.py 的流程生成今日教学；
                 所有状态变更只通过 scripts/nh80.py 写回，不要自己改 JSON / SQLite
创建后   = 人工点「立即运行」试跑一次，确认产物与状态文件符合预期
```

可选：企业微信消息推送（需在编辑窗口绑定）。

### 3.2 CodeBuddy Code CLI 定时任务

- `/loop [间隔] <指令>`、`CronCreate` / `CronList` / `CronDelete`、5 字段 cron 表达式。
- 通过对话创建的任务**默认是会话级，CLI 退出后自动清除**；需在 Web UI 创建 / 编辑时启用「持久化」才写入项目目录、重启后继续生效。

### 3.3 启用后必须接受的限制（官方明示 / 未核实项）

- 本地定时任务：**电脑离线 / 客户端退出会漏跑**；登录失效、连接器未授权、模型排队重试耗尽都会失败。
- 云端沙箱**无法访问本机文件**，所以「定时任务 + 本地状态文件」只能选本地来源。
- 循环任务（CLI）**创建 3 天后自动过期删除、且不补跑**；长周期无人值守不可靠。
- 同一任务同一时刻最多一个排队 / 执行实例；到点后在**会话空闲时**才开始；循环任务有 jitter。
- 「最大执行时长」「系统并发上限」具体数值**文档未给出，未能核实**。
- 定时任务**不自动注入上一次运行的状态 / 产物文件**（文档未提及，按不可用处理）—— 是否续上昨日进度，完全取决于提示词是否显式要求读项目文件。

> 再次强调：定时任务能做的是「到点自动发起一次 Agent 任务」，**不是**「自动把昨天的教学进度续上」。本任务不声称已实现自动调度教学。

---

## 4. 失败 / 关掉会话 / 断网怎么办

| 情况 | 处理 |
|---|---|
| **会话中途关闭 / 崩掉** | 状态只在 `import-web-result` / `finish-day` **成功执行后**才落盘；未落盘的作答不计数。重开一个新会话，从文件读昨日 / 当日已落盘状态，不靠聊天历史续。必要时重跑 `start-day N`；先查 `audit_log` 判断是否已写入，避免重复导入。 |
| **断网** | 本地闭环（①③⑤⑥）不依赖网络；第 ④ 步页面可改用本地 `web/day-NNN.html`。Cloudflare 页面打不开就跳过 ④，用会话内文本练习 + ⑤⑥ 记录。回传码可稍后联网再交回。 |
| **回传码被拒** | 按 `CONTRACTS.md` §10：结构校验 / 未知 `qid` / 重复导入都可能拒绝。重新从页面复制原码，不手改、不拼接；确认 `session` 与当天一致。 |
| **页面 / `web/data/day-NNN.json` 没生成** | 先运行对应构建脚本（以实际 `scripts/nh80.py` / 构建脚本实现为准），或跳过 ④，用会话内练习完成。 |
| **`curriculum.json` 不存在** | `new_session_prompt.py` 会输出降级提示、不编造课程。该文件由别的任务生成；等它就绪后重跑 ②。 |
| **`data/state.db` 不存在 / 表未就绪** | 先跑 `start-day N` 初始化；脚本只读容错，不会崩。不要凭空编造复习队列。 |
| **`student/*.json` 与 db 不一致** | 镜像是只读产物，重新跑 `start-day` / `finish-day` 流程经 `export_state` 刷新；**不要手改镜像**当作状态变更。 |
| **定时任务漏跑 / 失败** | 无补跑机制；手动补做当天七步闭环。检查运行记录、登录态、授权文件夹、电脑是否在线。 |
| **怀疑状态损坏** | 见第 5 节备份恢复；恢复后重新 `start-day N`，再核对 `audit_log` 与 `attempts` 幂等性。 |
| **AI 在会话里想直接改数值** | 拒绝：`AGENTS.md` §2 规定写状态一律经 `scripts/nh80.py`；AI 只输出评分 / 错误类别 / 讲解。 |

---

## 5. 状态如何备份与恢复

### 备份

- 位置：`data/backups/`。
- 时机：建议每天第 ⑥ 步 `finish-day N` 成功后备份一次 `data/state.db`。
- 方式：若 `scripts/nh80.py` 提供备份子命令则用它（以脚本实际实现为准，不要臆造命令字）；否则手动复制，例如
  `cp data/state.db data/backups/state-YYYYMMDD.db`。
- 一并可保留：`student/*.json` 快照、`sessions/` 日志、`reports/` 周报（均为可重建 / 可审计产物）。
- **不能用平台记忆做备份**：记忆是模糊、每晚生成、可能有概括偏差的提示词注入，不承载精确数值。

### 恢复

1. 停止一切写入（不跑 `start-day` / `import-web-result` / `finish-day`）。
2. 从 `data/backups/` 选最近一个完好副本，覆盖回 `data/state.db`。
3. 重新运行 `python3 scripts/nh80.py start-day N`，让 `export_state` 刷新 `student/*.json` 只读镜像。
4. 校验：
   - `audit_log` 是否连续、无断裂；
   - `attempts` 是否按 `session+qid` 幂等（无重复计数）；
   - FSRS 卡能否用 `Card.from_dict()` 正常反序列化；
   - 五阶段 `stage` 与 `mastered` 是否与门控规则一致（由脚本判定）。
5. 用 `python3 scripts/new_session_prompt.py N` 确认开场提示词能读到昨日总结；读不到则不要开新会话教学。

---

## 6. 每日收尾验收清单

- [ ] 第 ① 步 `start-day N` 退出码 0，`student/*.json` 已刷新
- [ ] 第 ② 步提示词无「[降级提示]」（若有，先解决依赖再开始教学）
- [ ] 当日有真实 `attempts` 记录，**不是**「读完页面 / 读完 AI 文本」
- [ ] 第 ⑤ 步：产生的回传码已被 `import-web-result` 接受（或本日无网页练习且已说明）
- [ ] 第 ⑥ 步 `finish-day N` 执行成功，`audit_log` 连续
- [ ] `data/state.db` 已备份到 `data/backups/`
- [ ] 次日 `new_session_prompt.py N+1` 能读到昨日总结 / 到期复习 / 最近错题
- [ ] 全程未手改 `student/*.json`、未直接改 `data/state.db`、未降低测试难度
- [ ] 未声称「平台自动传递状态 / 自动调度教学」

---

## 7. 快速命令卡（复制用）

```
# 在 ROOT = /Users/mj/Documents/learn/jp/nihongo-80 下
python3 scripts/nh80.py start-day N
python3 scripts/new_session_prompt.py N          # 复制输出 -> 新建 WorkBuddy 独立会话
# （会话内，网页练习后）
python3 scripts/nh80.py import-web-result '<NH80R1 回传码>'
# （会话结束）
python3 scripts/nh80.py finish-day N
# 次日
python3 scripts/nh80.py start-day N+1
python3 scripts/new_session_prompt.py N+1
```

> `N` 换成实际天数；`import-web-result` 与 `finish-day` 的具体子命令以 `scripts/nh80.py` 实现为准，契约（`CONTRACTS.md` §10 / §14）未列出的命令字不要臆造。

---

## 8. PC / 手机双端路径补充（用户可能在手机上学）

页面已同时适配 PC 与手机，但**状态真源始终在本地 `data/state.db`**，网页不写状态。
因此两种学习路径的差别只在「第 ④ 步怎么做、回传码怎么带回会话」。

| | PC 端 | 手机端 |
|---|---|---|
| 打开页面 | `python3 -m http.server 8080 -d web` → `http://localhost:8080/day-NNN.html` | 手机浏览器打开 Cloudflare 上线后的当天页，或同一局域网访问 PC 的 8080；可「加到主屏」离线打开 |
| 听力 | 浏览器 TTS `ja-JP`，鼠标点播放 | **首次必须手动点一次播放解锁**（iOS/Android 手势限制）；可调 0.7/0.9/1.0 语速 |
| 练习 | 一屏多题（grid） | 一屏一题（step）+ 粘性进度条 + 底部操作栏，触控目标 ≥44px |
| 回传码 | 直接复制粘贴到 WorkBuddy 会话 | 一键复制 / 系统分享 / 下载 `.txt`；**可先存备忘录，稍后到 PC 再导入** |
| 写回 | `import-web-result '<码>'` | 同一命令；手机端不要求当场完成，允许异步 |

**「手机学习 → PC 导入」异步路径**（推荐给通勤场景）：

1. 手机上打开当天页面，做完练习，点「复制回传码」并存到备忘录/发给自己。
2. 页面结果同时存在 `localStorage`，当天可恢复；但它**不是学习状态真源**，也不代表已完成。
3. 回到 PC，在 WorkBuddy 会话或终端执行 `python3 scripts/nh80.py import-web-result '<码>'`。
4. 脚本按 `session+qid` 幂等去重；重复导入同一码不会重复计分。
5. 开放题在网页上的自评**不算掌握依据**，导入后会被挂起，需 `grade-open` 由 AI 按 rubric 判定。
6. 最后照常 `finish-day N`，状态才落盘。

**边界**：离线只做展示 / 练习 / 判分 / 生成回传码；成绩必须经回传码写回 SQLite 才成立。
网页不发任何网络请求，不缓存学习数据。浏览器与 TTS 的已知限制见 `docs/CLOUDFLARE.md` 第 9 章。
