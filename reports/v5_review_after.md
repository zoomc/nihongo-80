# v5 修复后独立复审（after）

- 复审对象：`/Users/mj/Documents/learn/jp/nihongo-80`（2026-11-07 12:33 提交 `2a667fb` 后的工作树）
- 复审方式：只读源码/数据 + 独立复算 + 临时副本跑 CLI + Chrome 156 headless CDP 实测
- 未改任何源码、未 commit；跑测试时 `tests/test_v5.py` 自行改写了 `STATE.md` 与 `tasks/done/day-001-tutor.md`，已用 `git checkout --` 还原，最终 `git status --short` 仅剩本报告
- 临时目录：`/tmp/nh80_after_review`（仓库副本，隔离站点构建）、`/tmp/nh80_after_root`（只放 seeds + curriculum 的空根目录）
- 上一轮报告：`reports/v5_review.md`（P0-1 覆盖、P0-2 题目对齐、P0-5 init）

## 0. 结论摘要

| # | 检查项 | 结论 | 一句话 |
|---|---|---|---|
| 1 | 课程覆盖 | **PASS** | 150 天去重 2700/276/620，与 seeds 完全相等；每天 60 分钟；0 重复；先修 0 违规 |
| 2 | 练习对齐 | **FAIL** | 网页端已对齐，但 Day 1 只有 5 题；`curriculum.question_ids` 仍 133/150 天零对齐，会话 brief 仍发旧题 |
| 3 | CLI init / validate | **PASS** | 临时根目录 init 成功，DB 150 天 / 2700 词；validate 0 错误 |
| 4 | 内容抽样 | **FAIL** | 50 条抽样 + 四天网页题中 6 处明显错误（读音、词性、语法规则、例句错位） |
| 5 | 网页 | **FAIL** | 5 块、翻页、判分、无横滚均 PASS；遮盖三模式仍坏（重复绑定，日语/关不可达） |
| 6 | 诚实性 | **FAIL** | 2700/276/620/19 属实；但 README 仍写 1066 条 / 80 天 / 49 项；无 CC-BY-SA 说明 |

### 三项 P0 逐项判定

| P0 | 内容 | 判定 | 依据 |
|---|---|---|---|
| P0-1 | 旧 340 词 / 96 语法 / 140 汉字从未排课 | **YES** | 150 天 `new_*_ids` 去重后恰为 2700/276/620，与 seeds 集合完全相等，0 缺 0 多 |
| P0-2 | 每日题目与当天内容 150/150 零对齐 | **NO（只修了网页端）** | `web/data/day-*.json` 已对齐；但 `curriculum.question_ids` 133/150 天交集为空，Day 50 brief 的 6 题只有「壊す」1 题对得上；Day 1 仅 5 题 |
| P0-5 | `nh80 init` 不能生成 v5 | **YES** | 临时根目录 init 无报错，DB 150 天 / 2700 词 / 276 语法 / 620 汉字；validate 0 错误 |

> 结论：三项里 **2 项真修好，1 项（练习对齐）只修了网页展示层，课程真源和会话链路没修**。

---

## 1. 课程覆盖 — PASS

### 1.1 去重总数

| 指标 | seeds 行数 | 150 天去重后 | 总排课次数 | 重复 ID |
|---|---:|---:|---:|---:|
| `new_vocab_ids` | 2700 | **2700** | 2700 | 0 |
| `new_grammar_ids` | 276 | **276** | 276 | 0 |
| `new_kanji_ids` | 620 | **620** | 620 | 0 |

- 集合关系：`scheduled == seeds` 三项均为 `True`，缺失 0、多余 0。
- 证据：`python3` 复算 `curriculum/curriculum.json` 的 150 个 day 对象，`len(set(...))` 与 `knowledge/seeds/*.jsonl` 行数逐一相等。

### 1.2 时间块

```
sum(block.min per day) -> Counter({60: 150})
blocks 数 -> Counter({5: 105, 6: 45})   # 45 个听力日多一个听力块
```

150/150 天合计 60 分钟；无 0 分钟块；会话块为 `60 - 已分配` 的补足。

### 1.3 重复排课

- 三个字段全量扫描，重复 ID 均为 0。
- `nh80 validate` 的重复检查同样 0 错误。

### 1.4 语法先修

