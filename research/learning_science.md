# 学习科学机制 → 可执行逻辑（第一部分 + 第二部分）

- 调研日期：2026-11-06
- 查证方式：WebSearch / WebFetch 真实页面；逐条来源见 `sources_science.json`
- 诚实规则：凡未在原始/官方页面直接读到的结论，一律标「未核实」或「二手引用，未直接核对原文」，不写成定论
- 文档分工：本文件承载**第一部分（8 项机制）**与**第二部分（知识追踪 / 开源教学 Agent / 教育 Skills）**；WorkBuddy 平台核实与设计决策在 `platform_capabilities.md`

---

## 0. 统一状态数据结构（8 项机制共用，落在项目文件里）

8 项机制不要各写一套状态机，统一成一张 `items.json` + 一张 `session-log.jsonl`。这样每天的教学状态能被脚本确定性读写，不依赖 AI 记忆。

```jsonc
// items.json —— 每个学习条目一条
{
  "id": "vocab-0001",
  "type": "vocab | kanji | grammar | phrase",   // 交错练习按此分组
  "surface": "食べる", "reading": "たべる", "gloss": "吃",
  "tags": ["verb", "ichidan", "N5"],            // 易混淆组，用于辨析型交错
  "fsrs": {                                     // 对应 Spaced Repetition
    "D": 5.0,            // Difficulty ∈ [1,10]
    "S": 1.0,            // Stability，R=90% 时的间隔（天）
    "R": 1.0,            // Retrievability，当前回忆概率
    "last_review": "2026-11-06",
    "due": "2026-11-07",
    "reps": 0, "lapses": 0
  },
  "recall": {                                   // 对应 Active Recall / Retrieval Practice
    "answer_mode": "produce",                 // 只允许产出式，不用选择题判掌握
    "consecutive_correct": 0,
    "delayed_pass_count": 0,                  // 延迟 >= 7 天后的通过次数
    "distinct_contexts": [],                  // 出现过的语境 id 集合
    "first_seen": "2026-11-06",
    "last_pass_at": null
  },
  "exposure": { "known_token_ratio": 0.0, "input_samples": 0 },  // 对应 Comprehensible Input
  "practice": { "attempts": 0, "correct": 0, "error_rate": 0.0 }, // 对应 Deliberate Practice
  "mastery": { "state": "locked | learning | mastered", "score": 0.0,
               "assessment_version": 1 }      // 对应 Formative Assessment / Mastery Learning
}
```

```jsonc
// session-log.jsonl —— 每session追加一行，只做诊断、不记成绩
{"date":"2026-11-06","item_id":"vocab-0001","rating":3,"mode":"produce",
 "context":"ctx-001","feedback":{"goal":"...","current":"...","next_step":"..."},
 "elapsed_ms":4200}
```

> 阈值分两类，**务必区分**：标「文献/官方值」的来自下面查证过的来源；标「本项目工程设定」的是本项目自己定的策略参数，不是论文结论，可实测调整。

---

## 第一部分：8 项机制 → 确定性实现逻辑

### 1. Spaced Repetition（间隔重复）

**机制一句话**：在"刚要忘"的时候复习，比固定间隔更省复习量。FSRS 用三个量显式预测回忆概率，SM-2 只用一个 ease factor 乘间隔（详见 §A1）。

**确定性实现**：

```
配置: DESIRED_RETENTION = 0.90   # 文献/官方值：Anki 手册默认 0.90，建议 < 0.97
评分映射: rating = {1:Again, 2:Hard, 3:Good, 4:Easy}   # 官方 FSRS wiki 的 G 定义

每日启动 build_due_queue():
    for item in items:
        item.fsrs.R = R(t, S)        # t = today - last_review；FSRS-6: R=(1+FACTOR*t/S)^(-w20)
        if item.fsrs.R <= DESIRED_RETENTION or item.fsrs.due <= today:
            due_queue.append(item)
    # R 每天变，D/S 只在复习后变（OSR 官方中文 FAQ）

答题后 on_answer(item, rating):
    if rating == 1:                 # 忘记 → 必须按 Again，不能按 Hard
        item.fsrs.S = post_lapse_stability(D, S, R)   # 不再像 SM-2 那样一刀切重置
        item.fsrs.lapses += 1
    else:
        item.fsrs.D, item.fsrs.S = update_D_S(D, S, R, rating)
    t_next = I(DESIRED_RETENTION, S)   # FSRS-4.5: I(r,S)= S/FACTOR * (r^(1/DECAY) - 1)
    item.fsrs.due = today + round(t_next)
    item.fsrs.last_review = today
    item.fsrs.reps += 1
    append_session_log(...)
```

