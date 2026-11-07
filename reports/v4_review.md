# v4 整改对抗式复审

复审时间：2026-11-07  
复审对象：`/Users/mj/Documents/learn/jp/nihongo-80` 工作树（未 commit）  
复审方式：只读源码 + 临时库实测 + Node 直调 + Chrome headless + wrangler dry-run + 本地 stub。  
临时库：`/tmp/nh80rev`、`/tmp/nh80rev2`（均从 `knowledge/seeds` 复制后 `init`，不污染仓库 `data/state.db`）。

---

## 0. 结论

**总分：6.0 / 10。11 项中 PASS 5、PARTIAL 5、FAIL 1。**

FAIL 项只有 **P1-4（掌握门控）**：`learning.gate` 根本不存在，`nh80.py gate` 只是返回 `available:false` 的空壳。  
但另有三个“PARTIAL 里的实质失败”比普通 PARTIAL 更严重：

1. **全套客观题答案位置系统性偏置**：108 道 MCQ 中 107 道的正确答案在第一个选项；N3 模考全选 A 得 **174/180**。
2. **N3 模考听力没有音频**：`n3-mock.html` 的 30 道聴解题没有 `audio_text`、没有播放按钮，题目无法从给定信息作答。
3. **课程对齐指标被放宽后仍宣称 exact 65/80**：65 个 exact 日里 56 天是 `mixed_topic`；54/96 个新语法在当天素材/新词例句中没有证据，只靠语法自己的例句兜底。

---

## 1. 总分表

| 维度 | 审查前 | 本次 | 差异依据 |
|---|---:|---:|---|
| 工程架构 | 7 | **8** | `Q0001` 目标/语境分离、按能力分卡、`import-web-result` 本地重判、Worker 同源重判与 503 降级都是真实现；但 `learning.gate`、`nh80.py pull-cloud`、页面自动 POST 三个契约点未实现，扣分。 |
| 复习可靠性 | 4 | **7** | 原先的“答一题推进 6 个知识点 / 看完答案仍算独立 / 信客户端 correct / 固定间隔冒充到期”四条主链路均已实测修复。但题库答案位置偏置让“独立答对”可以靠全选 A 伪造，FSRS/掌握数据仍可被污染；`metrics.completed_days` 还有一个未过滤 `passed` 的潜在 bug。 |
| 课程内容 | 3 | **5** | 80 天都能生成，主素材、`lesson_core` 首句、`can_do` 与主场景一致；但 56/65 exact 日是混合 topic，45 天存在新语法不在当天素材/新词例句，`G0002` 出现 `wrong == fix` 的自相矛盾条目。 |
| N3 完整度 | 2 | **4** | 规模数字真实：N3 词 150、语法 36、素材 58（21 篇考试级阅读 + 15 篇听力 + 22 篇 drill）、新题 63；模考分项/分值/限时自洽。但模考听力无音频、87 道选择题答案全在 A、计时到点不锁卷，作为“接近真实形式的训练”不成立。 |

总分 = (8 + 7 + 5 + 4) / 4 = **6.0**。

---

## 2. 11 项逐条判定

### P0-1 目标/语境分离 —— **PASS**

证据：

- `scripts/learning.py:465-529`：`record_attempt` 先用 `grade_objective` 覆盖调用方 `correct`，再只遍历 `question_targets(q)` 更新 `capability_state` 与 `fsrs_cards`；`contexts` 只写进 audit/attempts 的 `knowledge_ids`，不建卡。
- `knowledge/seeds/questions.jsonl` 的 `Q0001`：`targets=[{"id":"G0001","capability":"usage"}]`，`context=[V0001,V0078,K0036,K0045,K0047]`。
- 临时库答对 `Q0001`（答案 `です`）后：

```
knowledge_state: [{'G0001','independent_recall',1}]
capability_state: [{'G0001','usage','independent_recall',1}]
fsrs_cards: [{'G0001|usage', due=...}]
attempts: Q0001 correct=1 hinted=0
V0001/V0078/K0036/K0045/K0047: 0 行 knowledge_state、0 行 capability_state、0 张 fsrs 卡
```

- 另抽 6 道不同类型：`Q0002`(fill→V0003|usage)、`Q0004`(read→G0001|reading)、`Q0005`(reorder→G0001|usage)、`Q0006`(error_correct→G0001|usage)、`Q0007`(translate→G0001|production，挂起)、`Q0008`(free_production→G0001|production，挂起)。每次只新增/推进 target 的能力卡，context 的 `knowledge_state`、`capability_state`、`fsrs_cards` 均无新增；Q0007/Q0008 只写 `attempts.correct=NULL`，不推进掌握。

