# Nihongo 80 — AI 私人日语学校（本地可运行项目）

> **已上线（2026-11-06）**：https://nihongo80.cmjfire.workers.dev
> **GitHub 仓库**：https://github.com/zoomc/nihongo-80
> Preview：https://nihongo80-preview.cmjfire.workers.dev
> 手机 / PC 直接打开当天页，例如 https://nihongo80.cmjfire.workers.dev/day-001.html
> 部署方式复用 zoomlab-web（Worker + 静态资源，一条 `wrangler deploy`），详见 `docs/CLOUDFLARE.md`。

一个**长期运行、状态落盘、可审计**的日语学习系统：SQLite 知识库 + FSRS 复习引擎 +
80 天完整课程 + 每日独立 WorkBuddy 教学会话 + Cloudflare/本地双端每日页面。

中文解释优先、日语比例随能力提高；面向中文母语者（可利用韩语背景，但不靠汉字猜词）。
**80 天是首轮学习周期，不是「第 80 天必达 N3」的成绩承诺。**

课程编排**不照抄任何一套教材的课序**，而是依据 `research/nh80_framework.md` 自研的
**NH80 高频压缩习得法**（频率优先、Can-do 任务驱动、变形先行拓扑、中日韩迁移强制验证、
N3 官方能力锚定、检索与输出最大化、交错边界、掌握门控）对 80 天重排。
Irodori / Marugoto / JLPT 官方 / Tadoku / JMdict 等只贡献目标格式、能力标准、题型边界与素材分级原理，
**不采用其线性课序与全量覆盖**，也**不照抄任何教材课序**。

**诚实口径**：80 天 × 60 分钟 = **80 学时**，这是**压缩冲刺路径**，**不等于 JLPT 官方学时标准**
（Irodori 官方全四册约 360–500 学时，Starter–Elementary 2 才相当于 JLPT N4），
**不承诺合格分数、不承诺第 80 天必达 N3**。本地正确率是原创模拟题的过程指标，
不是 JLPT 标准分、不可换算；`N5/N4/N3` 是项目自定分级标签，非 JLPT 官方词表。

---

## 0. 先看这里：这套系统怎么转

```
知识种子 JSONL ──> SQLite(FTS5 + 关系图) ──> 80 天课程骨架 ──> 每日静态页面(PC/手机)
                          │                        │                    │
                          └──> data/state.db <──────┴── 答题/批改/FSRS/错题/复习队列
                                      ▲                              │
                                      └──── 回传码 <────────────────┘
                                      （网页只展示+练习，不是状态真源）

每天：新开一个 WorkBuddy 会话 → 读 briefing（文件，不靠聊天记忆）→ 教学 → 写回 → 次日再读文件
```

**关键取舍**：平台不会自动把昨天的教学状态传给今天的新会话，记忆也装不下 FSRS 的 D/S/R 数值。
所有状态以 `data/state.db` 为唯一真源，AI 只输出「评分 / 错误类别 / 讲解」，数值一律由脚本写入。

---

## 1. 首次安装（只做一次）

环境：Python 3.13（本机已验证）、SQLite 3.50（含 FTS5）、Node 22（仅部署时需要）。
**不需要任何付费 API、不需要安装 npm 包即可学习**；FSRS 官方实现已 vendor 在 `scripts/vendor/`。

```bash
cd /Users/mj/Documents/learn/jp/nihongo-80
python3 scripts/nh80.py init
```

`init` 会：建库 → 导入 877 条种子 → 校验并生成 Day 1–80 课程 → 生成 80 个网页 → 导出状态镜像。
预期输出 `curriculum.validation: true, errors: 0`。

若只改了知识种子或课程规则，重建用：

```bash
python3 scripts/merge_sources.py     # 来源清单重映射（幂等）
python3 scripts/nh80.py build        # 重建课程 + 网页
python3 tests/test_all.py            # 19 项验收测试
```

---

## 2. Day 1 实际启动命令（现在就能跑）

```bash
cd /Users/mj/Documents/learn/jp/nihongo-80

# ① 生成当天 briefing（含 FSRS 到期队列、错题、昨日总结）
python3 scripts/nh80.py start-day 1

# ② 生成「可直接粘贴到新建 WorkBuddy 会话」的开场提示词
python3 scripts/new_session_prompt.py 1
```

