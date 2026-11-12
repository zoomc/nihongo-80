# HANDOFF · Nihongo 100 v15

主课 100 天，Day 001 保留原词和语法，Day 002–100 每天 25 词。主课覆盖 2489 词、286 条语法（其中 10 条为 N2 衔接）和 620 汉字。211 个词单列选学词库，45 篇合成听力及开放音频保留在独立资源页。

| 项 | 值 |
|---|---|
| Git | `https://github.com/zoomc/nihongo-80.git`，分支 `main` |
| 本地根 | `/Users/mj/Documents/learn/jp/nihongo-80` |
| Production | https://nihongo80.cmjfire.workers.dev |
| Preview | https://nihongo80-preview.cmjfire.workers.dev |
| 部署 | `bash scripts/deploy_cloudflare.sh preview` → `... production`（脚本先跑 `nh80.py build`） |
| D1 | `nihongo80`（prod）/ `nihongo80-preview`（preview）两库隔离，`0001`–`0006` 均已应用 |
| 额度 | Cloudflare Workers Free；无 R2 / KV / AI / 定时任务 / 日志；无付费绑定 |

## 新会话第一步（每天）

```sh
python3 scripts/today.py
```

合并本机 finish-day 与云端完成快照，输出今天 Day N、上次卡点、今天词/语法/汉字与页面链接，写 `TODAY.md` 并刷新 `STATE.md`、当天 `brief.md`。这是每日会话唯一入口；`session_v5.py daily` 退居兼容命令。云端不通加 `--offline`，回看用 `--day N`，机器读用 `--json`。

## 目的与产品决策

主课按记忆曲线复习、新词、语法、单选练习推进。会话负责答疑和错题讲解。N5 为 Day 001–026，N4 为 Day 027–050，N3 为 Day 051–100，后段加入 N2 衔接。

## 当前交付（带证据）

- **每日页**：4 个内容块（复习 / 新词 / 语法 / 练习）+ 1 个完成按钮。100 页全量生成，顶部与底部杂项断言为 0（`tests/test_v10.py`）。
- **练习**：100 页均为当天新词每词两题、语法每条三题，构建时确定性打乱。同页错题可多轮重练，完成快照保留首次作答。
- **新词（v13）**：左列为日语及假名，右列为中文和韩语读音。例句可展开，遮盖与自评仍可使用。整句仅在读音可完整解析时标韩语读音。
- **小日语文字 + 发音**：新词左列 `.kana-line` 小假名，例句汉字 `<ruby>` 注音，每条例句 `data-speak` 朗读；浏览器实测 375/1280 均可用。
- **到期复习（v14）**：`review_schedule.js` 按当前浏览器的每日首次作答建卡，`review.html` 单选结果更新间隔。跨设备的网页完成快照继续独立；`today.py` 从 SQLite 读取实时 FSRS 到期卡和待补先修。
- **完成 → 云端**：`POST /api/progress` 写 D1 `study_progress_120`（`day` 主键幂等覆盖，最多 120 行），页面无口令；`GET /api/progress?day=N|latest=1` 需 `X-NH80-Key`。
- **agent 侧**：`skills/nh80-progress/SKILL.md`（仓库内 + 项目级 + 用户级三份）、`scripts/progress_read.py`、`AGENTS.md` 已追加调用说明。
- **安全清理**：Codex v9 误入库的明文答案表 `deploy/worker/src/generated-key.json` 已移出版本库并 gitignore；Worker 只用公开的哈希分片 `web/data/grade/day-*.json`，本地构建仍会生成该表供测试。
- **Service Worker** 版本使用 `nh80-v15-*`，且每日页 HTML 纳入 revision 哈希，避免旧缓存。

## 真源与目录