**触发条件 / 阈值**：`R <= 0.90` 或 `due <= today` 即入队；`rating==1` 强制走 lapse 分支。
**数据结构**：`items[].fsrs`（D/S/R/due/reps/lapses）。
**诚实边界**：FSRS 只用「间隔长度 + grade」两个输入（Anki FSRS FAQ Q5），**不建模题目难度、知识点、跨技能迁移**，所以它只是"复习调度器"，不是知识追踪模型（见 §2.1）。

---

### 2. Active Recall（主动回忆）

**机制一句话**：必须从记忆里"产出"答案，而不是看到答案后认出它。再认（recognition，如选择题）与回忆（recall/production）是不同认知状态；流畅感来自再认，不等于能提取（见 §A2）。

**确定性实现**：

```
出题时 enforce_production_mode(item):
    assert item.recall.answer_mode == "produce"
    # 禁止把选项/答案/词表在作答前渲染出来
    render(prompt=item.gloss, expect=item.surface)   # 中→日产出，或给语境造句
    hide(answer=True, options=True, notes=True)
    start_timer()

# 判分阶段才揭示
on_submit(user_answer):
    reveal(answer=item.surface)
    correct = normalize(user_answer) == normalize(item.surface)   # 用脚本做规范化，不交给 AI
    return correct
```

**触发条件**：所有用于"掌握判定"的题目强制 `mode=produce`；选择题只允许出现在"诊断/曝光"环节，且**不得**写入 `mastery.score`。
**数据结构**：`items[].recall.answer_mode`、`session-log.mode`。
**为什么脚本做**：答案规范化、是否揭示答案、计时，都是确定性逻辑，不应由模型自由裁量（见 `platform_capabilities.md` 的分工建议）。

---

### 3. Retrieval Practice（提取练习）

**机制一句话**：一次答对不等于掌握。NAS《How People Learn II》(2018) 明确指出学习者常"retrieve something once and then, believing they have learned it for the long term, drop the item from further practice"——这正是要防的坑（见 §A2）。

**确定性实现**（掌握门控，三个条件同时满足才算"延迟掌握"）：

```
配置（本项目工程设定，非文献定值）:
    MIN_DELAYED_PASSES = 3        # 至少 3 次通过
    MIN_DISTINCT_CONTEXTS = 2     # 至少 2 种不同语境
    MIN_DELAY_DAYS = 7            # 首次通过距今 >= 7 天（对齐 Roediger&Karpicke 2006 的一周延迟测验）

on_correct(item, context_id):
    item.recall.consecutive_correct += 1
    item.recall.distinct_contexts.add(context_id)          # 去重
    if (today - item.recall.first_seen).days >= MIN_DELAY_DAYS:
        item.recall.delayed_pass_count += 1                # 只有延迟后的通过才计数
    item.recall.last_pass_at = today
    # 注意：此处不设 mastery.state='mastered'，交给 §8 的 Mastery Learning 门控

is_durable(item):
    return (item.recall.delayed_pass_count >= MIN_DELAYED_PASSES
            and len(item.recall.distinct_contexts) >= MIN_DISTINCT_CONTEXTS
            and (today - item.recall.last_pass_at).days <= 30)   # 30天未复现则重新验证
```

**触发条件 / 阈值**：`>=3 次延迟通过 + >=2 语境 + >=7 天跨度`；任一条件不满足，条目继续留在复习队列。
**数据结构**：`items[].recall`（delayed_pass_count / distinct_contexts / first_seen / last_pass_at）。
**诚实边界**：`3 / 2 / 7` 是本项目工程参数，不是文献给出的"魔法数字"；NAS 报告也提醒大部分提取练习研究针对的是**简单信息（如词汇）而非深度理解**，所以本门控只适用于词汇/句型层面，语法运用能力需另设产出任务评估。

---

### 4. Interleaving（交错练习）

**机制一句话**：把易混淆的类别打乱混练，强迫先"判断题型"再解题；blocked practice（同类连做）练习时分数高、延迟测验分数低。**但这条对词汇不成立**（见 §A4）。

**确定性实现**（关键：分材料类型，不能一刀切）：

```
# 已核实的实证边界（Brunmair & Richter 2019, DOI 10.1037/bul0000209）:
#   总体 Hedges' g = 0.42；绘画 0.67；数学 0.34；说明文不显著；词汇 g = -0.39（blocking 更好）
INTERLEAVE_ALLOWED_TYPES = {"grammar", "phrase"}   # 只对"需要辨析"的类型交错
BLOCK_ONLY_TYPES = {"vocab", "kanji"}              # 纯词汇走 SRS + blocked，不交错

build_session_queue(due_items):
    blocks = group_by(due_items, key=type)
    if item.type in BLOCK_ONLY_TYPES:
        queue = sorted(block, key=fsrs.due)       # 同类连做，靠 SRS 制造间隔
    else:
        queue = shuffle_no_adjacent_same_tag(blocks)  # 相邻两条不同 tag
    return queue[:DAILY_CAP]

def shuffle_no_adjacent_same_tag(items):
    # 保证相邻题 tag 不同；若无法满足（某类占比>50%），剩余归入下一 session
    ...
```

