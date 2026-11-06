# 官方日语教学资源站点核验记录（人读版）

- 核验日期：**2026-11-06**
- 核验方式：`WebFetch` 真实访问（必要时 `WebSearch` 辅助定位官方页面）；另用 `curl -I` 仅取 HTTP 响应头
- 核验范围：任务指定的 8 个 URL，且仅为**公开页面的元信息核验**；未批量抓取、未下载任何受限版权教材正文/PDF/MP3 内容
- 记录原则：所有结论均有当次工具返回的页面标题/原文片段作为 evidence；访问失败或部分失败时明确标注，绝不补写猜测内容
- 结果：**完全成功（OK）6 / 部分成功（PARTIAL）1 / 失败（FAIL）1**

---

## 一、汇总表

| # | 来源 | URL | fetch_status | 是否成功获取 |
|---|------|-----|--------------|--------------|
| 1 | IRODORI: Japanese for Life in Japan | https://www.irodori.jpf.go.jp/en/ | OK | 是 |
| 2 | Marugoto e-Learning | https://marugoto.jpf.go.jp/en/e-learning/ | OK | 是 |
| 3 | JF Japanese e-Learning Minato | https://minato-jf.jp/ | OK | 是 |
| 4 | NHK WORLD Easy Japanese | https://www.nhk.or.jp/lesson/ | PARTIAL | 主 URL 内容不完整；经官方子页面补全 |
| 5 | Erin's Challenge! Contents Library | https://erin.jpf.go.jp/ | **FAIL** | 否，无法访问，未核实 |
| 6 | Tadoku Our Graded Readers | https://tadoku.org/japanese/en/graded-readers-en/ | OK | 是 |
| 7 | JLPT Let's Try Sample Questions | https://www.jlpt.jp/e/samples/forlearners.html | OK | 是 |
| 8 | JLPT Level Summary | https://www.jlpt.jp/e/about/levelsummary.html | OK | 是 |

---

## 二、特别核实项结论

### 2.1 JLPT N3 官方样题页面提供哪些题型、是否可下载 PDF

**目标页 `forlearners.html` 本身只给说明和两个链接，未列出 N3 题型、也未给 PDF。** 其原文：
> "Sample questions show the form of test items on the JLPT. Sample questions are organized by level, from N1 to N5. One sample question is offered for each test item type. There may be differences from questions in the actual test booklet."
> "For more practice, please refer to ["New Japanese-Language Proficiency Test Sample Questions"](https://www.jlpt.jp/e/samples/sample09.html) or ["Japanese-Language Proficiency Test Official Practice Workbook."](https://www.jlpt.jp/e/samples/sampleindex.html)"

为完成核实，额外真实访问了 `sample09.html`、`sampleindex.html`、`guideline/testsections.html`（均成功）：

**（a）可下载 PDF：是（免费、官方直链）** —— 来自 `sample09.html` 逐条链接：
- 试题：`https://www.jlpt.jp/e/samples/pdf/N3-mondai.pdf`（3.1MB）
- 答题纸：`N3-kaitou.pdf`（370KB）
- 听解脚本：`N3-script.pdf`（1.33MB）
- 答案：`N3-seikai.pdf`（38.8KB）
- 听解音频：`https://www.jlpt.jp/e/samples/mp3/N3Sample.mp3`（11.0MB，MP3）
- 全级别题型构成：`sample_kousei.pdf`（2.94MB，In Japanese）
- 指导语变更：`shijibun_henkou.pdf`（103KB）
- `curl -I` 实测：`N3-mondai.pdf`、`sample_kousei.pdf`、`N3Sample.mp3`、`n3_e.pdf` 均返回 **200**（`application/pdf` / `audio/mpeg`）。

**（b）N3 题型** —— 来自 `https://www.jlpt.jp/e/guideline/testsections.html` 表格原文（○＝该级别有，―＝该级别无）：

考试科目与时间：
> `N3 Language Knowledge(Vocabulary)〈30min〉 Language Knowledge(Grammar)・Reading〈70min〉 Listening 〈40min〉`

题型构成（N3 列）：
| 科目 | 题型 | N3 |
|---|---|---|
| 文字·词汇 | Kanji reading（汉字读法） | ○ |
| | Orthography（表记） | ○ |
| | Word formation（构词） | ― |
| | Contextually-defined expressions（文脉规定） | ○ |
| | Paraphrases（近义替换） | ○ |
| | Usage（用法） | ○ |
| 语法 | Sentential grammar 1 (Selecting grammar form) | ○ |
| | Sentential grammar 2 (Sentence composition) | ○ |
| | Text grammar（文章语法） | ○ |
| 读解 | Comprehension (Short passages) | ○ |
| | Comprehension (Mid-size passages) | ○ |
| | Comprehension (Long passages) | ○ |
| | Integrated comprehension（综合理解） | ― |
| | Thematic comprehension (Long passages)（主张理解） | ― |
| | Information retrieval（信息检索） | ○ |
| 听解 | Task-based comprehension（课题理解） | ○ |
| | Comprehension of key points（要点理解） | ○ |
| | Comprehension of general outline（概要理解） | ○ |
| | Verbal expressions（语言表达） | ○ |
| | Quick response（即时应答） | ○ |
| | Integrated comprehension（综合理解） | ― |

该页另给出 N3 题型目的 PDF：`https://www.jlpt.jp/e/guideline/pdf/n3_e.pdf`（`curl -I` 实测 200）。

> 注意：`sample09.html` 明确标注该套样题为 "(published 2009)"、**2010 年改版前**编制，"the number of questions is different from the number of test items in an actual test"，并附 "Changes in directions" 提示；`sampleindex.html` 说明 2012 与 2018 Vol.2 两本官方练习册由 Bonjinsha **销售（付费）**。故免费部分仅为样题集，不等于现行真题或完整练习册。

### 2.2 `levelsummary.html` 页面 N3 能力描述原文要点

标题：`N1-N5: Summary of Linguistic Competence Required for Each Level | JLPT Japanese-Language Proficiency Test`

总述原文：
> "The JLPT has five levels: N1, N2, N3, N4 and N5. The easiest level is N5 and the most difficult level is N1."
> "N4 and N5 measure the level of understanding of basic Japanese mainly learned in class. N1and N2 measure the level of understanding of Japanese used in a broad range of scenes in actual everyday life. **N3 is a bridging level between N1/N2 and N4/N5.**"
> "While not noted in the table, **Language Knowledge, such as Vocabulary and Grammar, is also required** for successful execution of these activities."

