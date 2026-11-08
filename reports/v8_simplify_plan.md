# v8 网页大幅简化 · 只读审查与可执行改动清单

> 状态：**只读审查**，未修改任何源码、未 commit、未重跑构建。
> 基准提交 `f0571dc` (2026-11-08 22:43)。线上 `https://nihongo80.cmjfire.workers.dev/day-001.html` 与本地 `web/day-001.html` **逐字节一致**（`curl` + `diff` 校验通过），因此本文行号对源码与线上产物同时成立。
> 行号约定：`build_v5_site.py:N` = 源模板行；`app.js:N` / `study.js:N` / `app.css:N` = 生成物行（已用内容比对建立映射，见 §0.3）。`web/day-001.html:N` = 生成后的实际页面行。

---

## 0. 先校准三处事实（与任务描述有出入，动手前必须知道）

### 0.1 唯一构建入口是 `nh80 build`，不是直接跑 `build_v5_site.py`

```
python3 scripts/nh80.py build
  └─ nh80.py::_build_v5()          nh80.py:243-297
       ├─ day_questions() / sentence_questions() / build_daily() / build_unit()
       ├─ 写 curriculum/curriculum.json                 :291
       ├─ 写 deploy/worker/src/generated-key.json       :292
       ├─ 写 web/data/grade/day-NNN.json ×150           :293-296
       ├─ 写 data/state.db 的 questions 表 + 清孤儿题    :277-289
       └─ import build_v5_site as s5; s5.main()         :308-309
            └─ build_v5_site.py::main()  :553-841
                 ├─ web/assets/app.css = CSS + study_ui.CSS   :574
                 ├─ web/assets/app.js  = JS                   :575
                 ├─ web/assets/study.js = study_ui.JS         :576
                 ├─ web/day-NNN.html ×150                     :678
                 ├─ web/data/day-NNN.json ×150                :679-684
                 ├─ web/review.html / unit-NNN.html ×30       :586-592
                 ├─ web/index.html / listening.html / resources.html / library.html
                 └─ web/sw.js                                :833-840
```

**所有 `web/` 下的文件都是生成物，禁止手改**；`app.js == build_v5_site.py::JS`、`study.js == study_ui.py::JS`（已 `diff` 验证一致）。

### 0.2 「`nh80.py::_build_v5()` 把题目灌进 `__PRACTICE__`」不准确

`nh80.py::_build_v5()` 只负责登记题目到 DB / `generated-key.json` / grade 分片（`nh80.py:261-282`）。页面上的 `window.__PRACTICE__` 是 `build_v5_site.py::main()` **独立再跑一次** `build_daily()` 得到的：

- `build_v5_site.py:596` → `practice=[public_question(q) for q in build_daily(d,vocab,grammar,kanji)]`
- `build_v5_site.py:651` → `.replace("@@PRACTICE@@", json.dumps(practice, …))`；模板 `:433` 的挂载点是 `window.__PRACTICE__=@@PRACTICE@@;`
- ⚠️ 占位符命名不统一：模板里 `@@PRACTICE@@` / `@@REVIEW@@` / `@@FOCUS@@` 是 `@@…@@` 结尾，而 `@@VOCAB__` / `@@QUIZ__` / `@@SENT__` / `@@LQS@@` 混用下划线；`:672,:673,:677` 把同一个 `@@VOCAB__` 重复替换了 3 次，`:660` 的 `@@MIN@@` 在模板里根本不存在（死替换）。改占位符时必须按实测清单逐个核对，不能凭命名规律猜。
- 两处各算一次，题号靠确定性 `_digest()` 保证一致，**但任何改动必须两边同步改**（`nh80.py::_build_v5()` 与 `build_v5_site.py::main()`），否则页面题号与答案表错位。

### 0.3 「4872 题 / 600 题」的真实含义（不是每天）

| 数字 | 实际含义 | 恒等式 |
|---|---|---|
| 4872 | **150 天合计**的 `practice` 每日选做题 | `2 × 2160 core_vocab + 2 × 276 grammar = 4872` |
| 600 | 30 个五日单元 × 20 题 | `30 × 20` |
| 2535 | 必做题合计 | `900 quiz + 1500 sentences + 135 listening` |
| 8007 | 全答案表 | `2535 + 4872 + 600` |

每日 `practice` 实际是 **24 / 26 / 34 / 36** 题（分布 `{24:11, 26:37, 34:13, 36:89}` 天），不是 4872。
`reports/v9_completion.md:9`、`HANDOFF.md:14` 的「每日 4872 题」是文档笔误，实测数据见 §2.4。

### 0.4 源码 → 生成物行号映射（已逐行比对）

| 源 | 生成物 | 偏移 |
|---|---|---|
| `build_v5_site.py` JS 121-352 | `web/assets/app.js` | `-120`（如 `initMask` 163→43、`applyMode` 148→28、`initSpeak` 299→179、`initQuiz` 256→136、`#finish` 329→209） |
| `study_ui.py` JS 27-86 | `web/assets/study.js` | `-26`（`deck` 75→49、`init` 83→57、`attempt` 55→29、`flush` 62→36、`NHStudy` 84→58） |
| `build_v5_site.py` CSS 33-119 | `web/assets/app.css` 前段 | `-32`（`.mask` 78→46、`header.top` 54→22、`nav.toc a` 104→72） |
| `study_ui.py` CSS 4-25 | `web/assets/app.css` 后段 | `+83`（`.study-deck` 16→99） |

---

## 1. 逐项定位：用户抱怨的每个 UI 元素

### 1.1 归属分类（用户要求区分三类）

| 类别 | 真实机制 |
|---|---|
| **A. `build_v5_site.py` 静态 HTML 模板**（355-442） | 直接写在 `HTML` 字符串里，构建时 `.replace()` 填值。绝大多数顶部/底部杂项在这里。 |
| **B. `study_ui.py` 注入** | `study_ui.py` **本身不产出 HTML**，只有 `CSS`(4-25) / `JS`(27-86) / 死代码 `shell()`(89-95)。所谓「注入」= 它的 `JS` 被写成 `study.js`，运行时往 A 预留的**空 div** 里 `innerHTML`。占位 div 由 `build_v5_site.py:425`（`<div id="studySync"></div>`、`<div id="practiceDeck"></div>`）和 `study_page()`(`:550`) 提供。 |
| **C. `app.js` 运行时生成** | `initReview()`(192-211)、`initVocab()`(214-251)、`initQuiz()`(256-290)、`initSentences()`(292-297) 在 DOMContentLoaded 后造 DOM。 |

### 1.2 顶部杂项逐项清单

| 用户点名的元素 | 源码 `文件:行` | 生成页面 `web/day-001.html:行` | 片段 / 函数 | 类别 | 处理 |
|---|---|---|---|---|---|
| 「背诵模式」按钮区 | `build_v5_site.py:374` | `:20` | `<div class="study-toolbar" role="group" aria-label="遮盖背诵"><span class="small">背诵模式</span><button data-mask="all">显示全部</button>…` | A | **删** |
| 全局 `#modeBtn`（遮盖：中文 / 双向 循环） | `build_v5_site.py:365`；文案表 `app.js:159`；点击循环 `app.js:168-169`；`:145` `mode` 变量 | `:11` | `<button class="mode" id="modeBtn">遮盖：中文</button>`；`applyMode()` `build_v5_site.py:148-160` / `app.js:28-40`；`setMode()` `:161` / `app.js:41`；`initMask()` `:163-189` / `app.js:43-69` | A + C | **删**（详见 §5） |
| 「网页 42 分钟 · 会话 18 分钟」 | `build_v5_site.py:366`；CSS `.top .prog` `:58` | `:12` | `<span class="prog">网页 42 分钟 · 会话 18 分钟</span>`（硬编码字符串，与 `curriculum.blocks` 无关联） | A | **删** |
| ①②③④⑤ 导航（目录） | `build_v5_site.py:369-372`；CSS `nav.toc` `:103-104`；占位 `@@TOC_LISTEN@@:668`、`@@SNUM@@:666`、`@@QNUM@@:667` | `:15-18` | `<nav class="toc"><a href="#review">① 复习</a>…<a href="#quiz">⑤ 综合小测</a></nav>` | A | **删**；同时删 `@media(min-width:1024px)` `:102` 的 `grid-template-columns:200px minmax(0,760px)` 与 `main{grid-column:2}` `:105`，否则桌面端留 200px 空列 |
| ①②③④⑤ 编号（章节标题） | `:377` `① 今日复习`、`:395` `② 今日新词`、`:408` `③ 语法`、`:415` `@@SNUM@@ 选句练习`、`:421` `@@QNUM@@ 综合小测`、`:638` `④ 听力` | `:23, :41, :54, :61, :67`（Day1 无听力；Day47 另有 `:④听力`） | `h2` 里的圈号 + `.min` 分钟标签 | A | 圈号**删**；`<span class="min">N 分钟</span>` **保留或同步改测试**（见 §7.3 `test_v5.py:176-181`） |
| 课程目录 · 真人听力 · N3资源 · 错题与复习集 | `build_v5_site.py:375` | `:21` 后半 | `<p class="small"><a href="/">课程目录</a> · <a href="listening.html">真人听力</a> · <a href="resources.html">N3资源</a> · <a href="review.html">错题与复习集</a></p>` | A | **删**。注意 `tests/test_v7.py:186-187` 断言 day-047 含 `listening.html` / `真人听力`，听力区块 `:644` 另有同名链接，删顶部后仍成立 |
| 提示文案 `@@WEB_GOAL@@` | `build_v5_site.py:375` + 填充值 `:657` | `:21` 前半 | `<p class="hint">今天先理解重点词句，再完成3道选句、6道综合选择题。另有7道选句可按需练习。</p>` | A | **删**；文案里的「3道选句 / 6道综合 / 7道」也要一起废止 |
| 五日复习顶部 callout | `build_v5_site.py:375` `@@UNIT_LINK@@` + `:652`（`n%5==0` 注入）+ CSS `study_ui.py:5` `.unit-callout` | Day1 无 | `<p class="unit-callout"><a href="unit-005.html">五日复习…</a></p>` | A | **删**（或移到页尾，但用户要求顶部只留内容） |
| 整个 `header.top` 容器 | `build_v5_site.py:362-367`；CSS `:54-58` `position:sticky` | `:8-13` | `<header class="top">…</header>` | A | **删整块**（含 `.day` / `.goal`），CSS `:54-58`、`:59` `.mode` 一并删 |
| `.view-switch` 内的 `data-mask` 按钮 | `build_v5_site.py:379`（复习）、`:398`（新词） | `:25`, `:44` | `<button data-mask="all">显示</button><button data-mask="zh">遮中文</button><button data-mask="ja">遮日语</button>` | A | **删**；`列表/卡片` 两个 `data-view` 按钮按 §5 决策保留或删 |

