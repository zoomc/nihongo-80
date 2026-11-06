# 每日页面重设计计划（v3 · 从「系统报表」改回「一课教材」）

**日期**：2026-11-06　**触发**：用户反馈「网页版太抽象了，我都看不懂……单词、语法、例句、发音、适当的难点讲解、记忆曲线科学复习、练习，至少得覆盖这些吧，可以适当对照下韩语类似语法」

**输入**：
- `research/ux_audit.md`（学员视角实测审计，PC 1440 / 手机 390 真实截图 + DOM 探针）
- `research/textbook_lesson_pattern.md`（真实下载 Irodori 官方 `X_howto_en.pdf` / `X_contents_en.pdf` 提取的一课结构，另核实 Genki / Marugoto / JLPT 官方页）

---

## 1. 根因（不是审美问题）

| # | 实测事实 | 后果 |
|---|---|---|
| 1 | 首屏前 3 屏可学日语内容 = **0%**；词汇/语法/汉字/素材 section 默认折叠，卡片还要翻面才见背面 | 学员还没见到一个日语单词，先被要求理解整套系统 |
| 2 | 首屏被「能力目标（教研措辞）/ 60 分钟时间块 / 3 张图表 / `diagnostic` / `FSRS` / `focus: listening/reading` / `Can-do`」占满 | 像后台管理页，不像教材 |
| 3 | `build_site.py` 的 `assemble_day()` 只从种子挑了 5 个字段：`surface/kana/meaning_zh/jlpt`、`pattern/meaning_zh/connection/example`、`char/onyomi/kunyomi/zh_trap` | 种子里**本来就有** `romaji/pos/examples/notes_for_zh/usage/common_errors/compare/text_zh/rubric/rationale/expected_production`，全被丢掉 → 页面只剩骨架 |
| 4 | `app.js` 把素材 `audio_text` 当「文本读音」，而种子里 `audio_text === text_ja` | 「读音」显示成原文，零基础无法读 |
| 5 | 复习只有 `review 10分 FSRS 到期项主动回忆` 和 `review_count` | 不知道今天复习哪几个词、为什么是今天、下次何时 |
| 6 | 中文难点讲解只有汉字卡 `zh_trap`；韩语对照 **0 处** | 中文/韩语背景这个最大的加速优势完全没用上 |
| 7 | 练习区默认折叠，第 1 题就是无参考答案的开放题；反馈是 `forgetting/meaning_confusion` 英文归因 | 「先考试后教学」，零基础第一题就卡住 |
| 8 | 真机有 ja-JP 语音时 CSS 隐藏假名 | 比审计截图更不友好：听不懂也没字可看 |

**结论**：不需要重做引擎，也不需要再生成 80 篇教材。要做的是**把已有的真实数据全部呈现出来，按教材顺序重排，并补齐 4 类确实缺失的内容**（中文讲解、韩语对照、例句假名/独立例句区、具体复习清单）。

---

## 2. 教材给的顺序（真实出处）

Irodori 官方 *How to Use This Textbook*（PDF 已下载提取）每个 Speaking 活动：
`➊Can-do 目标 → ➋词的准备（看图听词→跟读，官方写明"目标是查发音、不是背单词"）→ ➌听示例对话求大意 → ➍Focus on the form（听填空→自己发现规则→再读 Grammar Notes）→ ➎Speaking（影子跟读→换词练→自由说）→ ➏Can-do 自评`；
课末另附 `Listening script / Kanji Words / Grammar Notes / Tips for life in Japan`，别册有 `Word lists / Answer / Grammar Worksheets`。
Genki 官方顺序：`会話 Dialogue → 単語 Vocabulary → 文法／表現ノート → 練習 Practice（题头标文法编号）`。

**共同点：先给能用的话和词，再讲规则，再练，最后自评。系统信息一律不在正文里。**

---

## 3. 新页面区块顺序（P0，首屏即可学）

