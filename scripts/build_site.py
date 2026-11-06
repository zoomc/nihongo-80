# -*- coding: utf-8 -*-
"""Nihongo 80 每日学习页构建器（纯 Python 标准库）。

真源：curriculum/curriculum.json + knowledge/seeds/*.jsonl
产物：web/data/day-NNN.json、web/day-NNN.html、web/index.html、web/404.html、
      web/assets/app.css、web/assets/app.js、
      web/manifest.webmanifest、web/sw.js、web/icon.svg

设计约束（见 CONTRACTS.md 第 0/9/10/14 节）：
- 网页不是状态真源；状态只在本地 SQLite。页面只做展示 / 练习 / 即时判分 / 生成回传码。
- 每日数据内嵌进 HTML（<script type="application/json">），页面不向任何服务器发送学习数据。
- 不引入任何 CDN、npm 运行时依赖、外部图表库 / 字体 / TTS；可视化用原生 SVG 字符串。
- 语音用浏览器内置 speechSynthesis (ja-JP)，零 API 零费用，并做手势解锁与降级。
- 同时适配 PC / 手机：移动优先响应式，手机一屏一题 + 底部操作栏，PC 侧栏 + 一屏多题。
- PWA：manifest + 纯原生 Service Worker（只缓存同源静态文件、不发网络请求、不缓存学习状态）。

CLI:
    python3 scripts/build_site.py [--root PATH] [--day N]
    --root  项目根目录（其下应有 curriculum/ 与 knowledge/seeds/；默认取本脚本上级目录）
    --day   只生成指定一天（1..N）的页面与数据；共享文件始终生成
"""

import argparse
import hashlib
import html
import json
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent

SEED_FILES = {
    "vocab": "vocabulary.jsonl",
    "grammar": "grammar.jsonl",
    "kanji": "kanji.jsonl",
    "questions": "questions.jsonl",
    "materials": "materials.jsonl",
}


def die(msg):
    """明确报错并退出，绝不静默生成空页。"""
    print("build_site.py: 错误: " + str(msg), file=sys.stderr)
    sys.exit(1)


def json_for_script(obj):
    """序列化为可安全放进 <script type=application/json> 的文本。

    转义 < > & 为 JSON 的 \\uXXXX，避免数据里出现 </script> 提前闭合标签；
    JSON.parse 会自动还原，不影响内容（CONTRACTS 第 9 节要求页面只读内嵌 JSON）。
    """
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def load_curriculum(path):
    if not path.is_file():
        die("找不到课程文件：%s（真实数据由别的任务并行生成，本脚本不会创建它）" % path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        die("读取/解析 curriculum.json 失败：%s：%s" % (path, e))
    if not isinstance(data, dict) or not isinstance(data.get("days"), list):
        die("curriculum.json 结构不合法：应为含 days 数组的对象（%s）" % path)
    if not data["days"]:
        die("curriculum.json 的 days 为空，拒绝生成空站点（%s）" % path)
    return data


def load_jsonl(path):
    out = {}
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                die("%s 第 %d 行不是合法 JSON：%s" % (path, ln, e))
            oid = obj.get("id")
            if not oid:
                die("%s 第 %d 行缺少 id 字段" % (path, ln))
            out[oid] = obj
    return out


def load_seeds(seeds_dir):
    if not seeds_dir.is_dir():
        die("找不到种子目录：%s" % seeds_dir)
    tables = {}
    for key, fname in SEED_FILES.items():
        p = seeds_dir / fname
        if not p.is_file():
            die("缺少种子文件：%s（请等待负责生成 seeds 的任务完成）" % p)
        tables[key] = load_jsonl(p)
    return tables


def resolve(ids, table, label, daynum):
    """强校验：curriculum 引用的 id 必须在种子库存在（CONTRACTS 第 8 节），缺失即失败。"""
    out = []
    for i in ids or []:
        if i not in table:
            die("第 %d 天的 %s 引用了种子库不存在的 id：%s（拒绝静默生成缺内容的页面）" % (daynum, label, i))
        out.append(table[i])
    return out


def assemble_day(d, tables, all_ids):
    """按 CONTRACTS 第 9 节组装某一天 web/data/day-NNN.json 的内容。"""
    daynum = d.get("day")
    if not isinstance(daynum, int):
        die("curriculum 中存在缺少 day（整数）的条目：%r" % (d,))

    for i in d.get("review_knowledge_ids") or []:
        if i not in all_ids:
            die("第 %d 天的 review_knowledge_ids 引用了不存在的 id：%s" % (daynum, i))

    vs = resolve(d.get("new_vocab_ids"), tables["vocab"], "new_vocab_ids", daynum)
    gs = resolve(d.get("new_grammar_ids"), tables["grammar"], "new_grammar_ids", daynum)
    ks = resolve(d.get("new_kanji_ids"), tables["kanji"], "new_kanji_ids", daynum)
    qs = resolve(d.get("question_ids"), tables["questions"], "question_ids", daynum)
    ms = resolve(d.get("material_ids"), tables["materials"], "material_ids", daynum)

    vocab_out = [{
        "id": v["id"],
        "surface": v.get("surface", ""),
        "kana": v.get("kana", ""),
        "meaning_zh": v.get("meaning_zh", ""),
        "jlpt": v.get("jlpt", ""),
    } for v in vs]

    grammar_out = [{
        "id": g["id"],
        "pattern": g.get("pattern", ""),
        "meaning_zh": g.get("meaning_zh", ""),
        "connection": g.get("connection", ""),
        "example": (g.get("examples") or [{}])[0].get("ja", "") if g.get("examples") else "",
    } for g in gs]

    kanji_out = [{
        "id": k["id"],
        "char": k.get("char", ""),
        "onyomi": k.get("onyomi") or [],
        "kunyomi": k.get("kunyomi") or [],
        "zh_trap": k.get("zh_trap", ""),
    } for k in ks]

    questions_out = [{
        "id": q["id"],
        "type": q.get("type", ""),
        "prompt_ja": q.get("prompt_ja", ""),
        "prompt_zh": q.get("prompt_zh", ""),
        "options": q.get("options") or [],
        "answer": q.get("answer") if q.get("answer") is not None else "",
        "rationale": q.get("rationale", ""),
        "audio_text": q.get("audio_text", ""),
        "rubric": q.get("rubric", ""),
        "difficulty": q.get("difficulty", 0),
    } for q in qs]

    materials_out = [{
        "id": m["id"],
        "kind": m.get("kind", ""),
        "title": m.get("title", ""),
        "text_ja": m.get("text_ja", ""),
        "audio_text": m.get("audio_text", ""),
        "url": m.get("url", ""),
        "license": m.get("license", ""),
    } for m in ms]

    viz = {
        "day": daynum,
        "phase": d.get("phase", ""),
        "new_count": len(vs) + len(gs) + len(ks),
        "review_count": len(d.get("review_knowledge_ids") or []),
        "question_count": len(qs),
    }

    return {
        "day": daynum,
        "phase": d.get("phase", ""),
        "theme": d.get("theme", ""),
        "scene": d.get("scene", ""),
        "scene_tag": d.get("scene_tag", ""),
        "can_do": d.get("can_do", ""),
        "focus": d.get("focus") or [],
        "objectives": d.get("objectives") or [],
        "minutes": d.get("minutes", 60),
        "blocks": d.get("blocks") or [],
        "vocab": vocab_out,
        "grammar": grammar_out,
        "kanji": kanji_out,
        "questions": questions_out,
        "materials": materials_out,
        "viz": viz,
        "assessment": d.get("assessment", "none"),
    }


def build_site_summary(curriculum):
    """80 天热力图用的站点级摘要，来自 curriculum 元数据（内嵌进每个页面）。"""
    meta = curriculum.get("meta", {})
    days = []
    for d in curriculum["days"]:
        days.append({
            "day": d.get("day"),
            "phase": d.get("phase", ""),
            "theme": d.get("theme", ""),
            "new_count": len(d.get("new_vocab_ids") or [])
                         + len(d.get("new_grammar_ids") or [])
                         + len(d.get("new_kanji_ids") or []),
            "review_count": len(d.get("review_knowledge_ids") or []),
            "question_count": len(d.get("question_ids") or []),
            "assessment": d.get("assessment", "none"),
        })
    days.sort(key=lambda x: x["day"])
    return {
        "meta": {
            "days": meta.get("days", len(days)),
            "minutes_per_day": meta.get("minutes_per_day", 60),
            "version": meta.get("version", "1"),
        },
        "days": days,
    }


def compute_build_id(curriculum_path, seeds_dir):
    """对真源数据取哈希作为 SW 缓存版本；任一源文件变化即失效更新。"""
    h = hashlib.sha256()
    h.update(b"nh80-sw-v1|")
    h.update(curriculum_path.read_bytes())
    for fname in sorted(SEED_FILES.values()):
        h.update((seeds_dir / fname).read_bytes())
    return h.hexdigest()[:12]


# --------------------------------------------------------------------------
# 页面外壳（无任何外部资源引用；CSS/JS/PWA 走相对路径，PC / 手机同一份外壳）
# --------------------------------------------------------------------------

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#f6f8fa" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0f1419" media="(prefers-color-scheme: dark)">
<meta name="color-scheme" content="light dark">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Nihongo 80">
<meta name="format-detection" content="telephone=no">
<title>@@TITLE@@</title>
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/svg+xml" href="icon.svg">
<link rel="apple-touch-icon" href="icon.svg">
<link rel="stylesheet" href="assets/app.css">
</head>
<body>
<a class="skip-link" href="#app">跳到主要内容</a>

<header class="appbar" id="appbar">
  <div class="appbar-inner">
    <a class="brand" href="index.html">Nihongo 80</a>
    <span class="appbar-sub" id="appbar-sub"></span>
    <span class="appbar-spacer"></span>
    <button class="icon-btn toc-toggle" id="toc-toggle" type="button" aria-expanded="false" aria-controls="sidebar">目录</button>
  </div>
  <div class="top-progress" id="top-progress" role="progressbar" aria-label="答题进度" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
    <div class="top-progress-bar" id="top-progress-bar"></div>
  </div>
</header>

<div class="layout" id="layout">
  <aside class="sidebar" id="sidebar" aria-label="侧栏">
    <div class="side-block">
      <div class="side-title">当日导航</div>
      <nav class="side-nav" id="side-nav"></nav>
    </div>
    <div class="side-block">
      <div class="side-title">学习进度</div>
      <div class="side-progress" id="side-progress">尚未开始</div>
    </div>
    <div class="side-block side-ttx" id="side-tts"></div>
    <div class="side-block side-offline" id="side-offline"></div>
    <div class="side-block side-note">
      网页不是状态真源。离线仅展示课程内容；成绩靠「回传码」复制回 WorkBuddy 会话导入。
    </div>
  </aside>

  <main class="main" id="app" tabindex="-1">
    <div id="tts-banner" class="banner banner-info" hidden></div>
  </main>
</div>

<nav class="actionbar" id="actionbar" aria-label="练习操作">
  <button class="act-btn" data-act="prev" type="button">上一题</button>
  <button class="act-btn" data-act="next" type="button">下一题</button>
  <button class="act-btn act-primary" data-act="submit" type="button">提交</button>
  <button class="act-btn" data-act="finish" type="button">完成</button>
  <button class="act-btn" data-act="copy" type="button">复制码</button>
</nav>

<footer class="site-footer">
  <p>本页面仅做展示、练习与即时判分；学习状态真源为本地 SQLite (data/state.db)，网页不向任何服务器发送学习数据。</p>
  <p>语音使用浏览器内置 speechSynthesis (ja-JP)，无外部 TTS / API / CDN；不支持时降级为文本 + 假名读音。</p>
  <p>离线仅展示，成绩靠回传码：复制 / 分享 / 下载后到 WorkBuddy 会话粘贴导入，或先存备忘录稍后导入。</p>
</footer>

<script type="application/json" id="nh80-site">@@SITE_JSON@@</script>
@@DAY_BLOCK@@<script src="assets/app.js"></script>
<script>
/* Service Worker 注册：加主屏后可离线打开已缓存课程。file:// 与不安全上下文自动跳过。 */
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('sw.js').catch(function () {});
}
</script>
<noscript><p class="banner banner-warn">需要启用 JavaScript 才能使用本学习页面。</p></noscript>
</body>
</html>
"""

HTML_404 = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#f6f8fa" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0f1419" media="(prefers-color-scheme: dark)">
<title>404 | Nihongo 80</title>
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/svg+xml" href="icon.svg">
<link rel="stylesheet" href="assets/app.css">
</head>
<body>
<a class="skip-link" href="#app">跳到主要内容</a>
<header class="appbar"><div class="appbar-inner"><a class="brand" href="index.html">Nihongo 80</a></div></header>
<main class="main" id="app" tabindex="-1">
  <h1 class="page-title">404 · 页面不存在</h1>
  <p class="lead">没有找到对应的每日页面。可能是该天尚未生成、链接有误，或该页尚未缓存到本机。</p>
  <p><a class="btn btn-primary" href="index.html">返回目录</a></p>
</main>
<footer class="site-footer"><p>离线仅展示，成绩靠回传码。</p></footer>
</body>
</html>
"""


