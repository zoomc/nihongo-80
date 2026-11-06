# 开源项目与语料数据调研记录（GitHub / 语料）

- 调研日期（checked_at）：**2026-11-06**
- 工作目录：`/Users/mj/Documents/learn/jp`，项目根：`/Users/mj/Documents/learn/jp/nihongo-80`
- 产出文件（仅此两个，未改动其他文件）：
  - `/Users/mj/Documents/learn/jp/nihongo-80/research/source_registry_github.md`
  - `/Users/mj/Documents/learn/jp/nihongo-80/research/sources_github.json`
- 执行方式：对每一个 URL 使用 **WebFetch 真实访问**（GitHub 仓库主页、raw README、raw LICENSE、releases/tags 页、官方站点、官方手册、官方 wiki），**WebSearch 仅用于发现项目名，凡未经 WebFetch 访问的搜索结果一律不作已核实依据**。
- 纪律：star 数、许可证、最新版本号、更新状态**全部来自当次页面实际返回的文本**；任何页面未暴露的字段一律写「未看到 / 未核实 / 无法访问，未核实」，**绝不凭记忆填写**。

---

## 0. 字段与判定约定（可审计性说明）

| 项 | 约定 |
|---|---|
| `http_status` | WebFetch 工具**不暴露原始 HTTP 状态码**。本表 `"200"` 表示「URL 成功返回可核验的页面内容」；`"404"` 表示工具明确返回 `404: Not Found`（仅 `MarvNC/jpdb-freq-list` 的 raw LICENSE 一例，已在该条 evidence 内注明）。 |
| `fetch_status = OK` | 主页/README、LICENSE、releases/tags（或对应官方页面）等目标页面均成功返回，且本条要求的字段均已核实。 |
| `fetch_status = PARTIAL` | 至少一个目标页面内容不可用，已在 evidence/notes 中明确写「无法访问，未核实」；但要求字段已用其他官方页面交叉补齐。本批 2 条：`jmdict`、`kanjidic`（EDRDG 文档 wiki 已关闭）。 |
| `fetch_status = FAIL` | 主要来源完全不可访问。本批 0 条。 |
| `languages` | GitHub 主页经 WebFetch 转 markdown 后**普遍不暴露 Languages 侧栏与 star/fork 计数**，故本调研不记录 star 数；语言项均在对应 evidence 中给出页面可见依据，未核实占比的已逐条注明。 |
| 许可证 SPDX | 以 LICENSE / README / 官方许可证声明页**原文**判断；原文未出现 SPDX 标识符时按明示许可证文本映射，并注明判断依据（如 yomitan 的 GPL v3 正文）。 |

### 成功 / 失败统计

| 分类 | 总数 | OK | PARTIAL | FAIL |
|---|---|---|---|---|
| GitHub 项目 | 6 | 6 | 0 | 0 |
| 语料（jmdict / kanjidic / tatoeba / frequency_data） | 4 | 2 | 2 | 0 |
| **合计** | **10** | **8** | **2** | **0** |

- 真实访问的 URL（含 raw / wiki / releases / tags / 官方站点）共 **40+** 次；明确 `404: Not Found` 2 次（`fsrs-rs/src/parameters.rs` raw、`MarvNC/jpdb-freq-list` raw LICENSE），均如实标注、未脑补。
- 2 条 PARTIAL 的唯一原因：**EDRDG 文档 wiki 已关闭**，官方 `edict_doc.html` 已停用，其详细 DTD 字段文档「无法访问，未核实」；许可证/格式/下载/更新频率已由其他官方页面交叉补齐。

---

## 1. 各项目许可证清单（全部来自页面原文）

