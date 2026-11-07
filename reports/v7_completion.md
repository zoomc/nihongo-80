# v7 完成与验收报告（2026-11-08）

三路独立 subagent 并行复审 → 汇总 → 修复 → 验收 → 部署 → push。
本报告只写跑过的命令与真实输出；没做到的单列在最后一节。

## 1. 三路复审发现了什么

| 路线 | 抽样/范围 | 结论 |
|---|---|---|
| 内容库与 AI 生成内容 | 逐条核读 226 条 + 全库 6220 行结构统计 | 23 条可执行修复（high 13 / medium 6 / low 4）；另有 26 条 `pos="词"` 占位符、`zh_trap` 空 140 条（设计允许）、`grammar.usage` 英文残留 1 处 |
| 免费听力资源 | 25 个候选源逐个实际访问 + 许可核实 | 2 可嵌入 / 15 只能外链 / 8 不采用；纠正 4 处原有来源判断错误；2 个 Archive.org 条目实为商业教材/专辑，绝对不用 |
| 课程与练习题 | 36 个检查项，PASS 19 / PARTIAL 10 / FAIL 7 | 7 个 FAIL：听力难度倒挂、阶段日丢汉字/语法题、复习快照只有词汇、语法重复与级别错标、3 道汉字题只有 3 选项、58 题答案写在题干里、测评标签不一致 |

最严重的 5 个已全部修掉：`G0148`/`G0066` 把合法日语判成错句、`V1469`/`V2462` 例句与词条无关、
`K0172`/`K0296`/`K0372` 音读混入外来单位词、听力素材 N4/N3 倒挂、45 篇听力题模板化可凭记忆作答。

原始报告：`reports/v7_content_review.md`、`reports/v7_listening_sources.md`、
`reports/v7_curriculum_quiz_review.md`、`reports/v7_listening_questions.md`；
结构化清单：`reports/evidence/v7_content_issues.jsonl`（23 行）、`v7_curriculum_issues.jsonl`（26 行）。

## 2. 内容修复（全部落地）

- **23 条硬错误**按 JSONL 的 `fix` 直接写入：合法句不再判错、例句改用本词、病句改正、
  音读数组去掉 `ダース/リットル/メエトル`、`V0349` 韩语提示改为 `열다` 并标 `ai_gloss`、
  `S1462` 主题与存在句冲突改正、`V0879` 补「（电池）耗尽」义项、`G0084` 删英文残留等。
- **26 条 `pos="词"`** 按标准日语词性补正（连体词 / 形容词 / 名词 / 动词(五段·サ变)），全库 `词` 归零。
- **3 条语法 jlpt 错标**（G0241/G0242/G0234，先修指向 N3 却标 N4）归位 N3；`G0052` 补 `G0187` 先修，修掉授受成组倒序。
- **9 条测评标签** `mock` → `self_check`；`A130-3`/`A148-3`/`A021-1` 三道题的选项与剧透修正。
- **45 篇听力 135 道题重写**：`audio_text`/`text_ja` 逐字不动（manifest 哈希 45/45 一致），
  9 个模板各自 5 变体的 Q3 答案全局互不相同；`M0057` 补独立短文消除与 `M0034` 的冗余。

## 3. 课程与题目修复

| 问题 | 修复 |
|---|---|
| 听力素材难度倒挂（原按字符串排序，N3 < N4） | `curriculum_v5.py` 改数值 rank；实测 Day47–88 全 N4、后期全 N3，`N4 in late = 0` |
| 6 个阶段/自测日丢汉字与语法题 | `quiz_v5.py` 题目顺序改 K/K/G/V/V/R，替换尾部题仍保留 K/G；实测 6 天均有 K0/K1/G |
| 3 道汉字题只有 3 选项 | `add()` 不足 4 项时从同类池补齐并断言；全库 1035 题选项数分布 `{4: 1035}` |
| 58 题把答案写在题干（中日同形词） | 释义含词形时改出「假名 → 词形」题，选项全是日文词形；回归测试锁住 |
| 干扰项与答案同义 / FNV 归一化重复 | 干扰项排除相同释义；每题断言 4 个哈希互异 |
| 语法只考第 1 条、复习快照只有词汇 | 语法按天轮换；复习快照 V/G/K 三类（888 / 548 / 342）；复现题三类轮换 |
| 同义语法连着两天教、级别重叠 | 同义至少错开 7 天；3 条错标归位；拓扑断言先修严格在前 |
| 共用读解材料重复渲染 2 次 | `initQuiz` 记录上一题 passage，连续相同显示「（同上材料）」；Day110/130/132/148 实测 2 段 + 1 标记 |
| `lesson_core` 截断、`is_listening_day` 阈值 46 | 改 `[:6]`、`day>=47`，与 `meta.listening_from=47` 和页面文案一致 |
| DB 有 988 条孤儿题、import-web 用 payload day 兜底 | `_build_v5` 写入后清理孤儿；`cmd_import_web` 拒绝无 `day` 的题；实测 DB 1035 = 答案表 1035，孤儿 0 |
| `nh80.py init` 在已有 `curriculum/` 时报 `FileExistsError` | 建目录改幂等判断 |

