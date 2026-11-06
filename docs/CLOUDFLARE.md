# Nihongo 80 · Cloudflare 每日学习页面与部署

> **已于 2026-11-06 实际部署上线**（用户明确授权；复用本机已有的 wrangler OAuth 登录态）。
>
> | 环境 | 线上地址 | Worker |
> |---|---|---|
> | **Production** | **https://nihongo80.cmjfire.workers.dev** | `nihongo80` |
> | Preview | https://nihongo80-preview.cmjfire.workers.dev | `nihongo80-preview` |
>
> 使用本机已有的 Cloudflare OAuth 登录态（账号信息不写入仓库）；一次上传 167 个静态资源。`wrangler.jsonc` 与脚本仍**不含**任何
> 账号 ID / API Token / 自定义域名 / 密钥。没有绑定自定义域名，也没有改动 zoomlab 的任何生产资源。
> 部署记录、线上逐路径验证与浏览器实测见第 4 节、`docs/VALIDATION.md` 第 6 节。

## 1. 复用 zoomlab-web 的模式 / 简化了什么

参考对象：`zoomlab-web/worker/wrangler.jsonc`、`zoomlab-web/scripts/deploy.sh`、`zoomlab-web/docs/DEPLOYMENT.md`。

| 维度 | zoomlab-web（参考） | Nihongo 80（本项目） | 结论 |
|---|---|---|---|
| 发布方式 | Worker + `assets.directory` 一起由 `wrangler deploy` 发布 | 相同 | **复用** |
| 触发方式 | 本机脚本优先，push 不自动部署 | 相同（仅本机 `scripts/deploy_cloudflare.sh`） | **复用** |
| 发布顺序 | 先 `preview` 后 `production` | 相同 | **复用** |
| 发布后校验 | `curl /api/health` 需 `{"status":"ok"}` | 相同 | **复用** |
| 前端构建 | React + Vite（`npm run build` → `frontend/dist`） | 纯 Python 标准库 `build_site.py` → `web/` | **简化** |
| 框架 / 运行时依赖 | React、Vite、npm 依赖 | 纯 HTML / CSS / 原生 JS，**零 CDN、零 npm 运行时依赖** | **简化** |
| 数据层 | D1、KV、Workers AI、Workflows | 全部不要；Worker 只有 `/api/health` | **简化** |
| `run_worker_first` | `/api/*`、`/health`、`/talk/*` 等多条 | 仅 `/api/*` 与 `/health` | **简化** |
| 404 | `single-page-application` | `404-page` + 构建生成 `web/404.html` | **调整** |
| `env.preview` | 独立 Worker + 独立 D1 + 独立 KV + 独立 Workflow | 独立 Worker，**无 cron / 无自定义域名 / 无数据库 / 无密钥** | **简化** |
| 账号信息 | 配置里含 account_id / database_id / 域名 / vars | **配置里不含任何真实账号 ID、database_id、域名、密钥** | **简化** |

一句话：**复用「Worker + 静态资源一起发、本机脚本优先、先 preview 后 production、部署后 health check」的发布骨架；把前端和数据层大幅砍成零依赖的静态站 + 健康检查 Worker。**

## 2. 架构与文件

```
nihongo-80/
├── scripts/build_site.py          # 唯一构建器：curriculum + seeds -> web/（纯标准库）
├── scripts/deploy_cloudflare.sh   # 本机部署脚本 preview|production（默认不部署）
├── deploy/
│   ├── wrangler.jsonc             # name=nihongo80；assets.directory=../web；binding=ASSETS
│   ├── package.json              # 仅 wrangler devDependency + dev/deploy scripts
│   └── worker/src/index.ts       # /api/health -> {"status":"ok"}，其余交 ASSETS
├── docs/CLOUDFLARE.md            # 本文件
└── web/                          # 构建产物（由 build_site.py 生成，不是手写源码）
    ├── index.html / 404.html
    ├── day-001.html ... day-080.html
    ├── data/day-001.json ... day-080.json   # CONTRACTS 第 9 节格式
    ├── assets/app.css / app.js
    ├── manifest.webmanifest      # PWA：可加到手机主屏
    ├── sw.js                     # 纯原生 Service Worker：版本化离线缓存
    └── icon.svg                  # 矢量主屏图标（零二进制依赖）
```