### 1.3 练习分段逐项清单

| 元素 | 源码 `文件:行` | 生成页面 | 函数 / 归属 | 处理 |
|---|---|---|---|---|
| 「④/⑤ 选句练习」独立 section + 「再练7题」折叠 | `build_v5_site.py:414-418`；拆题 `initSentences()` `:292-297`（`app.js:172-177`） | `:60-64`（section 起 `:60`，「再练7题」在 `:63`） | `<section id="sentences">…<div id="sentenceItems"></div><details><summary>再练7题</summary><div id="sentenceExtra"></div></details>` | **删整段**，题并入单块 |
| 「⑤/⑥ 综合小测」独立 section | `build_v5_site.py:420-424` | `:66-70` | `<section id="quiz"><div id="quizItems"></div></section>` | **删整段**，题并入单块 |
| 「词汇与语法 · 翻页练习」 | `build_v5_site.py:425` | `:71` | `<section id="practice"><div id="practiceDeck"></div></section>` | **删整段**；`#practiceDeck` 是 `study_ui.py::JS::deck()`(`study_ui.py:75` / `study.js:49`) 的挂载点，含 `全部/词汇/语法` 筛选 + `上一题/下一题` 翻页 |
| 听力 3 题（`#listenQuiz`） | `build_v5_site.py:637-647`（`listen_html`），`:642` 内嵌 `data-qs="%s"`；`initQuiz('#listenQuiz','#listenScore')` 在 `:321` | Day47 起 | 独立 `<section id="listing">` 内 | **保留 `<audio>` / 脚本 / `#transcript`，把 3 道 MCQ 并入单块**。`#transcript` 的 `TRANSCRIPT_HINTED` 逻辑要改（见 §3.7） |
| 词卡翻页 `#vPrev/#vNext` | `build_v5_site.py:400-403`；`initVocab()` `:221-250`（`app.js:101-130`） | `:46`（`#vocabCard`）、`:48`（`#vPrev`） | `<button id="vPrev">上一个</button><button id="vNext">下一个</button>` | §5 决策：建议删（内容卡片也别翻页），`initVocab()` 只留 `renderList()` |
| 复习卡翻页 `#rShow` / `.rRate` | `build_v5_site.py:381-389`；`initReview()` `:205-209` | `:27-33` | `<div id="reviewCard" data-view-panel="card" hidden>` | §5 同上 |
| 页面底部脚本注入的 7 个全局变量（其中 4 个要删） | `build_v5_site.py:433` | `:79` | `window.__REVIEW__=…;window.__VOCAB__=…;window.__QUIZ__=…;window.__SENT__=…;window.__LISTEN__=…;window.__FOCUS__=…;window.__PRACTICE__=…;` | 保留 `__REVIEW__/__VOCAB__/__FOCUS__`，**删 `__QUIZ__/__SENT__/__LISTEN__/__PRACTICE__`**，改 `window.__QUESTIONS__` |
| 内联 `data-qs` 设置 | `build_v5_site.py:435-440` | `:81-86` | `quizItems.setAttribute('data-qs',…)`、`sentenceItems.setAttribute('data-items',…)`（**后者是死代码**，`initSentences()` `:295` 会用 `data-qs` 覆盖它） | **删**，改 `questionItems` 一个 `data-qs` |
| 得分栏 4 个 | `:417` `#sentenceScore` / `#sentenceExtraScore`、`:422` `#score`、`:642` `#listenScore` | `:63, :68` | — | 只留一个 `#score` |

### 1.4 底部逐项清单

| 元素 | 源码 `文件:行` | 生成页面 | 归属 | 处理 |
|---|---|---|---|---|
| 学习口令 / 同步 / 导出待同步记录 | 占位 `build_v5_site.py:425` `<div id="studySync"></div>`；**运行时注入** `study_ui.py:83`（`study.js:57`） | `:71` 空 div → 运行时出现 | **B（study.js 运行时）** | **删**。`init()` 里 `controls.innerHTML='<div class="study-tools"><label>学习口令 <input id="studyAccess"></label><button id="studyFlush">同步</button><button id="studyExport">导出待同步记录</button></div>…'`。⚠️ 删它会使所有同步失效，见 §7 风险 2 |
| `#studyStatus` 状态文案 | 占位 `build_v5_site.py:425`；写入 `study_ui.py:49` `tell()`（`study.js:23`） | `:71` | B | **删** |
| 「必做题答齐且正确率达到70%才达标…」说明 | `build_v5_site.py:427` | `:73` 前半 | A | **删** |
| `#saveStatus` | `build_v5_site.py:427`；写入 `app.js:325,338,347,348`（`build_v5_site.py:325,338,347,348`） | `:73` 中 | A + C | **删** |
| 「导出作答」`#exportAnswers` | `build_v5_site.py:427`；handler `build_v5_site.py:323-327`（`app.js:203-207`） | `:73` 末 | A + C | **删**（连带 `LATEST_PAYLOAD` `:144`、`:343`） |
| 「再练一轮」`#restartPractice` | `build_v5_site.py:428`；handler `:328`；`:347` 成功后 `hidden=false` | `:74` | A + C | **删** |
| 「保存本次作答」`#finish` | `build_v5_site.py:429`；handler `:329-349`（`app.js:209-229`） | `:75` | A + C | **保留 id `#finish`**，改文案为「完成」，重写 handler（§6） |
| 第一课 · 课程目录 · 下一课 | `build_v5_site.py:430` `@@LESSON_NAV@@`；填充 `:653` | `:76` 前半 | A | **删**（连带 CSS `:35` `.lesson-nav`、`study_ui.py:9/23` 同名规则） |
| 署名行 | `build_v5_site.py:430` | `:76` 后半 | A | **删**：`<p class="small"><a href="listening.html">真人听力</a> · <a href="resources.html">样题与资源署名</a> · 原创文本合成语音；内容包含 AI 草稿。</p>`。⚠️ 许可署名若删除需另找位置（见 §7） |
| 死代码 `#accessKey` | `build_v5_site.py:322`（`app.js:202`） | 页面无此元素 | C | **删**。`var access=$('#accessKey');if(access){…}` 永远不执行 |

---

## 2. 练习数据来源（跑脚本实测）

### 2.1 页面实际渲染的题块：4 块 MCQ + 2 组翻页内容卡

| # | 容器 | 来源数组 | 题量 | 翻页 / 分段 | 渲染函数 |
|---|---|---|---|---|---|
| 1 | `#sentenceItems` + `#sentenceExtra` | `window.__SENT__` = `sentences[n]`（`build_v5_site.py:598`） | 3 必做 + 7 选做（折叠 `<details>再练7题`） | 无翻页，但分段/折叠 | `initSentences()` `:292-297` → `initQuiz()` |
| 2 | `#quizItems` | `window.__QUIZ__` = `qs`（`build_v5_site.py:610,674`） | 6 | 平铺 | `initQuiz('#quizItems','#score')` `:321` |
| 3 | `#listenQuiz` | **不读 `__LISTEN__`**，读 `listen_html` 内嵌 `data-qs`（`build_v5_site.py:642`）；`__LISTEN__` 只被 `#finish` 的 stale 校验用（`:336`） | 3（仅 45 个听力日） | 平铺 | `initQuiz('#listenQuiz','#listenScore')` `:321` |
| 4 | `#practiceDeck` | `window.__PRACTICE__` = `practice`（`build_v5_site.py:596,651`） | 24–36 | **翻页卡片**：一次 1 题 + `全部/词汇/语法` 筛选 + `上一题/下一题` | `study_ui.py::JS::deck()` `:75` / `study.js:49`，由 `init()` `:83` 调用 |
| (5) | `#reviewList` / `#reviewCard` | `window.__REVIEW__` | 0–12 条自评卡（非 MCQ） | 列表 + 卡片翻页 `#rShow`/`.rRate` | `initReview()` `:192-211` |
| (6) | `#vocabList` / `#vocabCard` | `window.__VOCAB__` | 11–21 词（非 MCQ） | 列表 + 卡片翻页 `#vPrev/#vNext` | `initVocab()` `:214-251` |

`unit_questions`（每 5 天 20 题）**只在 `web/data/day-NNN.json` 里，不渲染在当日页面**；它被 `study.js::renderPersonal()`（`study_ui.py:82`）在「复练曾错题」时按 day 拉 JSON 用。

### 2.2 Day 1 / 47 / 150 量化统计（实测 `web/data/day-*.json` + `curriculum.json`）