**N3 原文（逐字）**：
> 能力概要：**"The ability to understand Japanese used in everyday situations to a certain degree."**
>
> Reading：
> - "One is able to read and understand written materials with specific contents concerning everyday topics."
> - "One is also able to grasp summary information such as newspaper headlines."
> - "In addition, one is also able to read slightly difficult writings encountered in everyday situations and understand the main points of the content if some alternative phrases are available to aid one's understanding."
>
> Listening：
> - "One is able to listen and comprehend coherent conversations in everyday situations, spoken at near-natural speed, and is generally able to follow their contents as well as grasp the relationships among the people involved."

要点归纳（不改动原文的前提下）：N3 是 N4/N5 与 N1/N2 之间的**桥梁级别**；读解要求理解日常话题的具体内容、读懂报纸标题类概要信息、在提供替换表达时能理解日常场景中略难文章的主旨；听解要求以接近自然语速理解日常连贯会话、把握内容与人物关系；表格只覆盖 Reading/Listening，语言知识（词汇、语法）另属必需。

### 2.3 Irodori 是否提供免费可下载的 PDF/音频及其许可证条款

**免费可下载：是（有官方明文）。** 三条独立证据：
1. `https://marugoto.jpf.go.jp/en/e-learning/` 原文：
   > "You can download all the lesson materials in PDF format and as audio files **free of charge** on the "Irodori" website."
2. Irodori 首页给出 4 个级别的 `pdf.html` 入口与 `Digital audio files（MP3）`、各级 `Lesson 1–18 (MP3 playback)` 入口。
3. `https://www.irodori.jpf.go.jp/en/faq.html` Q29 原文："Audio files for downloading are compressed as ZIP files."（亦说明可流媒体播放）；Q31 原文："You should download PDFs with audio files on your own PC and open them with Adobe Acrobat Reader."；Q7 "At present, there are no plans to sell Irodori in print format."、Q8 "You can also print it in black and white."

> 注意：Irodori **首页本身**并未出现 `free` / `download` 字样，仅见 `pdf.html` 页面与 MP3 入口；"免费"这一措辞来自同批核验的 Marugoto 官方页面与 FAQ。

**许可证：不是 Creative Commons，是站点自定义《Terms of Use》**（`https://www.irodori.jpf.go.jp/en/privacy.html`，标题 "About this site | IRODORI Japanese for Life in Japan"）：
> "1. The copyright (or intellectual property rights) of all information (text, illustrations, images, sound, etc.) posted on This Site belongs to the Institute, the original author, and other rights holders."
> "2. The information contained on This Site may not be reproduced, copied, or altered, in whole or in part, **for any purpose other than for private use or use by schools or other educational institutions**."
> "3. If you produce your own teaching materials or worksheets using all or part of the information posted on This Site and release them to the public, **they must be free and please specify the source of the information**."
> "4. However, you may not use all or part of the information posted on This Site to produce new educational materials that are **not at all related to This Site**, whether they are offered for a cost or are free."
> 禁止项含 "(6) Use This Site for **commercial purposes**"；版权行 "Copyright© The Japan Foundation Japanese-Language Institute, Urawa, **All Rights Reserved**"。

FAQ Q22–Q28 补充的可使用范围（原文要点）：可印刷装订并出借/分发给学员（仅限课堂使用，可收印制成本费但**不得盈利**）；可用于付费课程；可转 PPT、加音频、加练习题自制 worksheets；自制教材可在线公开发布分享但**不得售卖**；插图不得改作（可裁切）且仅限 Irodori 教学使用。

> 结论：任务提示中"JF 系教材多为 CC BY-NC 或禁止再分发"——**Irodori 实测并非 CC BY-NC**，而是"版权保留 + 限定私用/教育用途 + 禁止商用 + 衍生教材须免费并注明来源"的自定义条款，已如实标注，未按印象套用 CC 许可。

### 2.4 Tadoku graded readers 的免费 PDF 许可范围

主页面 `graded-readers-en/` 原文（免费范围）：
> "Web Tadoku Books ＊FREE — Members of NPO Tadoku Supporters created these free readers to increase the number of books for tadoku and promote tadoku. **Available online with a web browser and/or download and print into book formats.**"
> "Price: FREE"

日文表格逐字（含最明确的使用范围）：
> "Web Tadoku Books【無料】（NPO多言語多読）… **PDFデータを無料公開しています。端末にダウンロードしたり、印刷・製本してご利用いただけます。サイト上で読むこともできます。** なし"

**许可范围**经真实访问官方条款页 `https://tadoku.org/japanese/en/free-books-en/note-en`（标题 "Guide to Using Our Free Tadoku Books - にほんごたどく"）核实：
> "use the books according to the **‘CC BY-NC-ND 4.0’** license."
> 允许分享链接："Absolutely yes! When sharing, please make sure to **give credit to ‘NPO多言語多読’**."
> 允许课堂使用下载 PDF/打印本："Sure! Feel free to use them (**even in commercial activities**) only if they are used for tadoku in university or Japanese language school classes, or for personal learning support. Just remember **not to make any changes**. If it's for commercial use, a donation would be greatly appreciated."
> 禁止改作后发布："No. You may not publish them after making any changes."；"**Please don't make any changes or add anything.** For instance, you cannot: Create videos… / Add translations, explanations, tests, etc., and use them as classroom material. / Make audio readings and publish them on websites, etc."
> 禁止转售："No, **commercial resale is not allowed**."

即：**CC BY-NC-ND 4.0** —— 需署名 NPO多言語多読；可免费下载/打印/制本、可分享链接、可在大学/日语学校课堂及个人学习支持中使用（官方明确含商业性教学活动，建议捐赠）；**但禁止任何改作/加注/翻译/出声朗读后公开发布，禁止商业转售**。第三方免费读物（other-grs 列表，托管于 Jimdo/Padlet/Notion/Wix 等）可能各有独立条款，本页未逐站核实。

---

## 三、来源逐条记录