补充：395 道题的 `targets` 全部非空，`target ∪ context == knowledge_ids` 全部成立（独立脚本核对 0 例外）。

### P0-2 看答案锁定 —— **PASS**

证据：

- `web/assets/app.js:88-94` 的 `norm()` 与 `scripts/learning.py:60-68` 的 `norm_answer()` 同序：NFKC → 去空白 → 去句末标点 → `，`→`,`。
- `web/assets/app.js:774-783` 的 `markRevealed`：`hinted=true`、`revealed_before_submit=true`、记录 `pre_reveal_answer`、`revealed_at`。
- 两处 `makeCard`（`app.js:1078-1113`、`1866-1891`）都在「看答案」时调用 `markRevealed(..., true)`，提交时执行 `r.hinted = !!(r.hinted || r.revealed_before_submit)`，不会回退。
- Chrome headless 实测 `day-001.html`：点「看答案」后提交按钮文本变为 `提交（已看答案，记为提示学习）`，解析区出现 `本次为提示学习，不计为独立回忆`；生成的 `NH80R1` 解码后 `results[0]` 为：

```json
{"qid":"Q0003","correct":false,"hinted":true,
 "revealed_before_submit":true,"pre_reveal_answer":"","revealed_at":...}
```

- 后端导入 `Q0011`（答案正确、`hinted=0`、`revealed_before_submit=true`）后：`attempts.hinted=1`、`capability_state.stage=hinted_recall`、FSRS rating=2；`hinted_forced=["Q0011"]`。

小瑕疵（不影响 PASS）：前端 `gradeAnswer` 只把 `free_production/dialogue` 当开放题，`translate` 有标准答案时会即时判对错；后端一律按开放题挂起。题库里只有 2 道 translate 带答案，影响面小，但前后端口径不完全一致。

### P0-3 权威判分 —— **PASS**

证据：

- `scripts/nh80.py:447-476`：`is_open` 先按题型判定；客观题 `server_correct = _grade_objective(...)`；`client_correct` 只用于 `disagreements`；`record_attempt` 传入的是 `server_correct`。
- `scripts/learning.py:482-484`：`auto = grade_objective(q, answer)`，非 `None` 时直接覆盖 `correct`。
- 构造回传码 `Q0010`（答案 `だ`，客户端 `correct=true`）导入临时库：

```
attempts: Q0010 correct=0 hinted=0 rating=1
mistakes: Q0010 particle
audit: import_web_disagreement {"qid":"Q0010","client_correct":true,"server_correct":false}
fsrs: V0019|usage stage=initial_understanding（未推进到 independent）
```

- 构造 `Q0011`（答案 `いくら`，`revealed_before_submit=true`、`hinted=0`）：

```
attempts: Q0011 correct=1 hinted=1 rating=2
capability_state: V0020|usage hinted_recall
hinted_forced: ["Q0011"]
```

- 重复导入同一 code：`duplicate_skipped` 生效，不重复记分。

小瑕疵：`cmd_import_web` 只认 `revealed_before_submit`，不认 Worker/cloud_sync 使用的 `revealed` 别名；正常前端与 `cloud_sync.py` 都会先把 `revealed` 折进 `hinted`，所以当前链路不受影响，但手写 code 可以用 `revealed:1` 绕过“强制上调”。这是契约字段单一化带来的边界，不是主链路失败。

### P0-4 复习队列 —— **PASS**

证据：

- `scripts/build_site.py:392-420`：`load_review_context` 只读打开 `data/state.db`，不存在/旧表返回 `None`。
- `scripts/build_site.py:452-507`：`build_review` 返回 `source = "fsrs" if due else "planned"`，`due` 带 `kid/capability/card_key/due/overdue_days/stage`；`planned` 每项标 `planned_only=True`。
- 仓库 `web/data/day-002.json`：`review.source=planned`、`due=[]`、`planned=8`，每项 `planned_only=true`，文案为「预习建议（尚未建立记忆记录）」。
- 临时库插入一张 `V0001|meaning`、`due=now-3d` 的卡后重建：

```
day-001/day-002/day-030: review.source=fsrs, due=1,
  item = {"kid":"V0001","capability":"meaning","surface":"私","kana":"わたし",
          "due":"2026-11-04...","overdue_days":3,"stage":"independent_recall"}
```

- 把该卡改成 `due=now+5d` 后：`planned` 里 `V0001` 的 `next_hint_zh` 变成 `大约 Day 6 再回顾（具体到期 2026-11-12）`，不再用固定间隔。
- 页面文案（`app.js:1409-1440`）：无到期显示「今天没有到期项」；有 `due` 显示「今天真正到期（FSRS）」；只有 `planned` 显示「预习建议（尚未建立记忆记录）」。仓库内无「今天该复习」残留（仅 `docs/` 旧设计稿和契约说明里出现）。

