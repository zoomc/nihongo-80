# v7 真人听力资源调研报告（N4/N3）

- 核验日期：**2026-11-08**（`generated` 同此）
- 项目：`/Users/mj/Documents/learn/jp/nihongo-80`，Cloudflare 公开部署的个人日语学习站（0 基础→N3，150 天，听力自 Day 47 起每周 3 次）
- 本轮性质：**只读调研 + 仅写两个输出文件**（`reports/v7_listening_sources.md`、`knowledge/resources_v7.json`）。未下载/转存任何第三方音频，未改动 `web/`、`scripts/`、`knowledge/resources.json`，未 git commit。
- 核验方式：`curl -I/-L` 取真实 HTTP 状态与重定向（GET 请求体一律丢弃到 `/dev/null`，音频文件只取响应头，不落盘）、`WebFetch` 读页面原文、iTunes Search API / Archive.org advancedsearch / Wikimedia Commons API 查真实 feed 与文件元信息。
- 现有资产：`web/audio/M0096–M0140.m4a`（45 个，Kokoro-82M `jf_alpha` 合成的原创文本语音，`web/audio/NOTICE.txt` 已完整署名，许可干净）**本轮不删、不替换**；它们是每日听力主线，真人听力只是**补充入口**。

---

## 〇、判定口径（先写清楚，便于审计）

用户硬约束：「不能有法律风险、不能有额外扣费」。本轮把 25 个候选分成三类，口径如下：

| embed | 判定标准 | 落地行为 |
|---|---|---|
| `inline` | **许可明文允许第三方网页嵌入 / 直链播放**，且有**实际验证过 200 的、真实存在的**可嵌入 URL | 页面内 `<audio src>` / `<iframe>` 直接播放；`embed_url` 必填且非编造 |
| `link` | 内容**官方免费公开发布**、页面与条款可实际访问、**无需登录 / 付费 / 地区限制**；许可为「版权保留 / personal use only / CC BY-NC-ND」等**不授权嵌入**，但「只放一个跳转链接」不构成复制或热链，风险与费用均为零 | 只渲染 `<a href="url" target="_blank" rel="noopener noreferrer">`，用户离开本站到原站听；`embed_url` 一律留空 |
| `none` | ① **许可无法核实**（站点无条款页、访问失败、需登录且条款在站外）；② **明文禁止再分发 / 热链 / 公开到网站**；③ **需付费 / 登录 / 有地区限制** | 不生成入口；`license` 写 `"待核实"` 或具体禁止原因，`embed_url` 留空 |

> 关键区分：「**版权保留但官方免费公开发布**」（JLPT 样题、Irodori、NHK Easy Japanese、播客 RSS）视为**许可性质可判定** → `link`；「**连能否合法公开放链接都不确定**」（Minato 需登录、TUFS 访问异常且无条款页）→ `none` + `"待核实"`。所有 `link` 类的 `license` 都写具体条款/事实，不写「待核实」。

---

## 一、现有 `knowledge/resources.json` 的核实与纠错

现有文件登记 5 条（`version:1, checked_at:2026-11-07`），总政策「外部资源仅链接官方站点；免费查看不代表可复制或再发布」**口径正确，应保留并强化**。逐条核实：

| id | 原记录 URL | 本轮 HTTP | 结论 |
|---|---|---|---|
| `jlpt-workbook` | `jlpt.jp/e/samples/sampleindex.html` | **200** | **描述有误，需纠正**。页面原文："The Official Practice Workbook published in 2012 and the Official Practice Workbook Vol.2 released in 2018 … are **sold by Bonjinsha**"。即该页指向**付费出版物**，页面本身不提供免费的听力 MP3 / 脚本下载。原记录写「官方免费提供试题、听力、答案与脚本」不成立。真正免费的听力 MP3 + 脚本 PDF 在 `sample09.html`（2009 改版前样题）。本轮拆成两条：`jlpt-workbook`（付费册，仅链接）+ `jlpt-n3-sample`（免费样题）。 |
| `jlpt-sample` | `jlpt.jp/e/samples/forlearners.html` | **200** | 页面仍活着，但它只是**入口说明页**（"Sample questions show the form of test items…"），本身无试题、无音频，指向 `sample09.html` 与 `sampleindex.html`。原 `license_url` 填 `https://www.jlpt.jp/e/samples/`（目录页，非条款页），已改为实际核验页。 |
| `irodori` | `irodori.jpf.go.jp/en/pre-intermediate/pdf.html` | **200** | 可用。条款判断**正确**：非 CC，是站点自定义 Terms of Use。本轮重读 `privacy.html` 原文确认：版权归国际交流基金/原作者；**仅限私用或学校/教育机构**；第 3 条自制教材公开须免费并注明来源；第 4 条禁止用于与本站点完全无关的新教材；禁止项含「Use This Site for **commercial purposes**」。未授权第三方嵌入或热链。 |
| `tadoku` | `tadoku.org/japanese/en/free-books-en/` | **200** | 可用。条款判断**正确且需补一句风险**：`note-en` 原文确认 **CC BY-NC-ND 4.0**，官方明确「**Absolutely yes!** Can I share links … give credit to NPO多言語多読」（允许分享链接）→ 适合 `link`；但同页明确禁止「**Make audio readings and publish them on websites**」「Create videos…」「Add translations, explanations, tests」→ **音频不得嵌入、不得改作**。ND 条款限制任何衍生。 |
| `nhk-easy` | `www3.nhk.or.jp/news/easy/` | **200 → 重定向到 `https://news.web.nhk/news/easy/`** | **判断过时，需纠正**。① 域名已迁移到 `news.web.nhk`；② 页面出现「ご利用意向の確認」同意门；③ 明确地区限制原文："NHK ONEは日本国内向けのサービスのため、**海外からの利用は一部制限されます**。文字情報は閲覧できますが、**動画は視聴できない場合があります**"；④ 主体是**简易新闻文字 + 振假名**，不是真人会话听力教材。按口径应改判 `embed:"none"`（地区限制），不再作为免费听力/阅读链接推荐。 |