### 1. IRODORI: Japanese for Life in Japan
- **URL**：https://www.irodori.jpf.go.jp/en/
- **category**：official_material
- **fetch_status**：OK
- **内容类型与覆盖范围**：免费可下载的 PDF 教材（课本/词表/答案/语法练习/句型表/插图）、MP3 音频（课文/词表/语法练习）、带音频 PDF、教学指导视频与在线课程入口。4 个级别 Starter / Elementary 1 / Elementary 2 / Pre-Intermediate，每级 18 课（Starter 另含 lesson00）；全四册共 **644 汉字**（FAQ Q15）；总学时约 **360–500 小时**（Q14）；FAQ Q11 自述 Starter–Elementary 2 相当于 **JLPT N4**，Pre-Intermediate 达 A2/B1（Q5）。面向在日生活/工作所需基础日语，基于 "JF Can-do for Life in Japan"。
- **可用语言**：首页见 `JP EN` 切换、`Editions in other languages`、乌克兰语 Starter 版链接；完整 22 种语言版清单来自同批核验的 Marugoto e-Learning 页面原文：Japanese, English, Indonesian, Ukrainian, Uzbek, Korean, Khmer, Spanish, Thai, Simplified Chinese, Traditional Chinese, Nepali, Filipino, Hindi, French, Vietnamese, Bengali, Portuguese, Burmese, Mongolian, Lao, Russian（附 "Editions in other languages will be successively released."）。
- **下载/访问方法**：网站公开免费下载；PDF 入口 `/en/starter/pdf.html`、`/en/elementary01/pdf.html`、`/en/elementary02/pdf.html`、`/en/pre-intermediate/pdf.html`；MP3 以 ZIP 压缩包下载（FAQ Q29），亦可浏览器流式播放；带音频 PDF 须下载到 PC 用 Adobe Acrobat Reader 打开（Q31）；无 API；另有外部在线课程 `https://www.irodori-online.jpf.go.jp` 与 iOS/Android "IRODORI Practice" App。
- **更新情况**：首页有 `News / updates`（`/en/news.html`）入口但**无最后更新日期/版本号**；版权行 "Copyright© The Japan Foundation Japanese-Language Institute, Urawa, All Rights Reserved" 无年份；FAQ Q6 "There are no plans to produce any Irodori textbooks for B1 level."、Q7 "At present, there are no plans to sell Irodori in print format."
- **许可证与可使用范围**：**非 CC**，为站点自定义 Terms of Use（详见 2.3）。仅限私用或学校/教育机构使用；禁止商用；衍生教材须免费并注明来源；禁止用于与 Irodori 完全无关的新教材；插图不得改作。
- **在本项目中的作用**：初级（N4–N3 前期）核心教材来源，提供完整会话/听读文本、词汇、语法、汉字与 Can-do 目标，适合构建分级语料与课程大纲；免费可下载、对教育用途相对宽松。
- **数据质量风险**：① 非 CC 且禁止商用/再分发牟利，公开发布或商用需另获授权；② 衍生教材必须免费并注明来源；③ 插图不得改作；④ 官方 FAQ 明确 Irodori 不是为 JLPT 设计、仅对应 N4，对 N3 覆盖不足；⑤ 无更新日期/版本记录，需固定快照；⑥ 带音频 PDF 依赖 Adobe Acrobat Reader，浏览器/移动端不可播放。
- **访问记录**：2026-11-06，`WebFetch` 成功返回页面内容（工具未暴露 HTTP 状态码）。为核实许可证与下载方式，额外真实访问 `https://www.irodori.jpf.go.jp/en/privacy.html`、`https://www.irodori.jpf.go.jp/en/faq.html`（均成功）。仅核验公开页面元信息。
- **Evidence**：标题 `TOP | IRODORI Japanese for Life in Japan`；`## Please click on a book below` + `[Starter](/en/starter/pdf.html)`、`[Elementary 1](/en/elementary01/pdf.html)`、`[Elementary 2](/en/elementary02/pdf.html)`、`[Pre-Intermediate](/en/pre-intermediate/pdf.html)`；`Starter Digital audio files（MP3）`；`[Lesson 1 (MP3 playback)](/en/starter/audio/lesson01.html)`；`Copyright© The Japan Foundation Japanese-Language Institute, Urawa, All Rights Reserved`；`JP EN` / `Editions in other languages` / `To Edition in Ukrainian 'Starter'`。补充页标题 `About this site | IRODORI   Japanese for Life in Japan`（含 `# About this site`、`Terms of Use`、`Copyright and usage guidelines` 四条）、`FAQ | IRODORI   Japanese for Life in Japan`（Q22/Q24/Q25/Q26/Q27/Q28/Q29/Q31）。

---