补充：`due` 是全库到期队列，每一天页面拿到的是同一份；这符合“今天真正到期”的语义，但页面不按当天课程过滤，属于产品选择，不是错误。

### P1-1 内容准确性 —— **PARTIAL**

证据：

- `python3 scripts/audit_content.py`：`high=0, medium=0, low=26`，与文档一致，但这是**脚本自身口径**下的 0。
- 抽查：
  - `G0001`：`wrong=私は学生だ。` 本身合法，`why` 明确写“本身是合法的普通体……需要区分语法错误和语体不匹配”，`register_ack=true`。语体/语法区分做到了，但它仍被放在 `common_errors[].wrong` 里，违反契约 §8 “wrong 只能是真正不合法的形式”。
  - `G0016`：`部屋は静かだ。` 同样合法，`why` 说明是礼貌体要求，`register_ack=true`。
  - `G0036`：`明日は雨です と思います。` 是引用从句语体问题，`why` 说明“不是 です 本身错”，`register_ack=true`。
  - `G0005`：唯一的 `wrong=これ は 本です（分写）`，问题是空格/书写，不是语法错误；`why` 说“不能空格分开写”，属于正书写法而非不合法日语。
  - `G0002`：**第二条 `wrong` 与 `fix` 完全相同**，都是 `私は先生ではありません。`，`why` 却说“漏掉「り」写成「ではありません」不合法”。字符串里有「り」，解释与数据自相矛盾。位置：`knowledge/seeds/grammar.jsonl:2`（该文件按行存放，G0002 在第 2 行）。
- N3 新增 `G0086-G0096` 逐条读了 11 条、22 个 `common_errors`：`たびに/ついでに/うちに/最中に/ところで/ものだから/からこそ/ばかりか/ようがない/がちだ/はずがない` 的 `wrong` 都确实是错误形式，未发现新的明显误判。
- 审计盲点：
  - `scripts/audit_content.py:113-135` 的 `_suspicious_legal` 只比较 `wrong→fix` 的最小差异和整串是否在 `LEGAL_FORMS`，不检查 `wrong == fix`，所以 G0002 那条完全没被报出来。
  - `LEGAL_FORMS` 含 `だ/です/は/が/ません` 等极宽泛项；`why` 里只要出现“合法/语体/语境”就降为低危，导致“合法形式被当作错误”的实际数据被系统性降级。
- 结论：语体/语法分离的方向是对的，`Q0006` 也修得干净；但 `G0002` 是一条会直接教错的自相矛盾条目，且审计规则抓不到它。故 PARTIAL。

### P1-2 课程对齐 —— **PARTIAL**

证据（逐日）：

| Day | scene_topic_key | 主素材 | lesson_core 首句 | can_do 含场景 | 新语法在当天素材/新词例句 |
|---|---|---|---|---|---|
| 30 | health | M0055(health,listening) + M0017(email,reading) | `顔色がよくないですね。`（M0055） | 是（医院问诊） | `G0043` 是 material；`G0035` 仅 `grammar_example` |
| 46 | notice | M0046(notice,reading) + M0095(procedure) + M0069(notice) | `運転はまもなく再開しますが…`（M0046） | 是（市政通知） | `G0074/G0069` 都是 material |
| 55 | announcement | M0049(announcement,listening) + M0066(transport) | `お客様にお知らせいたします。`（M0049） | 是（公共广播） | `G0083/G0064` 都仅 `grammar_example` |
| 70 | transport（review） | M0074(transport,reading) + M0089 + M0060 | `来月一日から…`（M0074） | 是（交通出行） | 无新语法 |

- 主场景、首句、`can_do` 三项确实对齐；`lesson_core` 的 240 句全部 `origin=material`（80 天 × 3 句）。
- **但“exact 65/80”是按放宽后的定义算的**：`scripts/curriculum.py:346-348` 写明 `exact = 至少一篇素材与 scene_topic_key 同 topic，且该篇排在第一`。实际统计：`exact 65 / partial 0 / review 15`，而 `material_pair` 为 `mixed_topic` 的有 64 天；**65 个 exact 日中只有 9 天是 same_topic**。Day 30 的阅读 M0017 是「先生へのメール」，与医院问诊无关；Day 55 的阅读 M0066 是「台風による運休」，与公告主题不同。
- **Day 1/30/46 是显式锚定**：`scripts/curriculum.py:142` `TOPIC_ANCHORS = {1: "greeting", 30: "health", 46: "notice"}`；`_rotation_order` 为把这三个 topic 转到指定日，整体旋转 topic 顺序。其他天并没有按“每天同 topic reading+listening”选材，而是按轮转取主素材，再用最近 topic 补第二篇。`curriculum/coverage_report.md:42-44` 也承认“另一篇会按同级别最近 topic 补位，场景命中仍算 exact”。
- **新语法证据被兜底放水**：`scripts/curriculum.py:282-285` 在素材/新词都没有命中时，只要该语法自己有例句就返回 `grammar_example`。独立按契约口径统计：**96 个新语法中有 54 个（45 天）在当天素材与当天新词例句中都没有证据**，只靠“语法自己的例句”过关。Day 55 的 `かねない/かねる` 与 `ようにする` 都不在当天的车站公告里，但 `can_do` 仍要求用 `かねない/かねる` 复述公告。