请求流：`/api/health` → Worker 返回 `{"status":"ok"}`；其余路径 → ASSETS 静态资源；未命中 → `web/404.html`（`not_found_handling: "404-page"`）。`run_worker_first` 只放行 `/api/*` 与 `/health`，静态资源不经过 Worker，零 CPU 开销。

**关键：网页不是状态真源。** 状态只在本地 `data/state.db`（SQLite）。网页只做展示、练习、即时判分、生成回传码；`web/data/*.json` 只含「题目 + 答案（用于本地判分）」，不含任何掌握状态、FSRS 卡片或历史记录。

## 3. 本地预览（无需 Cloudflare）

```bash
# 1) 生成站点（需要 curriculum/curriculum.json 与 knowledge/seeds/*.jsonl 已由其它任务生成）
python3 scripts/build_site.py --root /Users/mj/Documents/learn/jp/nihongo-80
# 只重建某一天（快速迭代）：
python3 scripts/build_site.py --root /Users/mj/Documents/learn/jp/nihongo-80 --day 1

# 2) 起本地静态服务
python3 -m http.server 8080 -d web
# 浏览器打开 http://localhost:8080/  与  http://localhost:8080/day-001.html
```

`build_site.py` 缺 `curriculum.json` 或任一 seeds 文件时会**明确报错退出**，不会静默生成空页；引用的 id 在种子库缺失时同样失败（CONTRACTS 第 8 节强校验）。

离线可用：每日数据以 `<script type="application/json">` **内嵌**进 HTML，不 `fetch` 任何接口；可视化是原生 SVG 字符串，无图表库、无 CDN。

双端本地自测：`localhost` 属安全上下文，SW 会正常注册。用浏览器 DevTools 设备模拟（如 `390px` 窄屏 / `1440px` 宽屏）可分别验证「一屏一题 + 底部操作栏」与「侧栏 + 一屏多题」。若想用真手机访问，把手机与电脑连同一 LAN、用 `http://<电脑局域网 IP>:8080/` 打开 —— 注意**非 localhost 的 http 不是安全上下文**，此时 SW 不会注册（页面其余功能照常，浏览器会自动跳过注册，见 9.8 节）；完整离线 / 主屏能力可直接用已上线的 `https://nihongo80.cmjfire.workers.dev` 验证（https 安全上下文，SW 会注册）。

## 4. 已上线记录与重新部署

### 4.1 实际执行过什么（2026-11-06）

> 以下是当时的真实执行记录；现在重新部署**不必手动 npm install**，脚本会按需自动安装（见 4.4）。

```bash
cd /Users/mj/Documents/learn/jp/nihongo-80/deploy
npm install --no-audit --no-fund          # 装 wrangler 4.158.0
cd ..
CI=1 bash scripts/deploy_cloudflare.sh preview      # nihongo80-preview，health check 通过
CI=1 bash scripts/deploy_cloudflare.sh production   # nihongo80，health check 通过
```

使用本机 `~/Library/Preferences/.wrangler/config/default.toml` 里已有的 OAuth 登录态
（`wrangler whoami` 确认已登录且具备 workers_scripts / pages 写权限；账号信息不写入仓库），
**没有新建 Token、没有写入任何凭证到项目文件**。`CI=1` 让 wrangler 在非交互环境下不询问确认。

Production 版本 ID 以每次 `wrangler deploy` 的实际输出为准（每次部署都会变化，不固化在仓库里）。
v2 课程重构后已重新发布 preview 与 production，线上 `day-050.html` 等页面为新版内容。

### 4.2 上线时真实修掉的一个问题

首次部署后 `/day-NNN.html` 返回 **307 → `/day-NNN`**：这是 Cloudflare Workers Assets 默认
`html_handling` 对 `.html` 的规范化。浏览器会跟随，但 `sw.js` 预缓存列表用的是 `.html` 路径，
重定向会影响 PWA 离线缓存，且本地与线上路径不一致。

修法（两处，都已在 preview 验证后才推 production）：

- `deploy/wrangler.jsonc`：两组 `assets` 均加 `"html_handling": "none"`；
  `run_worker_first` 加 `"/"`。
- `deploy/worker/src/index.ts`：`/` 显式转发到 `/index.html`（`none` 模式下 assets 不再自动映射首页），
  并让 `/health` 与 `/api/health` 都返回 `{"status":"ok"}`。

### 4.3 线上逐路径核对（全部实测）