**触发条件 / 阈值**：`type ∈ {grammar, phrase}` 且 `len(易混淆 tag 组) >= 2` 才启用交错；相邻两条不得同 tag；词汇类显式禁用交错。
**数据结构**：`items[].type` / `items[].tags`；`session-log.context`。
**诚实边界**：Rohrer & Taylor (2007)、Rohrer et al. (2015) 的**具体百分数在不同二手来源中互相矛盾**（20%/43% 与 20%/63% 两种写法），本次未直接核对原文，故**不采用其具体数值**；只采用已直接核实的 Brunmair & Richter 2019 元分析结论。Dunlosky et al. (2013) 把 interleaved practice 评为 "moderate utility"（低于 practice testing 的 high utility），该评级为二手引用，未直接核对原文。

---

### 5. Comprehensible Input（可理解输入 / i+1）

**机制一句话**：Krashen 主张输入略高于当前水平（i+1）即可习得。**但学界批评集中在：i+1 未操作化定义、不可检验/不可证伪、循环论证**（见 §A5），因此**不能当成定论，更不能写死成算法阈值**。

**确定性实现**（只做工程近似，明确标注为启发式）：

```
# 本项目工程设定，声明为启发式而非 Krashen 理论验证：
TARGET_KNOWN_RATIO = 0.92         # 阅读材料中已知词覆盖率约 90~95%，生词率 5~10%
MIN_INPUT_SAMPLES = 3             # 至少 3 篇不同材料才触发"可进入下一难度"

select_reading(candidate_text, learner_known_set):
    ratio = count(tokens ∩ learner_known_set) / count(tokens)   # 用脚本分词+查表，纯确定性
    if ratio >= TARGET_KNOWN_RATIO:
        candidate_text.exposure_ok = True
    else:
        candidate_text.exposure_ok = False        # 退回，或先预教生词
    return ratio

# 不做：不声称这就是 "i+1"；不因为 ratio 高就跳过产出练习（Swain 输出假说）
```

**触发条件 / 阈值**：`known_token_ratio >= 0.92`（工程值）；且**必须配合产出任务**，不能只给输入。
**数据结构**：`items[].exposure.known_token_ratio / input_samples`。
**诚实边界**：`0.92` 是本项目自定义近似，**不是** Krashen 给出的值（Krashen 本人从未给出可操作数值，这正是被批评点）。把它当作"选材过滤器"，不是"习得保证"。

---

### 6. Deliberate Practice（刻意练习）

**机制一句话**：Ericsson, Krampe & Tesch-Römer (1993) 强调技能提升来自"有挑战、有指导、有反馈"的刻意任务，而非单纯暴露时长（见 §A6）。

**确定性实现**（挑弱项 + 卡在"最近发展区"）：

```
配置（本项目工程设定；m98/fluent 开源项目把目标正确率设为 60~70%，可作参考）:
    MIN_ATTEMPTS = 3               # 样本不足不做判断
    TARGET_BAND = (0.60, 0.80)    # 正确率落在此区间才最值得练
    WEAK_TOP_N = 5

pick_deliberate_items(items):
    scored = [i for i in items if i.practice.attempts >= MIN_ATTEMPTS]
    # 优先挑"错得多但没完全不会"的：正确率在 TARGET_BAND 内且 error_rate 最高
    band = [i for i in scored if TARGET_BAND[0] <= 1-i.practice.error_rate <= TARGET_BAND[1]]
    return sorted(band, key=lambda i: -i.practice.error_rate)[:WEAK_TOP_N]
    # 正确率 >0.80 → 太易，交给 SRS 拉长间隔；<0.60 → 太难，退回讲解（corrective instruction）

每次练习必须带:
    worked_example → 独立作答 → immediate feedback → 记录 error_category
```

**触发条件 / 阈值**：`attempts >= 3`；`正确率 ∈ [0.60, 0.80]`；每 session 最多 5 个刻意项。
**数据结构**：`items[].practice`（attempts / correct / error_rate）。
**诚实边界**：60~70% 来自开源项目 `m98/fluent` 的自述目标，本次核实为**该项目设定**，不是 Ericsson 原文结论；Ericsson 1993 原文只核实到书目信息（Psychological Review, 100(3), 363-406），未逐页核对。

---

### 7. Formative Assessment（形成性评估）

**机制一句话**：Black & Wiliam (1998) *Inside the Black Box*（Phi Delta Kappan, 80(2), 139-148）综合约 250 项研究，报告形成性评估效应量约 0.4–0.7，且低成就学生受益更大；关键是"反馈被用于调整后续教学"，而非多打分（见 §A6）。

**确定性实现**（低风险诊断 + 三要素反馈，不进成绩册）：

