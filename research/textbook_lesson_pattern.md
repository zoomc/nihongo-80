# 日语教材「一课」是怎么教会人的 · Nihongo 80 内容规格与 Day 1 示范课

- **子任务**：教材学习思路总结
- **日期**：2026-11-06
- **唯一产物**：本文件 `/Users/mj/Documents/learn/jp/nihongo-80/research/textbook_lesson_pattern.md`
- **读者**：网页改造者。学员画像：中文母语、有韩语背景、**日语零基础**，每天 60 分钟、80 天冲 N3。
- **触发原话**（见 [P3]）：「网页版啥玩意儿啊，太抽象了，我都看不懂……单词、语法、例句、发音、适当的难点讲解、记忆曲线科学复习、练习，至少得覆盖这些吧，可以适当对照下韩语类似语法」。
- **立场**：全部结论真实查证，每条给「出处 URL + 实际看到的原文片段/模块名」；访问不到就写「未核实」，**绝不编造课名、页码、模块名、音调数字**；不写空泛教育学理论，全部落到「一页上有哪些文字、按什么顺序、每个词给哪些字段」。
- **边界**：只写这一个 md；**未修改**任何脚本、HTML、JSON、课程、种子或其他文档（见 §8）。

---

## 0. 一页结论（给赶时间的人）

1. **教材的一课不是「词表 + 语法表」，是一条有坡度的动作链**：先告诉你今天要能做什么（Can-do），给你要用的词，让你先听示范对话，再自己发现语法规律，然后跟读 → 换词 → 自由说，最后做练习和自评。Irodori 官方把每个活动的步骤写成 `➊Can-do objective → ➋Preparation for the words → ➌Listen to the example dialogs → ➍Focus on the form → ➎Speaking → ➏Can-do check`（[S5]），Genki 官方写的是 `会話 Dialogue → 単語 Vocabulary → 文法／表現ノート → 練習 Practice`（[S11]）。
2. **现有页面的问题不是「没内容」，是顺序和字段都不对**：首屏 100% 是系统元信息，可学内容 0%（[P3] §2.4）；单词卡只有「假名 + 中文义 + ID」，语法卡只有「含义 + 接续（日语术语）+ 1 条例句」，例句没有假名、没有中文，「文本读音」直接等于原文（[P3] §2.5）。改造要做的是**把教材那一页搬到学员眼前**，不是推倒重来。
3. **本项目不照抄教材课序**：教材把 Grammar Notes / Kanji Words / Word lists / Answer 放在课末或别册（[S5][S6][S4]），把汉字当「词的一部分」不单独教（[S3] Q15）；本项目面向零基础 + 60 分钟，必须把这些**提前、常显、加中文与假名、加韩语对照、加复习清单**。差别见 §2.4。
4. **韩语对照的总边界一句话**：**结构可以借，词不能猜**。SOV、助词后置、主题/主格分工、句末要变礼貌体，这些可以整句平移加速；具体选哪个助词、具体读音、具体词义、礼貌体层级，一律要验证（§4）。
5. **复习区不要写「FSRS 到期 12 项」**：要写「今天复习这 5 个词 → 遮住中文回忆 → 点开对答案 → 记住了/模糊/忘了 → 下次大约哪天再来」。页面只做展示与收集，**复习时间由 `scripts/learning.py` 算**（[P4]，§5）。

---

## 1. 核实记录：已核实 / 未核实

### 1.1 来源编号表（正文用 `[Sn]` / `[Pn]` 引用）

| 编号 | 类型 | URL / 文件 | 本轮是否真实访问 |
|---|---|---|---|
| [S1] | 官方页 | https://www.irodori.jpf.go.jp/en/starter/pdf.html | ✅ WebFetch 成功 |
| [S2] | 官方页 | https://www.irodori.jpf.go.jp/en/ | ✅ WebFetch 成功 |
| [S3] | 官方页 | https://www.irodori.jpf.go.jp/en/faq.html | ✅ WebFetch 成功 |
| [S4] | 官方页 | https://www.irodori.jpf.go.jp/en/resources.html | ✅ WebFetch 成功 |
| [S5] | 官方 PDF | https://www.irodori.jpf.go.jp/assets/data/starter/pdf/X_howto_en.pdf （How to Use This Textbook, English, 13 页） | ✅ `curl` 下载 2,539,799 字节 + PyMuPDF 提取 38,205 字符 |
| [S6] | 官方 PDF | https://www.irodori.jpf.go.jp/assets/data/starter/pdf/X_contents_en.pdf （Table of Contents, English, 6 页） | ✅ `curl` 下载 709,066 字节 + PyMuPDF 提取 14,595 字符 |
| [S7] | 官方页 | https://marugoto.jpf.go.jp/en/e-learning/ | ✅ WebFetch 成功 |
| [S8] | 官方页 | https://marugoto.jpf.go.jp/en/download/ | ✅ WebFetch 成功 |
| [S9] | 官方页 | https://www.jlpt.jp/e/about/levelsummary.html | ✅ WebFetch 成功 |
| [S10] | 官方页 | https://genki3.japantimes.co.jp/ （由 https://genki.japantimes.co.jp/en/ 重定向而来） | ✅ WebFetch 成功 |
| [S11] | 官方页 | https://genki3.japantimes.co.jp/intro/ （『げんき［第3版］』のご紹介） | ✅ WebFetch 成功 |
| [S12] | 官方页 | https://www.3anet.co.jp/mnn/ | ⚠️ 真实访问，返回 404 |
| [S13] | 官方页 | https://www.3anet.co.jp/ | ✅ WebFetch 成功，但无教材结构信息 |
| [P1] | 项目内已核实调研 | `research/source_registry_official.md`（2026-11-06） | ✅ 本轮阅读；其中 JLPT testsections 题型表本轮**未重新访问**，引用时按「项目内已核实」标注 |
| [P2] | 项目内框架 | `research/nh80_framework.md` | ✅ 本轮阅读 |
| [P3] | 项目内审计 | `research/ux_audit.md` | ✅ 本轮阅读 |
| [P4] | 项目内代码 | `scripts/learning.py` | ✅ 本轮阅读 |
| [P5] | 项目内数据 | `web/data/day-001.json` | ✅ 本轮阅读（对齐示范课） |

### 1.2 本轮「已核实」：逐条 URL + 实际看到的原文片段 / 模块名

**[S1] Irodori Starter PDF 下载页** —— 最重要的反直觉核实：
- 页面标题 `Starter | IRODORI Japanese for Life in Japan`；小节标题原文 `## Material Download and MP3 Play for each lesson`，并写 `You should download PDFs with audio files on your own PC and open them with Adobe Acrobat Reader.`
- **每课只有一个整册 PDF**，不是拆成「会話／単語／文法／練習」多个 PDF。实际看到的逐课条目：`### Topic Starting to Speak Japanese` → `#### Lesson 1 Good morning!` → `[PDF 12.7MB](.../X_L01.pdf)`、`[PDF with audio files 65MB](.../X_L01_au.pdf)`、`[MP3(ZIP) 10.9MB](.../X_audio_L01.zip)`、`[MP3 Play](.../lesson01.html)`；一路到 `#### Lesson 18 I want to go to a hot spring.`。另有 `#### Japanese in the classroom`（`X_kyoshitsu.pdf` / `X_L00_au.pdf`；`MP3 Play` 指向 `lesson00.html`，**页面本身未出现「Lesson 00」字样**）。
- 真实的 Topic / Lesson 名（逐字）：`Topic Starting to Speak Japanese` 下 `Lesson 1 Good morning!`、`Lesson 2 I'm sorry, I don't really understand.`；`Topic About Myself` 下 `Lesson 3 Nice to meet you.`、`Lesson 4 I live in Tokyo.`；`Topic My Favorite Foods` 下 `Lesson 5 I like udon.` … `Topic Holidays` 下 `Lesson 18 I want to go to a hot spring.`
- 全册共享 PDF（逐字）：`Cover`、`A message to the reader (in Japanese)` / `(in English)`、`How to Use This Textbook (in Japanese)` / `(in English)`、`Table of Contents (in Japanese)` / `(in English)`、`Can-do Check`、`Publication Information`；合订 `X_all.pdf (151MB)` 与 `X_audio_all.zip`。
- **结论**：任务提示里「看目录里一课有哪些 PDF：会話/単語/文法/練習等」在**该页并不成立**——该页没有这些独立 PDF 名。`会話 / 単語 / 文法 / 練習 作为独立下载 PDF：未在该页核实`（一课内部模块名另见 [S5][S6]，那是教材正文里的分区，不是下载页的文件名）。

**[S2] Irodori 首页**：`## Please click on a book below` + `Starter` / `Elementary 1` / `Elementary 2` / `Pre-Intermediate` 四个 `pdf.html` 链接；`Other Resources`、`How to teach Irodori`、`IRODORI Japanese Online Course (To another website)`；News 里有 `2026/10/29 Word list (Pre-Intermediate) has been released.`、`2026/11/06 Misprints in PDF files have been corrected.`。首页**没有**级别/学时/Can-do 的说明文字，说明在 FAQ 与「How to Use」里。

**[S3] Irodori FAQ**（全文可见，以下逐字引用与本任务相关的条目）：
- Q5：`Irodori covers learning up to the Pre-Intermediate (A2/B1), while Marugoto covers learning up to the intermediate level (B1).`
- Q11：`if you complete the "Starter" to "Elementary 2" levels of Irodori, you can be considered to have reached the N4 level of JLPT`；`Irodori is not a textbook designed to help students pass the JLPT`（Q12）。
- **Q13（一课的时间构成，极关键）**：`The suggested time for each lesson from "Starter" to "Elementary 2" takes about 150 minutes (2.5 hours) to 180 minutes (3 hours).` / `They do not include time for practicing the language knowledge needed for the activities, such as kanji, vocabulary, and grammar. Each lesson typically takes about 4 to 5 hours in total to complete (3 hours of Irodori activity time and about 1 to 2 hours of language knowledge practice).` → 官方把一课明确分成「**活动**」与「**语言知识（汉字/词汇/语法）练习**」两段。
- Q14：`Each part of "Starter," "Elementary 1," and "Elementary 2," typically takes about 80 to 100 hours` / `4 to 5 hours x 18 lessons = 72 to 90 hours` / `the entire course is estimated to take about 360 to 500 hours`。
- **Q15（汉字不孤立教，极关键）**：`In total of four books, you will learn 644 kanji characters` / `Kanji are not taught on their own. Instead, you will study them as words used in the activities in each lesson, and gradually learn and remember their meaning and pronunciation.`
- **Q16 / Q17（配套分册，极关键）**：`Q16.Are word lists and answers provided? A16.Yes. They come in separate booklets` → `Word lists` / `Answer`；`Q17.Are practice questions on grammar, vocabulary, expression, etc. provided? A17.Yes. For grammar exercises, "Grammar Worksheets" are available.` / `“IRODORI Practice” ... covers practice questions in four categories: words, kanji, grammar, and expressions.`
- Q20：`"How to use this textbook" section in the beginning of each book explains how to use Irodori to teach. If students are taught in the order of the textbook, they will be able to achieve the "Can-do" objectives`。
- Q18：`The "Sentence patterns list" ... compares the sentence patterns covered in Irodori and Marugoto.` 并提到越南 JF 中心做过与 `Minna No Nihongo` 的对照表（本轮未访问该表）。

**[S4] Irodori Other Resources 页**（配套分册真实模块名，逐字）：
- `## Compiled files of each section` → `Grammar Notes`、`Tips for life in Japan`、`Kanji Words`、`Hiragana Words and Katakana Words`。
- `## Word lists (Starter / Elementary 1 / Elementary 2 / Pre-Intermediate)` → 每级 `PDF` + `MP3(ZIP)` + `MP3 Play`，另有 `Excel file (Starter, Elementary1 and Elementary2)` / `wordlist_all.xlsx`。
- `## Answer` → 每级一个 `X_answer.pdf` / `Y_answer.pdf` / `Z_answer.pdf` / `ZZ_answer.pdf`。
- `## Grammar Worksheets` → 每级 `PDF` + `WORD` + **`WORD (without Furigana)`** + `MP3(ZIP)` + `MP3 Play`，另有 `How to Use Grammar Worksheets / Answer`。
  → **`Furigana`（振假名/注音）与「带/不带注音两版」是官方明文，本文件把它列为「例句必须给假名读音」的依据**（§3.5）。
- `Illustrations lists`、`Correspondence tables between Irodori Can-do and "JF Can-do for Life in Japan"`、`Sentence patterns list` / `Kanji list`、`Index of Tips for life in Japan`、`External resources`。