def render_page(title, day_data, site):
    day_block = ""
    if day_data is not None:
        day_block = ('<script type="application/json" id="nh80-day">'
                     + json_for_script(day_data) + '</script>\n')
    out = HTML_TEMPLATE
    out = out.replace("@@TITLE@@", html.escape(title, quote=True))
    out = out.replace("@@DAY_BLOCK@@", day_block)
    out = out.replace("@@SITE_JSON@@", json_for_script(site))
    return out


# --------------------------------------------------------------------------
# PWA：manifest / 纯原生 Service Worker / 矢量图标（均由本脚本生成）
# --------------------------------------------------------------------------

MANIFEST_TEMPLATE = r"""{
  "name": "Nihongo 80 · 每日日语",
  "short_name": "Nihongo 80",
  "description": "80 天日语每日学习页：展示、分步练习、即时判分、生成回传码；离线仅展示。",
  "lang": "zh-CN",
  "dir": "ltr",
  "start_url": "index.html",
  "scope": "./",
  "display": "standalone",
  "orientation": "any",
  "background_color": "#f6f8fa",
  "theme_color": "#f6f8fa",
  "categories": ["education", "productivity"],
  "icons": [
    { "src": "icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any" }
  ]
}
"""

# 纯原生 SW：install 预缓存同源静态文件；fetch 只读缓存，从不 fetch() 网络、
# 从不读取或缓存 localStorage / 答题结果 / 回传码（学习状态绝不进入缓存）。
# 版本随真源数据哈希变化，activate 时删除旧缓存实现失效更新。
SW_TEMPLATE = r"""/* Nihongo 80 Service Worker — 由 build_site.py 生成，勿手改。
 * 约束：只缓存同源静态文件；fetch 阶段绝不调用网络请求；不缓存任何学习状态；
 *       不向任何地址发送学习数据；版本化缓存，activate 清理旧版本。 */
var CACHE = 'nh80-@@BUILD_ID@@';
var ASSETS = @@ASSETS_JSON@@;

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      /* 逐个缓存并吞掉个别缺失资源，避免因单文件缺失导致整个 install 失败。 */
      return Promise.all(ASSETS.map(function (u) {
        return c.add(new Request(u, { cache: 'reload' })).catch(function () {});
      }));
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        if (k.indexOf('nh80-') === 0 && k !== CACHE) return caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.origin !== self.location.origin) return;
  /* /api/* 与 /health 交给 Worker（健康检查需在线），SW 不介入、不回传任何数据。 */
  if (url.pathname.indexOf('/api/') === 0 || url.pathname === '/health') return;
  e.respondWith(
    caches.match(req).then(function (hit) {
      if (hit) return hit;
      if (req.mode === 'navigate' && (url.pathname === '/' || /\/$/.test(url.pathname))) {
        return caches.match(new Request('index.html'));
      }
      return new Response('离线：该资源未缓存', {
        status: 503, statusText: 'Offline',
        headers: { 'content-type': 'text/plain; charset=utf-8' }
      });
    })
  );
});
"""

ICON_SVG = r"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192" role="img" aria-label="Nihongo 80">
  <rect width="192" height="192" rx="40" fill="#2f6feb"/>
  <rect x="18" y="18" width="156" height="156" rx="30" fill="none" stroke="#ffffff" stroke-opacity="0.35" stroke-width="3"/>
  <text x="96" y="134" text-anchor="middle" font-size="108" fill="#ffffff"
        font-family="Hiragino Sans, Hiragino Kaku Gothic ProN, Noto Sans JP, Yu Gothic, sans-serif">あ</text>
</svg>
"""


# --------------------------------------------------------------------------
# 样式（移动优先；断点 640 / 900；浅色默认 + dark 覆盖；零外部字体/CDN）
# 日文字体优先系统 Hiragino / Noto Sans JP，逐级回退。
# --------------------------------------------------------------------------

APP_CSS = r"""
:root{
  --bg:#f6f8fa; --surface:#ffffff; --surface-2:#fbfcfd; --surface-3:#f3f7ff;
  --ink:#1f2328; --ink-2:#3a424c; --muted:#626d78; --line:#e3e8ee;
  --accent:#2f6feb; --accent-weak:#e8f0ff; --accent-ink:#ffffff;
  --good:#1a7f37; --good-weak:#e6f4ea;
  --bad:#cf222e; --bad-weak:#fbe9eb;
  --warn:#9a6700; --warn-weak:#fff4d6;
  --bar-track:#eceff3; --code-bg:#ffffff;
  --radius:12px; --tap:44px;
  --appbar-h:56px;
  --sa-t:env(safe-area-inset-top, 0px);
  --sa-b:env(safe-area-inset-bottom, 0px);
  --sa-l:env(safe-area-inset-left, 0px);
  --sa-r:env(safe-area-inset-right, 0px);
  --jp-font:"Hiragino Sans","Hiragino Kaku Gothic ProN","Noto Sans JP",
    "Yu Gothic","Meiryo",-apple-system,BlinkMacSystemFont,"PingFang SC",
    "Microsoft YaHei",sans-serif;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0f1419; --surface:#171d24; --surface-2:#1c232c; --surface-3:#1b2433;
    --ink:#e9eef4; --ink-2:#c7d0da; --muted:#9aa6b2; --line:#2c3540;
    --accent:#79a6ff; --accent-weak:#1d2c47; --accent-ink:#0b1220;
    --good:#5ad07b; --good-weak:#16301f;
    --bad:#ff7b7b; --bad-weak:#3a1c20;
    --warn:#e6bb52; --warn-weak:#332a12;
    --bar-track:#242d38; --code-bg:#10161c;
  }
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%; text-size-adjust:100%}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family:var(--jp-font); line-height:1.7; font-size:16px;
  padding-left:var(--sa-l); padding-right:var(--sa-r);
  padding-bottom:calc(72px + var(--sa-b));
  overflow-wrap:break-word;
}
img,svg,textarea,input,select{max-width:100%}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
[hidden]{display:none !important}
.skip-link{position:absolute;left:-9999px;top:0;background:var(--accent);
  color:#fff;padding:10px 14px;z-index:200;border-radius:0 0 8px 0}
.skip-link:focus{left:0}

/* ------- 粘性顶部栏 + 进度条（移动端主进度） ------- */
.appbar{position:sticky;top:0;z-index:50;background:var(--surface);
  border-bottom:1px solid var(--line);padding-top:var(--sa-t)}
.appbar-inner{display:flex;align-items:center;gap:10px;min-height:var(--appbar-h);
  padding:6px calc(12px + var(--sa-r)) 6px calc(12px + var(--sa-l))}
.brand{font-weight:700;font-size:18px;color:var(--ink);white-space:nowrap}
.appbar-sub{font-size:13px;color:var(--muted);white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;max-width:44vw}
.appbar-spacer{flex:1;min-width:0}
.top-progress{height:4px;background:var(--bar-track);overflow:hidden}
.top-progress-bar{height:100%;width:0;background:var(--accent);
  transition:width .25s ease}

/* ------- 布局：手机单列；PC 侧栏 + 主区 ------- */
.layout{display:grid;grid-template-columns:minmax(0,1fr);max-width:100%;margin:0 auto}
.main{min-width:0;padding:14px calc(14px + var(--sa-r)) 20px calc(14px + var(--sa-l))}
.sidebar{display:none}
.sidebar.open{display:block;margin:12px calc(14px + var(--sa-r)) 0 calc(14px + var(--sa-l));
  border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);padding:6px 14px}
.side-block{padding:10px 0;border-bottom:1px solid var(--line)}
.side-block:last-child{border-bottom:none}
.side-title{font-size:12px;color:var(--muted);font-weight:700;letter-spacing:.04em;margin-bottom:6px}
.side-nav{display:flex;flex-direction:column;gap:2px}
.side-nav .nav-link{display:flex;align-items:center;min-height:var(--tap);
  padding:6px 8px;border-radius:8px;font-size:14px}
.side-nav .nav-link:hover{background:var(--surface-2);text-decoration:none}
.side-progress{font-size:13px;color:var(--ink-2)}
.side-ttx,.side-offline,.side-note{font-size:12.5px;color:var(--muted);line-height:1.6}

/* ------- 通用控件（触控目标 >= 44px，输入 >= 16px） ------- */
button,select,input,textarea{font-family:inherit}
button,.btn,.opt,.chip,.act-btn,.icon-btn,.toc-toggle,.nav-link,.day-tile,
.flip-front,.q-submit,select{min-height:var(--tap)}
input,textarea,select{font-size:16px;color:var(--ink);background:var(--surface);
  border:1px solid var(--line);border-radius:8px;padding:8px 10px}
textarea{width:100%;resize:vertical;line-height:1.6}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;
  border:1px solid var(--line);background:var(--surface);color:var(--ink);
  padding:8px 14px;border-radius:8px;font-size:14px;cursor:pointer}
.btn:hover{border-color:var(--accent)}
.btn:disabled,.act-btn:disabled{opacity:.42;cursor:not-allowed}
.btn-primary{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.btn-mini{font-size:13px;padding:6px 11px}
.icon-btn,.toc-toggle{display:inline-flex;align-items:center;justify-content:center;
  border:1px solid var(--line);background:var(--surface);color:var(--ink);
  border-radius:8px;padding:6px 12px;font-size:14px;cursor:pointer;min-width:var(--tap)}
.btn-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0}

/* ------- 移动端底部操作栏 ------- */
.actionbar{position:fixed;left:0;right:0;bottom:0;z-index:60;display:flex;gap:5px;
  padding:8px calc(8px + var(--sa-r)) calc(8px + var(--sa-b)) calc(8px + var(--sa-l));
  background:var(--surface);border-top:1px solid var(--line);
  box-shadow:0 -3px 14px rgba(0,0,0,.07)}
.act-btn{flex:1 1 0;min-width:0;border:1px solid var(--line);background:var(--surface);
  color:var(--ink);border-radius:9px;font-size:12px;line-height:1.25;cursor:pointer;
  padding:4px 2px}
.act-primary{background:var(--accent);border-color:var(--accent);color:var(--accent-ink);font-weight:700}

/* ------- 文本 / 标题 ------- */
.muted{color:var(--muted);font-size:13px}
.lead{color:var(--ink-2);font-size:15px}
.page-title{font-size:22px;margin:6px 0 8px;line-height:1.35;word-break:normal}
.day-head{margin-bottom:8px}
.day-kicker{color:var(--accent);font-weight:700;font-size:13px;letter-spacing:.02em}
.scene{color:var(--muted);margin:4px 0;word-break:normal}
.badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;
  background:var(--accent-weak);color:var(--accent);margin:2px 4px 2px 0}
