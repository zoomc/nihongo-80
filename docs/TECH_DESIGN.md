# 技术设计：Nihongo 80

本文档说明**为什么这样设计**、哪些是实测数据、哪些是明确未做的。数据契约以 `CONTRACTS.md` 为准。

## 1. 总体架构与职责边界

```
┌─ 人可编辑、可审计 ────────────────────────────────┐
│ knowledge/seeds/*.jsonl   1066 条（唯一知识真源）     │
│ curriculum/curriculum.json 80 天（唯一课程真源）      │
│ config/sources.json        80 条来源登记              │
└──────────────────────┬─────────────────────────────┘
                       │ import / build（确定性脚本）
┌──────────────────────▼─────────────────────────────┐
│ data/state.db  SQLite 3.50                          │
│  · 知识表 + FTS5(unicode61 + 字符 bigram)            │
│  · relations 4983 条（词汇→例句→语法→课程→题目…）     │
│  · knowledge_state / fsrs_cards / attempts /         │
│    mistakes / review_tasks / sessions /             │
│    daily_summary / plan_adjustments / audit_log      │
│  · 唯一可写真源；事务 + WAL + 审计哈希                │
└──────┬───────────────────────┬─────────────────────┘
       │                       │
   CLI / 引擎              student/*.json（只读镜像）
   scripts/nh80.py              │
   learning.py (FSRS)      每日独立 WorkBuddy 会话
   curriculum.py                ▲
   report.py                    │ 读 briefing / 写回命令
       │                       │
       └──> web/day-NNN.html ───┘（回传码 NH80R1）
            纯静态、零外部请求、PC/手机双端、PWA
```

> **知识库规模与关系边数（v4 更新口径）**：种子为 **1066 条**（340 词 / 96 语法 / 140 汉字 / 395 题 / 95 素材），
> 关系边随题目与素材增加而增长；具体数字以 `python3 scripts/nh80.py init` 的实测输出为准
> （沿用此前 `SELECT COUNT(*) FROM relations` 实测值，v3 未改动知识规模，不编造新的边数）。
> v3 新增的 `knowledge/ko_analogy.json`（85/85 语法 + 57 词的韩语对照）是**静态教学参考文件**，
> 不入 `state.db`、不产生关系边，仅由 `build_site.py` 按天裁剪后写进页面数据，详见 §12.2。

**硬分工**（依据 `research/learning_science.md` 与 WorkBuddy 技能规范）：

| 交给确定性程序 | 交给 AI |
|---|---|
| 状态读写与原子事务、备份/恢复/审计 | 讲解措辞、真实场景创设 |
| FSRS 的 R/D/S、due 计算（官方 py-fsrs） | 开放式产出评分与错误归因 |
| 客观题判分、答案规范化、计时 | 平行卷、补救教学的**不同讲法** |
| 掌握门控阈值、单元解锁、复习队列构建 | 今天重点讲什么、节奏与难度微调 |
| 课程检索、覆盖度检查、先修拓扑排序 | 学习者偏好等非精确背景 |
| 日志追加、幂等、状态校验 | — |

> 凡写进 `state.db` 的数值一律由脚本写入；AI 只输出「评分 + 错误类别 + 讲解」。
> 这样即使模型判断有偏差，状态仍可审计、可回滚、可跨会话复用。

**编排方法依据（v2）**：80 天的「教什么 / 按什么顺序 / 用什么任务」由 `research/nh80_framework.md`
自研的 **NH80 高频压缩习得法**定义，课程**不照抄任何教材课序**；Irodori / Marugoto / JLPT 官方 /
Tadoku / JMdict 只贡献目标格式、能力标准、题型边界与素材分级原理，不采用线性课序与全量覆盖。
80 学时是压缩冲刺路径，不等于 JLPT 官方 360–500 学时标准，不承诺合格分数。生成器实现与 v2 算法见第 6 节。

## 2. 检索方式实测对比（先比较，再决定不上向量库）

索引：1066 条文档入 FTS5，关系边由导入时实测生成。中文/日文无空格，`unicode61` 会把整句当一个 token，
因此把 `surface/kana/meaning_zh/例句/释义` 等拼成**字符 bigram** 再入索引，任意两字子串可查。

真实运行 `python3 scripts/nh80.py search "<q>" --mode ...` 的召回数（2026-11-06）：