**[S5] Irodori 官方《How to Use This Textbook》PDF（本轮 curl + PyMuPDF 提取，逐字）**：
- 教材整体构成 `How this textbook is organized`：`Main book (PDF)` 下含 `A message to the reader`、`How to use this textbook`、`Cover`、`Table of Contents`、`Can-do Check`、`Audio files (MP3)`、`Lessons 1 to 18`；`Other resources*` 下含 `Answers`、`Teaching guides`、`Word lists`、`Publication information`；`Lessons 1 to 18` 下含 `Activities`、`Listening script(s)`、`Grammar Notes`、`Kanji Words`、`Tips for life in Japan`。
- **`1 How each lesson is organized`**：`Starter, Elementary 1 and Elementary 2 each have nine topics, and are organized into 18 lessons. The suggested time for each lesson is around 150 to 180 minutes.` 然后 `Each lesson is organized as below:` → `◦Topic name and lesson title` / `◦Introductory questions`（`These are questions to help you get a clear image of the themes of the lessons. Look back on your own experiences, and talk about them in class.`）/ `◦Activities`（`These activities help you to achieve the Can-dos, and are the main part of this textbook. Each lesson has 3 to 6 activities.`）/ `◦Listening script(s)` / `◦Kanji Words`（`Study the kanji words that appear in the activities. (In Starter, you will study hiragana in Lesson 1 and katakana in Lesson 2.)`）/ `◦Grammar Notes`（`Explanations of the grammar and expressions that you study in each lesson.`）/ `◦Tips for life in Japan`。
- **`2 Activities and steps`**：(1) `There are four types of activity in each lesson: speaking, listening, reading, and writing.` 各自目标（Speaking：`become able to ask and answer questions in familiar situations`；Listening：`understand the important parts of everyday conversations`；Reading：`get the necessary information in written texts in everyday life`；Writing：`filling in the forms needed for everyday life`）。(2) `Each activity has the following steps:` → `➊Can-do objective`（`Look at the Can-do of that activity to understand its objective.`）→ `➋Activity` → `➌Can-do check`（`Use the Can-do check at the end of the book to do a self-evaluation.`）。自评档位逐字：`★☆☆：まだ難しかった(I did it, but could do it better.) ★★☆：できた(I did it.) ★★★：よくできた(I did it well.)`
- **Speaking activities 完整步骤（§3 of [S5]）**：`➊Can-do objective` → `➋Preparation for the words`（`1. Listen to the audio while looking at the illustrations, and check the meaning of the words` / `2. Listen to the audio and try repeating the words` / **`The aim is to check the pronunciation, not to memorize the words.`** / `3. Listen to the audio and choose the illustration that matches the content` / `Check whether you understand the meaning immediately after hearing the word. The aim is to become able to link the meaning with the expression.`）→ `➌Listen to the example dialogs`（`You do not need to understand the grammar and expressions in detail for this step.`；有脚本/无脚本两种听法各 3 步）→ `➍Focus on the form`（`1. Focus on the grammar and expressions` / `Listen to the audio and fill in the blanks, focusing on the linguistic form.` / `2. Think about the meaning and usage` / **`The learner should think about this and discover the rules of Japanese themselves, instead of the teacher explaining the grammar first.`** / `➡Afterwards, read and check the "Grammar Notes" example sentences and explanations.` / `3. Listen once again to the example dialogs, focusing on the expressions used`）→ `➎Speaking`（`1. Listen to the model dialog` / `2. Shadow the dialog` / `3. Practice it` / `4. Speak freely`：`Speak freely about yourself, or perform a role play.`）→ `➏Can-do check`。
- 真实课名 / Can-do / 词表样例（PDF 页内逐字）：`第9課 成人の日は、何をするんですか？ 年中行事とマナー` / `Can talk in simple terms about festivals and events in your country.` / `ことばの準備 Preparation for the words`；词表行 `大切（な） important ｜どんなふうに how ｜祝う celebrate ｜赤 red ｜色 color ｜例えば for example ｜飾りつけ decorations ｜半分 half`，并写 `ことばを確認して、もういちど聞きましょう。 Check the words and listen to the dialog again.`（**先查词、再听一遍**的官方复习动作）。
- **Reading activities**：`➊Can-do objective → ➋Reading`（`1. Check the situation` / `2. Understand the content step by step` / **`You do not need to understand everything; if you can answer the questions, you have achieved the Can-do.`** / `Generally, there are no furigana (ruby characters) on the texts ... just like real ones.` / `Check the useful words`：`First, read the text without looking anything up. Then, check the meaning of these useful words, and look up the ones you do not know and how to read the kanji in a dictionary. After this, it's a good idea to try reading the text again.` / `3. Deepen your understanding`）→ `➌Focus on the form` → `➍Can-do check`。
  → **注意**：Irodori 刻意不给阅读文本加振假名，是为了训练真实阅读；但本项目是零基础、目标是「看懂」，**必须反过来给假名**（§2.4 第 3 条）。
- **Kanji Words 步骤（§3 of [S5]）**：`➊Check how to read the kanji words and their meaning`（`The kanji are written in three different fonts`）/ `➋Read the kanji words in a sentence` / `➌Type the kanji words`（**`You do not have to be able to write the kanji by hand, but you can do so if you are interested in kanji`**）→ **这是「汉字不要求机械抄写」的官方依据**（§3.4）。`In each lesson, this section covers around 10 kanji words from the activity. (You will learn 429 kanji in total in Starter, Elementary 1, and Elementary 2.)`
- **Grammar Notes（§3 of [S5]）**：`These explanations cover the form, the meaning, and the usage of the grammar and expressions in the activity. There are also additional information and extra example sentences with grammar usages that are not included in the activities in the textbook. In addition, there are conjugation tables and comparisons to similar expressions, so you can organize your knowledge of grammar.` → **「意思 / 接续 / 用法 / 补充例句 / 变形表 / 与相近表达比较」正是本文件 §3.3 语法字段规格的官方依据**。`learners should first think about how to use the grammar and expressions themselves. Afterwards, they can read the explanations`（先自己发现，再看讲解）。真实例句：`お元気ですか？` / `去年、日本に来ました。` / `日本の生活に、もう慣れましたか？`（带振假名 `日本/にほん`、`来/き`、`慣/な`），课名 `第1課 レストランで働いています 今の私`。

**[S6] Irodori 官方《Table of Contents》PDF（本轮 curl + PyMuPDF 提取，逐字）**：
- 表头四技能：`Listen / Speak / Read / Write`。
- `Table of Contents Irodori Starter (A1)`；`▶Topic Starting to Speak Japanese` → `Lesson 1 Good morning!` → `Activities / Can-do` 列：`1. こんにちは / 01 Can exchange greetings when you meet someone.` / `2. お先に失礼します / 02 Can say goodbye when leaving.` / `3. ありがとうございます / 03 Can thank someone or apologize to them.` / `4. メッセージスタンプ / 04 Can understand stickers with messages such as "good morning" or "thanks."`；`Hiragana Words Hiragana`；`Tips for life in Japan` → `◦Greeting gestures ◦"Sayoonara" ◦When to use "sumimasen"`。
- `Lesson 3 Nice to meet you.`（`▶Topic About Myself`）→ `1. はじめまして / 08 Can give a simple self-introduction, for example by saying your name and country / hometown.` … `Kanji Words` → **`名前　国　私`**；`Grammar Notes` → **`➊ Nです / N1 はN2 です / トンです。/ 私はマルシアです。/ ➋【place】から来ました / ブラジルから来ました。/ ➌ Nは？ / お名前は？ / ➍ Sか？ / ➎ Nも / ➏ Nじゃないです`**；`Tips for life in Japan` → `◦Japanese characters ◦How to call someone ◦Japanese era names`。
  → **本项目 Day 1 的 `N は N です` 与 Irodori Starter Lesson 3 的 Grammar Notes ➊ 是同一句型，官方例句为 `私はマルシアです。`；但课序不同（本项目 Day 1 就教，Irodori 在第 3 课），这是 [P2] §1 明确的「不照抄课序」。**
- `Lesson 4 I live in Tokyo.` → `12 Can listen to a family being introduced and understand who is who.` 等。

**[S7] Marugoto e-Learning 页**：`The courses are from Starter A1 to Pre-Intermediate (A2/B1).`；`Self-Study Courses` / `Tutor Support Courses`；`MARUGOTO + (MARUGOTO Plus)` → `You can practise not just kanji and grammar, but also conversations while watching videos.`；`MARUGOTO Words（MARUGOTO-NO-KOTOBA）` → `You can use it as a dictionary to check the meaning of words, and to create My Lists for storing and organising vocabulary. You can also practise vocabulary by topic and by category. You can listen to recordings.`；`Irodori: Japanese for Life in Japan` → `You can download all the lesson materials in PDF format and as audio files free of charge on the "Irodori" website.`；`HIRAGANA/KATAKANA Memory Hint`（`illustrations` / `quizzes`）、`KANJI Memory Hint 1・2・3`（`mnemonic pictures` / `games`）。

**[S8] Marugoto Download Materials 页**：
- 双线与级别（逐字）：`## A1` → `### Starter` → `#### Katsudoo` / `#### Rikai`；`## A2` → `### Elementary 1` / `### Elementary 2` 各 `#### Katsudoo` / `#### Rikai`；`## A2/B1` → `### Pre-Intermediate`；`## B1` → `### Intermediate 1` / `### Intermediate 2`。
- **配套素材类型（真实模块名，逐字）**：`Digital audio files`、`Can-do Check`、`Word book`、`Vocabulary index`、`Phrase index`、`Task sheets for writing`、`Lesson Review (Can-do Conversation）`、`Kanji word list`、`Nihongo Check`、`Sakubun worksheets`、`Notes for talking`、`Topic Review (Can-do Conversation）`、`Vocabulary List`、`Translations of Listening Scripts and Text in the Textbook`、`Learning Record`、`"Write" Sheet`。
- **诚实标注**：该页**只把 Katsudoo / Rikai 作为两列并列，没有给出两者文字定义**。`Katsudoo 与 Rikai 的官方文字定义：本页未核实`（[P1] 亦仅记录「Katsudoo/Rikai 双线、级别」而未给定义）。URL 里 `starter_a` / `starter_c` 的 `a`/`c` 含义本轮未核实，不作推断。
- `Translations of Listening Scripts and Text in the Textbook`（课文/听力脚本翻译）与 `Can-do Check` / `Lesson Review (Can-do Conversation)` / `Learning Record` 是「例句给中文 + 自评 + 复习」的官方对照物。

**[S9] JLPT Level Summary 页**（逐字）：
- `N3 is a bridging level between N1/N2 and N4/N5.`
- N3：`**The ability to understand Japanese used in everyday situations to a certain degree.**`
- Reading 三条：`One is able to read and understand written materials with specific contents concerning everyday topics.` / `One is also able to grasp summary information such as newspaper headlines.` / `In addition, one is also able to read slightly difficult writings encountered in everyday situations and understand the main points of the content if some alternative phrases are available to aid one's understanding.`
- Listening：`One is able to listen and comprehend coherent conversations in everyday situations, spoken at near-natural speed, and is generally able to follow their contents as well as grasp the relationships among the people involved.`
- `While not noted in the table, Language Knowledge, such as Vocabulary and Grammar, is also required for successful execution of these activities.`
- 另可见 N4 `The ability to understand basic Japanese.`、N5 `The ability to understand some basic Japanese.`，可作为零基础起步的锚点（[P2] §1 已引用）。

**[S10] Genki 官网首页**（`https://genki3.japantimes.co.jp/`，由 `https://genki.japantimes.co.jp/en/` 重定向）：`初級日本語げんき第3版公式サイト「Genki-online」`；导航 `『げんき［第3版］』 のご紹介` / `学習者用ページ` / `教師用ページ` / `採用見本` / `取扱書店`。首页无教材结构信息。

**[S11] Genki 官方介绍页 `/intro/`（主流教材第 1 套，全套一课模块名，逐字）**：
- `『げんき』は全部で23 課構成です。第1巻（1～12 課）・第2巻（13～23 課）に分かれており、それぞれにテキストとワークブックがあります。`
- 双线：`『げんき』は、〈会話・文法編〉と〈読み書き編〉の２つのセクションに大きく分かれています。`；`会話・文法編` → `文法を学び、語彙を増やしながら、話す力と聞く力を養います。`；`読み書き編` → `ひらがな・カタカナ・漢字を学びながら、読む力と書く力を伸ばします。`；`学習する漢字：317字`、`約1,700語の基本語彙`。
- **真实课名（げんき1 会話・文法編 / 読み書き編）**：`第1課 あたらしいともだち / ひらがな`、`第2課 かいもの / カタカナ`、`第3課 デートの約束 / まいにちのせいかつ`、`第4課 初めてのデート / メアリーさんのしゅうまつ`、`第5課 沖縄旅行 / りょこう`、`第6課 ロバートさんの一日 / 私のすきなレストラン`、`第7課 家族の写真 / メアリーさんのてがみ` … `第12課 病気 / 七夕`；げんき2 `第13課 アルバイト探し` … `第23課 別れ / 顔文字と絵文字`。
- **一课模块名（§3「『げんき』の使い方」→ 5「〈会話・文法編〉の使い方」，逐字）**：
  - `会話 Dialogue`：`「会話」は、日本に来た留学生メアリーさんを中心にストーリーが展開し…その課で学ぶ新しい学習項目が含まれています。その課の単語や文法を習得した後で、学びましょう。` / `❶ 課の最初に、この課でできるようになることが書いてあります。` / `❷ 会話の音声は２回収録されています。１回目はふつうの会話、２回目は１文ごとに練習のためのポーズが入っています。`
  - `単語 Vocabulary`：`会話や練習に出てくる単語のリストです。単語は少しずつ繰り返し覚えましょう。` / `❶ 単語の音声には英訳も入っています。２回の音声のうち、１回目は日本語－英語、２回目は英語－日本語の順に流れます。` / `❷ 会話に出てくる単語には「＊」がついています。` / `❸ 単語リストに併記してある漢字は、覚える必要はありません。`
  - `文法／表現ノート Grammar/Expression Notes`：`「文法」には、その課で学ぶ文法の説明があります。なるべく専門的な用語を使わず、わかりやすく書いてあります。` / `文法の最後にある「表現ノート」では、文法項目としては取り上げていない表現や単語について説明しています。`
  - `練習 Practice`：`「文法」の次に「練習」があります。練習は文法と対応しています。` / `❶ 練習の見出しの横に、対応する文法の番号が書いてあります。必ずその文法説明を読んでから、練習してください。` / `❷ 音声マークがついている練習は、キューと答えが収録されています。`
  - `その他の情報`：`Useful Expressions` / `Culture Notes` / `Let's Find Out`。
  - `読み書き編`：`漢字表 Kanji list` → **`漢字表には、漢字の読み方、意味、総画数、筆順、またその漢字を使った熟語とその英訳が載っています。１課で学習する漢字は約15字です。`** / `漢字の練習 Kanji Practice` / `読む練習 Reading Practice`（`１課に１～２つの読み物があり、それぞれに内容質問がついています` / `❷ まだ学んでいない単語は訳がついています。`）/ `書く練習 Writing Practice`（`各課の最後に`）。
  - `巻末`：`文法さくいん Grammar Index` / `単語さくいん（日－英／英－日） Vocabulary Index (J-E / E-J)` / `日本地図／数／活用表 Map of Japan / Numbers / Conjugation Chart`。
- **表记 / 注音规则（极关键，逐字）**：`〈会話・文法編〉の第２課までは、漢字は使わず、ひらがな・カタカナにローマ字を併記してあります。第３課からは漢字を使った表記となり、ローマ字併記はなくなる` / **`〈会話・文法編〉では、漢字を勉強しない人でも学習できるように、漢字にすべてふりがなが振ってあります。〈読み書き編〉では、既習漢字にはふりがなは振ってありません。`** → 官方依据：**入门阶段给罗马字 + 全文振假名，随级别逐步撤掉**。本文件 §3.1 的「罗马字/假名/音调」规格据此。
- 学时：`全23課を修了するのに約200時間を想定しています（会話・文法編：各課６時間、読み書き編：各課３時間）`；`第1巻の修了時には日本語能力試験N5 あるいはCEFR のA1 レベル程度、第2巻の修了時にはN4 あるいはCEFR のA2 程度`。
- `ページ見本・音声試聴`：`テキスト⾒本 ・会話・⽂法編 第7課 ・読み書き編 第7課`（样本链接指向 actibookone 电子样书，本轮未打开样书正文，**样页内部版式未核实**）。

