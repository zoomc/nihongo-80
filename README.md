# Nihongo 150 — AI 私人日语学校（0 基础 → N3）

> **v5（2026-11-07）**：周期改为 **150 天 × 60 分钟**，核心 **2,700 词 / 276 语法 / 620 汉字**。
> 网页只留 5 块：复习、新词、语法（含朝鲜语对照）、句子输出、练习；支持**遮盖背诵**（遮中文/遮日文/双向）。
> 主会话 + 每日会话用**文件协议**编排（`STATE.md` / `days/` / `tasks/`），任何 agent 都能接手。
> 2,700 词 / 276 语法 / 620 汉字**全部排入 150 天**，不是“库里有但课不教”。
> 听力 Day 46 起，每周 3 次，隔天一次。设计见 `docs/v5/00–04`。
> 线上：https://nihongo80.cmjfire.workers.dev/day-001.html

---

# 旧版说明（v4，保留作历史）

> **已上线（2026-11-06）**：https://nihongo80.cmjfire.workers.dev
> **GitHub 仓库**：https://github.com/zoomc/nihongo-80
> Preview：https://nihongo80-preview.cmjfire.workers.dev
> 手机 / PC 直接打开当天页，例如 https://nihongo80.cmjfire.workers.dev/day-001.html
> 部署方式复用 zoomlab-web（Worker + 静态资源，一条 `wrangler deploy`），详见 `docs/CLOUDFLARE.md`。
> **当前线上为 v4**（2026-11-07 重新部署）：评分契约、课程对齐、N3 素材与掌握门控已按审查整改；
> 新增 `https://nihongo80.cmjfire.workers.dev/n3-mock.html`（N3 分项限时模拟）。
> 整改口径见 `docs/REVISION_CONTRACT.md`，实测记录见 `docs/VALIDATION.md` 的 v4 节，
> 独立复审（含未修完项）见 `reports/v4_review.md`。
> 当天页仍是「今天要会的 3 句话」+ 词卡 + 语法 + 例句 + 发音 + 复习 + 练习；系统术语在页尾。

## v4 整改（2026-11-07，针对深度审查的 P0/P1/P2）

审查指出的问题是真的：v3 的复习事件会被污染、课程是按模块拼接的、N3 素材不足以代表 N3。
v4 不改 FSRS 公式，改的是**事件采集与评分契约**，并把内容补齐到能支撑一次接近真实形式的训练。
实现口径见 `docs/REVISION_CONTRACT.md`，逐条验收见 `reports/`。

| 等级 | 问题 | v4 做法 |
|---|---|---|
| P0 | 答对一道题同时“学会”6 个知识点 | 题目拆成 `targets`（可改变掌握）与 `context`（只出现在题面）；`Q0001` 现在只推进 `G0001|usage`，不再碰 `私/学生` 等 |
| P0 | 一张卡代替一个词的所有能力 | 按 `meaning / reading / listening / usage / production` 分能力建卡、分能力排 FSRS；`knowledge_state` 只作聚合视图 |
| P0 | 看完答案仍算独立答对 | 点「看答案」立即锁定 `hinted=true`，提交按钮改文案，解析区标注“本次为提示学习”；后端 `hinted` 只能上调，封顶 `hinted_recall` |
| P0 | 后端直接相信前端判分 | `import-web-result` 用题库标准答案重新判分；前端 `correct` 只进 `disagreements` 审计 |
| P0 | 网页复习时间不是 FSRS 到期 | 页面优先显示 `review.due`（真实 FSRS 到期 + 逾期天数）；固定 1/2/3/7/14/30 只作“预习建议”，并明确标注 |
| P1 | 教材把正确日语判成错 | 修 `Q0006`、`G0002`、`G0005`；85+11 条语法全量补 `register_note`；`audit_content.py` 高危 0、中危 0 |
| P1 | 场景/语法/素材错配 | 按 topic 选材（主素材与场景同主题 65/80 天，其中读写两篇都同主题 9 天，另 15 天为综合复习）；96 条新语法中 76 条能在当天素材/新词里找到硬证据，其余 20 条逐天列入告警，不粉饰为“已对齐” |
| P1 | N3 听读不足 | N3 词汇 70→150、语法 25→36；新增 20 篇 N3 阅读（≥180 字符）、15 篇两人对话听力、63 道 N3 题；`n3-mock.html` 按 30/70/40 分钟分项限时计分 |
| P1 | 没有真正的掌握门控 | `learning.gate()` 检查先修：未到 `independent_recall` 的语法当天推迟，写 `gate_defer` 与补救任务，`start-day` 的 briefing 与 `nh80.py gate --day N` 都能看到 |
| P2 | 网页与数据库不通 | 页面在有网络时自动 `POST /api/events`（只发原始事件，不发 `correct`），Worker 用 `answer-key.json` 服务端重判后存 D1；`nh80.py pull-cloud` 拉回本地入库。无 D1 时自动上报失败即静默，回传码仍是兜底 |