### 2. Marugoto e-Learning
- **URL**：https://marugoto.jpf.go.jp/en/e-learning/
- **category**：official_material
- **fetch_status**：OK
- **内容类型与覆盖范围**：资源目录页，汇总「Online courses / Support sites / Japanese language learning sites / Apps」的链接与说明；含 `_Marugoto_ Japanese online course`（Minato 上的自助课与教师辅导课）、`MARUGOTO +`、`MARUGOTO Words`、`Irodori`、Hikidasu、Erin、Hirogaru、Japanese in Anime and Manga、HIRAGANA/KATAKANA Memory Hint、KANJI Memory Hint 1/2/3，以及 `Download Materials` 导航（Starter(A1)~Intermediate 2(B1) 的 Katsudoo/Rikai）。级别标记 A1 / A2 / A2/B1 / B1；**未见 B2/C1/C2，未见 CEFR/JLPT 字样**。
- **可用语言**：按资源分别列出（Japanese, English, Spanish, Chinese, Indonesian, Thai, Vietnamese, French, Portuguese 等，且 MARUGOTO+ 注明 "Spanish (Starter(A1) only)"、"Indonesian (part of Elementary 1 (A2) only)"）；导航仅见 `[日本語](/)` 站点语言入口；无统一站点级语言表。
- **下载/访问方法**：外链到各服务；`Download Materials` 内部页 `https://marugoto.jpf.go.jp/en/download/`；在线课程走 Minato；App 仅 App Store / Google Play 商店链接；**未见 API、无直接 .apk/.ipa、主页面未写 free（Irodori 说明除外）**。
- **更新情况**：版权行 `Copyright© 2017 The Japan Foundation Japanese-Language Institute, Urawa, All Rights Reserved.`（2017 为版权年份，非更新日期）；无 Last updated / 版本号 / changelog；唯一面向未来的状态是 Irodori 语言版 "Editions in other languages will be successively released."
- **许可证与可使用范围**：**非 CC**。主页面仅有 `[Copyright Policy](/en/copyright/)` 链接与 `All Rights Reserved`；额外真实访问 `https://marugoto.jpf.go.jp/en/copyright/`（标题 `Copyright Policy | Marugoto`）核实：教材须师生各自购买；课堂投影限注册学员、不得录屏；下载音频**仅限使用 Marugoto 的课堂/培训、不得单独使用、不得编辑、不得分发**（含云盘/学校服务器）；补充材料与教师资源可**免费分发给学员**（商用/非商用教学均可），但不得公开到网站/SNS/云盘；自制教材须免费分发、不得销售、不得公开；自学习可复制编辑但不得分发或公开；**禁止翻译并出版/销售**；"Yes. This policy also applies outside Japan."
- **在本项目中的作用**：JF 系教材体系与 CEFR/JF Can-do 分级参照、配套资源索引（MARUGOTO+、Words、Memory Hint Apps、Irodori/Erin/Hirogaru 等入口），用于确定分级框架与资源地图；不作为可直接再分发的正文语料。
- **数据质量风险**：① 教材本体为付费出版物，版权政策明确禁止扫描/复印全书、禁止公开分发音频与补充材料，语料再分发风险高；② 无更新日期/版本，版权年份停留在 2017；③ 该页是链接目录，实际内容散落在多个外部站点，链接可能失效；④ 无 API、无结构化数据下载；⑤ 语言/字幕按资源不同且有 "only" 限制，需逐个确认。
- **访问记录**：2026-11-06，`WebFetch` 成功返回（工具未暴露 HTTP 状态码）；额外访问 `/en/copyright/` 成功。仅核验公开页面元信息。
- **Evidence**：标题 `Marugoto e-Learning | Marugoto`；H1 `# _Marugoto_ e-Learning`；`## Website` / `## Apps`；`"This is ”_Marugoto_” as an online course in JF Japanese e-Learning ”_Minato_”. … The courses are from Starter A1 to Pre-Intermediate (A2/B1)."`；`"You can download all the lesson materials in PDF format and as audio files free of charge on the "Irodori" website."`；`Copyright© 2017 The Japan Foundation Japanese-Language Institute, Urawa, All Rights Reserved.`；`[Download Materials](/en/download/)` 及 `Starter (A1) _Katsudoo_` 等级别子项；`[Copyright Policy](/en/copyright/)`。补充页 `Copyright Policy | Marugoto` 含 `"This page explains how *Marugoto* coursebooks and materials on the Marugoto website (Audio files, Supplementary Materials, Resources for Teachers, etc.) may be used."`、`"Please do not distribute the downloaded audio files to anyone, including participants."`、`"Please do not photocopy all or part of a *Marugoto* coursebook and distribute it to participants."`、`"No. Please do not translate and publish, share, or sell the translation of *Marugoto* coursebooks without permission."`、`"Yes. This policy also applies outside Japan."`

---

### 3. JF Japanese e-Learning Minato
- **URL**：https://minato-jf.jp/
- **category**：official_material
- **fetch_status**：OK
- **内容类型与覆盖范围**：JF 官方在线日语学习平台的**课程目录页**：`Self-Study Course(95) Tutor Support Course(6) Course for Teachers(17)`，课程卡片标注 `Free` 与 `Applications Open`；课程详情走 `/CourseDetail/Index/…`。级别覆盖 A1 / A2 / A2 - B1 / B1 / B1 - B2（由卡片标签所见）。
- **可用语言**：课程卡片所见授课/界面语言包括 English, Español, Bahasa Indonesia, ภาษาไทย, 中文, Tiếng Việt, Français, Português, Deutsch, Italiano, Magyar, 日本語。
- **下载/访问方法**：网站公开课程目录；需注册/申请（"Applications Open"）；大量课程标 `Free`；**所访问页面未见 PDF/音频直接下载入口，未见 API**。
- **更新情况**：课程编号含 `KC26_` / `MC26_` / `CO26_` / `RO26_` / `MD26_` / `BP26_` / `SP26_` / `JA26_` / `BA26_` 等 2026 年度批次，且显示 `Applications Open`，说明为在招课程；页面**未给出最后更新日期或版本号**。
- **许可证与可使用范围**：**所访问页面未见任何许可/版权/再利用条款文本，未核实。** 同批核验的 Marugoto Copyright Policy 页指出在线课程另适用 "Terms of Use for JF Japanese e-Learning Minato"（链接 `https://www.jpf.go.jp/j/kansai/clip/minato/`），该条款正文本次未访问，不作结论。页面可见信息仅为：注册后可参加标注 `Free` 的在线课程；内容下载、复制、再分发、改作、商用授权均未核实。
- **在本项目中的作用**：作为官方免费课程的课程结构、级别标签、多语言覆盖的参考与选课入口，可用于对照 CEFR A1–B2 分级；不宜作为可批量抓取的语料来源。
- **数据质量风险**：① 许可与再利用条款未核实，贸然收录内容有版权风险；② 需注册/申请，内容不在公开页面，无法直接抓取；③ 课程为动态排期（Applications Open / 年度批次），会滚动失效；④ 页面为课程列表，无教材正文、无 API、无结构化下载；⑤ 级别/语言由卡片标签读取，需逐课程确认。
- **访问记录**：2026-11-06，`WebFetch` 成功返回课程列表页（工具未暴露 HTTP 状态码）。未注册、未抓取课程内容。
- **Evidence**：标题 `JF Japanese e-Learning Minato |The Japan Foundation`；`# Japanese Course`；`## Learn Japanese anytime, anywhere.`；`Self-Study Course(95) Tutor Support Course(6) Course for Teachers(17)`；卡片 `A1 English / Free / Applications Open` → `https://minato-jf.jp/CourseDetail/Index/KC26_MGKS_A101_EN02`、`A2 - B1 English`、`B1 - B2 日本語`、`A1 Français`、`A1 Deutsch`、`A1 Italiano`、`A1 Magyar`、`A1 Português`、`A1 Tiếng Việt` 等。

---