- 276 条语法共 **360 条先修边**。
- 先修目标不存在：**0**。
- 先修排在天数更晚：**0**。
- 同一天内先修排在本条之后：**0**。
- 21 条语法无 `prerequisites`（多为入门第一条），可接受。
- 残留小问题：Day 1 第二条语法 `G0261 〜か（or）` 的例句「飲み物はコーヒーか紅茶がいいです」用了 です，但 `prerequisites` 为空，未声明依赖同日第一条 `G0001`。这不是顺序违规，是**漏声明**（P2）。

### 1.5 排课质量残留

- **Day 150 一天排 24 个新汉字**（其余日 4 个）。生成器 `n=4 if d<DAYS else 8` 后再把余数全塞进最后一天，实际 620−149×4=24 全部压到 Day 150。当天同时还有 14 词 + 1 语法，60 分钟内不可能消化。属于 P1 节奏缺陷（不影响“覆盖数量”判定）。

---

## 2. 练习对齐 — FAIL

### 2.1 题量：Day 1 不足 6 题

全量统计 `web/data/day-*.json`：

```
quiz 题数分布 -> Counter({6: 149, 5: 1})
```

- 只有 **Day 1 是 5 题**，其余 149 天 6 题。
- Day 1 构成：3 个新词题 + 1 个汉字题 + 1 个语法题；`review_knowledge_ids=[]`，补题循环无词可补。
- 但 `blocks[3].desc` 写的是「6 题，交错混合」，页面也按 6 题设计。**Day 1 与自己的课程描述不一致**。
- 证据：`build_v5_site.py:373-432`，Day 1 的 3+1+1 之后没有第 6 题来源。

### 2.2 当天内容对齐：网页端 PASS

抽查 Day 1/50/100/150，`prompt` 中均出现当天 `surface` / `char` / `pattern`：

| Day | 新词题 | 汉字题 | 语法题 | 复习题 | 对齐结论 |
|---|---|---|---|---|---|
| 1 | 私 / あなた / さん | 日 | N は N です | — | 5/5 全部当天内容 |
| 50 | 込む / 米 / ごらんになる | 研 | 〜ておく | 高校 | 6/6（1 题为 T+ 复习） |
| 100 | 疑問 / 逆 / キャプテン | 身 | 〜こと（instruction） | きつい | 6/6 |
| 150 | 離れる / 羽 / 幅 | 歯 | 〜かける | 端 | 6/6 |

全量复算：

- 899 道网页题中，**0 道**既不属于当天新词/汉字/语法、也不是「复习：」题。
- 143 天为 5 道当天内容 + 1 道复习；7 天为 6 道当天内容（复习题面恰好与当天词重合）。
- 上一轮的「150/150 天零对齐」在**网页端已修复**。

### 2.3 答案隔离：基本 PASS，但有旁路

- 每题字段只有 `qid / prompt / options / h / oh / rationale`，**没有明文 `answer` 字段**。
- 899/899 题满足：`h` 恰好匹配 1 个选项；`h ∈ oh`；选项无重复。
- 判分哈希为 NFKC + 去空白后的 FNV-1a，Python 复算 899/899 一致。
- 旁路 1：`rationale` 在 **466/899** 题里直接包含正确选项文本（如「私（わたし）＝我」），虽然只在作答后插入 DOM，但查看源码即可看到。
- 旁路 2：`web/data/answer-key.json`（395 条答案）随静态站发布，本地实测 `GET /data/answer-key.json` 返回 **200**，内容为 `{"Q0001":{"answer":"です"...}}`。该文件被 Worker 用于服务端重判，但不应同时作为公开静态资源暴露。

### 2.4 Chrome 实测判分：PASS

Chrome 156 headless，375×812，加载 `day-001.html`：

| 操作 | 结果 |
|---|---|
| 第 1 题点「我」（正确） | class 变 `opt correct`；反馈「对。私（わたし）＝我」；分数 `1 / 1` |
| 同一题再点其他项 | 分数仍 `1 / 1`，不重复计分 |
| 第 2 题点「信封」（错误） | class `opt wrong`；正确项「你；您」被标 `opt correct`；分数 `1 / 2` |

判分逻辑与 UI 均正确。

### 2.5 课程真源 / 会话链路：FAIL（P0-2 残留）