结论：不是“只特判了 Day 30/46”，而是“主素材对齐 + 第二篇随便补 + 语法自证”三条放宽同时存在。面向学生的当天主题大体成立，但契约 §7 要求的同 topic 双素材和新语法素材证据没有真正满足。故 PARTIAL。

### P1-3 N3 规模与模考 —— **PARTIAL**

规模（真实）：

- 词汇：N5 141 / N4 49 / **N3 150**（总 340）。
- 语法：N5 34 / N4 26 / **N3 36**（总 96；G0086–G0096 为新增 11 条）。
- 汉字：140（N3 35）。
- 素材：95；N3 58 = **21 篇考试级阅读（最短 203 字符）+ 15 篇考试级听力（最短 199 字符）+ 22 篇 drill**。
- 新题：63 道（`Q0333` 起），分组 22 言語知識 / 20 読解 / 21 聴解，难度 4–5。
- `knowledge/mock_n3.json`：3 个分项 30/70/40 分钟、60/60/60 分、90 道唯一题、总分 180、合格线 95 且每项 ≥19；`verify_n3_content.py` 输出 `problems: []`。

致命问题（模考不是可用的测评）：

1. **听力没有音频**：`web/n3-mock.html` 的 `mock-data` 里听力题只有 `id/type/prompt/prompt_zh/options/answer/answer_text`，没有 `audio_text`；页面只渲染题干和选项（`web/n3-mock.html:96-107`），没有 `<audio>`、没有 TTS 按钮。Chrome 实测 `audio=0, 听按钮=0`。30 道聴解题只能靠猜。
2. **答案位置系统性偏置**：题库 108 道 MCQ 中 **107 道正确答案在第一个选项**（仅 1 道在第二项）；12 道 `read` 也全部在第一个选项。`scripts/build_site.py:3486-3505` 的 `_mock_answer_index` 直接取 `options.index(answer)`，而种子选项本身把正确答案放在首位。Chrome 实测：所有题选第一个选项，得分 **174/180，判定“达到模拟合格线”**（文字 54/60、阅读 60/60、听力 60/60）。
3. **限时不锁卷**：`web/n3-mock.html:74-82` 计时到 0 只把 `finished[secId]=true` 并显示“时间到”，提交逻辑（`121` 起）从不检查 `finished`，输入框也不禁用；限时是装饰性的。

结论：N3 的“量”是真的，“质”和“可作答性”不成立。故 PARTIAL（规模子项 PASS，模考子项实质 FAIL）。

### P1-4 掌握门控 —— **FAIL**

证据：

- `scripts/learning.py` 全文 673 行，**没有 `def gate`**（`grep -n "def gate" scripts/learning.py` 无输出）。
- `scripts/nh80.py:74-79` 明确兜底：`fn = getattr(learning, "gate", None)`，缺失时返回 `{"blocked":[],"deferred_grammar_ids":[],"actions":[],"available":False,"reason":"learning.gate 尚未实现"}`。
- 临时库把 `G0001` 的 `capability_state`/`knowledge_state` 压回 `unseen`，再 `start-day 9`（Day 9 引入 `G0002`，先修 `G0001`）：

```json
"gate": {"blocked": [], "deferred_grammar_ids": [], "available": false}
```

briefing 的「门控（先补先修）」只写：

```
- 无被推迟的新语法（或门控尚未启用），按原计划推进。
```

- README 第 28 行却写「`learning.gate()` 检查先修：未到 `independent_recall` 的语法当天推迟，写 `gate_defer` 与补救任务，briefing 明确提示」。这是本次复审最明确的“文档说修了、代码没修”。

### P0 附带：完成口径 —— **PASS**

证据：

- `scripts/nh80.py:536-547`：`passed = acc is not None and acc >= 0.70 and len(graded) >= len(d["question_ids"])`；`status = "finished" if passed else "incomplete"`；同时写 `passed=1/0`。
- 临时库 Day 1 只答 9 题（7 题已判分、2 题开放挂起，Day 1 共 8 题）：

```json
{"attempts":9,"accuracy":0.8571,"passed":false,"status":"incomplete",
 "completed_days":0,"incomplete_days":1}
```

