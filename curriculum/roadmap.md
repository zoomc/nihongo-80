# 80 天课程地图

**方法论**：`research/nh80_framework.md`（NH80 高频压缩习得法）。
不照抄 Irodori / Marugoto 任何一套教材的课序；综合多套教材与二语习得研究后自研一套
面向 80 学时压缩冲刺 N3 的编排原则：高频优先、Can-do 驱动、变形先行、迁移加速但强制验证、
N3 官方能力锚定、检索与输出占比最大化。

**学时口径（诚实）**：80 天 × 60 分钟 = 80 学时。Irodori 官方自述全四册需 360–500 学时，
且 Starter–Elementary 2 才到 N4。因此本路线是「用高强度换时长」的压缩冲刺，
目标是尽可能接近 N3 的高频能力与真实交流，**不等于官方学时标准，也不承诺 JLPT 合格分数**。
80 天是首轮周期，不是硬性成绩承诺。

每天原则上 60 分钟；同一天的多种测试已合并为一项，不叠加。

| 阶段 | 天数 | 主线 |
|---|---|---|
| P1 | 1–10 | 音形底座与判断句：假名、发音、は/が、です/ます |
| P2 | 11–25 | 高频日常 Can-do：N5 核心词、基础变形与场景输出 |
| P3 | 26–45 | 动词系统总攻：N4 词/汉字、てたない形复合与授受 |
| P4 | 46–65 | N3 高频冲刺：N3 词/汉字/句型 + 官方能力锚定的听读进阶 |
| P5 | 66–75 | 整合迁移：跨阶段交错、弱项补救、近自然语速输出 |
| P6 | 76–80 | 模拟评估：分项能力盘点与下一阶段规划 |

## 评估日历（每天最多一项）

| Day | 类型 |
|---|---|
| 1 | diagnostic |
| 7 | weekly |
| 14 | weekly |
| 20 | stage |
| 21 | weekly |
| 28 | weekly |
| 35 | weekly |
| 40 | midterm |
| 42 | weekly |
| 49 | weekly |
| 56 | weekly |
| 60 | n3_readiness |
| 63 | weekly |
| 70 | weekly |
| 77 | weekly |
| 80 | final |

## 运行方式

1. `python3 scripts/nh80.py start-day N` 生成当天 briefing（含 FSRS 到期队列）。
2. `python3 scripts/new_session_prompt.py N` 复制提示词，在 WorkBuddy **新建独立会话**粘贴。
3. 可选打开 `web/day-NNN.html` 做可视化/听力/练习，结束后复制回传码。
4. `python3 scripts/nh80.py import-web-result '<码>'` 写回本地 SQLite。
5. `python3 scripts/nh80.py finish-day N` 落盘、导出镜像、生成下一日任务。

详见 `docs/DAILY_SESSION.md` 与 `AGENTS.md`。