把 ② 的输出**整段复制**，在 WorkBuddy 里**新建一个独立会话**粘贴发送。每天一个新会话，
不继承聊天历史，状态全靠文件。教师会先让学生思考再揭示答案，逐题推进。

同时可打开当天页面（任选其一，推荐第一个）：

```bash
# ① 已上线的生产页面（手机 / PC 都能直接打开，https 下 PWA 可离线）
#    https://nihongo80.cmjfire.workers.dev/day-001.html
# ② 本地预览（PC）
python3 -m http.server 8080 -d web      # 浏览器访问 http://localhost:8080/day-001.html
# ③ 直接双击 web/day-001.html（file:// 下 PWA 会自动跳过，其余功能正常）
```

页面里有：60 分钟时间块可视化、词汇/语法/汉字卡（先自测再揭示）、阅读与听力素材、
9 类题型的交互练习、浏览器 TTS（`ja-JP`）、80 天热力图。手机端为一屏一题 + 触控大按钮 +
复制/分享/下载回传码，可加到主屏离线打开。

### 教学过程中的写回命令

```bash
# 客观题作答（脚本判分 + 归因 + FSRS 排期）
python3 scripts/nh80.py answer --day 1 --q Q0181 --answer "は" --seconds 12

# 答错时给出归因（省略则由启发式兜底，AI 判断更准）
python3 scripts/nh80.py answer --day 1 --q Q0182 --answer "だ" --error-type particle

# 开放题：先挂起，AI 按 rubric 判分后补录
python3 scripts/nh80.py answer --day 1 --q Q0187 --answer "私は李です。" --pending
python3 scripts/nh80.py grade-open --q Q0187 --correct 1

# 手机上做完网页练习，复制 NH80R1.xxx 回传码，粘回会话/终端导入
python3 scripts/nh80.py import-web-result 'NH80R1.xxxx'

# 收尾：落盘、导出镜像、生成下一日任务
python3 scripts/nh80.py finish-day 1 --minutes 58
```

完整人工闭环（含断网/关会话/备份恢复）见 `docs/DAILY_SESSION.md`。

---

## 3. 常用命令

| 命令 | 作用 |
|---|---|
| `python3 scripts/nh80.py status` | 进度、覆盖率、到期数、最近会话 |
| `python3 scripts/nh80.py start-day N` | 生成当天 briefing |
| `python3 scripts/nh80.py finish-day N` | 落盘并生成下一日任务 |
| `python3 scripts/nh80.py adjust --day N` | 依据成绩调整**动态任务**（不降难度） |
| `python3 scripts/nh80.py report --week 1` | 真实数据周报（无数据会明说） |
| `python3 scripts/nh80.py report --stage 40` / `--final` | 阶段评估 / 最终报告 |
| `python3 scripts/nh80.py search "食べる" --mode keyword\|relation\|hybrid\|semantic` | 检索方式对比 |
| `python3 scripts/nh80.py relation V0001` | 查看「词汇→例句→语法→课程→题目→错题→复习」链路 |
| `python3 scripts/nh80.py validate` | 80 天完整性、先修、超纲、覆盖率 |
| `python3 scripts/nh80.py backup` / `restore <path>` / `audit` | 备份、恢复、审计日志 |
| `python3 tests/test_all.py` | 19 项自动验收（含框架兑现测试） + Day 1–3 端到端演练 |

---

## 4. 项目里到底有什么