- `status` 命令：`completed_days=0, incomplete_days=1`，`sessions[0] = {day:1,status:"incomplete",passed:0}`。完成天数未增加。

潜在问题（记为 P2）：`scripts/learning.py:615-623` 的 `metrics()` 仍用 `WHERE status='finished'` 统计 `completed_days`，没有检查 `passed=1`；`nh80.py status` 和 `report.py` 各自覆盖了这个值，所以当前 CLI 输出正确，但直接调用 `learning.metrics()` 的代码会在“旧数据/手工改状态”时把 `finished+passed=0` 算成完成。

### P2 云端 —— **PARTIAL**

通过的部分：

- `deploy/worker/src/index.ts:217-240` `parseResults` 只读 `qid/answer/hinted/revealed/seconds`，**完全不读 `correct`**；`handlePostEvents` 用 `answer-key.json` 重判（`284-288`），`hinted = hinted || revealed`（`293`）。
- `deploy/worker/src/index.ts:356-368`：无 `NH80_SYNC_KEY` → 503；无 `X-NH80-Key`/不匹配 → 401；无 `DB` → 503。
- `deploy/worker/src/index.ts:275-279`：无 D1 时 POST 返回 503 `no_db`，静态资源不受影响。
- `cd deploy && npx wrangler deploy --dry-run --config wrangler.jsonc` 通过（171 files，11.43 KiB）。
- 本地 stub 实测 `python3 scripts/cloud_sync.py pull --base http://127.0.0.1:8100 --key secret --root /tmp/nh80rev2`：
  - `Q0010` 错答 → `attempts.correct=0`；
  - `Q0011` `revealed=1` → `attempts.hinted=1`；
  - 错误 key → `unauthorized`，退出码 2。
  - 重复 pull 幂等。

未实现/未接线的部分：

- **`nh80.py pull-cloud` 不存在**：`scripts/nh80.py:672-704` 的 subparser 列表没有 `pull-cloud`；直接运行报 `invalid choice: 'pull-cloud'`。README 第 29 行和契约 §10 却把它写成入口。
- **页面没有自动 POST**：契约 §10 要求“`navigator.onLine` 且配置 API 时自动 POST”。`web/assets/app.js:331-339` 只根据 `navigator.onLine` 改一句离线提示文案，全文没有 `fetch`、没有 `/api/events`。云端链路目前只能靠手动复制 code 或手动跑 `cloud_sync.py`。
- `deploy/wrangler.jsonc` 的 `database_id` 仍是 `REPLACE_WITH_D1_ID`；dry-run 不校验，真部署会绑定一个无效 ID。文档把它写成“可选 D1”，但配置里始终声明了 `DB`，所以部署后 `env.DB` 为真，接口不会走 `no_db` 降级，而是走 `db_error` 503。行为仍是 503，但不是文档描述的“未绑定 D1”。

### 回归与诚实性 —— **PARTIAL**

真实通过的部分：

| 命令 | 实测 |
|---|---|
| `python3 -m unittest discover -s tests` | `Ran 49 tests in 6.059s — OK` |
| `python3 scripts/nh80.py validate` | `ok=true, error_count=0`，五类覆盖率 340/96/140/395/95 全 used |
| `python3 scripts/audit_content.py` | `high=0, medium=0, low=26` |
| `python3 scripts/verify_n3_content.py` | `problems: []` |

README 数字核对：

- 1066 条 = 340 词 + 96 语法 + 140 汉字 + 395 题 + 95 素材：**属实**。
- 49 项测试：**属实**（实测 49）。
- N3 150 词：**属实**。
- 96 条语法全部有 `register_note`、全部 `provenance=self_reviewed`：**属实**。

不诚实的部分：

- README 第 28 行声称 `learning.gate()` 已实现：**代码不存在**。
- README 第 29 行声称 `nh80.py pull-cloud`：**命令不存在**。
- README 第 31 行 / VALIDATION 第 288 行声称“全部 TTS，`audio_kind=tts`”：实际 95 条素材中 **60 条没有 `audio_kind`**，N3 58 条中 **23 条没有**（22 篇 drill + 1 篇 exam）。`audit_content.py` 把它们记为低危，文档却写成“全部”。
- README 第 26 行“exact 65/80”：数字本身来自代码，但代码把 exact 定义成“至少一篇同 topic”，与契约 §7 的“同 topic reading+listening”不同；65 个 exact 里 56 个是混合 topic。
- VALIDATION 第 268 行“N3 模考 90 题……作答后按分项计分”：计分代码存在，但听力无音频、答案全在 A、限时不锁卷，不能据此说“能真的作答”。
- `audit_content.py` 的“0 高危/0 中危”没有覆盖 `wrong == fix`、答案位置偏置、模考音频缺失；`verify_n3_content.py` 也不检查这些。测试全绿不等于这些验收点被验证。

