# Nihongo 80 — 数据契约 v1

本文件是项目内所有脚本、数据、页面、Agent 的**唯一接口依据**。任何模块改动前先改这里。
所有 JSON 使用 UTF-8、`ensure_ascii=false`；JSONL 每行一个独立对象；代码中字符串分隔符只用 ASCII 直引号。

## 0. 真源规则（不可协商）

| 内容 | 真源 | 说明 |
|---|---|---|
| 知识条目 | `knowledge/seeds/*.jsonl` | 人可编辑、可审计；SQLite 只是构建产物 |
| 课程 | `curriculum/curriculum.json` | 80 天结构化数据；`day-NNN.md` 是其渲染视图 |
| 学习状态 | `data/state.db`（SQLite） | **唯一可写真源** |
| `student/*.json` | 由 `export_state` 生成的只读镜像 | 禁止手改后当作状态变更 |
| 每日网页 | `web/day-NNN.html` + `web/data/day-NNN.json` | 由构建脚本生成，**不持有状态** |
| 平台记忆/聊天上下文 | 不作为状态 | 会话可随时关闭，状态必须落盘 |

写状态一律经脚本（事务 + `audit_log`），AI 只输出「评分 / 错误类别 / 讲解」，不直接写数值。

## 1. ID 规范

稳定、单调递增、四位数字，永不复用：

- 词汇 `V0001`…；语法 `G0001`…；汉字 `K0001`…；题目 `Q0001`…；素材 `M0001`…
- 资料来源 `S001`…（见 `config/sources.json`）
- 会话 `session-YYYYMMDD-NNN`；卡片 `card:<knowledge_id>`

## 2. 审核状态

`review_status` 取值：
- `verified`：内容已核对（基础常用词、明确语法、原创题）
- `needs_review`：由模板/推断产生，或读音用法未二次核实
- `index_only`：仅索引外部资源，不含正文（版权原因）
- `original`：本题库原创
- `generated`：**课程专用**。由程序从已校验种子组装、可运行且通过 10 类强校验，
  但未经人工逐课精修。绝不等同于人工精修教材，也不得改标为 `verified`。

**不允许把推断内容标成 verified。** 不清楚就标 `needs_review` 并写进 `notes`。

## 3. knowledge/seeds/vocabulary.jsonl

```json
{"id":"V0001","surface":"食べる","kana":"たべる","romaji":"taberu","pos":"動詞/一段",
 "meaning_zh":"吃","jlpt":"N5","frequency":1,
 "examples":[{"ja":"朝ごはんを食べます。","zh":"我吃早饭。","grammar_ids":["G0002"]}],
 "confusables":["V0002"],"notes_for_zh":"中文「吃」不能直接套用宾语；日语用 を 标记对象",
 "tags":["food","daily"],"source_ids":["S001"],"review_status":"verified"}
```
`frequency` 为 1–5 的常用度分级（5 最高频），非精确词频。`pos` 用斜杠分类即可。
`confusables` 引用本文件内的 id。汉字词必须在 `surface` 用日语实际书写形式。

## 4. knowledge/seeds/grammar.jsonl

```json
{"id":"G0001","pattern":"N は N です","meaning_zh":"…是…",
 "connection":"名詞 + は + 名詞 + です","usage":"判断句，介绍身份/事物，礼貌体",
 "examples":[{"ja":"私は学生です。","zh":"我是学生。","vocab_ids":["V0003"]}],
 "prerequisites":[],"compare":[{"id":"G0007","diff":"は 提示主题，が 提示新信息/主语"}],
 "common_errors":[{"wrong":"私は学生だ。","why":"混用简体与礼貌体","fix":"私は学生です。","learner":"zh"}],
 "jlpt":"N5","tags":["sentence"],"source_ids":["S001"],"review_status":"verified"}
```
`prerequisites` 必须引用本文件内已存在的 id，且 id 数值更小（保证拓扑可排序）。
**硬约束**：依赖动词变形的语法，其 `prerequisites` 必须包含对应变形语法 id。

## 5. knowledge/seeds/kanji.jsonl

```json
{"id":"K0001","char":"日","onyomi":["ニチ","ジツ"],"kunyomi":["ひ","か"],
 "meaning_zh":"太阳；日子","vocab_refs":["V0004"],"jlpt":"N5",
 "zh_trap":"中文读 rì；日语「日本」にっぽん/にほん、「三日」みっか 训读不固定，不可按中文音推",
 "source_ids":["S007"],"review_status":"verified"}
```
面向中文母语者：**不要求机械抄写**，重点在日语音读/训读与实际用法验证。

## 6. knowledge/seeds/questions.jsonl