- `curriculum/curriculum.json` 的 `question_ids` 仍是旧题库轮转：900 个槽位、674 个唯一题。
- 逐日复算：**133/150 天**的 `question_ids.target` 与当天新词/语法/汉字交集为 **0**。
- 实测 Day 50：`start-day 50` 生成的 `sessions/day-050-brief.md` 给的是 `Q0473、Q0476、Q0479、Q0482、Q0485、Q0488`；查题库后只有 `Q0476 壊す` 命中当天新词（1/6），其余是 お願い / かっこう / 趣味 / 辞典 / 謝る。
- 也就是说：**学生打开网页做题是对齐的；老师按 brief 走会话流程拿到的仍是错题。** 这是 P0-2 只修了一半的直接证据。

---

## 3. CLI init / validate — PASS

### 3.1 init

在 `/tmp/nh80_after_review`（仓库副本）里执行：

```bash
python3 scripts/nh80.py --root /tmp/nh80_after_root init
```

输出（exit 0，0.8 s）：

```json
{
  "ok": true,
  "seeds": {"ok": true, "counts": {"vocabulary": 2700, "grammar": 276, "kanji": 620,
            "questions": 945, "materials": 95}, "total": 4636},
  "curriculum": {"days": 150, "validation": true},
  "site": {"ok": true, "days": 150}
}
```

临时 DB 复算：

| 表 | 行数 |
|---|---:|
| `curriculum_days` | **150** |
| `vocabulary` | **2700** |
| `grammar` | **276** |
| `kanji` | **620** |
| `questions` | 945 |
| `materials` | 95 |

`fsrs_cards` 仍为 0（init 不建卡，属预期），但上一轮 P0-6 的写回链路未在本次三项范围内。

### 3.2 validate

```json
{"ok": true, "error_count": 0, "errors": [], "warnings": [],
 "days": 150, "totals": {"v": 2700, "g": 276, "k": 620}, "listening_days": 45}
```

### 3.3 CLI 残留

- init 报的 seeds 总数是 **4636**，不含 1500 条 `sentences.jsonl`；README 说「导入 6,136 条种子」不成立（见第 6 节）。
- `cmd_init → cmd_build → build_v5_site.main()` 使用模块级 `ROOT = Path(__file__).parent.parent`，**忽略 `--root`**。实测 `/tmp/nh80_after_root` 下没有 `web/`，站点被写进了脚本所在仓库副本的 `web/`。在真实仓库上跑没问题（路径恰好相同），但 `--root` 的隔离语义是假的，属于 P2。

---

## 4. 内容抽样 — FAIL

抽样方法：固定 seed 分层随机（词汇 N5×7 / N4×7 / N3×6，语法 10，汉字 10，题 10），另加四天网页题共 23 道。

### 4.1 明显错误 6 处

| # | ID | 字段 | 问题 | 证据 |
|---|---|---|---|---|
| 1 | `V0505` グラム | 例句 | 例句根本不是「克」 | `"プログラムをいただけますか。"` / 「能给我一份节目单吗？」——例句是 program（节目单），只是字符串里恰好含「グラム」 |
| 2 | `V1827` 禁煙 | `pos` | 词性错误 | 标成「惯用表达」；禁煙是名词 / サ変动词（禁煙する） |
| 3 | `G0071` わけがない / わけにはいかない | 释义 + `common_errors` | 释义多出「不好…」；把可接受的「わけがないです」判成错 | `meaning_zh` 写「不可能…／不能…、不好…」，两形都没有「不好」义；错误项说「わけがない 是断定语，不加 です」，但「彼が来るわけがないです」是自然日语，规则过度绝对 |
| 4 | `K0336` 活 | `kunyomi` | 生造训读 | 标 `い.きる / い.かす / い.ける`；「活」在常用汉字表没有训读（生きる是「生」） |
| 5 | `K0383` 置 | `zh_trap` | 注释自相矛盾 | 「『物置』读ものおき，不读おき」——ものおき 的第二个字正读 おき |
| 6 | `K0597` 歯 | `kunyomi` + 题目解析 | 混入「齢」的读音 | `kunyomi` 含 `よわい / よわ.い / よわい.する`；Day 150 第 4 题解析直接写「歯：音 シ｜训 よわい、は、よわ.い、よわい.する」，学生会被教错 |

