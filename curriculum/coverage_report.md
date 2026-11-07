# 课程覆盖率与完整性检查

生成时间：2026-11-07T01:37:23.206779+00:00
校验结果：**PASS**（errors=0）

## 知识点覆盖

| 类别 | 总数 | 引入/使用 | 覆盖率 |
|---|---|---|---|
| vocabulary | 340 | 340 | 100.0% |
| grammar | 96 | 96 | 100.0% |
| kanji | 140 | 140 | 100.0% |
| questions | 395 | 395 | 100.0% |
| materials | 95 | 95 | 100.0% |

## 未覆盖项（如实列出，不隐藏）

- **vocabulary**：全部覆盖
- **grammar**：全部覆盖
- **kanji**：全部覆盖
- **questions**：全部覆盖
- **materials**：全部覆盖

## 分级兑现（防止 100% 覆盖率掩盖阶段偏科）

按 `research/nh80_framework.md` 的压缩路径，级别必须集中在对应阶段真实引入：

| 阶段 | N5 新知 | N4 新知 | N3 新知 |
|---|---|---|---|
| P1 | 109 | 0 | 0 |
| P2 | 135 | 0 | 0 |
| P3 | 0 | 111 | 0 |
| P4 | 0 | 0 | 221 |

- 强校验下限：P3 的 N4 ≥ 20 项、P4 的 N3 ≥ 40 项；P4 不得出现几乎无新知的天。
- 旧版曾出现 P4 20 天仅 1 个新词、0 个汉字，本表即为防止该问题复发。

## 场景-素材-语法对齐（契约第 7 节）

统计：主素材同主题 65 天｜读写两篇都同主题 9 天｜纯复习 15 天｜lesson_core 中 origin=material 的句子 240 行。
语法硬证据：76 / 96 条新语法能在当天素材正文、素材 grammar_ids 或当天新词例句中找到证据；其余只靠语法自身例句，已逐天列入下方告警，不计入「已对齐」。

> 「主素材同主题」只说明当天**第一主角素材**与场景一致；若该 topic 在本级别只有
> 一种体裁，另一篇会按「同级别最近 topic」补位（`material_pair=mixed_topic`）。
> 真正读写同主题的天数单独统计，不用一个「exact」夸大对齐度。