```json
{"id":"Q0001","type":"mcq","prompt_ja":"私は学生___。","prompt_zh":"选择正确助词",
 "options":["は","です","が","を"],"answer":"です","rubric":"选 です 得 1 分，其余 0 分",
 "rationale":"判断句礼貌体结尾用 です；は 已在主题后出现",
 "knowledge_ids":["G0001"],"difficulty":1,"source":"original",
 "review_status":"verified","audio_text":"私は学生です。","expected_production":null}
```
`type` 枚举：`mcq` / `fill` / `listen` / `read` / `reorder` / `error_correct` / `translate` / `free_production` / `dialogue`。
- `difficulty` 1–5。
- `free_production` / `dialogue` 必须给 `rubric`（分点评分准则）而不是单一 `answer`。
- `listen` 必须有 `audio_text`（交给浏览器 TTS 朗读），`answer` 为要听写/选择的内容。
- `reorder` 的 `options` 是打散的词块数组，`answer` 是正确顺序编号（如 `"2,1,4,3"`）。
- 每题必须能追溯到 `knowledge_ids`。

## 7. knowledge/seeds/materials.jsonl

```json
{"id":"M0001","kind":"reading","title":"自己紹介","text_ja":"はじめまして。私はリンです。",
 "text_zh":"初次见面，我是小林。","audio_text":"はじめまして。私はリンです。",
 "audio_url":"","duration_sec":30,"level":"N5","topic":"greeting",
 "vocab_ids":["V0003"],"grammar_ids":["G0001"],"known_ratio":0.9,
 "source_ids":["S003"],"license":"original","url":"","review_status":"original"}
```
`kind`：`reading` / `listening`。**外部版权教材一律 `index_only` + 只填 `url`，不填 `text_ja`**；正文只允许原创或明确开放许可（Tadoku CC BY-NC-ND 4.0 亦仅索引，不复制正文）。
`known_ratio` 用于可理解输入选材（目标 0.90–0.95，即生词率 5–10%）。

## 8. curriculum/curriculum.json

```json
{"meta":{"version":"1","days":80,"minutes_per_day":60,"generated_at":"...","generator":"..."},
 "days":[{"day":1,"phase":"P1","theme":"…","scene":"…","objectives":["…"],
  "new_vocab_ids":[],"new_grammar_ids":[],"new_kanji_ids":[],
  "review_knowledge_ids":[],"material_ids":[],
  "blocks":[{"min":10,"type":"review","desc":"…"}],
  "question_ids":[],"rubric":"…","minutes":60,"completion":"…",
  "assessment":"diagnostic","source_ids":[],"review_status":"verified"}]}
```
- `phase`：`P1`(1-10) / `P2`(11-25) / `P3`(26-45) / `P4`(46-65) / `P5`(66-75) / `P6`(76-80)
- `assessment`：`none|diagnostic|weekly|stage|midterm|n3_readiness|final`；同一天只能有一个值（不叠加）
- `blocks[].min` 合计必须等于 `minutes`
- 所有 id 引用必须在种子库中存在（构建时强校验，缺失即失败）
- 引入新知识必须满足其 `prerequisites` 已在更早的天数出现

## 9. web/data/day-NNN.json（每日页面输入）

由 `scripts/build_site.py` 从 curriculum + seeds 组装，页面只读：

```json
{"day":1,"phase":"P1","theme":"…","scene":"…","objectives":[],"minutes":60,
 "blocks":[{"min":10,"type":"review","desc":"…"}],
 "vocab":[{"id":"V0001","surface":"…","kana":"…","meaning_zh":"…","jlpt":"N5"}],
 "grammar":[{"id":"G0001","pattern":"…","meaning_zh":"…","connection":"…","example":"…"}],
 "kanji":[{"id":"K0001","char":"…","onyomi":[],"kunyomi":[],"zh_trap":"…"}],
 "questions":[{"id":"Q0001","type":"mcq","prompt_ja":"…","prompt_zh":"…","options":[],"answer":"…","rationale":"…","audio_text":"…","rubric":"…","difficulty":1}],
 "materials":[{"id":"M0001","kind":"reading","title":"…","text_ja":"…","audio_text":"…","url":"…","license":"…"}],
 "viz":{"day":1,"phase":"P1","new_count":0,"review_count":0,"question_count":0},
 "assessment":"diagnostic"}
```
**页面绝不内嵌答案以外的状态数据**；`answer` 仅用于本地即时判分，答题结束后由页面生成回传码。

## 10. 回传码（网页 → 本地 SQLite）

页面把答题结果序列化并 Base64URL 编码，用户复制回 WorkBuddy 会话：

```
NH80R1.<base64url(json)>
```
payload：
```json
{"v":1,"day":1,"session":"session-20261106-001","ts":"2026-11-06T15:00:00+08:00",
 "results":[{"qid":"Q0001","answer":"です","correct":true,"hinted":false,"seconds":12,"error_type":null}],
 "minutes":18,"source":"web"}
```
`scripts/nh80.py import-web-result '<回传码>'` 负责校验、去重（按 `session+qid` 幂等）、写入 `attempts` 并触发 FSRS 排期。
任何手写/篡改的码必须被拒绝（结构校验 + 未知 qid 拒绝 + 重复导入拒绝）。