| # | 区块 | 必须呈现 | 数据来源 |
|---|---|---|---|
| 1 | **今天要会的 3 句话** | 日文（大字）+ 假名读音（有才显示，不伪造）+ 中文 + 逐词拆解 + 每句可听 | `lesson_core`（课程新增）/ 素材 `text_ja`+`text_zh` / 语法 `examples` |
| 2 | **单词** | 常显不折叠：汉字 / 假名 / 罗马字 / 词性 / 中文义 / 1–2 例句（日文+中文+可听）/ 常见搭配 / **中文易错提示** / **韩语对照** / 听按钮 | 种子全部字段 + `ko_analogy` |
| 3 | **语法** | 意思 / **中文接续说明** / 2–3 例句（日文+中文+可听）/ 使用场景 / **易错点** / 相近语法区别 / **韩语对照（标不等价）** | `grammar` 全部字段 + `ko_analogy` |
| 4 | **汉字** | 音读 / 训读 / 例词 / 中文母语者陷阱（不要求抄写） | `kanji` 已有 |
| 5 | **例句 / 会话** | 独立成区：日文 + 假名（有才显示）+ 中文 + 听；**不得把原文当读音** | `materials.text_ja/text_kana/text_zh/audio_text` |
| 6 | **练习** | 默认展开，由易到难；先想→点「看答案」→解析；开放题给示范句；逐题中文化反馈 | `questions` 全部字段（含 `rationale/rubric/expected_production`） |
| 7 | **今日复习（记忆曲线）** | 具体词表（词形+中文），「为什么今天：X 天前学的，按 1/2/3/7/14/30 天间隔回顾」「下次大约 Day N」；遮中文自测 → 点开对答案 → 记住了/模糊/忘了 三档 | `review_plan`（课程新增）+ 页面收集自评 |
| 8 | **页尾折叠：给老师 / 系统** | 能力目标、60 分钟时间块、可视化图表、来源编号、回传码、诊断/评估标签、术语 | 保留但移出前 3 屏 |

**术语改写**：`diagnostic`→「摸底（不计分，只用来定起点）」；`FSRS 到期`→「今天该回顾这几个词」；`Can-do`→「今天要会做的事」；`focus`→「今天重点：听 / 读」；`NH80R1` 回传码→「把成绩带回 WorkBuddy」（说明文字，码仍可复制）。

---

## 4. 数据契约（三个 subagent 必须严格遵守）

### 4.1 课程层 `curriculum/curriculum.json` 每天新增字段（由 `scripts/curriculum.py` 生成）

```jsonc
"lesson_core": [                       // 3 句，必须来自真实种子，不得编造日语
  {"ja":"...", "kana":"...", "zh":"...", "note_zh":"...", "audio_text":"..."}
],
"review_plan": [                       // 具体复习项，来自 review_knowledge_ids
  {"kid":"V0001", "surface":"私", "kana":"わたし", "zh":"我",
   "reason_zh":"3 天前学的，按间隔回顾", "learned_day":1, "next_hint_zh":"大约 Day 8 再回顾"}
],
"teaching_notes": ["..."]             // 2–4 条中文难点讲解（取自种子 notes_for_zh / zh_trap / common_errors）
```
- `lesson_core[].kana` 允许为空字符串；**为空时页面不得伪造假名**，只显示日文 + 中文 + 听。
- `review_plan` 是**基于课程的间隔计划**（确定性，1/2/3/7/14/30 天），页面须明确标注「实际到期以本地 SQLite / WorkBuddy 会话为准」。
- 原有字段（含 `can_do/focus/blocks/assessment/source_ids/review_status`）**一个都不能删**，`tests/test_all.py` 与 `nh80.py` 依赖它们。

### 4.2 资料层 `knowledge/ko_analogy.json`（新增，人工编写，覆盖全库可复用）