| 查询 | keyword | relation(展开) | 说明 |
|---|---|---|---|
| `食べる` | 9 | 49 | 精确词形，FTS 直接命中，关系图展开到例句/题目/课程 |
| `ありがとうございます` | 4 | 21 | 长词形同样有效 |
| `条件形` | 2 | 12 | 语法主题命中 |
| `怎么表达感谢` | 0 → **3** | 0 → **17** | 自然语言意图：原 FTS 为 0；中文意图别名表兜底后命中 V0007/Q0190/M0012 |
| `日语里怎么婉拒邀请` | 0 → **8** | 0 → **24** | 同上，别名映射到 すみません/断り/誘う |
| `は が 助词` | 0 → **70** | 0 → **41** | 多词查询走别名展开（召回偏宽，需人工筛选） |

**结论与决策**：

1. **关键词检索（FTS5 bigram + LIKE 兜底）**：对精确词形/语法名/ID 查询足够，是教师备课和知识点定位的主路径。
2. **结构化关系检索**：一条 `relations` 边能把「词汇 → 例句 → 语法 → 课程 → 题目 → 错题 → 复习任务」
   串起来，这是向量检索做不到的（向量给不出可审计的先修链）。
3. **语义检索：当前明确不启用**。`--mode semantic` 返回 `enabled:false` 与理由，不会假装可用。
   - 真实缺口已识别：自然语言意图查询在纯 FTS 下召回 0。
   - 但当前用法是「AI 按课程 ID 取内容」，**没有真实发生的自由文本检索失败样本**；
     上向量库会引入嵌入模型/索引依赖、不可审计性与额外成本。
   - 已用**零依赖的结构化中文意图别名表**（`core.INTENT_ALIASES`，可审计、可编辑）补上主要缺口，
     实测把上述两类查询从 0 提到 3–8 条命中。
   - **升级触发条件（写死，不靠感觉）**：当每日教师需要按语义找素材/题目，
     且 `keyword + relation + alias` 连续 ≥10 次真实查询失败，
     或别名表覆盖率 < 60% 时，再评估轻量嵌入 + SQLite 向量扩展；
     评估前必须保留这 10 条失败样本作为证据。

## 3. 复习引擎（不自造公式）

- 使用 `scripts/vendor/fsrs` = **官方 py-fsrs 6.3.1（MIT）**，`pip install --no-deps` vendor 进项目，
  连同 `typing_extensions` 共 564K，纯标准库可运行。
- 默认 21 个参数、`desired_retention=0.9`；`enable_fuzzing=False` 保证可复现、可测试。
- rating 映射：答错 `Again(1)`；提示下答对 `Hard(2)`；独立答对 `Good(3)`；达到 transfer 阶段 `Easy(4)`。
  忘记**必须** Again，不能记 Hard（官方明确）。
- 卡片状态用官方 `Card.to_dict()/from_dict()` 序列化存 `fsrs_cards.card_json`；时间一律 UTC aware datetime。
- 测试验证：同输入 + 固定时间 → 相同 `due`（`TestBEngine.test_01`）。

**FSRS 只是记忆调度器，不是知识追踪模型**。知识掌握另由显式五阶段门控判定（可解释、可审计），
不引入 DKT（黑盒、稀疏数据退化）或 BKT（假设技能独立）。依据 `research/learning_science.md`。

## 4. 掌握状态机：一次答对不算掌握

`unseen → initial_understanding → hinted_recall → independent_recall → delayed_recall → transfer`

| 条件 | 规则（全部脚本判定） |
|---|---|
| 首次暴露 | 最多到 `initial_understanding`，不看对错 |
| 提示下答对 | `hinted_recall` |
| 无提示答对 | `independent_recall` |
| 距首次 ≥2 天且无提示答对 | `delayed_recall`，`delayed_count++` |
| `delayed_count≥3` + 语境数≥2 + 跨度≥7 天 | `transfer` |
| `mastered=1` | `stage==transfer` **且** 最近 10 次正确率 ≥0.85 |
| 遗忘类错误 / 连续 2 次错误 | 退回 `hinted_recall`，`mastered=0`，强制补救 |

0.85 取 Bloom/Guskey 常用建议区间 0.80–0.90（`research/learning_science.md` 已核实为建议值，**不是**官方规定）。
测试 `TestBEngine.test_02` 明确验证：一次答对 `mastered=0`；凑齐全部条件才 `mastered=1`；遗忘后退回。

## 5. 错误归因与补救（不同类型不同处理）

9 类 `error_type` → 9 套补救（`learning.REMEDY`）：遗忘→缩短间隔+无提示回忆；
词义混淆→最小对立对；助词→填空+场景替换；变形→变形表+前置语法回退检查；
听力→降速 TTS 复听+听写；理解→降级素材；汉字读音→音训对照；书写→假名选汉字。

