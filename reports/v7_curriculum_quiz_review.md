# v7 课程编排与练习题只读审查报告

- 审查日期：2026-11-08
- 审查对象：`/Users/mj/Documents/learn/jp/nihongo-80`（个人日语学习系统 v6，150 天 × 60 分钟）
- 性质：**只读审查**。未修改任何现有代码 / seeds / 页面 / DB；未执行 `git commit`；未运行任何会写回 `curriculum.json`、`generated-key.json`、`data/state.db` 的生成脚本。仅新增本文件与 `reports/evidence/v7_curriculum_issues.jsonl` 两个输出。
- 方法：直接读脚本与 seeds，重新在内存里调用 `quiz_v5.day_questions` 生成 150 天全部题目，与 `curriculum/curriculum.json`、`deploy/worker/src/generated-key.json`、`web/day-*.html`、`web/data/day-*.json`、`data/state.db` 交叉核对；解析 150 个页面的 `span.min` 分钟标注；逐题人工核读抽样题与 39 道周测/阶段题。

## 0. 结论摘要

| 指标 | 数值 |
|---|---|
| 检查项总数 | **36** |
| PASS | **19** |
| PARTIAL | **10** |
| **FAIL** | **7** |
| P0（阻断级） | **0**（未发现导致系统无法运行或数据不自洽的致命问题） |
| P1（高严重度，5 项） | `CURR-LISTEN-LEVEL`、`QUIZ-ASSESS-REPLACE`、`CURR-REVIEW-FSRS`、`CURR-GRAMMAR-DUP`、`QUIZ-KANJI-3OPT` |
| P2（中/低，21 项） | 其余 21 个 issue |
| `v7_curriculum_issues.jsonl` | **26 行**（high 5 / medium 7 / low 14；area：curriculum 9、quiz 6、assessment 6、listening 2、gating 2、key 1） |

**7 个 FAIL**：C6 语法条目重复 / C7 复习队列与 FSRS 脱节 / Q4 答案写进题干 / Q7 汉字题只有 3 选项 / Q10 阶段日丢汉字语法题 / L3 听力素材难度倒挂 / A4 种子标签与 curriculum 不一致。

**核心判断**：数据骨架（150 天、2700 词、276 语法、620 汉字、blocks=60、1035 题答案表、先修拓扑）是自洽且经得起自动校验的；问题集中在**题目质量与内容编排**——每日 6 题的覆盖与对齐、周测替换机制、听力素材难度与原创度、复习队列与 FSRS 的脱节。这些多数是「真 bug」或「AI 草稿边界」，而非架构缺陷。

---

## 1. 结论速查表（按 P0 → P1 → P2 排序）

| 优先级 | ID | 类别 | 结论 | 严重度 | 一句话 |
|---|---|---|---|---|---|
| P1 | `CURR-LISTEN-LEVEL` | 真 bug | **FAIL** | high | 听力素材按 level 字符串排序导致 N4 阶段做 N3 素材、N3 阶段做 N4 素材（39 天） |
| P1 | `QUIZ-ASSESS-REPLACE` | 真 bug | **FAIL** | high | 6 个 stage/self_check 日的替换切片把当天汉字题、语法题全部截掉 |
| P1 | `CURR-REVIEW-FSRS` | 真 bug | **FAIL** | high | 复习队列只含词汇、静态 T+1/3/7，与 `learning.due_queue` 无关联，276 语法 / 620 汉字从不复习 |
| P1 | `CURR-GRAMMAR-DUP` | 真 bug | **FAIL** | high | grammar 种子存在跨级别重复条目，276 条名义覆盖含水份 |
| P1 | `QUIZ-KANJI-3OPT` | 真 bug | **FAIL** | high | 3 道汉字读音题只有 3 个选项（`dict.fromkeys` 去重后不补齐） |
| P2 | `QUIZ-SAME-FORM-SPOILER` | 真 bug | FAIL | medium | 58 道词汇题日文词形 == 中文答案，答案在题干里 |
| P2 | `ASSESS-LABEL-MISMATCH` | 真 bug | FAIL | low | 9 条种子标 `mock`，curriculum 标 `self_check` |
| P2 | `QUIZ-MEANING-DUP-RISK` | 真 bug | PARTIAL | medium | 133 组重复释义 + 6 组语法重复释义，去重后可能不足 4 选项（本轮未触发） |
| P2 | `QUIZ-GRAMMAR-FIRST-ONLY` | 设计取舍 | PARTIAL | medium | 132 条语法 / 476 个汉字从未被每日题考查 |
| P2 | `CURR-GRAMMAR-JUJU-ORDER` | 真 bug | PARTIAL | medium | 授受组成组倒序（复合形式先于基础动词） |
| P2 | `CURR-EXAMPLE-KANJI` | AI 草稿边界 | PARTIAL | medium | 例句汉字进度与汉字教学脱钩，Day1 即出现未教汉字 |
| P2 | `LISTEN-TEMPLATE` | AI 草稿边界 | PARTIAL | medium | 45 篇听力 = 9 模板 × 5 变体，Q3 答案重复 5 次 |
| P2 | `KEY-ORPHAN-DB` | 真 bug | PARTIAL | medium | DB `questions` 表 988 条历史孤儿题，输入校验有兜底口子 |
| P2 | `CURR-PAGE-42-47` | 待核实 | PARTIAL | low | 实测 150 页 section 合计均为 42，与任务描述的「听力日 47」不符 |
| P2 | `ASSESS-SHARED-PASSAGE` | 设计取舍 | PARTIAL | low | 共用材料的 2 题各带完整 passage，页面重复渲染 2 次 |
| P2 | `ASSESS-TARGETS-COARSE` | 设计取舍 | PARTIAL | low | 39 题 targets 仅两类标签 |
| P2 | `GATING-70-LISTEN` | 设计取舍 | PARTIAL | low | 统一 70% + 全题必答对听力日更严苛，但「必须全对」不成立 |
| P2 | `ASSESS-A130-3-OPTIONS` / `ASSESS-A148-3-SPOILER` / `ASSESS-A021-1-DISTRACTOR` | AI 草稿边界 | PASS(整体)/单题 low | low | 单题选项颗粒度 / 轻微剧透 / 干扰项无关 |
| P2 | `GATING-HINTED` / `CURR-LISTEN-46-BOUNDARY` / `CURR-SPRINT-WEIGHT` / `CURR-LESSON-CORE-3` / `QUIZ-FNV-COLLISION` / `CURR-DUP-AUDIO` | 混合 | 见 §2 | low | 见 §2 对应检查项 |

