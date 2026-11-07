# HANDOFF — Nihongo 150 v5.1

核验日期：2026-11-07。本文件依据代码、CLI、浏览器和部署实测更新。原交接基线是 `0fba24e`；修复前后的证据见 `reports/v5_review_codex.md`。具体 Git 提交以 `git log -1` 为准。

## 1. 产品与学习者（不可随意改变）

彦祖的私人日语学习系统：150 天，每天预算 60 分钟，目标覆盖 N3 常用内容，不承诺合格。中文母语、朝鲜族、韩语母语级；语法可迁移，重点是词汇与独立造句。

网页提供当天资源，会话负责答疑、抽查、批改，主会话读日报调整计划。不做多用户、社区、动画导师或题库平台。跨会话状态必须读文件，不依赖平台记忆，不宣称自动续课。

## 2. 当前真实状态

- 内容库：2700 词、276 语法、620 汉字、1500 句；全部排入 150 天。
- 旧题库 945 题保留兼容历史数据；v5 当日练习不从旧题库抽题，而由 `quiz_v5.py` 统一生成、登记、判分，已接通本地和 Worker。
- 素材库 140 条：原有 95 条保留；新增 45 条原创 TTS 听力（M0096–M0140），来自九类情境各五个事实变体，每条三道理解题。45 个听力日不复用素材 ID。
- TTS 原稿 328–363 日文字符，按每秒五字估算 66–73 秒。**未测各浏览器实际播放时长、未真人试听、无真人音频、未证明 N3 真题难度或生词率。** `duration_sec=0` 表示未测。
- 新补 38 条缺失例句、修正 V2514 生硬例句及 V2697 面包/厢式车混淆；新增/修改内容仍为 AI 草稿。G0080/G0178/G0197 的语境疑点留作 needs_review。
- 网页 42 + 会话 18 = 60；听力包含在网页预算内。预算一致不等于真人能在该时间内完成。
- 保留 2700 词覆盖，因此实际每天 9–22 个；旧设计常规16/听力11只容纳2175词，词量取舍尚待用户决定。

## 3. 仓库与线上

- Git：`https://github.com/zoomc/nihongo-80.git`，main。
- 根目录：`/Users/mj/Documents/learn/jp/nihongo-80`。
- Production：`https://nihongo80.cmjfire.workers.dev`。
- Preview：`https://nihongo80-preview.cmjfire.workers.dev`。
- 最终 production Worker version：`0237b65b-0623-4062-b404-02d9cf6a548f`。
- Preview 曾验证的版本：`2ad7e6d7-6fae-4f26-bf81-469ebefa8816`，不是最终 production 的逐字同版。
- D1：nihongo80，绑定见 `deploy/wrangler.jsonc`；两环境目前共用数据库，不往线上写假学习记录做测试。
- `NH80_SYNC_KEY` 在 Worker secret；本机 `deploy/.sync-key` 已忽略，禁止打印或提交。
- Production `/api/health`：status ok、db true、sync true；Day 1/47/150 200，页面及 app.js 字节与本地构建一致。证据：`reports/evidence/v5.1-production.json`。

## 4. 跑起来

```sh
python3 scripts/nh80.py init
python3 scripts/nh80.py validate
python3 -m unittest discover -s tests -p test_v5.py
python3 -m http.server 8099 -d web
```

当前 validate：150 天、2700/276/620、45 个听力日、0 error。25 项测试通过（19 既有 + 6 个先失败后修复的回归测试）。

init 会建立 DB、导入种子、排课、登记题目、导出镜像、生成网页。已有 DB 不可随便删除。全新 clone 没有学习状态，不能用仓库或平台记忆伪造进度。

## 5. 真源与目录