另注：`research/source_registry_official.md`（2026-11-06）已详细核验过 8 个官方源，本轮对其中 JLPT/Irodori/Tadoku/NHK/Marugoto/Minato/Erin 重新取了 HTTP 状态与页面原文，结论一致处沿用，变化处以上表为准。

---

## 二、候选对比表（25 个源，含本轮实际访问结果）

HTTP 列格式：`状态码|Content-Type`，`→` 后为最终重定向 URL。`音频/字幕`列指页面是否确有真人音频与脚本/字幕。

### 2.1 可 `inline`（2 个）

| id | 源 | URL | 本轮 HTTP / 实测 | level | type | 音频/字幕 | 许可 | embed_url（已验证 200） |
|---|---|---|---|---|---|---|---|---|
| `commons-ja-pron` | Wikimedia Commons 日语发音/短句音频（`Category:Japanese_pronunciation`） | `https://commons.wikimedia.org/wiki/Category:Japanese_pronunciation` | 分类页 **200**；`File:Ja-pronunciation-practice5.ogg` → **Public domain**，直链 **200 `application/ogg`**；`Ja-arigato.oga` / `Ja-aisukurimu.ogg` → **CC BY-SA 3.0**，直链 **200**；`creativecommons.org/licenses/by-sa/3.0/` **200** | N5/N4 | listening | 真人单词/短句发音，无文字脚本（文件名即文本） | PD Mark 1.0 / CC BY-SA 3.0，明文允许复用与公开展示 | `https://upload.wikimedia.org/wikipedia/commons/4/49/Ja-pronunciation-practice5.ogg`（PD，实测 200 `application/ogg`） |
| `commons-ja-spokenwiki` | Wikimedia Commons 日语朗读维基百科（`Category:Spoken_Japanese_Wikipedia`） | `https://commons.wikimedia.org/wiki/Category:Spoken_Japanese_Wikipedia` | 分类页 **200**；`ウィキペディア日本語版 録音記事「藤村紀雄」…ogg` → **CC BY-SA 4.0**，直链 **200 `application/ogg`**；`creativecommons.org/licenses/by-sa/4.0/` **200** | N3 | listening | 真人朗读百科条目，文本即维基原文可作脚本 | CC BY-SA 4.0，明文允许复用与公开展示 | `https://upload.wikimedia.org/wikipedia/commons/9/95/%E3%82%A6%E3%82%A3%E3%82%AD%E3%83%9A%E3%83%87%E3%82%A3%E3%82%A2%E6%97%A5%E6%9C%AC%E8%AA%9E%E7%89%88_%E9%8C%B2%E9%9F%B3%E8%A8%98%E4%BA%8B%E3%80%8C%E8%97%A4%E6%9D%91%E7%B4%80%E9%9B%84%E3%80%8D20231201T233822%E7%89%88.ogg`（实测 200） |

> 依据：Wikimedia Commons 文件页明示 PD / CC BY-SA；`upload.wikimedia.org` 是 Commons 官方文件 CDN，CC 许可明文允许「复制、分发、公开表演/展示」，在第三方网页用 `<audio src>` 播放属许可范围内。4 条候选直链本轮逐条 `curl -I` 实测均 **200 `application/ogg`**，**不是编造**。

### 2.2 只能 `link`（15 个）