---

## 2. 逐项审查

### 2.1 课程编排（11 项：PASS 6 / PARTIAL 3 / FAIL 2）

脚本基线：`scripts/curriculum_v5.py`（生成 `curriculum/curriculum.json`，502 KB）、`scripts/build_v5_site.py`（生成 `web/day-001..150.html`）、`scripts/nh80.py::_build_v5`（写 DB 与答案表）。注意三者共用同一份 `curriculum.json`，`nh80.py:254` 会把 `question_ids` 覆盖为真实 qid 后写回。

**C1 · 150 天是否真覆盖 2700 词 / 276 语法 / 620 汉字且无重复 — PASS**
- 证据：`curriculum_v5.py:27` `DAYS=150`；seeds 计数 `vocabulary.jsonl=2700 / grammar.jsonl=276 / kanji.jsonl=620 / materials.jsonl=140`。
- 命令输出：`vocab: total=2700 uniq=2700 missing=0 extra=0 dup_keys=0`；`grammar: total=276 uniq=276 missing=0 extra=0 dup_keys=0`；`kanji: total=620 uniq=620 missing=0 extra=0 dup_keys=0`。
- `new_vocab per day dist {9:3, 14:45, 19:19, 20:72, 22:11}`（Day1-3 减半、45 个听力日 14 词、冲刺期加压）。

**C2 · core ≤16（常规）/ ≤11（听力日）、extension 是否仍可学 — PASS**
- 证据：`curriculum_v5.py:167-169` `core_limit = 11 if listening else 16`；实测 `core-limit violations: 0`。
- extension 合计 **546** 个、147 天有拓展、单日最多 6 个；页面 `build_v5_site.py:358` 有「包含选学拓展」复选框，`build_v5_site.py:476` 给拓展词打 `optional` 标记，仍可学。

**C3 · 语法先修拓扑是否严格在前（同天不互依、prerequisites 必须更早） — PASS**
- 证据：`curriculum_v5.py:103-140` DFS 拓扑 + 按天分配时 `all(p in gday and gday[p] < d)`；兜底 `for cand in pending: gby[DAYS].append(...)` 仅在拓扑异常时触发。
- 命令输出：`prereq-not-earlier violations: 0`、`prereq pointing to unknown id: 0`、`same-day mutual prereq days: 0`；`grammar per day dist {1:24, 2:126}`（252+24=276）；`cross-level prerequisites: 233`（绝大多数 N4→N5，正常）。

**C4 · 有没有 N3 语法排在 N5 前面 — PASS**
- 命令输出：`jlpt first-appearance day {N5:1, N4:33, N3:69}`、`jlpt last-appearance day {N5:32, N4:77, N3:150}`。N5 末次 Day32 < N3 首次 Day69，无倒挂。

**C5 · 成组语法（て形家族 / 条件四兄弟 / 授受 / 使役受身）— PARTIAL**
- PASS 部分：`G0020 て形 Day11` → `G0026/27/28/29 〜てください/いる/から/もいい Day13-14`；`G0025 条件形 Day33` → `G0038 使い分け Day35` → `G0221/222/223 ば/たら/なら Day63-64`；`G0049 受身形 / G0050 使役形 Day40` → `G0213/214 Day59` → `G0215 せられる/させられる Day60(pre=G0049,G0050)`。
- FAIL 部分（`CURR-GRAMMAR-JUJU-ORDER`）：`G0052 授受 〜てあげる/てくれる/てもらう Day41`（pre 仅 `G0020,G0009`）**早于**基础动词 `G0187 あげる/くれる/もらう Day46` 与 `G0188/189/190 〜てあげる/てくれる/てもらう Day46-47`。依赖未写进 `prerequisites`，拓扑检查因此为 0 违规但语义倒序。

**C6 · 语法条目重复 / N3 与 N4 重叠 — FAIL（`CURR-GRAMMAR-DUP`）**
- 命令输出：同 `meaning_zh` 重复 6 组 13 条：`越…越…`(G0079/G0134)、`不仅…而且…`(G0093/G0119/G0120)、`因为…；由于…`(G0104/G0228)、`正当…的时候`(G0133/G0153)、`即使…也…`(G0168/G0225)、`明明…却…`(G0175/G0226)。
- 近重复跨级别：`G0053(N3,Day73) ～はずだ/～わけではない` ↔ `G0241(N4,Day74) 〜はずだ`；`G0096(N3,Day74) 普通形+はずがない` ↔ `G0242(N4,Day75) 〜はずがない`；`G0064(N3,Day69) V辞書形/Vない形+ようにする` ↔ `G0234(N4,Day70) 〜ようにする`。
- `N3 grammars taught <= Day77: 4`（G0064/G0053/G0096/G0054），`N4 grammars taught >= Day69: 14`（G0233-G0246），即 Day69-77 期间 N3 与 N4 并行。同一语法相邻两天教两遍。

