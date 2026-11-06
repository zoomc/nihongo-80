# 课程来源与理论支撑审计（2026-11-06）

> 回答的问题：**这 80 天教学计划与内容，是随机拼的，还是有顶级教材 / 二语习得理论支撑？**
> 结论：**不是随机的**（确定性、可复现、有强校验），但**也不是教材理论推导出来的课纲**。
> 扎实的是「记忆调度与练习机制」，薄弱的是「教什么、按什么顺序教、场景与文案」。

本文件所有数字均为本次在真实项目文件上跑出的统计，不引用记忆或推断。

---

## 1. 三层证据

### A. 有真实外部依据，且确实落到了代码

| 依据 | 出处（已核实） | 落地位置 |
|---|---|---|
| FSRS-6 记忆模型 | 官方 `py-fsrs 6.3.1`（MIT，vendor 在 `scripts/vendor/`）；`awesome-fsrs/wiki/The-Algorithm` 21 个默认参数 | `learning.scheduler()`、`review_card()`；`desired_retention=0.9`、`enable_fuzzing=False`；rating 1–4 映射。**公式不是本项目自造** |
| 提取练习 / 一次答对≠掌握 | Roediger & Karpicke (2006)、NAS《How People Learn II》(2018) 点名 "retrieve once then drop the item" 误区 | 五阶段门控：需 `delayed_count≥3` + ≥2 语境 + ≥7 天跨度 + `rolling_accuracy≥0.85` 才 `mastered` |
| 掌握学习阈值 | Bloom (1968) / Guskey 常用建议区间 **0.80–0.90**（Bloom 原文精确数字未核实，故标「建议值」） | `MASTERY_THRESHOLD = 0.85` |
| 交错练习的适用边界 | Brunmair & Richter (2019) 元分析：总体 g=0.42，但**词汇 g=−0.39（分块反而更好）** | 交错只用于易混语法/助词/变形；词汇与汉字走分块 + SRS |
| 可理解输入 | Krashen i+1 的不可操作化/不可证伪批评、Swain 输出假说 | 只实现为 `known_ratio 0.90–0.95` 的选材启发式，**明确声明不是理论验证** |

> 注意：`MASTERY_THRESHOLD=0.85` 之外，延迟 2 天、延迟 3 次、2 语境、7 天跨度、每日正确率 0.70、
> 9 类错误补救映射，都是**本项目工程约定**，不是文献给的数值。文档里没有把它们包装成「研究结论」。

### B. 真实调研过、但**没有进入课程生成**

| 资源 | 调研到的体系 | 实际用途 |
|---|---|---|
| IRODORI | 4 级 × 18 课、644 汉字、360–500 学时、JF Can-do 目标、词表/语法练习齐全 | **只登记在 `source_registry`**。课程没按它的课序、没用 Can-do、没用它的词表 |
| Marugoto / JF Can-do | CEFR A1–B1 分级框架 | 只作分级参照，未落到任何一天 |
| JLPT 官方 `levelsummary` | N3 能力描述原文、Reading/Listening 要点、「N3 是 N4/N5 与 N1/N2 的 bridging level」 | 只用于报告里的**分数口径声明**；课程任务未据其能力描述设计，官方样题未入库 |
| Tadoku 分级读物 | Level 0–5 免费 PDF+音频，CC BY-NC-ND 4.0 | 6 条仅索引，每周 1 条延伸阅读，正文不入库 |
| JMdict / KANJIDIC | CC BY-SA-4.0，可读音/词性/释义 | **未用于词条校核** |

### C. 纯工程约定 / 模型整理，没有教材支撑

- **80 天 6 阶段**：基本照抄需求原文给的「初始分期」——而那段原文自己写着「以上只是初始建议，不要机械照搬」。
- **知识点清单**：522 条全部标 `S000 项目原创整理`，由模型按通用 N5–N3 印象生成，
  **未对照任何教材词表或权威词典**；6 条标 `needs_review`。
- **知识点顺序**：`curriculum._windows()` 的均匀铺开算法 + 语法 `prerequisites` 拓扑排序，
  是我写的工程约束，**不是任何教材的课序**。