| id | 项目 | SPDX 许可证 | 证据（页面原文摘录） |
|---|---|---|---|
| anki | ankitects/anki | **AGPL-3.0-or-later** | `LICENSE` 首行：`Anki is licensed under the GNU Affero General Public License, version 3 or later, with portions contributed by Anki users licensed under the BSD-3 license (see CONTRIBUTORS).`；docs-site 文档 CC-BY-SA 4.0 |
| ts-fsrs | open-spaced-repetition/ts-fsrs | **MIT** | `LICENSE`：`MIT License` / `Copyright (c) 2026 Open Spaced Repetition` |
| awesome-fsrs | open-spaced-repetition/awesome-fsrs | **CC0-1.0** | `LICENSE`：`Creative Commons Legal Code` / `CC0 1.0 Universal` |
| yomitan | yomidevs/yomitan | **GPL-3.0-only** | `LICENSE`：`GNU GENERAL PUBLIC LICENSE` / `Version 3, 29 June 2007`；原文无 SPDX 串、无本项目级 `or later` 声明 → 按 `GPL-3.0-only` 记录 |
| japanese-language-data | jkindrix/japanese-language-data | **CC-BY-SA-4.0** | `LICENSE`：`This work ... is licensed under the Creative Commons Attribution-ShareAlike 4.0 International License (CC-BY-SA 4.0).`；README `## Licensing` 同 |
| openlanguage | challenga-org/openlanguage | **MIT** | `LICENSE`：`MIT License` / `Copyright (c) 2025 Challenga`；README `# License  OpenLanguage is available under the MIT License.` |
| jmdict | JMdict / EDICT (EDRDG) | **CC-BY-SA-4.0**（+ EDRDG Licence Statement 附加条件） | `licence.html` §3：`The dictionary files are made available under a Creative Commons Attribution-ShareAlike Licence (V4.0).`；§6 版权人 `James William BREEN and The Electronic Dictionary Research and Development Group` |
| kanjidic | KANJIDIC / KANJIDIC2 (EDRDG) | **CC-BY-SA-4.0**（+ §8 特殊条件） | `licence.html` §2 明确列入 KANJIDIC2 / KANJIDIC / KANJD212；jmdict-simplified README：`The original kanjidic2.xml file is released under Creative Commons Attribution-ShareAlike License v4.0` |
| tatoeba | Tatoeba | **CC-BY 2.0 FR**（子集 CC0-1.0；Tanaka Corpus 公有领域） | `downloads` 页：`These files are released under CC BY 2.0 FR.` / `A part of our sentences are also available under CC0 1.0.` |
| frequency_data | 日语词频（多源） | 主推荐 **CC-BY-SA-4.0**；FrequencyWords 内容 CC-BY-SA-4.0 + 代码 MIT；KFTT CC-BY-SA-3.0；Leeds CC-BY；JESC/WikiMatrix/Wikipedia 派生 CC-BY-SA-4.0；BCCWJ 官方仅「研究/教育用途」；**JPDB 系 LICENSE-BLOCKED** | FrequencyWords README `MIT License for code. CC-by-sa-4.0 for content.`；BCCWJ 官方 `It is free for use for research or educational purposes.`；japanese-language-data docs/sources.md `## JPDB frequency list — LICENSE-BLOCKED` |
| （附录）py-fsrs | open-spaced-repetition/py-fsrs | **MIT** | `LICENSE`：`MIT License` / `Copyright (c) 2022 Open Spaced Repetition`；README badge `License-MIT` |
| （附录）fsrs-rs | open-spaced-repetition/fsrs-rs | **BSD-3-Clause** | `LICENSE`：`BSD 3-Clause License` / `Copyright (c) 2023, Open Spaced Repetition` |

### 合规要点

- **强 copyleft（慎用于本地项目）**：Anki（AGPL-3.0-or-later）、Yomitan（GPL-3.0-only）——只能参考其**数据格式/算法规范**，不要复制代码。
- **ShareAlike 传染**：JMdict / KANJIDIC / japanese-language-data / jmdict-simplified / FrequencyWords 内容均为 CC-BY-SA 系列，衍生数据须同许可分发 + 署名。
- **EDRDG 额外义务（必须工程落实）**：文档/宣传/网站致谢并提供 EDRDG 项目页链接；Web 词典**至少每月更新一次数据**且每屏显示致谢；App 须独立 About/Sources 页；不得对 EDRDG 材料主张版权；同意赔偿与无担保。
- **KANJIDIC §8 逐字段署名**：SKIP 码（Jack HALPERN）、拼音读音（WITTERN / YASUOKA）、四角号码与诸桥索引（Urs APP）、Spahn/Hadamitzky 描述符、韩语读音（Charles MULLER）、De Roo 码（Joseph DE ROO）。
- **禁止使用**：JPDB 系词表（无 LICENSE 文件 / 明确 LICENSE-BLOCKED）；BCCWJ 官方词表商用未获授权。

---

## 2. 六个 GitHub 项目核验摘要

