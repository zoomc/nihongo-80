# v5 对抗式复审报告

- 审查对象：`/Users/mj/Documents/learn/jp/nihongo-80`（v5，2026-11-07 工作树）
- 审查方式：只读源码/数据 + 独立复算 + 临时副本跑命令 + Chrome headless 实测；未改源码，未 commit
- 审查范围：`docs/v5/00–04`、`README.md`、`knowledge/seeds/*`、`curriculum/curriculum.json`、`web/`、`scripts/session_v5.py`、`scripts/build_v5_site.py`、`scripts/curriculum_v5.py`、`scripts/nh80.py`、`tests/test_v5.py`
- 临时协议测试目录：`/tmp/nh80_review`（仓库副本，避免污染工作树）

## 1. 总分

| 维度 | 分数 | 结论 |
|---|---:|---|
| 内容准确性 | **4/10** | 主体释义能看懂，但抽检到硬错误、把正确日语判错、例句机翻腔、大量复用 |
| 网页体验 | **5/10** | 5 块和响应式框架成立；遮盖、判分、发音、听力、完成块、答案隔离均有硬伤 |
| 课程结构 | **3/10** | 150 天/60 分钟/无重复这些“壳”成立；内容排课与教学法基本没有落地 |
| 协议可落地 | **6/10** | `daily`/`task` 能跑，并发能拒绝；但文档命令不存在、STATE 有错、DB 与 v5 脱节 |
| 诚实性 | **4/10** | 2700/276/620/6136/17 字面属实；但 init、49 项测试、1066 种子、课程覆盖等说法失实 |
| **总分** | **4.4/10** | 简单平均 |

按本报告 50 项细目：**PASS 18 / PARTIAL 5 / FAIL 27**。

## 2. 细目清单

### 2.1 内容准确性（8 项）

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| A1 | 随机 30 条词汇（N5/N4/N3 各 10） | PARTIAL | 30 条中约 8 条有硬伤或明显不自然，见 6.1 |
| A2 | 随机 15 条语法（pattern/接续/例句/common_errors/ko） | FAIL | 3/15 把正确日语判成错：G0038、G0045、G0215；G0025 可疑 |
| A3 | 随机 10 个汉字（读音/释义/ko） | PARTIAL | 读音大体可用；480/480 新排汉字 `vocab_refs` 为空，73 个无训读 |
| A4 | 随机 10 道题（唯一正确/答案在选项/解析） | PARTIAL | Q0026 题干与答案错位；排序题在网页不可答；听力题无音频 |
| A5 | 空字段统计 | FAIL | 38 词无例句；480 汉字无 `vocab_refs`；21 语法无 `prerequisites` |
| A6 | 重复/复用统计 | FAIL | 89 条例句重复；1050/1500 句子就是词条例句；330/945 题被反复使用 |
| A7 | 机翻腔/英文残留 | PARTIAL | 中文机翻腔可举 4 例；英文残留未发现 |
| A8 | `wrong == fix` / `ko_hanja` 乱填 | PASS | 374 条 `common_errors` 中 exact `wrong==fix` 为 0；抽样未见韩语乱填 |

### 2.2 网页（15 项）

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| B1 | 375×812 五块都在 | PASS | `review/vocab/grammar/sentences/quiz` 五个 section 均在，`h2` 为 ①–⑤ |
| B2 | 375×812 无横向滚动 | PASS | `scrollWidth=375, innerWidth=375` |
| B3 | 遮盖中文/日文/双向按钮 | FAIL | 一次点击从“中文”直接跳到“双向”，再点回“中文”；“日语/全显”不可达 |
| B4 | 词卡翻页 | PASS | 会う → 青 → 会う，上一张/下一张正常 |
| B5 | 练习判分 | FAIL | 排序题 answer=`2,3,1,4`，选项是词块文本，点任何项都判错；分数只按已答题数累计 |
| B6 | 句子草稿刷新保留 | PASS | 输入“テスト草稿”后 reload，值仍为“テスト草稿” |
| B7 | 1280×900 两栏、目录可用、无横滚 | PASS | `grid-template-columns: 200px 760px`，TOC sticky，`scrollWidth=1280` |
| B8 | 首屏加载/页面大小 | PASS | HTML 13,875 B + JS 8,276 B + CSS 4,068 B = 26,219 B；本地 FCP 52 ms、load 41 ms |
| B9 | 手机 4 屏内 | FAIL | 375 宽度下 `body.scrollHeight=5252`，约 6.5 屏；语法 1,179 px、句子 1,745 px、练习 1,422 px |
| B10 | 发音按钮 | FAIL | 150 页中仅 45 页各有 1 个 TTS 按钮（听力日），词卡/语法 0 个；无 `<audio>` |
| B11 | 听力日有音频+3 题 | FAIL | 听力块只有“播放（TTS）/看脚本”，0 题、0 `<audio>` |
| B12 | 汉字块 | FAIL | 网页 5 块没有汉字块；`day-001.json` 无 `kanji` 字段，480 个新排汉字学生端看不到 |
| B13 | 今日完成/同步状态 | FAIL | 页面只有“今天学完了，记录一下”按钮；无正确率/错题/同步状态/重试 |
| B14 | 答案不进页面 | FAIL | `web/day-001.html:64` 内嵌 `window.__QUIZ__` 的 `answer`；`window.__SENT__` 也含参考答案 |
| B15 | 残留热力图/雷达/时间块/回传码大面板 | PASS | 150 个 `day-*.html` 中 0 命中；仅 `404.html`/`manifest`/`n3-mock.html` 有旧文案，不构成日页面板 |

