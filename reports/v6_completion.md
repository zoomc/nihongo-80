# v6 完成与验收报告（2026-11-07）

本报告记录 Codex 会话 `01a1b609…` 的中断点、续做内容与最终验收。**只写跑过的命令与真实输出**；
未做到的事单列在最后一节，不包装成已完成。

## 1. 中断点

Codex 在 15:14 完成本地验证，最后一句是「正在发布预览版」，随后会话中断。工作区留下
481 个已修改文件 + 26 个未跟踪文件（音频、测评、资源页、迁移、v6 脚本），未提交、未部署。

本地状态：`27 tests OK`、`validate 150 天 / 2700 / 276 / 620`、`release_guard ok`，
但 `web/audio` 未上线（生产 `/audio/M0096.m4a` 为 404），`reports/v6_completion.md` 缺失。

## 2. 续做内容

| 问题 | 处理 | 证据 |
|---|---|---|
| `nh80.py init` 在已有 `curriculum/` 时抛 `FileExistsError` | `curriculum_v5.py` / `build_v5_site.py` 的建目录改为先判断再建 | 重跑 `init` 退出 0，150 天 |
| 生产 `/` 返回 404（`run_worker_first` 删了 `/`，而 `html_handling=none` 不映射 index） | 生产与 preview 恢复 `["/", "/api/*", "/health"]`；`release_guard` 增加「两处都要有 `/`」断言 | 线上 `/` 与 `/index.html` 均 200 / 16905 B |
| `check:true` 冒烟被 `empty_results` 提前拦截，D1 检查是死代码 | 把 check 分支前移到题目解析之前，只探 D1、不写入 | `POST {"day":1,"check":true}` → `{"ok":true,"check":true,"stored":0}` |
| 练习答错只显示「错。」，无任何提示 | 改为「错，正确项已标绿。回会话讲清为什么，再造一句自己的话。」（不含答案） | 浏览器实测文案 |
| 资料库 45 篇只有 TTS 按钮，没有音频 | `library.html` 为有音频的素材加 `<audio>` 与时长 | 线上 `/library.html` 有 45 个 `<audio>` |
| preview Worker 没有 `NH80_SYNC_KEY`，`/api/health` 显示 sync:false | 为 `--env preview` 设置同一密钥 | preview health `sync:true`，带 key POST 200 |
| 文档把 `audio_assets.py` 说成生成 `web/audio` | CONTRACTS / RESOURCE_POLICY 区分：`open_audio_assets.py`→`web/audio`；`audio_assets.py`→本机备选 | 文档已改 |
| 仓库根缺少统一的数据许可说明 | 新增 `DATA_LICENSES.md`（OpenJLPT / krdict / KANJIC / Unihan / Kokoro / 外部链接） | 文件存在并被 README 引用 |
| `data/audio/` 里 23 MB macOS `say` 产物，未发布且与新流程重复 | 删除；`.gitignore` 已排除该目录 | 目录不存在 |

## 3. 内容与课程（实测）

| 项 | 数值 |
|---|---|
| 词汇 | 2700（必学 2154 + 拓展 546；常规日必学 ≤16，听力日 ≤11） |
| 语法 | 276，`common_errors` 与 `ko_equiv` 均非空 |
| 汉字 | 620，`ko_hanja` 全覆盖 |
| 句子 | 1500（每天 10，前 3 必做） |
| 听力 | 45 篇，Kokoro 合成，实测 63.300–71.575 秒，平均 67.08 秒，共 24.9 MB |
| 测评 | 39 题：21 个周测日 ×1、3 个阶段日 ×3、3 个自测日 ×3；Day 1 另有 3 道诊断 |
| 词表缺口 | 无例句 0；无韩语提示 0（2050 词典匹配 + 650 AI 释义） |

## 4. 自动校验

```
python3 scripts/nh80.py validate
  → ok True, error 0, days 150, totals {v:2700,g:276,k:620}, listening 45

python3 scripts/release_guard.py
  → {"ok": true, "files": 357, "asset_bytes": 31887319, "public_audio": 45,
     "cloud_bindings": ["existing D1"], "paid_features": false}

python3 -m unittest discover -s tests -p "test*.py"
  → Ran 27 tests ... OK

node tests/test_worker_access.mjs
  → PASS: unauthenticated writes denied before database access
  → PASS: authenticated check probes D1 without writing
```

## 5. 线上验收

| 项 | 结果 |
|---|---|
| Production | `https://nihongo80.cmjfire.workers.dev`，Version `18d87f04-8414-43e6-a28d-3fa8e5fbd696` |
| Preview | `https://nihongo80-preview.cmjfire.workers.dev`，Version `4c022eca-0a84-4244-9f3c-f707e4f46c21` |
| `/api/health` | `{"status":"ok","features":{"db":true,"sync":true}}`（两环境） |
| 页面 | `/`、`/day-001/007/045/047/150.html`、`/library.html`、`/resources.html` 均 200 |
| 音频 | `/audio/M0096.m4a` 200，`content-type: audio/mp4`，561198 B；M0140 616046 B |
| 答案表 | `/data/answer-key.json` → 404 |
| 字节一致 | `day-047.html`、`assets/app.js`、`assets/app.css`、`data/day-047.json` 本地与线上 SHA-256 全部 MATCH |
| 鉴权 | 无 key POST → 401；有 key check → 200；无 key GET → 401 |
| 旧入口 | `/n3-mock.html` 改为官方资源引导页 |

浏览器实测（Chrome headless，375×812 与 1280×900，Day 1/7/47/150）：

- 听力日 6 块、顺序为 ①复习 ②新词 ③语法 ④听力 ⑤句子 ⑥练习；
- 音频可播放，时长 65 s / 72 s；
- 听力 3 题、周测阅读题带原文段落；
- 遮盖四态循环（日语 → 双向 → 关 → 中文）正常；
- 判分即时、错题标绿正确项；
- 无横向滚动、无 console/pageerror、页面源码无 `"answer":` 明文；
- `/library.html` 45 个音频播放器；`/` 152 个链接、按周折叠。

## 6. 免费与法律边界

- Cloudflare 账户为 **Workers Free**（Codex 于当日 Dashboard 只读核验；本次未改套餐）。
- 无 R2 / KV / Queues / Durable Objects / Workers AI / 定时任务；`observability=false`。
- 除首页与 `/api/*` 外的静态页面、音频直接由静态资源返回，不计 Worker 请求。
- Worker 写入需个人口令；应用内另有 1000 条/UTC 日、5000 条总预算，超限 429 并保留本机导出。
- 许可与署名：`DATA_LICENSES.md`、`web/resources.html`、`web/audio/NOTICE.txt`。
  对外只链接官方资源，不复制、不转存第三方教材/真题/真人录音。

## 7. 仍未做到（不粉饰）

1. **没有人工审校**：全部内容 `review_status=ai_draft`；AI 复审不等于日语/韩语教师逐条核对。
2. **音频不是真人**：Kokoro 合成，未逐条试听；发音、语调、自然度可能有问题，也不代表 N3 难度。
3. **不是官方模考**：39 道周测/阶段题是轻量练习，不换算 JLPT 分数；官方样题只在资源页外链。
4. **完成 ≠ 掌握**：`finish-day` 只校验当天题目 + 输出批改，不据此推断长期掌握。
5. **preview 与 production 共用 D1**：未做独立预览库；`check` 探针不写事件，但真实 preview 使用会写同一张表。
6. **音频不支持 Range**：静态资源对 `Range: bytes=0-1023` 返回 200 全量；文件约 0.5–0.6 MB，播放与拖动在实测浏览器可用，弱网首播会稍慢。