**[S12][S13] みんなの日本語 / スリーエーネットワーク（主流教材第 2 套）**：
- `https://www.3anet.co.jp/mnn/` 真实访问返回 `ページがみつかりません｜スリーエーネットワーク` → `# ページがみつかりません`（404）。
- `https://www.3anet.co.jp/` 真实访问成功，但可见内容仅为 `## 新刊 / 近刊` 与分类链接：`みんなの日本語 中級Ⅰ 第２版 本冊`、`中級`、`総合教科書`、`初級前期`、`初級後期`、`漢字`、`聴解`、`作文`、`日本留学試験対策` 等。
- **诚实结论**：`みんなの日本語 的一课模块名（本文／文型／例文／会話／単語／練習／問題 等）：未核实`。本轮真实访问到的只有 404 与官网新刊/分类标签，**不编造任何课名、模块名或页码**。主流教材的「一课模块名」结论全部基于已完整核实的 [S11] Genki 与 [S5][S6] Irodori，已满足「1–2 套」。

### 1.3 与项目内已核实调研的关系（不混淆一手/二手）

- 本轮**重新真实访问**了 [S1]–[S13]；其中 [S5][S6] 是官方公开 PDF（`How to Use This Textbook` / `Table of Contents`），用 `curl` 下载、PyMuPDF 提取正文，属于「官方公开目录/样页」的真实核实，未下载任何受限教材正文课文 PDF（[S1] 的 `X_L01.pdf` 等只记录了文件名与大小，未打开）。
- [P1] `source_registry_official.md` 的元信息（Irodori 4 级 ×18 课 / 644 汉字 / 360–500 学时 / 自定义 ToS / Marugoto Copyright Policy / Tadoku CC BY-NC-ND 4.0 / JLPT testsections 题型表 / N3 能力描述）本轮**阅读并沿用**，但其中 **JLPT `guideline/testsections.html` 的题型构成表与 N3 科目时间表，本轮未重新访问**，凡引用一律标注「引自 [P1]，项目内 2026-11-06 已核实，本轮未复访」。
- [P2] `nh80_framework.md`：本轮阅读，用于 §2.4（不照抄课序）、§5（FSRS 与五阶段由程序决定）、§6 与项目分级/种子的一致性说明。
- [P3] `ux_audit.md`：本轮阅读，用于「页面现在缺什么」与 §7 的 10 条硬要求（与 P0 呼应但不照抄）。
- [P4] `scripts/learning.py`：本轮**逐行阅读**，§5 的所有函数名、常量、字段均为真实代码，不臆造。
- [P5] `web/data/day-001.json`：本轮阅读，§6 示范课与项目现有 6 词 / 3 汉字 / 8 题对齐（差异在 §6.0 说明）。

### 1.4 两条「反直觉」核实结果（必须写进改造说明，避免按印象做）

1. **`irodori/en/starter/pdf.html` 上，一课不是拆成「会話/単語/文法/練習」多个 PDF，而是一个整册 PDF（`X_L01.pdf`～`X_L18.pdf`）+ 带音频 PDF + MP3 ZIP + MP3 Play。** 词表、答案、语法练习、句型表、汉字表是**全级别共享的分册**（[S4]），不在逐课下载页。所以「教材一课有哪些模块」的正确答案来自 [S5][S6][S11] 的教材正文/目录，不是下载页文件名。
2. **`marugoto/en/download/` 只把 Katsudoo / Rikai 并列成两列，没有给出文字定义。** 本文件只写「双线并列 + 各自配不同素材」这一**实际看到**的事实，不替官方补「活动/理解」的定义（[P2] §1 里「Katsudoo（活动）与 Rikai（理解）双线」是项目框架的概括，非本页原文）。

---

## 2. 典型一课的模块序列

### 2.1 教材里「一课」到底按什么顺序教（已核实的原文顺序）

**Irodori（[S5][S6]）**，按课：
```
Topic name and lesson title（主题名 + 课标题，如 Lesson 3 Nice to meet you.）
  → Introductory questions（导入问题，先聊自己的经验）
  → Activities（3–6 个活动，是主体；每个活动标 Listen/Speak/Read/Write + Can-do）
      每个 Speaking 活动内部：
       ➊ Can-do objective          今天这个活动要能做到什么
       ➋ Preparation for the words  ことばの準備：看图听词→跟读→听音选图（目标是查发音、不是背单词）
       ➌ Listen to the example dialogs  先听示范对话，只求大意，不细究语法
       ➍ Focus on the form         听填空聚焦形式 → 自己想意思和用法（教师先别讲）→ 再读 Grammar Notes → 再听一遍
       ➎ Speaking                 听示范 → 影子跟读 → 换词练 → 自由说/角色扮演
       ➏ Can-do check             ★☆☆/★★☆/★★★ 自评 + 写感想
  → Listening script(s) / Kanji Words / Grammar Notes / Tips for life in Japan（课末分区或别册）
  → 别册：Word lists / Answer / Grammar Worksheets / Can-do Check
```
**Genki（[S11]）**，按课（会話・文法編 → 読み書き編）：
```
会話 Dialogue（課の最初に、この課でできるようになることが書いてあります；音声 2 回，第 2 回逐句留停顿）
  → 単語 Vocabulary（单词表 + 日→英 / 英→日 两遍音频；会话出现过的词标 ＊）
  → 文法／表現ノート Grammar/Expression Notes（尽量不用术语）+ 表现笔记
  → 練習 Practice（题头标对应文法编号，"必ずその文法説明を読んでから、練習してください"；带音频标记的题收 cue+答案）
  → 其他：Useful Expressions / Culture Notes / Let's Find Out
読み書き編：漢字表 Kanji list（読み方・意味・総画数・筆順・熟語と英訳）→ 漢字の練習 → 読む練習（附内容質問，未学词给译）→ 書く練習（各課の最後に）
巻末：文法さくいん / 単語さくいん / 日本地図・数・活用表
```
**Marugoto（[S8]）**：`Katsudoo` 与 `Rikai` 双线各自配 `Can-do Check` / `Word book` / `Vocabulary index` / `Phrase index` / `Lesson Review (Can-do Conversation)` / `Kanji word list` / `Nihongo Check` / `Sakubun worksheets` / `Learning Record` / `Translations of Listening Scripts and Text in the Textbook`。

### 2.2 本项目「一页」的模块序列（表格 · 可直接照此排 DOM）

> 每行「给学习者哪些具体字段」就是页面上要有的文字，不是描述。**「教材里叫什么」列带出处编号。**

| # | 学员看到的区块标题 | 教材里叫什么（已核实原名） | 这一区必须给的具体字段 | 为什么这个顺序对零基础有用 |
|---|---|---|---|---|
| 1 | **今天要会的 3 句话** | `Can-do objective`（[S5]）；`課の最初に、この課でできるようになることが書いてあります`（[S11]）；目录的 `Topic name and lesson title` + `Introductory questions` + 每活动 `Can-do`（[S6]） | 一句白话目标（「学完这课，你能用日语说：我是学生」）+ 3 句：**日文（含汉字）｜假名读音｜中文｜🔊 听｜逐词拆解**；逐词行如 `私(わたし)=我　は=提示主题（读 wa）　学生=学生　です=礼貌体的「是」` | 零基础先看到「我今天能说出什么」，才知道下面每个词是拿来干什么的。教材把目标写在最前，现有页面却把它写成「本日 Can-do／能力侧重 listening/reading」的系统黑话（[P3] §2.1）。目标必须是**人话 + 能听的句子**，不是 ICF 式条目。 |
| 2 | **今日 6 个词**（常显，不折叠不翻面） | `ことばの準備 Preparation for the words`（[S5]）；`単語 Vocabulary`（[S11]）；`Word lists` / `Word book` / `Vocabulary index`（[S4][S8]） | 书写（汉字/假名）｜假名读音｜罗马字｜汉字词的音读/训读提示｜**词性（中文）**｜中文义｜1–2 个**带假名+中文**的例句｜常见搭配｜中日同形异义提示｜**韩语对照**｜🔊 听 | 先给「砖」，且官方明确这一步是「查发音、把音和义连起来」，不是背单词（[S5]：`The aim is to check the pronunciation, not to memorize the words.`）。零基础必须先能读出词才敢开口；先看到假名和中文，才不会去猜汉字。 |
| 2.5 | **今日 3 个汉字**（插在词后，独立小区） | `Kanji Words`（[S5][S6]）；`漢字表 Kanji list`（[S11]）；`Kanji word list`（[S8]） | 字形｜**音读（片假名）**｜**训读（平假名）**｜例词（日文+假名+中文）｜中文母语者陷阱｜「不要求机械抄写」说明｜（可选）韩语汉字词 | 教材把汉字放在课末 / 别册，且 Q15 明确 `Kanji are not taught on their own ... you will study them as words used in the activities`（[S3]）。本项目把它提前到词后，是为了让零基础当天就能读出「日/月/火」，但**仍按「放在词里学」写**（§3.4）。 |
| 3 | **今日 1 条语法** | `Focus on the form` → `Grammar Notes`（[S5]）；`文法／表現ノート Grammar/Expression Notes`（[S11]）；目录 `➊ Nです / N1 はN2 です`（[S6]） | **意思（中文白话）**｜**接续公式（中文注释，不能只写「名詞＋は＋名詞＋です」）**｜2–3 个例句（日文+假名+中文+逐词）｜使用场景｜**易错点（中文）**｜**与相近语法的区别**｜**韩语对照（含「必须验证」）** | Irodori 要求学习者先自己发现规则、之后才读 Grammar Notes（[S5]），Genki 要求「先读文法说明再做练习」（[S11]）。所以语法必须**先于练习**、且**用中文讲**（现有页面接续用日语术语「名詞」、例句无假名无中文、易错点 0 条，见 [P3] §2.5）。 |
| 4 | **例句 / 会话**（独立成区，不与素材混） | `Listen to the example dialogs` / `Listening script(s)` / `model dialog`（[S5]）；`会話 Dialogue`（[S11]）；`Translations of Listening Scripts and Text in the Textbook`、`Lesson Review (Can-do Conversation)`（[S8]） | 每段：**日文原文（含汉字）｜假名读音（必须 ≠ 原文）｜中文翻译｜逐句拆解｜超纲生词中文注释｜🔊 听** | 教材把「课文」和「听力脚本 / 课文翻译」分开给（[S5][S8][S11]）。现有页面把 `audio_text` 当「文本读音」输出，结果「读音」= 原文（[P3] §2.5、`app.js:602/955`），零基础看到 `お元気ですか` 仍然不会读。**原文与读音必须是两个不同节点。** |
| 5 | **听与说** | `➎ Speaking`：1 `Listen to the model dialog` 2 `Shadow the dialog` 3 `Practice it` 4 `Speak freely`（[S5]）；Genki `会話の音声は２回収録…２回目は１文ごとに練習のためのポーズ`（[S11]） | 示范对话音频（可逐句暂停/慢速）｜跟读提示｜换词替换框（把 `リン` 换成自己的名字）｜自由说/角色扮演提示｜「先听 → 跟读 → 换词 → 自己说」四步中文指引 | 教材的共同坡度是「先听后说、先模仿后替换再自由产出」，不要求一上来就自己造句（[S5][S11]）。零基础最怕「第一题就是开放产出题」（[P3] §5 手机端第 3 条），这条坡度把产出放在最后一步。 |
| 6 | **练一练（当日练习）** | `Grammar Worksheets` / `Answer` / `IRODORI Practice（words, kanji, grammar, expressions）`（[S3][S4]）；`練習 Practice` + ワークブック + `解答`（[S11]）；`Nihongo Check` / `Task sheets for writing` / `Sakubun worksheets`（[S8]） | 题干｜明确作答框｜提交｜**提交后同屏**：对/错 + 为什么（中文）+ 正确说法 + 🔊 再听一次｜**参考答案（开放题给示范句，不是只有自评按钮）**｜评分准则（中文） | Genki：`練習の見出しの横に、対応する文法の番号…必ずその文法説明を読んでから、練習してください` → 练习紧跟语法；Irodori 把答案单独成册 → **先作答后揭示**。现有页面 8 题全折叠、反馈是英文错误枚举、开放题无示范句（[P3] §2.5/§6 P0-8）。 |
| 7 | **今日复习清单 + 自测** | `Can-do Check`（★☆☆/★★☆/★★★ + comment）（[S5]）；`Check the words and listen to the dialog again`（[S5]）；`Can-do Check` / `Lesson Review (Can-do Conversation)` / `Learning Record` / `Nihongo Check`（[S8]）；项目 `scripts/learning.py`（[P4]） | **今天具体复习哪几个词（逐词列出）**｜首次学哪天 / 上次哪天 / 间隔几天｜**先遮住中文回忆**｜点开对答案｜**记住了 / 模糊 / 忘了**｜**下次大约哪天再来**｜中文三档自评（「还不行 / 会了 / 很熟」） | 教材用「自评 ★ + 写完再听一遍」收尾（[S5]），本项目用 FSRS 排期，但**必须翻译成人话**：不出现 `FSRS / 到期项 / 排期 / review_count`（[P3] §6 P0-7）。先回忆后对答案是检索练习，页面只展示与收集（§5）。 |

### 2.3 为什么这个顺序对零基础有用（一句话版，逐模块）

1. **目标先行**：先给「我今天要说出哪 3 句」，学习才有落点；否则词表和语法都是无意义的清单。
2. **词在语法前**：句子是由词拼出来的；先能读出 `わたし / がくせい / です`，再讲 `は` 怎么把它们串起来，认知负荷最低。
3. **汉字紧跟词**：当天见到的汉字当天给读音，但**放在词里给**，不孤立抄写（[S3] Q15、[S5] Kanji Words）。
4. **语法用中文、先例子后规则**：Irodori 让学习者自己从填空里发现规则（[S5]），Genki 说「尽量不用术语」（[S11]）——对零基础，先看到 3 个能懂的例句，再给一句接续公式，比先甩「名詞＋は＋名詞＋です」有效得多。
5. **例句独立、读音独立**：汉字句不等于读音句；把两者分开，学员才不会把 `今日` 读成中文「jīnrì」。
6. **先听后说、四步产出**：模仿 → 替换 → 自由说，是教材反复用的坡度（[S5] ➎、[S11] 会話音声 2 回），能挡住「零基础第一题就开放产出」的死局。
7. **练习紧跟语法、先做后讲**：题头标对应语法（[S11]），答案单独成册（[S4]），反馈必须是中文讲解不是英文枚举。
8. **收尾是回忆与自评，不是进度条**：教材用 Can-do Check ★（[S5]），本项目用 FSRS，但学员看到的必须是「具体词 + 下次哪天」。

