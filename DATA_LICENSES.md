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
