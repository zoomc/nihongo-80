# HANDOFF · Nihongo 150 v6

2026-11-07 完成并上线。验收、命令输出与线上版本见 `reports/v6_completion.md`；
数据来源与许可见 `DATA_LICENSES.md`。Git 具体提交以 `git log -1` 为准。

- Production：`https://nihongo80.cmjfire.workers.dev`，Version `18d87f04-8414-43e6-a28d-3fa8e5fbd696`
- Preview：`https://nihongo80-preview.cmjfire.workers.dev`，Version `4c022eca-0a84-4244-9f3c-f707e4f46c21`

## 产品决策

中文母语、朝鲜族、韩语母语级，目标高效学习N3。网页提供资源，会话答疑和验收。150天×60分钟，网页42+会话18；常规最多16必学词，听力日最多11。全2700词按天分为2154必学、546拓展；全部资源保留，不强迫每天塞完拓展。

十句中三句必做、七句拓展。完成选择题不足以完成当天，必须有教师录入的真实输出与反馈。默认下一课从SQLite的第一个未完成日计算。平台不会自动传递精确状态，仍须显式读文件。

## 当前交付

- 2700词、276语法、620汉字、1500句，全部可访问。
- 每词均有韩语提示：2050词典匹配＋650 AI释义，来源单独标识。
- 276语法和620汉字完成AI复审，修正多处错判、接续及韩语解释；不冒充人工教师审校或逐字词典认证。
- 45篇原创完整合成音频，Kokoro开放模型本机生成，实测63.3–71.575秒；不是人声录音。正文哈希、编码和时长均验证；来源声明位于web/audio/NOTICE.txt。
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
| data/state.db | 私人权威状态，gitignore；不得手改 |
| student/*.json | 自动导出的只读镜像，gitignore |
| curriculum/、web/、generated-key.json | 构建产物；音频文件随仓库交付，不必下载模型即可运行 |
| days/、tasks/、STATE.md | 运行时生成，不进仓库；report人工内容不自动覆盖 |

## 启动、验证、部署

```sh
python3 scripts/nh80.py init
python3 scripts/nh80.py validate
python3 scripts/release_guard.py
python3 -m unittest discover -s tests -p 'test*.py'
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

已使用0001/0002/0003迁移；0003为个人同步预算。两Worker复用现有D1，不额外创建服务。生产和preview实际版本及逐字校验记录以本次验收报告为准。

## 学习闭环

详见docs/STUDY_GUIDE.md。daily --sync读取本机密钥拉取作答，不把密钥放进命令参数或输出；离线导出的JSON用import-file。作答以session+qid幂等，独立会话不合并；最新课程每题的最新成绩用于完成判定。

教师在output-review.json记录三句批改、两句自主语法造句与三词回忆，confirm-output审核结构并记录能力；两句语法未通过不会放行完成。finish-day要求当天题目全有成绩、正确率≥70%且输出验收通过。自评与听力理解不擅自推进不相关卡片掌握。

旧浏览器失败载荷与新题号分开保留，重载后能恢复本版本答案并重试，原始旧载荷不丢。公开页面只包含课程复习词，不再打包本机FSRS阶段或真实学习记录。

## 免费与许可

当前Cloudflare Dashboard已核验Workers Free，未升级套餐。除首页 `/` 与 `/api/*` 外的静态页面、音频绕过 Worker；API读写均需个人口令，无定时任务、云AI、R2、KV或其他付费绑定。单项目同步另限1000条/UTC日、5000条总预算，超限拒绝并保留本机导出路径。额度是账户共享，其他项目或未来人为升级需单独管理，发布脚本不会自动升级。

资源许可及模型/词典署名见 `DATA_LICENSES.md` 与 `docs/RESOURCE_POLICY.md`；个人使用也不等于可以把外部受限音频公开上传。Apple系统声音产物只留在本机忽略目录，不发布。源内容含AI草稿，AI复审不是人工认证；以实际输出及官方样题衡量学习效果，不保证考试结果。

## 接手纪律

先看本文件、v6完成报告和CONTRACTS末尾v6修订。不得改DB、镜像或评分计数伪造进度；不得覆盖人工日报；不因一次答对判掌握。测试遵循先复现bug再修复，不补实现镜像测试、不新增CI测试。不操作Surge引擎或家庭旁路由。