| id | 主要语言 | 活跃度证据 | 最新 release / tag | 能否直接复用 |
|---|---|---|---|---|
| anki | Rust / Python / JS-TS（LICENSE 原文提及 `Python, Rust and Javascript libraries`，主页文件列表含 `rslib`、`ts`） | `63b419e · Nov 5, 2026`、`12,622 Commits` | **26.09.4**（04 Nov 2026，9 assets） | ❌ AGPL-3.0，不可复制代码；FSRS 由 `fsrs-rs 6.6.2` 提供（releases #5494 原文），仅作行为基准 |
| ts-fsrs | TypeScript（+ Rust/WASM binding） | 提交 May 26 / Jun 4, 2026 | **v6.0.0 / ts-fsrs@6.0.0**（28 Oct 2026） | ⚠️ MIT 可商用，但 Node ≥24 + v6 默认 FSRS-7（34 权重），不适合零依赖 |
| awesome-fsrs | （主页未暴露 Languages 侧栏，未核实） | `1b1eade · Nov 3, 2026`；wiki 48 revisions / Jul 28, 2026 | 无 release（tags 页 `There aren't any releases here`） | ✅ CC0-1.0；**官方算法 wiki 是 FSRS 公式与默认参数的首要出处** |
| yomitan | JavaScript / TypeScript（依据根目录 `.js` 配置与 README `Increasing our type coverage`，占比未核实） | 26.11.2.0（03 Nov 2026）、26.10.22.0（22 Oct）等密集发布 | **26.11.2.0** | ✅ 仅复用**词典数据格式**（zip + index.json + `*_bank_N.json`）；源码 GPL-3.0 不复制 |
| japanese-language-data | Python（`.python-version`、`pyproject.toml`、`build/transform/*.py`） | README `Status: Phase 4 — Active`；文件日期 Apr 13/14, 2026 | **v0.9.0**（Apr 13, 2026） | ✅ **最推荐**：CC-BY-SA 4.0 的统一 JSON 数据集（words/kanji/frequency×8/corpus/grammar/cross-refs）+ 完整署名清单 |
| openlanguage | React Native/Expo + SwiftUI（README 原文） | 主页未提供提交日期（活跃度未核实） | 无 release（releases 页 `There aren't any releases here`） | ✅ MIT，但与本项目关联度最低，仅作 iOS 形态参考 |

### 重点核实结论

- **Anki 的 FSRS 实现**：不是 TS/Python 手写，而是 Rust crate `fsrs-rs`（Anki 26.09 release notes 原文 `Update FSRS to 6.6.2` 指向 `open-spaced-repetition/fsrs-rs`），另有 `Add tests for FSRS simulator`、`use col.fsrs_enabled` 等提交。官方手册 `docs.ankiweb.net/deck-options.html#fsrs` 明确 `desired retention` 默认 **90%**、`Do not change the parameters manually or copy them from someone else`、参数需 Optimize 生成。→ **不要从 Anki 源码抄实现**。
- **ts-fsrs 的版本与参数**：v6.0.0（2026-10-28）为破坏性大版本，`DefaultScheduler()` **默认 FSRS-7（34 权重、`stabilityFast`、fractional-day intervals）**；FSRS-6 仍可用但需显式 `version: 'FSRS-6'`。release notes 明确 `FSRS-6 uses weights[20]`（可训练 decay）、`w[17]/w[18]` 与 `w[11]/w[13]/w[14]` 的 clip 约束。→ **若要与 Anki 对齐，必须显式锁定 FSRS-6**。根 README 未列出默认 w 数值（未核实），数值以官方 wiki / py-fsrs 为准。
- **Yomitan 的词典格式**（`docs/making-yomitan-dictionaries.md` 原文）：zip 根目录放 `index.json`（`dictionary-index-schema.json`）+ `term_bank_${number}.json`（词条）+ `kanji_bank_${number}.json`（汉字）+ `tag_bank_${number}.json`（标签）+ **`term_meta_bank_${number}.json`（存 frequency data 与 pitch accent）** + **`kanji_meta-bank_${number}.json`（存 kanji frequency data）**；可加 `styles.css`；`tag_bank` 类别含 `frequency`。词性标签文档指向官方 JMDict 页。→ 词频数据正好落在 `term_meta_bank` / `kanji_meta-bank`。

---

## 3. 四类语料核验摘要