| 路径 | 结果 |
|---|---|
| `/` | 200，index.html（80 天热力图 + 目录） |
| `/day-001.html` / `/day-040.html` / `/day-080.html` | 200，无重定向 |
| `/data/day-001.json` / `/data/day-080.json` | 200，合法 JSON |
| `/manifest.webmanifest` / `/sw.js` / `/icon.svg` | 200 |
| `/assets/app.css` / `/assets/app.js` | 200 |
| `/api/health` / `/health` | 200 `{"status":"ok"}` |
| `/no-such-page` | 404（走 404.html） |

预览环境 `nihongo80-preview.cmjfire.workers.dev` 同样通过 `/api/health`。

### 4.4 重新部署 / 本地调试

内容或课程更新后，直接跑（先 preview 再 production）：

```bash
cd /Users/mj/Documents/learn/jp/nihongo-80
CI=1 bash scripts/deploy_cloudflare.sh preview
CI=1 bash scripts/deploy_cloudflare.sh production
```

`deploy/node_modules` 不随项目长期保留（约 223M），脚本检测到缺失会自动 `npm install`（约 1 分钟）；
项目体积因此维持在约 6.7M。脚本还会先跑 `build_site.py` 校验重建，缺课程或种子会直接失败，
不会发布空页；部署后自动做 `/api/health` 检查。若无法从 wrangler 输出推断地址，可显式设置：

```bash
NH80_BASE_URL=https://nihongo80.cmjfire.workers.dev scripts/deploy_cloudflare.sh production
```

Wrangler 本地调试（可选）：
```bash
cd deploy && npm run dev   # wrangler dev --config wrangler.jsonc
```

回滚（Cloudflare 侧）：`cd deploy && npx wrangler rollback --config wrangler.jsonc`。

## 5. 免费额度与限制（以 Cloudflare 官方最新文档为准）

- **Workers Static Assets**：静态资源随 Worker 一起发布，通常不计流量/带宽费用；本项目 80 个 HTML + 少量 JSON/CSS/JS，体积极小。
- **Workers Free**：每日请求数、单次 CPU 时间有免费上限（常见约 10 万次请求/天、每次约 10ms CPU；**具体数值请查 Cloudflare 官方定价页，本仓库不写死**）。本站几乎不消耗 CPU：只有 `/api/*` 与 `/health` 经过 Worker，且 `/api/health` 只是返回一个常量 JSON；静态资源由 ASSETS 直接服务。
- 未使用 D1 / KV / Workers AI / 外部 API，因此**没有数据库额度、按次调用费或 TTS 费用**。语音全部在浏览器本地合成。
- 限制：自定义域名、更高额度、更多环境属于付费/需配置范畴，**本项目刻意不使用**；`env.preview` 与 production 共用同一份构建产物、不同 Worker 名。

## 6. 语音 / TTS 的真实限制与免费替代

实现：浏览器内置 `speechSynthesis`，`SpeechSynthesisUtterance.lang = "ja-JP"`，**零 API、零费用、零网络依赖**。页面提供「试听 / 解锁语音」「停止朗读」「语速 0.7 / 0.9 / 1.0」「静音学习」控件（详见第 9 节）。

真实限制（务必知悉）：
- **手机端首次必须由用户手势触发**：iOS Safari / Android Chrome 的 `speechSynthesis` 首次 `speak()` 必须发生在用户手势（点击）回调里，否则语音队列被静默挂起。因此页面**不自动播放**，所有朗读都绑在 click 上，并提供显式「试听 / 解锁语音」按钮（内部 `primeTTS()` 先以空串 `speak()` 解锁一次）。`voiceschanged` 时序在各平台不稳定，检测逻辑会在语音列表刷新后重试。
- **语音可用性因系统/浏览器而异**：macOS / iOS 通常自带日语语音；Windows 常无；Android 取决于是否安装日语 TTS 包；部分 Chromium 的语音可能走在线服务（此时发音依赖网络，且存在隐私/离线不确定性）。
- **能力检测与降级**：页面加载时检测 `speechSynthesis` 是否存在、以及 `getVoices()` 里是否有 `lang` 以 `ja` 开头的语音（`voiceschanged` 会刷新）。若不支持或没有日语语音：
  - 显示醒目的兼容提示；
  - **显示假名读音**（词汇 `kana`、汉字音读/训读、素材/题目 `audio_text` 文本），词汇卡正面直接给出假名；
  - 允许「手动播放」（可能以其它语言发音或无声，仅作参考）、「静音学习 / 仅看文本」；
  - 不自动播放（浏览器自动播放策略要求用户手势触发）。