### 2.4 与教材顺序的 3 处有意调整（并写清理由，呼应 [P2] §1「不照抄课序」）

| 调整 | 教材怎么做 | 本项目怎么做 | 理由（已核实依据） |
|---|---|---|---|
| **把课末 / 别册的内容搬到首屏常显** | Grammar Notes、Kanji Words、Word lists、Answer、Grammar Worksheets 都在课末分区或独立分册（[S4][S5][S6][S11]） | 单词 / 语法 / 汉字 / 例句 / 练习全部在同一页、默认展开 | 教材一课 150–180 分钟活动 + 60–120 分钟语言知识（[S3] Q13）、Genki 一课 6+3 小时（[S11]）；本项目每天 60 分钟，学员不会去翻别册。**不搬就是「内容存在但不可学」**（[P3] 一句话结论）。 |
| **给全部例句加假名与中文（教材刻意不给）** | Irodori 阅读文本 `there are no furigana (ruby characters) ... just like real ones`（[S5]）；Genki 会話・文法編给全文振假名、入口阶段还并记罗马字，第 3 课起撤罗马字（[S11]） | 零基础阶段**所有词 / 例句 / 素材常显假名 + 罗马字 + 中文翻译**，并明确「原文 ≠ 读音」 | Irodori 不给振假名是为了训练「真实材料里猜词」，那是 A1 后期目标；本项目 Day 1 学员连五十音都没学完，目标是「看懂、读出」，必须反着来。**Genki 的「入口给罗马字 + 全文振假名、逐步撤除」才是本项目该抄的分级做法**（[S11]）。 |
| **把「复习」显式化，且用程序排期** | 教材用 `Can-do Check` 纸质自评 + 「查词后再听一遍」（[S5]）、`Learning Record`（[S8]） | 页面列具体词 + 三档回忆 + 下次日期；**due 与掌握判定全部交给 `scripts/learning.py`** | 教材没有间隔重复调度；本项目已 vendor FSRS（[P2] §1、[P4]）。但页面必须把「FSRS 到期 12 项」翻译成人话（[P3] §6 P0-7），见 §5。 |

> **不采纳的部分**（[P2] §1 同调）：Irodori 18 课线性课序、全量 644 汉字、Marugoto CEFR 标签、JLPT 官方样题原题、教材正文语料。本文件只迁移**目标格式（Can-do 说人话）、模块顺序、字段规格、注音分级、先学后练**，不复制任何教材课文。

---

## 3. 每个知识点的最小呈现规格

### 3.1 字段规格总表

| 知识点 | 必填字段 | 选填 / 当前留空 | 页面硬规则 | 依据 |
|---|---|---|---|---|
| **单词** | 书写、假名读音、罗马字、词性（中文）、中文义、1–2 例句（日文+假名+中文）、常见搭配、中日同形异义提示、🔊 听按钮、韩语对照 | **音调（アクセント）**：本项目当前无权威音调数据源（[P2] §8：877 条种子标 `S000 项目原创整理`，未逐条对照 JMdict/KANJIDIC，14 条 `needs_review`），**Day 1 示范课留空，不编造 0/1/2 型数字** | 含汉字的词**先显示假名 + 听，再显示中文义**；中文义不得由汉字直接推断 | `単語 Vocabulary`（[S11]）、`ことばの準備`（[S5]）、`Word lists`（[S4]）、Genki 全册并记罗马字 + 全文振假名（[S11]） |
| **语法** | 意思（中文白话）、接续公式（中文注释）、2–3 例句（假名+中文+逐词）、使用场景、易错点（≥3 条中文）、与相近语法的区别、韩语对照（含差异）、🔊 | 变形表、补充例句（教材有 `conjugation tables` / `extra example sentences`，Day 1 无变形，留空） | 接续不得只写日语术语；例句必须同时有假名串与中文串；「易错」必须是讲解不是标签 | `Grammar Notes` 覆盖 `form, the meaning, and the usage` + `conjugation tables and comparisons to similar expressions`（[S5]）；`なるべく専門的な用語を使わず`（[S11]） |
| **汉字** | 字形、音读（片假名）、训读（平假名）、例词（日文+假名+中文）、中文母语者陷阱、「不要求机械抄写」说明 | 韩语汉字词、笔画数/笔顺（Genki 漢字表有 `総画数、筆順`，本项目不要求抄写，故不列为必填） | 例词必须带假名与中文；明确「会认、会读、会在词里读出来即可」 | `Kanji Words` ➌ `You do not have to be able to write the kanji by hand`（[S5]）；Q15 `Kanji are not taught on their own`（[S3]）；`漢字表には、漢字の読み方、意味…熟語とその英訳`（[S11]） |
| **例句 / 会话** | 日文原文、假名读音、中文翻译、逐句拆解、超纲生词中文注释、🔊 听 | 逐词语法标注 | **`假名读音 !== 日文原文`**（两个独立 DOM 节点，可用断言验收）；不得用 `audio_text` 冒充读音 | `Listening script(s)` / `Translations of Listening Scripts and Text in the Textbook`（[S5][S8]）；`WORD (without Furigana)` 证明官方区分「带/不带注音」（[S4]）；Genki 全文振假名（[S11]）；现网 bug 见 [P3] §2.5 §4 第 12 条 |

### 3.2 单词：一张卡上逐字该有什么

```
【书写】私          ← 汉字/假名并记；纯假名词直接写假名
【假名】わたし        ← 常显，不因「有 ja-JP 语音」而隐藏（现网 app.css:182 反着做）
【罗马字】watashi     ← 入口阶段必给，依据 Genki「ローマ字を併記」（[S11]）
【音读/训读提示】わたし 是训读；「私」音读 シ（私立 しりつ）
【词性】代名词（人称代名词）        ← 中文写，不写「名詞」
【中文义】我
【例句 1】私は学生です。／ わたしはがくせいです ／ 我是学生。
【例句 2】私の名前はリンです。／ わたしのなまえはリンです ／ 我的名字叫小林。（超纲词「名前 なまえ」给中文注释）
【常见搭配】私＋は（提示主题）／私の（我的）／正式场合 わたくし
【⚠ 中日同形异义】中文「私」读 sī，意思是「私人、私自」；日语「私」是「我」。字形一样、意思不同，别按中文猜。
【韩语对照】私 ≈ 저／나（저 是谦让、나 是平称）；注意日语「私」不分谦让/平称，韩语分。
【🔊 听这个词】
```
**为什么这些字段**：Genki 单词表明确「音声 2 回：1 回目 日本語－英語、2 回目 英語－日本語」「会話に出てくる単語には＊」「単語リストに併記してある漢字は、覚える必要はありません」（[S11]）→ **给音、给义、标明是否会话词、不要求记汉字写法**；Irodori 词准备是「看图听词 → 跟读 → 听音选图」（[S5]）→ 所以「听」按钮和「音-义直连」优先于中文解释。本项目额外补「词性 / 搭配 / 同形异义 / 韩语对照」，是针对中文母语者 + 韩语背景（[P2] P4「迁移加速但强制验证」）。

### 3.3 语法：一张卡上逐字该有什么

```
【意思】「A 是 B」。は 把 A 立成「我们接下来要聊的话题」，です 在句末礼貌地断定「是 B」。
【接续】名词 ＋ は ＋ 名词 ＋ です
        （中文注释：名词就是人、东西、地方、身份的名字；は 读 wa 不读 ha；です 是礼貌体句末）
【例句 1】私は学生です。／ わたしはがくせいです ／ 我是学生。
         逐词：私=我　は=主题（读 wa）　学生=学生　です=是（礼貌）
【例句 2】リンさんは学生です。／ リンさんはがくせいです ／ 小林是学生。
【例句 3】今日はいい天気です。／ きょうはいいてんきです ／ 今天天气好。
【使用场景】第一次见面、向老师/上级/不熟的人做自我介绍、说明身份或职业。
【易错点】
  ① は 做助词读 wa，不读 ha；中文「我」后面不用加东西，中国学习者最容易整个漏掉 は。
  ② 中文可以说「我是李先生」，日语不能给自己加 さん：×私は李さんです → ○私は李です。
  ③ です 别随便换成 だ：だ 是简体，对不熟的人失礼；朋友之间才用。
  ④ は 提示「主题」不是「主语」，别急着把 は 当成 が。
【与相近语法的区别】
  ・N は N です vs N が N です：回答「你是谁？」用 私は学生です；回答「谁是学生？」（强调是我不是别人）用 私が学生です。
  ・N です（省略 は）：回答「你是谁？」可直接说 リンです。话题已在问句里，は 可省。
  ・～ですか（疑问）、～ではありません（否定）：今天不教，明天学，先别急。
【韩语对照】は ≈ 은/는，が ≈ 이/가，です ≈ 입니다／이에요。
  ⚠ 必须验证：は 是「主题」不是「主语」；は 写 は 读 wa 不随词变形，韩语 은/는 要按收音选；
    です 只是「礼貌体句末」的近似，韩语礼貌体分 입니다（正式）／이에요（日常），不能一律翻成 입니다。
【🔊 听 3 个例句】
```
**依据**：`Grammar Notes` 官方写明覆盖 `form, the meaning, and the usage`、含 `extra example sentences`、`conjugation tables and comparisons to similar expressions`（[S5]）；`Focus on the form` 要求学习者先自己发现规则（[S5]）；Genki「なるべく専門的な用語を使わず、わかりやすく」（[S11]）；目录里 `➊ Nです / N1 はN2 です / 私はマルシアです。`（[S6]）正是这条句型。

### 3.4 汉字：不要求机械抄写

```
【日】
  音读：ニチ / ジツ      训读：ひ / か
  例词：日本（にほん／にっぽん）日本｜日曜日（にちようび）星期日｜三日（みっか）三号｜今日（きょう）今天
  ⚠ 中文母语者陷阱：中文「日」只读 rì，日语随词变 にち / じつ / ひ / か / きょう，不能按中文音类推；
    「日曜日」的「日」指星期日，中文「日」没有这个用法。
  （韩语汉字词可参考：일본 日本、일요일 日曜日 —— 只是提示，读音各不相同）
  ✅ 不要求抄写：会认、会读、能在词里读出来就行（[S5] Kanji Words ➌ 官方：不必手写）
```
**依据**：`Kanji Words` ➌ `Type the kanji words ... You do not have to be able to write the kanji by hand`（[S5]）；Q15 `Kanji are not taught on their own ... you will study them as words used in the activities`（[S3]）；Genki `漢字表には、漢字の読み方、意味、総画数、筆順、またその漢字を使った熟語とその英訳`（[S11]）——本项目取「読み方・意味・熟語」，**舍弃**「総画数・筆順・抄写」，理由就是零基础 + 80 学时压缩（[P2] §2）。

### 3.5 例句：原文与读音必须分开（硬规则）

```
【原文】今日はいい天気です。          ← 含汉字，是「写在纸上的样子」
【读音】きょうはいいてんきです。        ← 纯假名，是「怎么念」，两串字符串不相等
【中文】今天天气好。
【逐句】今日（きょう）=今天　は=主题（读 wa）　いい=好　天気（てんき）=天气　です=是（礼貌）
【🔊 听这句】
```
**验收断言**：`读音节点.textContent !== 原文节点.textContent`。现网 `app.js:602` / `app.js:955` 把 `m.audio_text` 直接当「文本读音（TTS 降级/对照）」输出，而 `day-001.json` 里 `audio_text === text_ja`（[P5] M0001/M0002），所以「读音」= 原文（[P3] §2.5 §4 第 12 条）。**这一条不修，零基础永远学不会读。**
**依据**：[S4] 官方同时提供 `WORD` 与 `WORD (without Furigana)` 两版，证明「带注音 / 不带注音」是两种不同呈现；[S11] Genki 会話・文法編「漢字にすべてふりがなが振ってあります」；[S8] Marugoto 单列 `Translations of Listening Scripts and Text in the Textbook`。

---

## 4. 中文母语者 + 韩语背景的讲解模板

### 4.0 总边界（写在页面最醒目处）

> **结构可以借，词不能猜。**
> - **可以对照（结构层，能加速，不必逐字验证）**：SOV 语序、助词后置这个「概念」、主题/主格的大致分工、「句末要变成礼貌体」这个意识、部分汉字词的大致词义。
> - **必须验证（词/句层，一律给「日文 + 假名 + 中文 + 韩语」四行并配 1 道题）**：具体选哪个助词、具体读音（音读/训读/韩语汉字音）、具体词义、礼貌体层级、日韩汉字词是否真的同义。
> - **防呆规则**：凡含汉字的词，页面必须先显示假名读音 + 听按钮，再显示中文义；教师/页面**禁止**说「看汉字就猜得出」；每个汉字词至少配 1 道「验音」或「验义」题（[P2] P4、`error_correct` 题型）。

以下每小节都用同一张「对照块」模板：**【可以对照】/【必须验证】/【页面写法示例】**。韩语对照为本项目原创教学讲解模板（**非引用某本教材，未核实特定教材原文**），日语与韩语形式逐条自检见 §6.8。

### 4.1 は / が ↔ 은/는 ・ 이/가

- **【可以对照】** は（主题/话题）≈ 은/는（主题/话题）；が（主格、新信息）≈ 이/가（主格）。
  - `私は学生です。` ≒ `저는 학생입니다.`（我是学生，话题是「我」）
  - `私が学生です。` ≒ `제가 학생입니다.`（是我，不是别人；回答「谁是」）
  - 四个都是**助词贴在名词后面**，这个概念可以直接平移，中文没有，韩语背景省掉一大截解释。
- **【必须验证】**
  1. **は 是「主题」不是「主语」，不能等同 은/는 后逐句硬套**。主题 = 「接下来我们要谈的是 X」，它可以和主语重合，也可以不是主语：`象は鼻が長い` ≒ `코끼리는 코가 길어요`（は 提示话题「大象」，が 才是真正主语「鼻子」）。日语 は 的对比/旧信息用法范围比韩语更宽，几乎每句都能带 `私は`。
  2. **形态不同**：は 永远写作 `は` 却读 `wa`，不随前面的词变形；韩语 은/는 要按前一音节有没有收音（받침）选 `은` 或 `는`，日语没有这一步。
  3. **が ≠ 永远 이/가**：`コーヒーが好きです`（喜欢咖啡）里 が 标记「喜欢的对象」，韩语说 `커피를 좋아해요`（宾语 을/를）——**这里 が 反而对应 을/를**，直接套 이/가 就错。
  4. 韩语口语常省助词（`저 학생이에요`），日语也常省，但 は 一旦出现就带话题功能，不能省着省着把 は 也丢了。