> 第 6 条同时算作「题目错误」：`Q-150-K` 的 `rationale` 是错的。网页判分本身仍能选中「シ」，但解析在教错误读音。

### 4.2 次要问题 3 处（未计入 6）

| ID | 问题 |
|---|---|
| `K0574` 列 | `onyomi` 含「レ」，非常用音；通常只有 レツ |
| `V0907` 急ぐ | `meaning_zh` 写「赶紧；着急」，但 `notes_for_zh` 又说「不是『着急不安』」，自相矛盾 |
| `G0005` これ/それ | `common_errors` 用「これ は 本です（分写）」当常见错误；日语不写空格，这是凑数错误，不是学习者会犯的错 |

### 4.3 抽样中确认正确的部分

- 20 条词汇：假名、中文释义、ko_hanja 抽样 5/5 正确（千=천、特急=특급、欠席=결석、銃=총、禁煙=금연）。
- 10 条语法：`ko_equiv` / `ko_diff` 276/276 全有值，抽样 10 条语义与韩语对照均成立；接续、例句大体正确。
- 10 个汉字：ko_hanja 抽样 10/10 正确；读音除上述问题外无假名与字不匹配。
- 10 道种子题：`Q0460/Q0910/Q0275/Q0354/Q0161/Q0474/Q0322/Q0825/Q0671/Q0907` 未发现硬错误；排序题 `Q0275` 答案 `4,2,1,3` 正确。

### 4.4 结构性问题（非抽样错误，但影响内容可用性）

- 38 个词仍无例句；26 个词 `pos="词"`；1839/2700 词无 `ko_hanja`；480/620 汉字 `vocab_refs` 为空（与上一轮相同，未修）。
- **句子块 1464/1500 条与当天新词/语法零交集**；`hint` 与答案不匹配 **1484/1500**（如 Day 1 提示「〜は」，句子却是「信号が青に変わったわよ。」）。
- Day 1 的 10 道句子是 N3 敬语/惯用句（「もうスミスさんに会われましたね。」「お前はまだ「青い」な。」），与 0 基础首日严重不匹配。

---

## 5. 网页 — FAIL

### 5.1 通过项

| 检查 | 375×812 | 1280×900 |
|---|---|---|
| 5 块存在 | `review / vocab / grammar / sentences / quiz` 全在 | 同左 |
| 横向滚动 | `scrollWidth=375, innerWidth=375` | `scrollWidth=1280, innerWidth=1280` |
| 布局 | 单列 | `grid-template-columns: 200px 760px`，TOC `sticky` |
| 词卡翻页 | 私 → あなた →（上一张）私；`vTotal=9` | 同左 |
| 练习判分 | 正确 `1/1`、错误标出正确项 `1/2`、不重复计分 | 同左 |

Day 50/100/150 在 375 宽同样 `scrollWidth=375`，无横滚；Day 50/150 有第 ⑥ 听力块。

### 5.2 失败项：遮盖三模式

**现象**（Chrome CDP 实测，清除 localStorage 后）：

- 初始按钮「遮盖：中文」。
- 点一次 →「遮盖：双向」；再点 →「遮盖：中文」；**「遮盖：日语」「遮盖：关」永远到不了**。
- 翻 3 次词卡后再点一次：从「双向」直接跳到「关」（跳过 3 个状态）。
- 语法卡上的「切换遮盖」按钮：`all → ja → all → ja`，`zh` 与 `both` 同样不可达。

**根因**（代码级）：

- `web/assets/app.js:90` 在词卡 `render()` 里调用 `initMask()`；
- `web/assets/app.js:165` 在 `DOMContentLoaded` 又调用一次 `initMask()`；
- `initMask()` 每次都执行 `$('#modeBtn').addEventListener('click', ...)`（`app.js:42-44`）和 `.eye` 绑定，**监听器随词卡翻页线性累积**。
- 初始化即有 2 个监听器 → 一次点击走 2 个状态；翻 3 次词卡后 5 个监听器 → 一次点击走 5 个状态。

这是上一轮 B3 的直接残留，且比上一轮更糟：行为取决于用户翻了多少张词卡。

### 5.3 其他网页残留