### 4. NHK WORLD / Easy Japanese（简明日语）
- **URL**：https://www.nhk.or.jp/lesson/
- **category**：official_material
- **fetch_status**：**PARTIAL**
- **内容类型与覆盖范围**：免费音频＋文本课程《Easy Japanese / 简明日语》，共 **48 课**；含会话短剧(Skits)、基本句型(Key Phrases)、练习(Exercises)、词汇(Vocabulary)、文化(Culture)、五十音、Q&A、My Haru-san 学习记录；官方说明含 "audio, animated video, and text"；另有 "Easy Japanese Grammar lessons" 语法课程与下载页。面向零基础/初级。多语言本地化版本。
- **可用语言**：主 URL 首页直接显示 Vietnamese（Tiếng Việt）、Indonesian（Bahasa Indonesia）、Korean（코리언）链接；额外真实访问了 English（`/lesson/en`）与 Vietnamese（`/vi/`）版本；WebSearch 返回官方中文简体版 `https://www3.nhk.or.jp/lesson/chinese/download/index.html`、中文繁体版 `…/nhkworld/lesson/zt/…`、孟加拉语版等入口（**未逐一访问，故未写入结论**）。
- **下载/访问方法**：网站公开免费；**MP3 与 PDF 免费下载，但明确 "for personal use only"**；官方英文下载页 `https://www.nhk.or.jp/lesson/english/download` 列出 `Complete edition of the textbook (all 48 lessons) PDF (6MB)`、逐课 `MP3 (4.6MB)` + `PDF (1MB)`、每 5 课合集 `MP3 (21MB)` / `PDF (4MB)`；英文版下载入口 `https://www3.nhk.or.jp/nhkworld/lesson/en/segment/downloads/`；无 API。
- **更新情况**：所访问页面**未给出最后更新日期/版本号/更新日志**；内容形态为固定的 48 课；站点仍在线并提供下载页。
- **许可证与可使用范围**：页面原文明确限定 **"(for personal use only)"（仅限个人使用）**，越南语版原文 `chỉ sử dụng cho mục đích cá nhân`；**未在所访问页面看到 Creative Commons 或其他开放许可、再分发/改作/商用授权，未核实**。属 NHK 版权内容，非开放许可。仅限个人学习使用，不得据此推定允许再分发、公开镜像、改作或商用。
- **在本项目中的作用**：初级 48 课的完整会话脚本＋音频＋文字教材，是分级对话语料与听力素材的优质公开参考；但因 "personal use only" 限制，只适合作为对齐/参考，不宜整段再分发或作为可发布语料。
- **数据质量风险**：① 明确 "for personal use only"，再分发/商用风险高；② 目标 URL 本身 `WebFetch` 仅返回标题与零散语言链接（疑似重定向/JS 渲染），主体信息需经官方子页面补全；③ 多语言版本为独立站点、内容不完全一致，需按版本分别处理；④ 无 API、无结构化数据，下载页为逐课文件列表；⑤ 无更新日期，需固定快照。
- **访问记录**：2026-11-06，主 URL `WebFetch` **两次**均返回标题但仅含极少量片段（工具未暴露 HTTP 状态码），主体内容未完整返回 → **无法访问完整页面，相关项未核实的部分不补写猜测**。为补全元信息，另真实访问 `https://www.nhk.or.jp/lesson/en`、`https://www.nhk.or.jp/lesson/english/download`、`https://www3.nhk.or.jp/nhkworld/lesson/vi/`（均成功；URL 来自页面内链接及 WebSearch 返回的官方地址），并用 WebSearch 检索官方入口。仅核验公开页面元信息，未下载任何 MP3/PDF。
- **Evidence**：主 URL 标题 `Easy Japanese, free audio & text lessons | NHK WORLD RADIO JAPAN`；片段 `Master basic grammar! Also－words that sound like what they describe.`；`[Tiếng ViệtVietnamese](https://www3.nhk.or.jp/nhkworld/lesson/vi/)`、`[Bahasa IndonesiaIndonesian](…/indonesian/)`、`[코리언Korean](…/korean/)`。补充页 `https://www.nhk.or.jp/lesson/en` 标题 `Easy Japanese Learn Japanese | NHK WORLD-JAPAN`：`"MP3 audio files of the lessons and PDF files of the textbook can be downloaded free of charge (for personal use only)."`、`"Click here to access all 48 lessons and learn the basics of Japanese conversation."`、`"The website--with audio, animated video, and text--helps you learn the basics of Japanese. It offers 48 lessons."`；下载页标题 `Easy Japanese Grammar lessons - Download Lessons | NHK WORLD RADIO JAPAN`：`"Complete edition of the textbook (all 48 lessons) PDF (6MB)"`、`Lesson 1 I'm Anna. MP3 (4.6MB) PDF (1MB)` … `Lesson 48 Thank you very much for everything.`、`"Download from Lesson 1 to Lesson 5 all at once MP3 (21MB)" / "PDF (4MB)"`；越南语版 `/vi/` 标题 `Cùng nhau học tiếng Nhật Học tiếng Nhật miễn phí | NHK WORLD-JAPAN`：`"Bạn có thể tải về miễn phí tệp MP3 âm thanh bài học và tệp PDF giáo trình (chỉ sử dụng cho mục đích cá nhân)."`、`"Có 48 bài."`

---

### 5. Erin's Challenge! I can speak Japanese. Contents Library
- **URL**：https://erin.jpf.go.jp/
- **category**：official_material
- **fetch_status**：**FAIL**
- **内容类型与覆盖范围**：**未核实**（目标 URL 无法访问，按规则留空，不补写猜测内容）
- **可用语言**：[]（未核实）
- **下载/访问方法**：（未核实）
- **更新情况**：（未核实）
- **许可证与可使用范围**：（未核实）
- **在本项目中的作用**：目标 URL 未核实，暂不纳入；如需 Erin 相关元信息，应另行核验 `https://www.erin.jpf.go.jp/` 及其条款页后再评估。
- **数据质量风险**：目标 URL 连续两次 `fetch failed`，**无法访问，未核实**；备用 www 别名虽可访问，但其内容、许可、下载方式均未在本次任务中系统核验；若把备用站点内容当作本 URL 的核实结果会造成审计错误。
- **访问记录 / 工具返回**：2026-11-06，目标 URL `WebFetch` 两次均返回 `Error: Error during web fetch for https://erin.jpf.go.jp/: fetch failed`（无 HTTP 响应/状态码）。
- **Evidence**：仅工具错误文本 `'Error: Error during web fetch for https://erin.jpf.go.jp/: fetch failed'`（两次）。**补充旁证（来源已标注，仅作参考，不代表目标 URL 已核实）**：同站官方别名 `https://www.erin.jpf.go.jp/` 于 2026-11-06 `WebFetch` 成功，标题 `エリンが挑戦！にほんごできます。コンテンツライブラリー | 国際交流基金`，页面列出 `第1課 はじめてのあいさつ- 教室 -` 至 `第25課 気持ちをつたえる- 別れ -` 共 25 课目录；该别名 URL 出现在同批核验的 `https://marugoto.jpf.go.jp/en/e-learning/` 页面原文中（`https://www.erin.jpf.go.jp/`）。
- **Notes**：**无法访问，未核实。** 按规则本条 `fetch_status` 为 FAIL，所有内容字段留空，未补写任何猜测内容。