### 2.3 课程（9 项）

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| C1 | 150 天、blocks 合计 60、无重复、总量 | PASS | 150 天；`Counter({60: 150})`；新 ID 无重复；新词 2360 + 旧 340 = 2700，语法 180 + 96 = 276，汉字 480 + 140 = 620 |
| C2 | 听力 Day 46 起、每周 3 次、`day%7 in {1,3,5}` | FAIL | 共 45 天，`mod7={1:15,3:15,5:15}` 正确；但第一天是 **47**，Day 46 `listening=false` |
| C3 | 旧 340 词/96 语法/140 汉字是否排课 | FAIL | `curriculum_v5.py:104-107` 明确只排 `>340/>96/>140`；三项旧内容在 150 天中 0 次出现 |
| C4 | 每周复盘日、周测 | FAIL | 150 天全部有 12/17/18 个新词；0 个“不学新词”的复盘日；21 个 `weekly` 只是标签 |
| C5 | 阶段测/模考内容 | FAIL | Day 45/95/130 标 `stage`，Day 110/132/148 标 `mock`；页面与 blocks 无任何测试内容，`n3-mock.html` 未从日页链接 |
| C6 | 语法先修 | FAIL | 182 条先修指向从未排课的 ID；96/276 条语法从未出现；Day 1 的 G0247 依赖 G0001（です），G0001 不在任何一天 |
| C7 | 素材与场景一致 | FAIL | 150 天中 **143 天**素材主题与 `scene_topic_key` 不符；例如 Day 2 场景 family、素材 shopping |
| C8 | 每日题目与当天内容对齐 | FAIL | **150/150 天**题目 target 与当天新词/语法/汉字/复习交集为空；Day 1 教 G0247/G0248，题考 G0001 |
| C9 | Day 1/45/46/95/110/150 抽查 + 听力素材 | FAIL | 新词 18/17/17/17/12/12（计划 8/16/16/16/11/11）；Day 45 全 read，Day 95 全 translate，Day 150 全 dialogue；听力素材 0 题、0 音频 |

### 2.4 会话协议（10 项）

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| D1 | `session_v5.py daily --day 1` 生成 STATE/brief | PASS | 命令返回 0，生成 `days/day-001/brief.md` 与 `STATE.md` |
| D2 | `task new/claim/done` | PASS | 均返回 `ok:true`，文件从 open → claimed → done，front matter 更新 |
| D3 | 并发 claim 两次被拒 | PASS | 两个进程同时 claim：一个 `{"ok": true}`，一个 `{"ok": false, "error": "already_claimed"}` |
| D4 | 12 小时租约 | FAIL | 代码只建 `.lock`，从不检查时间；claim 后不自动过期，文档的“12 小时”无实现 |
| D5 | 任务卡 front matter 自洽 | PASS | `owner/status/claimed_at/done_at` 与目录一致；`depends_on` 为空 |
| D6 | brief 泄露答案 | PASS | `brief.md` 无 `answer` 字段；仅有“ 不把答案写进本文件” |
| D7 | STATE.md 正确性 | FAIL | `STATE.md:4` 写成 `P0 P0`；`昨日摘要`读的是**当天** report；无 DB 正确率/到期数 |
| D8 | 文档 CLI 可执行 | FAIL | `docs/v5/02` 要求 `nh80 task/state/daily`；`nh80.py` 没有这些子命令，只有 `session_v5.py` |
| D9 | `finish-day` 可执行 | PARTIAL | 先 `start-day` 后 `finish-day` 能跑，但它写的是 v4 的 80 天 DB，不是 v5 |
| D10 | report.md 模板 | PASS | `session_v5.py report --day 1` 生成含「摘要」的模板 |