**C7 · 复习队列 `review_knowledge_ids` 合理性 / 与 FSRS 到期队列关系 — FAIL（`CURR-REVIEW-FSRS`）**
- 证据：`curriculum_v5.py:170-175` 只回溯 `vby[d-back]` 的前 4 个词 id，`dict.fromkeys` 去重后 `[:12]`。
- 命令输出：`review len dist {0:1, 4:2, 8:4, 12:143}` → **不是「总是 12 个固定」**，前几天不足；`review internal dup days: 0`；`review ids not learned strictly before: 0`；**`review ids that are grammar/kanji (not vocab): 0`**（全是 V 开头）。
- 与 FSRS 关系：`build_v5_site.py:403-414` 注释「公开页面只放课程复习词；权威到期队列由私人会话读取，避免公开学习状态」+ 页面 `build_v5_site.py:342` hint「会话再核对权威到期队列」——**架构说明是清楚的**；但 `learning.py:581-592 due_queue()` 才是真实到期队列（按 `fsrs_cards.due`），且 `learning.py:718-720` 在到期积压 >20 项时把复习块从 10 分钟扩到 20 分钟，而 `curriculum_v5.py:183` 的 blocks 固定「复习 10」、页面也固定 10 分钟。两套机制无数据关联、静态与动态冲突；620 汉字 / 276 语法学完即不再复习。

**C8 · 每天 blocks 合计 60 — PASS**
- 证据：`curriculum_v5.py:183-192` budgets；命令输出 `blocks sum dist {60: 150}`。常规日 `10+14+6+6+6+18=60`，听力日 `10+8+6+8+5+5+18=60`。抽样 Day001/007/045/047/090/150 均一致。

**C9 · 页面渲染分钟合计 42（听力日 47）与 curriculum 是否一致 — PARTIAL（待核实，`CURR-PAGE-42-47`）**
- 实测：解析 `web/day-001.html .. day-150.html` 的 `<span class="min">N 分钟</span>`，`all 150 pages section sums: {42: 150}`；头部 `build_v5_site.py:331` 硬编码「网页 42 分钟 · 会话 18 分钟」，150 页完全一致、无 47 的变体。
- 听力日 section = `10+8+6+8+5+5=42`（`build_v5_site.py:509` 听力块硬编码 8 分钟，同时新词/句子/练习各减，正好抵消）。页面 42 + 线下会话 18 = curriculum 60，自洽。
- **任务描述中的「听力日 47」在当前代码与 150 个页面里都不存在**；在 `reports/*.md` 中未检索到「47 分钟」说法。标 low 待核实，不据此改代码。

**C10 · 周测/阶段日有没有额外加题导致超时 — PASS**
- 证据：`quiz_v5.py:113-116` `qs = qs[:6-len(assessment)] + assessment` 是**替换**、不是追加，题数保持 6；`quiz_v5.py:129-130` 仅听力日追加 3 题。
- 实测 `per-day count dist {6:105, 9:45}`；`key per-day-count dist {6:105, 9:45}`。Day110/148 是 `self_check` 且是听力日 → 9 题，但时间块未增加（练习 5 + 听力 8），不额外超时。**但见 Q10：这 6 天丢的是汉字/语法题。**

**C11 · 阶段划分 P0–P4 与 assessment 日分布 — PASS**
- 证据：`curriculum_v5.py:28-34` P0(1-3)/P1(4-45)/P2(46-95)/P3(96-130)/P4(131-150)；`curriculum_v5.py:209-210` assessment 判定。
- 命令输出：`assessment dist {'diagnostic':1, 'none':122, 'weekly':21, 'stage':3, 'self_check':3}` —— 与任务描述「weekly 21 / stage 3 / self_check 3 / diagnostic 1」完全一致。
- 听力：45 天、首个 Day47、末个 Day150，`material_ids total 45 uniq 45 dups []`、`listening pool size 45`。（`is_listening_day` 用 `day>=46`，见 P2 项 `CURR-LISTEN-46-BOUNDARY`。）

### 2.2 每日 6 题（11 项：PASS 6 / PARTIAL 3 / FAIL 3 — 累计 FAIL 5）

脚本基线：`scripts/quiz_v5.py:15-84 build_quiz`、`:110-131 day_questions`、`scripts/assessment_v6.py:12-46 build_for_day`、前端 `build_v5_site.py:215-248 initQuiz`。

已重新生成 **1035 题**（= 105 天 × 6 + 45 天 × 9），与 `generated-key.json` 全量比对。

**Q1 · 抽 Day 1/7/45/47/90/150 全部题：题干清楚 / 4 选项 / 有且仅一个正确 — PASS（抽样日）**
- 全量命令输出：`option count dist {3:3, 4:1032}`、`h/oh/answer-in-options problems 0`、`每题恰有 1 个 option 的 fnv 等于 h`。
- 抽样逐题记录见 §5.1：Day001 `DDDKGV`、Day007 `VVVKGA`、Day045 `VVVAAA`、Day047 `VVVKGV+LLL`、Day090 `VVVKGV`、Day150 `VVVKGV+LLL`。所有抽样题题干明确、答案唯一、答案不在题干里（抽样日无同形词）、干扰项同层级。
- 例：Day047 `Q-047-G`「句型「〜てくれる」的意思是？」opts `…或… / 只要…就… / 每…；每隔… / （别人）为我做…`，唯一正确；Day090 `Q-090-G` 的 4 个选项均为不同语法释义。

**Q2 · 干扰项是否同层级/同词性 — PASS（抽样）**
- 词义题干扰项均为中文释义（`quiz_v5.py:40-41` 按相同 `jlpt` 抽），汉字题均为片假名音读，语法题均为 `meaning_zh`，听力题均为同类名词短语。抽样 6 天 + 12 篇听力未见一眼可排除的跨类干扰项（周测 A021-1 例外，见 §2.4）。