---

### 6. Tadoku — Our Graded Readers / Free Tadoku Books
- **URL**：https://tadoku.org/japanese/en/graded-readers-en/
- **category**：official_material
- **fetch_status**：OK
- **内容类型与覆盖范围**：免费分级读物（Web Tadoku Books ＊FREE）PDF＋在线阅读＋朗读音频；页面同时介绍 5 个系列（Japanese Graded Readers / Taishukan Japanese Readers / Nihongo Tadoku Books / Nihongo Tadoku Books app / Web Tadoku Books FREE）的纸质/电子/音频购买信息；另有 `other-grs` 其他免费读物目录。级别 0–5（NPO 自有分级），带振假名、插图、按级别控制词汇语法、配 CD 或 mp3 朗读；免费书由 NPO多言語多読 会员制作，另有学习者/教师/日语学校创作的免费读物。
- **可用语言**：Japanese（读物正文）、English（本页为英文版，站点有 JP/EN 切换）。
- **下载/访问方法**：网站公开免费；Web Tadoku Books 的 PDF 免费公开，可在线浏览器阅读、下载到终端、打印/制本；付费系列经出版社/书店/电子书店/App 购买；音频可 mp3 下载（`audio-downloads`）；无 API。
- **更新情况**：页面列出近期活动日期 `2026-11-07 (Sat)`（Online Japanese Tadoku Club）、`2026-11-29 (Sun)`（読みもの作成入門講座）、`2027-01-10 (Sun)`（日本語多読授業入門講座）、`2026/9/27 (日)` 及 `毎年8月` / `毎年12月`，并有 `https://tadoku.org/news/2026/08/27/22901` 新闻链接，说明站点近期活跃；但页面**未给出教材本身的最后更新日期/版本号**。
- **许可证与可使用范围**：**CC BY-NC-ND 4.0**（详见 2.4，来自官方条款页 `https://tadoku.org/japanese/en/free-books-en/note-en` 原文）。需署名 `NPO多言語多読`；可免费下载/打印/制本、可分享链接、可在大学/日语学校课堂及个人学习支持中使用（官方明确含商业性教学活动，建议捐赠）；**禁止任何改作/加注/翻译/出声朗读后公开发布，禁止商业转售**。付费系列不在免费范围。第三方免费读物可能各有独立条款，本页未逐站核实。
- **在本项目中的作用**：唯一有明确开放许可的分级阅读语料来源（Level 0–5），大量易读文本＋朗读音频，可合法用于教学，适合构建分级阅读与听读配对素材。
- **数据质量风险**：① ND 条款禁止改作（不得加翻译/注释/试题、不得制作朗读视频公开发布），若需改写、切分、加注音或生成衍生语料会受限；② 禁止商业转售；③ 需署名；④ 免费读物由会员/学习者/教师创作，质量与分级一致性参差；⑤ 付费系列（纸质/电子/App）须与免费 PDF 区分；⑥ 无教材版本/更新日期；⑦ 部分外部免费读物托管在 Jimdo/Padlet/Notion/Wix 等第三方，链接稳定性差。
- **访问记录**：2026-11-06，主 URL `WebFetch` 成功返回（工具未暴露 HTTP 状态码）。为核实免费 PDF 许可范围，用 WebSearch 定位到官方条款页并真实访问 `https://tadoku.org/japanese/en/free-books-en/note-en`；另访问 `https://tadoku.org/japanese/other-grs/`、`https://tadoku.org/japanese/en/other-grs-en/`（均成功）。仅核验公开页面元信息，未下载任何 PDF。
- **Evidence**：标题 `Our Graded Readers - にほんごたどく`；`"Audio recording will make listen-while-you-read even more of fun."`；`"All come with audio recording as CD or mp3 download."`；`"Web Tadoku Books ＊FREE — Members of NPO Tadoku Supporters created these free readers to increase the number of books for tadoku and promote tadoku. Available online with a web browser and/or download and print into book formats."`；`- Publisher: NPO Tadoku Supporters / Price: FREE`；`[To All books](https://tadoku.org/japanese/book-search/?series=050)`；日文表格逐字 `"Web Tadoku Books【無料】（NPO多言語多読）… PDFデータを無料公開しています。端末にダウンロードしたり、印刷・製本してご利用いただけます。サイト上で読むこともできます。 なし"`；活动 `2026-11-07 (Sat)`、`2026-11-29 (Sun)`、`2027-01-10 (Sun)`。补充页标题 `Guide to Using Our Free Tadoku Books - にほんごたどく`：`"use the books according to the ‘CC BY-NC-ND 4.0’ license."`、`"Absolutely yes! When sharing, please make sure to give credit to ‘NPO多言語多読’."`、`"Sure! Feel free to use them (even in commercial activities) only if they are used for tadoku in university or Japanese language school classes, or for personal learning support. Just remember not to make any changes."`、`"No. You may not publish them after making any changes."`、`"Please don't make any changes or add anything."`、`"No, commercial resale is not allowed."`；另 `/japanese/other-grs/` 标题 `その他のレベル別読みもの - にほんごたどく`（凡例 `無料 …無料の読みもの`）、`/japanese/en/other-grs-en/` 标题 `Other Graded Readers - にほんごたどく`（`Free – Free to read`）。

---

