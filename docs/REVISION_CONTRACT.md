# v4 修订契约（P0/P1/P2 整改的唯一口径）

> 本文件是 2026-11-07 深度审查后整改的**实现契约**。所有模块必须按此实现，
> 不得各自发明字段名或语义。修改本文件需同时改 `tests/` 中的契约测试。

## 0. 不变式（任何改动都不得破坏）

1. `data/state.db` 仍是学习状态唯一真源；`student/*.json` 只是只读镜像。
2. 网页永远不写状态。网页只产生**原始作答事件**；判分、掌握、FSRS 一律在本地权威侧完成。
3. FSRS 公式不重写，继续用 vendored `py-fsrs` 6.3.1；只重做**事件采集与评分契约**。
4. 一次答对绝不直接 `mastered`；`mastered` 只在 `transfer` 阶段且滚动正确率 ≥ 0.85 时成立。
5. 所有新增/修改的行为必须能在 `python3 -m unittest discover -s tests` 下被验证。

## 1. 题目 → 知识点：目标与语境分离（P0-1）

`knowledge/seeds/questions.jsonl` 每条新增三个字段：

```json
{
  "target_knowledge_ids": ["G0001"],
  "context_knowledge_ids": ["V0001", "V0078", "K0036"],
  "targets": [{"id": "G0001", "capability": "usage"}],
  "knowledge_ids": ["G0001", "V0001", "V0078", "K0036"]
}
```

- `knowledge_ids` 保留为 `target + context` 的并集（向后兼容、超纲检查继续用它）。
- **只有 `targets` 里的 (id, capability) 允许改变掌握状态与 FSRS 排期。**
- `context_knowledge_ids` 仅表示“出现在题面里”，答对不得提高其掌握度，也不得为它建卡。
- 校验（`curriculum.validate` + 新测试）：每条题 `targets` 非空；`targets ⊆ knowledge_ids`；
  `target + context == knowledge_ids` 无重复；`capability` ∈ 下表。

### 1.1 能力维度（capability）

| 值 | 含义 | 典型题 |
|---|---|---|
| `meaning` | 看汉字/词形认意思 | mcq/fill 问中文意思 |
| `reading` | 看汉字读假名、听音辨词 | 读音题、kanji 题、listen 题 |
| `listening` | 听句子/对话取信息 | listen、听解题 |
| `usage` | 在句子里正确使用（助词/接续/变形） | fill、reorder、error_correct |
| `production` | 自己产出（说/写） | free_production、dialogue、translate |

判定规则写在 `scripts/audit_questions.py`，确定性、可复现：
- 答案串与某语法 `pattern`/例句匹配 → 该语法 `usage`
- 答案串等于某词 `surface` 或 `kana` → 该词 `usage`（`listen` 题则 `listening`；问中文则为 `meaning`）
- 答案含某汉字音读/训读且题面问读音 → 该汉字 `reading`
- 无命中时取 `knowledge_ids[0]`，并在报告中列为 `fallback`
脚本必须输出 `reports/question_targets.md`（每条题的目标/语境/能力/命中理由），供人工复核。

## 2. 记忆状态：按能力分卡（P0-1 延伸）

新增表（`core.SCHEMA`）：

```sql
CREATE TABLE IF NOT EXISTS capability_state (
  kid TEXT NOT NULL, capability TEXT NOT NULL, stage TEXT DEFAULT 'unseen',
  attempts INTEGER DEFAULT 0, correct_attempts INTEGER DEFAULT 0,
  hinted_count INTEGER DEFAULT 0, independent_count INTEGER DEFAULT 0,
  delayed_count INTEGER DEFAULT 0, distinct_contexts TEXT DEFAULT '[]',
  last_review_day INTEGER, last_review_at TEXT, rolling TEXT DEFAULT '[]',
  rolling_accuracy REAL DEFAULT 0.0, updated_at TEXT,
  PRIMARY KEY (kid, capability)
);
```

- `fsrs_cards.knowledge_id` 改存 **`kid|capability`**（如 `V0001|meaning`）。旧数据无 `|` 视为 `meaning`（语法为 `usage`，汉字为 `reading`）。
- `knowledge_state` 仍按 `kid` 一行，作为**聚合视图**：`stage=max(各能力 stage)`，
  `attempts/correct_attempts/...=sum`，`mastered` 还需满足“≥2 个能力达到 independent_recall”。
- `learning.record_attempt()` 只对 `targets` 逐个更新 `capability_state` 与该能力卡。
- `learning.due_queue()` 返回 `{kid, capability, card_key, due, stage, stability, ...}`。
- 迁移：`core.init_db` 之后调用 `learning.migrate_v4(conn)`，把旧卡 `kid` 补成 `kid|默认能力`（幂等）。

## 3. 作答事件契约（P0-2 / P0-3）

