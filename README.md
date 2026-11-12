# Nihongo 120 · 个人 N3 学习系统

120 天的日语资源与会话教学。适合中文母语、朝鲜族（韩语母语级）学习者：借语法迁移，把时间放在词汇、句子与听读。

**线上入口：https://nihongo80.cmjfire.workers.dev**

## 每天怎么用

**每天新开一个会话，第一条命令固定是：**

```sh
python3 scripts/today.py
```

它把「课程表 + 本机 finish-day（权威）+ 云端「完成」快照（自报）」合并，直接告诉你：今天该学 Day 几、已经完成几天、上次正确率与卡点、今天必学词/语法/汉字、页面链接，并写 `TODAY.md`（同时刷新 `STATE.md` 与当天 `brief.md`）。会话读 `TODAY.md` 就能开工，不需要你复述进度。

- 云端连不上：`--offline`（只用本机，文件里会写明）；补课/回看：`--day N`；给程序用：`--json`。

网页只放内容，打开就是今天：**今日复习 → 今日新词 → 今日语法 → 一整块练习**，底部只有一个「完成」按钮。没有顶部模式按钮、分段导航、时间块、学习口令、导出/同步按钮。

- **遮盖下放到模块**：新词与语法各有一个局部开关（显示 / 遮中文 / 遮日语 / 双向），互不影响；点模糊处可临时揭开。
- **小日语文字 + 发音**：新词左栏是日语与假名，右栏是中文与韩语读音。例句可展开，例句汉字带 ruby 注音，并可朗读。
- **每日练习**：当天每个词两题、每条语法三题，题序与选项打乱。先练必学词和语法，再练选学词。题尾可只重练答错的题。听力日可先听音频复述，再展开脚本核对。
- **完成 → 云端 → agent**：点「完成」把当天答题、正确率、错题、自评上报 `/api/progress`，写入 Cloudflare D1 `study_progress`（按天幂等覆盖）。页面**不需要任何口令**；agent 侧用 `X-NH80-Key` 读取。

```sh
# 任何 agent（WorkBuddy / Claude Code / Codex）读取学习情况
python3 scripts/progress_read.py --latest        # 最近 7 天
python3 scripts/progress_read.py --day 47 --json
```

Skill 规范在 [`skills/nh80-progress/SKILL.md`](skills/nh80-progress/SKILL.md)（同一份已安装到 `~/.workbuddy/skills/` 与项目级 `.workbuddy/skills/`）。**云端进度是自报快照、非掌握权威**；本机 `data/state.db`（只经 `nh80.py finish-day` 写入）才是权威，agent 只读不回写，密钥不打印、不入库。

## 内容规模

2700 词（必学与拓展分开）、276 语法、620 汉字、1500 句、45 篇原创合成听力、120 天 × 60 分钟课程。韩语提示覆盖全部词汇：2050 条开放词典匹配、650 条 AI 释义。内容仍是 AI 草稿，未做教师逐条人工审校。

听力分两层：**每日精听**是 45 篇原创文本的合成音频；**真人听力页**提供 4 条开放许可音频（mp3 / Ogg 双格式，Safari 可播）以及 JLPT 官方样题、Irodori、Erin、NHK、免费播客等分阶段入口（跳转原站，不托管第三方音频）。

- [怎么学](docs/STUDY_GUIDE.md) · [真人听力页](web/listening.html) · [接手与构建](HANDOFF.md)
- [v10 完成验收](reports/v10_completion.md)（[v9](reports/v9_completion.md) · [v7](reports/v7_completion.md) · [Codex 会话调查](reports/codex_v8_investigation.md)）
- [数据来源与许可](DATA_LICENSES.md) · [外部资源与免费额度](docs/RESOURCE_POLICY.md)

```sh
python3 scripts/nh80.py init
python3 scripts/nh80.py validate
python3 scripts/release_guard.py
python3 -m unittest discover -s tests -p 'test*.py'   # 67 项
node tests/test_worker_access.mjs && node tests/test_progress_api.mjs
```

内容含 AI 释义与 AI 审校，合成音频不是人声录音。系统不调用付费云端 AI、不自动订阅或升级云服务；当前部署为已核验的 Cloudflare Workers Free。本站短测不换算 JLPT 官方成绩。

词汇等基础数据：OpenJLPT（CC BY-SA 4.0）；韩语词典字段：韩国国立国语院 한국어기초사전（CC BY-SA 2.0 KR）；原创文本合成语音：Kokoro-82M（Apache-2.0）+ UniDic 3.1.0，完整署名见 [音频 NOTICE](web/audio/NOTICE.txt)。