### 7. JLPT — For Examinees: Let's Try Sample Questions!
- **URL**：https://www.jlpt.jp/e/samples/forlearners.html
- **category**：official_material
- **fetch_status**：OK
- **内容类型与覆盖范围**：官方样题入口/说明页：N1–N5 全级别，"One sample question is offered for each test item type"；指向 `sample09.html`（2009 年 "New Japanese-Language Proficiency Test Sample Questions"，可下载 PDF/MP3）与 `sampleindex.html`（"Japanese-Language Proficiency Test Official Practice Workbook"，2012 / 2018 Vol.2，Bonjinsha 销售）。**N3 题型与可下载 PDF 详见 2.1**。
- **可用语言**：English（页面为 `/e/` 英文版）；样题 PDF 为日语内容（`sample09.html` 对部分 PDF 标注 "(In Japanese)"）。
- **下载/访问方法**：网站公开免费；`forlearners.html` 本身只给说明与链接；实际可下载资源在 `https://www.jlpt.jp/e/samples/sample09.html`：N1–N5 各自试题 PDF、答题纸 PDF、听解脚本 PDF、答案 PDF、听解 MP3；PDF 需 Acrobat Reader，非日语环境需 Asian Font Packs；无 API。N3 直链：`https://www.jlpt.jp/e/samples/pdf/N3-mondai.pdf`、`N3-kaitou.pdf`、`N3-script.pdf`、`N3-seikai.pdf`、`https://www.jlpt.jp/e/samples/mp3/N3Sample.mp3`。
- **更新情况**：`forlearners.html` 无最后更新日期；所指向的 `sample09.html` 明确 "(published 2009)"、为 2010 改版前样题，并附 `List of changes in directions (PDF/103KB)` 提示部分指导语此后有变更；`sampleindex.html` 提到 2012 与 2018 两版官方练习册。另同批核验的 `guideline/testsections.html` 显示 `2026 JLPT dates: 1st test Sunday, July 5 / 2nd test Sunday, December 6`，说明站点当前维护。**免费样题本身为旧版，需注明**。
- **许可证与可使用范围**：**所访问页面未见任何许可/版权/再利用条款文本，未核实。** 样题由 JLPT 官方公开发布供考生练习，页面说明用途为 "show the form of test items"，并注明 "There may be differences from questions in the actual test booklet."；再分发/改作/商用授权未核实。
- **在本项目中的作用**：N3 题型与官方样题的权威依据，用于确定题库的题型分类、难度锚点与评测标准；不宜直接再分发原题。
- **数据质量风险**：① 样题为 2009 年改版前编制，题量/指导语与现行考试有差异，不能当作现行真题；② 官方练习册为 Bonjinsha 付费出版物，免费部分仅样题；③ 未见许可条款，再分发/商用未核实；④ `sample_kousei.pdf` 与 `N3-mondai.pdf` 为 `application/pdf`，`WebFetch` 返回 "non-text resource"，无法解析，本次仅经 `curl -I` 确认 HTTP 200 与 Content-Type，**未读取题目正文**（按规则不批量抓取受限版权教材）；⑤ 无 API、无结构化数据。
- **访问记录**：2026-11-06，主 URL `WebFetch` 成功返回（工具未暴露 HTTP 状态码）；额外真实访问 `https://www.jlpt.jp/e/samples/sample09.html`、`https://www.jlpt.jp/e/samples/sampleindex.html`、`https://www.jlpt.jp/e/guideline/testsections.html`（均成功）；对 N3 PDF/MP3 用 `curl -I` 实测：`N3-mondai.pdf → 200 application/pdf`、`sample_kousei.pdf → 200 application/pdf`、`N3Sample.mp3 → 200 audio/mpeg`、`n3_e.pdf → 200 application/pdf`。仅做公开页面元信息核验。
- **Evidence**：标题 `For Examinees: Let's Try Sample Questions! | JLPT  Japanese-Language Proficiency Test`；`## JLPT sample questions`；`"Sample questions show the form of test items on the JLPT. Sample questions are organized by level, from N1 to N5. One sample question is offered for each test item type. There may be differences from questions in the actual test booklet."`；`"For more practice, please refer to ["New Japanese-Language Proficiency Test Sample Questions"](https://www.jlpt.jp/e/samples/sample09.html) or ["Japanese-Language Proficiency Test Official Practice Workbook."](https://www.jlpt.jp/e/samples/sampleindex.html)"`。补充页 `sample09.html` 标题 `New Japanese-Language Proficiency Test Sample Questions | JLPT  Japanese-Language Proficiency Test`：`"This is a collection of sample questions published prior to the 2010 revision to introduce revision details. It covers all forms of test item types for all levels (the number of questions is different from the number of test items in an actual test). In the Listening section, one sample question with an audio file is offered for each test item type."`，逐条列出 `Test question samples(PDF) N3 (https://www.jlpt.jp/e/samples/pdf/N3-mondai.pdf) (3.1MB)`、`Listening question audio sample(MP3) N3 N3Sample.mp3 (11.0MB)`、`Answer sheet (PDF) N3 N3-kaitou.pdf (370KB)`、`Listening question script(PDF) N3 N3-script.pdf (1.33MB)`、`Answers(PDF) N3 N3-seikai.pdf (38.8KB)`、`Composition of test items(PDF) sample_kousei.pdf (2.94MB)`、`List of changes in directions (PDF/103KB)`。`sampleindex.html` 标题 `Japanese-Language Proficiency Test Official Practice Workbook | JLPT …`：`"The Official Practice Workbook published in 2012 and the Official Practice Workbook Vol.2 released in 2018 … are sold by Bonjinsha."`。`testsections.html` 标题 `Composition of Test Sections and Items | JLPT …`：`"2026 JLPT dates"`、`N3 Language Knowledge(Vocabulary)〈30min〉 Language Knowledge(Grammar)・Reading〈70min〉 Listening〈40min〉`、题型构成表（详见 2.1）。

---