课程 `meta.honesty` 明确写「6 题为当天新内容抽样，不覆盖全部条目」，不把抽样成绩说成全量掌握。

## 4. 听力资源「替换上」的落地方式（诚实口径）

调研核实后又用 Commons API 逐文件补查作者与许可，清单扩到 **27 源**：

- **4 条可在本页播放**：Wikimedia Commons 的 PD / CC BY-SA 日语发音与百科朗读，
  `<audio src>` 指向官方 CDN，逐文件给作者、文件页、许可全文。4 条直链实测 200 `application/ogg`，
  线上 Chrome 实测可播（31 秒 / 93 秒，`readyState=4, error=null`）。
- **15 条免费真人听力 / 官方样题**：JLPT 官方样题、Irodori、Erin、NHK Easy Japanese、
  Tadoku、6 个免费播客，按 Day 47–90 / 91–130 / 131–150 三阶段分组，**点击跳转官方原站**，
  `embed_url` 一律留空，不复制、不下载、不热链。
- **8 条不采用**：付费墙、明确禁止公开再分发（Marugoto Q7）、海外地区限制（NHK Easy News）、
  许可待核实、或「日语」内容实为英语朗读（LibriVox）。页面折叠列出原因。

新增 `web/listening.html`；`web/resources.html` 改版；首页、每日页顶部/页脚、45 个听力日听力块内
按阶段给 3 个真人听力外链。`web/library.html` 保留 45 篇原创资料的音频播放器。

**不能说成**：已内置真人听力音频库、已替换为真人语音、站内可直接播放 N3 官方真题音频、
免费=可随意转载。**每日精听主线仍是 45 篇原创文本的 Kokoro 合成音频**，真人材料是补充，
页面明文写出「不托管在本站、不复制、不下载、不热链第三方音频」。

## 5. 自动验收

```
python3 scripts/nh80.py validate
  → ok True, error 0, days 150, totals {v:2700,g:276,k:620}, listening 45

python3 scripts/release_guard.py
  → {"ok": true, "files": 358, "asset_bytes": 32047031, "public_audio": 45,
     "cloud_bindings": ["existing D1"], "paid_features": false}

python3 -m unittest discover -s tests -p "test*.py"
  → Ran 41 tests ... OK      （v6 的 27 项 + v7 新增 14 项核心不变量）

node tests/test_worker_access.mjs
  → PASS: unauthenticated writes denied before database access
  → PASS: authenticated check probes D1 without writing
```

浏览器实测（Chrome headless，375×812 与 1280×900，线上）：
Day 1/45/47/110/150 均无横向滚动、无 console/pageerror、无明文答案；
6 题全部 4 选项、遮盖四态（日语→双向→关→中文）、判分反馈正常；
听力日 6 块、音频可播 65/71 秒、3 道听力题、3 个真人听力外链；
Day110 共用材料只渲染 2 段 + 1 个「同上材料」；
`/listening.html` 4 个音频、诚实声明与署名齐全。

## 6. 部署

| 项 | 值 |
|---|---|
| Production | `https://nihongo80.cmjfire.workers.dev`，Version `86f66f9e-3fda-412d-8650-5f2876d0a4fa` |
| Preview | `https://nihongo80-preview.cmjfire.workers.dev`，Version `0781c3f1-f63e-48da-ad91-7fa314133a77` |
| `/api/health` | `{"status":"ok","features":{"db":true,"sync":true}}`（两环境） |
| 页面 | `/`、Day 1/7/45/47/110/150、`/listening.html`、`/resources.html`、`/library.html` 全 200 |
| 音频 | `/audio/M0096.m4a` 561198 B、`/audio/M0140.m4a` 616046 B 均 200 |
| 答案表 | `/data/answer-key.json` → 404 |
| 字节一致 | `index.html`、`day-047.html`、`listening.html`、`resources.html`、`app.js`、`app.css`、`data/day-047.json` 本地与线上 SHA-256 全部 MATCH |
| 接口 | 无 key POST/GET → 401；带 key check → `{"ok":true,"check":true,"stored":0}` |

## 7. 免费与法律边界