```
# 反馈三要素（Sadler 1989，经 Black & Wiliam 1998 引用）：目标 / 当前位置 / 缩小差距的方法
on_session_end(session):
    for record in session.records:
        feedback = {
            "goal":      lookup_goal(record.item_id),        # 期望表现
            "current":   describe_error(record),             # 实际表现，脚本按 error_category 生成
            "next_step": pick_corrective(record.error_category)  # 具体下一步，非"再练一次"
        }
        assert all(feedback.values())                       # 三要素缺一即视为无效反馈
        record.feedback = feedback
    append_jsonl("session-log.jsonl", session)
    update_items_from_log(session)                          # 只更新状态，不生成分数/排名
    # 明确不做：不写 grade、不做与其他学习者的比较

# 下一 session 的选练必须消费上一次的诊断结果
build_next_session():
    weak = top_error_categories(last_session, k=3)
    return corrective_for(weak) + due_queue()
```

**触发条件**：每 session 结束必写日志；下一 session 必须读取上次 `error_category`，否则视为断链（脚本可校验）。
**数据结构**：`session-log.jsonl` 的 `feedback{goal,current,next_step}`、`error_category`。
**诚实边界**：效应量 0.4–0.7 来自二手引用（多来源一致），本次未直接核对 Black & Wiliam 1998 原文 PDF，标注为「二手引用」。

---

### 8. Mastery Learning（掌握学习）

**机制一句话**：Bloom (1968) *Learning for Mastery* 主张"学习固定、时间可变"，达标才进下一单元，未达标者接受**不同的**补救教学并重测（平行卷，不是同一张卷）。常用掌握阈值区间 **80–90%**（见 §A3）。

**确定性实现**：

```
配置: MASTERY_THRESHOLD = 0.85     # 文献区间 80~90%；Guskey 常引 85%
      PARALLEL_FORM_REQUIRED = True

evaluate_unit(learner, unit_id):
    score = score_on_parallel_form(unit_id, version=learner.mastery.assessment_version)
    learner.mastery.score = score
    if score >= MASTERY_THRESHOLD:
        learner.mastery.state = "mastered"
        unlock(next_unit(unit_id))
    else:
        learner.mastery.state = "learning"
        assign_corrective_instruction(learner, unit_id)   # 换讲法/换例子，不是重做同一份
        learner.mastery.assessment_version += 1          # 重测必须换平行卷
        schedule_reassessment(learner, delay_days >= 1)
    # 未达标不解锁、不推进；已达标者给 enrichment 而非空等

# 与 §3 联动：即使单题答对多次，也要过 unit 级阈值才算 mastered
```

**触发条件 / 阈值**：`score >= 0.85` 才解锁；重测必须 `assessment_version` 递增（平行卷）；未达标走 corrective 分支。
**数据结构**：`items[].mastery`（state / score / assessment_version）。
**诚实边界**：80–90% 是多个二手文献与教育机构页面一致的**常用建议区间**，Guskey 常引 85%；**Bloom 1968 原文中是否给出该精确数字，本次未能直接核实**，故写作"建议值区间"而非"Bloom 规定值"。

---

## 第一部分附录：必须真实查证的关键点（逐条交代）

### A1. FSRS vs SM-2 / rating 1-4 / desired retention / 三个量 —— ✅ 已核实（官方一手）

来源：`github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm`、`docs.ankiweb.net/deck-options.html`、`faqs.ankiweb.net/frequently-asked-questions-about-fsrs.html`、`open-spaced-repetition.github.io`

| 项 | 核实结果 |
|---|---|
| 三个量 | `R` Retrievability（当前回忆概率）、`S` Stability（R=90% 时的间隔天数）、`D` Difficulty（∈[1,10]）。FSRS 源自 MaiMemo DHP 模型，是 DSR 模型变体 |
| rating | `G: 1=Again, 2=Hard, 3=Good, 4=Easy`（官方 wiki 原文）。Anki 手册特别警告：**忘记时必须按 Again，按 Hard 会让所有间隔异常偏大**，因为 Hard 被当作"回忆成功但费力" |
| desired retention | "the proportion of cards recalled successfully when they are due"，**默认 0.90**，官方建议**保持低于 0.97**（超过后复习量急剧上升）；0.95 相比 0.90 间隔几乎减半 |
| 间隔公式 | FSRS-4.5: `I(r,S) = S/FACTOR * (r^(1/DECAY) - 1)`；FSRS-6 用 21 参数，遗忘曲线衰减指数 `w20` 变为可训练 |
| 与 SM-2 区别 | SM-2 每卡只存一个 ease factor，`下次间隔 = 上次间隔 × ease`，**不预测"今天还记得的概率"**；FSRS 显式建模遗忘曲线、可用复习历史拟合参数、遗忘后按 post-lapse stability 平滑处理而非把间隔一刀切重置、有 mean reversion 避免 "ease hell" |
| 输入 | Anki 官方 FAQ Q5：**FSRS 只使用 interval lengths 与 grades**，不考虑答题耗时 |
| 版本 | 官方 wiki 页面记录 FSRS-6（21 参数）、FSRS-5（19）、FSRS-4.5（17）；`awesome-fsrs` wiki 页面由 Jarrett Ye 于 2026-07-28 编辑（48 revisions），旧 `fsrs4anki/wiki/The-Algorithm` 已标注迁移 |