- **评估节奏**：Day 1 / 每 7 天 / 每 20 天 / Day 40 / 60 / 80，照抄需求原文。
- **题库**：212 道原创，难度 1–5 由模型分配。
- **掌握判定的其余阈值**：见 A 的注意项。

---

## 2. 实测数据（本次审计实际跑出）

```
scene 完全匹配同一模板        80 / 80
objectives 前 4 条完全相同    80 / 80
rubric 完全相同               80 / 80
completion 骨架相同           79 / 80
distinct theme                65（其余重复）
```

JLPT 标签分布与阶段新知：

| 类别 | N5 | N4 | N3 |
|---|---|---|---|
| 词汇 | 141 | 9 | **0** |
| 语法 | 34 | 18 | **3** |
| 汉字 | 69 | 1 | **0** |

| 阶段 | 天数 | 新词 | 新语法 | 新汉字 |
|---|---|---|---|---|
| P1 Day 1–10 | 10 | 57 | 8 | 23 |
| P2 Day 11–25 | 15 | 84 | 12 | 35 |
| P3 Day 26–45 | 20 | 8 | 16 | 12 |
| **P4 Day 46–65（标称「N3 高频」）** | 20 | **1** | 16 | **0** |
| P5 Day 66–75 | 10 | 0 | 3 | 0 |
| P6 Day 76–80 | 5 | 0 | 0 | 0 |

---

## 3. 两个必须披露的硬伤

### 3.1 「N3 阶段」名不副实

P4 标称「N3 高频知识、听力及阅读进阶」，但 20 天里只引入 1 个新词、0 个汉字，
16 条语法里绝大多数仍是 N5/N4 标签。**Day 50 的新词与汉字都是空的**，当天只有 1 条语法 + 6 道题。
原因：种子库几乎没有 N3 条目，而 `_windows()` 把 N3 铺在 Day 51–72，实际填不满。

更根本的是覆盖率口径漏洞：`validate` / `coverage_report.md` 只检查「每个知识点是否至少被引入一次」，
**没有检查分级目标是否兑现**，所以 100% 覆盖率掩盖了这个偏科。

### 3.2 文案是模板，不是教学设计

80 天的场景句、前 4 条能力目标、评分准则、完成条件骨架完全一致，只有主题词不同。
例如 Day 50 场景是「在「父の仕事」场景中使用当天表达完成一次真实交流（work）。」——
由素材 title + topic 拼出。这能跑、能指向真实知识点，但**不能称为 80 天逐课设计**。
`curriculum/coverage_report.md` 已诚实写了「不是 80 篇人工逐课精修教材」，但没有量化到这个程度。

### 3.3 学时事实（最硬的一条）

**80 天 × 60 分钟 = 80 学时**；而 Irodori 官方 FAQ 自述全四册需 **360–500 学时**，
且 Starter–Elementary 2 才相当于 **JLPT N4**。
因此「80 天接近 N3」在学时量级上就不成立。项目 README 已写「首轮周期，不是第 80 天必达 N3 的成绩承诺」，
但课程阶段名（P4「N3 高频」）仍在暗示这个目标，属于口径不一致。

---

## 4. 如果要变成真正的教材支撑，具体可做什么

资源与许可已在 `research/source_registry.md` / `source_registry_official.md` 核实，均可合法使用：

1. **按 Irodori 重建大纲**：下载 Starter / Elementary 1–2 / Pre-Intermediate 的免费 PDF 与词表，
   用其 **JF Can-do 目标 + 课序 + 场景** 重排 80 天，得到真实的「场景 → 句型 → 词汇」序列。
   许可：官方自定义 Terms of Use，允许私用与学校教育、允许自制教材（须免费并注明来源），
   **禁止商用、禁止再分发原 PDF、插图不得改作**。
2. **JMdict / KANJIDIC 校核**（CC BY-SA-4.0，需署名）：逐条核对读音、词性、释义，
   消掉 6 条 `needs_review`，把 `S000` 升级为可追溯来源。
3. **JLPT 官方 N3 锚定**：用 `levelsummary` 的 Reading/Listening 能力描述 + 公开样题题型
   重做评估蓝图（样题只作对齐与短句引用，**不入库、不复制原题**）。
4. **Tadoku 分级阅读**（CC BY-NC-ND 4.0，署名 NPO多言語多読，禁改作发布）：
   按 Level 0–5 建真实分级阅读索引，并用它实测 `known_ratio`，而不是模型自填。