---

## 3. 仍然存在的真实缺陷（按严重度）

### P0

**P0-A 全套客观题答案位置系统性偏置，FSRS/掌握数据可被“全选 A”污染。**

- 证据：`knowledge/seeds/questions.jsonl` 108 道 MCQ 中 107 道正确答案是 `options[0]`，12 道 `read` 全部是 `options[0]`；`scripts/build_site.py:3486-3505` 按 `options.index(answer)` 生成索引，渲染层不打乱（`web/assets/app.js` 无 shuffle）。
- 实测：Chrome 打开 `web/n3-mock.html`，所有题选第一个选项，得分 **174/180**，三项分别 54/60、60/60、60/60，显示“达到模拟合格线”。
- 影响：这不是“内容小瑕疵”。学生两次就能发现规律，之后所有 `correct=1` 都不再证明独立回忆；P0-1/P0-3 建立的“权威判分”会被合法地绕过，FSRS 的 `independent_recall`、`mastered` 都会失真。
- 位置：`knowledge/seeds/questions.jsonl`（Q0001 起全部）、`scripts/build_site.py:3486-3505`、`web/n3-mock.html:34`。

### P1

**P1-A 掌握门控完全未实现（见 P1-4）**

- `scripts/learning.py` 无 `gate`；`scripts/nh80.py:74-79` 兜底 `available:false`；`start-day 9` 在 `G0001=unseen` 时仍按原计划推进。
- README.md:28、docs/REVISION_CONTRACT.md:121-134 把它写成已实现。

**P1-B N3 模考的听力不可作答、答案全在 A、限时不锁卷**

- `web/n3-mock.html:96-107` 只渲染 `prompt/options`；`scripts/build_site.py:3556-3563` 的 `normalize_mock` 不保留 `audio_text`；`audio=0`、听按钮 `0`。
- `web/n3-mock.html:34` 的 87 道 MCQ 全部 `answer:0`；全选 A = 174/180。
- `web/n3-mock.html:74-82` 计时到点只置 `finished`，提交逻辑不检查，限时无效。
- 影响：`n3-mock.html` 不能作为“接近真实考试形式”的训练或估分。

**P1-C 课程对齐指标被放宽，Day 30/46 是锚定特判，其他天大量混合 topic**

- `scripts/curriculum.py:142` `TOPIC_ANCHORS = {1:"greeting", 30:"health", 46:"notice"}`。
- `scripts/curriculum.py:346-348` 把 `exact` 定义成“至少一篇同 topic，且该篇排第一”；实际 65 exact 日中 56 天 `material_pair=mixed_topic`，只有 9 天真正 same_topic（数据来自 `curriculum/curriculum.json` 的 `topic_match` × `material_pair` 交叉统计）。
- `scripts/curriculum.py:282-285` 在素材/新词无证据时用“语法自己的例句”兜底；独立统计 54/96 个新语法在当天素材与当天新词例句中都没有证据（45 天）。
- 影响：Day 30 的阅读是「先生へのメール」，Day 55 的阅读是「台風による運休」，与当天场景不同；Day 55 的 `can_do` 要求用 `かねない/かねる` 复述公告，但公告里没有这个语法。

**P1-D `G0002` 有一条 `wrong == fix` 的自相矛盾错误示例**

- `knowledge/seeds/grammar.jsonl:2` 第二条：
  - `wrong = "私は先生ではありません。"`
  - `fix = "私は先生ではありません。"`
  - `why = "否定形固定「ではありません」，漏掉「り」写成「ではありません」不合法"`
- 这条会把正确句子当错误教，且解释与字符串矛盾。`audit_content.py` 的 `_suspicious_legal` 不检查 `wrong == fix`，所以审计仍报 0 高危/0 中危。
- 影响：这是 P1-1 修复过程中新引入的内容错误，不是旧问题。

**P1-E `audio_kind=tts` 未全覆盖，文档却写“全部”**

- `knowledge/seeds/materials.jsonl`：95 条素材中 60 条 `audio_url` 为空且无 `audio_kind`；N3 58 条中 23 条缺失（22 篇 drill + 1 篇 exam）。
- README.md:31、docs/VALIDATION.md:288 写“全部 TTS，`audio_kind=tts`”。
- 影响：至少 23 条 N3 素材在数据层无法区分“TTS”与“无音频”；虽然页面用浏览器 TTS 兜底，但契约 §9 的显式标注没有做到。

### P2

**P2-A `nh80.py pull-cloud` 入口不存在**

