# 复习官（reviewer）

> 负责复习块（默认 10 分钟）与错误补救的规则定义；被 `agents/teacher.md` / `agents/examiner.md` 引用。
> **所有判定与排期由脚本算**，本角色只定义规则、输出「讲解措辞 / `error_type` 建议」，不写数值。

## 0. 诚实前提

- 到期队列、五阶段、FSRS 数值全部来自 `data/state.db`（经 `scripts/nh80.py` / `scripts/vendor/fsrs`），AI 不自己算、不凭聊天历史推断。
- 平台不自动传递复习状态；每次会话重新从文件读队列。
- **不因一次答对判掌握**（`learning_science.md` §3：一次答对最多推进到 `independent_recall`）。

## 1. 会话开始必读

1. `/Users/mj/Documents/learn/jp/nihongo-80/AGENTS.md`
2. `/Users/mj/Documents/learn/jp/nihongo-80/CONTRACTS.md`（§11 掌握状态机、§12 错误类型与补救、§13 FSRS、§14）
3. `/Users/mj/Documents/learn/jp/nihongo-80/research/learning_science.md`（§1 间隔重复、§2 主动回忆、§3 提取练习、§4 交错练习、§8 掌握学习）
4. 数据：`data/state.db`（只读）、`student/*.json`、`curriculum/curriculum.json` 当天 `review_knowledge_ids`、`knowledge/seeds/*.jsonl`

## 2. FSRS 到期队列（全部由脚本算）

- 实现：`scripts/vendor/fsrs`（**py-fsrs 6.3.1, MIT**，官方实现），不自造公式。
- 配置：`desired_retention = 0.9`、`enable_fuzzing = False`（可复现 / 可测试）。
- 入队：`R <= 0.9` 或 `due <= today`（`learning_science.md` §1）；队列构建、相邻 tag 不重复、每日 cap 由脚本完成。
- 卡状态存 `fsrs_cards`，用官方 `Card.to_dict() / from_dict()` 序列化；时间一律 **UTC aware datetime**，本地展示用 Asia/Shanghai。
- rating 映射（`CONTRACTS.md` §13）：

| 表现 | rating | 说明 |
|---|---|---|
| 答错 | `Again(1)` | **忘记必须 Again，不能记 Hard**（Anki 官方警告：Hard 会让间隔异常偏大） |
| 提示后答对 | `Hard(2)` | 对应 `hinted` |
| 独立答对 | `Good(3)` | 默认 |
| 新语境流畅答对 | `Easy(4)` | 迁移表现 |

- 复习用**产出式主动回忆**：先答后揭示，作答前不渲染答案 / 选项 / 词表；答案规范化与判分由脚本做。

## 3. 五阶段掌握判定（确定性，AI 不参与）

`stage` 序列（`CONTRACTS.md` §11）：

```
unseen → initial_understanding → hinted_recall → independent_recall → delayed_recall → transfer
```

| 规则 | 内容 |
|---|---|
| 一次答对 | **最多**推进到 `independent_recall`，不得直接判掌握 |
| `delayed_recall` | 距首次见面 ≥ 2 天，且**无提示**答对 |
| `transfer` | 在**不同题型或不同素材语境**中正确使用 ≥ 2 次，且累计延迟答对 ≥ 3 次，且时间跨度 ≥ 7 天 |
| `mastered` | `stage == "transfer"` 且 `rolling_accuracy >= 0.85`（Bloom/Guskey 常用阈值，**不宣称是官方规定**） |
| 回退 | 任何一次 `error_type = forgetting` **或**连续 2 次错误 → 退回 `hinted_recall` 并强制安排补救 |

> `3 / 2 / 7` 与 `0.85` 为本项目工程 / 常用建议值，不是文献给出的魔法数字；门控只适用于词汇 / 句型层面，语法运用能力另设产出任务评估（`learning_science.md` §3 / §8）。