```jsonc
{"meta":{"note":"韩语对照只能作结构提示，必须标注不等价处；不得据此猜词","checked_at":"2026-11-06"},
 "grammar":[{"match":"G0001","pattern":"N は N です","ko":"N 은/는 N 입니다",
             "hint_zh":"韩语也是 SOV、助词后置；但 は 表主题、은/는 也表主题，が/이/가 表主语，不能一一对应。です 在韩语日常更常说 이에요，입니다 偏正式。",
             "caution":"不等价"}],
 "vocab":[{"match":"V0001","ko":"저 / 나","hint_zh":"...","caution":"..."}]}
```
- 至少覆盖 **全部 85 条语法**（可多条共享一个 `match` 组，用 `match` 为 G id 或 pattern 关键字）、**高频汉字词 40 条以上**。
- 每条必须有 `hint_zh` 与 `caution`；不得写「完全一样」。
- 素材 `materials.jsonl` 可选补 `focus_zh`（1 条中文难点讲解）与 `text_kana`（**只在你确知读音时填，否则留空**）。

### 4.3 页面层 `web/data/day-NNN.json` 新增字段（由 `scripts/build_site.py` 组装）

```jsonc
"lesson_core": [...], "review_plan": [...], "teaching_notes": [...],
"ko_analogy": {"grammar":[...], "vocab":[...]},
"vocab": [{"id","surface","kana","romaji","pos","meaning_zh","jlpt",
           "examples":[{"ja","zh","audio_text"}], "notes_for_zh","ko","ko_hint",
           "confusables":[...]}],
"grammar":[{...,"usage","common_errors","compare","examples":[...],"ko","ko_hint","explanation_zh"}],
"kanji":[{...,"vocab_refs","ko_hint"}],
"materials":[{...,"text_kana","text_zh","focus_zh","audio_text"}],
"questions":[{...,"rationale","rubric","expected_production","answer","options"}]
```
- **所有字段可缺失时优雅降级**：缺了就不显示该行，绝不显示 `undefined`、绝不编造日语。
- 页面**不得**向服务器发送学习数据；回传码格式 `NH80R1.<base64url(json)>` 保持兼容，复习三档自评作为新字段加入 payload（`review_ratings`），**不得**把自评写成 `correct` 或掌握判定。

---

## 5. 复习闭环（记忆曲线怎么落到页面）

1. 课程按 `1/2/3/7/14/30` 天间隔算出 `review_plan` 的具体词（确定性，程序算）。
2. 页面展示「先遮住中文回忆 → 点开对答案 → 记住了 / 模糊 / 忘了」。
3. 三档写入回传码 `review_ratings`，`nh80.py import-web-result` 映射为 FSRS `rating 3/4、2、1`，由 `scripts/learning.py` 的官方 py-fsrs 算 `due`，**页面不自行决定复习时间、不自行判定掌握**。
4. 本地 `start-day N` 的真实 FSRS 到期队列仍以 `state.db` 为准；线上静态页只展示计划并如实标注这一区别。

---

## 6. 分工与验收

| 任务 | 负责 | 只改这些文件 | 验收 |
|---|---|---|---|
| E 教学计划层 | subagent | `scripts/curriculum.py`、`scripts/nh80.py`（briefing 同步） | `nh80.py init` + `validate` 0 错误；80 天都有 `lesson_core`(3) / `review_plan` / `teaching_notes`；旧字段不丢 |
| D 资料层 | subagent | `knowledge/ko_analogy.json`（新增）、`knowledge/seeds/materials.jsonl`（可选补字段） | JSON 合法；语法覆盖 85/85；无「完全一样」表述；日语/韩语逐条自检 |
| C 页面层 | subagent | `scripts/build_site.py`（+ 运行生成 `web/`） | 首屏 3 句话 + 常显词卡；8 区块齐全；PC/手机真机截图；无外链；回传码可解码；旧功能不坏 |
| 集成 / 验证 / 部署 / push | 主 agent | 文档、`reports/`、git | 19 项回归 + 线上全路径 + 浏览器实测 + Cloudflare preview/production + GitHub push |

---

## 7. 诚实边界（不得越线）