### 2.5 诚实性（8 项）

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| E1 | 2700/276/620/6136 字面属实 | PASS | `wc -l` 精确为 2700/276/620/945/1500/95，合计 6136 |
| E2 | 17 项测试属实 | PASS | `Ran 17 tests ... OK` |
| E3 | README 的“49 项测试”属实 | FAIL | `tests/` 只有 `test_v5.py`；实际 17 项；README:223/241 仍写 49 |
| E4 | README 的“1066 条种子”属实 | FAIL | 实际 6136 条；README:233 仍是 v4 的 1066/340/96/140 |
| E5 | README 的 init 生成 150 天 | FAIL | `nh80.py init` 直接报课程校验失败；成功路径 `nh80.py:242` 写死 `days: 80` |
| E6 | AI 草稿 vs 人工审校 | PASS | 页面页脚明说“AI 草稿”；README 说无外部教师逐条复核；未发现冒充人工审校 |
| E7 | OpenJLPT CC-BY-SA-4.0 署名/许可 | FAIL | 仅页脚一行“OpenJLPT（CC-BY-SA-4.0）”，无作者/链接/修改说明/许可证文本；README 无 |
| E8 | 17 项测试能证明 v5 可用 | FAIL | 测试只查数量和关键词，不查内容准确性、答案缺失、听力题、判分可解、init 可重建 |

## 3. 内容准确性抽样

### 3.1 词汇 30 条（N5/N4/N3 各 10）

抽样命令：分层随机，seed=20261107。以下为明确问题：