**交错练习只用于易混语法/助词/变形**；词汇与汉字走分块 + SRS。
依据 Brunmair & Richter 2019 元分析（总体 g=0.42，但**词汇 g=−0.39，分块反而更好**）——
这是调研中最反直觉、也最影响实现的结论，见 `research/learning_science.md`。

## 6. 课程生成与完整性保证

`scripts/curriculum.py` 从真实种子**程序化组装** 80 天，不是 80 个空标题。
编排依据 `research/nh80_framework.md`（NH80 高频压缩习得法，v2），**不照抄教材课序**。

**v2 算法（相对 v1 均匀铺开的改动；符号均取自 `scripts/curriculum.py` 真实实现）**：

- `LEVEL_WINDOWS = {"N5": (1,25), "N4": (26,45), "N3": (46,65)}` + `_windows_by_level(items, windows)`：
  按 `frequency` 降序 + id 稳定排序，把各级种子**分级窗口配额**集中投放。
  v1 的 `_windows()` 均匀铺开曾把几乎为空的 N3 摊到 Day 51–72，用 100% 覆盖率掩盖 P4 偏科
  （证据见 `research/curriculum_provenance.md` §3.1）。
- `_topo_days_by_level(grammar, windows)`：语法按 `prerequisites` 依赖链在分级窗口内**迭代拓扑修正**，
  保证动词变形规则先于依赖它的复合句型、先修一定出现在更早的天，不再按 id 硬排。
- `CANDO_BANK`（6 阶段真实任务池，按阶段内顺序取） + `OBJECTIVE_POOL` / `RUBRIC_POOL` / `FOCUS_CYCLE`：
  每天生成差异化 `can_do` / `scene_tag` / `focus` / `objectives` / `rubric` / `completion`，
  Day 1 固定从「初次见面」起步、不会轮到超纲任务（对应 §3.2 去模板化）。
- `validate` 新增 `level_delivery`（P3 的 N4 ≥ 20、P4 的 N3 ≥ 40）与 `teaching_design`（distinct 数量下限）
  两组强校验。本次实测：`level_delivery = {P1 N5:99, P2 N5:145, P3 N4:111, P4 N3:130}`、
  `teaching_design = {distinct_scene:78, distinct_can_do:77, distinct_objectives:80, distinct_rubric:66, distinct_theme:80}`，
  `python3 scripts/nh80.py validate` → `error_count=0`、`warnings=[]`；`python3 tests/test_all.py` → 20/20 PASS。

- N5 词汇/语法/汉字铺在前期，N4 中期，N3 后期；66 天后原则上不再塞新知，转入混合复习。
- 语法按 `prerequisites` 做**拓扑迭代修正**，保证先修一定出现在更早的天；依赖动词变形的语法必须先有变形语法。
- 题目严格超纲检查：`question.knowledge_ids` 必须全部在当天或更早出现。
- 素材按 **level 分级**（N5 全程可用 / N4 从 Day26 / N3 从 Day46），
  允许 5–10% 生词（可理解输入），这是 `known_ratio` 的本意；不要求所有引用词都已学。
- 每天 10 项要素齐全、时间块合计严格 60 分钟、`assessment` 按优先级合并（同一天绝不叠加多套试卷）。
- `validate` 对 80 天做多类强校验（含 v2 新增 `level_delivery` 分级兑现与 `teaching_design` 去模板化校验），失败即拒绝写入（不会产出空壳课程）。

**诚实标注**：全部课程 `review_status=generated`，是「从已校验种子组装的可运行课程」，
不是 80 篇人工逐课精修教材。`curriculum/coverage_report.md` 列出覆盖率与未覆盖项。
Day 1 另有 8 道专门手写的零基础诊断题（Q0181–Q0188），Day 2–5 有配套基础题。

## 7. 状态持久化、备份、审计

- `data/state.db` 唯一可写真源；`student/*.json` 是 `export_state` 生成的**只读镜像**（禁止手改当状态变更）。
- 每次写操作经事务 + `audit_log`（时间戳、动作、payload SHA256 前 16 位、摘要）。
- `backup` 用 SQLite 官方 backup API 生成时间戳快照到 `data/backups/`；每 7 天 `finish-day` 自动备份一次。
- `restore <path>` 先校验 integrity、先自动备份当前库、再覆盖；`audit` 可查看最近操作。
- 所有测试在独立临时目录跑，不污染真实学习档案。

## 8. 每日会话与平台能力边界（不做假）

`research/platform_capabilities.md` 的真实核实结论：