| id | 官方站点 / 下载 | 格式 | 更新频率 | 许可证 | 规模 | fetch_status |
|---|---|---|---|---|---|---|
| jmdict | `https://www.edrdg.org/jmdict/j_jmdict.html`；`ftp://ftp.edrdg.org/pub/Nihongo//JMdict.gz`、`JMdict_e.gz`、`JMdict.dtd`；JSON 版 `scriptin/jmdict-simplified/releases/latest` | XML + DTD（UTF-8，用 entities/DOCTYPE）；JSON 由 jmdict-simplified 转换（full / common-only / with-examples / 10 种语言） | 官方 `generated daily ... The source database is updated almost every day`；ftp 索引 `JMdict, Kanjidic, etc. will still be updated daily`；jmdict-simplified `every Monday`；EDRDG 要求使用者 ≥每月更新 | CC-BY-SA 4.0 + EDRDG Licence Statement | 官方页未给 JMdict 单独词条数（未核实）；`japanese-language-data` 聚合 `~277k committed entries`（多源合计，非纯 JMdict） | **PARTIAL** |
| kanjidic | `kanjidic2.xml.gz` / `kanjidic2.xml` / `kanjidic2_dtd.gz` / `kanjidic2_xsd.gz` / `kanjidic.gz` / `kanjd212.gz`（ftp 索引）；JSON `kanjidic2-all-*.json.tgz` | KANJIDIC2 为 XML（DTD/XSD，UTF-8）；旧 KANJIDIC 纯文本；JSON 由 jmdict-simplified 转换 | ftp 索引 `Dictionary files such as JMdict, Kanjidic, etc. will still be updated daily`；jmdict-simplified 每周一 | CC-BY-SA 4.0 + §8 特殊条件 | KANJIDIC 6,355 字（JIS X 0208）、KANJD212 5,801 字（JIS X 0212）、KANJIDIC2 覆盖 JIS X 0208/0212/0213；`kanjidic2-all` 13,108 字符（docs/sources.md） | **PARTIAL** |
| tatoeba | `https://tatoeba.org/eng/downloads` → `https://downloads.tatoeba.org/exports/sentences.tar.bz2`、`sentences_detailed.tar.bz2`、`sentences_base.tar.bz2`、`sentences_CC0.tar.bz2`；按语言 `.../per_language/jpn/`（如 `jpn-eng_links.tsv.bz2`） | TSV（tab 分隔）：`Sentence id [tab] Lang [tab] Text`，Lang 为 ISO 639-3；detailed 另含 Username / Date added / Date last modified；`.tar.bz2` | 官方 `updated every Saturday at 6:30 a.m. (UTC)`；docs/sources.md 记 `Daily snapshots`（口径不一致，未进一步核实） | **CC BY 2.0 FR**（子集 CC0 1.0；Tanaka Corpus 公有领域；音频许可由贡献者自选） | 全库 `13,661,633 sentences`；**日语 `jpn 249,247`**（统计页第 13 位，访问瞬时值）；日语音频 6,332 | OK |
| frequency_data | 主推荐 `japanese-language-data/data/enrichment/frequency-*.json`（8 个）；`FrequencyWords/content/2018/ja/ja_full.txt`；BCCWJ 官方 zip（DOI）；`Kuuuube/yomitan-dictionaries` 词典 zip | JSON（词→频次/排名，已与 `words.json` 对齐）；`{word}{space}{count}` 纯文本（FrequencyWords）；Yomitan `term_meta_bank` zip | japanese-language-data v0.9.0（Apr 13, 2026）+ 每月重建承诺；FrequencyWords 内容最后处理 **Feb 15, 2019**；BCCWJ ver1_0（2014/01/07 更正） | 主 CC-BY-SA 4.0；上游 MIT/CC-BY-SA-4.0、CC-BY-SA-3.0、CC-BY 等；BCCWJ 仅研究/教育；**JPDB LICENSE-BLOCKED** | 8 个语域词频文件；FrequencyWords 日语 34,504 词频对 → 匹配 8,598 条；`14,647 ranked`（README）；Leeds ~15,000 lemmas | OK |

### 语料质量风险（要点）