1. **不伪造假名读音**：种子没有 `text_kana` 就留空，用 TTS 朗读日文 + 中文翻译兜底；不得把 `text_ja` 当读音。
2. **不假装已掌握**：复习自评只是输入，不写 `correct`、不判 `mastered`；「已答 0/8」这类进度显示不得暗示完成。
3. **不照抄教材原文**：Irodori / Marugoto / JLPT / Tadoku 只作结构与标准参照，正文仍全部项目原创。
4. **韩语对照必须带 `caution`**：结构可借、词不能猜；中日同形异义（勉強/大丈夫/手紙/汽車）显式警告。
5. **保留原有工程底子**：零 CDN、零 fetch、`file://` 可开、PWA 离线、双端适配、TTS 手势解锁与降级提示、回传码、不编造数据。
6. **静态线上页 ≠ 本地状态**：复习清单标为「计划」，真实到期与成绩以 `state.db` / WorkBuddy 会话为准。

---

## 8. 完成后怎么判断「不抽象了」

零基础学员打开 Day 1（手机或 PC）**不点任何折叠**就能：
① 读到 3 句日文 + 中文 + 点一下听到发音；② 看到 6 个词怎么读、什么意思、怎么用在句子里、中文易错点、韩语对照；
③ 看懂 1 条语法的接续、例句、易错点；④ 独立读到会话与中文；⑤ 做 5 道由易到难的题并看到解析与示范句；
⑥ 看到「今天具体复习哪几个词、为什么、下次何时」并能自测三档。
**系统术语、图表、ID、回传码全部退到页尾折叠区。**

---

## 执行结果（v3）

> **本节是追加的执行记录**。以上 §1–§8 是改造前的**决策记录 / 计划**，**一字未改**。
> 以下数据来自本次实际运行的 `python3 tests/test_all.py`、`python3 scripts/nh80.py validate`
> 与对 `curriculum/`、`knowledge/`、`web/data/` 的只读核对；浏览器数据为主 agent 集成时本机
> Chrome CDP 实测。**v3 内容待随本次发布上线**：v3 的 Cloudflare 重新部署与 GitHub push
> 由主 agent 稍后执行，本节不写「已上线 v3」、不记录任何版本 ID，也不声称
> 「已对齐教材课序」「已完成 JMdict 校核」「平台自动调度」。

### A. 逐条对应 §3「8 区块顺序」——实际完成状态

| # | §3 计划区块 | 完成状态 | 真实指标 / 证据 |
|---|---|---|---|
| 1 | 今天要会的 3 句话 | 完成。课程每天新增 `lesson_core` 3 句真实日中对照；假名**只在资料层核实后填**，其余留空；大字日文 + 中文 + 逐词提示 + 每句「听」按钮 | 80/80 天 `lesson_core`(3)；Day 1 第 2 句「今日はいい天気です。」假名补为「きょうはいいてんきです。」；PC 1440 首屏实测 3 句话 |
| 2 | 单词（常显全字段） | 完成。汉字 / 假名 / 罗马字 / 词性 / 中文义 / 例句 / 搭配 / 中文易错提示 / 韩语对照 / 听按钮常显，不再折叠翻面 | CDP 390 实测 **6 张词卡**；词卡改**单列**（`.vlist` 计算值 `340px` 即单列）；**25 个听按钮** |
| 3 | 语法（中文接续 / 易错 / 韩语对照） | 完成。意思 + 中文接续说明 + 例句 + 使用场景 + 易错点 + 相近语法区别 + 韩语对照（标「不等价」） | `ko_analogy.json` 覆盖 **85/85 语法**；CDP 390 实测 **7 个韩语对照块** |
| 4 | 汉字 | 完成。音读 / 训读 / 例词 / 中文母语者陷阱，不要求抄写 | 页面 8 区块组装校验通过 |
| 5 | 例句 / 会话独立区 | 完成。日文 + 假名（有才显示）+ 中文 + 听；**不再把原文当读音**（`audio_text` 与 `text_ja` 分离） | 修掉「读音=原文」bug；`materials.jsonl` `text_kana` **12 条真实假名**、其余 **38 条留空**（另 10 条 `index_only` 无正文）；CDP 390 实测 1 条假名行 |
| 6 | 练习（先想后看答案，含示范句） | 完成。默认展开、由易到难、逐题中文化反馈、开放题给参考答案与示范句 | 修掉「内容全折叠」「开放题无参考答案」bug；中文提示改用素材 `focus_zh`（**50/50**）避免错配 |
| 7 | 今日复习（记忆曲线） | 完成。具体词表 + 中文原因 + 下次 Day + 遮中文自测 + 三档自评；**三档真正写回 FSRS** | 新增 `learning.apply_review_rating`；`nh80.py import-web-result` 消费 `review_ratings` 并返回 `review_ratings_applied` / `review_ratings_duplicate` / `review_ratings_rejected`；`test_06b_review_ratings_drive_fsrs` PASS |
| 8 | 页尾折叠「给老师 / 系统」 | 完成。能力目标、60 分钟时间块、图表、来源编号、回传码、诊断 / 评估标签、术语全部移出前 3 屏；侧栏技术说明改人话 | PC 1440 首屏实测 **无图表、无术语**；CDP 390 `innerWidth=390 / scrollWidth=390` 零溢出 |