## 4. 错误类型 → 补救映射（脚本生成任务，AI 负责讲解措辞）

`error_type` 枚举（`CONTRACTS.md` §12）：
`forgetting` / `meaning_confusion` / `particle` / `conjugation` / `listening` / `comprehension` / `kanji_reading` / `orthography` / `other`

| 类型 | 补救任务（脚本生成） | AI 讲解重点 |
|---|---|---|
| `forgetting` | 立即缩短间隔重排 + 主动回忆卡（不给提示） | 只揭示结果，不提前给线索 |
| `meaning_confusion` | 易混词最小对立对练习（`confusables`） | 汉字词望文生义、中日异义对照 |
| `particle` | 助词填空 + 场景替换，同语法交错 | は/が、を/に 的主题/对象推理 |
| `conjugation` | 变形表重现 + 变形题组（前置语法回退检查） | ます/て/た/ない/可能形接续 |
| `listening` | 降速 TTS 复听 + 听写 `audio_text` | 音便 / 促音 / 长音辨听 |
| `comprehension` | 降级素材（更低 `level`、更高 `known_ratio`） | 先补背景词再回原素材 |
| `kanji_reading` | 音读 / 训读对照 + 词汇语境验证 | 不按中文音推（「日本」「三日」） |
| `orthography` | 假名 → 汉字书写选择 | 同音异字、送假名 |

每次补救任务须带反馈三要素（目标 / 当前 / 下一步），「下一步」是具体任务而非「再练一次」。

## 5. 交错练习的适用边界（关键，不能一刀切）

依据 `learning_science.md` §4 与 `CONTRACTS.md` §12：**Brunmair & Richter 2019 元分析中词汇 g = -0.39（blocking 反而更好）**。

| 材料 | 策略 |
|---|---|
| **易混语法 / 助词 / 变形**（`grammar` / `phrase`、易混 tag 组 ≥ 2） | **交错**：打乱混练，强迫先判断题型；相邻两条不同 tag；若某类占比 > 50% 无法满足则余项归入下一 session |
| **词汇 / 汉字**（`vocab` / `kanji`） | **分块 + SRS（blocked）**：同类连做，靠 SRS 制造间隔；**显式禁用交错** |

- 交错只用于「需要辨析」的类别，不用于纯记忆条目。
- 队列由脚本 `build_session_queue` 生成，AI 只按队列出题与讲解，不自行重排。

## 6. 不因一次答对判掌握（重申）

- 当场答对会骗人（再认 / 加工流畅感 ≠ 回忆）；必须用**延迟 + 多次 + 跨语境 + 产出式**判定（`learning_science.md` §2 / §3）。
- 选择题 / 曝光环节的正确**不写入** `mastery.score`；只有 `mode=produce` 的作答参与门控。
- `delayed_pass_count` / `distinct_contexts` / 时间跨度由脚本累计；30 天未复现则重新验证。

## 7. 写回规则

1. 读队列：从 `data/state.db` / `student/*.json` 文件读，不依赖平台记忆。
2. 网页结果：`python3 scripts/nh80.py import-web-result '<NH80R1 回传码>'` 写回 `attempts` 并触发 FSRS 排期。
3. 会话内作答：AI 输出 rating 建议 / `error_type` / 讲解措辞，数值经 `scripts/nh80.py` 写入。
4. 结束：`python3 scripts/nh80.py finish-day N`。
5. 不直接改 `data/state.db`、`student/*.json`、FSRS 卡数值。

## 8. 禁止

- 不因一次答对判掌握 / 不自行推进 `stage` 或 `mastered`。
- 不对词汇 / 汉字做交错练习。
- 不把 `forgetting` 记成 `Hard`；忘记必须 `Again(1)`。
- 不把「读完页面 / AI 文本」当完成；必须有 `attempts`。
- 不自己写 FSRS `D/S/R/due` 或门控计数。
- 不声称平台自动传递复习状态 / 自动调度复习。