- **EDRDG wiki 已关闭**：`JMdict-EDICT_Dictionary_Project` 与 `KANJIDIC_Project` 两个页面均返回 `The documentation Wiki has been closed as a result of problems caused by large numbers of accesses from bots scraping the contents`；`edict_doc.html` 返回 `The page you reached is no longer in use`。这两处的详细 DTD 字段文档「**无法访问，未核实**」，故两条标 PARTIAL；已用 `licence.html`、官方首页、`ftp 00INDEX.html`、`jmdict-simplified`、`japanese-language-data` 交叉补齐。
- **Monash ftp 已关闭**：`WARNING!! After nearly 30 years of operation the Monash ftp server has been closed down.` 仅 edrdg.org 站点继续每日更新字典文件，且不再新增文件；提供 rsync `rsync ftp.edrdg.org::nihongo/filname filename`。
- **2026-05 起 NG 版**：`In May 2026 the "New Generation" (NG) version of JMdict began to be distributed.`（`JMdict_NG.gz`、`kanjidic2_NG.xml` 等）；NG 版与经典版字段差异**未核实**。
- **Tatoeba**：社区众包、`Quality varies by contributor and language pair`；CC-BY 2.0 FR 与 CC0 混合需按导出文件区分；`sentences.tar.bz2 ~204 MB`；建议用经 JMdict 编辑审校的 `jmdict-examples-eng` 子集。
- **词频**：不同语域（报纸 / 现代媒体 / 字幕 / 网络 / Wikipedia / JESC / Tatoeba）排名不可直接混用；JMdict 自带频度被 Kuuuube 明确评 `Quality: Low`；JPDB 系**禁用**；BCCWJ 官方仅限研究/教育；Leeds 原站已关闭仅存 Wayback 存档。

---

## 4. ★ 对「本地零依赖实现 FSRS」最有用的依据

> 结论：**不要引入任何运行时依赖**。直接照抄官方 wiki 的公式 + 官方默认参数数组，用语言自带的 `pow / exp / log` 即可实现 FSRS-6 的调度核心（纯算术，零第三方依赖）。

### 4.1 官方出处链接（按权威性排序）

| # | 用途 | 链接 | 许可 | 核验状态 |
|---|---|---|---|---|
| 1 | **FSRS 默认参数 w 数组 + 遗忘曲线公式（唯一权威官方原文）** | **https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm** | CC0-1.0（仓库 LICENSE） | ✅ 已访问；`Jarrett Ye edited this page Jul 28, 2026 · 48 revisions` |
| 2 | 默认参数的可执行交叉验证（21 个值与 wiki 逐值一致）+ 默认超参 | **https://github.com/open-spaced-repetition/py-fsrs** 与 **https://raw.githubusercontent.com/open-spaced-repetition/py-fsrs/main/README.md** | MIT | ✅ 已访问 |
| 3 | FSRS-4.5 / FSRS-5 完整公式与旧默认参数（历史快照） | **https://github.com/open-spaced-repetition/fsrs4anki/wiki/The-Algorithm/d040f23afdfcc33a1fab734f821008668ccfd116** | wiki（旧仓库） | ✅ 已访问 |
| 4 | 旧 wiki（**仅剩迁移提示，勿引用**） | https://github.com/open-spaced-repetition/fsrs4anki/wiki/The-Algorithm | — | ✅ 已访问，正文为 `Page moved` → 新地址见 #1 |
| 5 | desired retention 默认 90% / 参数需 Optimize | **https://docs.ankiweb.net/deck-options.html** | Anki 文档 | ✅ 已访问 |
| 6 | Anki 实际使用的官方 Rust 实现（版本基准） | **https://github.com/open-spaced-repetition/fsrs-rs** | BSD-3-Clause | ✅ 已访问（README + LICENSE）；Anki 26.09 releases 指向 `fsrs-rs 6.6.2` |
| 7 | 各语言实现清单（CC0） | https://github.com/open-spaced-repetition/awesome-fsrs | CC0-1.0 | ✅ 已访问 |

### 4.2 FSRS-6 默认参数 w 数组（官方 wiki 原文，21 个权重）

来源：`https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm` → `# FSRS-6 / ## Default parameters`，页面原文 `This version uses 21 parameters.`

```
[0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
 1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014,
 1.8729, 0.5425, 0.0912, 0.0658, 0.1542]
```

**交叉验证**：`py-fsrs` README `# NOTE: the following arguments are also the defaults` 给出的 `Scheduler(parameters=(...))` **21 个值与上表逐值完全相同**，并注明 `parameters are a set of 21 model weights`。py-fsrs 6.0.0 release notes 亦写明 `Creating a Scheduler object with custom parameters now requires 21 parameters instead of the previous 19`。→ 两个独立官方来源一致，可放心硬编码。

配套默认值（py-fsrs README 原文）：`desired_retention = 0.9`、`learning_steps = (1m, 10m)`、`relearning_steps = (10m,)`、`maximum_interval = 36500`、`enable_fuzzing = True`；Anki 官方手册亦记 desired retention 默认 90%。

### 4.3 遗忘曲线公式（官方 wiki 原文）