| id | 源 | URL | 本轮 HTTP / 实测 | level | type | 音频/字幕 | 许可要点 | embed | 付费/登录/地区 |
|---|---|---|---|---|---|---|---|---|---|
| `jlpt-n3-sample` | JLPT 官方 2009 改版前样题（N3） | `https://www.jlpt.jp/e/samples/sample09.html` | **200**；`N3Sample.mp3` **200 `audio/mpeg`**；`N3-script.pdf` 等 PDF 亦在页上列出 | N3 | mock/listening | 真人听解 MP3（11.0MB）+ 听解脚本 PDF + 答案；五类题型各 1 题 | 官方免费公开供考生练习；页面**未见再利用/嵌入条款**，著作权保留；样题为 2009 年改版前编制，题量与现行考试不同 | link | 免费、无登录、无地区限制 |
| `jlpt-workbook` | JLPT 官方练习册（2012 / 2018 Vol.2） | `https://www.jlpt.jp/e/samples/sampleindex.html` | **200**；原文 "**sold by Bonjinsha**" | N3 | mock | 该页不提供在线音频 | 付费出版物（凡人社销售）；著作权保留 | link | **部分内容付费**（册子），页面免费 |
| `jlpt-sample-forlearners` | JLPT 在线题型样题入口 | `https://www.jlpt.jp/e/samples/forlearners.html` | **200** | N3 | mock | 入口页，本身无音频 | 官方免费说明页；著作权保留 | link | 免费 |
| `irodori` | いろどり 初中級 / 入门·初级（含 MP3） | `https://www.irodori.jpf.go.jp/en/pre-intermediate/pdf.html` | **200**；`privacy.html` **200**，条款原文已复核 | N4/N3前期(A2/B1) | listening/reading | 真人会话 MP3（ZIP/在线播放）+ PDF 文本 | 自定义 Terms of Use：版权保留、仅限私用/教育机构、**禁止商用**、衍生教材须免费并注明来源；**未授权嵌入/热链** | link | 免费、无登录 |
| `tadoku` | Free Tadoku Books（带朗读音频） | `https://tadoku.org/japanese/en/free-books-en/` | **200**；`note-en/` **200** | N5–N3 | reading/listening | 官方朗读 MP3 + PDF 读物 | **CC BY-NC-ND 4.0**：官方明文允许分享链接（须署名 NPO多言語多読）；**明文禁止把朗读音频发布到网站、禁止改作/加注/翻译、禁止商业转售** | link | 免费 |
| `nhk-easy-japanese` | NHK WORLD-JAPAN《Easy Japanese / 简明日语》48 课 | `https://www3.nhk.or.jp/nhkworld/lesson/en/` | **200**（由 `nhk.or.jp/lesson/en` 重定向）；下载页 `.../segment/downloads/` **200**；课程页 `.../lessons/` **200** | N5/N4 | listening/video | 真人会话短剧 + MP3 + PDF 教材，逐课脚本 | 原文 "downloaded free of charge (**for personal use only**)"；NHK 版权内容，非开放许可，**未授权嵌入/再分发** | link | 免费、无登录、无地区限制 |
| `hirogaru` | ひろがる日本語（国際交流基金） | `https://www.hirogaru-nihongo.jpf.go.jp` | 新址 **200**；**旧址 `hirogaru-nihongo.jp` 200 但只是「サイトURL変更のお知らせ」告知页** | A1/A2（≈N5/N4） | reading/video | 主题式文章 + 视频，带振假名；听力属性弱 | JF 官方免费公开教育内容；著作权保留，未见嵌入授权 | link | 免费、无登录 |
| `erin` | エリンが挑戦！にほんごできます（25 课真人短剧） | `https://www.erin.jpf.go.jp/` | **200**；`jp/lesson/01/` **200**；**无 www 的 `erin.jpf.go.jp` 为 000（curl 失败）** | N4/N3 | video/listening | 真人场景短剧（问候/请求/问价/问路…）+ 课页文字 | JF 官方免费公开教育内容；站内未见独立再利用条款页，著作权保留；**链接必须用 www 别名** | link | 免费、无登录 |
| `podcast-teppei-beginners` | Japanese podcast for beginners (Nihongo con Teppei) | `https://nihongoconteppei.com/` | 官网 **200**；RSS `http://nihongoconteppei.com/feed/podcast` **200 `application/rss+xml`**（注意是 HTTP 非 HTTPS） | N4/N3 | listening | 真人独白，慢速短集；自动脚本需 Patreon | 免费公开发布的个人播客，版权保留（"All rights reserved" 类），未授权热链/嵌入；RSS 仅用于订阅 | link | 免费听（打赏/脚本为可选付费） |
| `podcast-shun` | Japanese with Shun | `https://feeds.redcircle.com/e8ab057c-683d-4375-a197-2dcc42d4f851` | RSS **200 `text/xml`** | N4 | listening | 真人独白，Genki 1/2 语法，5–10 分钟 | 播客版权 "**All rights reserved**"（podstatus 节目页）；脚本需 Patreon | link | 免费听（脚本付费） |
| `podcast-sakura-tips` | SAKURA TIPS｜Listen to Japanese | `https://anchor.fm/s/3c2daac8/podcast/rss` | RSS **200 `application/rss+xml`** | N5/N4 | listening | 真人独白，4–5 分钟，慢速；官网提供**免费脚本** | 免费公开发布播客，版权保留，未授权嵌入 | link | 免费 |
| `podcast-meg` | Meg's Simple Japanese Podcast（Simple Japanese Listening） | `https://anchor.fm/s/97402954/podcast/rss` | RSS **200 `application/rss+xml`** | N5–N3 | listening | 真人讲故事/童话，3–4 分钟起，免费脚本 + 影子跟读提示 | 免费公开发布播客，版权保留，未授权嵌入 | link | 免费 |
| `podcast-yuyu` | YUYUの日本語Podcast | `https://anchor.fm/s/cda85d4/podcast/rss` | RSS **200 `application/rss+xml`** | N3/N2 | listening | 真人独白，15–30 分钟，语速偏快 | 免费公开发布播客，版权保留，未授权嵌入 | link | 免费 |
| `podcast-noriko` | Learn Japanese with Noriko | `https://anchor.fm/s/1380f800/podcast/rss` | RSS **200 `application/rss+xml`** | N3/N2 | listening | 真人独白 10–30 分钟，YouTube 版带字幕 | 免费公开发布播客，版权保留，未授权嵌入 | link | 免费（另有付费会员内容） |
| `podcast-lets-talk` | Let's Talk in Japanese!（Tomo） | `https://anchor.fm/s/c56bd1c/podcast/rss` | RSS **200 `application/rss+xml`** | N4–N2 | listening | 真人独白 4–12 分钟，**按 JLPT 级别标注集数**，有脚本 | 免费公开发布播客，版权保留，未授权嵌入 | link | 免费 |