**Q3 · 答案哈希 h / oh 与选项一致、是否把答案写进公开页 — PASS**
- 全量：`h = fnv(answer)`、`oh = [fnv(o) for o in opts]` 全部一致，`answer` 均在 `options` 内；`public_question`（`quiz_v5.py:106-107`）只保留 `qid/prompt/options/h/oh/passage`。
- `web/data/day-047.json` 实测题目 keys = `['h','oh','options','prompt','qid']`，**无 answer / rationale / knowledge_ids / targets**；前端 `build_v5_site.py:234` 用 `fnv(o)===q.h` 判分、`:236` 用 `q.oh[i]===q.h` 标绿。

**Q4 · 有没有把答案写进题干 — FAIL（`QUIZ-SAME-FORM-SPOILER`）**
- 全量扫描 `「X」是什么意思？` 且 `X == answer`：**58 题**，分布 45 天。例：`Day007/Q-007-V2「旅行」=旅行`、`Day045/Q-045-V2「科学」=科学`、`Day047/Q-047-V5「教育」=教育`、`Day002/Q-002-V0「二」=二`、`Day013/Q-013-V1「海」=海`、`Day041/Q-041-V2「医学」=医学`。
- 另有 `answer literally in prompt` 子串命中 67 例，其中 9 例为误报（如「何」的答案「什么」出现在「是什么意思」里），不算剧透。
- 对中文母语 / 朝鲜族学习者，58 题无需日语知识即可答对，占 1035 题的 5.6%。

**Q5 · 有没有重复题 — PASS**
- 全量：`qid unique 1035`、`duplicate prompt within same day 0`、跨天 qid 内嵌 day 与 `key.day` 一致（`qid-embedded day != key.day: 0`）。

**Q6 · `rnd.sample` 是否可能取到与正确答案同义/相同的中文释义（双答案） — PARTIAL（`QUIZ-MEANING-DUP-RISK`）**
- 池子实测：`vocab meaning_zh duplicate groups 133 total words involved 281`（我/什么/医生/明天/星期一 … 各 2）；`grammar meaning_zh duplicate groups 6 total involved 13`。
- `quiz_v5.py:25` `dict.fromkeys` 去重 + `:28` `opts[:4]` 截断、**不补齐**。因此：
  - **完全相同字符串** → 被去重，**不产生双答案**，但选项数从 4 降到 3（判分仍唯一，学生选那个字符串就算对，因为 `fnv(answer)` 相同）；
  - **近义不同字符串**（如「我」vs「本人」）→ 两个都保留，认知上歧义，但 `h` 只匹配一个，客观题仍单答案。
- 本轮 1035 题恰好未触发词义/语法题去重（3 个短选项全在汉字题），属种子侥幸；换种子或题库顺序即会成批触发。用户所问「导致双答案」的准确答案是：**不会双答案，但会少选项 / 有认知歧义**。

**Q7 · `dict.fromkeys` 去重后不足 4 个选项会怎样 — PASS→实际 FAIL（`QUIZ-KANJI-3OPT`）**
- 答案：**不报错，直接输出 3 个选项**，前端照常渲染 3 个 radio，`oh` 也只有 3 项。
- 实测 3 题：`Day053/Q-053-K-c26cfe36e070`（青，opts キョ/カイ/セイ）、`Day098/Q-098-K-1d36e1e697be`（神）、`Day120/Q-120-K-58ae11d0c4d8`（苦）。
- 根因：`quiz_v5.py:50` `rnd.sample(..., 8)` 后按 `:52` `r not in (k.onyomi + k.kunyomi)` 过滤，8 个候选里能留下的不足 3 个；`add()` 不补齐。汉字题干扰项来源是「其他汉字的首音读」，多个汉字音读相同（如 コウ/セイ）时去重又少一项。

**Q8 · 汉字读音题：取 `(onyomi or kunyomi)[0]`，干扰项是否也是该字合法读音（双答案） — PASS**
- 证据：`quiz_v5.py:44-57`。`correct = (k.onyomi or k.kunyomi)[0]`；`:52` 过滤条件 `r not in (k.onyomi + k.kunyomi)` 保证**干扰项不属于该字的任何合法读音**；同时 `correct` 本身在 k 的读音集里，任何与 `correct` 字符串相同的候选也被过滤。
- 全量 1035 题每题恰好 1 个正确索引（`h/oh/answer-in-options problems 0`），无双答案。隐患只是「题目问『一个常用读音』但该字另有训读未列入选项」，属题干措辞，不产生双答案。

**Q9 · 语法题 `meaning_zh` 做选项，不同语法是否相同释义 — PARTIAL（`QUIZ-MEANING-DUP-RISK` / `CURR-GRAMMAR-DUP`）**
- 6 组 13 条完全相同释义（见 C6）。`quiz_v5.py:60-61` 从 `grammar.values()` 随机抽 3 个，若抽到与答案同释义的语法，`dict.fromkeys` 去重 → 选项变少；本轮未触发。判分按哈希仍唯一。

**Q10 · `assessment_v6.build_for_day` 替换部分题是否破坏课程对齐 — FAIL（`QUIZ-ASSESS-REPLACE`）**
- 证据：`quiz_v5.py:116` `qs = qs[:6-len(assessment)] + assessment` 保留的是 `build_quiz` **头部**题；而 `build_quiz` 顺序为 `[V0,V1,V2,K,G,V5]`。
- N=1（21 个 weekly 日）→ 保留 `VVVKG`，丢第 6 道词汇题；N=3（3 个 stage + 3 个 self_check 日）→ 只保留 `VVV`，**汉字题 K 与语法题 G 全部被丢**。
- 实测题型分布：`Day007 weekly = VVVKGA`、`Day045/095/110/130/132/148 = VVVAAA`（Day110/148 再 +LLL）、`Day001 diagnostic = DDDKGV`。
- 命令输出：`days with 2 grammars but 0 grammar question: [45, 95, 110]`、`days with new kanji but 0 kanji question: 6 [45,95,110,130,132,148]`、`grammar questions per day dist {1:144, 0:6}`、`kanji questions per day dist {1:144, 0:6}`。
- 这 6 天仍被 `finish-day` 要求「当天题目全有成绩 + 正确率 ≥70%」，但当天新语法/新汉字一道题都没考。

