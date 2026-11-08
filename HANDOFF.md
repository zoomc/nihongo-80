# HANDOFF · Nihongo 150 v9

2026-11-08：当前为 v9，新增词法翻页练习、五日复习单元、私有错题与跨会话 FSRS 同步，验收见 `reports/v9_completion.md`。v8记录见 `reports/v8_learning_ui.md`。v7.1历史发布基线：v7 做了三路独立复审（内容库 / 免费听力资源 / 课程与题目质量）并修掉点名问题；
v7.1 收尾又消掉两条技术边界：Safari 音频兼容、preview 与 production 的 D1 数据隔离，并清理全部临时残留。
验收与命令输出见 `reports/v7_completion.md`，v6 记录见 `reports/v6_completion.md`，
数据来源与许可见 `DATA_LICENSES.md`。Git 具体提交以 `git log -1` 为准。

- 当前v9 Production：`https://nihongo80.cmjfire.workers.dev`，Version `fd52e145-11e2-48d9-ab86-030d50b8c399`
- 当前v9 Preview：`https://nihongo80-preview.cmjfire.workers.dev`，Version `632d564c-65da-423b-b9c4-a6be99f2e912`

## v9 学习与同步入口

- 普通语法讲解不遮盖；今日重点红色加粗、句型与接续蓝色，浅色／深色均可用。
- 全题库 8007 题：既有2535＋每日词法选做4872＋五日单元600；每天选做24–36题，必做门槛保持原样。
- `review.html` 私人错题／忘了／不熟／到期清单，`unit-005.html` 至 `unit-150.html` 共30个完整五日词法清单与20题抽样巩固。
- 浏览器先持久化再批量同步，失败保留；自评和答题分别幂等。个人状态通过口令API取，公开catalog不含个人进度。
- WorkBuddy／其他 agent 开始：`python3 scripts/session_v5.py daily --sync`，显式读取 `data/review/CONTEXT.md`、`context.json` 及当天brief；结束：`python3 scripts/nh80.py study-sync --push-only`，确认 `published: true`。这由项目工作流执行，不依赖平台记忆。
- 离线导出的 `nihongo-pending.json` 与旧每日作答文件均可经 `nh80 import-file --file ...` 导入，再发布计划；不手改SQLite。
- 私有同步上下文、SQLite、学习口令不入Git。新增构建模块 `practice_v9.py` / `study_ui.py`，同步模块 `study_sync.py`。D1 的 `0004_study.sql` 已应用两环境。

## 产品决策

中文母语、朝鲜族、韩语母语级，目标高效学习N3。网页提供资源，会话答疑和验收。150天×60分钟，网页42+会话18；常规最多16必学词，听力日最多11。全2700词按天分为2154必学、546拓展；全部资源保留，不强迫每天塞完拓展。

十句全部转为选择题，三题必做、七题拓展。网页选择题模式不要求手写或教师输出验收；导入后由CLI自动按完整性和70%正确率计算完成。默认下一课从SQLite的第一个未完成日计算。平台不会自动传递精确状态，仍须显式读文件。

## 当前交付

- 2700词、276语法、620汉字、1500句，全部可访问。
- 每词均有韩语提示：2050词典匹配＋650 AI释义，来源单独标识。
- 276语法和620汉字完成AI复审，修正多处错判、接续及韩语解释；不冒充人工教师审校或逐字词典认证。
- 45篇原创完整合成音频，Kokoro开放模型本机生成，实测63.3–71.575秒；不是人声录音。
- 45 篇听力共 135 道理解题已重写：9 个模板的 5 变体 Q3 答案互不相同，`audio_text` 哈希与音频逐条一致。
- 新增 `web/listening.html`：4 条 Wikimedia Commons PD/CC BY-SA 开放音频可在本页播放并逐文件署名；
  每条同时给 Wikimedia 官方 mp3 转码与原始 Ogg 两个 `<source>`，Chrome / Firefox / Safari 均可播放。
- D1 已按环境隔离：`nihongo80`（production）与 `nihongo80-preview`（preview）两个独立库，四段 migration
  均已 `--remote` 应用；preview 的测试事件不会写入生产 `events` 表。两库都在 Workers Free 的
  10 个 D1 免费额度内，不产生额外费用。`release_guard.py` 会拒绝两环境共用一个库的配置回退。
  15 条免费真人听力/官方样题按阶段分组跳转原站；8 条不采用源列明原因。每日精听主线仍是本站合成音频。
- 21个周测日、6个阶段/自测日有39道原创阅读/语境题，替换每日六题中的部分题；Day1有三道假名/助词诊断。45个听力日另三题，不以短测假冒官方模拟卷。
- 官方N3题型、练习集与真人听力、Irodori、Tadoku、NHK入口位于resources.html，受限内容只链接原站。
- 首页按周分组、有继续学习入口；旧n3-mock入口改为官方资源引导。