5. **修正目标口径**：把阶段名改为「N5 扎实 → N4 核心 → N4/N3 桥接入门」，
   或明确写出 80 学时与 360–500 学时的差距，不再暗示 N3 达成。

### 明确不该做的

- 再让模型「生成一批 N3 词」来补标签：只会把偏科从「缺内容」变成「缺依据」，
  仍不是教材支撑，且可能引入不准的读音。
- 把 `0.85` 之外的工程阈值事后包装成文献结论。
- 因为覆盖率报告 100% 就宣称大纲合格。

---

## 5. 审计结论

| 维度 | 评价 |
|---|---|
| 随机性 | **不是随机**：种子固定、拓扑排序、10 类强校验、可复现重建 |
| 记忆与练习机制 | **有真实依据**：官方 FSRS + 已核实的学习科学结论，且落到确定性代码 |
| 知识点内容 | **模型整理的通用大纲**，未对照教材词表或词典，非教材支撑 |
| 课序与分期 | **工程约定 + 照抄需求初始分期**，无教材课序依据 |
| 场景 / 目标 / 文案 | **模板**，80 天高度重复 |
| 分级目标兑现 | **未兑现**：P4 标称 N3 但几乎无 N3 内容；80 学时与官方 360–500 学时差距未体现在阶段命名 |

一句话：**系统机制是认真做的，课程内容是工程拼的。**
这份审计本身是项目的一部分，不是辩解；修复路径见第 4 节。

---

## v2 修复记录（2026-11-06）

> **本节是 v2 修复后的追加记录**。以上 §1–§5 是 **v1 审计的历史证据**，其中的结论与数字（522 条、
> 6 条 `needs_review`、212 道题、P4 仅 1 新词 / 0 汉字、80/80 模板一致等）**原样保留、不改写**，
> 以便对照修复前后。修复的方法依据见 `research/nh80_framework.md`（自研 **NH80 高频压缩习得法**，v2）；
> 课程仍**不照抄任何教材课序**，教材只贡献目标格式 / 能力标准 / 题型边界 / 素材分级原理。
> 下列指标均来自本次实际运行的 `python3 scripts/nh80.py validate`、`python3 tests/test_all.py`
> 与 `SELECT COUNT(*) FROM relations` 等真实查询，不引用记忆或推断。

### 对应 §3.1「N3 阶段名不副实」—— 已修

- **修法**：种子库 522 → **877 条**，补齐 N4 / N3 内容（真实分布：260 词 = N5 141 / N4 49 / N3 70；
  85 语法 = N5 34 / N4 26 / N3 25；140 汉字 = N5 69 / N4 36 / N3 35；332 题、60 素材）。
  `scripts/curriculum.py` 改为**分级窗口配额** `LEVEL_WINDOWS = {N5: 1–25, N4: 26–45, N3: 46–65}`
  与 `_windows_by_level()`（窗口内按 `frequency` 降序 + id 稳定排序），N3 内容集中在 P4（Day 46–65）兑现；
  语法用 `_topo_days_by_level()` 在分级窗口内做 `prerequisites` 拓扑迭代修正。
  新增 `validate.level_delivery` 强校验（P3 的 N4 ≥ 20 项、P4 的 N3 ≥ 40 项，且 P4 不得出现几乎无新知的天），
  堵住原文指出的「只查覆盖率、不查分级目标是否兑现」的口径漏洞。
- **真实指标**：`validate` → `level_delivery = {P1 N5:99, P2 N5:145, P3 N4:111, P4 N3:130}`；
  `error_count=0`、`warnings=[]`；5 类覆盖率 100%（260 / 85 / 140 / 332 / 60 全部 `used`，`unused_count=0`）。
  关系边 `SELECT COUNT(*) FROM relations` = **4983**（v1 为 2820）。
- **自动化测试**：`python3 tests/test_all.py` **19/19 PASS**（新增 `test_01b_framework_delivery`：
  断言 P4 的 N3 ≥ 40、P3 的 N4 ≥ 20、`distinct_objectives` ≥ 70、80 天都有 `can_do` / `focus`）。

### 对应 §3.2「文案是模板，不是教学设计」—— 已修