| ID | 问题 | 具体 |
|---|---|---|
| V0519 `ここ` | 缺例句 | `examples` 为空，网页词卡只剩词形/假名/释义 |
| V0900 `以外` | 词性非法 | `pos="词"`，不是可用的日语词性标签 |
| V1113 `失敗` | 词性错误 | 标成“名词/动词(サ变)/**他动词/自动词**”；`失敗する` 是自动词 |
| V2415 `地区` | 注释事实错误 | 注“与「地球」同音不同字”；`地区=ちく`、`地球=ちきゅう`，不同音 |
| V0890 `アナウンサー` | 例句不自然 | “アナウンサーは早口が出来る。”应为「早口で話せる」等；中文“播音员能说得很快”是直译 |
| V1394 `もっとも` | 中文不通 | “健在三跑得最快”应为“三个人里跑得最快” |
| V2629 `軒` | 读音注释混淆 | 词卡 kana 是 `のき`，注却说“也作量词「…栋」”；量词读 `けん` |
| V0354 `あそこ` | 例句不当 | “先生、アソコがかゆいんです。”是成人向双关，不适合 N5 入门词卡 |
| V0652 `テーブル` | 例句/翻译生硬 | “このテーブルを頼んだのではない。”译“我点的不是这张桌子”，语义场景不自然 |
| V0422 `遅い` | 中文别扭 | “晚做总比不做好”与“遅くなっても何もないよりはまし”语感有偏差 |

未发现假名与词形明显不匹配的样本；`ko_hanja` 抽样未见乱填，但 2700 条中只有 861 条有值，1839 条为空（和语词可解释，但页面没有按要求写“无直接对应”）。

### 3.2 语法 15 条

| ID | 问题 | 具体 |
|---|---|---|
| G0038 | 把正确日语判错 | wrong=`雨が降るなら、行きません。`；「なら」在承接对方话题/假定条件下可用，不能一律判错并强制 `たら` |
| G0045 | 把正确日语判错 | wrong=`雨かもしれないです。`；这是广泛使用的礼貌口语形式，不是语法错误 |
| G0215 | 把可接受形式判错 | wrong=`駅で三十分も待たせられました。`；`待たされる`更常用，但`待たせられる`也是合法使役受身 |
| G0025 | 可疑 | wrong=`雨が降ると、行きません。`；一般条件/习惯句可成立，至少不是“绝对不合法” |
| G0078 | 一张卡塞 3 个句型 | pattern=`N + に基づいて / を もとに / どおり(に)`，接续也写三段；不符合“一条语法一张卡” |

`ko_equiv/ko_diff` 多数合理，但 G0215 的 `-게 시킴을 당하다` 不是自然韩语，正常说法是 `-하도록 강요받다` 一类。

### 3.3 汉字 10 个

抽样未见“读音完全错”的硬错误；问题主要在完整性和可用性：

- 480/480 个新排汉字 `vocab_refs` 为空，和词汇完全脱节。
- 73 个汉字无训读（部分如 `込/畑` 是国字，合理；其余未区分）。
- `K0001 日` 没有 `ko_hanja`，但 `K` 表整体有 475/620 有值，核心字反而缺。
- `K0255 悪` 收入 `ああ/いずくに/いずくんぞ` 等古语训读，对 N4 卡片是噪音。
- `K0184 体` 收 `かたち`，属于词典级罕见训读，不适合作为入门卡片的主读音。

### 3.4 题目 10 道

| ID | 问题 | 具体 |
|---|---|---|
| Q0026 | 题干与答案错位 | 题干“请用过去式写一句「昨天是星期几」”，期望答案却是`昨日は土曜日でした。`（陈述句，不是问句；且答案不唯一） |
| Q0005 | 网页不可答 | 题干排序，`answer="2,3,1,4"`，网页选项是`です/私は/学生/。`，字符串永远不相等 |
| Q0003 | 听力题无音频 | 标注“听录音”，网页 quiz 不播放 `audio_text`，只能看选项猜 |
| Q0251 | 听力题无音频 | 同上；`audio_text` 有对话，但页面没有播放按钮 |
| Q0764 | 解析含生僻音 | `求` 注“音读 キュウ、グ”；`グ` 是词典古音，对 N3 学习者是噪音 |

MCQ 抽样均满足“答案在选项内、选项不重复、只有一个文本正确答案”；解析方向基本正确。

### 3.5 统计数字

```text
V 2700  G 276  K 620  Q 945  S 1500  M 95  => 6136
V examples 空: 38
K vocab_refs 空: 480
K kunyomi 空: 73
G prerequisites 空: 21
V ko_hanja 非空: 861 / 2700
G common_errors: 374 条，wrong==fix: 0
V 同形异读: 17 组（私/四/七/何/今日/明日/上/中/後/開く/角/辛い/背/空/音/工場/日）
例句重复: 89 组
句子与词条例句完全相同: 1050 / 1500
题目使用: 330 / 945；同一组 6 题重复约 3 次
英文残留: 0（`meaning_zh` 中未发现英文）
```

## 4. 网页实测

环境：`python3 -m http.server 8099 -d web`；Chrome headless（`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`）+ puppeteer-core。

### 4.1 375×812

```text
sections: review, vocab, grammar, sentences, quiz
scrollWidth 375 / innerWidth 375   -> 无横向滚动
body.scrollHeight 5252             -> 约 6.5 屏（目标 4 屏）
section heights: 68 / 394 / 1179 / 1745 / 1422
vocab total: 18
quiz count: 6
sentences: 10
```

- 5 块齐全；词卡翻页正常；句子草稿刷新保留；MCQ 判分正常。
- 遮盖按钮实测：

```text
初始: 遮盖：中文   zh=mask  ja=visible
点击1: 遮盖：双向  zh=mask  ja=mask
点击2: 遮盖：中文  zh=mask  ja=visible
点击3: 遮盖：双向
点击4: 遮盖：中文
```

原因：`initMask()` 在 `initVocab().render()` 中重复调用，`#modeBtn` 被绑定多次；一次点击执行多次 `setMode`，跳过 `ja`/`all`。语法卡的眼睛按钮同样被重复绑定，`all → ja` 跳过 `zh`。

- 练习实测：第 1 题点“です”得 `1/1`；第 5 题排序点“私は”得到：

```text
错，正确答案：2,3,1,4。主题 は 在前，名词 + です 收尾，句号最后
score: 1 / 2
```

- 听力日 Day 47：

```text
sections: review, vocab, grammar, sentences, quiz, listening
listening innerText: ⑥ 听力 / 8 分钟 / 先听，再答题；脚本做完再展开。/ 播放（TTS）/ 看脚本
listening 内题目数: 0
<audio> 数: 0
```

- 发音按钮统计：`rg -o 'data-speak=' web/day-*.html | wc -l` = 45，全部在 45 个听力日；词卡/语法 0。

### 4.2 1280×900

```text
grid: 200px 760px
TOC position: sticky
scrollWidth 1280 / innerWidth 1280
点击 #quiz 后 location.hash = #quiz
```

两栏、目录、无横滚均成立。

### 4.3 性能与体积

```text
HTTP: 200, 13,875 bytes, 0.003 s（本地静态服务器）
assets: app.js 8,276 B + app.css 4,068 B
FCP 52 ms, DOMContentLoaded 36 ms, load 41 ms（本地；未做 4G 真机）
150 页 HTML 合计 2.4 MB
```

按体积和本地指标，首屏 ≤1.5 秒风险低；但没有 4G 真机证据，不能把“已验收”写死。

## 5. 课程结构实测

### 5.1 成立的部分

```text
days: 150
block minute sums: Counter({60: 150})
new vocab IDs: 2360 unique
new grammar IDs: 180 unique
new kanji IDs: 480 unique
vocab/day: 12×45, 17×70, 18×35
grammar/day: 1×120, 2×30
kanji/day: 3×120, 4×30
```

### 5.2 不成立的部分

**旧内容完全不排课。** `curriculum_v5.py:104-107`：

```python
new_vocab = [v for v in vocab if int(v["id"][1:]) > 340]
new_grammar = [g for g in grammar if int(g["id"][1:]) > 96]
new_kanji = [k for k in kanji if int(k["id"][1:]) > 140]
```

结果：课程实际只教 **2360 词 / 180 语法 / 480 汉字**。`curriculum/coverage_v5.md` 自己也写“新词 2360｜新语法 180｜新汉字 480”，但 README 标题写 2700/276/620。后者是数据库总量，不是 150 天覆盖量。对“0 基础”学习者，旧 340 词/96 语法/140 汉字等于从未教过。

**先修断裂。** Day 1 教 `G0247 〜は`，其 `prerequisites=["G0001"]`；G0001（`N は N です`）不在 150 天任何一天。Day 1 同时出 Q0001 考 `です`，学生还没学过。Day 46 的 `G0232 〜ために` 依赖 G0023/G0006，也从未出现。全量统计：

```text
prereq violations (含 NEVER): 182
grammar never taught: 96 / 276
```

`nh80.py validate` 也返回 `ok:false`，3 条错误：

```text
Day 45 语法 G0234 的先修 G0064 尚未出现
Day 45 语法 G0241 的先修 G0053 尚未出现
Day 45 语法 G0242 的先修 G0096 尚未出现
warnings: 41
```

**题目与当天内容零对齐。** `curriculum_v5.py:158-171` 按 JLPT 池顺序每 6 题切片，不看当天 `new_vocab_ids/new_grammar_ids`。复算：

```text
days with zero question target overlap: 150 / 150
unique questions used: 330 / 945
same 6-question set repeated: 3 times
Day 1: Q0001-Q0006 targets G0001/V0001...；当天新语法 G0247/G0248
Day 45: Q0265-Q0270 全是 read
Day 95: Q0295-Q0300 全是 translate
Day 150: Q0325-Q0330 全是 dialogue
```

**素材与场景脱节。** `curriculum_v5.py:143-156` 只按 level 选“最少使用”的素材，完全不看 `scene_topic_key`。复算 143/150 天不匹配：

```text
Day 2  场景 family   素材 topic shopping
Day 3  场景 food     素材 topic transport
Day 7  场景 work     素材 topic greeting
Day 46 场景 greeting 素材 topic ...
```

**没有复盘日/周测/阶段测/模考内容。** 150 天每天都有新词；`assessment` 只是字符串：

```text
assessment: none 122, weekly 21, stage 3, mock 3, diagnostic 1
days with zero new vocab: 0
days with zero new grammar: 0
```

**听力日名不副实。**

```text
listening days: 45, 第一天 47（不是 46）
materials: 95
audio_url 非空: 0
audio_kind: tts 95
materials.questions 非空: 0 / 95
Day 47  M0014 33 字，topic tech
Day 110 M0052 97 字，topic work
Day 150 M0094 219 字，topic work
```

计划要求“1 段 60–90 秒 + 3 题”；实际是 TTS 读 27–219 字短文，无题、无外部音频。

**抽查六天：**

| Day | 新词 | 语法 | 汉字 | 听力 | 主要问题 |
|---|---:|---:|---:|---|---|
| 1 | 18 | G0247/G0248 | 4 | 否 | 计划 P0 是 8 词/3 语法/0 汉字；题考 G0001；无 です 先修 |
| 45 | 17 | G0231 | 3 | 否 | 标 `stage` 但无阶段测；6 题全 read；先修 G0023 未教 |
| 46 | 17 | G0232 | 3 | 否 | 文档说 Day 46 起听力，实际不是；场景回到 greeting |
| 95 | 17 | G0131 | 3 | 否 | 标 `stage` 但无测试；6 题全 translate |
| 110 | 12 | G0146 | 3 | 是 | 标 `mock` 但无模考；听力素材 97 字、0 题 |
| 150 | 12 | G0186 | 3 | 是 | 6 题全 dialogue；听力 219 字、0 题 |

## 6. 会话协议实测

在 `/tmp/nh80_review` 副本执行（避免污染工作树）。

```text
$ python3 scripts/session_v5.py daily --day 1
/private/tmp/nh80_review/days/day-001/brief.md
/private/tmp/nh80_review/STATE.md
https://nihongo80.cmjfire.workers.dev/day-001.html
```

`STATE.md`：

```text
- 当前：Day 001 / 150（P0 P0）
- 今日：days/day-001/brief.md ｜ 60 分钟 ｜ 常规日
- 昨日摘要：无（还没写日报）
```

- `P0 P0` 是 `phase_name=phase_of(d)[0]` 导致（`session_v5.py:227`）。
- `昨日摘要` 实际读 `days/day-{day}/report.md`（`session_v5.py:218`），永远读当天，不是昨天。
- STATE 不读 `state.db`，所以没有正确率、到期数、卡点 Top3。

`brief.md`：

- 18 个新词、2 条语法、4 个汉字，含假名/释义/朝鲜语；
- 无 `answer` 字段，只有“ 不把答案写进本文件”；
- 但写“会话流程（18 分钟）”，课程 block 实际是 21 分钟会话。

任务卡：

```text
$ task new --day 1
tasks/open/day-001-tutor.md
$ task claim ... --owner alice
{"ok": true, ...}
$ task claim ... --owner bob
{"ok": false, "error": "not_open"}
```

并发（两个进程同时 claim 同一 open 任务）：

```text
A: {"ok": false, "error": "already_claimed"}
B: {"ok": true, "task": ".../tasks/claimed/day-099-tutor.md"}
```

并发拒绝成立；但 `claim` 只建 `.lock`，没有 12 小时过期逻辑；sequential 第二次报 `not_open` 而不是 `already_claimed`。`task done` 不校验 owner，bob 可以把 alice 的卡标 done。

**文档 CLI 不存在：**

```text
$ python3 scripts/nh80.py state --write
nh80.py: error: argument cmd: invalid choice: 'state'

$ python3 scripts/nh80.py task list
nh80.py: error: argument cmd: invalid choice: 'task'

$ python3 scripts/nh80.py daily
nh80.py: error: argument cmd: invalid choice: 'daily'
```

`docs/v5/02_SESSION_PROTOCOL.md:100-108` 和 `:187-188` 均按这些命令写。

**v4/v5 双轨：**

```text
$ python3 scripts/nh80.py start-day 1
主题：初次见面｜N は N です・私・学生
（v4 内容，不是 v5 的 会う/青/あ行 18 词）

$ python3 scripts/nh80.py finish-day 1
{"ok": true, "day": 1, "attempts": 0, "accuracy": null, "status": "incomplete", ...}
```

`start-day`/`finish-day` 读写的是 `data/state.db` 的 80 天 v4 课程；`session_v5.py` 只写 `progress.json`/STATE/brief，不写 DB。两条协议讲不同的 Day 1。

当前 `data/state.db`：

```text
vocabulary 260
grammar 85
kanji 140
curriculum_days 80
fsrs_cards 0
knowledge_state 0
attempts 0
sessions 0
```

所以“DB 是唯一数值真源”在 v5 里没有落地：v5 的 2700/276/150 在 JSONL/JSON，DB 仍是 v4；网页 `build_review` 读这个 DB，FSRS 卡片为 0，只能用 `review_knowledge_ids` 当“计划复习”，不是真实到期。

## 7. 诚实性核查

### 7.1 属实的数字

```text
vocabulary 2700
grammar 276
kanji 620
questions 945
sentences 1500
materials 95
total 6136
tests 17
```

`wc -l knowledge/seeds/*.jsonl` 与 `unittest` 输出一致。

### 7.2 失实/陈旧的说法

- `README.md:94`：“`init` 会……生成 Day 1–150 课程 → 生成 150 个网页”。实际 `python3 scripts/nh80.py init` 在临时副本直接失败：

```text
{"ok": false, "error": "课程校验失败：['Day 45 语法 G0234 的先修 G0064 尚未出现', ...]", "type": "ValueError"}
```

  即使修好校验，`nh80.py:242` 仍写 `days: 80`，`cmd_build` 调的是 v4 `build_site.py`，会覆盖 v5 页面。

- `README.md:223` 与 `:241`：“49 项自动验收 / 49 项全部通过”。实际 `tests/` 只有 `test_v5.py`，17 项。
- `README.md:233`：“1066 条种子，340 词、96 语法、140 汉字、395 题”。实际 6136 条，2700/276/620/945；这是 v4 段落未更新。
- `README.md:235-236`：“80 天课程 / 80 页”。实际工作树是 150 天/150 页；README 内部自相矛盾。
- 标题 2700/276/620 字面属实，但课程实际覆盖 2360/180/480；`coverage_v5.md` 自己写了这个差异。把“数据库总量”当“150 天覆盖量”是误导。

### 7.3 AI 草稿

未发现“人工审校”的虚假声明：

- 页脚：`资源骨架来自 OpenJLPT（CC-BY-SA-4.0），中文释义与翻译为 AI 草稿`
- README:44：`没有外部日语教师逐条复核（review_status=self_reviewed）`

但 v5 的 `review_status` 实际是：

```text
vocab: ai_draft 2360 / verified 337 / needs_review 3
grammar: ai_draft 180 / self_reviewed 96
kanji: ai_draft 480 / verified 132 / needs_review 8
```

README 没有披露“新增内容 2360/180/480 全部是 ai_draft”，只在页面页脚提了一句。属于披露不足，不是冒充人工。

### 7.4 OpenJLPT 署名

页面页脚只有一行名称 + 许可证简称：

```text
资源骨架来自 OpenJLPT（CC-BY-SA-4.0），中文释义与翻译为 AI 草稿
```

缺少 CC-BY-SA-4.0 要求的作者/来源 URL/许可证链接/修改说明；README 与 `docs/v5` 没有署名；仓库没有 `LICENSE`/`ATTRIBUTION` 文件。数据字段 `license: CC-BY-SA-4.0` 是内部记录，不等于对外合规署名。

## 8. P0/P1/P2 缺陷

### P0（阻断）

| ID | 缺陷 | 证据 |
|---|---|---|
| P0-1 | 150 天只教新增 2360/180/480；旧 340 词/96 语法/140 汉字从未出现；0 基础 Day 1 缺 です 先修 | `curriculum_v5.py:104-107`；`coverage_v5.md`；182 条先修未满足 |
| P0-2 | 每日题目与当天内容 150/150 零对齐；330/945 题反复用；Day 45/95/150 题型单一 | 复算；`curriculum_v5.py:158-171` |
| P0-3 | 练习不可用/可作弊：答案内嵌；排序题 answer=`2,3,1,4` 不可答；非选择题压成“答案/以上都不是”；结果不上报 | `web/day-001.html:64`；`build_v5_site.py:444-454`；`app.js:114-119` |
| P0-4 | 听力日没有听力题：95 素材 0 题、0 audio_url；Day 47 素材 33 字；网页只 TTS 读稿 | `materials.jsonl`；`build_v5_site.py:456-471` |
| P0-5 | `nh80 init/build` 不能生成 v5：init 报 3 个校验错误；成功路径是 80 天 v4，会覆盖 v5 页面；DB 仍是 80 天/260 词 | `nh80.py:214-244`；临时副本 init 输出 |
| P0-6 | v5 没有 FSRS 写回链路：网页 `results: []`，quiz 无 `id`，`session_v5.py` 不写 DB；`state.db` 的 `fsrs_cards=0` | `app.js:163-172`；`build_v5_site.py:453-454`；DB 计数 |

### P1（严重但可绕过）

| ID | 缺陷 | 证据 |
|---|---|---|
| P1-1 | 遮盖按钮只在中/双向之间跳；“日语/全显”不可达；语法眼睛跳状态 | `app.js:19-45`；headless 实测 |
| P1-2 | 手机 5,252 px ≈ 6.5 屏，超过 4 屏目标 | 375×812 实测 |
| P1-3 | 词卡/语法无发音按钮；150 页仅 45 个听力 TTS | `rg data-speak` = 45；`audio:null` |
| P1-4 | 网页没有汉字块，480 个新排汉字学生端不可见 | `day-001.json` 无 `kanji` 字段 |
| P1-5 | 没有“⑥ 今日完成”块；无正确率/错题/同步状态/重试；`results` 永远空 | 页面只有 finish 按钮；`app.js:165` |
| P1-6 | 每周复盘日/周测/阶段测/模考只有 `assessment` 标签，无内容 | 0 个零新词日；blocks 恒为复习/新词/语法/练习/会话 |
| P1-7 | 语法 3/15 把正确日语判错；G0038/G0045/G0215 | `grammar.jsonl:38/45/215` |
| P1-8 | 句子输出方向错：7 中→日 + 3 日→中，0 韩→日；1050/1500 是词条例句 | `sentences.jsonl`；`web/day-001.html:64` |
| P1-9 | 素材场景 143/150 不匹配 | 复算；`curriculum_v5.py:143-156` |
| P1-10 | 新词量超标：18/17/12 vs 计划 8/16/11 | `coverage_v5.md` |
| P1-11 | STATE `P0 P0`、昨日读今天、无 DB 数值 | `session_v5.py:218/227` |
| P1-12 | 文档 CLI `nh80 task/state/daily` 不存在；`finish-day` 走 v4 | `docs/v5/02:100-108/187-188`；CLI 输出 |
| P1-13 | 答案进页面：quiz answer + 句子 answer | `web/day-001.html:64`；`web/data/day-001.json` |
| P1-14 | PWA 未注册：`sw.js` 存在但日页无 `serviceWorker.register`/manifest link | `rg serviceWorker` 无结果 |
| P1-15 | OpenJLPT 署名不合规 | 页脚一行；README 无 |

### P2（质量/维护）

- `V0900` 等 26 个词 `pos="词"`；`名詞/名词`、`動詞/五段/动词(五段)` 混用。
- 89 组重复例句；`V0519` 等 38 词无例句。
- 480 个新排汉字 `vocab_refs` 全空；`K0001 日` 无 `ko_hanja`。
- G0215 的 `ko_equiv` 不是自然韩语。
- 17 组同形异读本身合理，但未在卡面区分读音场景（如 `私 わたし/わたくし`）。
- `.lock` 无过期；`task done` 不校验 owner；sequential claim 错误码是 `not_open`。
- `404.html`/`manifest.webmanifest`/`n3-mock.html` 仍是 v4 文案（回传码/80 天）。
- 页面 header 写“60 分钟”，设计写网页 42 分钟；5 块文案与 6 块完成目标混用。
- 打印样式只有单列，不是设计的 A4 两栏；字体三档、`prefers-reduced-motion`、键盘快捷键、长按固定、`peeked` 审计均未实现。
- 80/276 条语法 pattern 含 `/`，把多个句型塞一张卡。

## 9. 最严重的 3 个问题

1. **课程把“已有内容”当成已学，150 天实际只教 2360/180/480。**
   旧 340 词、96 语法、140 汉字一次都不出现；Day 1 教 `は/が`，但 `です`（G0001）从未排课；182 条先修关系不满足。对“0 基础”学习者，第一天就断链。`curriculum_v5.py:104-107` 与 `coverage_v5.md` 都证明了这一点，README 的 2700/276/620 只是库总量。

2. **每日练习与当天课程零对齐，而且不可答/可作弊。**
   150/150 天题目 target 与当天新知识无交集；330/945 题循环用；排序题 `answer="2,3,1,4"` 在网页永远判错；非选择题被压成“答案/以上都不是”；`answer` 直接写进 HTML 和 JSON；练习结果 `results: []` 不上报。学生做完练习，既不能证明学会，也不会进入 FSRS。

3. **`nh80.py init/build` 不能重建 v5，且会把人带回 v4。**
   `init` 在临时副本直接报 3 个课程校验错误；`nh80.py:242` 写死 `days: 80`，`cmd_build` 调 v4 `build_site.py`，成功时会覆盖 150 个 v5 页面。当前 `state.db` 只有 260 词/85 语法/80 天/0 FSRS 卡。README:94 的“init 生成 Day 1–150”是假的。

## 10. “文档说做了但代码没做”

| 文档说法 | 代码事实 | 证据 |
|---|---|---|
| 02: `nh80 task list/new/claim/done`、`nh80 state --write`、`nh80 daily` | 这些子命令不存在；实际命令是 `session_v5.py` | CLI 报 `invalid choice` |
| 02: claim 有 12 小时租约 | 只建 `.lock`，无时间检查/回收 | `session_v5.py:172-190` |
| 01: `day-NNN.json` 不含 `answer` | quiz 每项都有 `answer`，HTML 也内嵌 | `build_v5_site.py:453-454`；`day-001.html:64` |
| 01: 10 句 7 韩→日、3 中→日 | 7 中→日、3 日→中、0 韩→日 | `sentences.jsonl` 方向统计 |
| 01: 词卡/例句有发音按钮 | 词卡/语法 0 个，仅听力日 1 个 TTS | `rg data-speak` = 45 |
| 01: 手机 4 屏内 | 5,252 px ≈ 6.5 屏 | 375×812 实测 |
| 01: ⑥ 今日完成（正确率/错题/同步状态） | 只有 finish 按钮 | `day-001.html` 结尾 |
| 01: PWA 静默缓存/离线 | `sw.js` 没有注册，manifest 没有 link | `rg serviceWorker` 无结果 |
| 01: 语法卡有即时题 | 语法卡只有例句/韩语/易错，无即时题 | `build_grammar_html` |
| 01/04: 遮盖支持日语/全显、键盘、长按 | 按钮跳过状态；无键盘/长按/peeked 审计 | `app.js:19-45` |
| 03: 每周第 7 天复盘，不学新词 | 150 天每天都有新词；0 个复盘日 | 课程统计 |
| 03: 阶段测 Day 45/95/130，模考 110/132/148 | 只有 `assessment` 字符串，无测试内容 | `curriculum_v5.py:213-214` |
| 03: 听力 60–90 秒 + 3 题 | 0 题、0 外部音频；采样 33/97/219 字 | `materials.jsonl`；`build_v5_site.py:456-471` |
| 03: 620 汉字 | 只排 480 个新汉字；网页无汉字块 | `curriculum_v5.py:107`；`day-001.json` |
| 04: 1,500 句 70% 韩→日 | 0 韩→日；70% 中→日 | 方向统计 |
| 04: 16 词/天、听力 11 | 17/18 词；听力 12 | `coverage_v5.md` |
| 04: 53+ 测试 | 17 | `unittest` |
| README: init 生成 150 天 | init 失败；成功路径 80 天 v4 | `nh80.py:214-244` |

## 11. 测试结果

```text
$ python3 -m unittest discover -s tests -p "test_v5.py"
.................
----------------------------------------------------------------------
Ran 17 tests in 0.517s

OK
```

结论：**17/17 全绿属实**。但测试只覆盖：

- 文件数量（≥2700/276/620/900/1500）
- 必填字段非空
- grammar 有 ko 且 `wrong != fix`
- 150 天/60 分钟/ID 不重复
- 前 20 页不含 4 个中文仪表盘关键词
- Day 47 有 `id="listening"`
- `daily`/`task` 能跑

未覆盖：内容准确性、`wrong` 是否合法、答案是否进页面、听力题是否存在、排序题是否可答、`init` 是否能重建、`state.db` 是否 v5、`nh80 validate` 是否 0 error。因此“测试全绿”不能作为 v5 可用的证据。

## 12. 复审结论

v5 的**骨架**（150 天、60 分钟、5 块、文件协议、响应式两栏、17 项测试）是真实存在的；但**教学内容与交互闭环**没有完成。当前状态更像“把 2360 条新数据按 ID 顺序切成 150 天，再把旧题/旧句/旧素材循环贴上去”，而不是文档描述的“频率优先、场景驱动、先修门控、FSRS 闭环”。

在修复 P0-1 到 P0-6 之前，不建议把它当作可交付的 0 基础 N3 课程；可以作为“内容草稿 + 页面原型”继续迭代。