- 子 Agent、定时任务、记忆**确实存在**，但平台**不承诺**把每日结构化教学状态从上一日传到下一日；
  子 Agent 默认干净启动；记忆是「模型自动抽取 + 注入提示词」，官方自己警告可能有概括偏差，
  **装不下 FSRS 的 D/S/R/due 精确数值**。
- 定时任务语义是「到点发起一次任务」，所有查阅页面均未发现「自动注入上次运行状态」；
  CLI 循环任务 3 天过期且不补跑；本地任务需电脑与客户端在线。

因此：
1. 每天**人工新建独立会话**，粘贴 `new_session_prompt.py N` 生成的提示词（含绝对路径清单）。
2. 会话从文件读状态；结束时由 `answer` / `import-web-result` / `finish-day` 写回。
3. 次日会话从 `daily_summary`、`fsrs_cards`、`attempts` 读回昨天。
4. **本次未创建任何自动化任务，未声称实现自动状态传递或自动调度教学。**

## 9. Cloudflare 每日页面（复用 zoomlab 模式，大幅简化）

参考 `/Users/mj/Documents/Projects/zoomlab-web` 的真实配置：Worker + `assets.directory` 静态资源
由一条 `wrangler deploy` 一起发布；本机脚本优先、push 不自动部署、先 preview 后 production、部署后 health check。

本项目**砍掉** React/Vite/D1/KV/Workers AI：Python 生成 80 个纯静态 HTML + 一个极简 Worker（仅 `/api/health`）。
详见 `docs/CLOUDFLARE.md`。

**页面不是状态真源**：无 fetch/XHR/sendBeacon，无外部 CDN；练习判分在客户端，
结果生成 `NH80R1.<base64url(json)>` 回传码，由 `import-web-result` 校验、幂等去重后写入本地 SQLite。
开放题在网页上的自评**不算掌握依据**，会挂起等 AI `grade-open` 判定。

**PC / 手机双端**：移动优先断点 640/900px、44px 触控目标、16px 输入防缩放、安全区、
一屏一题（step）vs PC 多题（grid）、TTS 手势解锁与降级、一键复制/系统分享/下载回传码、
PWA（manifest + 版本化 Service Worker + SVG icon）支持加主屏离线打开。

## 10. 成本控制

| 项 | 方案 | 成本 |
|---|---|---|
| 复习算法 | vendor 官方 py-fsrs (MIT) | 0 |
| 语音 | 浏览器 `speechSynthesis(ja-JP)` | 0 |
| 知识检索 | SQLite FTS5 + 关系图 | 0 |
| 状态存储 | 本地 SQLite + JSONL | 0 |
| 向量库 / 嵌入 / TTS API | **未使用** | 0 |
| 每日页面 | 纯静态，已上线 Cloudflare 免费额度（也可本地 `http.server`） | 0（2026-11-06 已部署，用已有 OAuth 登录态） |
| AI | WorkBuddy 当前模型；每天只读 briefing + 少量文件，不重算资料库 | 0 额外付费 |

AI 负责解释、互动、出题措辞、开放题评价与分析；程序负责复习时间、课程检索、统计、持久化。
不需要每天重新研究资料库、不需要每天重新生成 80 天课程。

## 11. 版权与合规

- 外部版权教材（Irodori / Tadoku / JLPT 官方样题 / NHK）**只存 URL 索引**，
  `materials.jsonl` 中 `review_status=index_only` 的 `text_ja` 为空，构建时有强校验。
- 知识种子全部标注 `S000`（项目原创整理），**不虚构**「引用了 IRODORI 教材」的关系。
- 题库与短文为原创；14 条种子标 `needs_review`（v1 为 6 条；读音/语感待核），不冒充权威词典认证。
- 完整来源、许可证、失败记录见 `research/source_registry.md` 与 `config/sources.json`。

## 12. v3 数据流（页面从「系统报表」改回「一课教材」）

> 依据 `docs/REDESIGN_PLAN.md`（决策记录 + 执行结果）、`research/textbook_lesson_pattern.md`
> 与 `research/ux_audit.md`。本节只描述**数据流**，不记录部署结果：**v3 已上线（2026-11-06 重新部署）**，
> Cloudflare 重新部署与 GitHub push 由主 agent 稍后执行，不写「已上线 v3」、不编造版本 ID。

### 12.1 从课程真源到 8 区块