- **修法**：新增 `CANDO_BANK`（6 阶段真实任务池）按阶段内顺序取任务，保证 Day 1 从「初次见面」起步、
  不会轮到「时间安排」这类超纲任务；`OBJECTIVE_POOL` 10 条按日轮换并插入当天真实词 / 句型 / 主题，
  `RUBRIC_POOL` 5 种按日轮换，`FOCUS_CYCLE` 五项轮换，素材英文 topic 经 `TOPIC_ZH` 转中文；
  每天新增 `can_do` / `focus` / `scene_tag` 字段，`scene` / `objectives` / `rubric` / `completion` 差异化生成。
  `validate.teaching_design` 对 distinct 数量设下限、低于下限直接判失败，防止退回 80 天共用一套话。
- **真实指标**：`validate` → `teaching_design = {distinct_scene: 78, distinct_can_do: 77,
  distinct_objectives: 80, distinct_rubric: 66, distinct_theme: 80}`；
  `curriculum.json` 中 80/80 天 `can_do` / `focus` / `scene_tag` 齐全；
  Day 1 `scene_tag=初次见面`、`can_do=用「N は N です」向对方介绍自己并确认对方姓名`、
  `assessment=diagnostic`、8 道零基础诊断题（不超纲）。

### 对应 §3.3「学时事实」—— 口径已披露，结论不变

80 学时 vs 官方 360–500 学时的差距已在 `README.md` 与 `research/nh80_framework.md` §2 明确写为
「压缩冲刺路径 / 不等于 JLPT 官方学时标准 / 不承诺合格分数」。这是**口径披露，不是修复**：
学时量级本身仍不足以「达 N3」，因此该项列入下方「仍未落地」。

### 明确仍未落地（避免把上述修复写成全部完成）

1. **JMdict / KANJIDIC 逐条校核**：877 条仍标 `S000 项目原创整理`，**14 条**标 `needs_review`
   （v1 为 6 条），未逐条对照权威词典的书写 / 假名 / 词性 / 义项，仍是最大内容质量风险。
2. **官方样题未入库**：JLPT 官方 N3 样题只作题型与能力对齐、只存 `index_only` 索引，不复制原题、
   不分发；本地题库 332 题全部为项目原创模拟题。
3. **JLPT 分级标签非官方**：`N5/N4/N3` 是项目自定分级标签，JLPT 不公布官方词汇 / 语法清单，
   不得当作官方分级引用。
4. **80 学时口径**：压缩冲刺路径，不等于官方学时标准，不承诺合格分数 / 第 80 天必达 N3；
   本地正确率是原创模拟题过程指标，不是 JLPT 标准分、不可换算。

> 线上站点仍为 https://nihongo80.cmjfire.workers.dev （v2 内容重新部署中，本文档不记录部署结果）。

---

## v3 页面可用性修复（2026-11-07 追加）

> **本节只追加**：以上 §1–§5 是 v1 审计的历史证据，「v2 修复记录」是 v2 的修复记录，
> 其中的数字与结论（522 条、6 条 `needs_review`、212 道题、P4 仅 1 新词 / 0 汉字、
> 4983 关系边等）**全部原样保留、不改写**。
> 本节记录的是与「教什么 / 按什么顺序」**不同层面**的问题：v1/v2 的**每日网页把内容做成了系统报表**，
> 学员首屏看不到可学日语。v3 已上线，部署记录见 `docs/CLOUDFLARE.md`。

### 问题是怎么被发现的（不是审美，是实测）

- `research/ux_audit.md`：学员视角审计，PC 1440 / 手机 390 真实截图 + DOM 探针。
  实测**首屏前 3 屏可学日语内容 = 0%**；词汇 / 语法 / 汉字 / 素材 section 默认折叠、卡片还要翻面；
  首屏被「能力目标（教研措辞）/ 60 分钟时间块 / 3 张图表 / `diagnostic` / `FSRS` /
  `focus: listening` / `Can-do`」占满；复习只有「review 10 分 FSRS 到期项」一句话，
  不知道今天复习哪几个词；韩语对照 **0 处**；练习默认折叠且第 1 题是无参考答案的开放题。