| Day | topic | 素材 id | lesson_core 来源 | 是否 exact |
|---|---|---|---|---|
| 1 | 寒暄（greeting） | M0001、M0002 | material | 是 |
| 2 | 请求委托（request） | M0012、M0001 | material | 是 |
| 3 | 餐厅点餐（restaurant） | M0004、M0003 | material | 是 |
| 4 | 校园（school） | M0006、M0005 | material | 是 |
| 5 | 自我介绍（self_intro） | M0002、M0007 | material | 是 |
| 6 | 购物（shopping） | M0003、M0010 | material | 是 |
| 7 | 交通出行（transport） | M0005、M0010、M0030 | material | 是 |
| 8 | 天气（weather） | M0008、M0001 | material | 是 |
| 9 | 问路（asking_directions） | M0010、M0003 | material | 是 |
| 10 | 日常作息（daily_routine） | M0009、M0010 | material | 是 |
| 11 | 休闲娱乐（entertainment） | M0011、M0010 | material | 是 |
| 12 | 家庭（family） | M0007、M0010 | material | 是 |
| 13 | 寒暄（greeting） | M0001、M0002 | material | 是 |
| 14 | 请求委托（request） | M0012、M0001、M0031 | material | 是 |
| 15 | 餐厅点餐（restaurant） | M0004、M0003 | material | 是 |
| 16 | 校园（school） | M0006、M0005 | material | 是 |
| 17 | 自我介绍（self_intro） | M0002、M0007 | material | 是 |
| 18 | 购物（shopping） | M0003、M0004 | material | 是 |
| 19 | 交通出行（transport） | M0005、M0010 | material | 是 |
| 20 | 天气（weather） | M0008、M0001 | material | 是 |
| 21 | 问路（asking_directions） | M0010、M0003、M0032 | material | 是 |
| 22 | 日常作息（daily_routine） | M0009、M0010 | material | 是 |
| 23 | 休闲娱乐（entertainment） | M0011、M0010 | material | 是 |
| 24 | 家庭（family） | M0007、M0010 | material | 是 |
| 25 | 寒暄（greeting） | M0001、M0002 | material | 是 |
| 26 | 工作沟通（work） | M0013、M0016 | material | 是 |
| 27 | 预约（appointment） | M0016、M0043 | material | 是 |
| 28 | 问路（asking_directions） | M0022、M0036、M0033 | material | 是 |
| 29 | 邮件往来（email） | M0017、M0014 | material | 是 |
| 30 | 医院问诊（health） | M0055、M0017 | material | 是 |
| 31 | 市政通知（notice） | M0036、M0050 | material | 是 |
| 32 | 预订（reservation） | M0050、M0015 | material | 是 |
| 33 | 餐厅点餐（restaurant） | M0018、M0043 | material | 是 |
| 34 | 校园（school） | M0019、M0022 | material | 是 |
| 35 | 科技产品（tech） | M0014、M0021、M0034 | material | 是 |
| 36 | 交通出行（transport） | M0021、M0022 | material | 是 |
| 37 | 旅行（travel） | M0015、M0020 | material | 是 |
| 38 | 天气（weather） | M0051、M0017 | material | 是 |
| 39 | 工作沟通（work） | M0013、M0020 | material | 是 |
| 40 | 预约（appointment） | M0016、M0043 | material | 是 |
| 41 | 问路（asking_directions） | M0022、M0036 | material | 是 |
| 42 | 邮件往来（email） | M0017、M0014、M0035 | material | 是 |
| 43 | 医院问诊（health） | M0055、M0036 | material | 是 |
| 44 | 市政通知（notice） | M0043、M0050 | material | 是 |
| 45 | 预订（reservation） | M0050、M0015 | material | 是 |
| 46 | 市政通知（notice） | M0046、M0095、M0069 | material | 是 |
| 47 | 手续办理（procedure） | M0040、M0053、M0072 | material | 是 |
| 48 | 预订（reservation） | M0041、M0082 | material | 是 |
| 49 | 餐厅点餐（restaurant） | M0029、M0093、M0057 | material | 是 |
| 50 | 科技产品（tech） | M0024、M0042 | material | 是 |
| 51 | 科技（technology） | M0042、M0054 | material | 是 |
| 52 | 交通出行（transport） | M0066、M0083 | material | 是 |
| 53 | 旅行（travel） | M0025、M0056 | material | 是 |
| 54 | 工作沟通（work） | M0062、M0047、M0078、M0092、M0094 | material | 是 |
| 55 | 公告（announcement） | M0049、M0066 | material | 是 |
| 56 | 预约（appointment） | M0027、M0084、M0058 | material | 是 |
| 57 | 意见讨论（discussion） | M0023、M0085 | material | 是 |
| 58 | 邮件往来（email） | M0037、M0026、M0076 | material | 是 |
| 59 | 说明解释（explanation） | M0045、M0088 | material | 是 |
| 60 | 家庭（family） | M0028、M0079 | material | 是 |
| 61 | 医院问诊（health） | M0039、M0048、M0073 | material | 是 |
| 62 | housing（housing） | M0067、M0086 | material | 是 |
| 63 | 新闻概要（news_summary） | M0038、M0052、M0059、M0044、M0063、M0071 | material | 是 |
| 64 | 市政通知（notice） | M0061、M0095、M0077 | material | 是 |
| 65 | 手续办理（procedure） | M0064、M0087、M0080 | material | 是 |
| 66 | 预订（reservation） | M0041、M0082 | material | 复习 |
| 67 | 餐厅点餐（restaurant） | M0029、M0093 | material | 复习 |
| 68 | 科技产品（tech） | M0024、M0042 | material | 复习 |
| 69 | 科技（technology） | M0042、M0054 | material | 复习 |
| 70 | 交通出行（transport） | M0074、M0089、M0060 | material | 复习 |
| 71 | 旅行（travel） | M0025、M0056 | material | 复习 |
| 72 | 工作沟通（work） | M0070、M0081 | material | 复习 |
| 73 | 公告（announcement） | M0049、M0066 | material | 复习 |
| 74 | 预约（appointment） | M0027、M0084 | material | 复习 |
| 75 | 意见讨论（discussion） | M0023、M0085 | material | 复习 |
| 76 | 邮件往来（email） | M0068、M0026 | material | 复习 |
| 77 | 说明解释（explanation） | M0045、M0088、M0030 | material | 复习 |
| 78 | 家庭（family） | M0028、M0079 | material | 复习 |
| 79 | 医院问诊（health） | M0065、M0090 | material | 复习 |
| 80 | housing（housing） | M0075、M0091 | material | 复习 |

## 教学设计差异化（防止 80 天共用一套模板）

- distinct_can_do：**80 / 80** 种
- distinct_objectives：**80 / 80** 种
- distinct_rubric：**72 / 80** 种
- distinct_scene：**80 / 80** 种
- distinct_theme：**80 / 80** 种

## 先修与超纲检查

- 语法 prerequisites 必须出现在更早的天：通过
- 题目/素材不得引用尚未教授的知识：通过
- 每天时间块合计 60 分钟：通过
- 同一天多测试合并（不叠加）：通过

## 诚实披露

- 80 天课程全部由 `scripts/curriculum.py` 从真实、已校验的知识种子程序化组装，
  `review_status=generated`，**不是 80 篇人工逐课精修的教材**。Day 1–3 已做端到端演练验证。
- 课程内容引用的是结构化知识点 ID 与题库 ID，讲解措辞由每日教师 Agent 现场生成，
  不在此重复堆砌静态课文，也不假装已经教过。
- 固定骨架（知识目标）稳定；实际复习与练习由 `state.db` 的 FSRS 到期队列与
  `plan_adjustments` 动态决定。
- 未覆盖项与 `11` 条 needs_review 种子见 `knowledge/seeds/`。