.badge-good{background:var(--good-weak);color:var(--good)}
.badge-bad{background:var(--bad-weak);color:var(--bad)}
.banner{padding:10px 12px;border-radius:8px;font-size:13px;margin:10px 0;line-height:1.6}
.banner-info{background:var(--accent-weak);color:var(--ink)}
.cando-card{font-size:15px;font-weight:600;line-height:1.6;border-left:4px solid var(--accent)}
.banner-warn{background:var(--warn-weak);color:var(--warn)}
.tts-controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:8px}
.rate-sel{padding:6px 8px;font-size:14px}
.notice{background:var(--warn-weak);color:var(--ink);border-left:4px solid var(--warn);
  padding:10px 12px;border-radius:6px;font-size:13.5px;margin:12px 0;line-height:1.6}

/* ------- 折叠分区（移动避免几十屏滚动） ------- */
.section{border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);
  margin:12px 0;overflow:hidden}
.section-sum{cursor:pointer;padding:12px 14px;min-height:var(--tap);font-weight:600;
  list-style:none;background:var(--surface-2);user-select:none;
  display:flex;align-items:center;gap:8px;line-height:1.4}
.section-sum::-webkit-details-marker{display:none}
.section-sum::before{content:"";flex:0 0 auto;width:8px;height:8px;
  border-right:2px solid var(--muted);border-bottom:2px solid var(--muted);
  transform:rotate(-45deg);transition:transform .15s ease}
.section[open] > .section-sum::before{transform:rotate(45deg)}
.section-body{padding:2px 14px 14px}
.objectives{margin:8px 0;padding-left:20px}
.objectives li{margin:4px 0}

/* ------- 60 分钟时间条 ------- */
.timeline-wrap{margin:10px 0}
.timeline{display:flex;width:100%;height:32px;border-radius:6px;overflow:hidden;border:1px solid var(--line)}
.timeline-seg{height:100%;display:flex;align-items:center;justify-content:center;
  color:#20303f;font-size:11px;min-width:0;border-right:1px solid rgba(255,255,255,.6)}
.timeline-seg:last-child{border-right:none}
.timeline-lbl{white-space:nowrap}
.timeline-legend{display:flex;flex-wrap:wrap;gap:8px 16px;margin-top:8px}
.tl-item{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:6px}
.tl-swatch{width:12px;height:12px;border-radius:3px;display:inline-block;flex:0 0 auto}

/* ------- 可视化（SVG viewBox 自适应；窄屏热力图可横向滚动） ------- */
.viz-grid{display:grid;grid-template-columns:1fr;gap:12px;margin:10px 0}
.viz-card{border:1px solid var(--line);border-radius:8px;padding:10px;background:var(--surface-2);min-width:0}
.viz-title{font-size:13px;margin:0 0 6px;color:var(--muted);font-weight:700}
.viz-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.svg-mount svg{width:100%;height:auto;display:block}
.viz-heat .svg-mount svg{min-width:280px}
.svg-lbl{fill:var(--muted)}
.svg-val{fill:var(--ink)}
.svg-bar-track{fill:var(--bar-track)}
.svg-bar-accent{fill:var(--accent)}
.svg-bar-good{fill:var(--good)}
.legend{display:flex;flex-wrap:wrap;gap:10px;margin:6px 0 2px}
.legend-item{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:5px}
.legend-swatch{width:13px;height:13px;border-radius:3px;display:inline-block;border:1px solid var(--line)}

/* ------- 词汇 / 语法 / 汉字翻面卡（手机一次只展开一张） ------- */
.card-grid{display:grid;grid-template-columns:1fr;gap:10px;margin:10px 0}
.flipcard{border:1px solid var(--line);border-radius:8px;background:var(--surface-2);min-height:var(--tap)}
.flip-front,.flip-back{width:100%;border:none;background:transparent;cursor:pointer;
  font-family:var(--jp-font);color:var(--ink);text-align:left;padding:12px;word-break:normal;
  overflow-wrap:anywhere;line-break:strict}
.flip-front{font-size:26px;font-weight:700;min-height:88px;display:block;line-height:1.5}
.flip-back{display:none;font-size:14px}
.flipcard.revealed .flip-front{display:none}
.flipcard.revealed .flip-back{display:block}
.kv{display:flex;gap:6px;margin:3px 0;font-size:13.5px}
.kv-k{color:var(--muted);min-width:42px;flex:0 0 auto}
.kv-v{color:var(--ink);overflow-wrap:anywhere}
.kana-line{margin-top:6px;font-size:14px;color:var(--accent);line-height:1.9;
  word-break:normal;overflow-wrap:anywhere}
.front-kana{display:none;font-size:13px;color:var(--muted);font-weight:400;margin-top:6px}
.no-ja-tts .front-kana{display:block}
.trap{margin:6px 0;padding:6px 8px;background:var(--warn-weak);color:var(--ink);
  border-radius:6px;font-size:13px;line-height:1.6}
.speak-btn{margin-top:8px}

/* ------- 阅读 / 听力素材（日文大字号、软换行、长文折叠） ------- */
.material{border:1px solid var(--line);border-radius:8px;padding:12px;margin:10px 0;background:var(--surface-2)}
.material-title{margin:0 0 6px;font-size:14px}
.ja-text{font-family:var(--jp-font);font-size:18px;line-height:2.05;margin:6px 0;
  word-break:normal;overflow-wrap:anywhere;line-break:strict;color:var(--ink)}
.longtext{margin:6px 0}
.ext-link{word-break:break-all}
.material-actions{margin-top:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.inline-notice{font-size:12.5px;color:var(--warn);margin-top:6px;line-height:1.6}

/* ------- 练习：手机一屏一题；PC 一屏多题（折叠卡） ------- */
.quiz{margin:10px 0}
.quiz-toolbar{display:none;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0}
.quiz-toolbar .tb-progress{font-size:13px;color:var(--muted);margin-right:auto}
.q-list{margin:8px 0}
.q-list.step-mode .q-card{display:none}
.q-list.step-mode .q-card.active{display:block}
.q-list.grid-mode{display:grid;grid-template-columns:1fr;gap:12px}
.q-card{border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);
  margin:0 0 12px;overflow:hidden}
.q-list.grid-mode .q-card{margin:0}
.q-sum{cursor:pointer;padding:12px 14px;list-style:none;background:var(--surface-2);
  display:block;min-height:var(--tap)}
.q-sum::-webkit-details-marker{display:none}
.q-body{padding:12px 14px 14px;border-top:1px solid var(--line)}
.q-head{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px;color:var(--muted)}
.q-no{font-weight:700;color:var(--ink)}
.q-type{background:var(--accent-weak);color:var(--accent);padding:2px 9px;border-radius:999px}
.q-diff{background:var(--bar-track);color:var(--ink-2);padding:2px 9px;border-radius:999px}
.q-status{margin-left:auto;font-size:12px;color:var(--muted)}
.q-status.ok{color:var(--good)}
.q-status.bad{color:var(--bad)}
.q-prompt-zh{font-size:14px;margin:10px 0 4px;color:var(--ink-2)}
.q-prompt-ja{font-family:var(--jp-font);font-size:20px;line-height:2;margin:4px 0 10px;
  word-break:normal;overflow-wrap:anywhere;line-break:strict;color:var(--ink)}
.q-audio{margin:6px 0;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.q-input{margin:10px 0}
.opts{display:flex;flex-direction:column;gap:8px}
.opt{text-align:left;border:1px solid var(--line);background:var(--surface);border-radius:8px;
  padding:10px 12px;font-family:var(--jp-font);font-size:16px;cursor:pointer;color:var(--ink)}
.opt:hover{border-color:var(--accent)}
.opt.sel{border-color:var(--accent);background:var(--accent-weak)}
.q-text{min-height:var(--tap);font-size:16px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px}
.chip{border:1px solid var(--line);background:var(--surface);border-radius:8px;
  padding:8px 12px;font-family:var(--jp-font);font-size:16px;cursor:pointer;color:var(--ink)}
.chip.used{opacity:.4;cursor:not-allowed}
.reorder-answer{border:1px dashed var(--line);border-radius:8px;padding:8px;
  min-height:var(--tap);margin:4px 0 8px;background:var(--surface-2);font-size:16px;
  line-height:1.8;word-break:normal;overflow-wrap:anywhere}
.q-hint-row{margin:8px 0}
.hint-box{background:var(--warn-weak);color:var(--ink);padding:8px 10px;border-radius:6px;
  font-size:13px;margin-top:6px;line-height:1.6}
.q-actions{margin:10px 0}
.reveal{border-top:1px dashed var(--line);margin-top:10px;padding-top:10px}
.reveal:empty{display:none}
.reveal-row{font-size:14px;margin:5px 0;line-height:1.7;overflow-wrap:anywhere}
.rubric{background:var(--surface-2);border-radius:6px;padding:8px 10px;margin:8px 0;font-size:13.5px}
.rubric-title{font-weight:700;color:var(--muted);margin-bottom:4px}
.rubric-item{padding-left:16px;position:relative;margin:3px 0;line-height:1.6}
.rubric-item::before{content:"";position:absolute;left:2px;top:10px;width:6px;height:6px;
  border-radius:50%;background:var(--accent)}
.self-assess{margin:8px 0;display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:13.5px}
.err-type{margin:8px 0;display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:13.5px}
.sel{padding:6px 8px;font-size:14px}

/* ------- 回传码面板 ------- */
.return-box{border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);margin:14px 0}
.return-box > .section-sum{background:var(--surface-3)}
.return-hint{font-size:13.5px;line-height:1.7;color:var(--ink-2);
  background:var(--warn-weak);padding:10px 12px;border-radius:8px;margin:10px 0}
.return-summary{font-size:13px;color:var(--muted);margin:6px 0;overflow-wrap:anywhere}
.code-area{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:16px;word-break:break-all;background:var(--code-bg);color:var(--ink);
  line-height:1.5;-webkit-user-select:all;user-select:all}
.copy-status{font-size:12.5px;color:var(--good);min-height:1em}

/* ------- 目录页 ------- */
.day-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:9px;margin:10px 0}
.day-tile{border:1px solid var(--line);border-radius:8px;padding:9px;background:var(--surface-2);
  display:flex;flex-direction:column;gap:2px;color:var(--ink);min-height:56px;justify-content:center}
.day-tile:hover{border-color:var(--accent);text-decoration:none}
.day-tile.empty{opacity:.5}
.day-tile-n{font-weight:700;font-size:13px;color:var(--accent)}
.day-tile-t{font-size:12px;line-height:1.4}
.day-tile-p{font-size:11px;color:var(--muted)}

/* ------- 页脚 ------- */
.site-footer{margin-top:20px;padding:16px calc(14px + var(--sa-r)) calc(24px + var(--sa-b)) calc(14px + var(--sa-l));
  border-top:1px solid var(--line);color:var(--muted);font-size:12px;line-height:1.7}
.site-footer p{margin:4px 0}

/* ------- 断点 1：>= 640px（平板）：双列卡片 / 双列可视化 ------- */
@media (min-width:640px){
  .card-grid{grid-template-columns:repeat(auto-fill,minmax(200px,1fr))}
  .viz-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .day-grid{grid-template-columns:repeat(auto-fill,minmax(120px,1fr))}
  .appbar-sub{max-width:60vw}
  .q-list.grid-mode{grid-template-columns:repeat(2,minmax(0,1fr))}
}