- **【页面写法示例】**
  ```
  【可以对照】は ≈ 은/는（提示话题）；が ≈ 이/가（指出「是谁/是什么」）
  【必须验证】は 是主题不是主语；は 写 は 读 wa、不随词变形；韩语 은/는 要看收音；
              「～が好き」的 が 对应韩语 을/를，不是 이/가。
  私は学生です。≒ 저는 학생입니다。｜私が学生です。≒ 제가 학생입니다。
  ```

### 4.2 を ↔ 을/를、に / で ↔ 에 / 에서（**标出不等价处**）

- **【可以对照】**
  | 日语 | 韩语 | 中文 |
  |---|---|---|
  | 本**を**読みます（ほんをよみます） | 책**을** 읽어요 | 读书 |
  | ご飯**を**食べます（ごはんをたべます） | 밥**을** 먹어요 | 吃饭 |
  | 机の上**に**（つくえのうえに） | 책상 위**에** | 在桌子上 |
  | ７時**に**（しちじに） | 7시**에** | 在 7 点 |
  | 学校**に**行きます（がっこうにいきます） | 학교**에** 가요 | 去学校 |
  | 教室**で**勉強します（きょうしつでべんきょうします） | 교실**에서** 공부해요 | 在教室学习 |
- **【必须验证 —— 不等价处，任务点名要标】**
  1. **で 不总等于 에서**：で 表「动作场所 / 手段 / 材料 / 原因 / 时间界限」，韩语分别用 에서 / 로 / 로 / 때문에 / 에。
     - `バスで行きます` ≒ `버스**로** 가요`（手段用 로，**不是 에서**）
     - `３時で終わります` ≒ `3시**에** 끝나요`（时间界限用 에，不是 에서）
     - `紙で作ります` ≒ `종이**로** 만들어요`（材料用 로）
  2. **に 不总等于 에**：に 还能表「对象 / 方向 / 变化结果 / 目的」，韩语分别用 한테·에게 / 로 / (이)가 / -러 等。
     - `友達に会います` ≒ `친구**를** 만나요`（韩语用宾格 을/를，不是 에）
     - `水になります` ≒ `물**이** 돼요`（结果用 이/가）
  3. **韩语 에서 还表「起点（从…）」，日语要用 から，不是 で**：
     - `학교에서 왔어요` = 从学校来 → 日语 `学校**から**来ました`（がっこうからきました），**不能说 学校で来ました**。
     - 反过来，`日本に住んでいます` 韩语常说 `일본**에서** 살아요`（也可用 에），两边不一一对应。
  4. **を 也表「离开/经过的场所」**：`空を飛ぶ`（そらをとぶ）、`道を歩く`（みちをあるく），韩语用 을/를 或 에서，边界不同。
  5. **形态**：を 写作 `を` 通常读 `o`；韩语 을/를 按收音变，日语不变形。
- **【页面写法示例】**
  ```
  【可以对照】を ≈ 을/를（宾语）；に ≈ 에（存在点/时间点/归着点）；で ≈ 에서（动作场所）
  【必须验证】「坐公交」是 バスで ≒ 버스로（不是 에서）；「从学校来」是 から（不是 で）；
              「见朋友」是 に ≒ 한테/를（不是 에）；「变成水」是 に ≒ 이/가。
              一句话：动作场所能对照，手段/材料/起点/对象一律不能直接套。
  ```

### 4.3 です / ます ↔ 입니다 / ㅂ니다（礼貌体层级差异）

- **【可以对照】** 都是「句末要变成礼貌体」，`私は学生です` ≒ `저는 학생입니다`，`行きます` ≒ `갑니다`，`食べます` ≒ `먹습니다／먹어요`。名词句尾用 です / 입니다，动词句尾用 ます / ㅂ니다·습니다，形态位置一样（都在最后）。
- **【必须验证 —— 层级不同，这是最容易出错的对照】**
  1. **韩语礼貌体分得更细**：하십시오체（`습니다/ㅂ니다/입니다`，最正式：报告、发表、新闻、军队）、해요체（`어요/아요/이에요/예요`，日常礼貌）、해체/반말（`야/이야/어`，平语，只给朋友/小孩）。**日语的礼貌体主要就是 です/ます（丁寧語），简体是 だ/～る**；再往上是「尊敬語・謙譲語」（いらっしゃる／伺う），属于**敬语体系**，不是句末体的层级。
  2. **所以「です ≈ 입니다」只是「都礼貌」的近似**：日常跟老师说话，日语说 `です` 完全得体；韩语却更常说 `이에요/예요`，`입니다` 偏「做报告」。把 です 一律翻成 입니다，韩语听起来会很生硬。同理 `食べます` ≒ `먹어요`（日常）／`먹습니다`（正式）。
  3. 过去式形态不同源：ます→ました，韩语 습니다→았습니다/었습니다，只能类比不能套用。
  4. 两种语言都有「文体要统一」的要求（一篇文章别混 です/だ、别混 체），但规则不同。
- **【页面写法示例】**
  ```
  【可以对照】句末要变礼貌体：です ≈ 입니다／이에요，ます ≈ ㅂ니다·습니다／어요
  【必须验证】韩语礼貌体分 하십시오체(입니다) / 해요체(이에요) / 반말(야) 三级，日语主要只有 です（礼貌）vs だ（简体）；
              日常对话把 です 翻成 이에요 更自然，别一律写成 입니다。
  私は学生です。≒ 저는 학생이에요。（日常）／저는 학생입니다。（正式）
  ```

### 4.4 SOV 语序、助词后置 → 可加速理解

- **【可以对照】** 日语和韩语都是「主语—宾语—谓语」SOV，靠**后置助词**标成分；中文是 SVO、靠语序和前置介词。
  ```
  中文：我        饭        吃
  日语：私は      ご飯を    食べます。   （わたしは ごはんを たべます）
  韩语：저는      밥을     먹어요.
  逐词：我+主题    饭+宾语   吃（句末）
  ```
  → 有韩语背景的学员可以**整句平移**：把中文按「我 / 饭 / 吃」重排，再贴助词，几乎不用重学语序。这是最大的加速点。另外「谓语在最后」「修饰语放前面」「疑问靠句末（か / -요?·까?）」也相似。
- **【必须验证】**
  1. 日语动词「活用」（食べる→食べます）与韩语「活用」（먹다→먹어요）**不同源**，不能拿韩语词尾规则套日语。
  2. 中文没有助词，最容易漏 は/を/に。「有韩语背景」只帮你**接受「要加助词」这件事**，帮不了你**选哪一个**——所以每个助词都要单独验证（§4.1/§4.2）。
  3. `〜は、〜が` 同句共现（`象は鼻が長い`）韩语也能，但使用频率、语感不同，别按中文「大象的鼻子长」直译成语序。
- **【页面写法示例】** 给「中文 / 日语（原文+假名）/ 韩语」三行逐词对齐表，**每个助词单独上色并给一格中文说明**。

### 4.5 汉字词音读 ↔ 韩语汉字词（**音近不等于义同**）

- **【可以对照】**（可批量记「大致词义」）
  | 日语（音读） | 韩语汉字词 | 中文 |
  |---|---|---|
  | 日本語 にほんご | 일본어 (ilbon-eo) | 日语 |
  | 学生 がくせい | 학생 (haksaeng) | 学生 |
  | 図書館 としょかん | 도서관 (doseogwan) | 图书馆 |
  | 学校 がっこう | 학교 (hakgyo) | 学校 |
  | 先生 せんせい | 선생 (seonsaeng) | 老师 |
  中文母语 + 韩语背景 = **双重加速**：看到「図書館」能猜「图书馆」，看到「도서관」也能对上。
- **【必须验证 —— 音近不等于义同】**
  1. **读音不能互推**：日语是日语音读，韩语是韩语汉字音，只是「听起来像」。学生 `がくせい` ≠ 학생 `haksaeng`，図書館 `としょかん` ≠ 도서관 `doseogwan`；**看到韩语汉字词不能推出日语读音，反之亦然**。
  2. **字形可能不同**：日语「図」（简化）、韩语汉字「圖」、中文「图」；「日本語」的「語」韩语读 어、日语读 ご。
  3. **词义会漂移，而且方向不一致**（这是最关键的反例）：
     - `約束 やくそく` = 约定，韩语 `약속` = 约定 ✓，**但中文「约束」= 限制** → 日韩一致、中文不一致。
     - `汽車 きしゃ` = 火车，韩语 `기차` = 火车 ✓，**但中文「汽车」= 小轿车** → 日韩一致、中文相反。
     - `大丈夫 だいじょうぶ` = 没问题，中文「大丈夫」= 男子汉，韩语 `대장부` = 好汉 → **日语与中韩都不同**。
     - `勉強 べんきょう` = 学习，韩语不说这个汉字词（学习是 `공부`），中文「勉强」= 硬撑 → 三方都不同。
  4. 结论：**汉字词只能猜个大概**，必须过「读音 / 词义 / 用法」三关；页面要给「验音」「验义」题（[P2] P4）。
- **【页面写法示例】**
  ```
  【可以对照】汉字词可猜大意：学生 がくせい ≈ 학생 ≈ 学生；図書館 としょかん ≈ 도서관 ≈ 图书馆
  【必须验证】がくせい ≠ haksaeng（读音不同）；日/韩/中字形有差异；
              「汽車」日韩都是火车、中文是轿车；「大丈夫」日语是「没问题」、中韩是「好汉」。
              ⚠ 音近不等于义同，含汉字的词一律先给假名 + 听，再给中文，并配 1 道验义题。
  ```

### 4.6 中日同形异义：必须显式警告

> 页面模板：每个词一个 **⚠ 中日同形异义** 警示块，固定三段「中文里…／日语里…／别按中文猜」。

| 词 | 日语读音 | 日语意思 | 中文意思 | 错用后果 / 韩语背景旁注 |
|---|---|---|---|---|
| **勉強** | べんきょう | 学习 | 勉强、能力不够还硬做 | `日本語を勉強します` = 我学日语，不是「勉强日语」。韩语「学习」说 `공부`，不用这个汉字词 → 三方都不同。 |
| **大丈夫** | だいじょうぶ | 没问题、不要紧、够了 | 有志气的男子汉 | `大丈夫ですか` = 你没事吧？不是「你是男子汉吗」。韩语 `대장부` = 好汉（近中文）→ **韩语背景在这里反而更坑**。 |
| **手紙** | てがみ | 信、书信 | 卫生纸 / 手纸 | `手紙を書きます` = 写信，不是「写手纸」。韩语「信」是 `편지`，不是这个汉字词。 |
| **汽車** | きしゃ | 火车（现代日常多说 電車／列車） | 汽车、小轿车 | `汽車で行く` = 坐火车去。韩语 `기차` = 火车 ✓ → **这里韩语背景帮得上，中文反而错**。 |

**页面硬要求**：这 4 个词出现时必须有红色警示块；不能只给中文义了事。依据 [P2] P4「迁移加速但强制验证 / `zh_trap` / `error_correct` 题型 / 教师 Agent 明确禁止汉字猜词」、[P3] §7 第 9 条「现有 `zh_trap` 是全站唯一符合『适当难点讲解』的内容，应推广到词汇/语法卡」。

### 4.7 一张「对照块」在页面上长什么样（可直接抄）

```
┌─ 韩语对照 ────────────────────────────────┐
│ 【可以对照】は ≈ 은/는（提示话题）；语序都是 SOV，助词都后置。      │
│              私は学生です。≒ 저는 학생입니다。                     │
│ 【必须验证】① は 是「主题」不是「主语」，别当成 が；                │
│              ② は 写 は 读 wa、不随词变形，韩语 은/는 要看收音；   │
│              ③ です ≈ 입니다 只是「都礼貌」，日常更常说 이에요；    │
│              ④ 含汉字的词先给假名 + 听 + 中文，别按中文猜。        │
│ 【一句话】结构可以借，词不能猜。                                  │
└──────────────────────────────────────────┘
```
**验收**：语法区与词汇区各有独立「韩语对照」子块；全文韩文字符（가-힣）≥ 5 处；每条对照同时含「可以对照」与「必须验证」两句中文（[P3] §6 P1-1）。

---

## 5. 科学复习在页面上该长什么样

### 5.1 用户看到的（人话，不能出现算法黑话）

```
┌─ 今日复习（先自己想，别翻上面的词卡）─────────────┐
│ 今天要回忆 5 个词：                                  │
│  1. 私        第 1 天学的，上次回忆是第 2 天，隔了 2 天   │
│  2. さん      第 1 天学的，上次回忆是第 3 天，隔了 3 天   │
│  3. 学生      第 1 天学的，上次回忆是第 3 天，隔了 3 天   │
│  4. です      第 2 天学的，上次回忆是第 5 天，隔了 5 天   │
│  5. こんにちは 第 1 天学的，上次回忆是第 6 天，隔了 6 天  │
│                                                      │
│ 每个词：先遮住中文 → 心里想意思 → 点「看答案」→          │
│         选【记住了 / 模糊 / 忘了】→ 页面告诉你          │
│         「这个词大约 12 月 3 日再来」。                  │
│ 为什么是今天：这几个词到了该回忆的时间，趁还没忘先想一遍。   │
└──────────────────────────────────────────────────┘
```
**禁止出现**：`FSRS`、`到期项`、`排期`、`review_count: 12`、`stability / difficulty / due`、`desired_retention`（[P3] §6 P0-7）。日期写成「大约 12 月 3 日」或「大约 4 天后」，用「大约」二字，因为程序给的是估计值。

### 5.2 背后的程序（[P4] `scripts/learning.py` 真实读取，不臆造）