**Q11 · 每日 6 题对新条目的覆盖 — PARTIAL（`QUIZ-GRAMMAR-FIRST-ONLY`）**
- 证据：`quiz_v5.py:58` `for gid in gids[:1]`、`quiz_v5.py:44` `for kid in kids[:1]`。
- 命令输出：`grammar ids quizzed 144 of 276, never 132`；`kanji ids quizzed 144 of 620, never 476`；`vocab ids quizzed 570 of 2700`。
- 6 题无法覆盖每天约 20 个新条目属合理取舍；但教学编排覆盖 100%、评估覆盖仅 52%/23%/21%，且 `curriculum_v5.py:222` completion 文案「当天客观题全部作答且正确率 ≥70%」易被理解为「6 题代表当天全部新内容」。属设计取舍 + 契约落差。

### 2.3 听力 3 题（3 项：PASS 1 / PARTIAL 1 / FAIL 1 — 累计 FAIL 6）

**L1 · 抽 10 篇（实抽 12 篇）核题目能否从 `audio_text`/`text_ja` 推出、答案唯一、选项合理、题干不剧透 — PASS**
- 抽取：Day47 M0114、Day50 M0115、Day52 M0116、Day54 M0117、Day57 M0118、Day59 M0119、Day61 M0120、Day64 M0121、Day66 M0122、Day68 M0123、Day110 M0096、Day150 M0113。逐篇原文与 3 题见 §5.2。
- 全量：`45*3 = 135` 题，`answer not in options 0`、`len(options)!=4 0`、`dup options 0`（`OPTIONS UNIQUENESS ... issues 0`）；`answers NOT literally present in audio_text/text_ja: 20` 全部是合理改写（如「まとめて買ってある」← 原文「まとめて買ってあります」、「小さかったから」←「少し小さかったので」、「市の窓口への予約」←「市の窓口に予約しなければなりません」），均可从原文推出。
- 干扰项质量良好：原文提到的旧地点/被否定项都被用作干扰项（如 M0114 Q1「駅の東口」、M0120 Q3「包丁と鍋」、M0122 Q3「問題用紙」）。
- 听力题 `listening_quiz`（`quiz_v5.py:88-103`）**不设 passage**，原文通过 `build_v5_site.py:514` 的 `<details id="transcript">` 单独提供且打开计为提示，符合听力题不剧透的要求。

**L2 · 45 篇素材唯一性 / 原创度 — PARTIAL（`LISTEN-TEMPLATE`）**
- `material_ids total 45 uniq 45 dups []`；但 `distinct templates 9 of 45 materials`，即 **9 个标题模板 × 5 变体**（待ち合わせ / 図書館の案内 / 買い物の交換 / 病院の予約 / 会社の研修 / ホテルの荷物 / 料理教室 / ごみの日 / 試験の変更），仅改 2 个关键值。
- `Q3 answer repeated across days`：9 个答案各出现 5 次（まとめて買ってある / 一週間以内 / 小さかったから / 十五分前 / 筆記用具 / 番号札 / エプロンとタオル / 市の窓口への予約 / 解答用紙）。`M0034` 与 `M0057` 的 `audio_text` 逐字相同（均未被选中）。
- 题目本身逻辑无误，属内容原创度 / AI 草稿边界。

**L3 · 听力素材难度与学习阶段匹配 — FAIL（`CURR-LISTEN-LEVEL`）**
- 证据：`curriculum_v5.py:151-157` `listening_pool = sorted(..., key=lambda m: (m.get("level","N4"), m["id"]))`，字符串序 `"N3" < "N4"`，故 N3 素材先分配给早期听力日。
- 命令输出：`level values in pool: {N3:27, N4:18}`；`day_level=N4 material_level=N3 : 21 days`、`day_level=N3 material_level=N4 : 18 days`、`day_level=N3 material_level=N3 : 6 days`；`N3-material days range: 47..108`、`N4-material days range: 110..150`。
- 例：Day047（P2 / N4 阶段）用 `M0114《待ち合わせ・3》level=N3`；Day110（P4 / N3 阶段）用 `M0096《待ち合わせ・1》level=N4`。与 0 基础→N3 递进相悖，影响 39 天。

### 2.4 周测 / 阶段题 39 道（5 项：PASS 2 / PARTIAL 2 / FAIL 1 — 累计 FAIL 7）

脚本基线：`scripts/assessment_v6.py`（读 `knowledge/seeds/assessments.jsonl`，39 行）、`quiz_v5.py:113-116`。已逐行读完全部 39 题。

**A1 · 39 题 `passage` 与 `prompt` 对应、`answer` 在 `options`、歧义、日语自然度 — PASS**
- 命令输出：`count 39`、`per-day dist {1:21, 3:6}`、`issues 9`（9 个全是 A4 标签不一致，其余 0）；即 `passage`/`prompt` 非空、`len(options)==4`、`answer in options`、无重复选项 **全部通过**。
- `answer in passage` 15 例（如 A014-1「十分」、A028-1「傘」、A077-1「二階の窓口」）是阅读理解题的正常信息检索，不算剧透。
- 推理题质量良好：A007-1（今日日曜 + 明日の朝 → 月曜日の朝）、A126-1（3 人 - 1 人 = 2 人）、A147-1（平日且非月曜休馆 → 火曜日）、A091-1（時間があれば → 安いスーパー）。
- 日语自然度：A045-3「毎朝コーヒーを飲んでから…」、A110-3「鍵を忘れたため…」、A132-3「忘れないように…」、A148-3「遅れるおそれがあります」均自然；A095-3「雨が降るので、窓を閉めてください」、A130-3「雨がやんだら、出かけましょう」可接受。