/* ------- 断点 2：>= 900px（PC）：侧栏 + 多列，隐藏底部操作栏 ------- */
@media (min-width:900px){
  body{padding-bottom:16px}
  .appbar-inner{max-width:1200px;margin:0 auto}
  .toc-toggle{display:none}
  .actionbar{display:none}
  .layout{grid-template-columns:248px minmax(0,1fr);gap:26px;
    max-width:1200px;padding:0 24px}
  .sidebar,.sidebar.open{display:block;margin:0;padding:20px 0;border:none;
    border-radius:0;background:transparent;
    position:sticky;top:calc(var(--appbar-h) + var(--sa-t) + 12px);
    align-self:start;max-height:calc(100vh - 120px);overflow:auto}
  .main{padding:20px 0 32px}
  .viz-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
  .card-grid{grid-template-columns:repeat(auto-fill,minmax(190px,1fr))}
  .quiz-toolbar{display:flex}
  .q-list.grid-mode{grid-template-columns:repeat(2,minmax(0,1fr))}
  .act-btn,.q-submit{font-size:14px}
}
"""


# --------------------------------------------------------------------------
# 前端逻辑（纯原生 JS；无网络请求 API，无任何外部依赖）
# --------------------------------------------------------------------------

APP_JS = r"""
/* Nihongo 80 前端逻辑（PC / 手机双端）。
 * 不向任何服务器发送学习数据：不发起网络请求，不读写远程接口。
 * 学习状态真源是本地 SQLite；本页只展示 / 练习 / 即时判分 / 生成 NH80R1 回传码，
 * localStorage 仅用于「当日刷新恢复」缓存，不是状态真源。
 */