- 发音质量、语调、长音/促音/音读训读切换不保证准确，**不能替代真人/专业音频**；因此降级路线是「看文本 + 假名 + 跟读」。

免费替代（均不引入付费 TTS）：
- 系统自带 TTS：macOS `say -v Kyoko "<日语>"`、`espeak-ng -v ja`；
- 浏览器朗读插件 / 系统「朗读所选内容」；
- 跟读假名与文本，配合回传码里的 `listen` 题型做听写自测。
- **明确不引入**：任何付费 TTS、第三方语音 API、外链音频 CDN。

## 7. 兼容性风险汇总

| 项 | 风险 | 处理 |
|---|---|---|
| `speechSynthesis` / ja-JP 语音 | 部分环境缺失或发音不准 | 能力检测 + 假名读音降级 + 静音学习（见第 6 节） |
| 日文字体 | 各系统字形不同 | 优先系统 Hiragino / Noto Sans JP，逐级回退到 PingFang / 无衬线 |
| 内嵌 JSON | 数据里出现 `</script>` 会截断 | 构建时把 `< > &` 转成 `\uXXXX`，`JSON.parse` 还原 |
| SVG | 无外部图表库 | 用 innerHTML 注入 `<svg>`，HTML5 自动进入 SVG 命名空间，无需 `xmlns` 外链 |
| `TextEncoder` / `btoa` / `navigator.clipboard` | 极老浏览器 / 非安全上下文缺失 | 现代主流浏览器均支持；剪贴板 `navigator.clipboard` → `execCommand('copy')` → 全选文本框三级回退（见第 9 节） |
| `navigator.share` | 桌面浏览器 / 部分 iOS 不支持 | 不支持时明确提示改用「复制回传码」或「下载 .txt」，不静默失败 |
| 下载 `.txt` | iOS Safari 可能改为新标签打开而非下载 | 与复制 / 分享 / 全选并列，任一可用即可完成闭环 |
| Service Worker / PWA | 仅 https 或 localhost 生效；iOS 主屏行为有差异 | `file://` 自动跳过注册；纯原生 SW + 版本化缓存，不改变页面原有功能（见第 9 节） |
| SVG 主屏图标 | 部分平台（尤其 iOS）对 SVG 主屏图标支持有限 | 当前用 SVG 以保持零二进制依赖；如需更稳妥可后续补一份 PNG（不引入 CDN） |
| `localStorage` | 隐私模式可能不可写 | `try/catch` 包裹，失败仅影响「当日恢复」，不影响答题与回传码 |
| Wrangler 配置 | `not_found_handling: "404-page"`、`run_worker_first` 需较新 Wrangler | `package.json` 固定 `wrangler ^4.0.0`；低版本需升级 |
| 页面离线 | 依赖本地静态服务或已发布站点 | 数据内嵌、零外链，断网仍可展示与练习；加主屏后由 SW 缓存当天课程 |

## 8. 回传码闭环（网页 → 本地 SQLite）

网页**不写任何状态、不向任何服务器发送学习数据**（无 `fetch` / XHR / `sendBeacon` / 表单提交）。闭环靠用户手动带走回传码：

1. 用户在页面分步作答 → 提交后才揭示答案与解析 → 即时本地判分；`free_production` / `dialogue` 按 `rubric` 准则自评。手机端一屏一题、PC 端一屏多题（见第 9 节）。
2. 结束生成 `NH80R1.<base64url(json)>`（CONTRACTS 第 10 节）。「回传码」面板给出四种带走方式，页面明确提示**「复制后到 WorkBuddy 会话粘贴导入，或先存备忘录稍后导入」**：
   - 「复制回传码」：`navigator.clipboard.writeText` → `document.execCommand('copy')` 降级 → 全选文本框手动复制兜底；
   - 「系统分享」：`navigator.share` 调起手机系统分享（不支持时提示改用复制 / 下载）；
   - 「下载 .txt」：`Blob` + `<a download>` 存成本地文本备份；
   - 「全选文本」：选中文本框手动长按复制。
   payload：
   ```json
   {"v":1,"day":1,"session":"session-20261106-001","ts":"2026-11-06T15:00:00+08:00",
    "results":[{"qid":"Q0001","answer":"です","correct":true,"hinted":false,"seconds":12,"error_type":null}],
    "minutes":18,"source":"web"}
   ```
   其中 `error_type` 取自 CONTRACTS 第 12 节枚举；`session` 形如 `session-YYYYMMDD-NNN`。