**A2 · `targets` 是否合理 — PARTIAL（`ASSESS-TARGETS-COARSE`）**
- `targets values {('reading_information',):33, ('grammar_context',):6}`；`knowledge_ids` 恒为 `[]`（`assessment_v6.py:41`），注释 `assessment_v6.py:15-16` 明确「理解题是练习证据，不推断知识卡已掌握；短练习不是 JLPT 分数或模考」。粗粒度但为有意边界。

**A3 · 阶段日 3 题是否共用材料却只给一段 passage — PARTIAL（澄清 + `ASSESS-SHARED-PASSAGE`）**
- 实测：**Day45 / Day95 是 3 题 3 段不同 passage**；**Day110 / Day130 / Day132 / Day148 是 3 题 2 段 passage**（前 2 题共用一段，第 3 题是独立填空题）。命令输出：`Day110: 3 questions, 2 distinct passages`（另 3 天同）。
- 关键澄清：**不是「只给一段 passage」**。`assessment_v6.py:39` 给每题都写完整的 `passage` 字段，`public_question` 保留 `passage`，`build_v5_site.py:226` 每题渲染一个 `.passage` 块 → 共用材料时同一段文字被**重复渲染 2 次**。一材料多问是 JLPT 读解标准设计，不该改设计，只改呈现。

**A4 · 标签与 curriculum 一致 — FAIL（`ASSESS-LABEL-MISMATCH`）**
- `assessment label values {weekly:21, stage:9, mock:9}`；`A110-1/2/3`、`A132-1/2/3`、`A148-1/2/3` 共 9 条标 `mock`，而 `curriculum_v5.py:210` 对 Day110/132/148 标 `self_check`。不影响出题（`build_for_day` 只按 `day` 过滤），但分类口径不一致。

**A5 · 39 题是否覆盖全部 assessment 日 — PASS**
- `weekly days=21 missing_questions=[] counts={1:21}`；`stage days=3 ... counts={3:3}`；`self_check days=3 ... counts={3:3}`。零缺失、零多余。
- 单题小问题（均 low、AI 草稿边界）：`ASSESS-A130-3-OPTIONS`（正确项「ら」是单假名，其余是完整助词，颗粒度不一致）、`ASSESS-A148-3-SPOILER`（prompt「遅れる可能性を表す」点明语义，轻微剧透「おそれ」）、`ASSESS-A021-1-DISTRACTOR`（「料理を作る」「泳ぐ」与图书馆场景无关，可一眼排除）。

### 2.5 完成门控（3 项：PASS 2 / PARTIAL 1 / FAIL 0）

脚本基线：`scripts/nh80.py:622-679 cmd_finish_day`、`:444-519 cmd_import_web`、`scripts/learning.py`。

**G1 · `finish-day` 的 70% + 9 题是否导致「听力日必须全对才能过」 — PASS（前提纠正，`GATING-70-LISTEN`）**
- `nh80.py:648`：`passed = (acc is not None and acc >= 0.70 and bool(expected) and expected <= {x[qid] for x in scored} and output_confirmed)`。
- `expected = set(d["question_ids"])`（`nh80.py:637`），来自 DB `curriculum_days`；实测 `curriculum_days question_ids count dist {6:105, 9:45}`，与 `curriculum.json`、`generated-key.json` 完全一致（`DB question_ids vs curriculum.json: db-only=0 cur-only=0`）。
- 阈值数学（命令输出）：`6 questions: need >=5 correct (0.833); max wrong=1`、`9 questions: need >=7 correct (0.778); max wrong=2`。
- 结论：**「9 题错 3 题 = 66.7% 不通过」属实；但「听力日必须全对才能过」不成立**——听力日允许错 2 题，相对容错同为 30%、绝对容错反而多 1 题。用户描述的前提有误。

**G2 · 是否对听力日不公平 / 输出验收耦合 — PARTIAL（`GATING-70-LISTEN` / `GATING-HINTED`）**
- 真不公平点：`expected <= scored`（任一题未答即不通过，9 题比 6 题多 3 个「必答」约束）+ 听力题更难（原创合成 TTS、无真人音频）+ 45 个听力日恰好多 3 题。
- 教师验收耦合：**合理**。`output_confirmed` 来自 `output_reviews` 表（`nh80.py:646-647`），与 `acc`、`expected` 是 AND 关系；`learning.py` 的题目成绩与教师验收分离（开放题 `correct=NULL` 挂起、`nh80.py:630` pending 列表）。
- `hinted`：看 transcript 只被记录（`nh80.py:481`），`server_correct` 仍由 `_grade_objective` 照常判分（`nh80.py:487`），`finish-day` 的 acc 只看 `correct`。属「计为提示学习」的诚实性设计取舍，不是 bug。
- 当前 DB 状态：`sessions=1, attempts=0, fsrs_cards=0, output_reviews=0` —— 系统刚 build 完、尚无真实学习记录，门控只能静态审查，无法用真实作答验证。

### 2.6 答案表 `generated-key.json`（3 项：PASS 2 / PARTIAL 1 / FAIL 0）

脚本基线：`scripts/nh80.py:243-271 _build_v5`（`:250-266` 构建 keys、`:270` 写文件）。

**K1 · 是否覆盖全部 150 天题号 / 有无孤儿题号 — PASS（对当前课程）/ PARTIAL（对 DB 历史，`KEY-ORPHAN-DB`）**
- 命令输出：`key count 1035`、`key per-day-count dist {6:105, 9:45}`、`key-only (orphans not in curriculum): 0`、`curriculum-only (not in key): 0`。
- 重新生成 1035 题：`qid matches key 1035`、`answer matches key 1035 mismatches []`、`key day mismatch 0`；`DB raw.answer vs key mismatches 0`。
- **但**：`data/state.db` 的 `questions` 表有 **2023 行**，比 key 多 **988 条**：`945 条 Q0001 旧 seed 题库`（`knowledge/seeds/questions.jsonl`）+ `43 条旧 build 的 Q-xxx 题`（如 `Q-001-V0-77b4d867c188`，当前 key 里 Day1 的 V0 已被诊断题替换）。`nh80.py:451` 从全表建 `qmap`、`:464` `wrong_day` 用 `raw.get("day", data["day"])` 兜底，945 条无 day 的旧题会被默认接受为当天题。正常作答碰不到这些题，但输入校验留了口子。