- ⚠️ **未核实**：二手博客广泛流传的"FSRS 比 SM-2 少 20–30% 复习量""srs-benchmark 上 FSRS-6 log loss 0.4821 vs SM-2 0.5967"等具体数字，本次只在二手文章看到，**未直接核对 `open-spaced-repetition/srs-benchmark` 结果表**，故不写入结论。OSR 官方主页只确认该 benchmark 仓库存在。

### A2. 主动回忆 vs 再认；一次答对不等于掌握 —— ✅ 已核实（权威一手）

- **NAS《How People Learn II》(2018), National Academies Press, doi:10.17226/24783, 第 5 章**（`nationalacademies.org/read/24783/chapter/7`）：
  - 复习（re-reading）产生的是**加工流畅感 / 再认**，不是**回忆**；报告原文区分 `recognition` 与 `recall`。
  - 原文点名误区："few learners self-test because they view the act of retrieval as part of the process of learning. Instead, they are likely to **retrieve something once and then, believing they have learned it for the long term, drop the item from further practice**." → 这是"一次答对不等于掌握"的直接依据。
  - 原文亦提醒：多数提取练习研究针对**简单信息（如词汇）**而非深度理解。
- **Roediger & Karpicke (2006), Psychological Science**；华盛顿大学官方新闻稿（`source.wustl.edu/2006/03/...`）核实：一周后延迟测验，**反复提取组 61% vs 反复阅读组 40%**；5 分钟即时测验反而是阅读组略高（81% vs 75%）→ 说明"当场答对"会骗人，必须用延迟测验判定。
- 结论落到项目：判定掌握必须用**延迟 + 多次 + 产出式**，且至少跨语境（§3 门控）。

### A3. Bloom mastery threshold 建议值区间与出处 —— ⚠️ 部分核实（二手一致，原文未直接核对）

- 一致给出的区间：**80–90%**；Guskey 常引 **85%**。
- 出处（均为本次实际访问的页面）：
  - 台湾教育云「精熟學習」词条 `pedia.cloud.edu.tw`：「通常在一個測驗或其他評量中，能得到 80~90% 的分數……賈斯基(Guskey)認為精熟的標準通常是指答對百分之八十五」
  - Columbia College 页面 `excellence.columbia.ca`：「mastery thresholds typically in the range of 80 to 90 percent」，并列参考文献 Bloom 1968 / Guskey 2007, 2010 / Keller 1968 / Persky et al. 2022
  - `markinminutes.com/glossary/mastery-learning`：「Typical mastery threshold: 80–90% on the formative assessment」
  - VCU 学位论文 PDF（`scholarscompass.vcu.edu`）转述 Bloom (1968) 实验中 80%→90% 学生达 A
- **未能核实**：Bloom, B. S. (1968). *Learning for Mastery*. Evaluation Comment, 1(2), 1–12. **原文中是否给出 80–90% 这一精确数字**，本次未直接读到原文，故按「常用建议值区间」表述。

### A4. 交错练习 vs blocked practice 实证差异 —— ✅ 已核实（原始元分析一手）

- **Brunmair, M. & Richter, T. (2019). "Similarity matters: A meta-analysis of interleaved learning and its moderators." Psychological Bulletin, 145(11), 1029–1052. DOI: 10.1037/bul0000209, PMID: 31556629**（PubMed 摘要 + 维尔茨堡大学作者原稿 PDF 均已核实）
  - 59 项研究、238 个效应量、158 个样本；多层元分析总体 **Hedges' g = 0.42**（中等）
  - 分材料：绘画/视觉 **g = 0.67**；数学任务 **g = 0.34**（小）；说明文与味觉**不显著**；**词汇 g = −0.39（blocking 反而更好）**
  - 调节效应：类别之间越相似、类别内项目差异越大、材料越复杂，交错收益越大
  - 作者结论原文：interleaving "should be used with caution in certain conditions, especially for expository texts and words"
- **对本项目最关键的推论**：日语**词汇/汉字**学习不应盲目交错，应以 SRS + blocked 为主；交错只用于**易混淆语法/句型辨析**。
- ⚠️ **未核实**：Rohrer & Taylor (2007)、Rohrer, Dedrick & Stershic (2015) 的**具体百分数**（二手来源给出 20%/43% 与 20%/63% 两套互相矛盾的数字），未直接核对原文；Dunlosky et al. (2013) 的 "moderate utility" 评级亦为二手引用。三篇文献的存在与被引方向一致，但具体数值不写入实现。

