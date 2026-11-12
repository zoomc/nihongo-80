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

## v5.2 资源索引与本机音频（2026-11-07）

- `knowledge/resources.json` 是外部免费资源的链接索引，不存受限正文或音频；每项注明官方来源、用途和许可边界。链接免费不代表可转载，Tadoku 链接注明 NPO 多言語多読。
- `scripts/audio_assets.py` 只从原创、AI 草稿的 M0096–M0140 生成本机 macOS 合成语音；输出本机 `data/audio/Mxxxx.m4a` 与 `manifest.json`，均为不发布、不提交的生成物。清单记录原文 SHA-256、声音与实测时长；原文变更必须重新生成，本机使用方不可使用哈希不符的旧音频。
- 音频是机器合成、非真人、未人工试听或验证发音；测得文件时长不证明难度、学习时长或理解质量。v6 线上页面改用 `web/audio/` 的 Kokoro 合成音频，浏览器 TTS 仍作为播放失败时的降级。

## v6 完整个人学习版（2026-11-07）

用户已授权采用最佳完整方案，不再等待词量选择：150天保持2700词资源覆盖；每天必学词设常规16/听力11上限，其余作为同日可选拓展，仍可查阅、发音、练习，不以选学完成阻塞当天。正文分别显示必学与拓展，实际数量由排课生成；复习与会话优先必学。

- 词汇可新增 `ko_hint`（韩语释义或迁移提示）和 `ko_status`（`dictionary`/`ai_gloss`/`existing_hanja`/`native_or_loan`），保留原 ko_hanja；AI释义明确标识，不能将逐字韩音拼接当作已核实韩语词，也不得谎称人工审校。
- `knowledge/resources.json` 记录官方外部资源、使用方式和许可依据；版权不明或第三方音频只保存官方链接，不复制分发。
- `open_audio_assets.py` 用 Kokoro-82M 为自有原创文本生成 `web/audio/`（含 manifest 与 NOTICE），构建器按文本 SHA-256 核对失效；`audio_assets.py` 是 macOS `say` 的本机备选，产物只落 `data/audio/`、不发布不提交。两者都不调用付费云 TTS。
- `knowledge/seeds/assessments.jsonl` 存原创周测/阶段题；`assessment_v6.build_for_day(day)` 返回兼容 qid/id/type/prompt/options/answer/knowledge_ids/h/oh 的确定性题目。理解题knowledge_ids为空，CLI只记证据，不推断知识卡掌握；不是JLPT官方分数。公开投影不下发标准答案。
- 云端所有写入要求个人访问凭据，避免公开无鉴权写接口造成消耗；不启用 Workers Paid、R2、KV、AI等付费功能。生产部署前核验账户计划与用量，无免费资格时不部署到收费环境。
- 历史未知题号保留原始事件到隔离记录；可以由旧提交对应Git构建重建答案，有证据才重判，不能猜测。课程更新后的旧本机载荷保留、提示恢复，不混入新版本提交。
- 每日十句中前三句必做、其余七句拓展；同样保留全部1500句资源。教师通过 `confirm-output --day N --file <json>` 录入三句批改、两句自主语法造句、三词主动回忆（原文与反馈必须非空），CLI审计并写入output_reviews。finish-day须客观题达标且有输出验收，不能只凭选择题算整天完成。

## v5.2 补充：可公开合成音频

- Apple 系统语音产物仅放本机 `data/audio/`，不上传公开站点或 Git。另可使用 `scripts/open_audio_assets.py` 基于 Apache-2.0 的 Kokoro-82M v1.0（jf_alpha）和明确许可的 UniDic 生成原创草稿的公开音频到 `web/audio/`；资源说明必须注明模型、字典来源及其许可。
- 公开音频同样只表示机器合成，未经人工验收的发音与难度不可标 verified；manifest 包含文本哈希、声音和实测时长。素材变更后接入方必须拒绝旧哈希，缺失时退回设备端 TTS。

## v7 修订（2026-11-08）

- **题目契约**：`quiz_v5.py` 每题必须恰好 4 个选项、答案在选项内、4 个选项 FNV 哈希互异；
  干扰项排除与正确答案相同的中文释义；中文释义里出现词形（如「四」→「四（し／よん）」）时
  改出「假名 → 词形」题，避免剧透。题目顺序固定为汉字 2 + 语法 1 + 词汇 2 + 复现 1，
  阶段测替换尾部 3 题时仍保留当天汉字与语法题；`day_questions` 对全部 1035 题做不变量断言。
