# 数据与资源许可（DATA_LICENSES）

本项目是个人学习工具，代码与自建内容归项目作者。**第三方数据的来源、许可与署名如下**，
分发或再使用任何一部分前，请按对应条款处理。网页 `/resources.html` 与 `/audio/NOTICE.txt`
是面向使用者的同一套声明。

| 数据 / 资源 | 位置 | 来源 | 许可 | 义务 |
|---|---|---|---|---|
| 词汇、语法、汉字骨架与部分例句 | `knowledge/seeds/*.jsonl` | [OpenJLPT](https://github.com/evanclan/OpenJLPT) | CC BY-SA 4.0 | 署名 + 相同方式共享 |
| 韩语释义提示（2050 条词典匹配） | `vocabulary.jsonl` 的 `ko_hint`、`ko_source_ids` | 韩国国立国语院 [한국어기초사전](https://krdict.korean.go.kr/)，经 [spellcheck-ko/korean-dict-nikl](https://github.com/spellcheck-ko/korean-dict-nikl) 快照 | CC BY-SA 2.0 KR | 署名 + 相同方式共享 |
| 韩语释义提示（650 条） | 同上，`ko_status=ai_gloss` | 本项目 AI 草稿 | 随项目 | 标注为 AI，不声称词典释义 |
| 汉字韩语字音 | `kanji.jsonl` 的 `ko_hanja` / `ko_note` | [KANJIDIC2](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project)（EDRDG）、Unicode Unihan `kHangul` | CC BY-SA 4.0（KANJIDIC2）；Unicode License | 署名 + 相同方式共享 |
| 45 篇原创听力文本与题目 | `materials.jsonl` M0096–M0140 | 本项目原创 AI 草稿 | 随项目 | 标注 AI 草稿，未经真人试听 |
| 合成音频 | `web/audio/M0096–M0140.m4a` | [Kokoro-82M v1.0](https://huggingface.co/hexgrad/Kokoro-82M) `jf_alpha`，revision `f3ff357…`；UniDic 3.1.0 分词 | 模型 Apache-2.0；UniDic BSD 选项 | 见 `web/audio/NOTICE.txt`，含训练数据致谢 |
| 周测 / 阶段练习 39 题 | `knowledge/seeds/assessments.jsonl` | 本项目原创 | 随项目 | AI 草稿，非官方试题 |
| 外部官方资源（JLPT 样题、Irodori、Tadoku、NHK） | 仅 `web/resources.html` 外链 | 各官方站点 | 各自条款 | **不复制、不转存、不再分发**，只在原站使用 |

## 说明

- 旧题库 `knowledge/seeds/questions.jsonl`（945 题）为 v4 时期项目自建内容，v5/v6 页面不再从中抽题，保留作历史数据。
- 早期 `data/audio/` 下的 macOS `say` 产物仅限本机个人使用，已被 `.gitignore` 排除，**不发布、不提交**。
- 所有 `review_status=ai_draft` 的内容都未经日语/韩语教师逐条人工审校；AI 复审不等于人工认证。
- 许可可能随上游更新，再分发前请重新核对来源页面。

## Commons 开放音频逐文件署名（v7 新增，2026-11-08）

`web/listening.html` 直接播放以下 4 条 Wikimedia Commons 文件（`<audio src>` 指向 `upload.wikimedia.org`
官方 CDN，不下载转存）。页面卡片同时给出文件页、作者与许可全文链接。

| 文件 | 作者 | 许可 | 直链 |
|---|---|---|---|
| `Ja-pronunciation-practice5.ogg` | marsian | Public domain | `https://upload.wikimedia.org/wikipedia/commons/4/49/Ja-pronunciation-practice5.ogg` |
| `Ja-arigato.oga` | Fête | CC BY-SA 3.0 | `https://upload.wikimedia.org/wikipedia/commons/f/fb/Ja-arigato.oga` |
| `Ja-aisukurimu.ogg` | TAKASUGI Shinji | CC BY-SA 3.0 | `https://upload.wikimedia.org/wikipedia/commons/d/df/Ja-aisukurimu.ogg` |
| 维基百科日语版朗读记事「藤村紀雄」 | 朗读 Prefuture；条目作者见维基百科 | CC BY-SA 4.0 | `https://upload.wikimedia.org/wikipedia/commons/9/95/…ogg` |

四条直链 2026-11-08 实测 HTTP 200 `application/ogg`。许可与作者信息经
`commons.wikimedia.org/w/api.php` 的 `imageinfo/extmetadata` 逐文件核实。
CC BY-SA 文件仅播放、未改编；署名与许可链接已随音频卡片给出。

### mp3 官方转码（v7.1，2026-11-08）

`web/listening.html` 的每个 `<audio>` 同时给出两条 `<source>`：原始 Ogg/Oga 文件，以及 Wikimedia
自己生成的 mp3 转码（`https://upload.wikimedia.org/wikipedia/commons/transcoded/<hash>/<file>/<file>.mp3`）。
四条转码直链 2026-11-08 实测 HTTP 206 `audio/mpeg`，Safari 因此可以直接播放。

这里**只是引用 Wikimedia 官方 CDN 上已有的转码 URL**：项目没有下载、没有自行转码、没有改编音频文件，
因此不产生新的衍生作品，也不改变上表逐文件的作者与许可要求。页面卡片仍给出原作者、文件页与许可全文链接；
CC BY-SA / PD 的署名义务按原文件履行。