```
knowledge/seeds/*.jsonl (1066 条) ─┐
knowledge/ko_analogy.json (85/85 语法 + 57 词) ─┤
                                               ▼
scripts/curriculum.py  →  curriculum/curriculum.json 每天新增
   · lesson_core      3 句真实日中对照（kana 仅在资料层核实后填，否则留空）
   · review_plan      具体词 + 中文原因 + 下次 Day
   · teaching_notes   中文难点讲解
   · 旧字段（can_do/focus/blocks/assessment/source_ids/review_status）全部保留
                                               │
        nh80.py start-day N 的 briefing 同步带上这三段
                                               ▼
scripts/build_site.py  assemble_day()  →  web/data/day-NNN.json + web/day-NNN.html
   按 8 区块顺序组装：①今天要会的 3 句话 ②单词常显全字段
   ③语法（中文接续/易错/韩语对照）④汉字 ⑤例句会话独立区
   ⑥练习先想后看答案含示范句 ⑦今日复习具体词表 + 三档自评
   ⑧页尾折叠「给老师/系统」（能力目标/时间块/图表/编号/回传码/术语）
```

`assemble_day()` 现在读取种子里原先被丢掉的 `romaji` / `pos` / `examples` / `notes_for_zh` /
`usage` / `common_errors` / `compare` / `text_zh` / `rubric` / `rationale` / `expected_production`
等字段，页面不再只剩骨架；
所有字段缺失时优雅降级（不显示 `undefined`、不编造日语）。**读音与原文分离**：
`audio_text` 不再被当作读音显示，`text_kana` 有才显示；Day 1 第 2 句「今日はいい天気です。」
的真实假名「きょうはいいてんきです。」来自资料层核实，其余无把握的 `kana` 仍留空。

### 12.2 `ko_analogy.json` 按天裁剪

`knowledge/ko_analogy.json` 是**静态教学参考文件**，覆盖 85/85 语法 + 57 词，
每条含 `hint_zh` / `caution`（明确「结构可借、词不能猜」，并对中日同形异义显式警告）。
它**不入 `state.db` 关系图**，因此种子仍 **877 条**、关系边仍 **4983 条**（沿用此前实测，
不编造新的边数）。若把全量塞进每天的页面数据，`day-001.json` 会膨胀到 92,854 字节；
`build_site.py` 只把**当天相关**的语法 / 词条目写入顶层 `ko_analogy`（Day 1 实测 1 条语法 + 6 词），
裁剪后为 23,932 字节
（中日文多字节，字符计与字节计不可混用）。

### 12.3 复习三档自评 → FSRS（只排期，不判掌握）

```
页面「今日复习」：遮中文回忆 → 点开对答案 → 记住了 / 模糊 / 忘了
        │  写入回传码 NH80R1.<...> 的新字段 review_ratings
        ▼
nh80.py import-web-result  消费 review_ratings
        │  返回 review_ratings_applied / review_ratings_duplicate / review_ratings_rejected
        ▼
learning.apply_review_rating(kid, label, day, session_id)
        good→3  hard→2  again→1   （REVIEW_RATING_MAP）
        │  调用官方 py-fsrs，只算新的 due（排期）
        ▼
data/state.db  fsrs_cards.due 更新（+ review_tasks 补救记录 + audit_log）
```

**硬边界（强调）**：`apply_review_rating` **只排期**——不写 `attempts`、不改五阶段 `stage`、
**不判 `mastered`**；同会话按 `session + kid` 幂等（重复返回 `duplicate`）。三档自评只是
「下次什么时候再见到这个词」的输入，**不是**「已掌握」的证据。掌握仍由 §4 的五阶段门控 +
`rolling_accuracy` 判定，由脚本按 `CONTRACTS.md` §11 执行；**AI 不得据自评宣称「已掌握」**。
本地 `start-day N` 的真实到期队列仍以 `state.db` 为准，静态页只展示 `review_plan` 计划
并如实标注「实际到期以本地 SQLite / WorkBuddy 会话为准」。

### 12.4 与既有结论的关系（全部不变）

- §2「语义检索明确不启用」、§3「FSRS 只是记忆调度器、不是知识追踪模型」、
  §4「一次答对不算掌握」、§8「平台不自动传递状态」、§9「页面不是状态真源」——**结论不变**。
  `review_ratings` 只是回传码新增字段，不改变页面零 fetch / 零外部请求、不改变状态唯一真源。
- 术语中文化只作用于页面文案，不改 `CONTRACTS.md` 数据契约里的字段名。
- 课程编排仍依据 `research/nh80_framework.md` 自研方法，**不照抄任何教材课序、不声称已对齐教材课序**；
  教材只贡献一课的呈现顺序与规格（`research/textbook_lesson_pattern.md`）。