- **语法覆盖**：按天轮换当天新语法；复现题在词汇/语法/汉字间轮换；课程 `meta.honesty` 明确
  「6 题为当天新内容抽样，不覆盖全部条目」，不把抽样成绩说成全量掌握。
- **课程**：听力素材按 `N5<N4<N3` 数值排序，禁止难度倒挂；`is_listening_day` 阈值与
  `listening_from=47` 对齐；复习快照 `review_knowledge_ids` 三类（V/G/K）都复现，并标注
  「静态预览，权威队列见 `learning.due_queue()`」；`lesson_core` 取 6 条；同义语法至少错开 7 天。
- **内容**：修 23 条硬错误（含把合法日语判错的 G0148/G0066、例句与词条无关的 V1469/V2462、
  音读混入外来单位词的 K0172/K0296/K0372、V1117 病句、V0349 韩语错配等）；26 条 `pos="词"`
  按标准日语词性补正；3 条语法 jlpt 错标归位；9 条测评标签统一为 `self_check`。
- **听力原创度**：M0096–M0140 共 135 道题重写，`audio_text`/`text_ja` 逐字不动
  （manifest 的 `text_sha256` 必须继续一致），9 个模板各自的 5 变体 Q3 答案互不相同。
- **外部资源**：`knowledge/resources_v7.json` 27 源；`inline` 4 条 Wikimedia Commons
  PD / CC BY-SA 音频可在本页播放并逐文件署名；`link` 15 条只跳转原站；`none` 8 条列明不采用原因。
  **不下载、不转存、不热链受限音频**；每日精听主线仍是 45 篇原创合成音频。
- **数据卫生**：`_build_v5` 写入答案表后删除 DB 中不在本次 keys 的历史孤儿题；
  `cmd_import_web` 拒绝没有 `day` 的题，不再用 payload 的 day 兜底。
- **完成门控不变**：`finish-day` 仍需全部题作答、正确率 ≥70% 且教师输出验收通过。
  6 题日最多错 1 题、9 题（听力日）最多错 2 题；不存在「听力日必须全对」。

## v7.1 收尾修订（2026-11-08）

- **开放音频格式**：`knowledge/resources_v7.json` 的 4 条 `inline` 源新增 `mp3_url`，指向 Wikimedia
  官方 `transcoded/.../*.mp3`（2026-11-08 实测 206 `audio/mpeg`）。`build_v5_site.py::audio_card`
  给每个 `<audio>` 输出 mp3 + Ogg 两个 `<source>`，Safari 不再需要跳文件页。仍是外链播放，
  未下载转存、未自行转码、未改编，署名与许可链接不变。
- **环境隔离**：preview 绑定独立 D1 `nihongo80-preview`（三段 migration 已应用），与 production
  `nihongo80` 数据互不相通。`wrangler.jsonc` 顶部注释改为真实配置口径，移除过时的
  `REPLACE_WITH_D1_ID` 与「不含任何 database_id」表述；`0001_events.sql` 的 `day` 注释 80→150。
- **发布守卫**：新增断言「恰好两个且互不相同的 `database_id`、`database_name` 含
  `nihongo80-preview`」，拒绝共用库的回退；输出标明 `D1 prod` / `D1 preview (isolated)`。
- **回归**：`tests/test_v7.py` 新增 3 项（双格式源、D1 隔离、守卫真的会拦截共用库回退），
  Python 测试 41→44 项。
- **静态音频 Range**：实测 `audio/*.m4a` 对 `Range` 返回 200 全量（无 `accept-ranges`），
  Commons mp3 返回 206 + `content-range`。给静态 m4a 加 Range 必须把 `/audio/*` 放进
  `run_worker_first`，会让所有音频请求进入 Worker 请求额度，与「静态绕过 Worker」冲突；
  单篇仅 0.56–0.62 MB 且 `preload="none"`，实测播放/拖动正常，故**评估后不引入**，如实记录。

## v8 网页学习方式（2026-11-08，按用户本轮要求）