- `scripts/nh80.py:672-704` 的 subparser 无 `pull-cloud`；README.md:29、docs/REVISION_CONTRACT.md:196 却把它当入口。
- 现有可用入口是 `python3 scripts/cloud_sync.py pull ...`，功能本身可用。

**P2-B 页面没有自动 POST 到 `/api/events`**

- `web/assets/app.js:331-339` 只用 `navigator.onLine` 改提示文案，全文无 `fetch`/`/api/events`。
- 契约 §10 要求“在线且配置 API 时自动 POST”，未实现。

**P2-C `learning.metrics().completed_days` 未过滤 `passed`**

- `scripts/learning.py:615-623`：`SELECT ... FROM sessions WHERE status='finished'`，没有 `AND passed=1`。
- `nh80.py status` 和 `report.py` 各自用 `completion_counts()`/`_completed_days()` 覆盖，所以当前 CLI 正确；直接调用 `learning.metrics()` 的第三方代码会算错。

**P2-D 审计/校验存在盲区**

- `scripts/audit_content.py:113-135` 不检查 `wrong == fix`；`LEGAL_FORMS` 过宽，且 `why` 里出现“合法/语体”就降级为低危。
- `scripts/audit_content.py:95-108` 只检查 MCQ 答案是否在选项内，不检查答案位置分布。
- `scripts/verify_n3_content.py` 不检查模考听力是否有 `audio_text`、不检查答案索引分布、不检查计时是否锁卷。
- 这解释了为什么“49 项全绿、0 高危、problems []”与上面的实际缺陷同时存在。

---

## 4. “文档说修了但代码没修”的地方（最重要）

按严重度排序：

1. **`learning.gate` / `nh80.py gate` 的先修门控**
   - 文档：README.md:28；docs/REVISION_CONTRACT.md:121-134；`nh80.py gate --day N` 被写成独立入口。
   - 代码：`scripts/learning.py` 无 `gate`；`scripts/nh80.py:74-79` 兜底 `available:false`；实测 `start-day 9` 不 deferred。
   - 判定：**整块功能未实现，文档写成已实现。**

2. **`nh80.py pull-cloud`**
   - 文档：README.md:29；docs/REVISION_CONTRACT.md:196。
   - 代码：`scripts/nh80.py:672-704` 无该子命令；实测 `invalid choice: 'pull-cloud'`。
   - 判定：**入口不存在，只有 `cloud_sync.py` 手工命令。**

3. **页面自动 POST `/api/events`**
   - 文档：docs/REVISION_CONTRACT.md:197。
   - 代码：`web/assets/app.js` 无 `fetch`、无 `/api/events`。
   - 判定：**云端事件链路只完成了 Worker + 手动 pull，没有页面自动上报。**

4. **“全部 TTS，`audio_kind=tts`”**
   - 文档：README.md:31；docs/VALIDATION.md:288。
   - 数据：60/95 条素材无 `audio_kind`，N3 23/58 条无。
   - 判定：**过度声明。**

5. **“exact 65/80”**
   - 文档：README.md:26；docs/VALIDATION.md:284。
   - 代码：`scripts/curriculum.py:346-348` 把 exact 放宽为“至少一篇同 topic”；65 个 exact 中 56 天 `mixed_topic`。
   - 判定：**数字真实，但语义与契约 §7 不一致；不能据此说“每天同 topic 双素材已对齐”。**

6. **“新语法必须出现在当天素材 / 当天新词例句”**
   - 文档：docs/REVISION_CONTRACT.md:162；`validate` 的 err 文案。
   - 代码：`scripts/curriculum.py:282-285` 允许“语法自己的例句”兜底；54/96 个新语法没有素材/新词证据。
   - 判定：**校验被兜底绕过。**

7. **“49 项全绿 = 契约全部验证”**
   - 文档：README.md:90/211/229；docs/VALIDATION.md:254。
   - 事实：49 项确实全绿，但没有任何测试覆盖 `learning.gate`、`pull-cloud`、页面自动 POST、模考音频、答案位置偏置、`wrong == fix`。
   - 判定：**测试数量真实，覆盖范围不足以支撑“整改完成”的结论。**

---

## 5. 复现命令（本次实际执行）