| 指标 | Day 1 | Day 47 | Day 150 |
|---|---|---|---|
| `quiz`（`__QUIZ__`，`#quizItems`） | 6 | 6 | 6 |
| `sentences`（`__SENT__`，3+7） | 10 | 10 | 10 |
| `listening_material.questions`（`__LISTEN__`） | 0 | 3 | 3 |
| `practice`（`__PRACTICE__`，`#practiceDeck`） | 26 | 26 | 24 |
| `unit_questions`（仅 JSON） | 0 | 0 | 20 |
| **页面 MCQ 合计** | **42** | **45** | **43** |
| `curriculum.question_ids`（完成门控必做） | 9 | 12 | 12 |
| `new_vocab_ids` | 11 | 14 | 21 |
| `core_vocab_ids` | 11 | 11 | 11 |
| `extension_vocab_ids` | 0 | 3 | 10 |
| `new_grammar_ids` | 2 | 2 | 1 |
| **任一数组 `knowledge_ids` 覆盖到的新词** | 11 | 11（**缺 3 拓展**） | 11（**缺 10 拓展**） |
| **覆盖到的新语法** | 2 | 2 | 1 |
| 每知识点题数分布（新词） | `{2:11}` | `{0:3, 2:9, 3:2}` | `{0:10, 2:7, 3:4}` |
| 每知识点题数分布（新语法） | `{2:1, 3:1}` | `{2:1, 3:1}` | `{5:1}`（含 20 道 unit） |
| `practice` capability 分布 | meaning 13 / reading 11 / usage 2 | meaning 13 / reading 11 / usage 2 | meaning 12 / reading 11 / usage 1 |
| `practice` group 分布 | vocab 22 / grammar 4 | vocab 22 / grammar 4 | vocab 22 / grammar 2 |

**结论：当前题目没有覆盖当天「所有新词」**——`practice_v9.build_daily()` 只遍历 `core_vocab_ids`（`practice_v9.py:119`），拓展词完全没有出题；`sentences` 的 `knowledge_ids` 恒为 `[]`（`sentence_choices.py:47`），听力题也是 `[]`（`quiz_v5.py:178`），都不贡献知识点覆盖。新语法靠 `practice` 的 2 题/条覆盖，是满足的。

### 2.3 `practice_v9.build_daily()` 出题维度与重复度

`practice_v9.py:115-123`：

```python
for kid in day.get("core_vocab_ids", day["new_vocab_ids"]):
    questions.extend(_vocab_questions(number, number, kid, vocab))     # 2 题
for kid in day["new_grammar_ids"]:
    questions.extend(_grammar_questions(number, number, kid, grammar)) # 2 题
```

- **4 个维度**：`_vocab_questions()` `:77-94` → `meaning`（释义，`:88-90`）+ `reading`（假名读音，`:91-93`）；`_grammar_questions()` `:97-112` → `meaning`（释义，`:103-106`）+ `usage`（接续说明，`:109-111`）。
- **重复度**：每个 `core_vocab_id` 恰好 2 题、每条 `new_grammar_id` 恰好 2 题；`capability` 字段写在 `_make()` `:57`，`group` ∈ {vocab, grammar}，全部 `optional:True`（`:58`）。被 `__QUIZ__` 同时命中的知识点会到 3 题，五日单元的 20 题抽样再叠加（Day 150 语法达 5 题）。
- **qid**：`_make()` `:51-53` → `P-%03d-<kid>-<capability[0]>-<12位digest>`，`scope="unit"` 时前缀 `U-`；`assert len(qid)<=48`（Worker `parseResults` 也限 48，见 `index.ts:180`）。
- **选项**：`_options()` `:24-44` 恰好 4 项，`forbidden` 排除同词异读，`fnv()` 去重。
- **全库恒等式（实测）**：`2×2160 + 2×276 = 4872`；`30×20=600`；`900+1500+135=2535`；`2535+4872+600=8007`（=`generated-key.json` 的 `answers` 条数，`tests/test_v7.py:178` 硬断言 8007）。

---

## 3. 合并方案：一整块题目

### 3.1 目标数据结构

页面只保留一个 section：

```html
<section class="card" id="questions">
  <h2>今日练习</h2>
  <p class="small">已答 <strong id="score">0 / 0</strong></p>
  <div id="questionItems"></div>
</section>
```

`window.__QUESTIONS__ = [q, ...]`（单数组，无 `group` 分段、无 `required/optional` 折叠、无翻页）。`initQuiz('#questionItems','#score')` 一次调用渲染全部；`QUIZ_RESULTS`（`build_v5_site.py:253`）天然是所有题共用的单一数组，无需改。

### 3.2 构造算法（确定性，可直接落到 `practice_v9.py`）

```python
def build_merged(day, vocab, grammar, kanji, sentences_required, quiz_required):
    n = day["day"]
    # ① 必做集合 R：必须与 curriculum.question_ids 完全一致，否则 finish-day 永远 incomplete
    R = list(quiz_required) + list(sentences_required)      # 非听力日 9，听力日 12（含 3 道 L-）
    assert {q["qid"] for q in R} == set(day["question_ids"])

    # ② 已被 R 覆盖的知识点（只看 knowledge_ids；sentences/listening 恒为 []，不计）
    covered = collections.Counter(
        kid for q in R for kid in (q.get("knowledge_ids") or []))

    # ③ 覆盖池：对【全部】new_vocab_ids（含拓展）与【全部】new_grammar_ids 各挑 1 题
    out, seen_qid = [], {q["qid"] for q in R}
    for kid in day["new_vocab_ids"]:
        if covered[kid] >= 1:            # 上限 1 题/知识点，避免"同一考点重复太多"
            continue
        # 按 (day + 数字 id) 奇偶在 meaning / reading 间轮换，保证两种能力都被练到
        idx = (n + int(kid[1:])) % 2
        q = _vocab_questions(n, n, kid, vocab)[idx]
        _add(q, out, seen_qid, covered)
    for gid in day["new_grammar_ids"]:
        if covered[gid] >= 1:
            continue
        idx = (n + int(gid[1:])) % 2     # meaning / usage 轮换
        q = _grammar_questions(n, n, gid, grammar)[idx]
        _add(q, out, seen_qid, covered)

    # ④ 顺序：必做在前（完成门控题最显眼），覆盖题按 new_vocab_ids → new_grammar_ids
    merged = R + out
    assert len({q["qid"] for q in merged}) == len(merged)      # 全局 qid 唯一
    assert all(len(q["options"]) == 4 and q["h"] in q["oh"] for q in merged)
    # ⑤ 覆盖断言（CI 必须跑）
    for kid in day["new_vocab_ids"] + day["new_grammar_ids"]:
        assert any(kid in (q.get("knowledge_ids") or []) for q in merged), (n, kid)
    return [public_question(q) for q in merged]
```

要点：

- `_vocab_questions()` / `_grammar_questions()` **本身对任意 `kid` 都可用**（`practice_v9.py:77,97`），`build_daily()` 只是把范围收窄到 `core_vocab_ids`。因此「覆盖拓展词」不需要新写出题器，只要调用范围改成 `new_vocab_ids`。
- **上限 1 题/知识点**（`covered>=1` 就跳过）。当前 `build_daily` 是 2 题/知识点，改后重复度减半。
- 轮换用 `(day + id) % 2`，无随机、跨构建可复现；`_make()` 内 `seed` 已由 `_digest(day, source_day, group, capability, kid)` 决定（`practice_v9.py:49`）。
- `qid` 唯一性必须在**合并后**全量断言：现在 `quiz_v5.day_questions()` 的断言（`:223-230`）只覆盖 `qs` 自己，`P-` 前缀的 sentence 题与 practice 题之间从未做过跨池去重。

### 3.3 题量预算（实测上界）

```
|merged| = |question_ids| + |未覆盖 new_vocab| + |未覆盖 new_grammar|
```

| Day | `question_ids` | 未覆盖新词 | 未覆盖新语法 | merged |
|---|---|---|---|---|
| 1 | 9 | 11（Day1 的 3 道 Q 是 K/K/G，3 道 D 诊断无 knowledge_ids） | 1（G0001；G0261 被 quiz 命中） | **21** |
| 47 | 12 | 12 | 1 | **25** |
| 150 | 12 | 19 | 0 | **31** |

全库上限：`12 + (21-2) + (2-1) = 32`。**建议区间 21–32 题，硬上限 36**。

> 硬上限 36 是硬约束不是建议：Worker `MAX_RESULTS = 40`（`deploy/worker/src/index.ts:45`），`parseResults()` `:173-174` 超过 40 直接 `too_many_results` 400；`app.js::sync()`（`build_v5_site.py:314-319`）**一次 POST 整个 `results`**，不做分片（对比 `study_ui.py:63-65` 的 `flush()` 与 `tests/test_completion_gate.py:35` 都是按 40 分批；`study_sync.py:55` 的分页是 GET 拉事件，与提交无关）。若 merged > 40 必须给 `sync()` 加分片，否则「完成」必然 400。
> `MAX_BODY_BYTES = 64KB`（`index.ts:46`）也够用，但要顺带确认 `metadata` ≤16KB（`:260`）。

### 3.4 答案哈希继续用 FNV —— 不用改算法

三处 FNV-1a 实现完全一致（`NFKC` → 去空白 → 按 codepoint 异或乘 `16777619`）：

| 位置 | 用途 |
|---|---|
| `quiz_v5.py:14-22` `fnv()` | 生成 `answer`→`h`、`options`→`oh` |
| `build_v5_site.py:254-255` / `app.js:134` `fnv()` | `initQuiz()` `:275` `fnv(o)===q.h` 判对错、`:277` 用 `q.oh` 标正确项、`:279` 显示正确文本 |
| `study_ui.py:74` / `study.js:48` `fnv()` | `deck()` 的旧翻页判分（删掉 deck 后这处可留可删） |

服务端判分**是另一套**：`web/data/grade/day-NNN.json` 存 `sha256(_norm_answer(answer))`（`nh80.py:280`），Worker `regrade()` `index.ts:129-132` 比对。两套互不干扰。

**只要沿用 `quiz_v5.fnv()`、`practice_v9._make()`、`sentence_choices` 生成的 `h`/`oh`，FNV 一行都不用改。** 合并只是挑选题目、换容器，不重算哈希。唯一要注意：合并后 `initQuiz()` 的 `hinted` 判定写死了 `selector==='#listenQuiz'`（`build_v5_site.py:282-283`），听力题进了单块后会丢失 `TRANSCRIPT_HINTED` 标记 → **改成按题目判定**：`q.qid.indexOf('L-')===0 || !!q.passage`。