- Cloudflare 仍为 Workers Free；无 R2 / KV / AI / 定时任务；`observability=false`；
  静态页与音频绕过 Worker（仅 `/` 与 `/api/*` 进 Worker）；同步另限 1000 条/日、5000 条总预算。
- Commons 音频为外链，不占本站静态存储；Wikimedia 不建议大流量热链，本项目为低流量个人站。
- 4 条 Commons 文件的作者与许可经 `imageinfo/extmetadata` 逐文件核实，署名与许可链接随卡片给出，
  仅播放未改编；清单见 `DATA_LICENSES.md` 与 `docs/RESOURCE_POLICY.md`。
- 受限真人音频一律外链，未下载转存，避免侵权与额外费用。

## 8. 仍未做到（不粉饰）

1. 全部内容仍是 `ai_draft`：本轮修掉三路复审点名的硬错误，但没有日语/韩语教师逐条人工审校，
   2700 词里仍可能有漏网。
2. 每日精听仍是**合成音**不是真人；4 条可播的 Commons 音频是发音/百科朗读，不是 N3 会话，
   15 条真人听力只提供官方原站跳转。
3. 39 道周测/阶段题是轻量练习，不换算 JLPT 分数；官方样题只在资源页外链。
4. `zh_trap` 空 140/620（设计上「只在真会错时写」），`ko_hanja` 空缺由 `ko_hint` 覆盖，不逐字人工核证。
5. 本站静态音频**不支持服务端 Range**：实测 `/audio/M0096.m4a` 对 `Range: bytes=1000-1999`
   返回 200 全量 561198 B，无 `accept-ranges` / `content-range`；Commons mp3 则返回 206 +
   `content-range`。要支持必须把 `/audio/*` 放进 `run_worker_first`，让所有音频请求进入
   Worker 请求额度，与「静态资源绕过 Worker、零计费维度」的既有设计冲突。单篇 0.56–0.62 MB、
   `preload="none"`、实测播放与拖动正常，因此**评估后不引入**，不是遗漏；若将来需要弱网流式播放，
   加一个只处理带 Range 请求的 Worker 路由即可，代价是音频请求开始计入 Workers Free 的 10 万次/日。
6. 6 题为当天新内容抽样，语法/汉字/词汇的评估覆盖率仍低于教学覆盖率；这是 60 分钟预算内的取舍，
   已写进 `meta.honesty`，门控只代表抽样题 + 教师输出验收，不代表全量掌握。

原 v7 第 8 节里的「Safari 不支持 Ogg」「preview 与 production 共用同一 D1」两条，
已在 v7.1 收尾中消除，见下节。

## 9. v7.1 收尾（2026-11-08，全部完成）

| 项 | 处理 | 证据 |
|---|---|---|
| 残留清理 | `/tmp` 里 v6 遗留的 9 个临时脚本全部删除；`deploy/node_modules`、`data/audio` 均未留在仓库 | `git status --porcelain` 为 0，无密钥/运行时文件被跟踪 |
| Safari 音频 | 4 条 `inline` 源新增 `mp3_url`（Wikimedia 官方转码，实测 206 `audio/mpeg`）；`audio_card` 输出 mp3 + Ogg 双 `<source>` | `web/listening.html` 4 个 `<audio>`、4 个 mp3 source、4 个 Ogg source；旧「Safari 请打开文件页」提示已移除 |
| D1 隔离 | 新建 `nihongo80-preview`（APAC），三段 migration `--remote` 应用；`wrangler.jsonc` 的 `env.preview` 改绑独立库 | 远端表 `events`/`sync_budget` 存在；两库 `database_id` 不同；preview 写入的事件不出现在生产库 |
| 零扣费核实 | Cloudflare 官方文档核实：Workers Free 含 10 个 D1 库、5M 行读/天、10 万行写/天、5 GB 存储；超限只报错不自动计费 | `developers.cloudflare.com/d1/platform/pricing/` 与 `/limits/` |
| 配置注释 | 删掉过时的 `REPLACE_WITH_D1_ID`、「不含任何 database_id」；`0001_events.sql` 的 `day` 注释 80→150 | 配置文件与文档一致 |
| 发布守卫 | 新增「两环境必须是两个不同 D1」断言；输出标明 `D1 prod` / `D1 preview (isolated)` | 新增回归测试用临时目录故意改回共用库，守卫确实报错拦截 |
| 回归测试 | `tests/test_v7.py` 新增 3 项 | Python 41→**44 项全绿** + 2 项 Worker 访问测试 |
| 文档 | README / HANDOFF / CONTRACTS / DATA_LICENSES / RESOURCE_POLICY / CLOUDFLARE / 本报告同步 | 无过时口径 |

**部署版本**：production / preview 的 Version ID 见本节末尾的部署记录。