> 所有播客 RSS 的真实 feedUrl 均取自 Apple iTunes Search API，并逐条 `curl -I` 实测 200；`embed_url` 一律留空——RSS 是订阅源，不是被授权的网页内音频直链，不可写成可嵌入 URL。

### 2.3 `none`（8 个）

| id | 源 | URL | 本轮 HTTP / 实测 | 不用原因 | license |
|---|---|---|---|---|---|
| `nhk-news-easy` | NHK やさしいことばニュース / NEWS WEB EASY | `https://news.web.nhk/news/easy/` | **200**（`www3.nhk.or.jp/news/easy/` 重定向至此）；WebFetch 读到同意门与地区限制原文 | **地区限制**（"海外からの利用は一部制限されます…動画は視聴できない場合があります"）+ 需点同意门 + 主体是文字新闻非听力教材；原 `resources.json` 把它当免费阅读链接已过时 | NHK 版权内容，仅链接不复制 |
| `minato` | JF Japanese e-Learning Minato | `https://minato-jf.jp/` | **200**；课程详情 `.../KC26_MGRS_A205_EN02` **200** | **需注册/申请**（课程卡片均为 "Applications Open"），内容不在公开页；**许可条款未核实**（Marugoto 版权页指向站外 `jpf.go.jp/j/kansai/clip/minato/` 的 Minato 条款，本轮未取得正文） | **待核实** |
| `marugoto` | Marugoto / MARUGOTO+ 版权政策 | `https://marugoto.jpf.go.jp/en/copyright/` | **200**，条款原文已复核 | **明文禁止**：Q7 "**Please do not make them available to the public on websites, etc.**"、Q8 "**No.** …should download audio files directly from the Marugoto website"、Q3 "do not distribute the downloaded audio files to anyone"；教材本体需购买；Q3(C) 明确 "This policy also applies outside Japan" | 自定义 Copyright Policy（非 CC），明文禁止公开音频/再分发 |
| `satori-reader` | Satori Reader | `https://www.satorireader.com/` | **200** | **付费墙**：Pro **$9/月 或 $89/年**，仅少量免费章节；违反「不能有额外扣费」 | Freemium 商业订阅 |
| `japanesepod101` | JapanesePod101 | `https://www.japanesepod101.com/` | **200**；`pricing` **200** | **付费墙**：免费账号仅前 3 课 + 每周新课；Basic $8/月、Premium $25/月、PremiumPLUS $47/月（标准月付），核心音频课程需订阅 | Freemium 商业订阅 |
| `archive-org-jp-audio` | Archive.org 上标 PD / CC0 的「日语教学/会话音频」 | `https://archive.org/` | 站点 **200**；`advancedsearch.php` 日语 CC audio = **28** 条、PD = **4** 条；`metadata/05-02_202101`、`metadata/NEWS-STORY-ALBUM-SPECIAL` 已读；`archive.org/embed/{id}` **200**（官方 iframe 机制可用） | **权利瑕疵，最不该用**：`05-02_202101 "Basic Japanese mp3"` 描述为 "accompanying audio files for **Tuttle Basic Japanese**"、creator **Tuttle Publishing**，却被上传者标 `publicdomain/mark/1.0`；`NEWS-STORY-ALBUM-SPECIAL` 是日本偶像团体 **NEWS 的商业专辑**却标 `CC0`。**平台上的 PD/CC 标签不等于权利干净**，商业出版物不会因上传者标注而变成公有领域 | **待核实**（权利归属存疑，疑似误标/侵权上传） |
| `librivox-ja` | LibriVox 日语相关有声书 | `https://librivox.org/` | **200**；`collection:librivoxaudio AND subject:Japanese` = **54** 条；`japanese_prints_1607_librivox` metadata 原文 "**Read in English** by LibriVox volunteers", `language: eng`；`collection:librivoxaudio AND language:Japanese` = **0** 条 | **不适用**：LibriVox 的「日语相关」条目绝大多数是**英语朗读**关于日本的书，真正的日语朗读会话音频为 0 条；不能当日语听力源 | Public Domain（但内容非日语） |
| `tufs-langmodules` | TUFS 東京外国語大学 言語モジュール（Dialogue/Pronunciation） | `https://coelang.tufs.ac.jp/ja/` | **默认 curl 000 + exit 60（TLS 证书校验失败）**；`curl -k` 才返回 **200 `text/html`**；WebFetch 亦 `fetch failed`；介绍页 `wp3.tufs.ac.jp/nijiiro/` **200** | **可达性异常 + 许可未核实**：浏览器访问会报证书安全警告；页面未见明确再利用/嵌入条款；内容为 2003–2010 年面向「日语母语者学外语」的反向模块，维护状态不明 | **待核实** |

