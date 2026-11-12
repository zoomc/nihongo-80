# Nihongo 120 · 当前项目入口（v11）

先读 `HANDOFF.md`、`reports/v6_completion.md`、`CONTRACTS.md`（末尾 v11 修订优先于旧版示例）。当前目录名 nihongo-80 是历史名称，课程是 120 天。

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

## 每日会话（新会话第一步）

**不要问用户「学到哪了」。** 每个新会话第一条命令：

```sh
python3 scripts/today.py
```

它把「课程表 + 本机 finish-day（权威）+ 云端「完成」快照（自报）」合并，算出今天该学哪天、上次卡在哪、今天的词/语法/汉字/页面链接，写 `TODAY.md` 并刷新 `STATE.md`。然后读 `TODAY.md`，按里面「会话怎么做」执行；需要更细内容再读 `days/day-NNN/brief.md`。

- 云端连不上：加 `--offline`，只用本机记录，`TODAY.md` 会写明。
- 补课/回看：`--day N`。
- 机器可读：`--json`；只看不写：`--no-write`。

`session_v5.py daily` 仍可用（调 brief/state），但不再是入口；`study-sync` 只用于私有复习上下文，不是每日必经步骤。显式读取 `data/review/CONTEXT.md`（若存在）、STATE、当天 brief 与数据库（只读）。先给页面链接，等学生看完；答疑只讲他没懂的，逐题问错因。网页不要求手写，前 9–12 道基础题优先。页面不显示时间块，当天精确内容只取课程 blocks。

网页提交只代表原始作答保存。同步使用 `deploy/.sync-key` 本机密钥（禁止显示或提交）。choice模式导入后，CLI自动按必做题完整性及70%正确率计算完成，无需手写验收；未达标记录incomplete，不降低难度。旧教师输出接口仅兼容历史会话。

## 不可违反

- 不把读完页面记完成；必须有作答证据；一次答对不算掌握，门控由脚本计算。
- 自评只排复习，不作为客观能力测试。听力理解题只记练习证据，不推断知识卡掌握。
- 外部受限教材只索引，不复制正文；真人音频未落地就是未落地。
- 不引入向量数据库；检索继续 SQLite FTS5 与结构化关系。
- 任何模块变更先更新契约；发现契约与用户指令冲突先告知，不擅自决定。
- 测试按用户当前全局规则：bug 先复现再修；不在实现之后补镜像测试，不擅自删除已有测试。

## 角色

agents/teacher.md / examiner.md / reviewer.md / director.md 仅作为教师、考官、复习官、总监职责参考。其旧时间块和回传码流程不覆盖本文件与 v8 契约。数据评分继续按 CONTRACTS 的掌握门控执行。

## 通过 skill 读取学习进度

云端「完成」按钮把当天**自报快照**写入 `POST /api/progress`；任何 agent 用 `GET /api/progress` + `X-NH80-Key` 读取。**云端进度是自报、非掌握权威**；本机 `data/state.db`（只经 `python3 scripts/nh80.py finish-day` 写入）才是权威，不回写、不据此判掌握。

- Skill 规范：`skills/nh80-progress/SKILL.md`（源真本）。同一个文件装到 4 个加载位置：本仓库 `skills/`、仓库 `.workbuddy/skills/`、工作区根 `.workbuddy/skills/`、用户级 `~/.workbuddy/skills/`，WorkBuddy 本机立即可用。
- 改完 skill 必须同步，否则会出现「PC 能触发、换机器不触发」：`python3 scripts/skill_sync.py --write`；`--check` 只校验（不一致退出 1）。
- CLI：`python3 scripts/progress_read.py --latest`（最近 7 天）/ `--day N` / `--json`；密钥默认读 `deploy/.sync-key`，**禁止打印或写入**。

工作区根 `/Users/mj/Documents/learn/jp` 还有一份 `AGENTS.md` 做路由（会话 cwd 在根，不在本目录），内容只指向本文件与 `today.py`，**不承载规则**。那份不在 git 里，换机器需重建。

给 Claude Code / Codex 的一句话提示词：

> 读一下我的日语学习进度：在仓库根执行 `python3 scripts/progress_read.py --latest`，按 `skills/nh80-progress/SKILL.md` 把「错题优先 + 自评 again/hard 优先 + 当天新词/语法」整理成今天的复习重点；记住云端进度是自报快照、本机 SQLite 才是掌握权威，别据此判定已掌握，也别打印密钥。