### 3.1 前端（`web/assets/app.js`）

- 点「看答案 / 解析」= 显式声明放弃独立回忆：立即写
  `r.hinted=true`、`r.revealed_before_submit=true`、`r.revealed_at=Date.now()`，并 `save()`。
- 已揭示后再点「提交答案」：`hinted` 必须保持 `true`，按钮文案改为
  「提交（已看答案，记为提示学习）」，提交后解析区顶部显示
  「本次为提示学习，不计为独立回忆」。
- 提示按钮（`显示提示`）与「看答案」同等处理，已揭示/已提示都不得回退为 `hinted=false`。
- 回传码 `results[]` 必须带 `hinted`、`revealed_before_submit`、`pre_reveal_answer`（揭示前输入框内容）。
- 复习自评前必须先「显示答案」，未显示不得评分；评分按钮在显示答案后才启用。

### 3.2 后端（`scripts/nh80.py` + `scripts/learning.py`）

- `import-web-result` **不允许**信任 `results[].correct`。流程固定为：
  1. 取题库标准答案，用 `learning.grade_objective()` 重新判分；
  2. 前端 `correct` 只用于统计 `disagreements`，写审计日志，绝不进入掌握/FSRS；
  3. `hinted = hinted or revealed_before_submit`（逻辑或，无法被前端下调）；
  4. 开放题（`free_production/dialogue/translate`）一律挂起待 `grade-open`。
- 返回体新增 `regraded`、`disagreements`、`hinted_forced` 字段，便于对账。
- 前后端字符串标准化必须同构：NFKC → 去所有空白（含全角空格）→ 去句末 `。．.！!？?` →
  `，`转`,`。Python 见 `learning.norm_answer()`，JS 见 `app.js norm()`；两端口径由
  `tests/test_grading_contract.py` 用同一组用例锁定。

## 4. 复习队列统一（P0-4）

- `curriculum.py` 的 `review_plan` 明确改名为**预习建议**（字段名保留，新增 `planned_only: true`），
  文案不得再写「今天该复习」。
- `scripts/build_site.py` 构建时只读打开 `data/state.db`（不存在则跳过），为每天注入：

```json
"review": {
  "source": "fsrs" | "planned",
  "generated_at": "2026-11-07T...",
  "due": [{"kid":"V0001","capability":"meaning","surface":"私","kana":"わたし",
           "zh":"我","due":"2026-11-07T...","overdue_days":0,"stage":"independent_recall"}],
  "planned": [ ...旧 review_plan 结构... ]
}
```

- 页面「今日复习」规则：
  1. `review.due` 非空 → 显示真实 FSRS 到期项，标题「今天真正到期（FSRS）」，并显示每项到期时间/逾期天数；
  2. `review.due` 为空且 `planned` 非空 → 显示「预习建议（尚未建立记忆记录）」并说明“这些不是 FSRS 到期项”；
  3. 两者都空 → 「今天没有到期项」。
- `next_hint_zh` 若该卡已有 FSRS 记录，必须用真实 `due` 反算「大约 Day X / 具体日期」，不得再用固定间隔推算。
- 新增 `python3 scripts/nh80.py sync-web`：写入后重建站点（等价 `build`，语义更明确）。

## 5. 掌握门控（P1-4）

`learning.gate(conn, day, payload)` 返回：

```json
{"blocked": [{"kid":"G0012","prereq":"G0008","prereq_stage":"initial_understanding"}],
 "deferred_grammar_ids": ["G0012"], "actions": [{"type":"gate_defer","detail":"..."}]}
```

- 规则：某新语法 G 的任一先修 P 聚合 `stage` < `independent_recall` → 当天不引入 G，
  改写 `plan_adjustments`（`type=gate_defer`）并追加 `review_tasks`（先修补 P）。
- `start-day` 必须把 `blocked` 写进 briefing 的「门控」段，并明确告诉教师：
  先补先修，不推进被推迟的新语法；`finished` 判定不因推迟而放水。
- `nh80.py gate --day N` 提供独立入口。

## 6. 完成状态（P0 附带）

- `sessions` 新增 `passed INTEGER`。`finish-day`：
  - `passed=1` → `status='finished'`
  - `passed=0` → `status='incomplete'`，**不增加**完成天数；
- `learning.metrics().completed_days` 只统计 `status='finished' AND passed=1`；
  另返回 `incomplete_days`。
- `report.py` 的周报/阶段报告同步改用 completed 口径。

## 7. 课程对齐（P1-2）

- 每天新增 `scene_topic_key`（素材 topic 英文键）、`scene_topic`（中文标签）、
  `topic_match`（`exact|partial|review`）。
- 选材：按级别窗口（N5 1–25 / N4 26–45 / N3 46–65）把原创素材按 topic 分组，
  每天取**同一 topic 的 reading + listening 各一篇**；同 topic 不足时退化为同级别最近 topic 并标 `partial`。