### 3.5 `public_question` 契约（`quiz_v5.py:192-193`）

```python
def public_question(q):
    return {k: q[k] for k in ("id","qid","type","prompt","options","h","oh",
            "passage","day","group","capability","knowledge_ids","source_day","optional") if k in q}
```

- **不必改白名单**：merged 需要的 `h/oh/options/qid/knowledge_ids/capability/group/optional/passage` 全在里面。
- `direction` / `source_id` 现在由 `build_v5_site.py:598` 在投影后 `dict(public_question(q), direction=…, optional=…, source_id=…)` 补上；合并后若仍想显示「选择对应的日语句子 / 中文意思」（`initQuiz()` `:267`），沿用同样的「投影后补字段」写法即可，不必动白名单。
- **不要**把 `answer` / `rationale` 加进白名单：`release_guard.py:48-49` 对 `quiz+sentences+practice+unit_questions+listening.questions` 断言无明文答案，`tests/test_v5.py:120-127,199-205` 同样断言。
- 若给题目加 `kana_hint` / `speak` 字段（不建议，注音属于内容区不属于题目），才需要扩白名单并同步扩 `release_guard.py:47` 的拼接列表。

### 3.6 `generated-key.json` / grade 分片是否要同步改 —— 取决于覆盖方案

| 方案 | 做法 | 答案表 / grade / DB | 代价 |
|---|---|---|---|
| **A 零重生成** | merged 只从现有 `quiz/sentences/listening/practice` **挑选**，`build_daily()` 保持不变；拓展词不进题 | **完全不用改**（8007 不变，`test_v7.py:178` 不用动） | 不满足「所有新词」字面要求：Day47 缺 3、Day150 缺 10 个拓展词。**需用户确认** |
| **B′ 推荐** | 保留现有 4872 题的登记（历史已提交 qid 全部仍可重判），**仅为 540 个拓展词各新增 1 题**；页面只渲染 merged 子集 | `generated-key.json` 8007→**8547**（`540 = 2700−2160`）；`web/data/grade/day-NNN.json` 相应 +540；`data/state.db` questions 表 +540；`tests/test_v7.py:178` 断言 8007→8547 | 必须整链跑 `nh80 build`；题库变大但历史记录零损失 |
| **B 彻底重构** | 用 `build_merged()` 取代 `build_daily()`，`_build_v5()` 只登记 merged + 600 unit | 8007 → 约 `2535 + ~3900 + 600 ≈ 7035`，大量旧 `P-` qid 从答案表消失 | **历史 `events` 里的旧 qid 会被 Worker 判 `unknown_or_wrong_day_question` 400**（`index.ts:251-257`），且 `_build_v5()` `:284-289` 会删 DB 孤儿题。不建议 |

推荐 **B′**：在 `practice_v9.py` 增加 `build_merged()`（§3.2），`nh80.py::_build_v5()` `:261` 改为

```python
practice = build_daily(day, ...)                    # 保留：历史 qid 不丢
extra    = build_merged(day, ..., only_uncovered=True)   # 新增：仅拓展词的 540 题
...
for q in qs + sqs + practice + extra:               # :267 登记全部
```

`build_v5_site.py::main()` `:596` 同步改成 `build_merged()` 产出页面数组；`web/data/day-NNN.json` **保留 `quiz`/`sentences`/`practice`/`unit_questions` 四个旧键（向后兼容测试与 `renderPersonal()` 的错题复练路径，见 `study_ui.py:82`），另加一个新键 `questions`** 供页面用。`release_guard.py:47` 把 `d.get('questions',[])` 加进拼接列表。

> ⚠️ `day["question_ids"]`（`nh80.py:260`）**必须保持原样**（9 / 12 题）。`cmd_finish_day()` `nh80.py:779-793` 用 `expected=set(d["question_ids"])` 判「全部作答 + ≥70%」；merged 必须包含这 9/12 个 qid，否则用户永远无法完成当天。这也是 §3.2 里 `R` 的来源。

### 3.7 明确要删 / 改的函数清单

**`scripts/build_v5_site.py`**

| 行 | 动作 |
|---|---|
| CSS `35-42` | 删 `.lesson-nav`/`.study-toolbar`/`.view-switch`/`.study-row` 双列网格（改单列堆叠，见 §4）；`42` 的 `.speak` 规则保留 |
| CSS `54-61` | 删 `header.top`、`.top .day/.goal/.prog`、`.mode` |
| CSS `66-69`、`:37` | 删 `.btn[aria-pressed="true"]`（只为遮盖按钮存在）；`.btn` 本体保留给发音/完成按钮 |
| CSS `78-80` | 保留 `.mask`/`.mask.peek`，删 `.eye`（局部开关不用眼睛按钮） |
| CSS `100-107` | 删 `nav.toc` 相关与 `grid-template-columns:200px …`，改 `main{grid-column:1/-1}` |
| CSS `113-118` | `@media print` 里删 `header.top,.eye`，保留 `.foot,.btn` 与 `.mask{filter:none}` |
| CSS 新增 | `ruby rt{}`、`.kana-line{}`、`.ex-ja{}`、`.speak{}`、`[data-local-mask]` 样式 |
| JS `127-132` `focus()` | **保留**（`__FOCUS__` / `terms_for_day` 仍用） |
| JS `133` `reveal()` | **保留**（局部遮挡的临时揭示 + 键盘） |
| JS `134-138` `setView()` | 按 §5 决策：删卡片视图则一并删 |
| JS `139-143` `initViews()` | **删**（含 `:142` 的 `$$('[data-mask]')…setMode` 绑定） |
| JS `144` `LATEST_PAYLOAD` | **删**（`#exportAnswers` 删后无用） |
| JS `145` `var mode=…` / `148-160` `applyMode()` / `161` `setMode()` / `162-189` `initMask()` | **全删**；`:150` 的「`#grammar` 永远不遮挡」特例也随之消失（正是 §5 需要的） |
| JS `192-211` `initReview()` | 保留 `:200-204` 的列表行渲染 + `NHStudy.rate`；**删** `:205-209` 的 `render()`/`#rShow`/`.rRate`/`applyMode($('#reviewCard'))` |
| JS `214-251` `initVocab()` | 保留 `:218` `#extraVocab` 与 `:239-244` `renderList()`；**删** `:221-238` `render()` 卡片分支、`:237` `applyMode(area)`+`initMask()` 重入、`:246-249` `#vPrev/#vNext`/`.vRate` |
| JS `253-290` `initQuiz()` | **保留**，改名为 `renderQuestions()`；`:282-283` 的 `hinted` 判定改为按 `q.qid`/`q.passage`；`lastPassage` 逻辑 `:261,265-266` **必须保留**（`tests/test_v7.py:189` 断言） |
| JS `292-297` `initSentences()` | **删** |
| JS `299-306` `initSpeak()` | **保留，一行不改**（§4 的最小实现靠它） |
| JS `307-312` `collectPayload()` | 保留 `results`/`practice_mode:'choice'`；`:310-311` 的 `review_ratings:[]`/`sentences:[]` 是元数据占位，**不能随意改**（§7 风险 3） |
| JS `314-319` `sync()` | 按 §6 决策重写或删；`:315` 的口令检查是关键风险 |
| JS `320-350` DOMContentLoaded | `:321` 改成 `renderQuestions('#questionItems','#score'); initSpeak(); initLocalMask();`；删 `initMask()/initViews()/initSentences()/initQuiz('#listenQuiz',…)`；`:322` 删 `#accessKey` 死代码；`:323-328` 删 `#exportAnswers`/`#restartPractice` handler；`:329-349` 重写 `#finish` |
| JS `:336` | stale qid 白名单 `window.__QUIZ__.concat(__LISTEN__,__SENT__)` → `window.__QUESTIONS__` |
| HTML `362-375` | **整段删**（header + toc + toolbar + hint + links + UNIT_LINK） |
| HTML `376-411` | 保留 review/vocab/grammar 三个 section；删 `.view-switch` 里的 `data-mask` 按钮（`:379,:398`）、删圈号、删 `#vocabCard`/`#reviewCard` 分支 DOM |
| HTML `413` / `:637-647` `listen_html` | 保留 `<audio>`、`#transcript`、真人听力链接；**删 `<div id="listenQuiz">`**，3 题并入 merged |
| HTML `414-425` | 删 `#sentences`、`#quiz`、`#practice`、`#studySync`、`#studyStatus` 五段；替换为单个 `#questions` section |
| HTML `427-430` | 删必做题说明 / `#saveStatus` / `#exportAnswers` / `#restartPractice` / `.lesson-nav` / 署名行；`#finish` 改文案为「完成」 |
| HTML `433` | 删 `__QUIZ__/__SENT__/__LISTEN__/__PRACTICE__`，加 `__QUESTIONS__` |
| HTML `435-440` | 删 4 行内联 setter（含 `:439` 死代码 `sentenceItems.setAttribute('data-items',…)`），改 `questionItems` 一处 |
| `main()` `:596` | `build_daily()` → `build_merged()` |
| `main()` `:598` | `sentences[n]` 仍生成（写进 JSON 旧键），但不再注入页面 |
| `main()` `:649-678` | 删 `:651 PRACTICE`、`:652 UNIT_LINK`、`:653 LESSON_NAV`、`:656 LQS`、`:657 WEB_GOAL`、`:666 SNUM`、`:667 QNUM`、`:668 TOC_LISTEN`、`:674 QUIZ`、`:675 SENT`；清理 `:672-673,:677` 三次重复的 `@@VOCAB__` 替换；加 `@@QUESTIONS__` |
| `main()` `:679-684` | 保留 4 个旧键，加 `"questions": merged` |
| `main()` `:833` | **必须把 `HTML` 加进 revision**（见 §7 风险 1） |
| `build_review()` `:452-467` | 不改 |
| `build_grammar_html()` `:470-495` | `:476-478` 例句加小假名行 + `data-speak` 按钮（§4）；`:485` 的 `data-mode="all"` 删（局部开关接管）；保留 `emphasize()` |
| `study_page()` `:549-550` | unit 页专用，保留；若 unit 页也要去翻页卡片，一并改 |