| 内容 | 位置 | 数量 / 说明 |
|---|---|---|
| 研究资料 | `research/` | 6 份调研报告 + 3 份原始 JSON + 合并总表 `source_registry.md` |
| 机器可读来源清单 | `config/sources.json` | 80 条（67 OK / 4 PARTIAL / 1 FAIL / 7 UNVERIFIED / 1 内部） |
| 知识种子 | `knowledge/seeds/*.jsonl` | **877 条**：260 词（N5 141 / N4 49 / N3 70）、85 语法（N5 34 / N4 26 / N3 25）、140 汉字（N5 69 / N4 36 / N3 35）、332 题、60 素材 |
| 数据库 | `data/state.db` | SQLite，FTS5 字符 bigram 全文索引 + 关系图 + 状态表 + 审计日志 |
| 80 天课程 | `curriculum/` | `curriculum.json`（真源）、`roadmap.md`、`coverage_report.md`、`day-001.md`…`day-080.md` |
| 每日页面 | `web/` | 80 页 + index/404 + CSS/JS + PWA(manifest/sw/icon)，零 CDN、零外部请求 |
| Cloudflare 部署 | `deploy/`、`scripts/deploy_cloudflare.sh` | 仿 zoomlab 的 Worker + Static Assets 模式，见 `docs/CLOUDFLARE.md` |
| Agent 配置 | `AGENTS.md`、`agents/{director,teacher,examiner,reviewer}.md` | 教学总监/教师/考官/复习官 |
| 学习档案 | `student/*.json` | **只读镜像**，真源是 `data/state.db` |
| 报告 | `reports/` | 周报、阶段评估、最终报告（只从真实数据生成） |
| 测试 | `tests/test_all.py` | 19 项，全部通过（19/19 PASS） |

---

## 5. 成本与资源控制

- **零付费 API**：不需要 embeddings、不需要 TTS 服务、不需要云端数据库。
  音频用浏览器 `speechSynthesis(lang="ja-JP")`，无网络请求。
- **零 npm 运行时依赖**：网页是纯静态 HTML/CSS/原生 JS；`deploy/package.json` 只有 `wrangler`（部署时才装）。
- **FSRS 官方实现已 vendor**：`scripts/vendor/fsrs`（py-fsrs 6.3.1, MIT, 564K），纯标准库，不自造公式。
- **不每天重算一切**：知识/课程是缓存的结构化文件；AI 只负责解释、互动、出题措辞、开放题评价与分析。
- **网页不做状态真源**：成绩经回传码由本地脚本写回 SQLite，避免云端/本地双写，也不需要 Cloudflare 账号才能学习。

---

## 6. 已明确标注的限制（不伪装成已实现）

1. **已上线，但用的是 `*.workers.dev` 默认域名**：没有绑定自定义域名；
   PWA 首次安装需后台预缓存 167 个资源，实测约 15 秒后 `activated`（不阻塞页面使用）。
   重新部署需本机 wrangler 登录态有效；命令见 `docs/CLOUDFLARE.md` 第 4 节。
2. **平台不自动传递每日状态**：定时任务只是「到点发起一次任务」，不会注入上次的结构化状态；
   每日会话必须人工新建并粘贴提示词。详见 `research/platform_capabilities.md`。
3. **80 天课程是程序化组装**（`review_status=generated`），不是 80 篇人工精修教材；
   Day 1–3 已端到端演练验证，其余按种子数据可运行但未逐课精修。
4. **知识种子未逐条对照 JMdict/KANJIDIC**：14 条标 `needs_review`（读音 / 义项 / 分级边界待核）；全部为项目原创整理（来源 `S000`），
   不虚构外部教材引用关系。
5. **TTS 依赖浏览器**：iOS/Android 首次需用户手势解锁，部分环境无日语语音，会降级为「假名读音 + 跟读」。
6. **外部版权教材只存索引**：Irodori / Tadoku / JLPT 官方样题 / NHK 的正文不入库，`text_ja` 为空且有强校验。
7. **分数口径**：本地正确率是原创模拟题的过程指标，**不是** JLPT 标准分，不预测真实考试成绩。

细节见 `docs/VALIDATION.md` 与 `docs/CLOUDFLARE.md`。

---

## 7. 设计依据

- `CONTRACTS.md`：全项目唯一数据契约（ID、schema、掌握状态机、错误类型、回传码、禁止事项）
- `docs/TECH_DESIGN.md`：架构、检索方式对比、FSRS、掌握门控、状态持久化、成本控制
- `research/learning_science.md`：8 项学习机制的**可执行逻辑**（含「词汇不适合交错练习」等反直觉结论）
- `docs/CLOUDFLARE.md`：zoomlab 部署模式复用/简化、PC 与手机双端、回传码闭环