- 375 宽 Day 1 `scrollHeight=5332`，约 6.6 屏；上一轮「手机 4 屏内」仍未达成（P2）。
- 汉字条 `kchip` 单音时出现尾逗号：`火 カ、`、`歯 シ、`、`誤 ゴ、`（CSS/生成逻辑 cosmetic bug，P2）。
- 听力日仍只有「播放（TTS）/看脚本」，0 道听力题、0 个 `<audio>`；Day 150 素材 44 秒，不足 60–90 秒（上一轮 P0-4 未修，P1）。
- Day 1 的 `review` 为空（首日无到期卡），页面显示「今天没有到期项」，与 12 分钟复习块不完全匹配，但可接受。

---

## 6. 诚实性 — FAIL

| 声明 | 实际 | 判定 |
|---|---|---|
| 2,700 词 / 276 语法 / 620 汉字 | `wc -l` 与 curriculum 去重均为 2700/276/620 | 属实 |
| 6,136 条种子 | 六个 jsonl 合计 **6136** 行属实 | 数字属实 |
| README:95「init 导入 6,136 条种子」 | init 的 `counts` 只有 vocabulary/grammar/kanji/questions/materials，合计 **4636**；1500 条 sentences 未入库 | **失实** |
| README:103「19 项测试」 | 实跑 `Ran 19 tests ... OK` | 属实 |
| README:224/242「49 项 / 49/49 PASS」 | `tests/` 只有 `test_v5.py`，discover 只跑 19 项；49 项是 `archive/tests_v4` 的旧数 | **失实** |
| README:233「1066 条：340 词 / 96 语法 / 140 汉字 / 395 题」 | 实际 2700 / 276 / 620 / 945 / 1500 / 95；这是 v4 旧表 | **失实** |
| README:234「80 天课程」、235「80 页」 | 实际 150 天 / 150 页 | **失实** |
| AI 草稿 | 150/150 个日页页脚有一行「中文释义与翻译为 AI 草稿」；README 只在 v4 段说「无外部教师逐条复核」，没有明确写 AI 草稿 | **页面 PASS / README FAIL** |
| CC-BY-SA 来源 | 150/150 个日页有一行「资源骨架来自 OpenJLPT（CC-BY-SA-4.0）」；无作者、无链接、无版本、无修改说明、无许可证文本；README 中 `OpenJLPT/CC-BY-SA` 出现 **0 次** | **FAIL** |
| README:40「只发原始事件，不发 correct」 | `app.js:124` 把 `correct` 放进 `QUIZ_RESULTS`，`app.js:162` 原样 POST | **失实**（P2） |

结论：核心数量 2700/276/620 和 19 项测试是真的；但 README 仍混着 v4 的 1066/80 天/49 项，且 `init 导入 6136` 与 CC-BY-SA 署名不成立。

---

## 7. 缺陷清单

### P0（阻断级，仍未完全关闭）

| ID | 缺陷 | 证据 |
|---|---|---|
| P0-A | **P0-2 只修了网页端**：`curriculum.question_ids` 133/150 天与当天内容零交集；`start-day` brief 仍发旧题（Day 50 仅 1/6 对齐）；Day 1 网页只有 5 题 | 2.5 / 3.1；`sessions/day-050-brief.md` |

> 其余两项 P0（覆盖、init）已关闭；没有发现新的阻断级问题。

### P1（高）

| ID | 缺陷 | 证据 |
|---|---|---|
| P1-1 | 遮盖三模式失效：`initMask()` 在每次词卡 render 时重复绑定，日语/关不可达，行为随翻页次数变化 | 5.2；`app.js:90,165,42` |
| P1-2 | 句子块与当天课程脱节：1464/1500 零关联，1484/1500 hint 与答案不符；Day 1 就是 N3 敬语句 | 4.4 |
| P1-3 | 内容硬错误 6 处：V0505 例句、V1827 词性、G0071 规则、K0336 活、K0383 置、K0597 歯 | 4.1 |
| P1-4 | Day 150 一天 24 个新汉字，节奏不可执行 | 1.5 |
| P1-5 | `web/data/answer-key.json` 公开可访问（395 条答案），且 466/899 题 `rationale` 含正确选项明文 | 2.3 |
| P1-6 | README 仍是 v4 数据表（1066/80 天/80 页/49 项），与 v5 冲突；`init 导入 6136` 不实 | 6 |
| P1-7 | 听力日仍 0 题、0 音频，只有 TTS 读稿；Day 150 素材 44 秒 | 5.3；`listening_material.audio_url=""` |
| P1-8 | 38 词无例句；26 词 `pos="词"`；1839/2700 词无 `ko_hanja`；480 汉字 `vocab_refs` 空 | 4.4 |
| P1-9 | 听力首日仍是 Day 47 而非 Day 46（`day 46 listening=false`），与 meta「listening_from=46」不一致 | 1.5 复算 |