- 新知识按“当天 topic 亲和度”分配：在级别窗口内，对每天从剩余池中取
  `ceil(池大小/窗口天数)` 项，排序键 `(亲和度降序, frequency 降序, id)`。
  亲和度 = topic 词表命中次数（`TOPIC_LEXICON`），词表必须写进 `scripts/curriculum.py`。
- `can_do` 由 `SCENE_TASKS[topic]` 模板生成，必须包含当天 topic 中文标签与至少一个当天语法；
  不再用 `CANDO_BANK` 按天轮换。
- `lesson_core` 第一句必须来自当天素材（`_material_pairs` 命中）；不足时才用当天新知识例句，
  并在 `lesson_core[i].origin` 标注 `material|grammar|vocab|fallback`。
- 新增强校验（`validate` 的 errs）：
  1. 每天至少 1 篇素材 topic 与 `scene_topic_key` 相同（`review` 类型除外）；
  2. `lesson_core` 至少 1 句 `origin == "material"`；
  3. `can_do` 含 `scene_topic` 中文标签；
  4. 当天新语法必须在当天素材正文、或当天素材的 `grammar_ids`、或当天新词例句中出现（否则 err）。
- 报告 `curriculum/coverage_report.md` 增加「场景-素材-语法对齐」表：每天 topic / 素材 / 命中率。

## 8. 内容质量（P1-1）

- 修复已确认错误：`Q0006`（「私は学生だ。」不是错句）、`G0002`（`じゃありません` 合法）、
  `G0005`（`これが本ですか` 在焦点语境合法）。
- 原则：`common_errors[].wrong` 只能是**真正不合法**的形式；语体/语境差异必须写进 `why`，
  不得用「只能这样说」的口径。每条语法补 `register_note`（适用语体/语境）。
- `review_status` 语义收紧：`verified` 仅表示“项目内自查通过”，新增
  `provenance: "self_reviewed" | "external_verified" | "generated"`。当前全部标 `self_reviewed`，
  README 必须写明“未经外部日语教师逐条验证”。
- 新增 `scripts/audit_content.py` → `reports/content_audit.md`：
  检查 MCQ 答案是否在选项内、空字段、错误示例是否疑似合法、N3 素材长度下限（≥180 字符）、
  语法接续缺失、例句缺中文、绝对化措辞（「只能」「一定」）等。

## 9. N3 素材与模考（P1-3）

- N3 原创素材下限：阅读 ≥ 20 篇且每篇 ≥ 180 字符；听力 ≥ 15 篇且每篇 ≥ 150 字符，
  含两人对话、信息干扰与人物关系。
- 新题 ≥ 60 道，覆盖 `言語知識（文字・語彙・文法）`、`読解`、`聴解` 三组，难度 4–5。
- `knowledge/mock_n3.json` 定义接近真实考试的分项限时：
  文字・語彙 30 分 / 60 分、文法・読解 70 分 / 60 分、聴解 40 分 / 60 分，
  合格线总分 95 且每项 ≥ 19（写明“模拟估分，不是 JLPT 官方判定”）。
- `web/n3-mock.html` 由 `build_site.py` 生成：分项计时、交卷后按分项给分与合格判定。
- 素材 `audio_url` 为空时必须显式标注 `audio_kind: "tts"`，不得暗示真人录音。

## 10. 网页 ↔ 数据库（P2）

- Worker 新增 `POST /api/events`（D1 `events` 表）：只存**原始事件**，服务端用
  `web/data/answer-key.json` 重判客观题；不接受客户端 `correct`。
- `GET /api/events?since=<id>` 需要 `X-NH80-Key`，与 `env.NH80_SYNC_KEY` 比对；未配置则 503，
  不得裸奔。
- `scripts/cloud_sync.py pull` 拉取事件 → 生成 `NH80R1` 等价 payload → 复用
  `cmd_import_web` 的导入路径（同判分、同幂等）；`nh80.py pull-cloud` 为其入口。
- 页面在 `navigator.onLine` 且配置了 API 时自动 POST，失败静默保留回传码兜底。
- 无 D1 / 无密钥时，整套静态站行为与 v3 完全一致（优雅降级）。

## 11. 验收

1. `python3 -m unittest discover -s tests -v` 全绿（新增契约测试计入）。
2. `python3 scripts/nh80.py validate` 0 error。
3. `python3 scripts/audit_content.py` 0 高危项（中危项须在报告里逐条说明）。
4. `python3 scripts/build_site.py --root .` 成功，`web/day-030.html` 的
   场景/素材/语法/Can-do 与 Day 30 主题一致。
5. 部署后 `https://nihongo80.cmjfire.workers.dev/api/health` 返回 `{"status":"ok"}`。
