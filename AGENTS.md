# Nihongo 150 · 当前项目入口（v6）

先读 `HANDOFF.md`、`reports/v6_completion.md`、`CONTRACTS.md`（末尾 v6 修订优先于旧版示例）。当前目录名 nihongo-80 是历史名称，课程是 150 天。

## 产品与学习者

中文母语、朝鲜族、韩语母语级；语法可迁移，重点是词汇与独立造句。网页是资源，会话是教师。不要改成仪表盘、多用户或题库平台。

## 真源与唯一写入通道

- 内容：`knowledge/seeds/*.jsonl`，可审计的人类/AI 草稿；不把 AI 内容升级为 verified。
- 课程：`curriculum_v5.py` 生成；网页：`build_v5_site.py` 生成。`curriculum.json`、`web/` 不手改。
- 状态：`data/state.db` 唯一真源，**只经 `python3 scripts/nh80.py ...` 写入**（事务与 audit_log）。不得手改 DB、FSRS、阶段、门控计数。
- `student/*.json` 是 export_state 生成的只读镜像，不手改当状态。
- STATE/brief 是生成文档，不承载权威评分；report 是人工记录，不自动覆盖。
- 跨会话只能显式读文件，平台记忆不能传递精确状态。不宣称自动续课、自动传递或自动调度。

## 构建与验证

```sh
python3 scripts/nh80.py init
python3 scripts/nh80.py validate
python3 -m unittest discover -s tests -p test_v5.py
```

只用 nh80 init/build。禁止运行 v4 `scripts/build_site.py`、`scripts/curriculum.py` 重建当前站点。运行时状态、密钥、Wrangler 本地状态不提交。部署步骤见 HANDOFF。

## 每日会话

```sh
python3 scripts/session_v5.py daily --day N
python3 scripts/nh80.py start-day N
```

读 STATE、当天 brief、curriculum 与数据库（只读）。先给页面链接，等学生看完；答疑、抽词造句、语法造两句、批改三句必做翻译，其余七句拓展。网页预算 42 分钟，会话 18 分钟，听力已包含在 42 分钟内。当天精确内容和时间只取课程 blocks，不使用旧 80 天模板。

网页提交只代表原始作答保存。云端拉取要使用本机密钥（禁止显示或提交），见 `nh80.py pull-cloud --help`。句子草稿拉取后在 days/day-NNN/web-drafts.json，需教师批改。教师填 output-review.json 并运行 confirm-output 后，写 report 再 finish-day；未达标记录 incomplete，不降低难度。

## 不可违反

- 不把读完页面记完成；必须有作答证据；一次答对不算掌握，门控由脚本计算。
- 自评只排复习，不作为客观能力测试。听力理解题只记练习证据，不推断知识卡掌握。
- 外部受限教材只索引，不复制正文；真人音频未落地就是未落地。
- 不引入向量数据库；检索继续 SQLite FTS5 与结构化关系。
- 任何模块变更先更新契约；发现契约与用户指令冲突先告知，不擅自决定。
- 测试按用户当前全局规则：bug 先复现再修；不在实现之后补镜像测试，不擅自删除已有测试。

## 角色

agents/teacher.md / examiner.md / reviewer.md / director.md 仅作为教师、考官、复习官、总监职责参考。其旧时间块和回传码流程不覆盖本文件与 v6 契约。数据评分继续按 CONTRACTS 的掌握门控执行。