| 真实代码 | 作用 |
|---|---|
| `STAGES = ["unseen", "initial_understanding", "hinted_recall", "independent_recall", "delayed_recall", "transfer"]` | 六段状态；其中 `unseen` 是「未学」，**递进的五个学习阶段**是 `initial_understanding`（初次理解）→ `hinted_recall`（提示答对）→ `independent_recall`（独立回忆）→ `delayed_recall`（延迟回忆）→ `transfer`（新语境迁移）。[P2] §3 P8 说的「五阶段门控」即这五级。 |
| `MASTERY_THRESHOLD = 0.85`、`DELAY_MIN_DAYS = 2`、`TRANSFER_MIN_DELAYED = 3`、`TRANSFER_MIN_CONTEXTS = 2`、`TRANSFER_MIN_SPAN_DAYS = 7` | 掌握条件：到 `transfer` 且 `rolling_accuracy >= 0.85`；一次答对绝不算掌握。 |
| `_update_mastery()` | 按 `correct` / `hinted` / 跨度天数 / 语境数推进阶段；`first exposure` 最多到「初次理解」；答错且连续 2 次或 `forgetting` 会**退回** `hinted_recall` 并清 `mastered`。 |
| `scheduler()` → `Scheduler()`（官方 py-fsrs 6.3.1, MIT），`s.enable_fuzzing = False` | 确定性排期，可复现、可测试；不自造记忆公式（[P2] §1）。 |
| `_fsrs_review()` → `s.review_card(card, Rating(rating), at)` | 产出 `due / stability / difficulty / state / step`，写入 `fsrs_cards`。 |
| `due_queue(conn)` → `SELECT * FROM fsrs_cards WHERE due<=? ORDER BY due LIMIT ?` | 「今天该复习哪几个词」由这里给出，**页面不自己挑词**。 |
| `record_attempt()` 内 `rating = (1 if not correct else 2 if hinted else 4 if st["stage"]=="transfer" else 3)` | 三档按钮到 FSRS Rating 的真实映射，见下表。 |
| `review_tasks(knowledge_id, day, due, reason, remedy, status)`、`REMEDY` 9 类 | 答错时按 `error_type` 给不同补救（`particle` → 助词填空 + 场景替换；`kanji_reading` → 音读训读对照等）。 |
| `grade_open()` | 开放题 `correct=None` 挂起等 AI 判分，不自动判对、不推进掌握。 |

### 5.3 映射表：用户动作 → 程序 → 页面不做的事

| 学员在页面上做的 | 页面收集什么 | 交给程序什么（[P4] 真实） | **页面绝对不做** |
|---|---|---|---|
| 看到「今天回忆这 5 个词」 | 只读展示 | `due_queue(conn)` 取 `fsrs_cards.due <= now ORDER BY due LIMIT 50` | 不算 `due`、不写死「1→2→4→7 天」 |
| 「先遮住中文回忆」 | 记录「无提示」 | 对应 `hinted=False` → 五阶段的 `independent_recall` | 不给提示、不先翻答案 |
| 点「看答案」 | — | 对答案后由 `record_attempt` 判分 | 不把「认出答案」记成回忆成功 |
| 选 **忘了** | `rating=1`、答错 | `Rating(1)`（Again）→ 缩短间隔；`infer_error_type` 归 `forgetting` → `REMEDY["forgetting"]` 缩短间隔重排 + 无提示主动回忆卡 | 不自己定几天后再来 |
| 选 **模糊**（看了提示才想起） | `rating=2`、`hinted=True` | `Rating(2)`（Hard）+ `hinted_count` → `hinted_recall` | 不把「模糊」当成「记住了」 |
| 选 **记住了**（独立答对） | `rating=3`；已到 `transfer` 则 `4` | `Rating(3)`（Good）/ `Rating(4)`（Easy），`independent_count` + 条件满足则 `delayed_recall` / `transfer` | **不判 `mastered`**、不生成「正确率」「掌握度」 |
| 看到「下次大约 12 月 3 日」 | 只读展示 | `Scheduler.review_card` 产出的 `due`（`desired_retention=0.9`、`enable_fuzzing=False`） | 不换算、不四舍五入成「掌握进度」 |
| 中文三档自评「还不行 / 会了 / 很熟」 | 独立 `self_assessed` 字段 | 不写进 `correct`（[P3] §6 P0-9：现网 `app.js:887-891` 把「达成」直接写成 `correct=true`，须拆开） | 不用「已答 0/8 题」定义学员 |
| 点「把今天的作答存回 WorkBuddy」 | 生成回传码（`NH80R1`） | 本地 `import-web-result` 校验去重 → 写 SQLite → 触发 FSRS 排期 | **网页不写状态、不发送学习数据、不假装已掌握**（[P3] §7 第 3/4 条，保留） |

> **一句话**：页面是「展示层 + 采集层」，**复习时间与掌握判定是 `scripts/learning.py` 的确定性职责**（[P2] §8 第 7 条「AI 不是权威：复习时间、检索、统计、持久化全部由程序决定」）。

### 5.4 Day 1 / Day 2 复习清单写法示例

**Day 1（首日，全是新词）**——[P5] `viz.review_count: 0`、`curriculum/day-001.md:34-35`「需复习的旧知识：无」：
```
今天复习：0 个词（第一天全是新内容，不用复习）
今天新学 6 个词 + 1 条句型 + 3 个汉字，先不用管复习。
明天会开始带你回忆今天这几个词：私 / さん / こんにちは / 学生 / です / はじめまして。
```
**Day 2 起（示意，具体哪天、哪几个词由程序给，页面只显示结果、不编造）**：
```
今天复习 5 个词（都是你这几天学过的）：
  私（第 1 天学，隔 1 天）／さん（第 1 天学，隔 1 天）／こんにちは（第 1 天学，隔 1 天）
  学生（第 1 天学，隔 1 天）／です（第 2 天学，今天第一次回忆）
为什么是今天：刚学过的东西隔一天最容易忘，趁还没忘先想一遍，比忘了再重学省时间。
怎么复习：遮住中文 → 心里想 → 点开对答案 → 选 记住了/模糊/忘了。
下次大约哪天：每个词选完当场告诉你（由程序算，页面只显示）。
```
> 注：上表的「隔 1 天 / 下次哪天」是**展示格式示例**，不是页面硬编码的间隔；真实 `due` 来自 `fsrs_cards`（[P4]）。项目框架 [P2] §3 P8 的「延迟 ≥7 天、≥3 次、≥2 语境」是**掌握门控**条件，不是复习间隔，页面不要把它写成「每 7 天复习一次」。

---

## 6. Day 1 示范课全文（可直接喂给页面）

> §6.0 说明与项目现有数据的关系：**本示范课是「内容规格样例」，不修改任何文件**。[P5] `web/data/day-001.json` 现有 6 词为 `私 / さん / こんにちは / おはようございます / ありがとうございます / すみません`、语法 `N は N です`、汉字 `日 / 月 / 火`、8 道题、2 段素材。本示范课沿用其中 `私 / さん / こんにちは / 日 / 月 / 火` 与语法 `N は N です`、素材 `朝のあいさつ` / `自己紹介`；按任务要求把词表补成 `私 / さん / こんにちは / 学生 / です / はじめまして`（含 `学生`、`です`），并给出**字段齐全的写法**与**由易到难的 5 道题**（含参考答案与解析）。页面改造时应同步补齐词表字段，本次不改动任何 JSON。
> 官方句型核对：`N は N です` 与 Irodori Starter `Lesson 3 Nice to meet you.` 的 `Grammar Notes ➊ Nです / N1 はN2 です / 私はマルシアです。` 一致（[S6]）；课序不同是 [P2] §1 有意为之。

### 6.0 今日目标（人话，不是 Can-do 黑话）

> **学完这课，你能用日语说：早上好、初次见面、我是学生。**
> 今天不考试，先把这 3 句话听熟、读准、能自己说出来。

### 6.1 今天要会的 3 句话（首屏第一屏，不折叠、不翻面）

| # | 日文（原文） | 假名读音 | 中文 | 听 |
|---|---|---|---|---|
| 1 | おはようございます。 | おはようございます | 早上好（对老师、同事、不太熟的人说的礼貌说法） | 🔊 |
| 2 | はじめまして。 | はじめまして | 初次见面（第一次见人时先说这句，只说一次） | 🔊 |
| 3 | 私は学生です。 | わたしはがくせいです | 我是学生 | 🔊 |

**逐词（挂在第 3 句下面）**：
`私（わたし）= 我`　`は = 提示主题，读 wa 不读 ha`　`学生（がくせい）= 学生`　`です = 礼貌体的「是」`

> 罗马字（入口阶段给，依据 [S11] Genki 前两课并记罗马字）：`ohayō gozaimasu` / `hajimemashite` / `watashi wa gakusei desu`。

### 6.2 今日 6 个词（卡片常显，字段齐全）

---
**① 私**
- 假名：**わたし**　罗马字：`watashi`
- 音读/训读提示：`わたし` 是训读；「私」作汉字词时音读 **シ**（例：私立 しりつ／私鉄 してつ）
- 词性：代名词（人称代名词）
- 中文义：我
- 例句 1：私は学生です。／ わたしはがくせいです ／ 我是学生。
- 例句 2：私はリンです。／ わたしはリンです ／ 我是小林。
- 常见搭配：`私＋は`（提示主题）／`私の`（我的）／更正式的「我」说 `わたくし`
- ⚠ 中日同形异义：**中文「私」读 sī，意思是「私人、私自」；日语「私」是「我」。字形一样、意思不同，别按中文猜。**
- 韩语对照：`私 ≈ 저 / 나`。**必须验证**：日语「私」不分谦让/平称，韩语 `저`（谦让，对长辈）与 `나`（平称，对朋友）要分场合。
- 🔊 听这个词
---
**② さん**
- 假名：**さん**　罗马字：`san`
- 音读/训读提示：`さん` 是音读（サン），作敬称时一般写假名
- 词性：接尾辞（敬称，粘在别人姓名后）
- 中文义：…先生／…小姐／…同学（接在名字后面表示礼貌）
- 例句 1：リンさん、こんにちは。／ リンさん、こんにちは ／ 小林，你好。
- 例句 2：リンさんは学生です。／ リンさんはがくせいです ／ 小林是学生。
- 常见搭配：`姓名＋さん`（田中さん／リンさん）；**不能接在自己名字后**；不说「先生さん」（先生 本身就是敬称）；对小孩用 `ちゃん / くん`
- ⚠ 中日同形异义：中文「先生／小姐」是能独立用的词，日语 `さん` **必须粘在人名后面**，不能单独喊；中文可以自称「我是李先生」，日语**绝不能给自己加 さん**。
- 韩语对照：`さん ≈ 씨`（都接在名字后）。**必须验证**：韩语 `씨` 前面通常接全名或名字（`김민수 씨`），日语 `さん` 多接姓（`田中さん`）；两边都不能用于自己。
- 🔊 听这个词
---
**③ こんにちは**
- 假名：**こんにちは**　罗马字：`konnichiwa`（注意最后是 wa，不是 ha）
- 音读/训读提示：原写作「今日は」，其中 `にち` 是「日」的音读 **ニチ**
- 词性：感叹词（寒暄语）
- 中文义：你好／日安（白天用的问候，大约上午十点到傍晚）
- 例句 1：こんにちは、リンさん。／ こんにちは、リンさん ／ 你好，小林。
- 例句 2：こんにちは。お元気ですか。／ こんにちは。おげんきですか ／ 你好，您好吗？（`お元気ですか` 今天只要求听懂，见 §6.5 注释）
- 常见搭配：早上用 `おはようございます`，晚上用 `こんばんは`；`こんにちは` **不是**「今天」的意思
- ⚠ 中日同形异义 / 假名陷阱：**最后一个假名写作「は」，做助词和在这个寒暄语里都读 wa，不读 ha**；「こんにちは」是固定寒暄语，不能按字面「今日は」直译成「今天…」。
- 韩语对照：`こんにちは ≈ 안녕하세요`。**必须验证**：韩语 `안녕하세요` 早晚都能用，日语分 `おはようございます / こんにちは / こんばんは` 三段，不能一天到晚只说一句。
- 🔊 听这个词
---
**④ 学生**
- 假名：**がくせい**　罗马字：`gakusei`
- 音读/训读提示：「学」**ガク**、「生」**セイ**，都是**音读**（汉字词），不能按中文 xuésheng 读
- 词性：名词
- 中文义：学生
- 例句 1：私は学生です。／ わたしはがくせいです ／ 我是学生。
- 例句 2：リンさんは学生です。／ リンさんはがくせいです ／ 小林是学生。
- 常见搭配：`学生＋です`／大学生（だいがくせい）／留学生（りゅうがくせい）／学校（がっこう）
- ⚠ 中日同形异义：**意思大致相同，但日语「学生」多指大学生、专科生；中小学生一般说「生徒（せいと）」「児童（じどう）」**。而且读音 `がくせい` 与中文完全不同，看到汉字别读成中文。
- 韩语对照：`学生 がくせい ≈ 학생`。**必须验证**：`がくせい` ≠ `haksaeng`（读音不同）；但词义在这里确实一致，是「可以对照」的好例子——**音近不等于音同，也不保证别的汉字词义同**（见 §4.5）。
- 🔊 听这个词
---
**⑤ です**
- 假名：**です**　罗马字：`desu`
- 音读/训读提示：假名词，无汉字
- 词性：助动词（断定助动词 `だ` 的礼貌形，也可理解为「礼貌体句末词」）
- 中文义：「是」（礼貌说法）。中文的「是」不分礼貌/简体，日语分
- 例句 1：私は学生です。／ わたしはがくせいです ／ 我是学生（礼貌）。
- 例句 2：今日はいい天気です。／ きょうはいいてんきです ／ 今天天气好。
- 常见搭配：`名词＋です`；简体 `だ`（朋友之间）；过去 `でした`；疑问 `ですか`、否定 `ではありません`（**今天不教，只预告**）
- ⚠ 中日同形异义：中文「是」只有一个，日语 `です / だ / である` 要按场合选；第一次见面、对不熟的人用 `だ` 会失礼。
- 韩语对照：`です ≈ 입니다 / 이에요`。**必须验证**：韩语礼貌体分 `입니다`（正式）/`이에요`（日常）/`야`（平语）三级，日语主要 `です`（礼貌）vs `だ`（简体）；日常对话翻成 `이에요` 更自然，别一律写 `입니다`。
- 🔊 听这个词
---
**⑥ はじめまして**
- 假名：**はじめまして**　罗马字：`hajimemashite`
- 音读/训读提示：来自「初めまして」，「初」常见音读 **ショ**（初級 しょきゅう）、训读 **はじ**（初め はじめ）；`まして` 是 `ます` 的连用形＋て。**这个词整体记成一句寒暄语即可，不必拆字**
- 词性：感叹词（寒暄语）
- 中文义：初次见面
- 例句 1：はじめまして。私はリンです。／ はじめまして。わたしはリンです ／ 初次见面，我是小林。
- 例句 2：はじめまして。よろしくお願いします。／ はじめまして。よろしくおねがいします ／ 初次见面，请多关照。
- 常见搭配：`はじめまして → 自报姓名 → よろしくお願いします`（三连，第一次见面的固定流程）
- ⚠ 中日同形异义 / 用法陷阱：**只在第一次见面说一次**，不能当「你好」天天说；字面虽来自「初次」，但现在是固定寒暄语，别逐字翻。
- 韩语对照：`はじめまして ≈ 처음 뵙겠습니다 / 만나서 반갑습니다`。**必须验证**：日语是「初次见面」的陈述，韩语常用「拜见/很高兴见到您」的表达，字面不同，不能直译。
- 🔊 听这个词
---