---

## 三、三类结论（明确分类）

### 3.1 可 `inline` 的 2 个（列名字与依据）

1. **`commons-ja-pron` — Wikimedia Commons 日语发音/短句音频**
   依据：`File:Ja-pronunciation-practice5.ogg` 为 **Public domain**，`Ja-arigato.oga` / `Ja-aisukurimu.ogg` 为 **CC BY-SA 3.0**；CC/PD 明文允许复用与公开展示；`upload.wikimedia.org` 官方 CDN 直链经 `curl -I` 实测 **200 `application/ogg`**。
2. **`commons-ja-spokenwiki` — Wikimedia Commons 日语朗读维基百科条目**
   依据：`ウィキペディア日本語版 録音記事「藤村紀雄」…ogg` 为 **CC BY-SA 4.0**；直链实测 **200**；维基原文可当脚本。

> **诚实提示**：这 2 个 inline 源是**单词/短句发音**与**百科朗读**，**不是 N3 会话、不是 N3 模拟题**。它们只能做辨音热身、影子跟读、概要理解泛听的补充，**不能替代**每日合成音频，也不能声称「站内已有 N3 真人听解题库」。

### 3.2 只能 `link` 的 15 个（名字）

`jlpt-n3-sample`、`jlpt-workbook`、`jlpt-sample-forlearners`、`irodori`、`tadoku`、`nhk-easy-japanese`、`hirogaru`、`erin`、`podcast-teppei-beginners`、`podcast-shun`、`podcast-sakura-tips`、`podcast-meg`、`podcast-yuyu`、`podcast-noriko`、`podcast-lets-talk`。

共同依据：全部**免费、无需登录、无地区限制**且本轮实际访问 200；但许可分别为「著作权保留 / personal use only / 自定义教育条款 / CC BY-NC-ND 4.0 / All rights reserved」，**均未授权第三方网页嵌入或热链音频**。因此一律只给跳转链接，用户点击后到原站/官方平台收听，`embed_url` 全部留空。

### 3.3 绝对不用的（重点 3 个 + 补充）

1. **`archive-org-jp-audio`（Archive.org 上误标 PD/CC0 的日语教学/流行音频）——最不该用**。
   `05-02_202101` 实为 **Tuttle Publishing 商业教材《Basic Japanese》配套 MP3**，`NEWS-STORY-ALBUM-SPECIAL` 实为 **NEWS 乐队商业专辑**，却被上传者标成 `Public Domain Mark` / `CC0`。**平台标签不是权利证明**；据此嵌入或转存将直接构成侵权风险，与「不能有法律风险」正面冲突。即便 `archive.org/embed/{id}` 官方 iframe 实测 200、技术上能嵌，也不得使用。
2. **`marugoto`（Marugoto 音频）——明文禁止**。
   版权政策 Q7「do not make them available to the public on websites」、Q8「do not distribute downloaded audio files」、Q3「do not use the audio files on their own」，教材还需购买，且条款明确适用于日本境外。属于用户定义的「明确禁止再分发/热链」→ `none`。
3. **`satori-reader` / `japanesepod101`（付费墙）——违反「不能有额外扣费」**。
   Satori Reader Pro $9/月 或 $89/年；JapanesePod101 免费账号仅前 3 课，Basic/Premium/PremiumPLUS 为 $8/$25/$47 每月。

**补充不用**：`nhk-news-easy`（海外地区限制 + 同意门，且非听力教材）、`minato`（需登录 + 条款待核实）、`librivox-ja`（实为英语朗读，不适用）、`tufs-langmodules`（TLS 证书校验失败 + 条款待核实）。

---

## 四、按阶段的听力路径（Day 47–150，每周 3 次）

前提：**现有合成音频 M0096–M0140 仍是每天听力主线**（Day 47 起每周 3 次，带 3 道题 + 脚本）。下面是**额外**的真人听力补充，不替换主线。每次真人听力建议 10–15 分钟，插在合成音频之后。

### 4.1 Day 47–90（N4→N3 过渡：慢速、短、有脚本）