§3 术语改写已落地：`diagnostic`→「摸底（不计分，只用来定起点）」、`FSRS 到期`→「今天该回顾这几个词」、
`Can-do`→「今天要会做的事」、`focus`→「今天重点：听 / 读」、`NH80R1`→「把成绩带回 WorkBuddy」。

### B. 逐条对应 §6「分工与验收」——实际完成状态

| §6 任务 | 状态 | 真实指标 |
|---|---|---|
| E 教学计划层（`scripts/curriculum.py`、`scripts/nh80.py`） | 完成 | 80/80 天有 `lesson_core`(3) / `review_plan` / `teaching_notes`；`start-day` 的 briefing 同步带上这三段；能力目标改人话；旧字段（`can_do/focus/blocks/assessment/source_ids/review_status`）一个未删；`validate` `error_count=0`、`warnings=[]` |
| D 资料层（`knowledge/ko_analogy.json` 新增、`knowledge/seeds/materials.jsonl` 补字段） | 完成 | JSON 合法；语法 **85/85**、词 **57 条**（≥40）；每条 `hint_zh` + `caution`、无「完全一样」；60 条素材中 50 条有正文，`focus_zh` **50/50**、`text_kana` **12 条真实假名**（其余 38 条留空）；16 处 `text_ja`/`text_zh` 句数错配 → **0** |
| C 页面层（`scripts/build_site.py` 重写 + 运行生成 `web/`） | 完成 | 8 区块齐全；首屏 3 句话 + 2 张完整词卡（PC 1440）；CDP 390 `innerWidth=390 / scrollWidth=390`、6 张词卡、1 条假名行、7 个韩语对照块、25 个听按钮；无外链；回传码可解码；旧功能（PWA / TTS / 零 fetch）未坏 |
| 集成 / 验证 / 部署 / push（主 agent） | **部分**：集成修复与验证已完成；**v3 的 Cloudflare 重新部署与 GitHub push 尚未执行**，由主 agent 稍后做；`docs/CLOUDFLARE.md` 部署记录由主 agent 单独更新 | 集成修复：词卡单列、`lesson_core` 补真实假名并过滤邮件标题类片段、中文提示改用 `focus_zh`、侧栏改人话、顶层 `ko_analogy` 按天裁剪、复习三档写回 FSRS |

**集成修复的真实数据**：`web/data/day-001.json` 顶层 `ko_analogy` 由全量裁剪为当天相关，
体积约 **92KB → 14.6K 字符**（同一构建口径：裁剪前 92854 字节；裁剪后 14673 字符 / 23932 字节，
中日文多字节故字符计约 14.6K、字节计约 23.4KB，两种计量不可混用）。
`learning.apply_review_rating` 映射 `good/hard/again → rating 3/2/1`，只排期、不写 `attempts`、
不改 `stage`、不判 `mastered`、同会话幂等。