3. 用户把码粘贴回 WorkBuddy 会话，由本地脚本导入：
   ```bash
   python3 scripts/nh80.py import-web-result '<回传码>'
   ```
   该脚本负责：结构校验、未知 qid 拒绝、按 `session+qid` 幂等去重、写入 `attempts` 并触发 FSRS 排期（由其它任务实现，本子任务不含）。
4. `localStorage`（键 `nh80:day:N`）只保存当日结果，用于刷新 / 断网后的「当日恢复」，页面上有「清除缓存」；**它只是本地便利缓存，不是状态真源**。是否「完成」由 SQLite 的 `attempts` 记录决定，而非页面是否打开（CONTRACTS 第 14 节第 3 条）。回传码是**纯文本、自包含、不依赖网络**，因此可在手机学习、回到 PC（或任意设备）再粘贴导入（见第 9 节「异步路径」）。

## 9. PC / 手机双端适配（移动优先）

> 用户可能在手机上学习，也可能在 PC 上学习。本节说明**真实做了什么**、**浏览器限制到哪**、**离线边界在哪**。
> 所有适配都在 `scripts/build_site.py` 生成的外壳 HTML、`web/assets/app.css`、`web/assets/app.js` 里，零框架、零 CDN、零 npm 运行时依赖、零付费服务。**网页依旧不是状态真源**（第 0/8 节），双端适配只改「展示与交互」，不改真源规则。

### 9.1 布局：真适配，不是一句 media query

CSS 移动优先，断点 `640px`（平板/大屏手机）与 `900px`（PC）：

| 维度 | 手机（< 900px） | PC（≥ 900px） |
|---|---|---|
| 栅格 | 单列，卡片全宽，无横向滚动 | 侧栏 `248px` + 主区；卡片 / 可视化 2–3 列 |
| 导航 | 粘性顶栏 + 「目录」按钮展开侧栏（overlay） | 常驻粘性侧栏（前一天 / 目录 / 后一天 / 跳到练习） |
| 进度 | 粘性**顶部进度条** + appbar 副标题显示「第 X / N 题」 | 侧栏「学习进度」+ 顶部工具条「已答 X / N 题」 |
| 练习操作 | **底部固定操作栏**：上一题 / 下一题 / 提交 / 完成 / 复制码 | 底部操作栏隐藏；题卡内自带提交 + 顶部「完成并生成回传码」 |
| 练习呈现 | **一屏一题**（step），其余题卡隐藏 | **一屏多题**（grid，2 列） |
| 触控 / 安全区 | 所有可点元素 ≥ `44px`（`--tap:44px`）；输入 `font-size:16px` 防 iOS 自动缩放；`env(safe-area-inset-*)` 四边处理刘海 / 底部横条 | 同套变量，主要受益于安全区与暗色对比度 |

HTML `<head>` 含 `viewport-fit=cover`、light/dark 双 `theme-color`、`color-scheme`、`apple-mobile-web-app-capable`、`mobile-web-app-capable`、`apple-mobile-web-app-title`、`format-detection`，以及 `manifest` / `icon` 引用。

### 9.2 日语阅读与可视化（手机专项）

- 日文正文 `.ja-text`：`font-size:18px`、`line-height:2.05`、`word-break:normal`、`overflow-wrap:anywhere`、`line-break:strict` —— 字号行高足够大、禁用生硬断词、长例句可自然换行。
- 词汇卡在手机端 `data-solo="1"`：**一次只展开一张**（先自测再揭示，点开一张会收起其它张）；语法 / 汉字卡同理折叠在 `<details>` 分区里。
- 长文本 `collapsibleText()` 超过 90 字默认折叠，给「展开全文 / 收起」，除练习外分区默认折叠 —— 避免手机一次铺开几十屏。
- 可视化全部原生 SVG，用 `viewBox` 自适应（非固定像素宽），CSS `.svg-mount svg{width:100%;height:auto}`；80 天热力图窄屏放进 `.viz-scroll` 横向滚动容器（PC 保持紧凑）。含当日结构、80 天热力图、题型分布三种图，数据来自内嵌 JSON，无图表库。