- 今日复习和今日新词均提供卡片/列表切换，默认列表，支持明确的显示全部、遮中文、遮日语；遮中文时同时遮韩语释义以免泄题。点击或键盘可临时揭示。视图与遮盖偏好保存在设备。
- 网页不再要求手写句子；1500句保留种子参考答案，由sentence_choices生成四选一理解练习，每天3题必做、7题拓展；六题综合与听力三题仍保留。所有答案由同一CLI构建登记、本地重判，句子理解题只记录证据，不计为自主产出。
- 新增句子题不改变day_questions既有1035题；总答案表为2535题。当天question_ids只要求基础题、听力及3道句子必做题，拓展题不影响达标分母。
- 网页practice_mode=choice经云端原始元数据传回本地，CLI根据完整题号与本地重判成绩计算是否达标；该模式不要求confirm-output或手写记录。旧会话教师输出验收仍兼容，但不得据选择题宣称口语产出或掌握。
- 今日新词、汉字与语法的可识别学习片段在语法说明和例句中用strong突出；语法标题整体加粗，例句中的具体词形/变形与语法片段按本地明确匹配突出，不整句乱加粗或修改原文。
- choice模式原始作答导入后，由同一CLI自动执行finish-day计算（完整必做题＋本地正确率≥70%），无需教师提交手写验收文件；未答齐或未达标只保留incomplete。网页保存只说明云端收到，权威完成仍在本地导入后计算，不信客户端correct。

## v9 练习与个人复习同步（2026-11-08）

- 日常语法讲解区始终可读，不受全局遮盖控制；红色突出今日词句，蓝色标识句型/练习导航。复习、新词和五日复习单元仍支持遮中文/日语；错误和遗忘使用红色文字标记，不熟使用橙色，不能只靠颜色表达状态。
- 日常必做题规模不增加。新增可选翻页练习覆盖当天必学词（意义、读音）及全部当日语法（含义、接续/语境）；每5天生成一个五日复习单元，列全该区间词汇与语法，20道复习练习为抽样，不声称穷尽测验或掌握。
- 个人记录不编入公开静态HTML/JSON。公开catalog仅含课程内容、题目和内容ID；私有状态必须经个人口令读取。浏览器点击自评/答题即本机排队、可用时批量同步；断网、无口令或超预算保留待同步，重试按事件ID/session+qid幂等。
- D1保存原始题目事件与独立自评事件，不以自评判掌握。SQLite仍为FSRS/能力卡权威真源，仅nh80 CLI写；浏览器云端标记为即时练习记录，FSRS到期建议带最后会话同步时间。
- CLI study-sync按游标拉取作答与自评，全部成功才推进游标，生成私有data/review/context.json与复习说明，再发布精简到期计划到D1。会话入口和AGENTS明确要求开始/结束执行该命令，不宣称WorkBuddy平台跨会话自动注入。
- 云端补传的作答与自评均按本机成功导入时刻排期；自评的服务端 `created_at` 仅作为原始时间写入审计，不用来倒推 FSRS。若现有卡的 `last_review` 晚于本机导入时间或缺少时区，拒绝本次自评并保留游标等待处理，不静默修正时间。
- `nh80 import-file` 支持 v9 导出的 `version:1,pending` 队列：整份先校验，按 day/session 分批复用本地客观题重判，忽略网页传入的正确与知识点；`replay-` 使用 teacher 模式，其他会话使用 choice。独立自评以 `rating-<event_id>` 去重，与云同步共享幂等键，只排期不判掌握。
- 服务端判分从每日日志键静态分片读取规范化答案SHA-256及knowledge_ids；公开分片无明文答案，仍可枚举选项，不用于防作弊。私有generated-key.json继续供本地独立重判和对账，但不再整体打包进Worker。
- API增加GET /api/study、POST /api/reviews、POST /api/study-plan、GET /api/reviews，均先鉴权再碰D1。新增sessions元数据表去重载荷、rating_events表记录自评、study_projection表保存CLI发布的派生计划；D1原有events增加knowledge_ids列。生产/预览继续隔离，不创建额外云产品。
- 同一session可追加不同题，但元数据必须一致；有变化返回409并保留本机记录，使用新session重传，不静默丢弃。作答和自评每请求最多40项，为D1 Free单次调用50查询保留余量。
- 应用预算使用去重后的新事件数：每日1000、总计20000；新事件不重复存整批元数据，个人计划上限128KB，元数据上限16KB，失败保留离线导出。所有状态读写均有界且无自动轮询，不升级付费套餐。

## v10 修订（2026-11-08）：页面只留内容 + 完成按钮进度链路