**K2 · day 是否匹配 — PASS**
- `key day mismatch 0`（重新生成题的 day 与 `key[qid]["day"]`）；`qid-embedded day != key.day: 0`（qid 内嵌的 3 位天数与 key.day）；`key type values {mcq:1035}`。

**K3 · 私有答案是否泄露到公开页 — PASS**
- `web/data/day-047.json` 的 quiz 与听力题 keys 均为 `['h','oh','options','prompt','qid']`，无 `answer`（详见 Q3）。

---

## 3. 三类问题分类

### 真 bug（应修）
`CURR-LISTEN-LEVEL`、`QUIZ-ASSESS-REPLACE`、`CURR-REVIEW-FSRS`、`CURR-GRAMMAR-DUP`、`QUIZ-KANJI-3OPT`、`QUIZ-SAME-FORM-SPOILER`、`QUIZ-MEANING-DUP-RISK`、`CURR-GRAMMAR-JUJU-ORDER`、`ASSESS-LABEL-MISMATCH`、`KEY-ORPHAN-DB`、`CURR-LISTEN-46-BOUNDARY`、`CURR-LESSON-CORE-3`、`CURR-DUP-AUDIO`。

### 设计取舍（不该改，见 §4）
`QUIZ-GRAMMAR-FIRST-ONLY`（6 题抽样上限）、`ASSESS-TARGETS-COARSE`、`ASSESS-SHARED-PASSAGE`（一材料多问）、`GATING-70-LISTEN`、`GATING-HINTED`、`CURR-SPRINT-WEIGHT`、`CURR-PAGE-42-47`（页面 42 = 60 - 会话 18 的自洽口径）、public_question 只留哈希、`evidence_only` 空 knowledge_ids。

### AI 草稿边界（内容质量，非代码错误）
`CURR-EXAMPLE-KANJI`、`LISTEN-TEMPLATE`、`ASSESS-A130-3-OPTIONS`、`ASSESS-A148-3-SPOILER`、`ASSESS-A021-1-DISTRACTOR`；`curriculum_v5.py:236` meta 已自述「中文释义与例句翻译为 AI 草稿」、`assessment_v6.py` 全部题 `review_status="ai_draft"`。

### 待核实（low，不据此改代码）
`CURR-PAGE-42-47`（任务描述的「听力日 47」在代码/页面/现有报告中均无对应）、`QUIZ-FNV-COLLISION`（NFKC 归一化潜在哈希碰撞，1035 题无实例）、`CURR-EXAMPLE-KANJI` 的 555/714 统计为近似上界。

---

## 4. 设计取舍：哪些不该改

1. **150 天全量排入 2700 词 / 276 语法 / 620 汉字且无重复**（C1/C3/C4）：覆盖与先修拓扑均经自动校验通过，编排正确。
2. **语法每天 2 条（126 天）+ 1 条（24 天）= 276**，且 `prerequisites` 严格更早、同天不互依：`curriculum_v5.py:103-140` 的拓扑分配正确，不该动。
3. **core / extension 分层 + 页面「包含选学拓展」复选框**：必学 16（听力日 11）、其余 546 词选学，是 60 分钟约束下的合理取舍。
4. **blocks 60 = 网页 42 + 线下会话 18**：页面 section 合计 42（常规与听力日都自洽），会话不计入网页。任务描述的「听力日 47」无代码依据（C9）。
5. **周测/阶段题是「替换」不是「追加」**，每天题数恒 6（听力日 +3 = 9）：不加题、不超时（C10）。要修的是替换时丢 K/G 题，不是替换机制本身。
6. **`public_question` 只保留 `qid/prompt/options/h/oh/passage`**，剥离 `answer/rationale/knowledge_ids/targets`；前端用 FNV 哈希判分。「哈希可被比对反推」是前端方案的固有局限，注释已声明目的是「不把答案明文写进 HTML」，接受该取舍。
7. **公开页复习词 = 静态 T+1/3/7 快照，权威到期队列放私人会话**（`build_v5_site.py:404` 注释 + 页面 hint）：隐私边界合理，**不该改架构**；要修的是快照只含词汇、且与 `learning.due_queue` 完全脱节（C7）。
8. **一材料多问（共用 passage）**：JLPT 读解标准设计；不该改题目结构，只改页面重复渲染（A3）。
9. **assessment 题 `knowledge_ids=[]` / `evidence_only`**：`assessment_v6.py:15-16` 明确「理解题是练习证据，不推断知识卡已掌握」，且 targets 粗粒度、非 JLPT 分数，属有意边界（A2）。
10. **统一 70% 阈值 + 全部作答 + 教师 `output_review` 三者 AND**（`nh80.py:648`）：完成契约明确，数学上听力日允许错 2 题；公平性讨论属调优，不是 bug（G1/G2）。
11. **打开 transcript 计 `hinted` 但不扣分**：诚实记录、不额外惩罚（G2）。
12. **45 个听力日、每篇 3 题、原创 TTS 合成语音（非真人）**：`curriculum_v5.py:190` 已注明「时长为估计，非真人音频」，`build_v5_site.py:550` 指向官方真人资源；架构取舍，接受。
13. **`finish-day` 以 `status=finished AND passed=1` 计完成天数**（`nh80.py:63-70`）：状态契约清晰。

---

## 5. 抽样逐题核验记录