**FSRS-6（当前生产版，decay 可训练）** —— `awesome-fsrs/wiki/The-Algorithm` 的 `# FSRS-6 / ## Formula`：

```
R(t, S) = (1 + factor · t / S)^(−w20)
其中  factor = 0.9^(−1/w20) − 1       （确保 R(S, S) = 90%）
w20 默认 = 0.1542
```

- `R` Retrievability（回忆概率）、`S` Stability（`R=90%` 时的间隔）、`D` Difficulty（∈[1,10]）、`G` Grade：1=again / 2=hard / 3=good / 4=easy。
- 同日复习（short-term）稳定性更新（wiki 原文）：`S′(S,G) = S · e^{w17·(G−3+w18)} · S^{−w19}`，并注明 `In practice, we should ensure that SInc ≥ 1 when G ≥ 2`。
- 由 `R` 反解间隔（wiki 在 FSRS-4.5 段给出的通式 `I(r,S) = S/FACTOR · (r^(1/DECAY) − 1)`；FSRS-6 对应式按上式解出 `t`，属推导而非 wiki 逐字原文，实现时需自行代入 `−w20` 与 `factor`）。

**FSRS-4.5 / FSRS-5（固定 decay 的旧版，wiki 原文）**：

```
R(t, S) = (1 + FACTOR · t / S)^DECAY        R(t,S) = 0.9 when t = S
I(r, S) = S / FACTOR · (r^(1/DECAY) − 1)    I(r,S) = S when r = 0.9
FSRS v4   : DECAY = −1,     FACTOR = 1/9
FSRS-4.5  : DECAY = −0.5,   FACTOR = 19/81
```

**FSRS v4 初始状态与更新公式（wiki 原文，便于零依赖复刻）**：

```
S0(G) = w_{G−1}                                   （w0..w3 对应 Again/Hard/Good/Easy）
D0(G) = w4 − (G−3)·w5                             （FSRS-5 改为 D0(G) = w4 − e^{w5·(G−1)} + 1）
D′(D,G) = w7·D0(3) + (1−w7)·(D − w6·(G−3))        （均值回归，避免 ease hell）
S′r(D,S,R,G) = S·( e^{w8}·(11−D)·S^{−w9}·(e^{w10·(1−R)}−1)·w15(if G=2)·w16(if G=4) + 1 )
S′f(D,S,R)   = w11·D^{−w12}·((S+1)^{w13}−1)·e^{w14·(1−R)}
R(t,S) = (1 + t/(9·S))^{−1}  ；  I(r,S) = 9·S·(1/r − 1)     （v4）
```

wiki 同页还给出 FSRS-5（19 参数）、FSRS-4.5（17）、v4（17）、v3（13）、v2（14）、v1（7）的完整默认参数数组，便于版本对照；**建议本地实现锁定 FSRS-6 / 21 参数**，与 Anki 26.09（fsrs-rs 6.6.2）同代。

### 4.4 实现建议（避坑）

1. **公式与参数直接抄 #1 + #2**（CC0 / MIT，可自由引用），不要 import Anki（AGPL-3.0）、不要依赖 fsrs-rs（需 Rust 工具链 / binding）、不要把 ts-fsrs v6 默认当 FSRS-6（它默认是 FSRS-7，34 权重）。
2. 只需 `Math.pow / exp / log` 等标准库运算即可实现 `R(t,S)`、`I(r,S)`、`S0/D0`、`S′r/S′f/D′`；`Card`/`Scheduler` 状态机自行用结构体 + 时间戳表示，零第三方依赖。
3. `desired_retention = 0.9` 作为默认；`learning_steps (1m,10m)`、`relearning_steps (10m,)`、`maximum_interval = 36500` 属**客户端调度策略**（py-fsrs README / ts-fsrs release notes 均有说明），与记忆状态公式分层实现。
4. 版本一致性：py-fsrs README NOTE 原文提醒 `The computed optimal parameters and retention may be slightly different than the numbers computed by Anki for the same set of review logs. This is because the two implementations are slightly different and updated at different times.` → 本地实现的结果与 Anki 可能有细微差异，属预期，需在测试中留容差。
5. 参数优化（Optimizer）需要机器学习训练，**不属于零依赖最小实现**；最小可用版本使用官方默认 w 数组即可，后续再考虑用户数据优化。

---

## 5. 附录：py-fsrs / FSRS 官方 Python 实现核实