**`scripts/study_ui.py`（→ `study.js`）**

| 行 | 动作 |
|---|---|
| `75` / `study.js:49` `deck()` | 日页不再有 `#practiceDeck` → 调用自然早退（`deck(null,…)` 有 `if(!root)return`）。**暂不删**：`unit-*.html` 的 20 题巩固还靠它；若 unit 页也简化再删 |
| `83` / `study.js:57` `init()` | **删 `#studySync` 控件注入块**（`controls.innerHTML=…` 到 `$('#studyExport').onclick=exportPending`）；保留 `deck()`、`renderUnit()`、`refresh()`、`pending()`/`schedule()`/`online` 监听 |
| `49` `tell()`、`:69` `exportPending()` | `#studyStatus` / 导出按钮删后可一并删（或留着无害） |
| `54` `rate()`、`:55-60` `attempt()`、`:62-68` `flush()`、`:61` `post()`、`:73` `refresh()`、`:72` `paintBadges()`、`:84` `NHStudy` | **必须全部保留**：`app.js` 的 `initQuiz()` `:282` 调 `window.NHStudy.attempt()`，`initReview/initVocab` 调 `NHStudy.rate()`；删了离线队列与 `/api/reviews` 全断 |
| `76-82` `mask/card/masking/maskControls/renderUnit/renderPersonal` | **保留**：unit 页与 `review.html` 仍用；`renderPersonal()` 的错题复练路径（`study_ui.py:82`）依赖 day JSON 的 `practice/quiz/sentences/unit_questions`，这正是 §3.6 要保留旧键的原因 |
| `89-95` `shell()` | v5 页无调用（用的是 `build_v5_site.py::study_page()`），是死代码，可删 |
| CSS `4-25` | 删 `.unit-callout`(`:5`)；其余 unit/review 页样式保留 |

**`scripts/practice_v9.py`**：保留 `_make()`/`_options()`/`_vocab_questions()`/`_grammar_questions()`/`build_unit()` **原样**；`build_daily()` `:115-123` 保留（B′ 方案要登记旧题）；**新增** `build_merged()`（§3.2）。

**`scripts/nh80.py::_build_v5()`**：`:261` 增加 `extra = build_merged(..., only_uncovered=True)`；`:267` 改为 `for q in qs + sqs + practice + extra:`；`:260` `question_ids`、`:283-289` purge、`:291-296` 三处写盘 **不改**。

**`scripts/release_guard.py:47`**：`public_questions=d['quiz']+d['sentences']+d.get('practice',[])+d.get('unit_questions',[])+d.get('questions',[])+…`。

**`CONTRACTS.md`**：§v8（`:276-283`）、§v9（`:285-298`）以及 §9（`:119-134`）明确写了「3题必做/7题拓展」「六题综合」「翻页练习」「页面只含选项及哈希」。文件头 `:3` 自称「唯一接口依据，任何模块改动前先改这里」→ **必须最先改文档**，否则契约与产物漂移。

---

## 4. 小日语文字（假名/日文原文）+ 例句发音：不改 seeds 的最小路径

### 4.1 现状（实测，别信文档）

- `knowledge/seeds/vocabulary.jsonl` 2700 行，字段含 `surface/kana/romaji/…`，`examples` 只有 `{ja, zh, grammar_ids}` —— **例句无假名字段**（2700 条里带 `kana`/`reading`/`furigana` 的例句数 = **0**）。
- `knowledge/seeds/grammar.jsonl` 276 行，`examples` 只有 `{ja, zh, vocab_ids}` —— 同样 **0** 条带假名。
- `web/data/day-001.json` 的 `vocab[0]` = `{id,surface,kana,meaning,ko,ko_status,optional,pos,ex:{ja,zh},audio:"tts"}`；`grammar[0]` 是整条 seed 原样拷贝。
- `web/audio/` 只有 **45 个 m4a**（`manifest.json` items = `M0096…M0140`），是**整篇听力素材**的 Kokoro 合成音频；**没有单词级 / 例句级音频文件**。`vcards[].audio:"tts"`（`build_v5_site.py:607`）只是占位字符串，没有任何 `<audio src>` 指向它。
- 现有渲染里：词卡的 `.kana`（`build_v5_site.py:231`）、列表的 `.kana-line`（`:241`）**已经有小假名**，但在 `.study-row` 的**右邻列**（CSS `:38` 双列网格），不在中文「上面」；例句 `<span data-role="ja">focus(ex.ja)</span><br><span class="zh" data-role="zh">zh</span>`（`:227,:242,:477-478`）**日文原文已在中文上方**，但缺假名、无发音按钮。

### 4.2 最小实现（三步，零 seed 改动）

**第 1 步：把「小日语文字」放到中文上面 —— 纯 CSS + 模板重排**

`build_v5_site.py:38` 现在是左右双列：

```css
.study-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) auto;…}
```

改为纵向堆叠（`.study-ja`/`.study-meaning` 都 `grid-column:1/-1`），并新增：

```css
.kana-line{display:block;font-size:12px;line-height:1.4;color:var(--muted);letter-spacing:.02em}
.ex-ja{font-size:15px;line-height:1.6}
.ex .zh{display:block;font-size:14px;color:var(--muted)}
ruby rt{font-size:.58em;color:var(--muted);font-weight:400}
.speak{font-size:12px;padding:6px}
```

`.ex`（`:76-77`）改成三段结构，**中文上面依次是：日文原文 → 小假名行**：

```html
<div class="ex">
  <div class="ex-ja" data-role="ja">{日文原文} <button class="btn speak" data-speak="{日文原文}">发音</button></div>
  <div class="kana-line" data-role="ja">{kana_hint}</div>   <!-- 小的日语文字 -->
  <div class="zh" data-role="zh">{中文}</div>
</div>
```

**第 2 步：例句假名从现有 `kana` 推导（不改 seeds）**

在 `build_v5_site.py` 加一个构建期 helper，用**当天全部新词**建 `surface → kana` 映射，对例句做最长匹配替换：

```python
def kana_hint(ja, vmap):
    """读音提示：只用 vocabulary.jsonl 已有的 surface/kana，按最长词形匹配。"""
    out, i = [], 0
    while i < len(ja):
        hit = next((s for s in sorted(vmap, key=len, reverse=True) if ja.startswith(s, i)), None)
        if hit:
            out.append('<ruby>%s<rt>%s</rt></ruby>' % (esc(hit), esc(vmap[hit])))
            i += len(hit)
        else:
            j = i + 1
            while j < len(ja) and not any(ja.startswith(s, j) for s in vmap): j += 1
            out.append(esc(ja[i:j])); i = j
    return "".join(out)
```

- 词形带汉字时用 `<ruby><rb>…</rb><rt>…</rt></ruby>`；纯假名词直接给 `.kana-line` 小字即可。
- **诚实标注**：`terms_for_day()`（`lesson_emphasis.py:12-14`）本来就把 `v['kana']` 放进 `__FOCUS__`，所以 `focus()` 会自然把今日假名加粗；生成的提示必须写明「读音提示（按词条匹配），非逐字假名转写」——不能冒充完整 furigana。活用语尾、送り仮名、未在当天词表里的词不会命中，这是可接受的已知边界。
- **避免破坏现有高亮管线**：不要把 ruby 塞进 `focus()` 的输入字符串（`app.js:127-132` 是纯文本扫描，遇 `<ruby>` 标签会切坏）。把 `kana_hint` 作为**独立小字行**用 `esc()`/`emphasize()` 输出，与 `focus(ex.ja)` 并行，两边互不干扰 —— 这是「最小」的关键。
- 落地位置：`vcards[].ex.kana`（`build_v5_site.py:602-607` 加字段）、`build_grammar_html()` `:476-478` 的每条 `examples[:3]` 加一行 `.kana-line`。`web/data/day-NNN.json` 的 `vocab[].ex` 多一个 `kana` 键不影响 `release_guard.py`（它只查题目数组）。

**第 3 步：发音复用已有 `initSpeak()`，一行 JS 都不用加**

`build_v5_site.py:299-306`（`app.js:179-186`）已经是一个 **document 级事件委托**，只绑 `[data-speak]`：

```js
function initSpeak(){
  document.addEventListener('click',function(e){
    var b=e.target.closest('[data-speak]'); if(!b)return;
    if(!window.speechSynthesis){b.textContent='此设备不支持朗读';return;}
    var u=new SpeechSynthesisUtterance(b.getAttribute('data-speak'));
    u.lang='ja-JP'; u.rate=0.95; … speechSynthesis.cancel(); speechSynthesis.speak(u);
  });
}
```

要做的只是**给元素加 `data-speak="日文文本"`**：

| 位置 | 现在 | 改成 |
|---|---|---|
| 词列表朗读按钮 `build_v5_site.py:241` | `data-speak="'+safe(c.surface)+'"`（只念单词） | 保留一个念单词的，另加 `data-speak="'+safe(c.ex.ja)+'"` 念整句 |
| 词卡 `听发音` `:234` | `data-speak="'+safe(c.surface)+'"` | 卡片视图若删则一并删 |
| 语法例句 `:477` | **无** | 每条 `<div class="ex">` 加 `<button class="btn speak" data-speak="'+esc(e["ja"])+'">发音</button>` |
| 听力降级 `:641` | `data-speak="'+esc(m["audio_text"])+'"` | 保留 |
| `library.html` `:830-831` | `data-speak` + `<script src="assets/app.js">` | 保留，`app.js` 是共享的 |

**必须避开的 4 个已有冲突**：