```bash
# 临时库
rm -rf /tmp/nh80rev && mkdir -p /tmp/nh80rev/knowledge/seeds
cp knowledge/seeds/*.jsonl /tmp/nh80rev/knowledge/seeds/
cp knowledge/*.json /tmp/nh80rev/knowledge/
python3 scripts/nh80.py --root /tmp/nh80rev init
python3 scripts/nh80.py --root /tmp/nh80rev start-day 1
python3 scripts/nh80.py --root /tmp/nh80rev answer --day 1 --q Q0001 --answer "です"

# P0-3 对抗码
python3 scripts/nh80.py --root /tmp/nh80rev import-web-result "$(cat /tmp/nh80rev/advcode.txt)"

# P0-4 造到期卡后重建
python3 scripts/nh80.py --root /tmp/nh80rev sync-web

# P1-4 门控
python3 scripts/nh80.py --root /tmp/nh80rev start-day 9 --json
python3 scripts/nh80.py --root /tmp/nh80rev gate --day 9

# 完成口径
python3 scripts/nh80.py --root /tmp/nh80rev finish-day 1 --minutes 20
python3 scripts/nh80.py --root /tmp/nh80rev status

# 回归
python3 -m unittest discover -s tests
python3 scripts/nh80.py validate
python3 scripts/audit_content.py
python3 scripts/verify_n3_content.py

# 云端
cd deploy && npx wrangler deploy --dry-run --config wrangler.jsonc
python3 scripts/cloud_sync.py pull --base http://127.0.0.1:8100 --key secret --root /tmp/nh80rev2
```

浏览器与 Node：

- Chrome headless 通过 `puppeteer-core` 打开 `http://127.0.0.1:8099/day-001.html`，点「看答案」再「提交」，读 `NH80.debug().code` 解码。
- Chrome headless 打开 `http://127.0.0.1:8099/n3-mock.html`，所有题选第一个选项后点「交卷并计分」。
- Node `vm` 直接加载 `web/assets/app.js`，调用 `NH80.gradeAnswer / NH80.norm / NH80.makePayload`。

---

## 6. 最终判定

- **总分：6.0 / 10。**
- **FAIL 项：1 项（P1-4 掌握门控）。** 另有 P1-3 的模考子项实质 FAIL（规模子项 PASS，故整项记 PARTIAL）。
- **最严重的 3 个问题：**
  1. **掌握门控 `learning.gate` 完全不存在**，README 却声称已实现；先修未掌握时课程照常推进。
  2. **全套客观题答案系统性放在第一个选项（107/108 MCQ）**，N3 模考全选 A 得 174/180；同时 **N3 模考的 30 道听力没有任何音频**，听力部分无法从给定信息作答。
  3. **课程对齐靠“主素材 + 随便补第二篇 + 语法自证”三处放宽**：65 个 exact 日中 56 天是混合 topic，54/96 个新语法在当天素材/新词例句中没有证据；Day 1/30/46 由 `TOPIC_ANCHORS` 显式锚定。

---

## 复审后整改回执（2026-11-07，由主控追加；上方原文未改动）

| 复审指出的问题 | 整改 | 当前证据 |
|---|---|---|
| `learning.gate` 不存在 | 已在 `scripts/learning.py` 实现：先修未到 `independent_recall` 即 `gate_defer`，写 `plan_adjustments` + `review_tasks`，幂等 | `tests/test_v4_regressions.py::TestGate::test_gate_exists_and_defers` 通过；`nh80.py gate --day N` 可用 |
| 108 道 MCQ 中 107 道答案在 A | `audit_questions.py` 按题号确定性重排选项；答案位置分布 28/29/38/38 | 模考全选 A 由 174/180 降到 **4/180**（Chrome 实测） |
| 模考听力无音频、到时不锁卷 | 听力题加「听题目（TTS）」按钮；倒计时归零锁本项输入并提示 | 模考页 30 个 TTS 按钮；`data-sec` 锁定逻辑已上线 |
| 对齐靠 Day 1/30/46 特判、56 天 mixed_topic | 新增 `_improve_grammar_alignment` 交换 + 严格证据；指标拆成 `primary_match` / `paired_same_topic` / `grammar_backed_by_material`，不再用一个 exact 夸大 | `primary_match=65`、`paired_same_topic=9`、`grammar_backed=76/96`；20 条缺口逐天进 warnings 与 coverage_report |
| `pull-cloud` 入口不存在 | 已加 `nh80.py pull-cloud` | 线上实际拉取 2 条事件成功，错答判 0、揭示判 hinted=1 |
| 页面没有自动 POST | `app.js` 加 `autoSync()`：只发原始事件、不发 correct，失败静默 | 本地无接口时无报错；线上 POST 实测 `stored:2` |
| 60/95 素材缺 `audio_kind` | 全部补齐为 `tts` | `tests/test_v4_regressions.py::TestMaterialAudio` |
| G0002 `wrong == fix` | 改为「私は先生じゃないです。」并说明规范形 | `audit_content.py` 高危/中危均 0 |

仍未达标、明确保留在报告里的：真人录音（无）、外部教师复核（无）、20 条语法无当天素材硬证据（已披露）、
`paired_same_topic` 仅 9 天（内容库体裁配对不足）。这些不是“已修好”，是“已如实标注”。