用户明确否决了 v8/v9 叠加出的复杂 UI，以下契约优先于前面所有版本的页面约定。

- **页面结构**：每日页只有 `review / vocab / grammar / questions` 四个内容块 + 一个「完成」按钮。
  顶部 `modeBtn`、分钟数、`nav.toc`、`study-toolbar`、站点外链、提示文案，底部口令 / 同步 /
  导出 / 保存 / 再练一轮 / 课程翻页 / 署名行，一律删除；每日页不再加载 `assets/study.js`。
  `build_v5_site.py` 在构建期生成完整 HTML，`app.js` 只做遮挡、朗读、判分、完成上报。
- **遮盖下沉**：`applyScope(section, mode)` 只作用于该 section 内的 `[data-role]`；
  新词与语法各一个 `.mask-switch`（all/zh/ja/both），偏好按 section 存 localStorage，互不干扰。
- **练习一整块**：`merge_questions()` 以 `curriculum.question_ids` 为必做骨架，
  再按 `knowledge_ids` 去重（每点最多 2 题）吸收选句 / 综合 / 词法练习，
  最后用 `coverage_question()` 为未覆盖的当天新词（含选学拓展）与新语法各补 1 题。
  硬断言：150 天全部覆盖、qid 唯一、恰好 4 选项、`h ∈ oh`、无 `answer`/`rationale`、总量 ≤ 60。
  听力日音频与脚本并入练习块，`id="listening"` 保留但不再是独立 section。
- **小日语文字 + 发音**：中文正上方必须有 `.kana-line` 小假名，日文汉字用 `<ruby>` 注音，
  每条例句带 `data-speak`（`speechSynthesis`, `ja-JP`）。`ruby_text()`/`kana_hint()` 只做
  当天词表最长匹配，文案明确写「读音提示」，不冒充逐字转写。
- **完成 → 云端**：`POST /api/progress` 写 D1 `study_progress`（`day INTEGER PRIMARY KEY`，
  幂等覆盖，全表 ≤ 150 行），页面**不带任何密钥或口令**；服务端靠 Origin 白名单、64KB 体上限、
  字段白名单、按天覆盖、每 IP/日限流兜底。`questions[].correct` 是客户端自算，
  整份标 `self_reported=1`，服务端不重判、不作为掌握依据。
  `GET /api/progress?day=N|latest=1` 必须 `X-NH80-Key`。
- **agent 读取**：`skills/nh80-progress/SKILL.md`（仓库内 + 项目级 + 用户级三份）与
  `scripts/progress_read.py`；任何能跑 Python 的 agent 都可用。agent 只读云端、不回写，
  不据此判「已达标」；本机 `data/state.db`（`finish-day`）仍是唯一掌握权威。
- **移除口令链路**：`study_ui.py` 不再注入「学习口令 / 同步 / 导出待同步记录」，
  `flush()` 改为纯本地合并，不再 POST `/api/events`；旧 `/api/events`、`/api/reviews`、
  `/api/study` 路由保持不变但每日页不再调用。
- **数据卫生**：明文答案表 `deploy/worker/src/generated-key.json` 移出版本库并 gitignore；
  Worker 只用公开哈希分片 `web/data/grade/day-*.json`。`release_guard.py` 新增合并题契约校验。
- **缓存**：SW 版本升到 `nh80-v10-*`，HTML 模板纳入 revision，避免只改模板时命中旧缓存。
- **完成门控不变**：`finish-day` 仍要求 `curriculum.question_ids` 齐全且正确率 ≥70%。
  页面合并题与 CLI 门控 qid 集合不同，因此**页面「完成」不等于本地已完成**，文档不得混淆。

## v11 · 120 天课程

- 120 天，每天 60 分钟（网页 42、会话 18）。Day 1–30 N5、31–60 N4、61–120 N3；全部词汇、语法、汉字按级别重排，词汇保留必学和拓展，语法先修必须在前一天或更早。
- 保留 45 篇精听、39 道既有测评和 1500 条句子资源。按新课程日期分配素材；零基础期补假名和短句听辨，后期加入官方题型练习任务，计时整卷另安排。
- 保留 v10 每日页结构，新词区内折叠显示当天汉字、常用读音与韩语字音。当前网页完成快照使用 v2，旧页面不得写入新课程日；历史快照保留在旧表，当前进度读写独立的 `study_progress_120` 表。历史本地学习数据不因排课清空。