### 8. JLPT — N1-N5: Summary of Linguistic Competence Required for Each Level
- **URL**：https://www.jlpt.jp/e/about/levelsummary.html
- **category**：official_material
- **fetch_status**：OK
- **内容类型与覆盖范围**：官方能力标准说明页，N1–N5 五级，每级按 Reading / Listening 列出能力描述（配 `levelsummary_read.gif` / `levelsummary_listen.gif` 图标）；含总述（各级定位、N3 为 bridging level、语言知识另属必需）。**N3 原文要点详见 2.2**。
- **可用语言**：English（页面为 `/e/` 英文版；JLPT 站点另有日文版，本次未核验）。
- **下载/访问方法**：网站公开免费 HTML 页面；无下载、无 API；页面内含 gif 图标与指向 `https://www.jlpt.jp/e/application/overseas_list.html` 的考试日程链接。
- **更新情况**：页面**未给出最后更新日期或版本号**；含页脚 `"＊Outside Japan, the test may be held only in July or December in some cities."`；同批核验的 `testsections.html` 含 2026 年考试日期，说明站点当前维护。
- **许可证与可使用范围**：**所访问页面未见任何许可/版权/再利用条款文本，未核实。** 属官方公开发布的能力标准说明，供了解各级要求；引用需注明出处。
- **在本项目中的作用**：N3 能力目标与难度锚点的权威定义，可直接作为分级目标、评测维度（Reading/Listening）与课程大纲设计依据；原文要点可短句引用。
- **数据质量风险**：① 仅给能力描述，不提供词汇表/语法表/汉字表或题量，需另找资料；② 页面明确 "While not noted in the table, Language Knowledge, such as Vocabulary and Grammar, is also required"，表格不覆盖语言知识，不能当作完整考纲；③ 未见许可条款，引用需注明出处；④ 无更新日期/版本号，需固定快照；⑤ 为英文版，日文原版表述可能略有差异，本次未核验。
- **访问记录**：2026-11-06，`WebFetch` 成功返回完整页面（工具未暴露 HTTP 状态码）。仅核验公开页面元信息。
- **Evidence**：标题 `N1-N5: Summary of Linguistic Competence Required for Each Level | JLPT  Japanese-Language Proficiency Test`；`"The JLPT has five levels: N1, N2, N3, N4 and N5. The easiest level is N5 and the most difficult level is N1."`；`"N4 and N5 measure the level of understanding of basic Japanese mainly learned in class. N1and N2 measure the level of understanding of Japanese used in a broad range of scenes in actual everyday life. N3 is a bridging level between N1/N2 and N4/N5."`；`"While not noted in the table, Language Knowledge, such as Vocabulary and Grammar, is also required for successful execution of these activities."`；N3：`"The ability to understand Japanese used in everyday situations to a certain degree."`；Reading：`"One is able to read and understand written materials with specific contents concerning everyday topics."`、`"One is also able to grasp summary information such as newspaper headlines."`、`"In addition, one is also able to read slightly difficult writings encountered in everyday situations and understand the main points of the content if some alternative phrases are available to aid one's understanding."`；Listening：`"One is able to listen and comprehend coherent conversations in everyday situations, spoken at near-natural speed, and is generally able to follow their contents as well as grasp the relationships among the people involved."`

---

## 四、对本项目最可用的 3 个来源

1. **IRODORI（https://www.irodori.jpf.go.jp/en/）** —— 免费可下载的完整 PDF 教材＋MP3 音频，体系最完整（4 级 ×18 课、644 汉字、360–500 学时、Can-do 目标、词表/答案/语法练习/插图齐全），可作为课程大纲与初级语料的主体。许可为自定义 Terms of Use，明确允许私用与学校/教育机构使用、允许自制教材与课堂分发（须免费并注明来源、禁止商用），对教育类项目相对友好；需注意其官方自述只对应 JLPT N4，N3 部分需补充。
2. **Tadoku Free Tadoku Books（https://tadoku.org/japanese/en/graded-readers-en/）** —— 本批 8 个来源中**唯一有明确开放许可（CC BY-NC-ND 4.0）**的语料库，许可条款单独成页、边界清晰；Level 0–5 大量免费 PDF＋朗读音频，可合法下载/打印/课堂使用（官方明确含商业性教学活动）。适合作为分级阅读与听读配对语料；主要限制是 ND 禁止改作与商业转售，需署名。
3. **JLPT 官方站（levelsummary.html + samples/forlearners.html 及 sample09/testsections）** —— 唯一能给出项目所需「N3 权威标准」的来源：levelsummary 提供 N3 能力描述原文（bridging level、Reading/Listening 要点），samples 链提供 N3 官方样题 PDF/MP3 与完整题型构成表。作为分级目标与评测锚点不可替代。相较 NHK（明确 "personal use only"）、Marugoto（付费教材、禁止扫描与公开分发）、Minato（注册制、条款未核实）、Erin（未核实），其公开性与作为「标准」的低再利用风险最优；但页面未见许可条款，只宜作标准参照与短句引用，不宜再分发原题。

---

## 五、审计说明与限制

- 所有 `fetch_status=OK` / `PARTIAL` 的条目，evidence 均为 2026-11-06 当次 `WebFetch` 实际返回的页面标题或原文片段；`WebFetch` 工具本身**不暴露 HTTP 状态码**，故 `http_status` 字段如实记录工具返回，未臆造 "200"。唯一显式 HTTP 状态码来自 `curl -I` 对 4 个 JLPT PDF/MP3 的实测（均为 200），已单独标注。
- 为完成 4 个「特别核实项」，额外真实访问了官方子页面（Irodori privacy/faq、Marugoto copyright、JLPT sample09/sampleindex/testsections、NHK /lesson/en 及下载页、Tadoku note-en/other-grs 等）。这些补充访问均在对应条目的 notes / evidence 中逐一标明 URL，**不与目标 URL 的核实结果混淆**。
- 目标 URL `https://www.nhk.or.jp/lesson/` 两次仅返回极少量片段 → `PARTIAL`；目标 URL `https://erin.jpf.go.jp/` 两次 `fetch failed` → `FAIL`，**无法访问，未核实**，内容字段留空，未补写猜测内容。
- 全程仅做公开页面元信息核验：`WebFetch` 对 2 个 PDF 返回 "non-text resource (application/pdf)" 后**未重试、未下载正文**；`curl -I` 仅取响应头。未批量抓取任何受限版权教材。
- 许可结论均基于页面原文：Irodori 为自定义 Terms of Use（**非 CC BY-NC**）、Marugoto 为 Copyright Policy（**非 CC**、禁止再分发音频/扫描件）、NHK 为 "personal use only"、Tadoku 为 **CC BY-NC-ND 4.0**、Minato/两个 JLPT 页面未见许可条款（未核实）。未按印象套用许可类型。
- 机器可读版见同目录 `sources_official.json`（8 个对象，字段严格固定）。