### P2（中低）

| ID | 缺陷 | 证据 |
|---|---|---|
| P2-1 | Day 1 只有 5 题，但 block 写「6 题」 | 2.1 |
| P2-2 | `kchip` 单音尾逗号：`カ、` `シ、` `ゴ、` | 5.3 |
| P2-3 | `init --root` 的站点构建忽略 root，写到脚本所在仓库 | 3.3 |
| P2-4 | Day 1 `G0261` 使用 です 但未声明依赖 `G0001`；21 条语法无先修 | 1.4 |
| P2-5 | `V0907` 释义与注释矛盾；`G0005` 用「空格分写」凑常见错误 | 4.2 |
| P2-6 | 375 宽首屏约 6.6 屏，未达 4 屏目标 | 5.3 |
| P2-7 | README 说同步「不发 correct」，代码实际发送 | 6 |
| P2-8 | `tests/test_v5.py` 直接改写仓库内 `STATE.md` 与 `tasks/done/day-001-tutor.md`（时间戳/昨日摘要），测试不隔离工作树 | 本次跑 19 项测试后 `git status` 出现两处改动，已用 `git checkout --` 还原 |

---

## 8. 剩余最严重的 3 个问题

1. **P0-2 半修：会话/课程真源仍在用错题。** 网页做题已对齐，但 `curriculum.question_ids` 133/150 天零对齐，Day 50 brief 6 题只有「壊す」1 题命中，Day 1 网页还少 1 题。学生按文档走「网页 + 会话」两条链路时，得到的题目质量不一致。
2. **遮盖三模式仍坏。** 重复绑定导致「中文 ↔ 双向」二态循环，日语和关不可达；翻词卡越多，一次点击跳得越远。这是本轮要求明确检查的核心交互，且上一轮就报过。
3. **内容硬错误 6 处，其中读音错误会直接教错。** 最典型是 `K0597 歯` 混入「齢」的 `よわい`，并原样进入 Day 150 第 4 题解析；`K0336 活` 生造 `い.きる/い.かす/い.ける`。其次是 `V0505 グラム` 的例句其实是 program，`V1827 禁煙` 词性错，`G0071` 规则过度绝对。

> 第 4 名（同级严重）：句子输出块 1464/1500 与当天课程无关、1484/1500 提示词错误，Day 1 即出现 N3 敬语——这一块占每日页面 1/5，但对 0 基础学生基本不可用。

---

## 9. 复现命令与证据位置

```bash
# 1) 覆盖
python3 - <<'PY'  # 见本报告 1.1；读取 curriculum.json 与 seeds，统计去重/块/先修
PY

# 2) 练习
python3 - <<'PY'  # 统计 web/data/day-*.json 的 quiz 数、prompt 命中、h/oh 一致性
PY

# 3) CLI（隔离副本）
rsync -a --exclude .git --exclude data/state.db ./ /tmp/nh80_after_review/
mkdir -p /tmp/nh80_after_root/{knowledge/seeds,curriculum}
cp knowledge/seeds/*.jsonl /tmp/nh80_after_root/knowledge/seeds/
cp curriculum/curriculum.json /tmp/nh80_after_root/curriculum/
cd /tmp/nh80_after_review
python3 scripts/nh80.py --root /tmp/nh80_after_root init
python3 scripts/nh80.py --root /tmp/nh80_after_root validate

# 4) 网页（Chrome 156 headless + CDP）
cd web && python3 -m http.server 8765
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
  --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-nh80 about:blank
# 通过 CDP 设置 375×812 / 1280×900，点击 #modeBtn、#vNext、#quiz .opt 取证
```

- 本报告未修改任何源码；仅新增本文件。
- 临时目录：`/tmp/nh80_after_review`、`/tmp/nh80_after_root`、`/tmp/chrome-nh80`、`/tmp/cdp_*.mjs`。