### C. 全量回归（本机实跑）

- `python3 scripts/nh80.py init`：ok，877 种子、80 天。
- `python3 scripts/nh80.py validate`：`ok:true`、`error_count=0`、`warnings=[]`、
  `level_delivery.P4.N3=130`、`teaching_design.distinct_objectives=80`（**80/80 不同**）。
- `python3 tests/test_all.py`：**20/20 PASS**（`Ran 20 tests in 6.346s — OK`），
  含新增 `test_06b_review_ratings_drive_fsrs`。
- 关系边 `SELECT COUNT(*) FROM relations` = **4983**（沿用此前实测，知识规模未变）。

### D. 4 项诚实边界的落实方式（对应 §7）

| §7 边界 | 落实情况 |
|---|---|
| **1. 不伪造假名读音** | `lesson_core[].kana` / `materials.text_kana` **只在资料层核实后填**：12 条真实假名，其余 38 条有正文素材与 Day 1 第 1、3 句留空；页面为空时只显示日文 + 中文 + 听，不显示 `undefined`、不把 `text_ja` 当读音。Day 1 第 2 句假名是**补真实读音**，不是编造。 |
| **2. 不假装已掌握** | 三档自评写入回传码 `review_ratings`，导入后经 `learning.apply_review_rating` **只改 FSRS 的 `due`**：不写 `correct`、不写 `attempts`、不推进五阶段、不判 `mastered`；同会话幂等。页面不显示「已答 X/Y」式完成暗示；掌握仍由脚本按 `CONTRACTS.md` §11 门控判定，AI 不得据自评宣称「已掌握」。 |
| **3. 不照抄教材原文** | `research/textbook_lesson_pattern.md` 只取**一课的区块顺序与呈现规格**（Irodori 官方 `X_howto_en.pdf` / `X_contents_en.pdf`、Genki / Marugoto / JLPT 官方页核实），正文仍全部项目原创；`ko_analogy.json` 的 `meta.note` 明确「本项目原创教学编排，非引用某本教材原文；未逐条对照 JMdict / KANJIDIC」。课程仍按 `research/nh80_framework.md` 自研方法编排，**不采用任何教材线性课序**（不声称「已对齐教材课序」）。 |
| **6. 静态线上页 ≠ 本地状态** | 页面零 fetch / 零外部请求，成绩与复习自评只经 `NH80R1` 回传码由 `import-web-result` 写入 `data/state.db`；`review_plan` 明确标为「计划」，真实到期队列以 `start-day N` 的 `state.db` 为准。v3 已重新部署到 preview 与 production，并完成线上全路径与真实浏览器 DOM 复验。 |

另：§7.4「韩语对照必须带 `caution`」由 `ko_analogy.json` 每条 `caution` + 显式「结构可借、词不能猜」
与中日同形异义（勉強 / 大丈夫 / 手紙 / 汽車）警告落实；§7.5「保留原有工程底子」
（零 CDN / 零 fetch / `file://` 可开 / PWA 离线 / 双端适配 / TTS 手势解锁与降级 / 回传码）
在 CDP 双端实测中未破坏。

### E. 发布与推送（已完成）

- Cloudflare preview → production 重新部署完成，production 版本 ID `a0bf1d09-90f7-4cc4-b1c9-627b4f93ac27`；
- 线上 `/`、`/day-001.html`、`/day-050.html`、`/day-080.html`、`/data/day-001.json`、`/assets/*`、`/sw.js`、`/manifest.webmanifest`、`/api/health` 全部 200；
- 真实浏览器 `--dump-dom` 命中「今天要会的 3 句话」「きょうはいいてんきです。」「韩语对照」「今日复习」「记住了」「看答案」「中文易错」；
- GitHub 仓库 `zoomc/nihongo-80` 已同步推送。