### A5. 可理解输入 i+1 的争议 —— ✅ 已核实（多个学术一手 PDF）

学界批评（如实记录，**不当成定论**）：

| 批评 | 出处（本次实际访问） |
|---|---|
| `i+1` **未操作化定义**（"The 'i+1' construct is not operationally defined"） | Ellis (1990:104)，转引自 `auhw.repo.nii.ac.jp/record/1771/files/KJ00004828676.pdf` |
| **循环论证**：凡导致习得的输入即为"可理解输入"，可理解输入即"导致习得的输入" | Cook (1993)、Ellis (1990)、McLaughlin (1987)，同上 PDF |
| **不可检验 / 不可证伪**："if it is impossible to test the theory in any meaningful way, such claims have little credibility" | McLaughlin (1987:42)；Gregg (1984, 1994) 论精确性与可检验性，同上 PDF |
| 定义含混：`i` 有时指整体能力、有时只指语法；`+1` 的"单位"无法确定 | Liu (2015)、White (1987)，`files.eric.ed.gov/fulltext/EJ1329865.pdf` |
| 课堂不可行：40 人班级如何对每个学生定位各自的 i+1 | `files.eric.ed.gov/fulltext/EJ1311570.pdf`（ERIC EJ1311570） |
| **输入不是唯一途径**：Swain (1985) 输出假说——沉浸式大量可理解输入的学生仍有持续语法错误 | EJ1311570、`mikeydoes.com` 术语页 |
| 近期神经生态学批评：语言学习是主动、具身、交互+反馈+多模态的过程，静态 i+1 模型不足 | `pmc.ncbi.nlm.nih.gov/articles/PMC12577063/`（"Beyond comprehensible input: a neuro-ecological critique..."，PMC 全文） |

- 同时如实记录：Krashen 强调"可理解输入、低情感过滤、意义聚焦"在教学实践中仍被广泛接受且影响巨大（EJ1311570 称其为 "a wonderful, messy success"）。
- **落到项目**：i+1 只作为「选材时控制生词率」的**启发式**，不写进掌握判定、不声称理论正确；且必须配合产出练习。

### A6. 形成性评估 / 刻意练习出处 —— ⚠️ 二手引用核实

- Black, P. & Wiliam, D. (1998). *Inside the Black Box: Raising Standards Through Classroom Assessment*. **Phi Delta Kappan, 80(2), 139–148**（书目信息由 Michigan Dept. of Education 汇编 PDF、American Book Company ESSA 报告、hantsmusic 教学资源页交叉确认）。效应量 0.4–0.7 为多来源一致的二手转述，未直接核对原文 PDF。
- Ericsson, K. A., Krampe, R. T., & Tesch-Römer, C. (1993). *The Role of Deliberate Practice in the Acquisition of Expert Performance*. **Psychological Review, 100(3), 363–406**（书目信息由 American Book Company ESSA 报告与教学研究页交叉确认）；原文未逐页核对。
- 反馈三要素（目标 / 现状 / 缩小差距的方式）源自 Sadler (1989)，经 Black & Wiliam (1998) 引用（hantsmusic 教学资源页原文摘录）。

---

## 第二部分：知识追踪与开源教学 Agent

### 2.1 BKT / DKT / FSRS 各自适用场景与局限（含真实出处）

三者的定位**根本不同**，不要混用：BKT/DKT 是**"学生会不会这个知识点"的推断模型**，FSRS 是**"这张卡什么时候该复习"的调度器**。

| 模型 | 机制 | 适用场景 | 局限 | 真实出处 |
|---|---|---|---|---|
| **BKT** (Corbett & Anderson, 1994) | 隐马尔可夫模型；每个技能一个二值隐状态（会/不会）；参数 `P(L0)` 初始、`P(T)` 学习、slip、guess | 技能可清晰拆分、题目单技能、需要**可解释**的教学诊断、数据量小 | 二值掌握状态过于粗糙；假设技能相互独立，**无法建模跨技能迁移**；多数变体对不同学生共用同一组参数 | `arxiv.org/pdf/2112.11209v1`（Interpretable KT，明确写 "treat skills independently and are unable to detect learning transfer across skills"）；`arxiv.org/pdf/2101.11335v1`；ScienceDirect `S0957417422009769`（EnKT） |
| **DKT** (Piech et al., 2015) | RNN/LSTM 把"题目 skill id + 对错"序列编码，输出各技能答对概率 | 大规模交互日志、需要跨技能迁移建模、追求预测精度 | **黑盒不可解释**（心理意义藏在数万参数隐层）；**稀疏数据/噪声下性能明显下降**；需要大量数据；`arxiv.org/pdf/2101.11335v1` 提到 ASSISTments 数据集存在重复样本问题（Xiong et al. 2016） | `arxiv.org/pdf/2101.11335v1`（含 BKT 67% AUC vs DKT >80% AUC 的对比）；`arxiv.org/pdf/2112.11209v1`；Springer `10.1007/s44443-025-00280-3.pdf` |
| **FSRS** | 见 §A1，DSR 记忆状态 + 遗忘曲线，输出下次复习间隔 | **单条目（卡片）的长期记忆保持**、复习排程 | 只用 interval + grade；**不建模技能/知识点/题目难度/跨技能迁移**；冷启动阶段用默认参数（Anki FAQ Q6 说明 24.06.3+ 任意复习量即可优化，早期版本需 1000 条） | `awesome-fsrs/wiki/The-Algorithm`、`docs.ankiweb.net/deck-options.html`、`faqs.ankiweb.net/frequently-asked-questions-about-fsrs.html` |