- 推荐源：`commons-ja-pron`（辨音热身）、`podcast-sakura-tips`（4–5 分钟、免费脚本）、`nhk-easy-japanese`（48 课会话 + PDF 脚本）、`podcast-teppei-beginners`（短集泛听）、`tadoku`（听读配对，只读不改作）、`irodori`（入门/初级会话 MP3）。
- **每周 3 次配法**：
  1. **精听 + 脚本对照**（Sakura Tips 或 NHK Easy Japanese 1 课）：先盲听 2 遍 → 看脚本 → 再听 1 遍，摘 3 个生词。
  2. **泛听 + 影子跟读**（Teppei 1–2 集 或 Commons 发音文件）：不看文本，跟读，练语流与音高。
  3. **听读配对**（Tadoku 易级别 1 篇 或 Irodori 1 课）：边听朗读边读 PDF，练「音–文字」对应（注意 Tadoku 禁止改作/发布朗读音频，只个人使用）。
- 本周目标：从「逐词辨音」过渡到「抓住短独白大意」，语速以慢速为主。

### 4.2 Day 91–130（N3 核心：场景会话 + 要点/概要理解）

- 推荐源：`irodori`（初中級 A2/B1 生活场景会话）、`erin`（25 课真人短剧，场景用语）、`podcast-shun`（Genki 语法实景）、`podcast-meg`（故事，概要理解）、`podcast-lets-talk`（按 JLPT 级别标注，N4→N2 渐进）、`nhk-easy-japanese`（复习）、`commons-ja-pron`（继续热身）。
- **每周 3 次配法**：
  1. **场景会话 / 課題理解**（Erin 1 课短剧 或 Irodori 初中級 1 课）：只问「谁、在哪、要做什么、接下来做什么」。
  2. **概要理解**（Meg 故事 1 集 或 Let's Talk 1 集）：听后用一句中文写出主旨，不逐字。
  3. **要点理解 + 脚本复盘**（Shun 1 集 或 Irodori 会话）：先听抓关键词，再对照脚本核对漏听点，整理 3 条表达。
- 本周目标：把合成音频里学过的语法在真人语流中认出来；开始适应接近自然语速。

### 4.3 Day 131–150（N3 冲刺：题型对齐 + 自然语速）

- 推荐源：`jlpt-n3-sample`（**唯一权威题型锚点**，2009 样题五类题型各 1 题 + MP3 + 脚本）、`commons-ja-spokenwiki`（自然语速概要理解，站内可播放）、`podcast-noriko`、`podcast-yuyu`（近自然语速）、`tadoku`（听读维持）、`podcast-lets-talk`（N3 标注集）。
- **每周 3 次配法**：
  1. **官方样题限时模考**（`jlpt-n3-sample`）：按 40 分钟听解的比例做一小段，先独立作答再对 `N3-script.pdf` / `N3-seikai.pdf`。**必须注明这是 2009 改版前样题，题量与现行考试不同，不能换算官方分数**。
  2. **自然语速泛听**（YUYU / Noriko 或 Commons 朗读维基）：只抓大意与说话人态度。
  3. **听读 + 脚本核对**（Tadoku / Let's Talk）：查漏补缺，回看本站合成音频的脚本做对照。
- 本周目标：熟悉 N3 五类题型的提问方式，适应 near-natural speed。

### 4.4 N3 聴解五类题型的覆盖来源

| N3 题型 | 主要覆盖源 | 说明 |
|---|---|---|
| **課題理解**（Task-based） | `jlpt-n3-sample`、`irodori`、`erin`、`nhk-easy-japanese` | 场景会话里「接下来做什么」；JLPT 样题给标准提问形式 |
| **ポイント理解**（Key points） | `jlpt-n3-sample`、`podcast-shun`、`podcast-lets-talk`、`irodori` | 先抓关键词再作答；Shun/Let's Talk 有脚本可复盘 |
| **概要理解**（General outline） | `commons-ja-spokenwiki`、`podcast-meg`、`podcast-noriko`、`podcast-yuyu`、`jlpt-n3-sample` | 长段独白/朗读抓主旨与说话人意图 |
| **発話表現**（Verbal expressions） | `jlpt-n3-sample`、`erin`、`nhk-easy-japanese`、`irodori` | 场景用语、寒暄、请求、敬体/常体选择 |
| **即時応答**（Quick response） | `jlpt-n3-sample`、`erin`、`nhk-easy-japanese`、`irodori` | 短发话→选应答；靠真人短剧的对话轮次练反应 |

> 覆盖率说明：只有 `jlpt-n3-sample` 同时提供五类的**标准题型样例**（含 MP3 与脚本 PDF），其余源是**能力训练**而非题型训练。请在页面上把这点写清楚，避免让使用者误以为做了播客就等于刷了真题。

---

## 五、页面落地方案

### 5.1 现状（`scripts/build_v5_site.py`）