1. **不要重复绑定**：`initSpeak()` 在 DOMContentLoaded 只调一次（`:321`）。历史上 `initMask()` 在 `initVocab().render()` 里被反复调用（`:237`）导致监听器线性累积（`reports/v5_review_after.md:251` 记录过）；发音按钮若放在 `renderList()` 里用 `addEventListener` 逐个绑，会重蹈覆辙。**统一靠 `[data-speak]` 委托**。
2. **不要放进 `.mask` 容器里**：`initMask()` 删掉后无此问题；但若保留局部遮挡，按钮必须放在 `[data-role]` 遮盖 span **之外**，否则点击会同时触发「临时揭示」。
3. **`u.onend/u.onerror` 会覆写 `b.textContent`**（`:304`），所以按钮内容只能是纯文本，不要塞 `<svg>`/子元素；若要图标，用 `data-label` 在 `onend` 里恢复（需改 `initSpeak`，非最小路径）。
4. **`app.js` 只在 `day-*.html` 和 `library.html` 加载**（`:434` / `:831`）；`review.html`、`unit-*.html` 只加载 `study.js`（`:586` / `:550`），**没有 `initSpeak()`**。若也要给 unit/review 页加发音，得引入 `app.js` 或把 `initSpeak()` 复制进 `study_ui.py::JS`。
5. `speechSynthesis` 需要用户手势、且依赖设备日语音色；`speechSynthesis.cancel()` 会掐掉正在播的另一句。没有音频文件可退，也不该造：45 个 m4a 与例句文本无关。

---

## 5. 遮挡下沉：新词 / 语法各自一个局部开关

### 5.1 现状四套入口（全删）

| 入口 | 位置 | 绑定到 |
|---|---|---|
| `#modeBtn` 四态循环 | `build_v5_site.py:365` + `:168-169` | `setMode()` → 全局 `mode` |
| `.study-toolbar` 3 按钮 | `:374` | `initViews()` `:142` → `setMode()` |
| 复习 / 新词 `.view-switch` 各 3 按钮 | `:379`, `:398` | 同上 |
| 词卡 `.eye`「切换遮盖」 | `:229` + `:170-184` | 卡片级 `data-mode` 四态 |

全部由 `applyMode()` `:148-160` 统一生效，且 `:150` 有一行特例 `if(el.closest('#grammar')){…return;}` —— **语法区永远不遮挡**。用户现在要语法也有自己的开关，这个特例必须一起删。

### 5.2 推荐实现：事件委托 + section 作用域

**不新增全局 `mode`，不写 localStorage 全局态**（或按模块存 `STORE+'mask.vocab'`/`STORE+'mask.grammar'`）。每个模块一个三态按钮组，用 `data-local-mask` 标注作用域：

```html
<!-- 在 #vocab 与 #grammar 的 h2 后面各放一份 -->
<div class="row local-mask" role="group" aria-label="新词遮盖">
  <button type="button" data-local-mask="vocab" data-side="all" aria-pressed="true">显示</button>
  <button type="button" data-local-mask="vocab" data-side="zh">遮中文</button>
  <button type="button" data-local-mask="vocab" data-side="ja">遮日语</button>
</div>
```

```js
function initLocalMask(){
  var state = {};                       // {'vocab':'all','grammar':'all'}
  function apply(section, side){
    var root = document.getElementById(section); if(!root) return;
    $$('[data-role]', root).forEach(function(el){
      var hide = side==='both' || (side==='zh'&&el.getAttribute('data-role')==='zh')
                              || (side==='ja'&&el.getAttribute('data-role')==='ja');
      el.classList.toggle('mask', hide);
      if(hide){el.setAttribute('tabindex','0');el.setAttribute('role','button');
               el.setAttribute('aria-label','内容已遮盖，按回车临时查看');}
      else{el.classList.remove('peek');el.removeAttribute('tabindex');
           el.removeAttribute('role');el.removeAttribute('aria-label');}
    });
    $$('[data-local-mask="'+section+'"]', root).forEach(function(b){
      b.setAttribute('aria-pressed', String(b.getAttribute('data-side')===side));
    });
  }
  document.addEventListener('click', function(e){
    var b=e.target.closest('[data-local-mask]');
    if(b){var s=b.getAttribute('data-local-mask');state[s]=b.getAttribute('data-side');
          apply(s,state[s]);return;}
    var m=e.target.closest('.mask'); if(m) reveal(m);           // 沿用 :133
  });
  document.addEventListener('keydown', function(e){
    if((e.key==='Enter'||e.key===' ')&&e.target.classList.contains('mask')){
      e.preventDefault(); reveal(e.target);}
  });
  ['vocab','grammar'].forEach(function(s){apply(s, state[s]||'all')});
}
```

要点：

- **事件委托 vs 每模块按钮**：按钮每模块各一份（满足「各自单独设置」），但**监听器只有 2 个 document 级**（click + keydown），与 `initSpeak()` 同构，不会随词卡渲染累积。不要给每个 `[data-role]` 绑 `onclick`。
- `data-role="zh"` 在新词卡里同时覆盖韩语 `ko` 释义（`:226,:242`），遮中文时韩语一起遮，符合 `CONTRACTS.md:278`「遮中文时同时遮韩语释义以免泄题」。语法 `ko-box`（`:482`）目前无 `data-role`，要不要一起遮需显式决定（建议补 `data-role="zh"`）。
- `.mask`/`.mask.peek`（`:78-79`）与 `reveal()`（`:133`）**保留**；`.eye`（`:80`）删。
- `@media print` `:114-115` 的 `.mask{filter:none!important}` 保留（打印时全部显示）。
- `focus()` / `emphasize()` 生成的 `<strong class="today-focus">` 在 `[data-role]` 内部，会被整块 blur，不影响。

### 5.3 删掉 `initMask()/applyMode()/setMode()/initViews()` 后哪些 JS 会失效

| 被引用处 | 引用内容 | 处理 |
|---|---|---|
| `build_v5_site.py:206` `initReview()` `render()` | `applyMode($('#reviewCard'))` | 删卡片视图则整段删 |
| `build_v5_site.py:237` `initVocab()` `render()` | `applyMode(area); initMask();` | **删**（这是重复绑定的根源） |
| `build_v5_site.py:243` `initVocab()` `renderList()` | `applyMode(list);` | 删，改由 `initLocalMask()` 统一 `apply('vocab',…)` |
| `build_v5_site.py:321` DOMContentLoaded | `initMask(); initViews();` | 删，改 `initLocalMask()` |
| `build_v5_site.py:142` `initViews()` | `$$('[data-mask]')…setMode` | 随 `initViews()` 一起删 |
| `build_v5_site.py:159` `applyMode()` | `$('#modeBtn').textContent=…` | 删 |
| `build_v5_site.py:337` `#finish` 的 `#saveStatus` | 与遮盖无关 | §6 单独处理 |
| `build_v5_site.py:145` `mode` 变量、`:228` `data-mode="'+mode+'"` | 词卡 HTML | 删 |
| `study_ui.py:76-79` `mask/masking/maskControls/card` | **独立一套** `data-side` / `data-study-mask`，服务于 `unit-*.html` 与 `review.html` | **与本次改动无关，保留**；别误删 |

### 5.4 词卡翻页是否还要 —— 建议删

理由：(a) 用户要「只专注内容」「不要翻页」；(b) `initVocab()` 的卡片分支是唯一会重复调用 `initMask()`/`applyMode()` 的地方，删掉它可彻底消除多套遮盖入口；(c) `#vocabList`（`:240-242`）已经完整承载词形/假名/释义/例句/韩语/自评/发音，卡片是冗余。

**保留**：`initVocab()` 的 `#extraVocab`（`:218` 选学拓展勾选）与 `renderList()`（`:239-244`）、`initReview()` 的列表行 + `NHStudy.rate`（`:200-204`）、`#reviewList`。
**删除**：`#vocabCard`/`#vArea`/`#vPrev`/`#vNext`（`:400-403`）、`#reviewCard`/`#rShow`/`.rRate`（`:381-389`）、`vState`/`reviewState.i`（`:191,:213`）、`initViews()` 的 `setView()`/列表卡片切换（`:134-141`）、CSS `:71-77` 的 `.vcard/.surface` 等（若词卡删干净）。

若决定**保留**卡片视图，则必须保留 `setView()`+`[data-view]` 绑定，但把 `initViews()` 里 `:142` 的 `[data-mask]→setMode` 那行摘掉，并在 `render()` 里去掉 `applyMode(area); initMask();` 两行。

---

## 6. 底部：只留一个「完成」按钮

### 6.1 现有 `#finish` handler 做了什么（`build_v5_site.py:329-349` / `app.js:209-229`）

**不只是 sync**，共 7 件事：

1. `:332` `collectPayload()` → `{v:1, practice_mode:'choice', day, session, minutes:null, ts, source:'web', results:QUIZ_RESULTS, review_ratings:[], sentences:[]}`（定义 `:307-312`）。
2. `:333-342` 读 `localStorage['nh80.v5.pending.<day>']` 旧载荷，用 `window.__QUIZ__+__LISTEN__+__SENT__` 做 **stale qid 过滤**（注意**不含 `__PRACTICE__`**），有陈旧题则把旧载荷另存 `archive.<day>.<ts>`，合并有效旧 results/review_ratings 到本次。
3. `:343-345` 置 `LATEST_PAYLOAD`、写 `sessionStorage['nh80.v5.session.<day>']`、写 `localStorage` pending、按钮 `disabled` + 「正在保存…」。
4. `:347` `sync(payload)` → **POST `/api/events`**，带 `X-NH80-Key = sessionStorage['nh80.v5.access']`（`sync()` `:314-319`；无口令直接 reject）。
5. `:347` 成功后删 pending、文案「作答已保存」、`#restartPractice.hidden=false`、`#saveStatus` 写「已同步。会话读取后会核对必做题是否齐全、正确率是否达到70%。」、`localStorage['nh80.v5.lastDay']=day`。
6. `:348` 失败后恢复按钮「保存失败，点击重试」+ 错误文案，作答留在本机。
7. `:321` 之外还有**第二套写入**：`initQuiz()` `:282` 调 `window.NHStudy.attempt()` → `study.js:29` 本地队列 → `flush()`（`study.js:36`）批量 POST `/api/events`；自评走 `/api/reviews`。两套共用 `sessionStorage['nh80.v5.session.<day>']`，但**独立发起请求**。