补充核实：`Khajah, Lindsey & Mozer (2016)` 通过给 BKT 增加遗忘、学生能力、技能发现等组件，可取得接近 DKT 的结果（转引自 `arxiv.org/pdf/2112.11209v1` 与 `arxiv.org/pdf/2101.11335v1`）——说明"深度模型一定更好"并非定论。

**对本项目（单人日语学习、条目规模小、需可审计）的建议**：不引入 DKT；用 **FSRS 做复习调度 + 显式规则做掌握门控（§3/§8）**。若将来要建模语法点之间的前置依赖，可借鉴 BKT 的思路用**可读的规则/表格**表达，而不是黑盒模型。依据：本项目数据量远小于 DKT 所需规模，且教学状态必须可被人/脚本审计。

### 2.2 开源 AI 语言教学 Agent / 自适应学习系统（GitHub 真实核实）

用 GitHub API (`api.github.com/repos/...`) 核实了 star / license / push 时间，**未编造仓库名**。查证日 2026-11-06。

| 仓库 | 许可证 | 活跃度（API 实测） | 主要语言 | 可借鉴点 |
|---|---|---|---|---|
| **`HKUDS/DeepTutor`** | Apache-2.0 | **55,612 stars / 6,816 forks / 307 open issues**；created 2025-12-28，pushed **2026-11-05**；README 发布 v1.7.1 (2026.11.1) | Python（Next.js 前端） | "agent-native learning workspace"；`Mastery Path` + mastery gate + mastery evidence；可检查的三层记忆（L1 traces / L2 facts / L3 synthesis，Memory Graph 可审计）；subagents / Partners；CLI 输出 NDJSON 便于被其他 Agent 调用；Anki 导出 |
| **`m98/fluent`** | MIT | **453 stars / 67 forks / 12 open issues**；created 2025-11-17，pushed **2026-06-15**（updated 2026-11-05） | Python | **与本项目最贴近**：把 Claude Code 变成语言导师；SM-2 间隔重复；**6 个 JSON 数据库**（learner-profile / progress / mistakes / mastery / spaced-repetition / session-log）；12 个 Skills（8 面向学习者 + 4 helper）；Hooks 在 SessionStart/SessionEnd/PostToolUse/PreCompact 自动备份与校验；目标正确率 60–70%；数据全部本地、`.gitignore` 排除 |
| **`zijinz456/OpenTutor`** | MIT | **167 stars / 40 forks / 27 open issues**；created 2026-02-26，pushed **2026-11-05** | Python | local-first / self-hosted；**FSRS 4.5 + BKT** 同时落地（`services/learning_science/` 含 BKT、难度选择、认知负荷）；3 个 specialist agents（Tutor / Planner / Layout）由 intent-routing orchestrator 协调；知识图谱前置依赖、错题归因；SQLite |
| `DoroninDobroCorp/LinguaLearn` | MIT | **1 star / 0 forks / 0 issues**；created 2026-02-24，pushed 2026-11-02 | JavaScript | 轻量参考：CEFR A1–C2 150 主题掌握度追踪；对话中自动识别错误 → 生成针对性练习；词汇间隔重复（自定义 ladder，非 FSRS）；进度 +5/-10 计分。**规模很小，代码质量/维护未评估** |

**核实过程中发现并如实记录的两点**：
1. 搜索结果里的 `This-wang/OpenTutor` 经 GitHub API 确认为 **fork（0 stars / 0 forks，pushed 2026-10-08）**，其 `parent`/`source` 均为 `zijinz456/OpenTutor`。因此上表记录的是**源仓库 `zijinz456/OpenTutor`**，不是那个 fork。
2. 搜索结果中的中文博客 `xujun.org` 还列出 `Akash049/teaching_agent`、`Ebimsv/AITutorAgent`、`gsaini/educational-tutor-ai`、`Zc0812/EduPlanner` 等仓库；**本次未逐一 WebFetch/GitHub API 核实，故不纳入上表、不写其许可证与活跃度**（避免编造）。
3. 二手博客称 DeepTutor 有 arXiv 2604.26962 与"42.6K stars"；GitHub API 实测为 **55,612**，以 API 为准；arXiv 编号未在 arXiv 官方页面核实，仅见于 README 的 homepage 字段与二手报道。