### 5.1 Day 1 / 7 / 45 / 47 / 90 / 150 全部题

| Day | 题型序列 | 逐题结论 |
|---|---|---|
| 001 | `D D D K G V` | 3 道假名/助词诊断（きゃ→kya、ざ→za、は→wa）+ 汉字「日」→ニチ + 语法「N は N です」→…是… + 词汇「こんにちは」→你好（白天问候）。均 4 选项、唯一正确、无剧透 |
| 007 | `V V V K G A` | 医者/電話/旅行词义、人→ジン、と（并列/共同/引用）→和…、A007-1 读解（月曜日の朝，需推理）。全部合格 |
| 045 | `V V V A A A` | 会話/帰り/科学词义 + A045-1/2/3。**无 K、无 G**（Q10） |
| 047 | `V V V K G V + L L L` | 客/急/急行/教育、族→ゾク、〜てくれる→（别人）为我做…；听力 3 题 南口/十時/まとめて買ってある。全部合格 |
| 090 | `V V V K G V` | 汚染/おそらく/恐れる/恐ろしい、容→ヨウ、うちに→趁着…。全部合格 |
| 150 | `V V V K G V + L L L` | 離れる/羽/幅/母親、腹→フク、〜かける→…了一半；听力 3 题 火曜日/三階の教室/解答用紙。全部合格 |

### 5.2 抽 12 篇听力（逐篇见 §2.3 L1）

每篇 3 题均可由 `audio_text` 唯一推出；干扰项同层级且常取自原文被否定/被更改的信息；题干为「どこで / 何時に / どうしますか」等，不剧透。`listening_quiz` 不给 passage，原文在 `<details id="transcript">` 中且打开计提示。

### 5.3 39 道周测/阶段题

`A007-1 … A148-3` 全部读毕：`passage` 与 `prompt` 对应、`answer` 在 `options`、4 选项无重复、日语自然。6 道语法填空题（A045-3 飲んで / A095-3 ので / A110-3 ため / A130-3 ら / A132-3 ように / A148-3 おそれ）答案唯一。问题仅 A4 标签不一致 + 3 道单题 low 质量项 + A3 共用 passage 重复渲染。

---

## 6. 可复现证据（只读命令输出摘录）

```
days 150 | seed counts vocab/grammar/kanji/materials 2700 276 620 140
vocab: total=2700 uniq=2700 missing=0 extra=0 dup_keys=0
grammar: total=276 uniq=276 missing=0 extra=0 dup_keys=0
kanji: total=620 uniq=620 missing=0 extra=0 dup_keys=0
core-limit violations: 0 []   | extension total 546 days_with_ext 147
blocks sum dist {60: 150}
prereq-not-earlier violations: 0 [] | same-day mutual prereq days: 0 []
jlpt first-appearance day {'N5': 1, 'N4': 33, 'N3': 69}
review len dist {0:1, 4:2, 8:4, 12:143} | review ids that are grammar/kanji: 0
assessment dist {'diagnostic':1,'none':122,'weekly':21,'stage':3,'self_check':3}
listening days 45 first [47,50,52,54,57,59] last [138,141,143,145,148,150]
key count 1035 | key per-day-count dist {6:105, 9:45}
key-only (orphans not in curriculum): 0 | curriculum-only (not in key): 0
total generated 1035 | qid unique 1035 | answer matches key 1035 | key day mismatch 0
option count dist {3:3, 4:1032} | h/oh/answer-in-options problems 0 []
SHORT(<4) : Day053/Q-053-K, Day098/Q-098-K, Day120/Q-120-K
questions where target word surface == its Chinese answer: 58
vocab meaning_zh duplicate groups 133 (281 words) | grammar 6 groups (13)
grammar ids quizzed 144 of 276 (never 132) | kanji 144 of 620 (never 476)
Day045/095/110/130/132/148 kinds = VVVAAA | Day007 = VVVKGA | Day001 = DDDKGV
all 150 pages section sums: {42: 150} | header: '网页 42 分钟 · 会话 18 分钟'
day_level=N4/material_level=N3 : 21 days | day_level=N3/material_level=N4 : 18 days
distinct templates 9 of 45 materials | Q3 answer repeated 5x for 9 answers
39 items: count 39, per-day {1:21,3:6}, issues 9 (all label mismatch)
6 questions: need >=5 correct; 9 questions: need >=7 correct
DB: curriculum_days 150 rows, questions 2023 rows, key 1035, orphans 988 (945 old seed + 43 old build)
DB raw.answer vs key mismatches 0 | DB question_ids vs curriculum.json db-only=0 cur-only=0
```

---

## 7. 待核实项（low，均已在 JSONL 标注）

1. `CURR-PAGE-42-47`：任务描述「页面渲染分钟合计 42（听力日 47）」——实测 150 页全 42，现有 `reports/*.md` 无「47 分钟」表述，可能为旧版本或口误。
2. `QUIZ-FNV-COLLISION`：`fnv` 的 NFKC + 去空白归一化理论上会让不同选项哈希相同；1035 题无实例。
3. `CURR-EXAMPLE-KANJI`：555/714 的「例句含未教汉字」为近似上界（仅比对 620 汉字表首次教学日），不排除教材惯例「先整句后拆字」。

---

## 8. 交付与纪律

- 输出 1：`reports/v7_curriculum_quiz_review.md`（本文件）
- 输出 2：`reports/evidence/v7_curriculum_issues.jsonl`（26 行，每行含 `area/id/severity/problem/current/fix/reason`，`fix` 均具体到函数与字段）
- 未修改 `scripts/*`、`knowledge/seeds/*`、`curriculum/*`、`web/*`、`deploy/*`、`data/state.db`；未执行 `git commit`、未运行任何生成脚本写回。
- 分析脚本均通过 `python3 - <<'PY'` 以 stdin 只读执行，未在项目内创建临时文件。