**仍未解决的诚实边界**：没有真人录音（全部 TTS，`audio_kind=tts`）；没有外部日语教师逐条复核
（`review_status=self_reviewed`）；`n3-mock.html` 是模拟估分，不是 JLPT 官方判定；
80 天仍只是压缩冲刺路径，不承诺合格。

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

`init` 会：建库 → 导入 **6,136 条**种子 → 生成 Day 1–150 课程 → 生成 150 个网页 → 导出状态镜像。
预期输出 `curriculum.validation: true, errors: 0`。

若只改了知识种子或课程规则，重建用：

```bash
python3 scripts/merge_sources.py     # 来源清单重映射（幂等）
python3 scripts/nh80.py build        # 重建课程 + 网页
python3 -m unittest discover -s tests -p "test_v5.py"   # v5 验收（19 项）
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

页面在 v3 已按「一课教材」重排：首屏就是 3 句能用的日语，往下依次是词卡、语法、例句 / 会话、
练习、今日复习；系统信息（60 分钟时间块、能力目标、图表、80 天热力图、来源编号、回传码、
诊断 / 评估标签与术语）退到页尾折叠区。**逐块怎么用见下方「每天页面怎么用（v3）」**。
工程特性保留：9 类题型的交互练习、浏览器 TTS（`ja-JP`）、纯静态零 CDN、手机端触控大按钮 +
复制 / 分享 / 下载回传码，可加到主屏离线打开。

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

## 每天页面怎么用（v3）

> 这一节写给**打开页面学日语的你**，不是写给系统。v3 把页面从「系统报表」改回「一课教材」，
> 顺序依据 `docs/REDESIGN_PLAN.md` 与 `research/textbook_lesson_pattern.md`（真实核实过的一课结构）。
> 下面说的就是**你不点任何折叠、从上往下**会看到的东西。v3 已上线（2026-11-06 重新部署），
> 线上重新部署由项目维护者完成后生效。

打开当天的 `day-NNN.html`（手机、电脑都行），**从上往下**依次是：

1. **今天要会的 3 句话** —— 一进来就是 3 句大字日文，配中文意思；有把握的读音才给假名，
   没有就只给日文和中文，**不会瞎编读音**。每句有「听」按钮，点一下用浏览器读日语给你听。
2. **单词** —— 当天的词卡**直接摊开**、不用翻面：汉字、假名、罗马字、词性、中文意思、
   例句、常见搭配、中国学生容易错的地方、韩语对照，一张卡上都有，也有「听」按钮。
3. **语法** —— 这条句型什么意思、怎么用中文说清**接续**、例句、什么场景用、易错点、
   和相近句型的区别，以及**韩语对照（标明不等价）**。
4. **汉字** —— 音读、训读、例词、中文母语者最容易踩的坑；不要求你抄写。
5. **例句 / 会话** —— 独立一块：日文、假名（有才显示）、中文，外加「听」。
   **日文原文不会假装成读音**，读音和原文是分开的两行。
6. **练习** —— 默认展开、由易到难。先自己想，再点「看答案」对照解析；开放题给示范句，
   不会第一题就把你卡住。
7. **今日复习（记忆曲线）** —— 今天具体该回顾哪几个词、为什么是今天（几天前学的、
   按 1 / 2 / 3 / 7 / 14 / 30 天间隔）、下次大约第几天。先遮住中文自己回忆，点开对答案，
   再选「记住了 / 模糊 / 忘了」。
8. **最底下折叠区「给老师 / 系统」** —— 能力目标、60 分钟时间块、图表、编号、诊断标签、
   回传码这些系统信息全收在这里。**正文里看不到术语**，不想看可以完全不点开。

**发音怎么听**：所有「听」按钮走浏览器自带语音（`ja-JP`），不联网、不花 API；手机上第一次
要你手动点一下解锁；没有日语语音时会降级成「显示假名 + 跟读」，不保证发音质量。

**韩语对照怎么用**：如果你有韩语背景，语法卡里的对照能帮你快速抓住「SOV 语序、助词后置、
主题 / 主格大致分工」这类**结构**——结构可以借。但**词不能猜**：具体助词、读音、词义、
礼貌体层级日韩并不一一对应，`knowledge/ko_analogy.json` 每条都写了「不等价」提醒，
中日同形异义（勉強 / 大丈夫 / 手紙 / 汽車）也显式标了警告。别照着韩语去推日语单词。

**复习三档自评要注意**：第 7 区选的「记住了 / 模糊 / 忘了」只是告诉程序**下次什么时候**
再让你见到这个词（记住了→间隔拉长、模糊→适中、忘了→尽快再来），由 FSRS 排期；
它**不代表你已经掌握**，不写进「答对次数」、不改学习阶段、不判「已掌握」。真正掌握要靠
跨天、多次、无提示的作答，由脚本按门控判定。

**成绩怎么回到 WorkBuddy**：页面是静态的，不保存你的状态。做完练习点「生成回传码」，
把那串 `NH80R1.` 开头的码复制，粘回当天 WorkBuddy 会话（或终端跑
`python3 scripts/nh80.py import-web-result '<码>'`）。复习三档自评也在这个码里
（`review_ratings`），导入后由程序写入 `data/state.db`。网页只负责展示和收集，
成绩与真实复习到期以本地 SQLite / 会话为准。

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
| `python3 -m unittest discover -s tests` | 49 项自动验收（评分契约、内容准确性、课程对齐、网页契约 + Day 1–3 端到端演练） |

---

## 4. 项目里到底有什么

| 内容 | 位置 | 数量 / 说明 |
|---|---|---|
| 研究资料 | `research/` | **9 份 .md**（含 v3 新增 `ux_audit.md` / `textbook_lesson_pattern.md`、合并总表 `source_registry.md`）+ 3 份原始 JSON |
| 机器可读来源清单 | `config/sources.json` | 80 条（67 OK / 4 PARTIAL / 1 FAIL / 7 UNVERIFIED / 1 内部） |
| 知识种子 | `knowledge/seeds/*.jsonl` | **1066 条**：340 词（N5 141 / N4 49 / N3 150）、96 语法（N5 34 / N4 26 / N3 36）、140 汉字（N5 69 / N4 36 / N3 35）、395 题、95 素材（N3 素材 58 篇 = 36 篇考试级长文 + 22 篇短句练习） |
| 数据库 | `data/state.db` | SQLite，FTS5 字符 bigram 全文索引 + 关系图 + 状态表 + 审计日志 |
| 80 天课程 | `curriculum/` | `curriculum.json`（真源）、`roadmap.md`、`coverage_report.md`、`day-001.md`…`day-080.md` |
| 每日页面 | `web/` | 80 页 + index/404 + CSS/JS + PWA(manifest/sw/icon)，零 CDN、零外部请求 |
| Cloudflare 部署 | `deploy/`、`scripts/deploy_cloudflare.sh` | 仿 zoomlab 的 Worker + Static Assets 模式，见 `docs/CLOUDFLARE.md` |
| Agent 配置 | `AGENTS.md`、`agents/{director,teacher,examiner,reviewer}.md` | 教学总监/教师/考官/复习官 |
| 学习档案 | `student/*.json` | **只读镜像**，真源是 `data/state.db` |
| 报告 | `reports/` | 周报、阶段评估、最终报告（只从真实数据生成） |
| 测试 | `tests/` | 49 项，全部通过（49/49 PASS） |

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