### 9.3 音频：手势解锁 + 降级

- **不自动播放**。所有 `speak()` 都发生在用户点击回调内；提供显式「试听 / 解锁语音」按钮，`primeTTS()` 在手势里用空串 `SpeechSynthesisUtterance` 先解锁一次语音队列（iOS / Android 必需）。
- 控件：试听 / 解锁、停止朗读、语速 `0.7 / 0.9 / 1.0`、静音学习。
- `getVoices()` + `voiceschanged` 检测 `ja-JP` 语音；**无日语语音 / 不支持时明确提示**并显示假名读音（`kana`、音读训读、`audio_text`），可「静音学习 / 跟读」，不静默失败。
- 全程浏览器内置 `speechSynthesis`，零 API、零网络、零费用；不引入付费 TTS（第 6 节）。

### 9.4 练习交互：手机一屏一题 / PC 一屏多题

`app.js` 启动时 `detectLayout()` 依 `matchMedia('(min-width: 900px)')` 设定 `LAYOUT.mode = 'grid' | 'step'`，同一套题目渲染两条路径：

- 手机 `step`：`setActive(i)` 只显示当前题，底部操作栏「上一题 / 下一题 / 提交 / 完成 / 复制码」+ 顶部进度条；提交后才揭示答案、解析、评分准则。
- PC `grid`：题卡 2 列铺开，每题独立提交 / 判分 / 解析。
- 两条路径都：先作答再揭示、本地即时判分；`free_production` / `dialogue` 给 `rubric` 自评（达成 / 未达成）；答错可选 `error_type`（§12 枚举）；结果写 `localStorage` 仅供当日恢复。

### 9.5 回传码手机关键路径

生成 `NH80R1.<base64url(json)>` 后（第 8 节），手机端提供四条带走路径，并按可用性逐级降级：

1. **一键复制**：`navigator.clipboard.writeText` →（失败 / 不支持）`document.execCommand('copy')` →（再失败）`codeArea.select()` 全选文本框 + 明确提示手动长按复制。
2. **系统分享**：`navigator.share`（手机安全上下文 + 用户手势）；不支持时提示改用复制 / 下载。
3. **下载 .txt**：`Blob` + `URL.createObjectURL` + `<a download>` 存本地备份。
4. **全选文本**：文本框可整体选中复制。

页面固定提示「复制后到 WorkBuddy 会话粘贴导入，或先存备忘录稍后导入」。**未引入二维码 / 第三方库**（避免 CDN 依赖）。

### 9.6 手机端完整学习闭环

1. 手机浏览器打开 `https://<你的 workers.dev>/day-001.html`（或加到主屏后离线打开）。
2. 首次语音：点「试听 / 解锁语音」完成用户手势解锁 → 之后词汇 / 素材 / 题目可点「朗读」反复听；无日语语音则看假名读音、静音学习。
3. 分步练习：底部操作栏一屏一题作答 → 「提交」揭示答案与解析即时判分 → 「下一题」推进，顶部进度条显示进度；开放题按 rubric 自评。
4. 点「完成」生成回传码 → 用「复制回传码 / 系统分享 / 下载 .txt」把码带走。
5. 回到 WorkBuddy 会话粘贴该码（或先存备忘录 / 发给自己，稍后导入）。
6. 由本地 `import-web-result` 校验、去重、写入 SQLite `attempts` 并触发 FSRS 排期 —— **成绩在此时才算落盘**；网页只产出码，不代表已完成（CONTRACTS §14 第 3 条）。

### 9.7 「手机学习、PC 导入」异步路径

回传码是**纯文本、自包含、不依赖网络、不依赖设备**的载体，因此学习设备与导入设备可以不同、也可以不同时：

```
手机（在线/离线学习）
   └─ 生成 NH80R1 码 → 复制 / 系统分享到微信、备忘录、邮件 / 下载 .txt
        └─（任意时间）在 PC 上打开 WorkBuddy 会话粘贴
             └─ python3 scripts/nh80.py import-web-result '<码>' → 写 data/state.db
```

- 真源始终是**跑 WorkBuddy 那台机器**的 `data/state.db`；手机网页、`localStorage`、回传码、聊天上下文都不是状态真源。
- 这正对应 CONTRACTS §14 第 5 条：**不声称平台自动传递每日状态；跨会话 / 跨设备状态只能来自文件**（这里就是回传码这段文本）。
- 因此「离线仅展示，成绩靠回传码」—— 断网也能学，成绩不会丢，只要把码带回有 `state.db` 的会话即可。