- 根因不在引擎：§1 已确认「系统机制是认真做的」（官方 FSRS、关系图、强校验），
  `knowledge/seeds/` 里**本来就有** `romaji` / `pos` / `examples` / `notes_for_zh` / `usage` /
  `common_errors` / `compare` / `text_zh` / `rubric` / `rationale` / `expected_production` 等字段，
  但 `build_site.py` 的 `assemble_day()` 只挑了 5 个字段，页面只剩骨架；
  `app.js` 还把 `audio_text`（等于 `text_ja`）当「读音」显示，真机有 `ja-JP` 语音时 CSS 又隐藏假名。

### 修复路径（顺序依据真实教材，不照抄课序）

- `research/textbook_lesson_pattern.md`：真实下载 Irodori 官方 `X_howto_en.pdf` /
  `X_contents_en.pdf` 提取一课结构，另核实 Genki / Marugoto / JLPT 官方页；
  共同点是**先给能用的话和词，再讲规则，再练，最后自评，系统信息一律不在正文里**。
  教材只贡献「一课的呈现顺序与规格」，**课程编排仍按 `research/nh80_framework.md` 自研方法**，
  不采用任何教材线性课序（本审计 §1「课序是工程约定、无教材课序依据」的历史结论不变）。
- `docs/REDESIGN_PLAN.md` 定下 8 区块顺序、数据契约与诚实边界，并新增「执行结果（v3）」记录落实。

### 实际完成（真实指标，见 `docs/VALIDATION.md` §8）

- 课程层：每天新增 `lesson_core`（3 句真实日中对照，假名只在资料层核实后填）、
  `review_plan`（具体词 + 中文原因 + 下次 Day）、`teaching_notes`（中文难点）；
  `start-day` briefing 同步带上；80/80 天齐全，旧字段未删。
- 资料层：新增 `knowledge/ko_analogy.json`，覆盖 **85/85 语法 + 57 词**，每条含
  `hint_zh` / `caution`（「结构可借、词不能猜」）；`materials.jsonl` 补 `focus_zh` **50/50**、
  `text_kana` **12 条真实假名**（其余 38 条诚实留空），16 处 `text_ja`/`text_zh` 句数错配修到 **0**。
- 页面层：`build_site.py` 重写为 8 区块；修掉「读音=原文」「真机隐藏假名」「内容全折叠」
  「开放题无参考答案」等 bug；术语中文化；顶层 `ko_analogy` 按天裁剪，
  `day-001.json` **92,854 字节 → 23,932 字节**（统一按字节计，减少约 74%）。
- 复习闭环：新增 `learning.apply_review_rating`（`good/hard/again → 3/2/1`），
  `import-web-result` 消费 `review_ratings`；**只排期、不写 `attempts`、不改 `stage`、不判 `mastered`**，
  同会话幂等——与 §1「一次答对 ≠ 掌握」的历史结论一致，未放松门控。
- 验证：`python3 scripts/nh80.py validate` → `error_count=0`、`warnings=[]`、
  `level_delivery.P4.N3=130`、`teaching_design.distinct_objectives=80`；
  `python3 tests/test_all.py` **20/20 PASS**（含 `test_06b_review_ratings_drive_fsrs`）；
  关系边仍 **4983**（未变）；Chrome CDP 390 视口 `innerWidth=390 / scrollWidth=390`、6 张词卡、
  1 条假名行、7 个韩语对照块、25 个听按钮；PC 1440 首屏 3 句话 + 2 张完整词卡、无图表 / 术语。

### 本节不改动的既有结论

- §1–§5 与「v2 修复记录」的**全部历史结论与数字**保留：知识点内容仍是项目原创整理、
  未逐条对照 JMdict / KANJIDIC（14 条 `needs_review`）、JLPT 官方样题未入库、
  `N5/N4/N3` 是项目自定标签、80 学时压缩冲刺路径不等于官方标准、不承诺第 80 天必达 N3。
- v3 改的是**页面呈现与复习自评闭环**，**没有**把课程变成「教材支撑的课纲」，
  也**没有**完成 §4 列出的 JMdict / KANJIDIC 校核或 Irodori 重建大纲；
  这些仍是「明确仍未落地」项。
- v3 的 Cloudflare 重新部署与 GitHub push 由主 agent 稍后执行，本节不记录部署结果。