**可借鉴点归纳（对本项目最有用）**：
- `m98/fluent` 的**"学习状态 = 一组本地 JSON 文件 + 确定性脚本更新 + Hooks 自动备份"**，正是"平台不承诺自动传递状态"时最稳妥的做法。
- `m98/fluent` 把**算法（SM-2 计算、DB 更新、反馈格式）做成独立的 helper Skills / 脚本**，把**教学对话**留给 AI —— 与本任务最后要回答的"确定性 vs AI 分工"完全一致。
- `zijinz456/OpenTutor` 的 `learning_science/` 分层说明：FSRS 与 BKT 可以并存但职责不同（调度 vs 掌握推断）。
- `HKUDS/DeepTutor` 的"可检查记忆 +  mastery evidence"提示：状态应可审计，不要只存在模型上下文里。

### 2.3 教育类 Agent Skills 是否有真实可复用实现 —— ✅ 有（已核实）

- **真实可复用实现：`m98/fluent`（MIT）**。它就是"教育类 Agent Skills"的成品：12 个 `SKILL.md`（YAML frontmatter + Markdown 指令），分两类——
  - 8 个**面向学习者**的命令型 Skills（`/fluent-setup`、`/fluent-learn`、`/fluent-review`、`/fluent-progress`、`/fluent-vocab`、`/fluent-writing`、`/fluent-speaking`、`/fluent-reading`），README 明确说 learner-facing skills **被 gated，只能显式调用**，避免"聊天一句话触发 20 分钟练习"。
  - 4 个 **helper Skills** 自动加载：`/fluent-sm2-calculator`（SM-2 算法参考）、`/fluent-feedback-formatter`（反馈模板）、`/fluent-db-updater`（调用 `update-db.py` 用单个 JSON payload 原子更新全部 6 个数据库）、`/fluent-session-analyzer`（解析 session 文件提取错误模式）。
  - 其 `update-db.py` + Hooks 的模式，就是"确定性程序负责状态、AI 负责教学"的可复用范例。
- **WorkBuddy / CodeBuddy 平台侧的 Skills 机制也真实存在**（已核实，见 `platform_capabilities.md`）：
  - 官方开放平台 `open.workbuddy.cn/docs/skill` 定义标准结构：`SKILL.md`（必需）+ `references/` + **`scripts/`（可执行脚本）** + `templates/`，并给出 YAML frontmatter 字段（name / display_name / description / version / author 等）。
  - 官方 IDE 文档 `workbuddy.ai/docs/ide/Features/Skills` 明确写：`scripts/` 用于 **"Executable code for tasks requiring deterministic reliability or that are repeatedly rewritten"**，并说明三级渐进式加载（Metadata 常驻 → SKILL.md 触发时加载 → 资源按需加载）。
  - 技能市场页面 `workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market` 说明安装/上传/创建/启用关闭、开关状态多端同步且不改动原 SKILL.md。
- ⚠️ **未能核实**：WorkBuddy **技能市场里是否存在现成的"日语教学 / 语言学习"官方 Skill 可直接安装复用**。本次搜索未命中具体技能条目，故不编造技能名；如需要，应自行按官方规范创建（这也正是本项目要做的事）。

### 2.4 第二部分未能核实清单

1. `open-spaced-repetition/srs-benchmark` 结果表中的 FSRS vs SM-2 具体指标（log loss / AUC / "少 20–30% 复习量"）——仅见二手博客，未直接核对。
2. Rohrer & Taylor (2007)、Rohrer et al. (2015)、Dunlosky et al. (2013) 原文 PDF 与具体数值——仅二手引用，且不同来源数字互相矛盾。
3. Bloom (1968) 原文中 80–90% 阈值的精确表述；Black & Wiliam (1998)、Ericsson et al. (1993) 原文 PDF 未逐页核对（仅核实书目信息）。
4. `Akash049/teaching_agent`、`Ebimsv/AITutorAgent`、`gsaini/educational-tutor-ai`、`Zc0812/EduPlanner` 的真实性、许可证、活跃度——未核实，不纳入结论。
5. DeepTutor 的 arXiv 2604.26962 是否在 arXiv 官方页面真实存在——仅见 README homepage 与二手报道。
6. WorkBuddy 技能市场中是否有现成教育/语言学习 Skill——未核实。
7. 各仓库的**代码质量、测试覆盖、长期维护承诺**——未评估，只核实了元数据与 README 自述。