### 9.8 离线 / 主屏（PWA）与边界

`build_site.py` 额外生成 `web/manifest.webmanifest`、`web/icon.svg`、`web/sw.js`，纯原生、版本化：

- `manifest`：`display:standalone` / `start_url` / `scope` / 矢量 `icon.svg`，手机「添加到主屏幕」后可全屏打开。
- `sw.js`：缓存名 `nh80-<build_id>`，`build_id` 取 curriculum + seeds 的 SHA-256 前 12 位 —— **真源数据一变、缓存版本即失效**；`activate` 清理旧版本缓存。
- 预缓存清单只含**同源静态文件**（`index/404`、全部 `day-NNN.html`、`data/day-NNN.json` 只读课程数据、`assets/*`、`manifest`、`icon`），**不含任何学习状态**（无成绩 / attempts / FSRS）；手机加主屏后能离线打开当天课程。之所以在 `install` 一次性预缓存**全部**每日页，正是为了让 `fetch` 阶段永远命中缓存、无需网络回源 —— 这与「不发网络请求」是自洽的；80 天全量约 160+ 个小静态文件，属一次性、同源、可失效（版本变即重取），首次安装建议在联网 / Wi-Fi 下完成。
  线上实测（2026-11-06，CDP 390px）：约 15 秒后 `active: activated`、`controller: true`、缓存 166 个资源；
  install 期间页面可正常使用，不影响学习。
- `/api/*` 与 `/health` 交回 Worker（健康检查需在线），SW 不介入、不回传任何数据。

**「不发网络请求」的准确边界（务必看清）：**

| 阶段 | 是否发起网络请求 | 说明 |
|---|---|---|
| 页面 `app.js` | **否** | 无 `fetch` / XHR / `sendBeacon` / 表单；学习数据永不外发，数据全部内嵌 |
| SW `fetch` 阶段 | **否** | 只读 `caches.match`；未命中返回离线 503，不调用 `fetch()` |
| SW `install` 阶段 | **是，仅同源静态文件一次** | `cache.add(new Request(相对路径))` 预取这 10 个静态文件，是「离线可用」的必要前提；**请求对象是本站静态 HTML/CSS/JS/JSON，绝非学习数据、成绩或状态** |

- 风险与降级：SW 只在 **https 或 localhost（安全上下文）** 生效，`file://` 自动跳过注册（HTML 内联脚本 `'serviceWorker' in navigator` 检测）；SW 更新通常下次访问生效（已用 `skipWaiting()` + `clients.claim()` 尽量缩短）；某天页面若未预缓存（新构建后从未在线打开），离线访问返回「离线：该资源未缓存」提示 —— **联网打开一次即可缓存，且不影响复制回传码**。SW 不破坏原有在线功能：注册失败被 `.catch` 吞掉，页面照常工作。

### 9.9 iOS / Android 已知限制

| 平台 | 限制 | 本项目的处理 |
|---|---|---|
| iOS Safari | `speechSynthesis` 首次必须用户手势解锁；`voiceschanged` 时序不稳；后台 / 锁屏暂停朗读 | 显式「试听 / 解锁语音」、所有朗读绑 click、假名降级、静音学习 |
| iOS Safari | `navigator.clipboard.writeText` 在部分版本 / 非安全上下文受限；`navigator.share` 需用户手势 | `execCommand('copy')` → 全选文本框三级回退；分享不支持则提示复制 / 下载 |
| iOS Safari | 「下载 .txt」可能改为新标签打开；SVG 主屏图标支持有限 | 下载与复制 / 分享 / 全选并列，任一可用即可；图标用 SVG 保持零二进制依赖，必要时可后补 PNG（不引 CDN） |
| iOS 主屏 PWA | `apple-mobile-web-app-capable` 与 `display:standalone` 在部分版本行为不完全一致；standalone 下 `speechSynthesis` 表现有差异 | meta 双写；SW 注册失败静默降级，页面功能不受影响 |
| Android Chrome | 依赖系统日语 TTS 引擎；`getVoices()` 初期可能为空、无 ja 语音时无声或走在线合成 | `voiceschanged` 重检 + 假名读音 + 明确提示；不依赖外部音频服务 |
| 通用 | 自动播放策略禁止无手势播放；暗色 / 对比度差异 | 不自动播放；`prefers-color-scheme: dark` 覆盖 CSS 变量保证对比度 |