## 11. 掌握状态机（五阶段，确定性）

`stage`：`unseen` → `initial_understanding` → `hinted_recall` → `independent_recall` → `delayed_recall` → `transfer`

判定规则（全部由脚本算，AI 不参与）：
- 一次答对 **最多**推进到 `independent_recall`，不得直接判掌握。
- 进入 `delayed_recall`：距首次见面 ≥ 2 天，且无提示答对。
- 进入 `transfer`：在**不同题型或不同素材语境**中正确使用 ≥ 2 次，且累计延迟答对 ≥ 3 次，且时间跨度 ≥ 7 天。
- `mastered` 布尔值 = `stage == "transfer"` 且 `rolling_accuracy >= 0.85`（Bloom/Guskey 常用阈值，见 research/learning_science.md；不宣称是官方规定）。
- 任何一次 `error_type = forgetting` 或连续 2 次错误 → 退回 `hinted_recall` 并强制安排补救。

## 12. 错误类型与补救映射

`error_type` 枚举：`forgetting` / `meaning_confusion` / `particle` / `conjugation` / `listening` / `comprehension` / `kanji_reading` / `orthography` / `other`

| 类型 | 补救（由脚本生成任务，AI 负责讲解措辞） |
|---|---|
| forgetting | 立即缩短间隔重排 + 主动回忆卡（不给提示） |
| meaning_confusion | 易混词最小对立对练习（confusables） |
| particle | 助词填空 + 场景替换，同语法交错 |
| conjugation | 变形表重现 + 变形题组（前置语法回退检查） |
| listening | 降速 TTS 复听 + 听写 `audio_text` |
| comprehension | 降级素材（更低 level、更高 known_ratio） |
| kanji_reading | 音读/训读对照 + 词汇语境验证 |
| orthography | 假名→汉字书写选择 |

交错练习**只用于易混语法/助词/变形**（元分析显示词汇分类 blocking 更优），词汇与汉字按主题分块 + SRS。

## 13. FSRS

- 使用 `scripts/vendor/fsrs`（**py-fsrs 6.3.1, MIT**，官方实现），不自造公式。
- `desired_retention = 0.9`，`enable_fuzzing = False`（可复现/可测试）。
- rating 映射：答错=`Again(1)`，提示后答对=`Hard(2)`，独立答对=`Good(3)`，新语境流畅答对=`Easy(4)`。忘记**必须** Again，不能记 Hard。
- 卡状态存 `fsrs_cards`，用官方 `Card.to_dict()/from_dict()` 序列化。
- 时间一律 UTC aware datetime，本地展示用 Asia/Shanghai。

## 14. 禁止事项

1. 不把外部受限教材正文写进仓库。
2. 不虚构调研结果；未核实一律标注。
3. 不把「读完页面/AI 文本」记为完成；必须有 `attempts` 记录。
4. 不因为进度落后而降低测试难度；只能减内容、补基础、调任务。
5. 不声称平台自动传递每日状态；跨会话状态只能来自文件。
6. 不引入向量数据库；检索用 SQLite FTS5 + 结构化关系。

## v5.1 修订（2026-11-07，优先于旧版示例）

- 课程由 `curriculum_v5.py` 生成 150 天，网页 42 分钟 + 会话 18 分钟（听力包含在 42 分钟内）。`blocks` 是分钟唯一真源，包含句子输出。
- 保持 2700 词完整覆盖时，16/11 词只是不可同时实现的旧目标；未经用户选择不丢弃 525 词。实际每日数量必须如实显示。
- 主题、can_do 从当天语法及释义生成，不再宣称未编排的情境主题。
- 新听力材料使用 seeds 的原创 `ai_draft` TTS 场景变体，每条三道理解题；`duration_sec:0` 表示未测，`duration_estimate_sec` 只是估算，不冒充真实播放时长或真人音频。
- v5 当日题由共同生成函数输出，CLI build 注册到本地 questions（保留旧题兼容历史记录）。题号带内容摘要，修改题目不复用旧题号。Worker 使用打包的答案表，不从公开静态目录读取答案。
- 页面练习只含选项及哈希，不含 answer/rationale；句子练习不下发参考译文。哈希供离线自评，可被枚举，不构成保密机制。
- `nh80.py build/init` 是状态库写入入口；构建题目通过该入口事务登记并审计。拉取事件仍由本地重判，不信客户端 correct。
- brief 是可重新生成的任务书，默认刷新；report 是人工记录，默认保留。
- 浏览器提交只有服务器成功确认后才显示已记录；失败保留本次作答及会话标识，允许重试。
- `ai_draft` 是未人工审校的内容状态；不得升级为 verified。
- v5.1 事件扩展：`events.session_payload` 存同一批提交的 review_ratings 与当天句子草稿（不含判分）。仅带密钥的 GET 可读；cloud_sync 将其交给 CLI，复习走现有 apply_review_rating，草稿存 days/day-NNN/web-drafts.json 供教师批改，不据此算掌握或完成。