| 路径 | 性质与修改方法 |
|---|---|
| knowledge/seeds/*.jsonl | 内容真源；修改后 init 重新导入，保持审核状态诚实 |
| scripts/curriculum_v5.py | 150 天排课、时间预算、内容目标 |
| scripts/quiz_v5.py | 确定性出题、私有答案、网页安全投影 |
| scripts/build_v5_site.py | 页面/CSS/JS/缓存生成器；界面改这里 |
| scripts/nh80.py | 唯一状态写入入口，build/import/finish/validate |
| scripts/learning.py | FSRS、能力与掌握门控 |
| scripts/cloud_sync.py | 拉取原始事件，交 CLI 本地重判 |
| scripts/session_v5.py | STATE/brief/report/task/daily 文件协议 |
| curriculum/curriculum.json、day-*.md | 生成物，不手改 |
| web/ | 生成物，不手改、不放私有答案表或学习状态 |
| deploy/worker/src/generated-key.json | CLI 生成、Worker 打包的答案表；不是密钥，不发布到 web/ |
| deploy/migrations/ | 0001 建事件表，0002 增加原始复习/草稿载荷 |
| data/state.db | 权威学习状态，只由 nh80 CLI 写，gitignore |
| student/*.json | export_state 只读镜像，已移出版本跟踪，本机文件保留 |
| STATE.md、days/、tasks/、inbox/ | 运行时文件，gitignore |
| tests/test_v5.py | 25 项测试；遵守当前用户“bug先复现再修”的策略 |
| reports/v5_review_codex.md、reports/evidence/ | 审查、验证及限制 |
| scripts/build_site.py、scripts/curriculum.py、archive/tests_v4/ | v4 历史，不运行旧构建器 |

## 6. 唯一构建链路

`nh80 init/build` → `curriculum_v5.build` → `quiz_v5.day_questions` → CLI 事务登记题目及审计 → import_curriculum → `build_v5_site.main`。

题号带内容摘要；题面或答案改变时不复用旧题号。旧本地题目保留兼容已存事件；Worker 只接受当前发布题号和对应 day。旧浏览器页面提交被拒时，保留原始作答，刷新课程后重新核对，不伪造导入。

不要单独跑 `build_site.py`，会覆盖成旧站。不要直接改 app.js 或 curriculum.json，下次 build 会覆盖。

## 7. 每日网页

| 块 | 常规分钟 | 听力日分钟 |
|---|---:|---:|
| 复习 | 10 | 10 |
| 新词 | 14 | 8 |
| 语法 | 6 | 6 |
| 听力 | — | 8 |
| 句子输出 | 6 | 5 |
| 练习 | 6 | 5 |
| 会话 | 18 | 18 |

首个听力日47，共45天。主题与can-do取当天语法及释义，不虚构15个轮转情境。

- 遮盖四态：全显/遮中文/遮日语/双向；全局和单卡可用，点遮盖块揭开三秒。
- 句子十题：7中→日、3日→中；不下发参考译文，会话批改。
- 练习六题，听力另三题。网页只有选项与哈希，无独立答案字段和解析；选项哈希可枚举，不是保密措施。
- TTS按钮朗读完整文本；脚本提交前展开会计提示。
- API确认成功才显示作答已保存；失败本机暂存并可重试。保存不是整天已完成。
- 新缓存优先网络，离线回退已访问页面，API不缓存；未访问页不承诺离线。

## 8. 会话与落盘

```sh
python3 scripts/session_v5.py daily --day N
python3 scripts/nh80.py start-day N
# 读 STATE、当天 brief、课程、数据库只读查询；先发页面链接再答疑/抽查/批改。
# 网页作答后：用本机密钥按 pull-cloud --help 拉取；不要把密钥写到命令记录或报告。
python3 scripts/nh80.py finish-day N
```

brief 默认刷新，report 默认保留；不得用 `report --force` 覆盖学生已有记录。原始句子拉取到 `days/day-NNN/web-drafts.json` 供教师批改。自评走现有排期函数，不据此声称掌握。听力三题只记录理解练习，不推进不相关知识卡。

finish-day 至少要求当天全部客观题均有已判分记录、正确率≥70%；它不能证明独立口语、句子输出和整段60分钟学习已完成人工验收。未完成就记 incomplete。不同浏览器会话不合并成同一次作答；相同session+qid仍去重。

## 9. 部署

```sh
# 已有凭据；首次才需人工登录。
cd deploy
npx wrangler d1 migrations apply nihongo80 --remote --config wrangler.jsonc
cd ..
bash scripts/deploy_cloudflare.sh preview
bash scripts/deploy_cloudflare.sh production
```

0001/0002 已于本次在远程成功应用；migrations apply可幂等检查。发布脚本先build+validate，再发布并health check。完整浏览器/CLI验证在发布前独立执行，不新增CI测试。

## 10. 已核验与边界

- init、加强版validate、25项测试通过。
- 10组浏览器检查：1/46/47/100/150 × 375/1280；顺序、四态、6题判分、错误反馈与重试、无横向溢出、无pageerror。
- 隔离本地Worker+D1：Day150保存9题、重判9题、重复提交去重9题，元数据保留。
- 隔离SQLite：9题本地重判、幂等、跨天拒绝、独立会话重做、草稿落盘及复习自评元数据恢复。
- Production只做只读验证，不写假学生作答。未在真实手机上试听TTS，未用生产真实学习事件证明端到端拉取。

## 11. 尚未完成（下一位必须知道）

1. **每日词量偏高**：150天/2700词/16与11词上限不能同时成立。暂保留前两项，未替用户决定减词或延期。
2. **真人听力未落地**：当前仅原创TTS情境变体。真人音频许可、质量、实测时长和N3难度均未验收。
3. **全库人工审校未完成**：只做30词/15语法/10汉字抽样；新增内容仍是AI草稿，疑点不得当唯一判错规则。
4. **韩语汉字音仍缺1839条**：页面明确“待核对”，未随意拼音补全，也未声称所有缺失都是和语。
5. **真实学习用时未证明**：42+18是预算；十句产出、复习债与后期词量能否完成须真人试学。
6. **历史学习事件**：v5.0合成题未登记标准答案，不能对旧事件猜答案；旧发布页面的作答须另行核对。
7. **旧文档/脚本仍在**：v3/v4文档、旧构建器和原设计目标仅作历史参考；当前以本文件、v5.1契约与审查报告为准。
8. **缓存迁移/旧页离线升级**：全新上下文已验证；未穷举所有旧浏览器缓存升级。旧题号的失败暂存载荷跨课程版本需人工核对，不要反复盲重试。

## 12. 下一会话起步

先读本文件与审查报告，git status核对实际状态；不要照抄旧报告当当前事实。若用户选择词量方案，先改契约，再改排课/句子对齐/验收要求，保留原始学习记录。不得为了零告警改低测试难度或篡改掌握数据。