## 真源和目录

| 真源/入口 | 作用 |
|---|---|
| knowledge/seeds/*.jsonl | 内容种子，保持真实来源和审核状态 |
| scripts/curriculum_v5.py | 150天排课、必学/拓展、预算 |
| scripts/quiz_v5.py + assessment_v6.py | 同源确定性出题、私有答案及公开投影 |
| scripts/build_v5_site.py | 页面/CSS/JS/索引生成；不直接改web |
| scripts/nh80.py | 唯一学习状态写入入口，事务与audit_log |
| scripts/learning.py | FSRS、能力卡、掌握门控 |
| scripts/session_v5.py | 下一课、STATE、brief、输出模板、日报协议 |
| scripts/cloud_sync.py | 从D1拉取原始事件，再由本地重判 |
| scripts/open_audio_assets.py | 开放模型离线重建音频，固定版本并校验哈希 |
| scripts/release_guard.py | 发布前阻止超文件限额、私有文件或付费服务绑定混入 |
| knowledge/resources_v7.json | 27 个外部听力/阅读源的许可与嵌入能力清单 |
| web/listening.html | 真人听力页（4 条可播开放音频 + 分阶段外链，生成物） |
| tests/test_v7.py | 14 项 v7 核心不变量回归 |
| data/state.db | 私人权威状态，gitignore；不得手改 |
| student/*.json | 自动导出的只读镜像，gitignore |
| curriculum/、web/、generated-key.json | 构建产物；音频文件随仓库交付，不必下载模型即可运行 |
| days/、tasks/、STATE.md | 运行时生成，不进仓库；report人工内容不自动覆盖 |

## 启动、验证、部署

```sh
python3 scripts/nh80.py init
python3 scripts/nh80.py validate
python3 scripts/release_guard.py
python3 -m unittest discover -s tests -p 'test*.py'   # 45 项
node tests/test_worker_access.mjs  # 需要deploy/npm install后的esbuild
python3 -m http.server 8099 -d web
```

修改内容后用 `init` 重新导入；只改呈现用 `build`。`build_site.py` / `curriculum.py` 是 v4 遗留，CLI 与部署脚本已不调用，**不要手动运行**（会生成 80 天旧站并覆盖 `web/`）。

```sh
cd deploy
npx wrangler d1 migrations apply nihongo80 --remote --config wrangler.jsonc
cd ..
bash scripts/deploy_cloudflare.sh preview
bash scripts/deploy_cloudflare.sh production
```

已使用0001/0002/0003迁移；0003为个人同步预算。两Worker分别使用独立D1，保持预览与生产隔离，本轮不新增服务。生产和preview实际版本及逐字校验记录以本次验收报告为准。

## 学习闭环

详见docs/STUDY_GUIDE.md。daily --sync读取本机密钥拉取作答，不把密钥放进命令参数或输出；离线导出的JSON用import-file。作答以session+qid幂等，独立会话不合并；最新课程每题的最新成绩用于完成判定。

choice模式由网页明确上报，D1元数据传回CLI后按完整必做题＋70%正确率计算完成，不需confirm-output或手写批改。日常基础题仍1035道，另将1500句生成1500道四选一，总答案表2535题；拓展7题不进入完成判定分母。旧教师验收接口兼容历史模式，选择题不推进production能力。

旧浏览器失败载荷与新题号分开保留，重载后能恢复本版本答案并重试，原始旧载荷不丢。公开页面只包含课程复习词，不再打包本机FSRS阶段或真实学习记录。

## 免费与许可

当前Cloudflare Dashboard已核验Workers Free，未升级套餐。除首页 `/` 与 `/api/*` 外的静态页面、音频绕过 Worker；API读写均需个人口令，无定时任务、云AI、R2、KV或其他付费绑定。单项目同步另限1000条/UTC日、5000条总预算，超限拒绝并保留本机导出路径。额度是账户共享，其他项目或未来人为升级需单独管理，发布脚本不会自动升级。

资源许可及模型/词典署名见 `DATA_LICENSES.md` 与 `docs/RESOURCE_POLICY.md`；个人使用也不等于可以把外部受限音频公开上传。Apple系统声音产物只留在本机忽略目录，不发布。源内容含AI草稿，AI复审不是人工认证；以实际输出及官方样题衡量学习效果，不保证考试结果。

## 接手纪律

先看本文件、v7完成报告和CONTRACTS末尾v7修订。不得改DB、镜像或评分计数伪造进度；不得覆盖人工日报；不因一次答对判掌握。测试遵循先复现bug再修复，不补实现镜像测试、不新增CI测试。不操作Surge引擎或家庭旁路由。