### 6.3 今日 3 个汉字（含音读训读与中文陷阱，不要求抄写）

> 三个字共同说明（每卡都要有）：**✅ 不要求机械抄写**——会认、会读、能在词里读出来即可（依据 [S5] `Kanji Words ➌ You do not have to be able to write the kanji by hand`、[S3] Q15「汉字不孤立教，放在活动的词里学」）。

**① 日**
- 音读：**ニチ / ジツ**　训读：**ひ / か**
- 例词：日本（にほん／にっぽん）日本｜日曜日（にちようび）星期日｜三日（みっか）三号、三天｜今日（きょう）今天
- ⚠ 中文母语者陷阱：中文「日」只读 rì，日语随词变成 `にち / じつ / ひ / か / きょう`，**不能按中文音类推**；「日曜日」里的「日」指星期日，中文「日」没有这个用法。
- 韩语汉字词提示（仅参考）：일본 日本、일요일 日曜日 —— 读音各自不同。
- ✅ 不要求抄写

**② 月**
- 音读：**ゲツ / ガツ**　训读：**つき**
- 例词：月曜日（げつようび）星期一｜一月（いちがつ）一月｜月（つき）月亮｜今月（こんげつ）这个月
- ⚠ 中文母语者陷阱：中文读 yuè；日语单说「月亮」读 `つき`，说「月份」读 `がつ`（一月 いちがつ），说「星期／月份名」读 `げつ`（月曜日、今月）。**一看到「月」就念 げつ 是错的**。
- 韩语汉字词提示：월요일 月曜日、일월 一月。
- ✅ 不要求抄写

**③ 火**
- 音读：**カ**　训读：**ひ**
- 例词：火曜日（かようび）星期二｜火事（かじ）火灾｜火（ひ）火
- ⚠ 中文母语者陷阱：中文读 huǒ、意思是「火焰」；日语「火」还因「七曜」（日月火水木金土）借指**星期二**（火曜日），中文「火」没有「星期」的意思——**看到「火曜日」别理解成「着火的日子」**。
- 韩语汉字词提示：화요일 火曜日（这里日韩一致、中文不同）。
- ✅ 不要求抄写

### 6.4 今日 1 条语法：N は N です

**【意思（中文白话）】**
「A 是 B」。`は` 把 A 立成「我们接下来要聊的话题」，`です` 在句子最后礼貌地说「是 B」。中文说「我是学生」中间不用加东西，日语必须在「我」后面放一个 `は`。

**【接续公式】**
```
名词 ＋ は ＋ 名词 ＋ です
```
中文注释：`名词` = 人、东西、地方、身份的名字（私、学生、リン、日本…）；`は` 是助词，**读 wa 不读 ha**；`です` 是礼貌体句末，不能换成简体 `だ`（对不熟的人失礼）。
> 官方对照：Irodori Starter Lesson 3 `Grammar Notes ➊ Nです / N1 はN2 です / 私はマルシアです。`（[S6]）。

**【3 个例句（带假名、中文、逐词）】**
1. 私は学生です。／ **わたしはがくせいです** ／ 我是学生。
   逐词：`私（わたし）=我`　`は=主题（读 wa）`　`学生（がくせい）=学生`　`です=是（礼貌）`
2. リンさんは学生です。／ **リンさんはがくせいです** ／ 小林是学生。
   逐词：`リン=人名`　`さん=接在别人名字后的敬称`　`は=主题`　`学生`　`です`
3. 今日はいい天気です。／ **きょうはいいてんきです** ／ 今天天气好。
   逐词：`今日（きょう）=今天`　`は=主题（读 wa）`　`いい=好`　`天気（てんき）=天气`　`です`
   （这句来自 [P5] M0001；`今日 / 天気` 是超纲词，这里给假名与中文，只要求听懂）

**【使用场景】**
第一次见面做自我介绍、向老师或上级说明自己的身份/职业/国籍、介绍身边的人。属于**礼貌场合**的说法。

**【易错点（中文，必须常显在讲解区，不要藏在提交后的 rationale 里）】**
1. **`は` 做助词读 wa，不读 ha**；中文「我」后面不用加任何词，中国学习者最容易把 `は` 整个漏掉，写成「私学生です」。
2. **不能给自己加 `さん`**：中文可以说「我是李先生」，日语 `× 私は李さんです` → `○ 私は李です`。
3. **`です` 别随便换成 `だ`**：`だ` 是简体，第一次见面、对不熟的人用会失礼；朋友之间才可以用，甚至可以省略。
4. **`は` 是「主题」不是「主语」**：主题是「我们接下来要谈的那个东西」，和 `が`（主语/新信息）不一样，今天先记住「`は` 提示话题」，别急着把 `は` 当成 `が`。
> 第 1 条与项目 [P5] `Q0181.rationale` 原文一致：「主题用 は（读 wa）；中文「我」后无对应助词，中国学习者常漏填或误用 が。」现网只在提交该题后才显示这条（[P3] §6 P1-4），改造要**前置到语法卡**。

**【与相近语法的区别】**
| 对比 | 什么时候用 | 例子 |
|---|---|---|
| `N は N です` | 接着话题做说明（「要说我的话…是学生」） | 私は学生です。／ わたしはがくせいです |
| `N が N です` | 回答「是谁/哪个」，强调「是我、不是别人」 | 私が学生です。／ わたしががくせいです |
| `N です`（省掉 `は`） | 话题已在问句里，直接报名字 | リンです。／ リンです |
| `～ですか`（疑问）、`～ではありません`（否定） | **今天不教，明天学** | 学生ですか。／ がくせいですか |

**【韩语对照（可对照，必须标差异）】**
```
【可以对照】は ≈ 은/는（话题），が ≈ 이/가（主语/新信息），です ≈ 입니다/이에요。
            私は学生です。≒ 저는 학생입니다. ／ 私が学生です。≒ 제가 학생입니다.
            SOV 语序、助词后置，和韩语一样，可以整句平移。
【必须验证】① は 是「主题」不是「主语」，不能等同 が；「象は鼻が長い」里 は 和 が 分工不同。
            ② は 写 は 读 wa、不随词变形；韩语 은/는 要按收音选，日语没有这一步。
            ③ が 不总是 이/가：「コーヒーが好き」的 が 对应韩语 을/를。
            ④ です ≈ 입니다 只是「都礼貌」的近似；韩语日常更常说 이에요，입니다 偏正式。
【一句话】结构可以借，词不能猜。
```
🔊 听 3 个例句

### 6.5 例句 / 会话（2 段，独立成区；原文 ≠ 读音）

---
**会话 1 · 朝のあいさつ（早上的寒暄）** —— 原文来自 [P5] M0001
- **日文原文**：おはようございます。今日はいい天気です。お元気ですか。
- **假名读音**：おはようございます。きょうはいいてんきです。おげんきですか。
- **中文**：早上好。今天天气真好。您好吗？
- **逐句**
  1. `おはようございます。` / おはようございます / 早上好（礼貌）
  2. `今日はいい天気です。` / きょうはいいてんきです / 今天天气好。（`今日 きょう`=今天；`は`=wa；`天気 てんき`=天气）
  3. `お元気ですか。` / おげんきですか / 您好吗？（`お`=礼貌前缀；`元気 げんき`=精神、健康；`ですか` 是 `です` 的疑问形，**今天只要求听懂，不要求会用**）
- **生词注释**：今日（きょう）今天｜天気（てんき）天气｜元気（げんき）精神/健康｜お〜 礼貌前缀
- 🔊 听整段 ／ 🔊 逐句听
---
**会话 2 · 自己紹介（初次见面）** —— 原文来自 [P5] M0002
- **日文原文**：はじめまして。私はリンです。学生です。日本語を勉強します。よろしくお願いします。
- **假名读音**：はじめまして。わたしはリンです。がくせいです。にほんごをべんきょうします。よろしくおねがいします。
- **中文**：初次见面。我是小林。是学生。我学日语。请多关照。
- **逐句**
  1. `はじめまして。` / はじめまして / 初次见面
  2. `私はリンです。` / わたしはリンです / 我是小林
  3. `学生です。` / がくせいです /（我）是学生。**这里省略了 `私は`**，日语里话题清楚时常省
  4. `日本語を勉強します。` / にほんごをべんきょうします / 我学日语。（`日本語 にほんご`=日语；`を`=宾语助词，读 o；`勉強 べんきょう`=学习 ⚠ 不是中文「勉强」；`します`=做。**本句今天只要求听懂**）
  5. `よろしくお願いします。` / よろしくおねがいします / 请多关照（初次见面的固定说法）
- **生词注释**：日本語（にほんご）日语｜勉強（べんきょう）学习 ⚠ 中日同形异义｜よろしくお願いします（よろしくおねがいします）请多关照
- 🔊 听整段 ／ 🔊 逐句听
---
> **验收断言**：两段的「假名读音」串与「日文原文」串**不相等**（`きょうはいいてんきです` ≠ `今日はいい天気です`）。这一条专门修 [P3] §2.5 指出的现网 bug。

### 6.6 练一练（5 道，由易到难；含参考答案与解析）

> 排序依据：听辨 → 填助词 → 填句末 → 语用改错 → 独立产出（对应 [S5] ➎「听示范 → 跟读 → 换词 → 自由说」的坡度，也修正 [P3] 手机端「第一题就是开放产出题」的死局）。**先作答后揭示**，反馈为中文讲解，开放题给示范句。

---
**第 1 题（难度 1 · 听辨）** 🔊 播放 `こんにちは。`
问：刚才那句是什么意思？
- A 早上好　B 你好（白天）　C 晚上好　D 谢谢
- **参考答案**：`B`
- **解析**：`こんにちは` 是**白天**用的「你好」。早上要说 `おはようございます`，晚上是 `こんばんは`，「谢谢」是 `ありがとうございます`。顺便记住：它最后一个假名写作 `は`，**读 wa 不读 ha**。
---
**第 2 题（难度 2 · 填助词）**
补全：`私 ___ 学生です。`
- **参考答案**：`は`（读 wa）
- **解析**：中文说「我是学生」，「我」后面不加东西；日语必须在「私」后面放一个 `は`，意思是「接下来我要说的是『我』这件事」。**漏掉 `は` 写成「私学生です」是中国学习者最常见的错**。选 `が` 也不对：`が` 是用来回答「谁是学生？」、强调「是我不是别人」的，这里是普通自我介绍。
- 韩语对照提示：`私は` ≒ `저는`，都是话题助词后置；但韩语 `는` 要按收音选，日语 `は` 不变形。
---
**第 3 题（难度 2 · 填句末）**
补全：`私は学生 ___ 。`
- **参考答案**：`です`
- **解析**：句末的 `です` 相当于中文的「是」，但它是**礼貌体**。填 `だ` 意思一样却太随便，第一次见面、对老师或不熟的人说会失礼；`である` 更书面，日常对话不用。中文的「是」不分礼貌，所以这一格特别容易漏。
- 韩语对照提示：`です` ≒ `이에요 / 입니다`；注意韩语日常更常说 `이에요`，`입니다` 偏正式。
---
**第 4 题（难度 3 · 改错，考语用）**
改正这句自我介绍里的失礼说法：`私は李さんです。`
- **参考答案**：`私は李です。`（或简说 `李です。`）
- **解析**：`さん` 是贴在**别人**名字后面的敬称，相当于中文「先生/小姐」、韩语 `씨`，用来尊重对方。中文可以说「我是李先生」，**日语绝不能给自己加 `さん`**，否则听起来像在称自己为「先生」，很奇怪。想说自己的姓，直接 `李です`。
- 韩语对照提示：韩语一般也不会说 `저는 이 씨입니다` 来称自己，边界类似——**这条是可以对照的**；但 `さん` 多接姓、`씨` 多接全名，别混用。
---
**第 5 题（难度 4 · 独立产出 / 迁移）**
第一次见到日语老师，请用今天学的话写 2–3 句：先问候，再说自己是谁、是不是学生。**先自己写，写完再看示范。**
- **参考答案（示范句，不是唯一答案）**
  ```
  はじめまして。
  私はリンです。
  学生です。
  よろしくお願いします。
  ```
  假名：`はじめまして。／ わたしはリンです。／ がくせいです。／ よろしくおねがいします。`
  中文：初次见面。我是小林。是学生。请多关照。
- **解析（三点评分，中文写）**：① 有没有先问候（`はじめまして` 或 `こんにちは`）；② 有没有用 `〜は〜です` 报出姓名或身份；③ 有没有**不给自己的名字加 `さん`**、句末保持 `です`。
  **这题没有唯一答案**，把自己的真名写进去也对——这才叫「会用」，不是「背下来」。
  > 现网开放题只有「达成/未达成」自评、无示范句，且 `app.js:887-891` 把「达成」直接写成 `correct=true`（[P3] §2.5/§6 P0-8/P0-9）；改造要给示范句，自评写独立字段。
---

### 6.7 今日复习清单（Day 1 写法）

```
┌─ 今日复习 ─────────────────────────────────┐
│ 今天复习：0 个词（第一天全是新内容，不用复习）        │
│                                                │
│ 今天新学：6 个词 · 1 条句型 · 3 个汉字              │
│   私 / さん / こんにちは / 学生 / です / はじめまして │
│   N は N です / 日・月・火                        │
│                                                │
│ 明天会开始带你回忆今天这几个词：                    │
│   先遮住中文 → 心里想 → 点开对答案 →              │
│   选【记住了 / 模糊 / 忘了】→ 告诉你下次大约哪天再来。│
│                                                │
│ 为什么第一天没有复习：还没学过，自然没有「该回忆」的。  │
│ （具体哪天复习、复习哪几个，由程序算好告诉你，本页不编）│
└────────────────────────────────────────────┘
```
**验收**：本区 `innerText` 不含 `FSRS / 到期项 / 排期 / review_count / due`；出现具体词表与「下次大约哪天」（[P3] §6 P0-7）。页面只展示与收集，`due` 来自 [P4] `due_queue` / `fsrs_cards`。