- 第 **567–572 行**：读 `knowledge/resources.json` 的 `resources` 数组，平铺生成 `web/resources.html`：每个资源一个 `<section class="card"><h2><a href=url target=_blank>` + `usage` + `license`，**没有分组、没有 embed 判断、没有 audio 标签**。
- 第 **493–516 行**：听力日生成 `listen_html`，含 `<audio controls src="{本站合成音频 url}">` + 3 道题 + `<details>` 脚本，说明文字为「原创文本 · Kokoro 合成语音」。这是**必须保留**的主线。
- 第 **339 / 385 行**：每日页已有 `<a href="resources.html">` 文字链（「官方真人听力与N3样题」/「官方真人听力、样题与资源署名」）——文案里的「真人听力」目前名不副实，需按 5.4 的诚实口径改写。
- `web/audio/NOTICE.txt` 与 `resources.html` 尾部的本地署名段（OpenJLPT / 韩国国立国语院 / KANJIDIC / Kokoro-82M / UniDic）**保持不变**。

### 5.2 `resources.html` 分组渲染建议

生成脚本改为读 `knowledge/resources_v7.json`（或把其 `sources` 合并进 `resources.json` 的 v2 结构），按 **`embed` → `level` → `type`** 三级分组：

1. **`embed:"inline"` 组（标题建议「可在本页直接播放（开放许可）」）**
   仅当 `embed_url` 非空时渲染 `<audio controls preload="none" src="{embed_url}">`，并在下方给出 `license` + `license_url` + 文件页链接 + 署名。**这一组只有 2 个源**，且必须注明是发音/朗读、不是 N3 会话。
2. **`embed:"link"` 组（标题建议「真人听力 · 跳转原站收听」）**
   按 `level`（N5/N4/N3）再按 `type`（listening / mock / video / reading）分小节。每条渲染 `<a href="{url}" target="_blank" rel="noopener noreferrer">`，并附一行元信息：`level · type · speed · avg_duration · 脚本:有/无 · license · 免费/登录/地区`。**绝不输出 `<audio>` 标签**。
3. **`embed:"none"` 组**
   **不生成可点击入口**。可选地在页尾「未收录与原因」里以纯文字列出名字 + `risk`，帮助使用者理解为什么没有收录（尤其 `archive-org-jp-audio` 的权利瑕疵）。

字段渲染前一律 `esc()` 转义（沿用脚本现有 `esc`）；`embed_url` 只允许出现在 `inline` 分支，`link`/`none` 强制忽略，避免误把外链写成已嵌入。

### 5.3 听力日页面加「真人听力」入口

在 `listen_html`（第 508–516 行）的**合成音频 `<audio>` 与题目之后**、`<details id="transcript">` 附近，追加一个**独立的补充块**（不改 `audio.src`、不动 `listen_json`、不动 `@@LISTEN@@` 结构）：

```
<details class="card" id="real-listening">
  <summary>真人听力（补充，非必做）</summary>
  <p class="hint">本站每日听力仍是原创文本合成语音。以下是免费的真人材料入口，点击会跳转到原站收听；站点不托管、不转存第三方音频。</p>
  <ul>…按当天 day 从 stage_plan 取 1–2 个 link 源，渲染 <a href target=_blank rel=noopener noreferrer>…</a>…</ul>
  <p class="small"><a href="resources.html#listening-real">查看全部真人听力清单与版权说明</a></p>
</details>
```

`stage_plan` 的 `days` 区间可直接映射 `day`：47–90 / 91–130 / 131–150 各取该段 `items` 的第 `(day % len(items))` 个，保证每周 3 次轮换不重复；**只有 `embed` 为 `inline`/`link` 的 id 才能进 `items`**（`none` 已在 JSON 里排除）。

### 5.4 版权声明文字（可直接落地）

> **真人听力资源与版权说明**
> 本站每日听力音频（M0096–M0140）为原创文本经 Kokoro-82M 合成的语音，不是真人录音，许可与署名见 `audio/NOTICE.txt`。
> 本页「真人听力」清单中的绝大多数条目**只提供跳转链接**：点击后你将离开本站，前往原作者/官方站点或播客平台收听；本站**不下载、不转存、不热链、不嵌入**任何第三方真人录音，也不对第三方内容的可用性、准确性与持久性负责。免费查看不等于可以复制或再发布，请遵守各站的使用条款。
> 仅标注「可在本页直接播放」的条目为 Wikimedia Commons 上采用 **Public Domain / CC BY-SA** 许可的日语发音与朗读文件；其许可与作者见对应文件页，署名与相同方式共享（SA）条款按其许可执行。这些是发音/朗读素材，**不是 N3 会话或 JLPT 真题**。
> 需付费订阅、需登录、有地区限制、或权利归属存疑的资源，本站**不予收录**。JLPT 官方样题为 2009 年改版前编制，仅用于了解题型，不能换算官方分数。

### 5.5 失效降级（保留原创合成音频）