(function () {
  'use strict';

  function byId(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = String(text);
    return n;
  }
  function esc(s) {
    return String(s === undefined || s === null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function readJSON(id) {
    var n = byId(id);
    if (!n) return null;
    try { return JSON.parse(n.textContent); } catch (e) { return null; }
  }
  function pad2(n) { return String(n).padStart(2, '0'); }
  function pad3(n) { return String(n).padStart(3, '0'); }
  function norm(s) {
    return String(s === undefined || s === null ? '' : s)
      .replace(/[\s\u3000]+/g, '').toLowerCase();
  }
  function isWide() {
    try {
      if (typeof window !== 'undefined' && window.matchMedia) {
        return window.matchMedia('(min-width: 900px)').matches;
      }
      if (typeof window !== 'undefined' && window.innerWidth) {
        return window.innerWidth >= 900;
      }
    } catch (e) {}
    return false;
  }

  /* ---------------- 回传码（CONTRACTS 第 10 节） ---------------- */
  function b64urlEncode(str) {
    var bytes = new TextEncoder().encode(str);
    var bin = '';
    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  function localISO() {
    var d = new Date();
    var off = -d.getTimezoneOffset();
    var sign = off >= 0 ? '+' : '-';
    return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate())
      + 'T' + pad2(d.getHours()) + ':' + pad2(d.getMinutes()) + ':' + pad2(d.getSeconds())
      + sign + pad2(Math.floor(Math.abs(off) / 60)) + ':' + pad2(Math.abs(off) % 60);
  }
  function makeSessionId() {
    var d = new Date();
    var date = '' + d.getFullYear() + pad2(d.getMonth() + 1) + pad2(d.getDate());
    var ck = 'nh80:seq:' + date, n = 0;
    try { n = parseInt(localStorage.getItem(ck) || '0', 10) || 0; } catch (e) { n = 0; }
    n += 1;
    try { localStorage.setItem(ck, String(n)); } catch (e) {}
    return 'session-' + date + '-' + String(n).padStart(3, '0');
  }
  function encodeReturnCode(payload) {
    return 'NH80R1.' + b64urlEncode(JSON.stringify(payload));
  }
  function gradeAnswer(q, ans) {
    if (q.type === 'free_production' || q.type === 'dialogue') return null;
    if (q.answer === undefined || q.answer === null || String(q.answer).length === 0) return null;
    return norm(ans) === norm(q.answer);
  }
  function makePayload(state) {
    var results = Object.keys(state.results).map(function (qid) {
      var r = state.results[qid];
      return {
        qid: r.qid, answer: r.answer, correct: !!r.correct, hinted: !!r.hinted,
        seconds: Math.max(0, Math.round(r.seconds || 0)), error_type: r.error_type || null
      };
    });
    var total = results.reduce(function (a, r) { return a + r.seconds; }, 0);
    return {
      v: 1, day: state.day, session: state.session, ts: localISO(),
      results: results, minutes: Math.max(1, Math.round(total / 60)), source: 'web'
    };
  }

  /* 暴露纯函数 + 调试快照，便于在 Node 中做回传码与布局自测（不影响浏览器运行）。 */
  globalThis.NH80 = {
    b64urlEncode: b64urlEncode,
    encodeReturnCode: encodeReturnCode,
    gradeAnswer: gradeAnswer,
    makePayload: makePayload,
    norm: norm,
    debug: function () {
      return {
        mode: (typeof LAYOUT !== 'undefined' && LAYOUT) ? LAYOUT.mode : null,
        hasQuiz: !!QUIZ,
        answered: QUIZ ? Object.keys(QUIZ.state.results).length : 0,
        total: QUIZ ? QUIZ.total : 0,
        code: QUIZ ? QUIZ.lastCode : null
      };
    }
  };

  if (typeof document === 'undefined' || !document.addEventListener) return;
  /* 入口调用置于 IIFE 最末尾，确保下方 var 顶层状态已初始化后再 init()。 */

  /* ---------------- 全局状态 ---------------- */
  var LAYOUT = { wide: false, mode: 'step' };   // step=手机一屏一题 / grid=PC 一屏多题
  var TTS = { supported: false, jaVoice: false, muted: false, rate: 0.9, unlocked: false, lastText: '' };
  var QUIZ = null;                              // 练习控制器，供外壳按钮调用

  /* ---------------- 语音：手势解锁 + 播放/停止/语速 + 降级 ---------------- */
  function refreshVoices() {
    if (!TTS.supported) { TTS.jaVoice = false; return; }
    var vs = [];
    try { vs = speechSynthesis.getVoices() || []; } catch (e) { vs = []; }
    TTS.jaVoice = vs.some(function (v) { return v && v.lang && /^ja/i.test(v.lang); });
  }
  function detectTTS() {
    TTS.supported = (typeof window !== 'undefined') && ('speechSynthesis' in window)
      && (typeof SpeechSynthesisUtterance !== 'undefined');
    refreshVoices();
    if (TTS.supported && typeof speechSynthesis !== 'undefined') {
      try { speechSynthesis.addEventListener('voiceschanged', refreshVoices); } catch (e) {}
    }
  }
  function showTTSNotice(node, msg) {
    if (!node) return;
    node.textContent = msg;
    node.hidden = false;
  }
  /* iOS / Android：speechSynthesis 首次必须在用户手势里 speak 一次来解锁语音队列。
     所有 speak 调用本身都发生在 click 处理器内；这里额外提供显式「试听/解锁」手势。 */
  function primeTTS() {
    if (TTS.unlocked || !TTS.supported) return;
    try {
      var u = new SpeechSynthesisUtterance('');
      u.lang = 'ja-JP'; u.volume = 0; u.rate = 1;
      speechSynthesis.speak(u);
      TTS.unlocked = true;
    } catch (e) {}
  }
  function speak(text, noticeNode) {
    if (!text) return;
    TTS.lastText = String(text);
    if (TTS.muted) { showTTSNotice(noticeNode, '静音学习已开启：仅显示文本与假名读音。'); return; }
    if (!TTS.supported) {
      showTTSNotice(noticeNode, '当前浏览器不支持语音合成，已显示文本与假名读音，请跟读 / 静音学习。');
      return;
    }
    primeTTS();  // 必须在用户手势内
    if (!TTS.jaVoice) {
      showTTSNotice(noticeNode, '未检测到日语语音（ja-JP）：可能发音不准或无声；已显示假名读音，请跟读或开启静音学习。');
    }
    try {
      speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance(String(text));
      u.lang = 'ja-JP';
      u.rate = TTS.rate;
      if (TTS.jaVoice) {
        var vs = speechSynthesis.getVoices() || [];
        for (var i = 0; i < vs.length; i++) {
          if (vs[i] && vs[i].lang && /^ja/i.test(vs[i].lang)) { u.voice = vs[i]; break; }
        }
      }
      u.onerror = function () {
        showTTSNotice(noticeNode, '语音播放被系统拒绝 / 失败：已显示文本与假名读音，请跟读或静音学习。');
      };
      speechSynthesis.speak(u);
    } catch (e) {
      showTTSNotice(noticeNode, '语音播放失败：已显示文本与假名读音，请跟读或静音学习。');
    }
  }
  function stopSpeak() {
    try { speechSynthesis.cancel(); } catch (e) {}
  }
  function setupTTSBanner() {
    detectTTS();
    document.body.classList.toggle('no-ja-tts', !TTS.supported || !TTS.jaVoice);
    var b = byId('tts-banner');
    var side = byId('side-tts');
    var msg;
    if (!TTS.supported) {
      msg = '语音能力检测：浏览器不支持 speechSynthesis。已降级为「文本 + 假名读音」，可跟读或静音学习；不依赖任何外部 TTS。';
    } else if (!TTS.jaVoice) {
      msg = '语音能力检测：支持语音合成，但未发现日语语音（ja-JP）。发音可能不准或无声；已显示假名读音，可手动播放或静音学习。';
    } else {
      msg = '语音能力检测：已发现日语语音（ja-JP）。首次播放请在下方点「试听 / 解锁语音」（iOS / Android 需用户手势解锁）。';
    }
    if (b) {
      b.textContent = msg;
      var bar = el('div', 'tts-controls');
      var unlock = el('button', 'btn btn-mini', '试听 / 解锁语音');
      unlock.type = 'button';
      unlock.addEventListener('click', function () { primeTTS(); speak(TTS.lastText || 'こんにちは'); });
      var stop = el('button', 'btn btn-mini', '停止朗读');
      stop.type = 'button';
      stop.addEventListener('click', function () { stopSpeak(); });
      var rate = el('select', 'rate-sel');
      [['0.7', '慢 0.7'], ['0.9', '标准 0.9'], ['1.0', '快 1.0']].forEach(function (o) {
        var op = el('option', '', o[1]); op.value = o[0]; rate.appendChild(op);
      });
      rate.value = String(TTS.rate);
      rate.setAttribute('aria-label', '朗读语速');
      rate.addEventListener('change', function () {
        TTS.rate = parseFloat(rate.value) || 0.9;
        if (TTS.lastText) speak(TTS.lastText);
      });
      var mute = el('button', 'btn btn-mini', TTS.muted ? '关闭静音' : '静音学习');
      mute.type = 'button';
      mute.addEventListener('click', function () {
        TTS.muted = !TTS.muted;
        mute.textContent = TTS.muted ? '关闭静音' : '静音学习';
        if (TTS.muted) stopSpeak();
      });
      bar.appendChild(unlock); bar.appendChild(stop); bar.appendChild(rate); bar.appendChild(mute);
      b.appendChild(bar);
      b.hidden = false;
    }
    if (side) {
      side.textContent = '语音：' + (TTS.supported
        ? (TTS.jaVoice ? 'ja-JP 可用（需手势解锁）' : '无日语语音，降级为假名读音')
        : '不支持，降级为文本 + 假名');
    }
  }

  /* ---------------- 外壳：布局 / 进度 / 在线状态 / 侧栏导航 ---------------- */
  function detectLayout() {
    LAYOUT.wide = isWide();
    LAYOUT.mode = LAYOUT.wide ? 'grid' : 'step';
    document.body.classList.toggle('is-wide', LAYOUT.wide);
    document.body.classList.toggle('is-narrow', !LAYOUT.wide);
  }
  function setProgress(done, total, label, sub) {
    var pct = total ? Math.round((done / total) * 100) : 0;
    var bar = byId('top-progress-bar');
    if (bar) bar.style.width = pct + '%';
    var tp = byId('top-progress');
    if (tp && tp.setAttribute) tp.setAttribute('aria-valuenow', String(pct));
    var sp = byId('side-progress');
    if (sp) sp.textContent = label || ('已答 ' + done + ' / ' + total + ' 题');
    var as = byId('appbar-sub');
    if (as && sub) as.textContent = sub;
  }
  function setOnlineStatus() {
    var box = byId('side-offline');
    var online = (typeof navigator !== 'undefined' && 'onLine' in navigator) ? navigator.onLine : true;
    if (box) {
      box.textContent = online
        ? '在线 · 课程与素材已缓存，可离线打开；离线仅展示，成绩靠回传码。'
        : '当前离线 · 仅展示已缓存课程；成绩靠回传码回 WorkBuddy 会话导入。';
    }
    document.body.classList.toggle('is-offline', !online);
  }
  function doAction(act) {
    if (!QUIZ) return;
    if (act === 'prev') QUIZ.prev();
    else if (act === 'next') QUIZ.next();
    else if (act === 'submit') QUIZ.submit();
    else if (act === 'finish') QUIZ.finish();
    else if (act === 'copy') QUIZ.copy();
  }
  function setupChrome() {
    var toggle = byId('toc-toggle');
    var sidebar = byId('sidebar');
    if (toggle && sidebar) {
      toggle.addEventListener('click', function () {
        var open = sidebar.classList.toggle('open');
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        toggle.textContent = open ? '收起' : '目录';
      });
      sidebar.addEventListener('click', function (e) {
        if (e.target && e.target.tagName === 'A') {
          sidebar.classList.remove('open');
          toggle.setAttribute('aria-expanded', 'false');
          toggle.textContent = '目录';
        }
      });
    }
    var actionbar = byId('actionbar');
    if (actionbar && actionbar.children) {
      Array.prototype.forEach.call(actionbar.children, function (btn) {
        var act = btn.getAttribute && btn.getAttribute('data-act');
        if (act) btn.addEventListener('click', function () { doAction(act); });
      });
    }
    if (typeof window !== 'undefined' && window.addEventListener) {
      try {
        window.addEventListener('online', setOnlineStatus);
        window.addEventListener('offline', setOnlineStatus);
      } catch (e) {}
    }
    setOnlineStatus();
  }
  function renderNav(site, day) {
    var nav = byId('side-nav');
    var as = byId('appbar-sub');
    if (!day) {
      if (as) as.textContent = '每日学习 · 目录';
      if (nav) {
        var home = el('a', 'nav-link', '目录首页');
        home.href = 'index.html';
        nav.appendChild(home);
      }
      return;
    }
    var d = day.day;
    var total = (site && site.meta && site.meta.days)
      ? site.meta.days : (site && site.days ? site.days.length : 80);
    if (as) as.textContent = '第 ' + d + ' 天 · ' + (day.phase || '') + ' · ' + (day.theme || '');
    if (!nav) return;
    var prev = el('a', 'nav-link', '前一天');
    prev.href = d > 1 ? 'day-' + pad3(d - 1) + '.html' : 'index.html';
    var home2 = el('a', 'nav-link', '目录');
    home2.href = 'index.html';
    var next = el('a', 'nav-link', '后一天');
    next.href = d < total ? 'day-' + pad3(d + 1) + '.html' : 'index.html';
    nav.appendChild(prev); nav.appendChild(home2); nav.appendChild(next);
    var jump = el('a', 'nav-link', '跳到练习');
    jump.href = '#app';
    nav.appendChild(jump);
  }

  /* ---------------- 通用渲染 ---------------- */
  function section(title, open) {
    var d = el('details', 'section');
    if (open) d.open = true;
    d.appendChild(el('summary', 'section-sum', title));
    var body = el('div', 'section-body');
    d.appendChild(body);
    d._body = body;
    return d;
  }
  var PHASE_COLORS = {
    P1: '#bcd7ff', P2: '#a9e6c3', P3: '#ffe1a1',
    P4: '#ffc7bb', P5: '#dcc8ff', P6: '#d3dae2'
  };
  var BLOCK_COLORS = {
    review: '#8fb8ff', input: '#8fd9ad', practice: '#ffd27a',
    output: '#f4a7a0', drill: '#c9b3f5', assessment: '#e59ad6'
  };
  function phaseColor(p) { return PHASE_COLORS[p] || '#e6e9ed'; }
  function shade(hex, f) {
    var c = hex.replace('#', '');
    var r = parseInt(c.substring(0, 2), 16),
        g = parseInt(c.substring(2, 4), 16),
        b = parseInt(c.substring(4, 6), 16);
    f = Math.max(0, Math.min(1, f));
    return 'rgb(' + Math.round(255 + (r - 255) * f) + ','
      + Math.round(255 + (g - 255) * f) + ',' + Math.round(255 + (b - 255) * f) + ')';
  }
  function phaseLegend() {
    var box = el('div', 'legend');
    Object.keys(PHASE_COLORS).forEach(function (p) {
      var it = el('span', 'legend-item');
      var sw = el('span', 'legend-swatch');
      sw.style.background = PHASE_COLORS[p];
      it.appendChild(sw);
      it.appendChild(document.createTextNode(p));
      box.appendChild(it);
    });
    return box;
  }
  function vizCard(title, markup, extra) {
    var c = el('div', 'viz-card' + (extra ? ' ' + extra : ''));
    c.appendChild(el('h3', 'viz-title', title));
    var sc = el('div', 'viz-scroll');
    var m = el('div', 'svg-mount');
    m.innerHTML = markup;        // HTML5 自动进入 SVG 命名空间，无需外部 xmlns
    sc.appendChild(m);
    c.appendChild(sc);
    return c;
  }
  function heatmapSVG(site, currentDay) {
    var s = site || { days: [], meta: {} };
    var total = (s.meta && s.meta.days) ? s.meta.days : (s.days ? s.days.length : 80);
    var map = {};
    (s.days || []).forEach(function (x) { map[x.day] = x; });
    var cols = 10, cell = 26, gap = 5, pad = 8;
    var rows = Math.ceil(total / cols);
    var w = pad * 2 + cols * (cell + gap);
    var h = pad * 2 + rows * (cell + gap);
    var maxQ = 1;
    (s.days || []).forEach(function (x) { if ((x.question_count || 0) > maxQ) maxQ = x.question_count; });
    var out = '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="80 天课程结构热力图">';
    for (var i = 0; i < total; i++) {
      var day = i + 1;
      var col = i % cols, row = Math.floor(i / cols);
      var x = pad + col * (cell + gap), y = pad + row * (cell + gap);
      var info = map[day];
      var fill = '#dfe4ea', stroke = '#c3ccd6', sw = 1;
      var title = 'D' + pad3(day) + '（待生成）';
      if (info) {
        var ratio = (info.question_count || 0) / maxQ;
        fill = shade(phaseColor(info.phase), 0.15 + 0.55 * ratio);
        stroke = '#9aa4b0';
        title = 'D' + pad3(day) + ' · ' + (info.phase || '') + ' · ' + (info.theme || '')
          + ' · 题 ' + (info.question_count || 0) + ' / 新 ' + (info.new_count || 0);
      }
      if (currentDay === day) { stroke = '#1f6feb'; sw = 3; }
      out += '<a href="day-' + pad3(day) + '.html"><rect x="' + x + '" y="' + y
        + '" width="' + cell + '" height="' + cell + '" rx="4" fill="' + fill
        + '" stroke="' + stroke + '" stroke-width="' + sw + '"><title>' + esc(title)
        + '</title></rect></a>';
    }
    out += '</svg>';
    return out;
  }
  function dayStructureSVG(day) {
    var items = [
      ['词汇', (day.vocab || []).length], ['语法', (day.grammar || []).length],
      ['汉字', (day.kanji || []).length], ['题目', (day.questions || []).length],
      ['素材', (day.materials || []).length]
    ];
    var w = 300, rowH = 30, pad = 8, labelW = 48, barMax = 200;
    var h = pad * 2 + items.length * rowH, max = 1;
    items.forEach(function (it) { if (it[1] > max) max = it[1]; });
    var out = '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="当日结构">';
    items.forEach(function (it, i) {
      var y = pad + i * rowH, bw = Math.round((it[1] / max) * barMax);
      out += '<text class="svg-lbl" x="' + pad + '" y="' + (y + 18) + '" font-size="12">' + esc(it[0]) + '</text>'
        + '<rect class="svg-bar-track" x="' + (pad + labelW) + '" y="' + (y + 4) + '" width="' + barMax + '" height="16" rx="3"/>'
        + '<rect class="svg-bar-accent" x="' + (pad + labelW) + '" y="' + (y + 4) + '" width="' + bw + '" height="16" rx="3"/>'
        + '<text class="svg-val" x="' + (pad + labelW + barMax + 6) + '" y="' + (y + 18) + '" font-size="12">' + it[1] + '</text>';
    });
    out += '</svg>';
    return out;
  }
  function typeDistSVG(questions) {
    var counts = {};
    (questions || []).forEach(function (q) { counts[q.type] = (counts[q.type] || 0) + 1; });
    var keys = Object.keys(counts), max = 1;
    keys.forEach(function (k) { if (counts[k] > max) max = counts[k]; });
    var w = 300, rowH = 28, pad = 8, labelW = 92, barMax = 170;
    var h = pad * 2 + Math.max(1, keys.length) * rowH;
    var out = '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="题型分布">';
    if (!keys.length) {
      out += '<text class="svg-lbl" x="' + pad + '" y="' + (pad + 16) + '" font-size="12">（无题目）</text>';
    }
    keys.forEach(function (k, i) {
      var y = pad + i * rowH, bw = Math.round((counts[k] / max) * barMax);
      out += '<text class="svg-lbl" x="' + pad + '" y="' + (y + 17) + '" font-size="12">' + esc(k) + '</text>'
        + '<rect class="svg-bar-track" x="' + (pad + labelW) + '" y="' + (y + 4) + '" width="' + barMax + '" height="14" rx="3"/>'
        + '<rect class="svg-bar-good" x="' + (pad + labelW) + '" y="' + (y + 4) + '" width="' + bw + '" height="14" rx="3"/>'
        + '<text class="svg-val" x="' + (pad + labelW + barMax + 6) + '" y="' + (y + 17) + '" font-size="12">' + counts[k] + '</text>';
    });
    out += '</svg>';
    return out;
  }
  function timeBar(blocks, minutes) {
    var total = 0;
    (blocks || []).forEach(function (b) { total += (b.min || 0); });
    if (!total) total = minutes || 60;
    var wrap = el('div', 'timeline-wrap');
    var bar = el('div', 'timeline');
    (blocks || []).forEach(function (b) {
      var seg = el('div', 'timeline-seg');
      seg.style.width = (((b.min || 0) / total) * 100) + '%';
      seg.style.background = BLOCK_COLORS[b.type] || '#cdd6e0';
      seg.title = (b.type || '') + ' · ' + (b.min || 0) + ' 分 · ' + (b.desc || '');
      seg.appendChild(el('span', 'timeline-lbl', (b.min || 0) + '分'));
      bar.appendChild(seg);
    });
    wrap.appendChild(bar);
    var legend = el('div', 'timeline-legend');
    (blocks || []).forEach(function (b) {
      var it = el('span', 'tl-item');
      var sw = el('span', 'tl-swatch');
      sw.style.background = BLOCK_COLORS[b.type] || '#cdd6e0';
      it.appendChild(sw);
      it.appendChild(document.createTextNode((b.type || '') + ' ' + (b.min || 0) + '分 ' + (b.desc || '')));
      legend.appendChild(it);
    });
    wrap.appendChild(legend);
    return wrap;
  }

  /* ---------------- 翻面卡 / 素材 ---------------- */
  function line(parent, label, value) {
    var p = el('div', 'kv');
    if (label) p.appendChild(el('span', 'kv-k', label));
    p.appendChild(el('span', 'kv-v', value === undefined || value === null || value === '' ? '—' : value));
    parent.appendChild(p);
  }
  function toggleReveal(c) {
    var parent = c.parentNode;
    var solo = parent && parent.getAttribute && parent.getAttribute('data-solo') === '1';
    var willReveal = !c.classList.contains('revealed');
    if (willReveal && solo && parent && parent.children) {
      Array.prototype.forEach.call(parent.children, function (sib) {
        if (sib !== c && sib.classList && sib.classList.contains('revealed')) {
          sib.classList.remove('revealed');
        }
      });
    }
    c.classList.toggle('revealed');
  }
  function flipCard(frontText, backBuilder, speakText) {
    var c = el('div', 'flipcard');
    var f = el('button', 'flip-front', frontText);
    f.type = 'button';
    var b = el('div', 'flip-back');
    backBuilder(b);
    if (speakText) {
      var s = el('button', 'btn btn-mini speak-btn', '朗读');
      s.type = 'button';
      s.addEventListener('click', function (e) { e.stopPropagation(); primeTTS(); speak(speakText, null); });
      b.appendChild(s);
    }
    c.appendChild(f); c.appendChild(b);
    f.addEventListener('click', function () { toggleReveal(c); });
    b.addEventListener('click', function (e) { if (!e.target || e.target.tagName !== 'BUTTON') toggleReveal(c); });
    return c;
  }
  function cardGrid(items, builder, solo) {
    var grid = el('div', 'card-grid');
    if (solo) grid.setAttribute('data-solo', '1');
    items.forEach(function (it) { grid.appendChild(builder(it)); });
    return grid;
  }
  function vocabCard(v) {
    var c = flipCard(v.surface || v.id, function (b) {
      line(b, '假名', v.kana);
      line(b, '释义', v.meaning_zh);
      line(b, 'JLPT', v.jlpt);
      line(b, 'ID', v.id);
      b.appendChild(el('div', 'kana-line', '读音：' + (v.kana || '（无）')));
    }, v.surface || v.kana);
    var fk = el('span', 'front-kana', v.kana || '');
    c.querySelector('.flip-front').appendChild(fk);
    return c;
  }
  function grammarCard(g) {
    return flipCard(g.pattern || g.id, function (b) {
      line(b, '含义', g.meaning_zh);
      line(b, '接续', g.connection);
      line(b, '例句', g.example);
      line(b, 'ID', g.id);
    }, g.example || g.pattern);
  }
  function kanjiCard(k) {
    return flipCard(k.char || k.id, function (b) {
      line(b, '音读', (k.onyomi || []).join(' / '));
      line(b, '训读', (k.kunyomi || []).join(' / '));
      b.appendChild(el('div', 'trap', '中日差异：' + (k.zh_trap || '（无）')));
      line(b, 'ID', k.id);
    }, k.char);
  }
  function collapsibleText(text) {
    if (!text) return el('p', 'muted', '（无正文）');
    var limit = 90;
    if (text.length <= limit) return el('p', 'ja-text', text);
    var box = el('div', 'longtext');
    var preview = el('p', 'ja-text', text.slice(0, limit) + '…');
    var full = el('p', 'ja-text', text);
    full.hidden = true;
    var btn = el('button', 'btn btn-mini', '展开全文');
    btn.type = 'button';
    btn.addEventListener('click', function () {
      var showing = !full.hidden;
      full.hidden = showing;
      preview.hidden = !showing;
      btn.textContent = showing ? '展开全文' : '收起';
    });
    box.appendChild(preview); box.appendChild(full); box.appendChild(btn);
    return box;
  }
  function materialCard(m) {
    var c = el('div', 'material');
    c.appendChild(el('h4', 'material-title', (m.kind || '') + ' · ' + (m.title || m.id)));
    if (m.text_ja) {
      c.appendChild(collapsibleText(m.text_ja));
    } else if (m.url) {
      var a = el('a', 'ext-link', m.url);
      a.href = m.url; a.target = '_blank'; a.rel = 'noopener noreferrer';
      var p = el('p', 'muted', '正文为外部索引（版权原因仅链接）：');
      p.appendChild(a); c.appendChild(p);
    } else {
      c.appendChild(el('p', 'muted', '（无正文）'));
    }
    c.appendChild(el('div', 'muted', '许可：' + (m.license || '—') + ' · ID：' + m.id));
    if (m.audio_text) {
      var row = el('div', 'material-actions');
      var play = el('button', 'btn btn-mini', '朗读 / 播放');
      play.type = 'button';
      var stop = el('button', 'btn btn-mini', '停止');
      stop.type = 'button';
      var notice = el('div', 'inline-notice');
      notice.hidden = true;
      play.addEventListener('click', function () { primeTTS(); speak(m.audio_text, notice); });
      stop.addEventListener('click', function () { stopSpeak(); });
      row.appendChild(play); row.appendChild(stop);
      if (m.kind === 'listening') row.appendChild(el('span', 'muted', '听力素材：可反复播放，或静音跟读文本'));
      c.appendChild(row);
      c.appendChild(notice);
      /* 无 ja-JP 语音或不支持时，明确给出可读文本 / 假名，不静默失败。 */
      c.appendChild(el('div', 'kana-line', '文本读音（TTS 降级/对照）：' + m.audio_text));
    }
    return c;
  }

  /* ---------------- 练习输入 ---------------- */
  function buildInput(q, wrap, initial) {
    var opts = q.options || [];
    if (q.type === 'reorder') {
      var chunks = opts.slice(), seq = [];
      var chips = el('div', 'chips');
      var answerLine = el('div', 'reorder-answer', '（按顺序点击词块）');
      var reset = el('button', 'btn btn-mini', '重置');
      reset.type = 'button';
      function refresh() {
        answerLine.textContent = seq.length
          ? seq.map(function (n) { return chunks[n - 1]; }).join(' ') : '（按顺序点击词块）';
      }
      function restore(v) {
        seq = [];
        Array.prototype.forEach.call(chips.children, function (b) { b.disabled = false; b.classList.remove('used'); });
        String(v || '').split(/[,，\s]+/).forEach(function (x) {
          var n = parseInt(x, 10);
          if (n >= 1 && n <= chunks.length) {
            seq.push(n);
            var btn = chips.children[n - 1];
            if (btn) { btn.disabled = true; btn.classList.add('used'); }
          }
        });
        refresh();
      }
      chunks.forEach(function (ch, idx) {
        var b = el('button', 'chip', ch);
        b.type = 'button';
        b.addEventListener('click', function () {
          if (b.disabled) return;
          seq.push(idx + 1); b.disabled = true; b.classList.add('used'); refresh();
        });
        chips.appendChild(b);
      });
      reset.addEventListener('click', function () { restore(''); });
      wrap.appendChild(chips);
      wrap.appendChild(el('div', 'muted', '你的排列：'));
      wrap.appendChild(answerLine);
      wrap.appendChild(reset);
      wrap._getValue = function () { return seq.join(','); };
      wrap._setValue = restore;
      restore(initial);
      return;
    }
    if (opts.length && (q.type === 'mcq' || q.type === 'read' || q.type === 'listen')) {
      var grp = el('div', 'opts'), chosen = String(initial || ''), buttons = [];
      opts.forEach(function (o) {
        var b = el('button', 'opt', o);
        b.type = 'button';
        if (String(o) === chosen) b.classList.add('sel');
        b.addEventListener('click', function () {
          buttons.forEach(function (x) { x.classList.remove('sel'); });
          b.classList.add('sel'); chosen = String(o);
        });
        buttons.push(b); grp.appendChild(b);
      });
      wrap.appendChild(grp);
      wrap._getValue = function () { return chosen; };
      wrap._setValue = function (v) {
        chosen = String(v || '');
        buttons.forEach(function (b) { b.classList.toggle('sel', b.textContent === chosen); });
      };
      return;
    }
    var ta = el('textarea', 'q-text');
    ta.rows = (q.type === 'free_production' || q.type === 'dialogue') ? 4 : 2;
    ta.placeholder = q.type === 'listen' ? '听写你听到的内容…' : '在此作答…';
    ta.value = String(initial || '');
    ta.setAttribute('aria-label', '作答输入框');
    wrap.appendChild(ta);
    wrap._getValue = function () { return ta.value; };
    wrap._setValue = function (v) { ta.value = String(v || ''); };
  }
  function hintText(q) {
    if (q.rubric) return '评分要点：' + q.rubric.replace(/\n+/g, ' ');
    if (q.answer) {
      var a = String(q.answer);
      return '提示：答案共 ' + Array.from(a).length + ' 个字符，开头是「' + a.charAt(0) + '」。';
    }
    if (q.audio_text) return '提示：可反复点击「朗读题目」，注意听写假名。';
    return '提示：先回忆当天词汇 / 语法，再作答。';
  }

  /* ---------------- 练习 + 回传码 ---------------- */
  function buildPractice(day) {
    var qs = day.questions || [];
    var state = { day: day.day, index: 0, session: null, results: {}, started: {} };
    var mode = LAYOUT.mode;

    var sec = section('练习与测验（先作答，再揭示答案与解析）', true);
    sec._body.appendChild(el('p', 'muted',
      mode === 'step'
        ? '手机端一屏一题：用底部「上一题 / 下一题 / 提交」操作，顶部进度条显示进度。'
        : 'PC 端一屏多题：点击题头展开作答，每题独立判分与解析。'));

    var root = el('div', 'quiz quiz-' + mode);
    sec._body.appendChild(root);

    /* 当日恢复：localStorage 只是刷新/断网缓存，不是状态真源 */
    var saved = null;
    try { saved = JSON.parse(localStorage.getItem('nh80:day:' + day.day) || 'null'); } catch (e) { saved = null; }
    if (saved && saved.results) {
      state.results = saved.results;
      state.session = saved.session || null;
      var rb = el('div', 'banner banner-info',
        '已恢复本机当日缓存（仅用于刷新 / 断网恢复，不是学习状态真源，也不代表已完成）。');
      var clr = el('button', 'btn btn-mini', '清除缓存');
      clr.type = 'button';
      clr.addEventListener('click', function () {
        try { localStorage.removeItem('nh80:day:' + day.day); } catch (e) {}
        if (typeof location !== 'undefined' && location.reload) location.reload();
      });
      rb.appendChild(document.createTextNode(' '));
      rb.appendChild(clr);
      root.appendChild(rb);
    }
    if (!state.session) state.session = makeSessionId();

    /* PC 工具条 */
    var toolbar = el('div', 'quiz-toolbar');
    var tbProgress = el('span', 'tb-progress', '已答 0 / ' + qs.length + ' 题');
    var tbFinish = el('button', 'btn btn-primary', '完成并生成回传码');
    tbFinish.type = 'button';
    var tbCopy = el('button', 'btn', '复制回传码');
    tbCopy.type = 'button';
    toolbar.appendChild(tbProgress); toolbar.appendChild(tbFinish); toolbar.appendChild(tbCopy);
    root.appendChild(toolbar);

    /* 回传码面板 */
    var returnBox = el('details', 'return-box');
    returnBox.appendChild(el('summary', 'section-sum', '回传码（NH80R1 · 复制 / 分享 / 下载）'));
    var rbBody = el('div', 'section-body');
    rbBody.appendChild(el('div', 'return-hint',
      '复制后到 WorkBuddy 会话粘贴导入，或先存备忘录稍后导入。由本地 import-web-result 校验、去重、写入 SQLite 并触发 FSRS 排期。网页不写状态、不发送学习数据。'));
    var summary = el('div', 'return-summary', '尚未生成');
    rbBody.appendChild(summary);
    var codeArea = el('textarea', 'code-area');
    codeArea.readOnly = true; codeArea.rows = 4;
    codeArea.setAttribute('aria-label', '回传码文本框（可全选复制）');
    rbBody.appendChild(codeArea);
    var btnRow = el('div', 'btn-row');
    var copyBtn = el('button', 'btn btn-primary', '复制回传码');
    copyBtn.type = 'button';
    var selectBtn = el('button', 'btn', '全选文本');
    selectBtn.type = 'button';
    var shareBtn = el('button', 'btn', '系统分享');
    shareBtn.type = 'button';
    var dlBtn = el('button', 'btn', '下载 .txt');
    dlBtn.type = 'button';
    var regenBtn = el('button', 'btn', '重新生成');
    regenBtn.type = 'button';
    [copyBtn, selectBtn, shareBtn, dlBtn, regenBtn].forEach(function (b) { btnRow.appendChild(b); });
    rbBody.appendChild(btnRow);
    var copyStatus = el('div', 'copy-status', '');
    rbBody.appendChild(copyStatus);
    returnBox.appendChild(rbBody);
    root.appendChild(returnBox);

    var lastCode = '';

    function save() {
      try {
        localStorage.setItem('nh80:day:' + day.day,
          JSON.stringify({ session: state.session, results: state.results }));
      } catch (e) {}
    }
    function elapsed(qid) {
      if (!state.started[qid]) state.started[qid] = Date.now();
      return Math.round((Date.now() - state.started[qid]) / 1000);
    }
    function generate(open) {
      var payload = makePayload(state);
      lastCode = encodeReturnCode(payload);
      QUIZ.lastCode = lastCode;
      codeArea.value = lastCode;
      summary.textContent = '已答 ' + payload.results.length + ' / ' + qs.length
        + ' 题 · 约 ' + payload.minutes + ' 分钟 · 会话 ' + payload.session
        + ' · 来源 ' + payload.source;
      if (open) returnBox.open = true;
      return lastCode;
    }
    function selectCode() {
      codeArea.focus();
      if (codeArea.select) codeArea.select();
      if (codeArea.setSelectionRange) {
        try { codeArea.setSelectionRange(0, codeArea.value.length); } catch (e) {}
      }
      copyStatus.textContent = '已全选文本框，可长按 / 复制';
    }
    function copyCode() {
      var code = codeArea.value || generate(true);
      var done = function (m) { copyStatus.textContent = m; };
      var fallback = function () {
        try {
          codeArea.focus();
          if (codeArea.select) codeArea.select();
          var ok = document.execCommand && document.execCommand('copy');
          done(ok ? '已复制（兼容模式）' : '复制不可用：已全选文本框，请手动长按 / 复制');
        } catch (e) { done('复制不可用：已全选文本框，请手动复制'); }
      };
      if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
        try {
          var p = navigator.clipboard.writeText(code);
          if (p && p.then) p.then(function () { done('已复制到剪贴板'); }, fallback);
          else fallback();
        } catch (e) { fallback(); }
      } else fallback();
    }
    function shareCode() {
      var code = codeArea.value || generate(true);
      if (typeof navigator !== 'undefined' && navigator.share) {
        try {
          var p = navigator.share({
            title: 'Nihongo 80 回传码 · 第 ' + day.day + ' 天',
            text: code
          });
          if (p && p.catch) p.catch(function () {});
        } catch (e) { copyStatus.textContent = '系统分享未成功，请用「复制回传码」'; }
      } else {
        copyStatus.textContent = '此浏览器不支持系统分享，请用「复制回传码」或「下载 .txt」';
      }
    }
    function downloadCode() {
      var code = codeArea.value || generate(true);
      try {
        var blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'nh80-day-' + pad3(day.day) + '-' + state.session + '.txt';
        document.body.appendChild(a);
        if (a.click) a.click();
        document.body.removeChild(a);
        if (URL.revokeObjectURL && typeof setTimeout !== 'undefined') {
          setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
        }
        copyStatus.textContent = '已下载 .txt 备份，稍后可从中复制导入';
      } catch (e) {
        copyStatus.textContent = '下载不可用，请「复制回传码」或「全选文本」';
      }
    }
    function finish() {
      generate(true);
      if (returnBox.scrollIntoView) {
        try { returnBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } catch (e) {}
      }
    }

    copyBtn.addEventListener('click', copyCode);
    selectBtn.addEventListener('click', selectCode);
    shareBtn.addEventListener('click', shareCode);
    dlBtn.addEventListener('click', downloadCode);
    regenBtn.addEventListener('click', function () { generate(true); copyStatus.textContent = '已重新生成'; });
    tbFinish.addEventListener('click', finish);
    tbCopy.addEventListener('click', copyCode);

    function showReveal(q, r, box, onChange) {
      box.innerHTML = '';
      var badge = r.correct
        ? el('span', 'badge badge-good', '答对')
        : el('span', 'badge badge-bad', '未答对 / 待复核');
      box.appendChild(badge);
      box.appendChild(el('div', 'reveal-row', '你的答案：' + (r.answer || '（空）')));
      if (q.answer) box.appendChild(el('div', 'reveal-row', '参考答案：' + q.answer));
      if (q.rationale) box.appendChild(el('div', 'reveal-row', '解析：' + q.rationale));
      if (q.rubric) {
        var rub = el('div', 'rubric');
        rub.appendChild(el('div', 'rubric-title', '评分准则（自评）'));
        String(q.rubric).split(/\n+/).forEach(function (t) {
          if (t.trim()) rub.appendChild(el('div', 'rubric-item', t.trim()));
        });
        box.appendChild(rub);
      }
      if (q.type === 'free_production' || q.type === 'dialogue' || !q.answer) {
        var sa = el('div', 'self-assess');
        sa.appendChild(el('span', '', '自评：'));
        var yes = el('button', 'btn btn-mini', '达成');
        var no = el('button', 'btn btn-mini', '未达成');
        yes.type = no.type = 'button';
        yes.addEventListener('click', function () {
          r.correct = true; save();
          badge.className = 'badge badge-good'; badge.textContent = '答对（自评达成）';
          if (onChange) onChange();
        });
        no.addEventListener('click', function () {
          r.correct = false; save();
          badge.className = 'badge badge-bad'; badge.textContent = '未达成（自评）';
          if (onChange) onChange();
        });
        sa.appendChild(yes); sa.appendChild(no);
        box.appendChild(sa);
      }
      if (!r.correct) {
        var et = el('div', 'err-type');
        et.appendChild(el('span', '', '错误类型（可选）：'));
        var sel = el('select', 'sel');
        [['', '（不指定）'], ['forgetting', '遗忘'], ['meaning_confusion', '词义混淆'],
         ['particle', '助词'], ['conjugation', '变形'], ['listening', '听力'],
         ['comprehension', '理解'], ['kanji_reading', '汉字读音'],
         ['orthography', '书写'], ['other', '其他']].forEach(function (o) {
          var op = el('option', '', o[1]);
          op.value = o[0];
          sel.appendChild(op);
        });
        sel.value = r.error_type || '';
        sel.addEventListener('change', function () {
          r.error_type = sel.value || null; save(); if (onChange) onChange();
        });
        et.appendChild(sel);
        box.appendChild(et);
      }
    }

    var cards = [];
    function makeCard(q, i) {
      state.started[q.id] = Date.now();
      var node = el('details', 'q-card');
      node.setAttribute('data-qid', q.id);
      if (mode === 'step') node.open = true;   // 手机：正文常显，仅 active 卡可见
      var sum = el('summary', 'q-sum');
      if (mode === 'step') {
        sum.addEventListener('click', function (e) { if (e.preventDefault) e.preventDefault(); });
      }
      var head = el('div', 'q-head');
      head.appendChild(el('span', 'q-no', '第 ' + (i + 1) + ' / ' + qs.length + ' 题'));
      head.appendChild(el('span', 'q-type', q.type));
      head.appendChild(el('span', 'q-diff', '难度 ' + (q.difficulty || '-')));
      var status = el('span', 'q-status', '未答');
      head.appendChild(status);
      sum.appendChild(head);
      if (q.prompt_zh) sum.appendChild(el('p', 'q-prompt-zh', q.prompt_zh));
      if (q.prompt_ja) sum.appendChild(el('p', 'q-prompt-ja', q.prompt_ja));
      node.appendChild(sum);

      var body = el('div', 'q-body');
      if (q.audio_text) {
        var arow = el('div', 'q-audio');
        var play = el('button', 'btn btn-mini', '朗读题目');
        play.type = 'button';
        var stop = el('button', 'btn btn-mini', '停止');
        stop.type = 'button';
        var anotice = el('div', 'inline-notice');
        anotice.hidden = true;
        play.addEventListener('click', function () { primeTTS(); speak(q.audio_text, anotice); });
        stop.addEventListener('click', function () { stopSpeak(); });
        arow.appendChild(play); arow.appendChild(stop); arow.appendChild(anotice);
        body.appendChild(arow);
        body.appendChild(el('div', 'kana-line', '文本读音（TTS 降级/对照）：' + q.audio_text));
      }

      var inputWrap = el('div', 'q-input');
      buildInput(q, inputWrap, '');
      var getValue = inputWrap._getValue;
      var setValue = inputWrap._setValue;
      body.appendChild(inputWrap);

      var hintRow = el('div', 'q-hint-row');
      var hintBtn = el('button', 'btn btn-mini', '显示提示');
      hintBtn.type = 'button';
      var hintBox = el('div', 'hint-box');
      hintBox.hidden = true;
      hintBtn.addEventListener('click', function () {
        hintBox.hidden = false; hintBox.textContent = hintText(q);
        markHint(q);
      });
      hintRow.appendChild(hintBtn); hintRow.appendChild(hintBox);
      body.appendChild(hintRow);

      var actionRow = el('div', 'q-actions');
      var submit = el('button', 'btn btn-primary q-submit', '提交答案');
      submit.type = 'button';
      actionRow.appendChild(submit);
      body.appendChild(actionRow);

      var reveal = el('div', 'reveal');
      body.appendChild(reveal);
      node.appendChild(body);

      function markHint(q2) {
        var r = state.results[q2.id];
        if (!r) {
          r = { qid: q2.id, answer: '', correct: false, hinted: true,
                seconds: elapsed(q2.id), error_type: null };
          state.results[q2.id] = r;
        }
        r.hinted = true;
        save();
      }
      function paintStatus(r) {
        status.textContent = r.correct ? '答对' : '未答对';
        status.className = 'q-status ' + (r.correct ? 'ok' : 'bad');
      }
      function doSubmit() {
        var r = state.results[q.id];
        if (r && r._graded) return;
        var ans = getValue();
        if (!r) {
          r = { qid: q.id, answer: ans, correct: false, hinted: false,
                seconds: elapsed(q.id), error_type: null };
        }
        r.answer = ans;
        var g = gradeAnswer(q, ans);
        if (g !== null) r.correct = g;
        else if (r.correct === null || r.correct === undefined) r.correct = false;
        r._graded = true;
        state.results[q.id] = r;
        save();
        submit.disabled = true;
        showReveal(q, r, reveal, updateChrome);
        paintStatus(r);
        updateChrome();
      }
      submit.addEventListener('click', doSubmit);

      var existing = state.results[q.id];
      if (existing) {
        if (setValue) setValue(existing.answer);
        submit.disabled = true;
        showReveal(q, existing, reveal, updateChrome);
        paintStatus(existing);
        if (existing.hinted) { hintBox.hidden = false; hintBox.textContent = hintText(q); }
      }
      return { node: node, q: q, submit: doSubmit };
    }
    function updateChrome() {
      var done = Object.keys(state.results).length;
      var total = qs.length;
      var sub = mode === 'step'
        ? ('第 ' + (state.index + 1) + ' / ' + total + ' 题')
        : ('第 ' + day.day + ' 天 · 共 ' + total + ' 题');
      setProgress(done, total, '已答 ' + done + ' / ' + total + ' 题', sub);
      tbProgress.textContent = '已答 ' + done + ' / ' + total + ' 题';
      setActDisabled('prev', mode !== 'step' || state.index <= 0);
      setActDisabled('next', mode !== 'step' || state.index >= total - 1);
      var cur = mode === 'step' ? cards[state.index] : null;
      var graded = cur && state.results[cur.q.id] && state.results[cur.q.id]._graded;
      setActDisabled('submit', mode !== 'step' || !!graded);
      setActDisabled('finish', total === 0);
    }
    function setActDisabled(act, disabled) {
      var ab = byId('actionbar');
      if (!ab || !ab.children) return;
      Array.prototype.forEach.call(ab.children, function (b) {
        if (b.getAttribute && b.getAttribute('data-act') === act) b.disabled = !!disabled;
      });
    }
    function setActive(i) {
      if (mode !== 'step' || i < 0 || i >= qs.length) return;
      state.index = i;
      cards.forEach(function (c, idx) {
        if (idx === i) c.node.classList.add('active');
        else c.node.classList.remove('active');
      });
      updateChrome();
      var n = cards[i].node;
      if (n.scrollIntoView) { try { n.scrollIntoView({ block: 'start' }); } catch (e) {} }
    }

    QUIZ = {
      state: state,
      total: qs.length,
      lastCode: '',
      prev: function () { setActive(state.index - 1); },
      next: function () { setActive(state.index + 1); },
      submit: function () { if (mode === 'step' && cards[state.index]) cards[state.index].submit(); },
      finish: finish,
      copy: copyCode
    };

    if (qs.length) {
      var list = el('div', 'q-list ' + (mode === 'grid' ? 'grid-mode' : 'step-mode'));
      qs.forEach(function (q, i) { cards.push(makeCard(q, i)); });
      cards.forEach(function (c) { list.appendChild(c.node); });
      root.appendChild(list);
      if (mode === 'step') setActive(0);
    } else {
      root.appendChild(el('p', 'muted', '本日暂无题目；仍可生成空结果的回传码。'));
    }
    updateChrome();
    return sec;
  }

  /* ---------------- 页面入口 ---------------- */
  function renderIndex(site) {
    var app = byId('app');
    app.appendChild(el('h1', 'page-title', 'Nihongo 80 · 每日学习'));
    app.appendChild(el('p', 'lead',
      '80 天日语学习计划，同时适配 PC 与手机。每天一页：主题 / 真实场景 / 能力目标 / 60 分钟时间块、词汇·语法·汉字卡、阅读听力素材、分步练习与即时判分，最后生成回传码。'));
    app.appendChild(el('div', 'notice',
      '重要：本网站不是学习状态的真源。状态只存在于本地 SQLite（data/state.db）。网页仅做展示、练习、即时判分并生成 NH80R1 回传码；不会向任何服务器发送学习数据，也不会把「读完页面」记为完成。'));
    app.appendChild(el('div', 'notice',
      '手机学习闭环：打开当天页面 → 首次点「试听 / 解锁语音」→ 分步练习（一屏一题）→ 完成生成回传码 → 复制 / 系统分享 / 下载 .txt → 回到 WorkBuddy 会话粘贴导入，或先存备忘录稍后导入。离线仅展示，成绩靠回传码。'));

    var sec = section('80 天进度热力图（课程结构）', true);
    sec._body.appendChild(el('p', 'muted',
      '按天展示课程结构：颜色代表阶段（P1–P6），深浅代表当天题量；当前天有描边。窄屏可横向滚动，PC 保持紧凑。数据来自内嵌 JSON，仅是课程计划，不代表你的掌握进度。'));
    sec._body.appendChild(vizCard('课程结构热力图', heatmapSVG(site, null), 'viz-heat'));
    sec._body.appendChild(phaseLegend());
    app.appendChild(sec);

    var list = section('每日入口', true);
    var grid = el('div', 'day-grid');
    var total = (site.meta && site.meta.days) ? site.meta.days : site.days.length;
    var map = {};
    site.days.forEach(function (x) { map[x.day] = x; });
    for (var i = 1; i <= total; i++) {
      var info = map[i];
      var a = el('a', 'day-tile', '');
      a.href = 'day-' + pad3(i) + '.html';
      a.appendChild(el('span', 'day-tile-n', 'D' + pad3(i)));
      if (info) {
        a.appendChild(el('span', 'day-tile-t', info.theme || ''));
        a.appendChild(el('span', 'day-tile-p', info.phase || ''));
      } else {
        a.appendChild(el('span', 'day-tile-t', '（待生成）'));
        a.classList.add('empty');
      }
      grid.appendChild(a);
    }
    list._body.appendChild(grid);
    app.appendChild(list);
  }
  function renderDay(day, site) {
    var app = byId('app');
    var W = LAYOUT.wide;
    var head = el('div', 'day-head');
    head.appendChild(el('div', 'day-kicker', '第 ' + day.day + ' 天 · ' + (day.phase || '')));
    head.appendChild(el('h1', 'page-title', day.theme || '当日学习'));
    if (day.scene) head.appendChild(el('p', 'scene', '真实场景：' + day.scene));
    if (day.can_do) {
      head.appendChild(el('div', 'banner banner-info cando-card', '本日 Can-do：' + day.can_do));
      if (day.focus && day.focus.length) {
        head.appendChild(el('p', 'muted', '能力侧重：' + day.focus.join(' / ')));
      }
    }
    if (day.assessment && day.assessment !== 'none') {
      head.appendChild(el('span', 'badge', '测评：' + day.assessment));
    }
    app.appendChild(head);

    /* 手机：除练习外默认折叠，避免几十屏滚动；PC 展开更多分区 */
    if (day.objectives && day.objectives.length) {
      var os = section('能力目标', W);
      var ul = el('ul', 'objectives');
      day.objectives.forEach(function (o) { ul.appendChild(el('li', '', o)); });
      os._body.appendChild(ul); app.appendChild(os);
    }

    var ts = section('60 分钟时间块', W);
    ts._body.appendChild(timeBar(day.blocks, day.minutes));
    app.appendChild(ts);

    var vs = section('当日可视化', W);
    var vg = el('div', 'viz-grid');
    vg.appendChild(vizCard('当日结构', dayStructureSVG(day)));
    vg.appendChild(vizCard('80 天进度热力图', heatmapSVG(site, day.day), 'viz-heat'));
    vg.appendChild(vizCard('题型分布', typeDistSVG(day.questions)));
    vs._body.appendChild(vg);
    vs._body.appendChild(phaseLegend());
    app.appendChild(vs);

    if (day.vocab && day.vocab.length) {
      var vsec = section('词汇卡（先自测，再点开看读音与释义）', false);
      vsec._body.appendChild(el('p', 'muted',
        LAYOUT.wide ? '点击卡片翻面查看读音与释义。' : '点击卡片翻面；手机上一次只展开一张，先自测再揭示。'));
      vsec._body.appendChild(cardGrid(day.vocab, vocabCard, !LAYOUT.wide));
      app.appendChild(vsec);
    }
    if (day.grammar && day.grammar.length) {
      var gsec = section('语法卡', false);
      gsec._body.appendChild(cardGrid(day.grammar, grammarCard, false));
      app.appendChild(gsec);
    }
    if (day.kanji && day.kanji.length) {
      var ksec = section('汉字卡（中日差异提示）', false);
      ksec._body.appendChild(cardGrid(day.kanji, kanjiCard, false));
      app.appendChild(ksec);
    }
    if (day.materials && day.materials.length) {
      var msec = section('阅读 / 听力素材', false);
      day.materials.forEach(function (m) { msec._body.appendChild(materialCard(m)); });
      app.appendChild(msec);
    }
    app.appendChild(buildPractice(day));
  }
  function init() {
    detectLayout();
    setupTTSBanner();
    setupChrome();
    var site = readJSON('nh80-site') || { days: [], meta: {} };
    var day = readJSON('nh80-day');
    renderNav(site, day);
    if (day) renderDay(day, site);
    else renderIndex(site);
  }

  /* ---------------- 入口（置于最末，避免 readyState 非 loading 时顶层 var 未初始化） ---------------- */
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
"""


def main(argv):
    ap = argparse.ArgumentParser(
        description="从 curriculum + seeds 生成 Nihongo 80 每日静态页（纯标准库，PC/手机双端）")
    ap.add_argument("--root", default=str(DEFAULT_ROOT),
                    help="项目根目录（其下有 curriculum/ 与 knowledge/seeds/）")
    ap.add_argument("--day", type=int, default=None,
                    help="只生成指定一天（1..N）；默认生成 curriculum 中全部天")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    curriculum_path = root / "curriculum" / "curriculum.json"
    seeds_dir = root / "knowledge" / "seeds"
    curriculum = load_curriculum(curriculum_path)
    tables = load_seeds(seeds_dir)
    all_ids = set()
    for t in tables.values():
        all_ids |= set(t.keys())

    all_days = curriculum["days"]
    max_day = max(d["day"] for d in all_days)
    if args.day is not None:
        if args.day < 1 or args.day > max_day:
            die("--day %d 超出 curriculum 的天数范围 1..%d" % (args.day, max_day))
        target = [d for d in all_days if d["day"] == args.day]
        if not target:
            die("curriculum 中不存在第 %d 天" % args.day)
        target_days = target
    else:
        target_days = list(all_days)
    target_days.sort(key=lambda d: d["day"])

    site = build_site_summary(curriculum)

    web_dir = root / "web"
    data_dir = web_dir / "data"
    assets_dir = web_dir / "assets"
    for p in (web_dir, data_dir, assets_dir):
        p.mkdir(parents=True, exist_ok=True)

    # 共享资产与外壳（始终生成）
    (assets_dir / "app.css").write_text(APP_CSS.lstrip("\n"), encoding="utf-8")
    (assets_dir / "app.js").write_text(APP_JS.lstrip("\n"), encoding="utf-8")
    (web_dir / "404.html").write_text(HTML_404.lstrip("\n"), encoding="utf-8")
    (web_dir / "index.html").write_text(
        render_page("Nihongo 80 · 每日学习", None, site), encoding="utf-8")

    # PWA：manifest / 矢量图标 / 纯原生 Service Worker（版本随真源数据变化）
    build_id = compute_build_id(curriculum_path, seeds_dir)
    all_day_numbers = sorted(d["day"] for d in all_days)
    sw_assets = [
        "index.html", "404.html", "manifest.webmanifest", "icon.svg",
        "assets/app.css", "assets/app.js",
    ]
    for n in all_day_numbers:
        sw_assets.append("day-%03d.html" % n)
    for n in all_day_numbers:
        sw_assets.append("data/day-%03d.json" % n)
    (web_dir / "manifest.webmanifest").write_text(
        MANIFEST_TEMPLATE.lstrip("\n"), encoding="utf-8")
    (web_dir / "icon.svg").write_text(ICON_SVG.lstrip("\n"), encoding="utf-8")
    sw_text = (SW_TEMPLATE
               .replace("@@BUILD_ID@@", build_id)
               .replace("@@ASSETS_JSON@@", json.dumps(sw_assets, ensure_ascii=False)))
    (web_dir / "sw.js").write_text(sw_text.lstrip("\n"), encoding="utf-8")

    generated = []
    for d in target_days:
        day_data = assemble_day(d, tables, all_ids)
        daynum = day_data["day"]
        stem = "day-%03d" % daynum
        (data_dir / (stem + ".json")).write_text(
            json.dumps(day_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        title = "第 %03d 天 · %s | Nihongo 80" % (daynum, day_data["theme"] or "当日学习")
        (web_dir / (stem + ".html")).write_text(
            render_page(title, day_data, site), encoding="utf-8")
        generated.append(stem)

    print("build_site.py: root=%s" % root)
    print("build_site.py: 已生成 %d 个每日页面与数据：%s%s" %
          (len(generated), ", ".join(generated[:6]), " ..." if len(generated) > 6 else ""))
    print("build_site.py: 共享文件：index.html, 404.html, assets/app.css, assets/app.js")
    print("build_site.py: PWA：manifest.webmanifest, icon.svg, sw.js (build=%s, %d 个预缓存条目)"
          % (build_id, len(sw_assets)))


if __name__ == "__main__":
    main(sys.argv[1:])