### 9.10 哪些是真做的、哪些受浏览器限制

**真做了（构建产物里可验证，已通过自测）：**

- 移动优先 CSS、`640 / 900` 双断点、手机单列 / PC 侧栏多列、`44px` 触控、`16px` 输入、四边安全区、**默认浅色** + 可选 `prefers-color-scheme: dark`（深色变量保证对比度）、粘性顶栏 + 底部操作栏。
- 手机 `step` 一屏一题 / PC `grid` 一屏多题、进度指示、先答后揭、rubric 自评、`error_type` 选择。
- 日文大字号高行高不断词、词汇卡一次一张、长文本折叠、SVG `viewBox` + 窄屏横向滚动。
- TTS 手势解锁、播放 / 停止 / 语速 / 静音、ja-JP 检测与假名降级。
- 回传码复制三级降级 / 系统分享 / 下载 .txt / 全选，以及「复制到 WorkBuddy 会话或备忘录」提示。
- 原生 `manifest` + `icon.svg` + 版本化 `sw.js` 离线缓存；HTML 内嵌 JSON、零外链、无网络 API。
- `NH80R1` 回传码结构、session、ts、§12 错误类型；双端 `390px / 1440px` DOM 桩 `init → 答题 → 生成回传码` 全通过，回传码解码符合 §10。

**受浏览器 / 平台限制（无法由本项目代码消除，已给降级）：**

- 日语语音的有无、发音质量、在线合成依赖 —— 由系统 TTS 决定，只能假名 + 跟读降级（6 / 9.3 / 9.9 节）。
- 剪贴板 / 系统分享 / 下载在 iOS 等环境的可用性差异 —— 三级复制回退 + 多路径并列（9.5 / 9.9 节）。
- SW 仅在安全上下文生效、iOS 主屏 PWA 行为差异、SVG 图标支持 —— `file://` 跳过、注册失败静默降级（9.8 / 9.9 节）。
- **离线只做「展示 + 练习 + 本地判分 + 生成回传码」，不写任何状态**；成绩必须由用户把回传码带回 WorkBuddy 会话、经 `import-web-result` 写入 `data/state.db` 才成立 —— 这是 CONTRACTS 真源规则的硬约束，不是浏览器限制，而是刻意设计（8 / 9.7 节）。

## v3 页面改造后的重新部署（2026-11-06）

用户反馈原页面「太抽象看不懂」后，按 `docs/REDESIGN_PLAN.md` 把每日页从系统报表改回
「一课教材」：首屏 3 句可听的日文 + 字段齐全的常显词卡，随后语法 / 汉字 / 例句会话 /
练习 / 今日复习，系统术语与图表退到页尾折叠区。单词补罗马字、词性、例句、中文易错与
韩语对照；复习改成「今天具体复习这几个词 + 为什么 + 下次何时 + 三档自评」，
三档经回传码由 `learning.apply_review_rating` 写入 FSRS（只排期、不判掌握）。

| 环境 | Worker | 版本 ID | 地址 |
|---|---|---|---|
| Production | `nihongo80` | `a0bf1d09-90f7-4cc4-b1c9-627b4f93ac27` | https://nihongo80.cmjfire.workers.dev |
| Preview | `nihongo80-preview` | `d5dfc6ef-c2c2-4a0a-a7cd-6a009a963874` | https://nihongo80-preview.cmjfire.workers.dev |

线上复验：`/`、`/day-001.html`、`/day-050.html`、`/day-080.html`、`/data/day-001.json`、
`/assets/app.js`、`/assets/app.css`、`/sw.js`、`/manifest.webmanifest`、`/api/health` 全部 200；
真实浏览器 `--dump-dom` 命中「今天要会的 3 句话」「きょうはいいてんきです。」「韩语对照」
「必须验证」「今日复习」「记住了」「看答案」「中文易错」「今日难点」「给老师」。
CDP 真实 390 CSS 视口：`innerWidth=390 / scrollWidth=390`，零横向溢出，词卡单列。

原有工程约束不变：零 CDN / 零 fetch、`file://` 可开、PWA 离线、双端、TTS 手势解锁与降级、
`NH80R1` 回传码；静态页仍不是状态真源，复习清单标为「计划」，真实到期以本地 `state.db` 为准。