- **主线不受影响**：`web/audio/M0096–M0140.m4a` 与 `manifest.json` 完整保留，`build_v5_site.py` 的 `valid_audio` 校验仍以本站文件为准；任何外部源失效都不会导致听力日页面构建失败或音频缺失。
- **`inline` 音频**：`<audio>` 加 `onerror` 回退——隐藏播放器并显示「该文件暂时不可用，前往 Wikimedia Commons 文件页」链接，或回退到当天合成音频；不因外部 404 阻断页面。
- **`link` 外链**：`target="_blank" rel="noopener noreferrer"`，生成时不做外链存活性依赖；可另写一个**非构建期**的巡检脚本定期 HEAD 检查，失效的条目在 JSON 里把 `embed` 降级为 `none` 并写 `risk`，下次构建自动不再生成入口。
- **构建期可选校验**：对 `embed:"inline"` 的 `embed_url` 做一次 HEAD；非 200 时本次构建按 `link` 渲染（只给文件页链接），避免把挂掉的直链写成可播放。
- **Cloudflare 侧**：无需新增回源规则、无需新增存储桶、无额外流量/费用；所有第三方音频流量都由用户浏览器直接向原站发起。

---

## 六、风险与「替换」的诚实口径

### 6.1 主要风险点

1. **平台标签 ≠ 权利证明**：Archive.org / LibriVox 上「日语」+「PD/CC」的条目里混有商业出版物、英语朗读。任何「看起来开放」的第三方音频，若要 inline，必须逐个核对**内容本体**（作者、出版社、语言、许可页），不能只看平台的 `licenseurl` 字段。
2. **CC BY-SA 的署名/SA 义务**：2 个 inline 源需在卡片上写明协议与文件页链接；只是播放不改编，不触发对整页的 SA，但**署名不可省**。
3. **CC BY-NC-ND（Tadoku）**：官方允许分享链接，但**禁止把朗读音频发布到网站、禁止改作/加注/翻译**。因此只能 `link`，且不得把 Tadoku PDF 内容搬进本站。
4. **personal use only（NHK Easy Japanese）**：只适合个人在原站学习；不得镜像、不得批量抓取、不得嵌入。
5. **旧样题（JLPT 2009）**：题量、指导语与现行考试不同；必须标注，不能当真题或分数依据。
6. **域名/入口漂移**：本轮实测 `www3.nhk.or.jp/news/easy/` → `news.web.nhk`、`nhk.or.jp/lesson/en` → `www3.nhk.or.jp/nhkworld/lesson/en/`、`hirogaru-nihongo.jp` → `www.hirogaru-nihongo.jpf.go.jp`、`erin.jpf.go.jp`（无 www）不可达、`coelang.tufs.ac.jp` 证书校验失败。链接需写**本轮验证过的最终 URL**，并定期巡检。
7. **播客 transcript 的付费部分**：Teppei 自动脚本、Shun 脚本需 Patreon；本站只推荐**免费收听**，不引导付费。

### 6.2 「替换」的诚实口径 —— 哪些话不能对使用者说

- **真正嵌进页面、可在本页播放的**：只有 `commons-ja-pron`、`commons-ja-spokenwiki` 两个（Wikimedia Commons 的 PD / CC BY-SA 发音与朗读文件），且它们是**发音/朗读**，不是 N3 会话。
- **只是外链的**：其余 15 个 `link` 源。用户点击后**离开本站**到原站/播客平台收听；本站不托管、不缓存、不转存任何真人录音。
- 因此**不能**说：
  - 「本站已接入 / 已内置真人听力音频库」「已替换为真人语音」「每日听力已改用真人录音」；
  - 「站内可直接播放 N3 真人听解 / 官方真题音频」；
  - 「已把 JLPT 官方听力、NHK、播客音频集成到页面」；
  - 「免费=可随意使用」「CC/PD 标签=权利干净」；
  - 「做完这些就等于刷完 N3 真题」（只对 2009 旧样题成立，且题量不同）。
- **可以**说：
  - 「新增了一份**真人听力入口清单**（按阶段/级别/题型分组），点击跳转到原站免费收听」；
  - 「其中 2 个开放许可的 Commons 发音/朗读文件**可在本页直接播放**，并已标注许可与署名」；
  - 「每日听力主线仍是本站原创文本合成语音（Kokoro），真人材料是**补充**，不影响离线可用性与原有音频」。

### 6.3 审计限制

- 本轮 HTTP 状态来自 `curl -I/-L`（HEAD，跟随重定向）；`WebFetch` 不暴露状态码，故状态码以 curl 实测为准并在表中标注。
- **未下载任何音频正文**：对 MP3 / OGG 只取响应头，GET 请求体一律丢弃到 `/dev/null`；未批量抓取教材 PDF/MP3 正文。
- **许可结论均基于页面原文或官方 API 元信息**；未见条款处标「未见条款」或「待核实」，未按印象套用 CC 类型。
- `coelang.tufs.ac.jp` 默认 TLS 校验失败（curl exit 60），仅 `curl -k` 得 200，表中如实记为「可达性异常」，`embed:"none"`。
- `Minato` 的使用条款正文位于站外 `jpf.go.jp/j/kansai/clip/minato/`，本轮未取得正文，`license:"待核实"`、`embed:"none"`。
- 机器可读版见 `knowledge/resources_v7.json`（`sources` 25 条，字段齐全；`stage_plan` 3 段；`conclusion` 计数与本报告一致）。