| 路径 | 作用 |
|---|---|
| `knowledge/seeds/*.jsonl` | 内容种子（词 / 语法 / 汉字 / 句子 / 素材 / 测评），改内容改这里 |
| `scripts/curriculum_v5.py` | 100 天排课、必学/拓展、时间块 |
| `scripts/quiz_v5.py` + `assessment_v6.py` + `practice_v9.py` + `sentence_choices.py` | 确定性出题、私有答案、公开投影 |
| `scripts/ko_pron.py` | 假名→한글 转写、数词量词、整句读音解析（v12 读音层） |
| `knowledge/ko_reading_supplement.json` | 例句读音补充词表（160 条：专名/复合词/活用形，self_reviewed） |
| `scripts/build_v5_site.py` | **唯一页面生成器**：每日页 HTML、CSS、`assets/app.js`、首页、资源页、听力页、资料库、复习集、五日单元、`sw.js` |
| `scripts/nh80.py` | 唯一学习状态写入入口；生成 `curriculum.json`、答案表、grade 分片、DB |
| `scripts/study_ui.py` | 复习集 / 五日单元的本地自评与练习 JS（已去掉口令与自动 POST） |
| `scripts/progress_read.py` | agent 读取云端进度的 CLI |
| `skills/nh80-progress/SKILL.md` | skill 真源 |
| `deploy/worker/src/index.ts` | Worker：`/api/events`、`/api/reviews`、`/api/study`、`/api/progress`、`/api/health` |
| `deploy/migrations/0005_progress.sql` | `study_progress` 表 |
| `scripts/release_guard.py` | 发布前阻断超限额、私有文件、明文答案、付费绑定、D1 未隔离 |
| `tests/test_v10.py` | 页面与进度 不变量回归 |
| `web/`、`curriculum/`、`deploy/worker/src/generated-key.json` | 构建产物；**不要手改** |
| `data/state.db`、`STATE.md`、`days/`、`tasks/`、`data/review/`、`deploy/.sync-key` | 私人状态与密钥，gitignore |

**唯一构建入口**：`python3 scripts/nh80.py build`（或 `init` 重建 DB）。`build_site.py` / `curriculum.py` 是 v4 遗留，**不要手动运行**（会覆盖成 80 天旧站）。改页面改 `build_v5_site.py`，改内容改 seeds 后跑 `init`。

## 启动、验证、部署

```sh
python3 scripts/nh80.py init
python3 scripts/nh80.py validate          # 100 天 / 2489 / 286 / 620 / 0 听力日 / 0 error
python3 scripts/release_guard.py         # paid_features:false
python3 -m unittest discover -s tests -p 'test*.py'   # 现有回归测试
node tests/test_worker_access.mjs && node tests/test_progress_api.mjs
python3 -m http.server 8099 -d web
```

```sh
cd deploy && npm install --no-audit --no-fund
# 新环境才需要：两库各跑 0001–0006 迁移
cd .. && bash scripts/deploy_cloudflare.sh preview
bash scripts/deploy_cloudflare.sh production
```

## 会话协议（任何 agent）

```sh
python3 scripts/progress_read.py --latest          # 云端自报快照
python3 scripts/session_v5.py daily --day N       # STATE / brief / 页面链接
python3 scripts/nh80.py finish-day N              # 本机权威完成判定（唯一写入口）
```

**边界**：云端 `study_progress_120` 是网页自报（`self_reported=1`），`questions[].correct` 与 `accuracy` 客户端自算，服务端不重判；agent 只读、不回写、不据此宣布达标。密钥从 `deploy/.sync-key` 读，禁止打印或写进报告。主会话/每日会话通过 `STATE.md`、`days/day-NNN/{brief,report}.md`、`tasks/` 文件协议协作，WorkBuddy 没有父子会话消息总线。

## 仍未做到（不粉饰）

1. 内容仍是 `ai_draft`，无日语/韩语教师逐条人工审校。
2. 独立精听资源是 Kokoro 合成音，不是真人；真人材料只外链或开放许可音频。
3. 39 道周测/阶段题不是官方模考，不换算 JLPT 分数。
4. `web/data/grade/day-*.json` 哈希分片与旧 `/api/events` 链路仍保留（兼容历史 CLI），但每日页已不再使用；`nh80.py finish-day` 的 70% 门控仍看 `curriculum.question_ids`，和当前每日题共用题号，网页完成快照为自报。
5. 静态音频不支持服务端 Range；加它要把 `/audio/*` 放进 Worker 请求额度，与「静态绕过 Worker」冲突，实测 0.56–0.62 MB 播放正常，故不引入。
6. preview 与 production 共用同一密钥值（库已隔离）。

## 接手纪律

先看本文件与 `CONTRACTS.md`，再跑一次 `validate` + 现有回归测试确认基线。不得改 DB、镜像或评分计数伪造进度；不得覆盖人工日报；不因一次答对判掌握。不引入付费服务、不下载转存受限第三方音频。

一句话开场提示词：

> 读 HANDOFF.md 与 CONTRACTS.md，跑 validate + 全量测试确认基线，然后按用户新需求改动；改完 build、验收、部署两环境、push。