| 项 | 核实结果 | 证据 |
|---|---|---|
| 是否存在 | ✅ 存在 | `https://github.com/open-spaced-repetition/py-fsrs` 标题 `GitHub - open-spaced-repetition/py-fsrs: Python Package for FSRS Spaced Repetition · GitHub` |
| Python 包名 | **`fsrs`**（PyPI） | README `You can install the fsrs python package from PyPI using pip: pip install fsrs`；PyPI `https://pypi.org/project/fsrs/`；优化器可选 `pip install "fsrs[optimizer]"`；Python `3.10+`（README badge） |
| 许可证 | **MIT** | raw LICENSE `MIT License` / `Copyright (c) 2022 Open Spaced Repetition`；README badge `License-MIT-brightgreen` |
| 最新版本 | **v6.3.1** | releases 页 `#154 bump version to 6.3.1`、`#155 Fix same-day Hard stability floor`、`#156 Fix Ruff autofix failures`；`Full Changelog: v6.3.0...v6.3.1`；`Py-FSRS 6.0.0` 起 `upgrades Py-FSRS to use the new FSRS 6 model`，`requires 21 parameters instead of the previous 19`；另有 `#133 Update default parameters` |
| 默认参数来源 | **官方 wiki + 本仓库 README** | README `# NOTE: the following arguments are also the defaults` 给出 21 个权重，与 `awesome-fsrs/wiki/The-Algorithm` FSRS-6 默认数组逐值一致；`parameters are a set of 21 model weights`；`If you're not familiar with optimizing FSRS, it is best not to modify these default values.` |
| 默认超参 | desired_retention 0.9 / learning_steps (1m,10m) / relearning_steps (10m,) / maximum_interval 36500 / enable_fuzzing True | 同上 README `### Custom parameters` 代码块 |
| API | `from fsrs import Scheduler, Card, Rating, ReviewLog`；`scheduler.review_card(card, rating)`；`get_card_retrievability(card)`；`to_json/from_json` 序列化；`Optimizer` 可选 | README Quickstart / Usage / Reference 段 |
| 官方 Rust 实现（Anki 使用） | `fsrs-rs`，crate 名 **`fsrs`**（`cargo add fsrs`），**BSD-3-Clause** | `https://github.com/open-spaced-repetition/fsrs-rs` README `FSRS-rs is a Rust implementation of FSRS`、示例 `use fsrs::{FSRS, MemoryState}` / `FSRS::default()` / `desired_retention = 0.9`；LICENSE `BSD 3-Clause License / Copyright (c) 2023, Open Spaced Repetition`；bindings 列出 c / python(`fsrs-rs-python`) / nodejs / dart / php；`FSRS-6 and FSRS-7 are selected from the parameter count`；最近提交 Nov 5, 2026 |
| 其他 | 与 Anki 数值可能略有差异；旧版参数迁移 | README NOTE 原文；releases `Py-FSRS 6.0.0` 给出 FSRS-5→6 迁移示例（`new_parameter_19 = 0.0`, `new_parameter_20 = 0.5`） |

补充：`https://raw.githubusercontent.com/open-spaced-repetition/fsrs-rs/main/src/parameters.rs` 返回 `404: Not Found`（该路径不存在，未核实到该文件内容）；fsrs-rs 的默认参数请以官方 wiki 与 py-fsrs README 为准，本调研未据此路径推断任何数值。

---

## 6. 无法访问 / 未核实清单（如实记录，绝不脑补）