### 6.2 要删的按钮与其来源（完整清单）

| 按钮 / 文案 | 来源 |
|---|---|
| 学习口令 `#studyAccess` | `study_ui.py:83` 运行时注入（占位 `build_v5_site.py:425`） |
| 同步 `#studyFlush` | 同上 |
| 导出待同步记录 `#studyExport` | 同上（→ `exportPending()` `study_ui.py:69`） |
| `#studyStatus` 文案 | 同上（→ `tell()` `study_ui.py:49`） |
| 必做题…说明 + `#saveStatus` | `build_v5_site.py:427` / `app.js:325,338,347,348` |
| 导出作答 `#exportAnswers` | `build_v5_site.py:427` + handler `:323-327` |
| 再练一轮 `#restartPractice` | `build_v5_site.py:428` + handler `:328` + `:347` 显示 |
| 保存本次作答 `#finish` 的旧逻辑 | `build_v5_site.py:429` + handler `:329-349` |
| 第一课 / 课程目录 / 下一课 | `build_v5_site.py:430` + `:653` |
| 署名行 | `build_v5_site.py:430` |
| `#accessKey` 死代码 | `build_v5_site.py:322` |

### 6.3 「完成」按钮应上报的字段草案

```js
{
  v: 1,
  practice_mode: 'choice',        // 必须保留且恒为 'choice'，CLI 靠它判定免教师验收
  day: Number(document.body.dataset.day),        // 1..150，Worker strictInt
  session: 'web-<day>-<uuid>',    // 与 study.js 共用 sessionStorage['nh80.v5.session.<day>']
  ts: new Date().toISOString(),   // client_ts，Worker :240 截 40 字符
  source: 'web',
  results: [                      // 逐题明细，长度 ≤40（MAX_RESULTS）
    { qid, answer, seconds, hinted, revealed_before_submit }
  ],
  review_ratings: [ {kid, rating} ],  // 自评：again|hard|good；见下
  sentences: [],                  // 元数据占位，必须与同 session 其他 POST 完全一致
  // —— 以下为客户端自算、非权威，仅用于本机 UI / 本地导出 ——
  attempted: n, total: m, accuracy: 0.xx,
  self_rating: 'again'|'hard'|'good'|null,
  completed_at: ISO
}
```

**字段落地约束（务必遵守，否则 400/409）**：

- Worker `handlePostEvents()`（`index.ts:197-291`）**只读** `v/day/check/session/results/client_ts/minutes` 与元数据 `review_ratings / sentences / practice_mode`（`:259`）；**其余顶层字段被静默丢弃**。所以 `accuracy`、`self_rating`、`attempted`、`completed_at` 现在**不会入库**。要真正落库有三条路：
  - (a) 扩 Worker：加 `/api/completion` 端点或 `events` 新列 + migration（`deploy/migrations/0005_*.sql`）+ `release_guard.py:56-57` 仍要禁止 `generated-key.json` 被打包；`cloud_sync.py:190-207` / `study_sync.py:61-76` 的 `_validate_event` 也要同步放字段。
  - (b) 把自评塞进 `review_ratings`（`nh80.py:560-574` 会走 `learning.apply_review_rating` 排期）——但**会改变 session metadata**。
  - (c) **推荐（最小）**：`accuracy` 只用于按钮上的即时文案（「已完成 28/31，正确率 90%」），不上报；权威正确率由 `cmd_finish_day()` `nh80.py:773-793` 用本地重算结果得出。自评走既有 `NHStudy.rate()` → `/api/reviews`，不混进 `/api/events`。
- **`session metadata` 不可变**：`index.ts:259-264` 把 `{review_ratings, sentences, practice_mode}` 存进 `study_sessions.payload`，同 session 后续 POST 若不同 → **409 `session_metadata_conflict`**；`tests/test_worker_access.mjs:50-55` 明确断言这一点。而 `study.js::flush()`（`:65`）提交 attempts 时**不带** `review_ratings`/`sentences`（Worker 用 `?? []` 补空），`app.js::sync()` 带空数组——两者必须继续一致。**给「完成」加任何顶层元数据字段都要两边同步改，且不能只改一次提交的形状**。
- `results.length===0` → `empty_results` 400（`index.ts:238`）；未答任何题就点「完成」要在本机拦截并提示。
- `qid` 必须 ≤48 字符且匹配 `^[A-Za-z0-9_.:-]{1,48}$`（`:180`），`knowledge_ids` 必须 `^[VGK]\d{4}$`（`:255`）——§3.2 的 `build_merged()` 天然满足。
- **完成 ≠ 达标**：`CONTRACTS.md:283` 明确「网页保存只说明云端收到，权威完成仍在本地导入后计算，不信客户端 correct」。按钮文案应写「完成 / 已保存到本机」，不要写「已达标」。

### 6.4 最棘手的一点：删掉口令 UI 后按钮还能不能工作

`app.js::sync()` `:315` 与 `study.js::post()`（`study_ui.py:61`）都要求 `sessionStorage['nh80.v5.access']`，而页面上唯一的写入口就是被删掉的 `#studyAccess`（`study_ui.py:83`）。**删掉它后两条 POST 路径都会失败**。必须在动手前选定其一：

- **方案 1（推荐，最贴合「只留一个完成按钮」）**：完成按钮**只写本机**（`localStorage['nh80.v5.pending.<day>']` + `study.js` 的 `nh80.v9.pending.*` 队列），文案「已保存到本机，等待会话导入」；删掉 `app.js::sync()`、`#saveStatus`、所有 `fetch('/api/events')` UI 触发点；由 `python3 scripts/nh80.py import-file --file nihongo-pending.json`（`CONTRACTS.md:293`、`HANDOFF.md:18`）在会话侧导入。`study.js::flush()` 保留但只在有口令时自动跑（口令由会话侧注入 `sessionStorage`），页面不再提供输入框。
- **方案 2**：保留一个**非 UI** 的口令注入（例如 URL 参数 / 会话脚本写入 `sessionStorage`），完成按钮继续 POST。需要明确写进 `CONTRACTS.md` 并让 `release_guard.py` 不误判。
- 无论哪种，`localStorage['nh80.v5.lastDay']`（`:347`）要保留，`index.html:705` 的「继续学习」靠它。

---

## 7. 回归风险：必须同步更新的生成物、测试、契约与守卫

### 7.1 必须重生成的产物（全部由 `python3 scripts/nh80.py build` 一次产出，禁止手改）

| 产物 | 数量 | 变更点 |
|---|---|---|
| `web/day-NNN.html` | 150 | 模板、脚本全局、单块题目、`#finish` |
| `web/data/day-NNN.json` | 150 | 加 `questions` 键；保留 `quiz/sentences/practice/unit_questions` |
| `web/assets/app.js` | 1 | `build_v5_site.py::JS` |
| `web/assets/study.js` | 1 | `study_ui.py::JS` |
| `web/assets/app.css` | 1 | `build_v5_site.py::CSS + study_ui.py::CSS` |
| `web/sw.js` | 1 | `build_v5_site.py:833-840` |
| `curriculum/curriculum.json` | 1 | `nh80.py:291`（`question_ids` 不变，但文件被整体重写） |
| `deploy/worker/src/generated-key.json` | 1 | `nh80.py:292`，B′ 方案 8007→8547 |
| `web/data/grade/day-NNN.json` | 150 | `nh80.py:293-296`，每个 qid 的 `answer_hash`（SHA-256，非 FNV）|
| `data/state.db` 的 `questions` 表 | 8007→8547 | `nh80.py:277-289`，**这是状态写入**，需用户授权后执行 |
| `web/index.html` / `review.html` / `unit-*.html` / `listening.html` / `resources.html` / `library.html` | 30+ | `build_v5_site.py::main()` 全量重写 |

`deploy/worker/src/generated-key.json` **不打包进 Worker**（`release_guard.py:56-57` 断言、`CONTRACTS.md:294`）；Worker 判分读的是公开的 `web/data/grade/day-NNN.json`（`index.ts:118-127`）。**两者必须同批生成**，否则页面新 qid 会被 `unknown_or_wrong_day_question` 400 拒绝（`:251-257`）。

### 7.2 `web/sw.js` —— 最重要的隐藏地雷

`build_v5_site.py:833`：

```python
revision = sha256((CSS + JS + study_ui.CSS + study_ui.JS + json.dumps(cur)).encode()).hexdigest()[:12]
```

**`HTML` 模板字符串不在哈希里**。若本次只改 HTML 模板（顶部/底部删减）而 JS/CSS 改动恰好抵消或未改，`C='nh80-v5.1-e03c5bd29321'`（见当前 `web/sw.js`）**不会变**，Service Worker `activate` 不删旧缓存，`fetch` 优先走网络但离线回退会命中旧 HTML（`index.ts` 之外由 `sw.js:837-839` 的 cache-first 逻辑），用户会长期看到旧页面。

**必须**：把 `HTML` 加进 `:833` 的哈希输入，或显式把版本串改成 `nh80-v5.2-<revision>`。同时 `index.html` 的 `<a id="resume">`、`day-*.html` 的 `<script src="assets/app.js">` 无版本号，缓存失效完全依赖这个 `C`。

### 7.3 测试文件（逐条，跑 `python3 -m unittest discover -s tests` + `node tests/test_worker_access.mjs`）