### 6.8 日语自检表（逐条核对，诚实标注依据）

| # | 形式 | 读音 | 义 / 用法 | 核对依据 |
|---|---|---|---|---|
| 1 | 私 | わたし | 我；代名词；音读 シ（私立 しりつ） | [P5] `V0001`；通用词典知识；[S6] Lesson 3 `Kanji Words 名前 国 私` |
| 2 | さん | さん | 敬称接尾辞，**不能用于自己** | [P5] `V0003`、`Q0185.rationale`；[S6] `Tips: How to call someone` |
| 3 | こんにちは | こんにちは（は→wa） | 白天问候 | [P5] `V0004`；[S6] Lesson 1 Activity 1 `こんにちは / 01 Can exchange greetings` |
| 4 | 学生 | がくせい | 学生；「学」ガク「生」セイ 音读 | [P5] 语法例句 `私は学生です。`；[S6] 汉字词体系 |
| 5 | です | です | `だ` 的礼貌形 | [P5] `Q0182`；[S6] `Grammar Notes ➊ Nです` |
| 6 | はじめまして | はじめまして | 初次见面 | [P5] `Q0009` / M0002；[S6] Lesson 3 Activity 1 `はじめまして / 08 Can give a simple self-introduction` |
| 7 | おはようございます | おはようございます | 早上好（礼貌） | [P5] `V0006` / `Q0183`；[S6] Lesson 1 `Good morning!` |
| 8 | 私は学生です | わたしはがくせいです | 我是学生 | [P5] `G0001.example`；[S6] `N1 はN2 です / 私はマルシアです。`（句型一致） |
| 9 | 今日はいい天気です | きょうはいいてんきです | 今天天气好；`今日` 特殊读 きょう | [P5] M0001（原文与 audio_text 相同，本示范课**补出不同假名读音**） |
| 10 | お元気ですか | おげんきですか | 您好吗；`ですか` 为 `です` 疑问形 | [P5] M0001；[S5] 汉字练习真实例句 `お元気ですか？` |
| 11 | はじめまして。私はリンです。学生です。日本語を勉強します。よろしくお願いします。 | はじめまして。わたしはリンです。がくせいです。にほんごをべんきょうします。よろしくおねがいします。 | 初次见面/我是小林/是学生/学日语/请多关照 | [P5] M0002（原文）；假名读音、中文、生词注释为本示范课补齐 |
| 12 | 日 ニチ・ジツ / ひ・か；月 ゲツ・ガツ / つき；火 カ / ひ | 日本 にほん、日曜日 にちようび、三日 みっか、月曜日 げつようび、一月 いちがつ、火曜日 かようび、火事 かじ | 音读/训读与例词 | [P5] `K0001–K0003.onyomi/kunyomi/zh_trap`；[S6] 七曜体系（Lesson 3 `Japanese era names`） |
| 13 | 勉強 べんきょう / 大丈夫 だいじょうぶ / 手紙 てがみ / 汽車 きしゃ | — | 学习 / 没问题 / 信 / 火车 | 中日同形异义通用教学知识；[P2] P4 `zh_trap` / `error_correct`；[P3] §7 第 9 条 |
| 14 | 韩语对照（저는 학생입니다 / 제가 학생입니다 / 밥을 먹어요 / 교실에서 공부해요 / 버스로 가요 / 이에요·입니다 / 학생·도서관·기차·대장부） | — | 见 §4 | **本项目原创教学讲解模板，非引用某本教材**；日语/韩语形式逐条自核 |

**诚实标注**：以上日语形式与 [P5] 项目种子一致；[P2] §8 已明确「877 条种子标 `S000 项目原创整理`，**未逐条对照 JMdict / KANJIDIC**，14 条 `needs_review`」。本示范课沿用该精度，**未把项目种子当成已对照词典的权威数据**；音调（アクセント）因无权威数据源，全部留空，未编造数字。韩语对照为教学编排，不是「已核实的教材原文」。

---

## 7. 给页面改造的 10 条硬要求（可验收）

> 与 [P3] §6 P0/P1 呼应，但**新增**本次教材调研带来的「原文≠读音、汉字不抄写、韩语对照边界、复习人话化、先学后练」等要求。每条给「必须 + 验收方法」。

| # | 硬要求（必须） | 验收方法 |
|---|---|---|
| **1** | **首屏先出「今天要会的 3 句话」**：默认展开、位于 `h1` 下第一屏内，每句含日文原文 + 假名 + 中文 + 🔊 听 + 逐词拆解；一句话白话目标（不写「本日 Can-do／能力侧重 listening/reading」）。依据 [S5] `➊Can-do objective`、[S11] `課の最初に…できるようになること`。 | 1440×900 与 390×844 打开 `day-001.html`，`document.body.innerText` 前 400 字内必须含 ≥1 句日文 + 其假名 + 中文，且截图首屏可见「听」按钮；不滚动、不点折叠即可读到。 |
| **2** | **单词卡常显（不折叠、不翻面），字段齐全**：书写 / 假名 / 罗马字 / 汉字词音读训读提示 / **词性（中文）** / 中文义 / 1–2 例句（带假名+中文）/ 常见搭配 / 中日同形异义 / 韩语对照 / 🔊。ID、JLPT、难度移出学习区（[P3] P2-4）。含汉字的词**先显示假名+听再显示中文义**。依据 [S11] `単語 Vocabulary`、[S4] `WORD (without Furigana)`、[S5] `ことばの準備`。 | 词汇区不在 `details:not([open])` 内；每张卡 `innerText` 同时命中「假名」「罗马字」「词性」「例句」「中文」「搭配」「听」；对 `私` 卡断言含 `わたし`、`watashi`、代名词、含 `私` 的例句及其中文、`音读 シ`。 |
| **3** | **语法卡用中文讲全 7 项**：意思 / 接续（**中文注释，不得只写「名詞＋は＋名詞＋です」**）/ 2–3 例句（假名+中文+逐词）/ 使用场景 / **易错点 ≥3 条中文** / 与相近语法的区别 / 韩语对照（含「可以对照」与「必须验证」）。把 [P5] `Q0181.rationale` 等易错中文**前置到语法卡**，提交后仍能再看。依据 [S5] `Grammar Notes: form, meaning, usage + comparisons to similar expressions`、[S11] `なるべく専門的な用語を使わず`。 | 语法区 `innerText` 含「易错」「注意」「区别」，≥3 条中文差异句；`接续` 附「名词」中文注释；例句同时含假名串与中文串；含韩文字符。 |
| **4** | **例句独立成区，且「日文原文」与「假名读音」是两个不同节点**：每段给原文 / 假名读音 / 中文 / 逐句拆解 / 生词注释 / 🔊；素材逐句假名 + 中文，超纲词（お元気ですか、日本語、勉強…）给中文注释。依据 [S5] `Listening script(s)`、[S8] `Translations of Listening Scripts...`、[S11] 全文振假名、[S4] 带/不带 Furigana 两版。 | 断言 `读音节点.textContent !== 原文节点.textContent`（对 `今日はいい天気です` → `きょうはいいてんきです` 必须成立）；删除/改写 `app.js:602` / `app.js:955` 把 `audio_text` 当读音的逻辑；不再出现「文本读音（TTS 降级/对照）= 原文」。 |
| **5** | **每个词 / 每句 / 每段素材旁有明确「听」入口，且假名常显**：不依赖 `no-ja-tts`，也不因「有 ja-JP 语音」用 `app.css:182` 隐藏假名；无日语语音时给白话提示「这台设备没有日语发音，请照着假名跟读」；首屏有中文指引「点小喇叭听这句」。依据 [S5] 每步都 `Listen to the audio`、[S11] 会話音声 2 回、[S4] 词表配 MP3。 | 覆盖 `app.css:182-183` 后，模拟「有/无 ja-JP」两种状态截图，词汇卡正面均显示假名；点任一「听」有 TTS 调用或明确降级提示；首屏前 300 字含「点小喇叭听这句」类中文指引。 |
| **6** | **汉字卡给音读（片假名）/ 训读（平假名）/ 例词（日文+假名+中文）/ 中文母语者陷阱，并明写「✅ 不要求机械抄写，会认会读会在词里读出来即可」**。保留并推广 [P5] `zh_trap` 到词汇/语法卡。依据 [S5] `Kanji Words ➌ You do not have to be able to write the kanji by hand`、[S3] Q15、[S11] `漢字表には、漢字の読み方、意味…熟語`。 | 每张汉字卡 `innerText` 含「音读」「训读」「不要求抄写」及 ≥2 个带假名与中文的例词；词汇区与语法区各 ≥1 段 ≥30 字中文讲解（非标签）。 |
| **7** | **韩语对照独立成块，每条同时给「可以对照」与「必须验证」**；覆盖 §4 的 6 组（は/が↔은/는·이/가、を↔을/를、に/で↔에/에서、です/ます↔입니다/ㅂ니다、SOV 与助词后置、汉字词音读↔韩语汉字词）；**中日同形异义（勉強 / 大丈夫 / 手紙 / 汽車）显式红色警示**；「结构可以借，词不能猜」写在醒目处。 | 语法区与词汇区各有「韩语对照」子块；全文韩文字符（가-힣）≥5 处；每条对照含「必须验证」中文差异句；4 个同形异义词各有 ⚠ 警示块且写全「中文里…／日语里…／别按中文猜」。 |
| **8** | **复习区写人话**：列出「今天具体复习哪几个词 + 首次学哪天 + 间隔几天 + 为什么是今天」；交互为「遮住中文回忆 → 点开对答案 → 记住了/模糊/忘了 → 下次大约哪天再来」；首日明写「今天复习 0 个词，6 个都是新词」。**不出现 `FSRS / 到期项 / 排期 / review_count / due` 等词**。页面只做展示与收集，`due` 与掌握判定由 `scripts/learning.py` 的 `due_queue` / `Scheduler.review_card` / `_update_mastery` 算（[P4]）。 | 复习区 `innerText` 含具体词表与「下次大约」；不含上述 5 个黑话；Day 2 起条目数 = 程序给出的到期数且每条可发音；三档分别写回 `rating=3(或4)/2/1` 与 `hinted`，自评写独立 `self_assessed` 字段而非 `correct`。 |
| **9** | **先学后练**：练习区排在所有内容卡之后；PC 题卡默认展开（或改非常显），手机保留一屏一题但提供「查看全部 / 回看上一题解析」；提交后**同屏立即**给「对/错 + 为什么（中文）+ 正确说法 + 🔊 再听一次」；**开放题必须给示范句**而非只有自评；反馈区不出现英文错误枚举（或收进「给系统」折叠并中文化）。依据 [S11] `練習の見出しの横に対応する文法の番号…必ず読んでから`、[S4] `Answer` 单独成册、[S5] `➏Can-do check`。 | 提交任一客观题后不滚动即可读到「解析」「参考答案」；开放题 DOM 含示范句节点；`innerText` 不含 `forgetting / meaning_confusion / particle / orthography` 等英文枚举（或置于折叠内并附中文）；`app.js:887-891` 自评「达成」不再写 `correct=true`。 |
| **10** | **系统元信息后置**：`diagnostic / FSRS / Can-do / focus / NH80R1 / 60 分钟时间块 / 80 天热力图 / P1–P6 / V·G·K·M ID / 难度 / SQLite / speechSynthesis / S000` 全部收进默认折叠的「关于本页」，或移到独立进度页；三张可视化图表不在首屏可视区。**同时保留** [P3] §7 的既有优点：零 CDN / 纯静态 `file://` 可开、Service Worker 降级、回传码与「状态真源在 SQLite」、不向服务器发送学习数据、TTS 降级不静默失败、双端适配、逐题即时判分、翻面卡留作复习模式、汉字 `zh_trap`、数据层已有字段。 | 取 `document.body.innerText` 前 3000 字符，断言上述 14 个关键词命中数为 0；`getBoundingClientRect().top > 900` 或位于折叠容器；页脚三条声明、`sw.js`、`NH80R1` 回传码机制仍在；`innerText` 不含「已答 0 / 8」定义学员。 |

---

## 8. 边界声明（本文件做了什么、没做什么）

**做了**：
- 真实访问并逐条记录 13 个官方 URL（含 2 个官方 PDF 用 `curl` + PyMuPDF 提取正文），阅读 5 个项目内文件；所有结论带出处 URL + 实际看到的原文片段/模块名。
- 产出：模块序列表、字段规格表、中文母语者+韩语背景讲解模板（6 组对照 + 边界）、科学复习页面形态（结合 [P4] 真实代码）、完整 Day 1 示范课、10 条硬要求。

**没做 / 明确未核实**：
1. **未修改任何脚本、HTML、JSON、课程、种子或其他文档**；只创建本文件 `research/textbook_lesson_pattern.md`。
2. `みんなの日本語` 的一课模块名、课名、页码：**未核实**（[S12] 404、[S13] 官网无结构信息；见 §1.2）。主流教材结论基于已完整核实的 [S11] Genki 与 [S5][S6] Irodori。
3. `marugoto/en/download/` 上 **Katsudoo / Rikai 的文字定义：本页未核实**（只有双线并列与素材类型表）；URL 里 `starter_a` / `starter_c` 的 `a`/`c` 含义未核实、未推断。
4. `irodori/en/starter/pdf.html` 上 **「会話/単語/文法/練習」作为独立下载 PDF：未在该页核实**（实际是每课一个整册 PDF）；一课内部模块名来自 [S5][S6] 教材正文/目录。
5. **未打开**任何教材课文 PDF 正文（`X_L01.pdf` 等只记录文件名与大小）、未打开 Genki actibookone 电子样书正文（**样页内部版式未核实**）、未下载任何 MP3/ZIP、未注册 Minato、未访问 JLPT `guideline/testsections.html`（其题型表引自 [P1] 项目内 2026-11-06 已核实记录，本轮未复访）。
6. **音调（アクセント）数字全部留空**：项目无权威音调数据源（[P2] §8：种子未逐条对照 JMdict/KANJIDIC），未编造 0/1/2 型。
7. **韩语对照与中文讲解为本项目原创教学编排**，不是「已核实的某本教材原文」；日语形式沿用 [P5] 项目种子精度，未伪称已对照词典。
8. 本文档**不承诺** JLPT 合格分数，不产出标准分换算（[P2] §2 诚实边界）；Day 1 示范课是「内容规格样例」，不是要写回 `web/data/day-001.json` 的数据（改造时才同步补齐字段）。