| 项 | 状态 | 处理方式 |
|---|---|---|
| `https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project` | **无法访问，未核实**：页面返回 `The documentation Wiki has been closed ... bots scraping`，仅给 archive.org 快照链接 | 用 `j_jmdict.html`、`licence.html`、官方首页、`ftp 00INDEX.html`、`jmdict-simplified` 交叉补齐；该条标 PARTIAL |
| `https://www.edrdg.org/wiki/index.php/KANJIDIC_Project` | **无法访问，未核实**：同上关闭公告 | 用 `licence.html` §2/§8、ftp 索引、`jmdict-simplified`、`japanese-language-data` 交叉补齐；该条标 PARTIAL |
| `http://www.edrdg.org/jmdict/edict_doc.html` | **无法访问，未核实**（`The page you reached is no longer in use`） | 改用 `j_jmdict.html` 获取 XML/DTD/下载/每日更新信息 |
| `https://raw.githubusercontent.com/open-spaced-repetition/fsrs-rs/main/src/parameters.rs` | `404: Not Found` | 未据此推断默认参数；改以官方 wiki + py-fsrs README 为参数出处 |
| `https://raw.githubusercontent.com/MarvNC/jpdb-freq-list/main/LICENSE` | `404: Not Found`，**许可证无法核实，未使用** | 依 `japanese-language-data/docs/sources.md` 的 `LICENSE-BLOCKED` 判定禁用 JPDB 系词表 |
| `Kuuuube/yomitan-dictionaries` 主页未显示 License 名称 | **未核实** | 其 JPDB v2.2 / BCCWJ 词典包仅作线索，不作已核实可用来源 |
| 各 GitHub 主页的 star/fork 数、Languages 占比 | 多数页面经 WebFetch 转码后**未暴露侧栏，未核实** | 遵守「禁止凭记忆填写 star 数」，本调研不记录 star 数；`FrequencyWords` 主页实际显示了 `1.6k stars / 601 forks / C# 97.4%`，仅该条如实记录 |
| `openlanguage` 主页最近提交日期 | **未核实** | 如实标注活跃度未核实 |
| `anki` 主页 star/fork/README 首段（片段截断） | 主页片段未看到，已用 raw README 补齐首段 | 侧栏数值仍未核实，未填写 |
| `edrdg.org` 2026-05 起 JMdict / KANJIDIC2 的 NG 版字段差异 | **未核实** | 仅在质量风险中提示，未据此推断格式 |
| `Tatoeba` 官方下载页「每周六」与 docs/sources.md「Daily snapshots」口径不一致 | **未进一步核实** | 两条原文并列记录 |
| WebSearch 发现但未 WebFetch 核实的项目：`toasted-nutbread/yomichan-bccwj-frequency-dictionary`、`chriskempson/japanese-subtitles-word-kanji-frequency-lists`、Wiktionary Frequency lists/Japanese 的 Leipzig/Leeds 线索 | **仅搜索结果，未核实** | 明确排除在「已核实可用来源」之外 |

---

## 7. 完整访问日志（按记录分组，均为 WebFetch 真实访问）

**GitHub 项目**
- anki：主页 / `raw .../main/LICENSE` / `/releases` / `raw .../main/README.md` / `https://docs.ankiweb.net/deck-options.html`
- ts-fsrs：主页 / `raw .../main/LICENSE` / `raw .../main/README.md` / `/releases`
- awesome-fsrs：主页 / `raw .../main/LICENSE` / `/tags` / `https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm` / `https://github.com/open-spaced-repetition/fsrs4anki/wiki/The-Algorithm` / 历史快照 `.../The-Algorithm/d040f23afdfcc33a1fab734f821008668ccfd116`
- yomitan：主页 / `raw .../master/LICENSE` / `/releases` / `raw .../master/docs/making-yomitan-dictionaries.md`
- japanese-language-data：主页 / `/tags` / `raw .../main/LICENSE` / `raw .../main/docs/sources.md`
- openlanguage：主页 / `raw .../main/LICENSE` / `/releases`

**语料**
- JMdict / KANJIDIC：`http://www.edrdg.org/jmdict/edict_doc.html`、`https://www.edrdg.org/edrdg/licence.html`、`https://www.edrdg.org/`、`https://www.edrdg.org/jmdict/j_jmdict.html`、`http://ftp.edrdg.org/pub/Nihongo/00INDEX.html`、两个 EDRDG wiki 项目页、`https://github.com/scriptin/jmdict-simplified`
- Tatoeba：`https://tatoeba.org/eng/downloads`、`https://tatoeba.org/eng/stats/sentences_by_language`
- 词频：`https://github.com/hermitdave/FrequencyWords`、`raw .../master/LICENSE`、`/tree/master/content`、`http://clrd.ninjal.ac.jp/bccwj/en/freq-list.html`、`https://github.com/MarvNC/jpdb-freq-list`、`raw .../main/LICENSE`、`https://github.com/Kuuuube/yomitan-dictionaries`（另用 WebSearch 辅助发现项目名，未核实者已标注）

**FSRS 官方实现（附录）**
- `https://github.com/open-spaced-repetition/py-fsrs`、`raw .../main/README.md`、`raw .../main/LICENSE`、`/releases`
- `https://github.com/open-spaced-repetition/fsrs-rs`、`raw .../main/LICENSE`、`raw .../main/src/parameters.rs`（404）

---

*本文件与 `sources_github.json` 一一对应；JSON 中每条 `evidence` 字段保存了逐 URL 的页面标题与原文片段，供审计复核。*