| 文件:行 | 现有断言 | 需要改 |
|---|---|---|
| `tests/test_v5.py:108-114` | `day-001.html` 含 `id="sentences"` / `id="quiz"` / `modeBtn` / `data-role="ja"` / `data-role="zh"` | 删 `sentences`/`quiz`/`modeBtn` 断言，改 `id="questions"`；`data-role` 仍应存在（局部遮挡用） |
| `tests/test_v5.py:116-118` | day-047 含 `id="listening"` | 保留（听力 `<audio>` 段落不删） |
| `tests/test_v5.py:120-127` | `d["quiz"]` ≥4、含 `h`/`oh`、无 `answer` | 若保留 `quiz` 键则不动；建议**新增**对 `d["questions"]` 的同类断言 |
| `tests/test_v5.py:176-181` | 每页 `class="min">(\d+) 分钟` 求和 **== 42** | 若删掉 h2 的分钟标签 → 全 150 天失败。**保留 `<span class="min">N 分钟</span>`**（它不算顶部杂项），或同步改测试断言 |
| `tests/test_v5.py:184-197` | `html.index('id="listening"') < html.index('id="sentences"')` | **必挂**：`#sentences` 被删。改成 `< id="questions"`，或更新断言 |
| `tests/test_v5.py:199-205` | `p['quiz']`/`p['sentences']` 无 `rationale`/`answer_ja` | 保留旧键则不动；加 `p['questions']` 检查 |
| `tests/test_v5.py:223-230` | day-047 `p['quiz']` 每个 qid 在 DB `questions` 表 | 保留旧键则不动；加 `p['questions']` 全量检查（这是防「页面题号与答案表错位」的关键新断言） |
| `tests/test_v5.py:98-106` | 150 页 / 无仪表盘关键词 | 不受影响 |
| `tests/test_v7.py:168-178` | `len(ids)==8007` 且 `set(DB ids)==set(generated-key keys)` | B′ 方案改 **8547**；A 方案不动 |
| `tests/test_v7.py:180-189` | day-047 含 `listening.html`/`真人听力`；`app.js` 含 `lastPassage` | 顶部链接删了但 `listen_html:644` 仍有；`lastPassage` **必须保留**（§3.7） |
| `tests/test_v7.py:196-209` / `:211-230` | 音频双格式 / D1 隔离 / `release_guard` | 不受影响，`release_guard.py` 输出仍须含 `isolated` |
| `tests/test_completion_gate.py:35` | 按 40 分批 `cmd_import_web` | 印证 `MAX_RESULTS=40`；merged ≤36 时单批即可，但仍应加一条「merged 长度 ≤40」的断言 |
| `tests/test_worker_access.mjs:50-60` | `session_metadata_conflict` 409 / 同 session 追加 | **加字段会触发 409**，见 §6.3 |
| `tests/test_emphasis.py:9-12` | `emphasize()` 输出 `<strong class="today-focus">` | 保留 `lesson_emphasis.py`，不受影响 |
| `tests/test_content_invariants.py` / `test_study_sync_late_rating.py` | 内容 / FSRS 时间 | 不受影响 |

### 7.4 `scripts/release_guard.py` 的断言

| 行 | 断言 | 影响 |
|---|---|---|
| `:19-23` | `web/` 文件数 <20000、单文件 <25MB、无 `.key/.db/.wav` 等 | 新增 540 条答案表 ~45KB、grade 分片增大，仍远低于限额 |
| `:31-40` | `web/audio/NOTICE.txt` + manifest 45 条 + 逐条 `text_sha256`/bytes/时长 | **不要动音频**；删署名行 HTML 不影响文件存在，但 `DATA_LICENSES.md` / `resources.html:810-814` 的许可说明要保留（署名义务） |
| `:41-44` | vocabulary 每行 `ko_hint` | 不改 seeds，安全 |
| `:45-52` | `d['quiz']+d['sentences']+d.get('practice',[])+d.get('unit_questions',[])+listening.questions` 无 `answer`/`rationale`；`core` 上限 11/16、`core∩extra=∅`、`len(core)+len(extra)==len(d['vocab'])` | **`:47` 必须加 `d.get('questions',[])`**；`d['vocab']` 仍须等于 `new_vocab_ids` 全量（`build_v5_site.py:600` 已是），否则合并后若只渲染 core 词会挂 |
| `:53-55` | 150 个 grade 分片、每个 `answer_hash` 是 64 位 hex、无明文 `answer` | B′ 重生成后自动满足；**漏跑 `nh80 build` 会立刻挂** |
| `:56-57` | `generated-key.json` 不得出现在 `index.ts` | 若加 `/api/completion` 端点别误引这个文件 |
| `:24-30` | `run_worker_first` / 两个不同 `database_id` / `nihongo80-preview` | 不受影响 |

### 7.5 `deploy/worker/src/index.ts`（若需新字段）

- `MAX_RESULTS=40`（`:45`）、`parseResults` qid 48 字符（`:180`）、`strictInt(day,1,150)`（`:218`）、`MAX_BODY_BYTES=64KB`（`:46`）、metadata ≤16KB（`:260`）。
- `loadAnswerKey()`（`:118-127`）读 `/data/grade/day-NNN.json`，`:251-257` 校验 `entry.day===day`、`knowledge_ids` 格式。
- `metadata` 不可变（`:259-264`），`tests/test_worker_access.mjs:50-55`。
- 若加「完成」字段：需新 migration（`deploy/migrations/0005_*.sql`）+ `EVENT_COLUMNS`（`:297-299`）+ `cloud_sync.py:190-207` / `study_sync.py:61-76` 的解析；并更新 `CONTRACTS.md` §10。

### 7.6 契约与文档（必须先改）

`CONTRACTS.md:3` 自称唯一接口依据。至少要改：

- `:204` 「页面练习只含选项及哈希」→ 加「单一 `__QUESTIONS__` 数组」；
- `:227` 「每日十句中前三句必做、其余七句拓展」→ 废止分段；
- `:279` 「3题必做、7题拓展；六题综合与听力三题仍保留」→ 改为单块 + 覆盖算法；
- `:280` 「总答案表为2535题」→ 已过时（现 8007，B′ 后 8547）；
- `:288` 「新增可选翻页练习」→ 删除；
- `:9` `web/data/day-NNN.json` 结构示例（`:119-134`）→ 加 `questions`；
- `HANDOFF.md:14` 「每天选做24–36题」、`:25` 「三题必做、七题拓展」；
- `reports/v9_completion.md:9`、`reports/v9_practice.md` 的「4872 每日」措辞（实测为 150 天合计）。
- `AGENTS.md`、`scripts/session_v5.py:106` 的 brief 文案若引用「3道选句/6道综合」也要同步。

---

## 8. 建议执行顺序（供实施阶段参考，本次**未执行**）

1. 先改 `CONTRACTS.md` / `HANDOFF.md`（契约先行）。
2. 改 `scripts/practice_v9.py`：新增 `build_merged()` + 覆盖/唯一性断言；`build_daily()` 与 `build_unit()` 保留。
3. 改 `scripts/nh80.py::_build_v5()`：登记 `extra`；`question_ids` 不动。
4. 改 `scripts/build_v5_site.py`：CSS/JS/HTML/main 四层一次性改完；`:833` 把 `HTML` 加进 sw revision。
5. 改 `scripts/study_ui.py::JS::init()`：删 `#studySync` 控件；保留 `NHStudy`/`deck`/`renderPersonal`。
6. 改 `scripts/release_guard.py:47` 与 `tests/*.py` 的 6 处断言。
7. `python3 scripts/nh80.py build`（**会写 `data/state.db`，属状态写入，需单独授权**）→ 检查 `git status` 的生成物数量与 `sw.js` 的 `C` 是否变化。
8. `python3 scripts/release_guard.py`、`python3 -m unittest discover -s tests -v`、`node tests/test_worker_access.mjs`。
9. 浏览器实测：`curl` preview 的 `day-001.html` 与本地一致；移动端 375px 无横向溢出；点「完成」在有/无口令两种情况下的行为；`speechSynthesis` 在语法例句上发音；`#grammar` 局部遮挡生效而 `#vocab` 不受影响。
10. 部署后再 `curl` 线上确认 Service Worker 缓存已失效（§7.2）。

---

## 附：本次审查用到的可复现命令

```bash
# 线上 = 本地
curl -sS https://nihongo80.cmjfire.workers.dev/day-001.html -o /tmp/online.html
diff /tmp/online.html web/day-001.html

# 生成物 = 源码模板
diff <(python3 -c "import re,pathlib;print(re.search(r'^JS = r\"\"\"(.*?)^\"\"\"',pathlib.Path('scripts/build_v5_site.py').read_text(),re.S|re.M).group(1),end='')") web/assets/app.js
diff <(python3 -c "import re,pathlib;print(re.search(r'^JS = r\"\"\"(.*?)^\"\"\"',pathlib.Path('scripts/study_ui.py').read_text(),re.S|re.M).group(1),end='')") web/assets/study.js

# 题量与覆盖统计（本报告 §2 数据来源）
python3 - <<'PY'
import json, pathlib, collections
cur = json.loads(pathlib.Path('curriculum/curriculum.json').read_text())['days']
for n in (1, 47, 150):
    d = json.loads(pathlib.Path('web/data/day-%03d.json' % n).read_text())
    cd = cur[n-1]
    arrays = {'quiz':d['quiz'],'sentences':d['sentences'],'practice':d['practice'],
              'listening':(d.get('listening_material') or {}).get('questions',[]),
              'unit_questions':d.get('unit_questions') or []}
    cnt = collections.Counter(k for v in arrays.values() for q in v
                              for k in (q.get('knowledge_ids') or []))
    print(n, {k:len(v) for k,v in arrays.items()},
          'question_ids=',len(cd['question_ids']),
          'new_vocab=',len(cd['new_vocab_ids']),
          'missing_vocab=',[k for k in cd['new_vocab_ids'] if cnt[k]==0],
          'missing_grammar=',[k for k in cd['new_grammar_ids'] if cnt[k]==0],
          'per_kid=',dict(collections.Counter(cnt[k] for k in cd['new_vocab_ids'])))
print('sum practice =', sum(len(json.loads(pathlib.Path('web/data/day-%03d.json'%n).read_text())['practice']) for n in range(1,151)))
PY
```
