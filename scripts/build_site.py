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
import sqlite3
import sys
from datetime import datetime, timezone
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


def load_ko_analogy(root):
    """加载韩语对照资料（knowledge/ko_analogy.json）。
    文件不存在 / 损坏 / 结构异常时一律优雅降级为空，绝不阻断建站（--root 临时目录常无此文件）。"""
    empty = {"grammar": [], "vocab": []}
    p = root / "knowledge" / "ko_analogy.json"
    if not p.is_file():
        return empty
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return empty
    if not isinstance(data, dict):
        return empty
    g, v = data.get("grammar"), data.get("vocab")
    return {
        "grammar": g if isinstance(g, list) else [],
        "vocab": v if isinstance(v, list) else [],
    }


# 只把「日语语法术语」翻译成中文，用于接续说明；不新增、不改写任何语法规则。
_TERM_ZH = {
    "名詞": "名词", "動詞": "动词", "イ形容詞": "い形容词", "ナ形容詞": "な形容词",
    "形容詞": "形容词", "助動詞": "助动词", "助詞": "助词", "副詞": "副词",
    "代名詞": "代名词", "数詞": "数词", "連体詞": "连体词", "接続詞": "接续词",
    "感動詞": "感叹词", "自動詞": "自动词", "他動詞": "他动词",
    "普通形": "简体", "丁寧形": "礼貌体", "辞書形": "辞书形", "連用形": "连用形",
    "連体形": "连体形", "命令形": "命令形", "意志形": "意志形", "仮定形": "假定形",
    "可能形": "可能形", "受身形": "被动形", "使役形": "使役形", "禁止形": "禁止形",
    "文末": "句末", "疑問": "疑问", "否定": "否定", "過去": "过去",
}


def _zh_terms(text):
    s = text or ""
    for k in sorted(_TERM_ZH, key=len, reverse=True):
        s = s.replace(k, _TERM_ZH[k])
    return s


def _sval(x):
    """安全字符串：None / 缺失一律空串。页面据此不渲染该行，绝不出现 undefined。"""
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, bool):
        return "是" if x else "否"
    return str(x)


def _slist(x):
    return x if isinstance(x, list) else []


def assemble_day(d, tables, all_ids, ko):
    """按 REDESIGN_PLAN §4.3 组装某一天 web/data/day-NNN.json。

    把种子里「已有但旧版丢弃」的字段全部带出；所有字段可缺失——缺失即空串/空数组，
    页面据此跳过该行，绝不显示 undefined、绝不编造日语。旧字段（CONTRACTS §9）一个不删。
    """
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

    # 韩语对照索引：grammar 按 G id、vocab 按 V id 匹配；查不到即留空，绝不编造。
    ko_g, ko_v = {}, {}
    for it in _slist(ko.get("grammar")):
        if isinstance(it, dict) and it.get("match") is not None:
            ko_g[_sval(it.get("match"))] = it
    for it in _slist(ko.get("vocab")):
        if isinstance(it, dict) and it.get("match") is not None:
            ko_v[_sval(it.get("match"))] = it

    def ex_pairs(raw):
        """例句：日文 + 中文 + TTS 文本。audio_text 只用于 TTS，不作可见「读音」。"""
        out = []
        for e in _slist(raw):
            if not isinstance(e, dict):
                continue
            ja = _sval(e.get("ja"))
            out.append({
                "ja": ja,
                "zh": _sval(e.get("zh")),
                "audio_text": _sval(e.get("audio_text")) or ja,
            })
        return out

    vocab_out = []
    for v in vs:
        ka = ko_v.get(_sval(v.get("id")), {})
        vocab_out.append({
            "id": _sval(v.get("id")),
            "surface": _sval(v.get("surface")),
            "kana": _sval(v.get("kana")),
            "romaji": _sval(v.get("romaji")),
            "pos": _sval(v.get("pos")),
            "meaning_zh": _sval(v.get("meaning_zh")),
            "jlpt": _sval(v.get("jlpt")),
            "examples": ex_pairs(v.get("examples")),
            "notes_for_zh": _sval(v.get("notes_for_zh")),
            "confusables": _slist(v.get("confusables")),
            "ko": _sval(ka.get("ko")),
            "ko_hint": _sval(ka.get("hint_zh")),
            "caution": _sval(ka.get("caution")),
        })

    grammar_out = []
    for g in gs:
        conn = _sval(g.get("connection"))
        usage = _sval(g.get("usage"))
        meaning = _sval(g.get("meaning_zh"))
        # explanation_zh：只把 meaning + connection(附中文术语) + usage 组合成中文接续说明，
        # 不发明任何新规则。
        parts = []
        if meaning:
            parts.append("意思是「" + meaning + "」")
        if conn:
            parts.append("接续：" + conn + "（中文术语：" + _zh_terms(conn) + "）")
        if usage:
            parts.append("用法：" + usage)
        ka = ko_g.get(_sval(g.get("id")), {})
        exs = ex_pairs(g.get("examples"))
        grammar_out.append({
            "id": _sval(g.get("id")),
            "pattern": _sval(g.get("pattern")),
            "meaning_zh": meaning,
            "connection": conn,
            "example": exs[0]["ja"] if exs else "",
            "usage": usage,
            "explanation_zh": "；".join(parts),
            "common_errors": _slist(g.get("common_errors")),
            "compare": _slist(g.get("compare")),
            "examples": exs,
            "ko": _sval(ka.get("ko")),
            "ko_hint": _sval(ka.get("hint_zh")),
            "caution": _sval(ka.get("caution")),
        })

    kanji_out = []
    for k in ks:
        refs = _slist(k.get("vocab_refs"))
        # 韩语汉字词提示：只有当 vocab_refs 指向的词在 ko_analogy 里查得到才显示。
        ko_hint = ""
        for rid in refs:
            hit = ko_v.get(_sval(rid))
            if hit and _sval(hit.get("ko")):
                ko_hint = ("韩语汉字词可参考：" + _sval(hit.get("ko"))
                           + "。" + _sval(hit.get("hint_zh")))
                break
        # 例词取自 vocab_refs 指向的真实词汇种子（日文 + 假名 + 中文），不编造。
        exs = []
        for rid in refs:
            rv = tables["vocab"].get(_sval(rid))
            if rv:
                exs.append({
                    "ja": _sval(rv.get("surface")),
                    "kana": _sval(rv.get("kana")),
                    "zh": _sval(rv.get("meaning_zh")),
                })
            if len(exs) >= 4:
                break
        kanji_out.append({
            "id": _sval(k.get("id")),
            "char": _sval(k.get("char")),
            "onyomi": _slist(k.get("onyomi")),
            "kunyomi": _slist(k.get("kunyomi")),
            "meaning_zh": _sval(k.get("meaning_zh")),
            "zh_trap": _sval(k.get("zh_trap")),
            "vocab_refs": refs,
            "examples": exs,
            "ko_hint": ko_hint,
        })

    questions_out = [{
        "id": _sval(q.get("id")),
        "type": _sval(q.get("type")),
        "prompt_ja": _sval(q.get("prompt_ja")),
        "prompt_zh": _sval(q.get("prompt_zh")),
        "options": _slist(q.get("options")),
        "answer": _sval(q.get("answer")),
        "rationale": _sval(q.get("rationale")),
        "audio_text": _sval(q.get("audio_text")),
        "rubric": _sval(q.get("rubric")),
        "expected_production": _sval(q.get("expected_production")),
        "difficulty": q.get("difficulty") or 0,
    } for q in qs]

    materials_out = []
    for m in ms:
        text_ja = _sval(m.get("text_ja"))
        materials_out.append({
            "id": _sval(m.get("id")),
            "kind": _sval(m.get("kind")),
            "title": _sval(m.get("title")),
            "text_ja": text_ja,
            # text_kana 为空时页面不显示假名行；audio_text 只用于 TTS，不作为可见读音。
            "text_kana": _sval(m.get("text_kana")),
            "text_zh": _sval(m.get("text_zh")),
            "focus_zh": _sval(m.get("focus_zh")),
            "audio_text": _sval(m.get("audio_text")) or text_ja,
            "url": _sval(m.get("url")),
            "license": _sval(m.get("license")),
        })

    viz = {
        "day": daynum,
        "phase": d.get("phase", ""),
        "new_count": len(vs) + len(gs) + len(ks),
        "review_count": len(d.get("review_knowledge_ids") or []),
        "question_count": len(qs),
    }

    # 只嵌入当天用得上的对照，避免把 85+57 条全量塞进 80 个页面（约 7MB）
    _gids = {x["id"] for x in grammar_out}
    _vids = {x["id"] for x in vocab_out}
    ko_g = [e for e in _slist(ko.get("grammar")) if e.get("match") in _gids]
    ko_v = [e for e in _slist(ko.get("vocab")) if e.get("match") in _vids]

    return {
        "day": daynum,
        "phase": d.get("phase", ""),
        "theme": d.get("theme", ""),
        "scene": d.get("scene", ""),
        "scene_tag": d.get("scene_tag", ""),
        # v4：场景主题与对齐标记，供页面显示「今天场景 / 素材是否同主题」
        "scene_topic_key": d.get("scene_topic_key", ""),
        "scene_topic": d.get("scene_topic", ""),
        "topic_match": d.get("topic_match", ""),
        "material_topic_keys": d.get("material_topic_keys") or [],
        "material_pair": d.get("material_pair", ""),
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
        # ---- v3 新增（REDESIGN_PLAN §4.3），缺失一律空数组，页面优雅降级 ----
        "lesson_core": d.get("lesson_core") if isinstance(d.get("lesson_core"), list) else [],
        "review_plan": d.get("review_plan") if isinstance(d.get("review_plan"), list) else [],
        "teaching_notes": d.get("teaching_notes") if isinstance(d.get("teaching_notes"), list) else [],
        "ko_analogy": {"grammar": ko_g, "vocab": ko_v},
    }


def _parse_iso(s):
    """容错解析 state.db / FSRS 的 ISO 时间；无法解析返回 None。"""
    if not s:
        return None
    try:
        v = str(s).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_review_context(root):
    """只读打开 data/state.db，读出 FSRS 到期卡与聚合掌握状态。

    数据库不存在、无法打开或表结构还是旧版时一律返回 None：建站继续，
    页面退回「预习建议」，绝不让网页构建依赖学习状态。
    """
    db = root / "data" / "state.db"
    if not db.is_file():
        return None
    try:
        uri = "file:%s?mode=ro" % str(db).replace("\\", "/")
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            cards = [dict(r) for r in conn.execute(
                "SELECT knowledge_id,due,stability,stage FROM fsrs_cards ORDER BY due").fetchall()]
            ks = {r["knowledge_id"]: dict(r) for r in conn.execute(
                "SELECT knowledge_id,stage FROM knowledge_state").fetchall()}
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        return None
    return {"cards": cards, "ks": ks, "now": _now_iso()}


def _knowledge_index(tables):
    """kid → 页面展示所需的最小字段（surface / kana / zh / 默认能力）。"""
    idx = {}
    for v in tables.get("vocab", {}).values():
        idx[str(v.get("id"))] = {
            "surface": _sval(v.get("surface")), "kana": _sval(v.get("kana")),
            "zh": _sval(v.get("meaning_zh")), "capability": "meaning",
        }
    for g in tables.get("grammar", {}).values():
        idx[str(g.get("id"))] = {
            "surface": _sval(g.get("pattern")), "kana": "",
            "zh": _sval(g.get("meaning_zh")), "capability": "usage",
        }
    for k in tables.get("kanji", {}).values():
        idx[str(k.get("id"))] = {
            "surface": _sval(k.get("char")), "kana": "",
            "zh": _sval(k.get("meaning_zh")), "capability": "reading",
        }
    return idx


def _card_due_map(ctx, kid):
    """同一 kid 可能有多张能力卡；取最早到期的一张，用于 next_hint 反算。"""
    best = None
    for c in (ctx or {}).get("cards", []):
        key = str(c.get("knowledge_id") or "")
        base = key.split("|", 1)[0]
        if base != kid:
            continue
        dt = _parse_iso(c.get("due"))
        if dt and (best is None or dt < best):
            best = dt
    return best


def build_review(daynum, day_data, ctx, idx):
    """REVISION_CONTRACT §4：review.source / due / planned 三件套。

    due 是真实 FSRS 到期卡（含 due / overdue_days / capability / stage）；
    planned 是旧 review_plan，逐条标 planned_only，不再冒充「今天该复习」。
    """
    planned = []
    for p in (day_data.get("review_plan") or []):
        if not isinstance(p, dict):
            continue
        q = dict(p)
        q["planned_only"] = True
        kid = _sval(q.get("kid"))
        due_dt = _card_due_map(ctx, kid) if kid else None
        if due_dt:
            now = _parse_iso(ctx.get("now")) or datetime.now(timezone.utc)
            days = (due_dt - now).days
            if days <= 0:
                q["next_hint_zh"] = "已到 FSRS 到期时间（具体日期 %s），以到期队列为准" % due_dt.date().isoformat()
            else:
                q["next_hint_zh"] = "大约 Day %d 再回顾（具体到期 %s）" % (
                    daynum + days, due_dt.date().isoformat())
        planned.append(q)

    due = []
    if ctx:
        now = _parse_iso(ctx.get("now")) or datetime.now(timezone.utc)
        for c in ctx["cards"]:
            dt = _parse_iso(c.get("due"))
            if not dt or dt > now:
                continue
            key = str(c.get("knowledge_id") or "")
            kid, _, cap = key.partition("|")
            info = idx.get(kid, {})
            if not info:
                continue   # 种子里查不到的知识点不编造展示
            ks = (ctx.get("ks") or {}).get(kid) or {}
            due.append({
                "kid": kid,
                "capability": cap or info.get("capability") or "meaning",
                "surface": info.get("surface", ""),
                "kana": info.get("kana", ""),
                "zh": info.get("zh", ""),
                "due": str(c.get("due") or ""),
                "overdue_days": max(0, (now - dt).days),
                "stage": c.get("stage") or ks.get("stage") or "unseen",
                "card_key": key,
            })
    return {
        "source": "fsrs" if due else "planned",
        "generated_at": (ctx or {}).get("now") or _now_iso(),
        "due": due,
        "planned": planned,
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
      今天学的内容都存在本地；做完练习把结果带回 WorkBuddy 会话就行。
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
      /* 缓存未命中时先走网络，成功后补进缓存；真的断网才回 503。 */
      return fetch(req).then(function (res) {
        if (res && res.ok && res.type === 'basic') {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); }).catch(function () {});
        }
        return res;
      }).catch(function () {
        return new Response('离线：该资源未缓存', {
          status: 503, statusText: 'Offline',
          headers: { 'content-type': 'text/plain; charset=utf-8' }
        });
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
  padding-bottom:calc(16px + var(--sa-b));
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
/* v3：假名一律常显，绝不因「检测到 ja-JP 语音」而隐藏（修掉旧网 bug）。 */
.front-kana{display:block;font-size:13px;color:var(--muted);font-weight:400;margin-top:6px}
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

/* ===== v3：从「系统报表」改回「一课教材」的常显区块（首屏即可学） ===== */
.block{border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);
  margin:10px 0;padding:10px 12px}
.block-title{font-size:18px;margin:2px 0;line-height:1.35;font-weight:700}
.block-hint{font-size:12.5px;color:var(--muted);margin:2px 0 8px;line-height:1.5}
.sub-title{font-weight:700;font-size:13px;color:var(--ink-2);margin:6px 0 4px}
.tts-fallback-hint{display:none;background:var(--warn-weak);color:var(--warn);
  border-left:4px solid var(--warn);padding:6px 8px;border-radius:6px;
  font-size:12px;line-height:1.5;margin:4px 0 8px}
body.no-ja-tts .tts-fallback-hint{display:block}
.listen-wrap{display:inline-flex;flex-direction:column;align-items:flex-start;gap:2px;vertical-align:middle}
button.listen-btn{min-height:34px;padding:3px 10px;font-size:12.5px;line-height:1.2;white-space:nowrap}
.inline-notice{font-size:11.5px;color:var(--warn);line-height:1.4;max-width:230px}

/* ① 今天要会的 3 句话 */
.core-sentence{display:flex;gap:8px;align-items:flex-start;border:1px solid var(--line);
  border-radius:8px;background:var(--surface-2);padding:7px 9px;margin:6px 0}
.core-main{flex:1 1 auto;min-width:0}
.core-ja{font-size:22px;font-weight:700;line-height:1.4;word-break:normal;overflow-wrap:anywhere}
.core-kana{font-size:13px;color:var(--accent);line-height:1.5}
.core-zh{font-size:14.5px;color:var(--ink);line-height:1.5}
.core-note{font-size:12px;color:var(--muted);line-height:1.45;margin-top:2px}
.core-side{flex:0 0 auto;display:flex;flex-direction:column;align-items:flex-end;gap:4px}
.core-no{font-size:11px;color:var(--muted)}

/* ② 单词：常显、不折叠、不翻面，假名常显 */
.vlist{display:grid;grid-template-columns:1fr;gap:8px;margin:8px 0}
.vcard{border:1px solid var(--line);border-radius:8px;background:var(--surface-2);
  padding:8px 10px;font-size:13px;min-width:0}
.vcard-top{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.v-surface{font-size:25px;font-weight:700;line-height:1.3}
.v-kana{font-size:15px;color:var(--accent);font-weight:600}
.v-meta{display:flex;flex-wrap:wrap;gap:4px 8px;margin:3px 0}
.v-tag{font-size:11.5px;color:var(--muted);background:var(--surface-3);
  padding:1px 7px;border-radius:4px}
.v-meaning{font-size:14px;margin:3px 0;line-height:1.5}
.v-ex{border-left:3px solid var(--accent-weak);padding:2px 0 2px 8px;margin:4px 0}
.v-ex-ja{font-size:14px;line-height:1.5;word-break:normal;overflow-wrap:anywhere}
.v-ex-zh{font-size:12.5px;color:var(--ink-2);line-height:1.4}
.note-zh{background:var(--warn-weak);border-left:3px solid var(--warn);padding:5px 8px;
  border-radius:6px;font-size:12.5px;margin:5px 0;line-height:1.5}
.ko-box{background:var(--surface-3);border:1px dashed var(--line);border-radius:6px;
  padding:6px 8px;margin:5px 0;font-size:12.5px;line-height:1.5}
.ko-title{font-weight:700;color:var(--accent);font-size:12.5px;margin-bottom:2px}
.ko-line{color:var(--ink);line-height:1.5}
.ko-hint{color:var(--ink-2);line-height:1.5;margin-top:2px}
.ko-caution{color:var(--bad);line-height:1.5;margin-top:3px;font-weight:600}

/* ③ 语法 */
.gcard{border:1px solid var(--line);border-radius:8px;background:var(--surface-2);
  padding:9px 10px;margin:8px 0;font-size:13.5px}
.g-pattern{font-size:19px;font-weight:700;line-height:1.4;color:var(--ink)}
.g-expl{background:var(--accent-weak);border-radius:6px;padding:6px 8px;
  margin:5px 0;font-size:13px;line-height:1.6}
.g-exs,.err-box,.cmp-box{margin:6px 0}
.g-ex{display:flex;gap:8px;align-items:center;flex-wrap:wrap;border-bottom:1px dashed var(--line);
  padding:4px 0;font-size:14px}
.g-ex-ja{font-weight:600}
.g-ex-zh{color:var(--ink-2);font-size:13px}
.err-item,.cmp-item{font-size:13px;line-height:1.6;padding-left:6px;margin:3px 0}

/* ④ 汉字 */
.klist{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin:8px 0}
.kcard{border:1px solid var(--line);border-radius:8px;background:var(--surface-2);
  padding:8px 10px;font-size:13px}
.k-char{font-size:34px;font-weight:700;line-height:1.2}
.k-mean{font-size:13px;color:var(--ink-2)}
.k-ex{font-size:13px;line-height:1.6;margin:2px 0;word-break:normal;overflow-wrap:anywhere}
.k-ex-kana{color:var(--accent);font-size:12px}
.k-note{font-size:12px;color:var(--good);margin:5px 0}

/* ⑤ 例句 / 会话 */
.material .ja-text{font-size:18px;line-height:1.9}
.m-zh{font-size:14px;color:var(--ink-2);line-height:1.6;margin:4px 0}
.material .note-zh{margin-top:8px}

/* ⑥ 练习 */
.demo-box{background:var(--good-weak);border-radius:6px;padding:8px 10px;margin:8px 0}
.demo-title{font-weight:700;font-size:13px;margin-bottom:4px;color:var(--good)}
.demo-ja{font-size:16px;line-height:1.7;word-break:normal;overflow-wrap:anywhere}
.feedback-zh{background:var(--accent-weak);border-radius:6px;padding:6px 9px;
  margin:8px 0;font-size:13px;line-height:1.6}
.self-assess-note{font-size:12px;color:var(--muted)}

/* ⑦ 今日复习 */
.review-disclaimer{background:var(--accent-weak);border-radius:6px;padding:7px 9px;
  font-size:12.5px;line-height:1.6;margin:4px 0 8px}
.review-count,.review-empty,.review-new,.review-why{font-size:13.5px;line-height:1.6;margin:4px 0}
.review-item{border:1px solid var(--line);border-radius:8px;background:var(--surface-2);
  padding:8px 10px;margin:7px 0}
.review-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.review-no{color:var(--muted);font-size:12px}
.review-surface{font-size:20px;font-weight:700}
.review-kana{font-size:14px;color:var(--accent)}
.review-ans{margin:5px 0;font-size:14px}
.review-zh{color:var(--ink);font-weight:600}
.review-reason,.review-next{font-size:12.5px;color:var(--ink-2);line-height:1.5;margin:2px 0}
.review-next{color:var(--accent)}
.rating-btns{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:6px}
.rating-label{font-size:12.5px;color:var(--muted)}
button.rate-btn{min-height:34px;font-size:12.5px;padding:3px 10px}
button.rate-btn.sel{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}

/* ⑧ 页尾折叠：给老师 / 系统 */
.teacher{margin:16px 0;border:1px solid var(--line);border-radius:var(--radius);
  background:var(--surface-2)}
.teacher > .section-sum{background:var(--surface-3)}
.teacher .section{margin:8px 0}
.teacher-lead{font-size:12.5px;color:var(--muted);margin:2px 0 8px}

@media (min-width:900px){
  .vlist{grid-template-columns:repeat(2,minmax(0,1fr))}
  .block{padding:12px 16px}
  .core-ja{font-size:24px}
}

/* 手机：隐藏底部「考试感」操作栏（上方练习区已有提交/查看全部），
   并整体压缩首屏，让 3 句话 + 至少 2 张完整词卡落在首屏内。 */
@media (max-width:899px){
  .actionbar{display:none}
  .day-head .page-title{font-size:19px;margin:2px 0}
  .day-head .lead{font-size:12.5px;line-height:1.45;margin:2px 0}
  .block{padding:8px 10px;margin:8px 0}
  .block-title{font-size:16px}
  .block-hint{font-size:11.5px;line-height:1.4;margin:2px 0 6px}
  .tts-fallback-hint{font-size:11px;padding:4px 6px;margin:3px 0 6px;line-height:1.35}
  .core-sentence{padding:4px 6px;margin:3px 0}
  .core-main{display:flex;flex-wrap:wrap;align-items:baseline;gap:1px 8px}
  .core-ja{font-size:17px}
  .core-zh{font-size:12.5px;line-height:1.4}
  .core-kana{font-size:11.5px}
  .core-no{font-size:10px}
  button.listen-btn{min-height:30px;font-size:11px;padding:2px 7px}
  /* 手机单列：词卡含例句 / 中文易错 / 韩语对照，双列会把中文压成窄条，可读性优先。 */
  .vlist{grid-template-columns:1fr}
  .vcard{padding:9px 11px}
  .vcard-top{gap:6px}
  .v-surface{font-size:21px}
  .v-kana{font-size:14px}
  .v-tag{font-size:10px;padding:1px 5px}
  .v-meta{gap:2px 7px;margin:3px 0}
  .v-meaning{font-size:14px;margin:3px 0;line-height:1.5}
  .v-ex{margin:3px 0;padding:2px 0 2px 7px}
  .v-ex-ja{font-size:14px;line-height:1.5}
  .v-ex-zh{font-size:13px;line-height:1.45}
  .note-zh{font-size:12.5px;padding:5px 7px;margin:3px 0;line-height:1.5}
  .ko-box{font-size:12.5px;padding:5px 7px;margin:3px 0;line-height:1.5}
  .ko-title{font-size:12px}
  .sub-title{font-size:13px;margin:5px 0 4px}
  .gcard,.kcard,.review-item,.material{padding:7px 8px}
  .g-pattern{font-size:17px}
  .g-expl{font-size:12px;padding:5px 6px}
  .g-ex-ja{font-size:13px}
  .g-ex-zh{font-size:11.5px}
  .err-item,.cmp-item{font-size:11.5px;line-height:1.45}
  .ja-text{font-size:16px}
  .review-disclaimer{font-size:11px;padding:5px 7px}
  button.rate-btn{min-height:30px;font-size:11px;padding:2px 8px}
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
  function t(v) { return (v === undefined || v === null) ? '' : String(v); }

  /* 词性 / 题型 / 评估标签中文化（首屏不出现英文黑话）。 */
  var POS_ZH = {
    '名詞': '名词', '代名詞': '代名词', '動詞': '动词', '形容詞': '形容词',
    '助動詞': '助动词', '助詞': '助词', '副詞': '副词', '数詞': '数词',
    '感動詞': '感叹词', '連体詞': '连体词', '接続詞': '接续词',
    '接尾辞': '接尾辞', '接頭辞': '接头辞'
  };
  function zhPos(s) {
    var out = t(s);
    Object.keys(POS_ZH).forEach(function (k) { out = out.split(k).join(POS_ZH[k]); });
    return out;
  }
  var QTYPE_ZH = {
    mcq: '选择题', fill: '填空题', listen: '听写题', read: '阅读题',
    reorder: '排序题', error_correct: '改错题', translate: '翻译题',
    free_production: '自由表达', dialogue: '对话题'
  };
  function qTypeZh(s) { return QTYPE_ZH[t(s)] || (t(s) ? t(s) : '练习题'); }
  var ASSESS_ZH = {
    diagnostic: '摸底（不计分，只用来定起点）', weekly: '每周小测',
    stage: '阶段测', midterm: '中期测', n3_readiness: 'N3 水平摸底',
    final: '结课测', none: '无'
  };
  function assessmentZh(s) { return ASSESS_ZH[t(s)] || t(s); }

  /* 有值才渲染该行；缺失字段一律跳过，页面绝不出现 undefined。 */
  function lineIf(parent, label, value, cls) {
    if (value === undefined || value === null || value === '') return null;
    var p = el('div', 'kv');
    if (label) p.appendChild(el('span', 'kv-k', label));
    p.appendChild(el('span', 'kv-v' + (cls ? ' ' + cls : ''), value));
    parent.appendChild(p);
    return p;
  }

  /* 每个词 / 每句 / 每段旁的「听」入口：用户手势内解锁 + 朗读，自带降级提示节点。 */
  function listenBtn(text, label) {
    var wrap = el('span', 'listen-wrap');
    var b = el('button', 'btn btn-mini listen-btn', label || '听');
    b.type = 'button';
    var notice = el('span', 'inline-notice');
    notice.hidden = true;
    b.addEventListener('click', function () { primeTTS(); speak(text || '', notice); });
    wrap.appendChild(b);
    wrap.appendChild(notice);
    return wrap;
  }

  /* 常显区块（非折叠）：标题 + 一句中文引导。 */
  function sectionPlain(title, hint) {
    var box = el('section', 'block');
    box.appendChild(el('h2', 'block-title', title));
    if (hint) box.appendChild(el('p', 'block-hint', hint));
    return box;
  }
  function readJSON(id) {
    var n = byId(id);
    if (!n) return null;
    try { return JSON.parse(n.textContent); } catch (e) { return null; }
  }
  function pad2(n) { return String(n).padStart(2, '0'); }
  function pad3(n) { return String(n).padStart(3, '0'); }
  /* 与 scripts/learning.py 的 norm_answer() 保持同构（REVISION_CONTRACT §3.2）：
     NFKC 归一 → 去所有空白（含全角空格）→ ，转 , → 去句末 。．.！!？?。
     判分只做「等价形式」归一，不做语义猜测。 */
  function norm(s) {
    var v = String(s === undefined || s === null ? '' : s);
    if (v.normalize) { try { v = v.normalize('NFKC'); } catch (e) {} }
    v = v.replace(/[\s\u3000]+/g, '').replace(/，/g, ',');
    return v.replace(/[。．.！!？?]+$/, '');
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
      /* 已揭示答案 = 放弃独立回忆；hinted 只能上调，不能被前端回退（契约 §3.1）。 */
      var revealed = !!r.revealed_before_submit;
      var o = {
        qid: r.qid, answer: r.answer, correct: !!r.correct,
        hinted: !!(r.hinted || revealed),
        revealed_before_submit: revealed,
        pre_reveal_answer: (r.pre_reveal_answer === undefined || r.pre_reveal_answer === null)
          ? '' : String(r.pre_reveal_answer),
        seconds: Math.max(0, Math.round(r.seconds || 0)), error_type: r.error_type || null
      };
      if (revealed && r.revealed_at) o.revealed_at = r.revealed_at;
      /* 开放题自评写独立字段，绝不冒充 correct / 掌握判定（REDESIGN §5、P0-9）。 */
      if (r.self_assessed) o.self_assessed = r.self_assessed;
      return o;
    });
    var total = results.reduce(function (a, r) { return a + r.seconds; }, 0);
    /* 复习三档自评单独成数组，绝不写进 results[].correct（REDESIGN §4.3 / §5）。
       import-web-result 只读取它认识的字段，新增顶层字段完全向后兼容。 */
    var rr = state.reviewRatings || {};
    var review_ratings = Object.keys(rr).map(function (kid) {
      return { kid: kid, rating: rr[kid] };
    });
    return {
      v: 1, day: state.day, session: state.session, ts: localISO(),
      results: results, minutes: Math.max(1, Math.round(total / 60)), source: 'web',
      review_ratings: review_ratings
    };
  }


  /* 可选云端同步：只发原始作答事件，不发 correct；失败静默，回传码仍是唯一兜底。
     服务端（Worker）会用 answer-key.json 重新判分，网页永远不是判分权威。 */
  function autoSync(payload) {
    try {
      if (typeof fetch !== 'function' || typeof location === 'undefined') return;
      if (location.protocol !== 'http:' && location.protocol !== 'https:') return;
      if (typeof navigator !== 'undefined' && navigator.onLine === false) return;
      if (!payload || (!(payload.results || []).length && !(payload.review_ratings || []).length)) return;
      var body = JSON.stringify({
        v: 1, day: payload.day, session: payload.session, minutes: payload.minutes,
        client_ts: payload.ts,
        results: (payload.results || []).map(function (r) {
          return { qid: r.qid, answer: r.answer, hinted: !!r.hinted,
                   revealed_before_submit: !!r.revealed_before_submit, seconds: r.seconds || 0 };
        })
      });
      fetch('/api/events', { method: 'POST', headers: { 'content-type': 'application/json' },
                             body: body, keepalive: true })
        .then(function (res) { globalThis.NH80.lastSync = res && res.ok ? 'ok' : 'skipped'; })
        .catch(function () { globalThis.NH80.lastSync = 'offline'; });
    } catch (e) { /* 同步不是学习的前置条件，任何异常都不影响回传码 */ }
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
  var TEACHER_BOX = null;                       // 页尾折叠「给老师/系统」容器，完成回传码时打开

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
      side.textContent = TTS.jaVoice
        ? '发音：点句子旁的「听」跟读一遍。'
        : '发音：这台设备没有日语语音，看假名跟读即可，不影响今天的学习。';
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
        ? '离线也能看今天的内容；做完的练习记得带回 WorkBuddy 会话。'
        : '当前离线：内容已缓存，练习结果稍后带回 WorkBuddy 会话。';
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

  /* 揭示答案 / 提示都属于「放弃独立回忆」，只允许向上写，不允许回退（契约 §3.1）。 */
  var REVEAL_NOTICE = '本次为提示学习，不计为独立回忆';
  var REVEAL_SUBMIT_LABEL = '提交（已看答案，记为提示学习）';

  function markRevealed(r, preAnswer, full) {
    r.hinted = true;
    if (full) r.revealed_before_submit = true;
    if (!r.revealed_at) r.revealed_at = Date.now();
    if (r.pre_reveal_answer === undefined || r.pre_reveal_answer === null) {
      r.pre_reveal_answer = String(preAnswer === undefined || preAnswer === null ? '' : preAnswer);
    }
    return r;
  }
  function revealNoticeNode() {
    return el('div', 'reveal-notice', REVEAL_NOTICE);
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
      autoSync(payload);
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
      if (r && r.revealed_before_submit) box.appendChild(revealNoticeNode());
      var badge = el('span', 'badge badge-good', '答对');
      if (r && r._graded) {
        badge = r.correct
          ? el('span', 'badge badge-good', '答对')
          : el('span', 'badge badge-bad', '未答对 / 待复核');
        box.appendChild(badge);
      }
      box.appendChild(el('div', 'reveal-row', '你的答案：' + (r && r.answer ? r.answer : '（空）')));
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
      var showAns = el('button', 'btn', '看答案 / 解析');
      showAns.type = 'button';
      var submit = el('button', 'btn btn-primary q-submit', '提交答案');
      submit.type = 'button';
      actionRow.appendChild(showAns); actionRow.appendChild(submit);
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
        markRevealed(r, getValue ? getValue() : r.answer, false);
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
        /* 已揭示 / 已提示后提交，hinted 只能保持 true，不能回退（契约 §3.1）。 */
        r.hinted = !!(r.hinted || r.revealed_before_submit);
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
      showAns.addEventListener('click', function () {
        var r = state.results[q.id];
        if (!r) {
          r = { qid: q.id, answer: getValue(), correct: false, hinted: true,
                seconds: elapsed(q.id), error_type: null };
          state.results[q.id] = r;
        }
        markRevealed(r, getValue(), true);
        save();
        reveal.hidden = false;
        showReveal(q, r, reveal, updateChrome);
        if (!r._graded) submit.textContent = REVEAL_SUBMIT_LABEL;
      });
      submit.addEventListener('click', doSubmit);

      var existing = state.results[q.id];
      if (existing) {
        if (setValue) setValue(existing.answer);
        submit.disabled = true;
        showReveal(q, existing, reveal, updateChrome);
        paintStatus(existing);
        if (existing.hinted) { hintBox.hidden = false; hintBox.textContent = hintText(q); }
        if (existing.revealed_before_submit) submit.textContent = REVEAL_SUBMIT_LABEL;
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

  /* ================= v3：一课教材的 8 个区块（首屏即可学） ================= */

  /* ① 今天要会的 3 句话：日文大字 + 假名（有才显示，不伪造）+ 中文 + 中文提示 + 听。 */
  function renderLessonCore(day) {
    var core = day.lesson_core || [];
    var box = sectionPlain('今天要会的 3 句话',
      '点「听」听发音，没声音就照着假名跟读。');
    if (!core.length) {
      box.appendChild(el('p', 'muted', '（今天暂时没有可展示的句子，先看下面的单词。）'));
      return box;
    }
    core.forEach(function (s, i) {
      var card = el('div', 'core-sentence');
      var main = el('div', 'core-main');
      main.appendChild(el('div', 'core-ja', t(s.ja)));
      if (t(s.kana)) main.appendChild(el('div', 'core-kana', s.kana));  // 有才显示，不伪造
      main.appendChild(el('div', 'core-zh', t(s.zh)));
      /* lesson_core[].note_zh 由课程层生成、未必与本句对应，故不逐句渲染；
         中文难点统一放到语法区「今日难点」常显，避免错配与首屏拥挤。 */
      var side = el('div', 'core-side');
      side.appendChild(listenBtn(t(s.audio_text) || t(s.ja), '听这句'));
      card.appendChild(main); card.appendChild(side);
      box.appendChild(card);
    });
    return box;
  }

  /* ② 单词：常显、不折叠、不翻面；假名常显；全字段 + 韩语对照 + 易错提示。 */
  function renderVocabBlock(day) {
    var vs = day.vocab || [];
    var box = sectionPlain('单词',
      '每个词都常显：先读假名、听发音，再看中文意思、例句、中文易错点和韩语对照。');
    var list = el('div', 'vlist');
    vs.forEach(function (v) {
      var c = el('div', 'vcard');
      var top = el('div', 'vcard-top');
      top.appendChild(el('span', 'v-surface', t(v.surface)));
      if (t(v.kana)) top.appendChild(el('span', 'v-kana', v.kana));
      top.appendChild(listenBtn(t(v.surface) || t(v.kana), '听这个词'));
      c.appendChild(top);
      var meta = el('div', 'v-meta');
      if (t(v.romaji)) meta.appendChild(el('span', 'v-tag', '罗马字 ' + v.romaji));
      if (t(v.pos)) meta.appendChild(el('span', 'v-tag', '词性 ' + zhPos(v.pos)));
      if (t(v.jlpt)) meta.appendChild(el('span', 'v-tag', 'JLPT ' + v.jlpt));
      if (meta.children.length) c.appendChild(meta);
      if (t(v.meaning_zh)) c.appendChild(el('div', 'v-meaning', '中文：' + v.meaning_zh));
      var exLimit = LAYOUT.wide ? 2 : 1;   // 手机更紧凑：每卡 1 例句，PC 最多 2 例句
      (v.examples || []).slice(0, exLimit).forEach(function (e) {
        var ex = el('div', 'v-ex');
        ex.appendChild(el('div', 'v-ex-ja', t(e.ja)));
        if (t(e.zh)) ex.appendChild(el('div', 'v-ex-zh', e.zh));
        ex.appendChild(listenBtn(t(e.audio_text) || t(e.ja), '听'));
        c.appendChild(ex);
      });
      if (t(v.notes_for_zh)) c.appendChild(el('div', 'note-zh', '中文易错：' + v.notes_for_zh));
      if (t(v.ko) || t(v.ko_hint) || t(v.caution)) {
        var kb = el('div', 'ko-box');
        kb.appendChild(el('div', 'ko-title', '韩语对照（结构可以借，词不能猜）'));
        if (t(v.ko)) kb.appendChild(el('div', 'ko-line', '可以对照：' + v.ko));
        if (t(v.ko_hint)) kb.appendChild(el('div', 'ko-hint', v.ko_hint));
        if (t(v.caution)) kb.appendChild(el('div', 'ko-caution', '必须验证 / 不等价：' + v.caution));
        c.appendChild(kb);
      }
      list.appendChild(c);
    });
    if (!vs.length) box.appendChild(el('p', 'muted', '（今天没有新词）'));
    box.appendChild(list);
    return box;
  }

  /* ③ 语法：中文意思 / 中文接续说明 / 例句 / 使用场景 / 易错点 / 相近语法 / 韩语对照。 */
  function renderGrammarBlock(day) {
    var gs = day.grammar || [];
    var box = sectionPlain('语法',
      '用中文讲清楚：什么意思、怎么接续、怎么用、容易错在哪，再对照韩语。');
    gs.forEach(function (g) {
      var c = el('div', 'gcard');
      c.appendChild(el('div', 'g-pattern', t(g.pattern)));
      if (t(g.meaning_zh)) lineIf(c, '意思', g.meaning_zh);
      if (t(g.explanation_zh)) c.appendChild(el('div', 'g-expl', '中文接续说明：' + g.explanation_zh));
      else if (t(g.connection)) lineIf(c, '接续', g.connection);
      if (t(g.usage)) lineIf(c, '使用场景', g.usage);
      var exs = g.examples || [];
      if (exs.length) {
        var ebox = el('div', 'g-exs');
        ebox.appendChild(el('div', 'sub-title', '例句（点「听」跟读）'));
        exs.slice(0, 3).forEach(function (e) {
          var ex = el('div', 'g-ex');
          ex.appendChild(el('span', 'g-ex-ja', t(e.ja)));
          if (t(e.zh)) ex.appendChild(el('span', 'g-ex-zh', e.zh));
          ex.appendChild(listenBtn(t(e.audio_text) || t(e.ja), '听'));
          ebox.appendChild(ex);
        });
        c.appendChild(ebox);
      }
      var errs = g.common_errors || [];
      if (errs.length) {
        var eb = el('div', 'err-box');
        eb.appendChild(el('div', 'sub-title', '易错点（中文）'));
        errs.forEach(function (e, k) {
          var s2 = (k + 1) + '. ' + t(e.why || '');
          if (t(e.wrong) || t(e.fix)) {
            s2 += '（';
            if (t(e.wrong)) s2 += '常见错例：' + e.wrong;
            if (t(e.fix)) s2 += (t(e.wrong) ? '；正确：' : '正确：') + e.fix;
            s2 += '）';
          }
          eb.appendChild(el('div', 'err-item', s2));
        });
        c.appendChild(eb);
      }
      var cmp = g.compare || [];
      if (cmp.length) {
        var cb = el('div', 'cmp-box');
        cb.appendChild(el('div', 'sub-title', '与相近语法的区别'));
        cmp.forEach(function (x) {
          /* 只给中文区别，不展示内部 G 编号。 */
          cb.appendChild(el('div', 'cmp-item', t(x.diff)));
        });
        c.appendChild(cb);
      }
      if (t(g.ko) || t(g.ko_hint) || t(g.caution)) {
        var kb = el('div', 'ko-box');
        kb.appendChild(el('div', 'ko-title', '韩语对照（结构可以借，词不能猜）'));
        if (t(g.ko)) kb.appendChild(el('div', 'ko-line', '可以对照：' + g.ko));
        if (t(g.ko_hint)) kb.appendChild(el('div', 'ko-hint', g.ko_hint));
        if (t(g.caution)) kb.appendChild(el('div', 'ko-caution', '必须验证 / 不等价：' + g.caution));
        c.appendChild(kb);
      }
      box.appendChild(c);
    });
    if (!gs.length) box.appendChild(el('p', 'muted', '（今天没有新语法）'));
    /* 课程层 teaching_notes（中文难点讲解）在学习区常显，不藏到提交后。 */
    var notes = day.teaching_notes || [];
    if (notes.length) {
      var nb = el('div', 'note-zh');
      nb.appendChild(el('div', 'sub-title', '今日难点（中文讲解）'));
      notes.forEach(function (n) { nb.appendChild(el('div', '', t(n))); });
      box.appendChild(nb);
    }
    return box;
  }

  /* ④ 汉字：音读 / 训读 / 例词 / 中文陷阱，明写不要求抄写。 */
  function renderKanjiBlock(day) {
    var ks = day.kanji || [];
    var box = sectionPlain('汉字', '会认、会读、能在词里读出来即可，不要求机械抄写。');
    var list = el('div', 'klist');
    ks.forEach(function (k) {
      var c = el('div', 'kcard');
      c.appendChild(el('div', 'k-char', t(k.char)));
      if (t(k.meaning_zh)) c.appendChild(el('div', 'k-mean', '意思：' + k.meaning_zh));
      lineIf(c, '音读', (k.onyomi || []).join(' / '));
      lineIf(c, '训读', (k.kunyomi || []).join(' / '));
      var exs = k.examples || [];
      if (exs.length) {
        var eb = el('div', 'k-ex-list');
        eb.appendChild(el('div', 'sub-title', '例词'));
        exs.forEach(function (e) {
          eb.appendChild(el('div', 'k-ex',
            t(e.ja) + (t(e.kana) ? '（' + e.kana + '）' : '') + (t(e.zh) ? ' ' + e.zh : '')));
        });
        c.appendChild(eb);
      }
      if (t(k.zh_trap)) c.appendChild(el('div', 'trap', '中文母语者陷阱：' + k.zh_trap));
      if (t(k.ko_hint)) c.appendChild(el('div', 'ko-hint', k.ko_hint));
      c.appendChild(el('div', 'k-note', '不要求机械抄写：会认、会读、能在词里读出来即可。'));
      c.appendChild(listenBtn(t(k.char), '听'));
      list.appendChild(c);
    });
    if (!ks.length) box.appendChild(el('p', 'muted', '（今天没有新汉字）'));
    box.appendChild(list);
    return box;
  }

  /* ⑤ 例句 / 会话：原文与假名读音两个不同节点；audio_text 只用于 TTS。 */
  function renderExamplesBlock(day) {
    var ms = day.materials || [];
    var box = sectionPlain('例句 / 会话',
      '日文原文与假名读音分开给：原文是「写在纸上的样子」，假名是「怎么念」。点「听」听整段。');
    ms.forEach(function (m) {
      var c = el('div', 'material');
      c.appendChild(el('h3', 'material-title',
        (m.kind === 'listening' ? '听力 · ' : '阅读 · ') + t(m.title)));
      if (t(m.text_ja)) c.appendChild(el('div', 'ja-text', m.text_ja));
      /* 只有确有真实假名、且与原文不同时才显示读音行；绝不把 audio_text 当读音。 */
      if (t(m.text_kana) && m.text_kana !== m.text_ja) {
        c.appendChild(el('div', 'kana-line', '假名读音：' + m.text_kana));
      }
      if (t(m.text_zh)) c.appendChild(el('div', 'm-zh', '中文：' + m.text_zh));
      var row = el('div', 'material-actions');
      row.appendChild(listenBtn(t(m.audio_text) || t(m.text_ja), '听这段'));
      c.appendChild(row);
      if (t(m.focus_zh)) c.appendChild(el('div', 'note-zh', '难点：' + m.focus_zh));
      box.appendChild(c);
    });
    if (!ms.length) box.appendChild(el('p', 'muted', '（今天没有会话素材）'));
    return box;
  }

  /* ⑦ 今日复习：优先真实 FSRS 到期项；没有记忆记录时才展示「预习建议」。
     三条分支见 REVISION_CONTRACT §4；自评必须先显示答案才可点（§3.1）。 */
  var CAP_ZH = {
    meaning: '认意思', reading: '读音', listening: '听解', usage: '用法', production: '产出'
  };
  function renderReviewBlock(day, state) {
    var review = (day.review && typeof day.review === 'object') ? day.review : null;
    var due = (review && review.due) ? review.due : [];
    /* 旧数据没有 review 对象时退回 review_plan（视为预习建议，不宣称到期）。 */
    var planned = (review && review.planned) ? review.planned
      : (review ? [] : (day.review_plan || []));
    var box = sectionPlain('今日复习（记忆曲线）',
      '先遮住中文自己想，再点开对答案，最后选「记住了 / 模糊 / 忘了」。');
    if (!due.length && !planned.length) {
      box.appendChild(el('div', 'review-empty', '今天没有到期项。'));
      var news = (day.vocab || []).map(function (v) { return t(v.surface); }).filter(Boolean);
      if (news.length) box.appendChild(el('div', 'review-new',
        '今天新学：' + news.join(' / ') + '。明天会开始带你回忆这几个词。'));
      box.appendChild(el('div', 'review-why',
        '没有到期项就是没有到期项：本页不编造复习任务，也不把「读完页面」记为复习。'));
      return box;
    }
    var isFsrs = due.length > 0;
    var items = isFsrs ? due : planned;
    if (isFsrs) {
      box.appendChild(el('p', 'review-disclaimer',
        '下面是本地 SQLite 里真实到期的 FSRS 记忆卡；到期时间由 FSRS 计算，页面只记录你的自评，不替你判定掌握。'));
      box.appendChild(el('div', 'review-count', '今天真正到期（FSRS） · 共 ' + due.length + ' 项'));
    } else {
      box.appendChild(el('p', 'review-disclaimer',
        '下面是预习建议（按粗略间隔生成），这些不是 FSRS 到期项；实际到期以本地 SQLite / WorkBuddy 会话为准。'));
      box.appendChild(el('div', 'review-count', '预习建议（尚未建立记忆记录） · 共 ' + planned.length + ' 项'));
    }
    items.forEach(function (p, i) {
      var kid = t(p.kid || p.knowledge_id);
      var rateKid = t(p.card_key) || kid;   /* 能力卡按 kid|capability 精确排期 */
      var it = el('div', 'review-item');
      if (p.planned_only) it.setAttribute('data-planned-only', '1');
      var head = el('div', 'review-head');
      head.appendChild(el('span', 'review-no', String(i + 1)));
      head.appendChild(el('span', 'review-surface', t(p.surface)));
      if (t(p.kana)) head.appendChild(el('span', 'review-kana', p.kana));
      head.appendChild(listenBtn(t(p.surface) || t(p.kana), '听'));
      it.appendChild(head);
      var ansRow = el('div', 'review-ans');
      var showBtn = el('button', 'btn btn-mini', '显示答案');
      showBtn.type = 'button';
      var zhSpan = el('span', 'review-zh', '');
      zhSpan.hidden = true;
      ansRow.appendChild(showBtn); ansRow.appendChild(zhSpan);
      it.appendChild(ansRow);
      if (isFsrs) {
        var over = Number(p.overdue_days || 0);
        var meta = '到期：' + t(p.due);
        if (over > 0) meta += ' · 已逾期 ' + over + ' 天';
        if (t(p.capability)) meta += ' · 能力：' + (CAP_ZH[t(p.capability)] || t(p.capability));
        if (t(p.stage)) meta += ' · 阶段：' + t(p.stage);
        it.appendChild(el('div', 'review-next', meta));
      } else {
        it.appendChild(el('div', 'review-reason', '为什么是今天：' + t(p.reason_zh)));
        if (t(p.next_hint_zh)) it.appendChild(el('div', 'review-next', t(p.next_hint_zh)));
      }
      var rates = el('div', 'rating-btns');
      rates.appendChild(el('span', 'rating-label', '回想一下：'));
      var btns = [];
      [['good', '记住了'], ['hard', '模糊'], ['again', '忘了']].forEach(function (o) {
        var b = el('button', 'btn btn-mini rate-btn', o[1]);
        b.type = 'button';
        b.disabled = true;   /* 未显示答案不得自评 */
        b.addEventListener('click', function () {
          if (b.disabled) return;
          if (state && rateKid) { state.reviewRatings[rateKid] = o[0]; if (QUIZ && QUIZ.save) QUIZ.save(); }
          btns.forEach(function (x) { x.classList.remove('sel'); });
          b.classList.add('sel');
        });
        btns.push(b);
        rates.appendChild(b);
      });
      showBtn.addEventListener('click', function () {
        zhSpan.textContent = t(p.zh); zhSpan.hidden = false; showBtn.hidden = true;
        btns.forEach(function (x) { x.disabled = false; });
      });
      it.appendChild(rates);
      box.appendChild(it);
    });
    return box;
  }

  /* ⑧ 页尾折叠：给老师 / 系统。能力目标、时间块、图表、术语、TTS、回传码全在这里。 */
  function renderTeacherBlock(day, site) {
    var d = el('details', 'teacher');
    d.appendChild(el('summary', 'section-sum', '给老师 / 系统（课程编排与系统信息，点开查看）'));
    var body = el('div', 'section-body');
    d.appendChild(body);
    body.appendChild(el('p', 'teacher-lead',
      '下面是排课、统计与工程信息，不影响今天学日语。学员看上面的 7 个区块就够了。'));

    if (t(day.can_do)) {
      var s1 = section('今天要会做的事', false);
      s1._body.appendChild(el('p', '', day.can_do));
      body.appendChild(s1);
    }
    if ((day.focus || []).length) {
      var fz = { listening: '听', reading: '读', speaking: '说', writing: '写',
                 production: '表达', grammar: '语法' };
      var fparts = day.focus.map(function (f) { return fz[f] || t(f); });
      body.appendChild(el('p', 'muted', '今天重点：' + fparts.join(' / ')));
    }
    if (t(day.assessment) && day.assessment !== 'none') {
      body.appendChild(el('p', 'muted', '评估标签：' + assessmentZh(day.assessment)));
    }
    if (t(day.scene)) body.appendChild(el('p', 'muted', '真实场景：' + day.scene));

    if ((day.objectives || []).length) {
      var so = section('能力目标（教研用语）', false);
      var ul = el('ul', 'objectives');
      day.objectives.forEach(function (o) { ul.appendChild(el('li', '', o)); });
      so._body.appendChild(ul); body.appendChild(so);
    }
    var st = section('60 分钟时间块（排课视角）', false);
    st._body.appendChild(timeBar(day.blocks, day.minutes));
    body.appendChild(st);
    var sv = section('当日可视化（课程结构，不代表掌握进度）', false);
    var vg = el('div', 'viz-grid');
    vg.appendChild(vizCard('当日结构', dayStructureSVG(day)));
    vg.appendChild(vizCard('80 天进度热力图', heatmapSVG(site, day.day), 'viz-heat'));
    vg.appendChild(vizCard('题型分布', typeDistSVG(day.questions)));
    sv._body.appendChild(vg);
    sv._body.appendChild(phaseLegend());
    body.appendChild(sv);

    if ((day.teaching_notes || []).length) {
      var sn = section('中文难点讲解（备课用）', false);
      day.teaching_notes.forEach(function (n) { sn._body.appendChild(el('p', '', n)); });
      body.appendChild(sn);
    }
    body.appendChild(el('p', 'muted',
      '来源编号、内部 ID、评估标签与课程结构数据仅用于教研溯源，不在学习区展示。'));

    /* TTS 设备自检 / 语速控件降级到页尾折叠（保留手势解锁与降级提示）。 */
    var banner = byId('tts-banner');
    if (banner) body.appendChild(banner);
    /* 回传码面板（由 buildPracticeV3 生成）挂到页尾折叠区，移出前 3 屏。 */
    if (QUIZ && QUIZ.returnBox) body.appendChild(QUIZ.returnBox);
    body.appendChild(el('p', 'muted',
      '术语：摸底（不计分，只用来定起点）；复习任务分为「FSRS 到期项」与「预习建议（尚未建立记忆记录）」两种，页面会分别标注；把成绩带回 WorkBuddy（回传码）。网页不向任何服务器发送学习数据，学习状态以本地 SQLite / WorkBuddy 会话为准。'));
    return d;
  }

  /* ⑥ 练习：默认展开、由易到难；先想 → 看答案 → 解析+示范句+rubric；逐题中文化反馈。
     保留逐题判分 / 复制·分享·下载回传码 / 手势解锁等既有机制；
     复习自评与开放题自评都写独立字段，绝不写进 results[].correct。 */
  function buildPracticeV3(day) {
    var TYPE_ORDER = { listen: 0, mcq: 1, read: 1, fill: 2, reorder: 3,
                       translate: 4, error_correct: 5, dialogue: 6, free_production: 7 };
    var qs = (day.questions || []).slice().sort(function (a, b) {
      var da = a.difficulty || 0, db = b.difficulty || 0;
      if (da !== db) return da - db;
      var ta = TYPE_ORDER[a.type] === undefined ? 9 : TYPE_ORDER[a.type];
      var tb = TYPE_ORDER[b.type] === undefined ? 9 : TYPE_ORDER[b.type];
      return ta - tb;
    });
    var state = { day: day.day, index: 0, session: null, results: {},
                  started: {}, reviewRatings: {} };
    var mode = LAYOUT.mode;

    var sec = sectionPlain('练一练（学完马上做）',
      '先自己想，再点「看答案」对照解析与示范句；也可以直接「提交答案」看判分。开放题没有唯一答案，照着示范句把自己的话写进去也对。');

    if (mode === 'step') {
      var viewRow = el('div', 'btn-row');
      var viewAll = el('button', 'btn btn-mini', '查看全部题目 / 回看解析');
      viewAll.type = 'button';
      viewAll.addEventListener('click', function () {
        var list = sec.querySelector('.q-list');
        if (!list) return;
        var all = list.classList.contains('grid-mode');
        list.classList.toggle('grid-mode', !all);
        list.classList.toggle('step-mode', all);
        viewAll.textContent = all ? '查看全部题目 / 回看解析' : '回到一屏一题';
      });
      viewRow.appendChild(viewAll);
      sec.appendChild(viewRow);
    }

    var root = el('div', 'quiz quiz-' + mode);
    sec.appendChild(root);

    /* 当日恢复：localStorage 只是刷新/断网缓存，不是状态真源（保留既有机制）。 */
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
    if (saved && saved.reviewRatings) state.reviewRatings = saved.reviewRatings;
    if (!state.session) state.session = makeSessionId();

    /* PC 工具条（保留），文案白话化，不用「已答 X / Y」定义学员。 */
    var toolbar = el('div', 'quiz-toolbar');
    var tbProgress = el('span', 'tb-progress', '共 ' + qs.length + ' 题 · 按自己节奏做');
    var tbFinish = el('button', 'btn btn-primary', '把成绩带回 WorkBuddy');
    tbFinish.type = 'button';
    var tbCopy = el('button', 'btn', '复制回传码');
    tbCopy.type = 'button';
    toolbar.appendChild(tbProgress); toolbar.appendChild(tbFinish); toolbar.appendChild(tbCopy);
    root.appendChild(toolbar);

    /* 回传码面板：白话改名，不出现协议号 / 算法缩写；DOM 由 renderDay 挂到页尾折叠区。 */
    var returnBox = el('details', 'return-box');
    returnBox.appendChild(el('summary', 'section-sum', '把成绩带回 WorkBuddy（复制 / 分享 / 下载）'));
    var rbBody = el('div', 'section-body');
    rbBody.appendChild(el('div', 'return-hint',
      '复制后粘贴到 WorkBuddy 对话即可导入；本页不保存成绩、不向任何服务器发送学习数据，仅保存作答记录，不代表已掌握。'));
    var summary = el('div', 'return-summary', '尚未生成');
    rbBody.appendChild(summary);
    var codeArea = el('textarea', 'code-area');
    codeArea.readOnly = true; codeArea.rows = 4;
    codeArea.setAttribute('aria-label', '回传码文本框（可全选复制）');
    rbBody.appendChild(codeArea);
    var btnRow = el('div', 'btn-row');
    var copyBtn = el('button', 'btn btn-primary', '复制回传码'); copyBtn.type = 'button';
    var selectBtn = el('button', 'btn', '全选文本'); selectBtn.type = 'button';
    var shareBtn = el('button', 'btn', '系统分享'); shareBtn.type = 'button';
    var dlBtn = el('button', 'btn', '下载 .txt'); dlBtn.type = 'button';
    var regenBtn = el('button', 'btn', '重新生成'); regenBtn.type = 'button';
    [copyBtn, selectBtn, shareBtn, dlBtn, regenBtn].forEach(function (b) { btnRow.appendChild(b); });
    rbBody.appendChild(btnRow);
    var copyStatus = el('div', 'copy-status', '');
    rbBody.appendChild(copyStatus);
    returnBox.appendChild(rbBody);
    /* 故意不 append 到 root：由 renderTeacherBlock 挂到页尾折叠区，移出前 3 屏。 */

    var lastCode = '';

    function save() {
      try {
        localStorage.setItem('nh80:day:' + day.day,
          JSON.stringify({ session: state.session, results: state.results,
                           reviewRatings: state.reviewRatings }));
      } catch (e) {}
    }
    function elapsed(qid) {
      if (!state.started[qid]) state.started[qid] = Date.now();
      return Math.round((Date.now() - state.started[qid]) / 1000);
    }
    function generate(open) {
      var payload = makePayload(state);
      autoSync(payload);
      lastCode = encodeReturnCode(payload);
      QUIZ.lastCode = lastCode;
      codeArea.value = lastCode;
      summary.textContent = '共 ' + qs.length + ' 题 · 已记录 ' + payload.results.length
        + ' 条作答 · 复习自评 ' + payload.review_ratings.length + ' 条 · 会话 ' + payload.session;
      if (open) {
        if (TEACHER_BOX) TEACHER_BOX.open = true;
        returnBox.open = true;
      }
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
          var p = navigator.share({ title: 'Nihongo 80 学习记录 · 第 ' + day.day + ' 天', text: code });
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

    /* 解析区预渲染（DOM 里已有文本，初始隐藏）。中文化反馈，不出现英文错误归因枚举。 */
    function renderRevealContent(q, box, r) {
      box.innerHTML = '';
      if (r && r.revealed_before_submit) box.appendChild(revealNoticeNode());
      if (r) {
        if (r._graded) {
          var badge = r.correct
            ? el('span', 'badge badge-good', '答对')
            : el('span', 'badge badge-bad', '再核对一下');
          box.appendChild(badge);
        }
        box.appendChild(el('div', 'reveal-row', '你的答案：' + (r.answer || '（空）')));
      }
      if (t(q.answer)) box.appendChild(el('div', 'reveal-row', '参考答案：' + q.answer));
      if (t(q.rationale)) box.appendChild(el('div', 'reveal-row', '解析：' + q.rationale));
      if (t(q.expected_production)) {
        var ep = el('div', 'demo-box');
        ep.appendChild(el('div', 'demo-title', '示范句（不是唯一答案）'));
        ep.appendChild(el('div', 'demo-ja', q.expected_production));
        ep.appendChild(listenBtn(q.expected_production, '听示范句'));
        box.appendChild(ep);
      }
      if (t(q.rubric)) {
        var rub = el('div', 'rubric');
        rub.appendChild(el('div', 'rubric-title', '评分准则（分点对照）'));
        String(q.rubric).split(/[；;①②③④⑤⑥\n]+/).forEach(function (s2) {
          if (s2.trim()) rub.appendChild(el('div', 'rubric-item', s2.trim()));
        });
        box.appendChild(rub);
      }
      box.appendChild(el('div', 'feedback-zh',
        '下次遇到这类题：先看清句子里的助词和句末，再对照上面的讲解；写错也没关系，重点是知道为什么。'));
      if (q.type === 'free_production' || q.type === 'dialogue' || !t(q.answer)) {
        var sa = el('div', 'self-assess');
        sa.appendChild(el('span', '', '自查（不计入成绩）：'));
        var yes = el('button', 'btn btn-mini', '会了');
        var no = el('button', 'btn btn-mini', '还不熟');
        yes.type = no.type = 'button';
        function setSA(v, label) {
          var cur = state.results[q.id];
          if (cur) { cur.self_assessed = v; save(); }
          var note = sa.querySelector('.self-assess-note');
          if (note) note.textContent = label;
          else sa.appendChild(el('span', 'self-assess-note', label));
          yes.disabled = no.disabled = true;
        }
        yes.addEventListener('click', function () { setSA('yes', '已记录：会了（仅自评，不计成绩）'); });
        no.addEventListener('click', function () { setSA('no', '已记录：还不熟（仅自评，不计成绩）'); });
        sa.appendChild(yes); sa.appendChild(no);
        box.appendChild(sa);
      }
    }
    function showReveal(q, r, box, onChange) {
      renderRevealContent(q, box, r);
      box.hidden = false;
      if (onChange) onChange();
    }

    var cards = [];
    function makeCard(q, i) {
      state.started[q.id] = Date.now();
      var node = el('details', 'q-card');
      node.setAttribute('data-qid', q.id);
      node.open = true;                       /* 默认展开，不点折叠即可作答 */
      var sum = el('summary', 'q-sum');
      if (mode === 'step') {
        sum.addEventListener('click', function (e) { if (e.preventDefault) e.preventDefault(); });
      }
      var head = el('div', 'q-head');
      head.appendChild(el('span', 'q-no', '第 ' + (i + 1) + ' / ' + qs.length + ' 题'));
      head.appendChild(el('span', 'q-type', qTypeZh(q.type)));   /* 中文化题型 */
      var status = el('span', 'q-status', '');
      head.appendChild(status);
      sum.appendChild(head);
      if (t(q.prompt_zh)) sum.appendChild(el('p', 'q-prompt-zh', q.prompt_zh));
      if (t(q.prompt_ja)) sum.appendChild(el('p', 'q-prompt-ja', q.prompt_ja));
      node.appendChild(sum);

      var body = el('div', 'q-body');
      if (t(q.audio_text)) {
        var arow = el('div', 'q-audio');
        var play = el('button', 'btn btn-mini', '听题目'); play.type = 'button';
        var stop = el('button', 'btn btn-mini', '停止'); stop.type = 'button';
        var anotice = el('span', 'inline-notice'); anotice.hidden = true;
        play.addEventListener('click', function () { primeTTS(); speak(q.audio_text, anotice); });
        stop.addEventListener('click', function () { stopSpeak(); });
        arow.appendChild(play); arow.appendChild(stop); arow.appendChild(anotice);
        body.appendChild(arow);
        /* audio_text 只用于 TTS，不再当作可见「文本读音」（修掉读音=原文 bug）。 */
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
        var r = state.results[q.id];
        if (!r) {
          r = { qid: q.id, answer: getValue(), correct: false, hinted: true,
                seconds: elapsed(q.id), error_type: null };
          state.results[q.id] = r;
        }
        markRevealed(r, getValue(), false);
        save();
      });
      hintRow.appendChild(hintBtn); hintRow.appendChild(hintBox);
      body.appendChild(hintRow);

      var actionRow = el('div', 'q-actions');
      var showAns = el('button', 'btn', '看答案 / 解析'); showAns.type = 'button';
      var submit = el('button', 'btn btn-primary q-submit', '提交答案'); submit.type = 'button';
      actionRow.appendChild(showAns); actionRow.appendChild(submit);
      body.appendChild(actionRow);

      var reveal = el('div', 'reveal');
      reveal.hidden = true;
      renderRevealContent(q, reveal, null);   /* 预渲染：解析/示范句/rubric 已在 DOM 里 */
      body.appendChild(reveal);
      node.appendChild(body);

      function paintStatus(r) {
        status.textContent = r && r.correct ? '答对' : (r ? '再看看' : '');
        status.className = 'q-status ' + (r && r.correct ? 'ok' : (r ? 'bad' : ''));
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
        /* 已揭示 / 已提示后提交，hinted 只能保持 true，不能回退（契约 §3.1）。 */
        r.hinted = !!(r.hinted || r.revealed_before_submit);
        var g = gradeAnswer(q, ans);
        if (g !== null) r.correct = g;
        else if (r.correct === null || r.correct === undefined) r.correct = false;
        r._graded = true;
        state.results[q.id] = r;
        save();
        submit.disabled = true;
        reveal.hidden = false;
        showReveal(q, r, reveal, updateChrome);
        paintStatus(r);
        updateChrome();
      }
      showAns.addEventListener('click', function () {
        var r = state.results[q.id];
        if (!r) {
          r = { qid: q.id, answer: getValue(), correct: false, hinted: true,
                seconds: elapsed(q.id), error_type: null };
          state.results[q.id] = r;
        }
        markRevealed(r, getValue(), true);
        save();
        reveal.hidden = false;
        showReveal(q, r, reveal, updateChrome);
        if (!r._graded) submit.textContent = REVEAL_SUBMIT_LABEL;
      });
      submit.addEventListener('click', doSubmit);

      var existing = state.results[q.id];
      if (existing) {
        if (setValue) setValue(existing.answer);
        submit.disabled = true;
        reveal.hidden = false;
        showReveal(q, existing, reveal, updateChrome);
        paintStatus(existing);
        if (existing.hinted) { hintBox.hidden = false; hintBox.textContent = hintText(q); }
        if (existing.revealed_before_submit) submit.textContent = REVEAL_SUBMIT_LABEL;
      }
      return { node: node, q: q, submit: doSubmit };
    }
    function updateChrome() {
      var done = Object.keys(state.results).length;
      var total = qs.length;
      var sub = mode === 'step'
        ? ('第 ' + (state.index + 1) + ' / ' + total + ' 题')
        : ('第 ' + day.day + ' 天 · 共 ' + total + ' 题');
      setProgress(done, total, '今天 ' + total + ' 道题 · 先学后练', sub);
      tbProgress.textContent = '共 ' + total + ' 题 · 按自己节奏做';
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
      returnBox: returnBox,
      save: save,
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
      root.appendChild(el('p', 'muted', '本日暂无题目。'));
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
      '重要：本网站不是学习状态的真源。状态只存在于本地 SQLite（data/state.db）。网页仅做展示、练习、即时判分并生成「把成绩带回 WorkBuddy」的回传码；不会向任何服务器发送学习数据，也不会把「读完页面」记为完成。'));
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
    /* 标题区：去掉阶段 / ID / 评估 / 英文标签，只留白话目标与主题。 */
    var head = el('div', 'day-head');
    head.appendChild(el('div', 'day-kicker', '第 ' + day.day + ' 天'));
    head.appendChild(el('h1', 'page-title', t(day.theme) || '当日学习'));
    if (t(day.can_do)) head.appendChild(el('p', 'lead', '今天要会做的事：' + day.can_do));
    app.appendChild(head);

    /* 8 区块顺序（REDESIGN_PLAN §3）：首屏即 3 句话 + 常显词卡，不点任何折叠即可学。 */
    app.appendChild(renderLessonCore(day));                              /* ① */
    app.appendChild(renderVocabBlock(day));                             /* ② */
    app.appendChild(renderGrammarBlock(day));                           /* ③ */
    app.appendChild(renderKanjiBlock(day));                             /* ④ */
    app.appendChild(renderExamplesBlock(day));                          /* ⑤ */
    app.appendChild(buildPracticeV3(day));                              /* ⑥（建 QUIZ / returnBox） */
    app.appendChild(renderReviewBlock(day, QUIZ ? QUIZ.state : null));  /* ⑦ */
    /* 收尾可见入口：手机也能一键生成 / 复制回传码（点开页尾折叠区）。 */
    var reWrap = el('div', 'block return-entry');
    reWrap.appendChild(el('h2', 'block-title', '把成绩带回 WorkBuddy'));
    reWrap.appendChild(el('p', 'block-hint',
      '本页不保存成绩、不向任何服务器发送学习数据；点下面生成回传码，复制后粘贴到 WorkBuddy 对话即可。仅保存作答记录，不代表已掌握。'));
    var reBtn = el('button', 'btn btn-primary', '生成 / 查看回传码');
    reBtn.type = 'button';
    reBtn.addEventListener('click', function () { if (QUIZ) QUIZ.finish(); });
    reWrap.appendChild(reBtn);
    app.appendChild(reWrap);
    TEACHER_BOX = renderTeacherBlock(day, site);                        /* ⑧ */
    app.appendChild(TEACHER_BOX);
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


MOCK_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>@@TITLE@@</title>
<link rel="stylesheet" href="assets/app.css">
<style>
.mock-wrap{max-width:860px;margin:0 auto;padding:16px}
.mock-sec{border:1px solid var(--line);border-radius:10px;padding:12px;margin:14px 0;background:var(--surface-2)}
.mock-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.mock-name{font-size:17px;font-weight:700}
.mock-timer{margin-left:auto;font-variant-numeric:tabular-nums;color:var(--accent);font-weight:700}
.mock-q{padding:9px 0;border-bottom:1px dashed var(--line)}
.mock-q:last-child{border-bottom:0}
.mock-prompt{font-size:14.5px;line-height:1.6;margin-bottom:6px}
.mock-opts{display:flex;flex-direction:column;gap:5px}
.mock-opt{display:flex;gap:7px;align-items:flex-start;font-size:14px;line-height:1.5;cursor:pointer}
.mock-opt input{margin-top:3px}
.mock-result{border:1px solid var(--line);border-radius:10px;padding:12px;margin:14px 0;background:var(--surface-2)}
.mock-note{font-size:12.5px;color:var(--muted);line-height:1.6}
</style>
</head>
<body>
<main class="mock-wrap">
<h1 class="page-title">@@TITLE@@</h1>
<p class="mock-note">分项计时模拟：@@NOTE@@ 交卷后按分项给分。这是<strong>模拟估分</strong>，不是 JLPT 官方判定，也不预测真实考试分数。</p>
<div id="mock-sections"></div>
<div class="btn-row"><button class="btn btn-primary" type="button" id="mock-submit">交卷并计分</button></div>
<div id="mock-result"></div>
<p class="mock-note">本页不向任何服务器发送作答数据；成绩不会写回 data/state.db。</p>
</main>
<script type="application/json" id="mock-data">@@JSON@@</script>
<script>
(function () {
  'use strict';
  var data = {};
  try { data = JSON.parse(document.getElementById('mock-data').textContent); } catch (e) { data = {}; }
  var sections = data.sections || [];
  var wrap = document.getElementById('mock-sections');
  var resultBox = document.getElementById('mock-result');
  var timers = {};
  var finished = {};
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = String(text);
    return n;
  }
  function norm(v) {
    var s = String(v == null ? '' : v);
    if (s.normalize) s = s.normalize('NFKC');
    s = s.replace(/\s+/g, '').replace(/，/g, ',');
    return s.replace(/[。．.！!？?]+$/g, '');
  }
  function fmt(sec) {
    var m = Math.floor(sec / 60), s = sec % 60;
    return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
  }
  function startTimer(secId) {
    var sec = null;
    for (var i = 0; i < sections.length; i++) if (String(sections[i].id) === String(secId)) sec = sections[i];
    if (!sec || timers[secId]) return;
    var left = Math.max(0, Number(sec.minutes || 0) * 60);
    var node = document.querySelector('[data-timer="' + secId + '"]');
    function tick() {
      if (node) node.textContent = fmt(left);
      if (left <= 0) {
        clearInterval(timers[secId]); timers[secId] = null;
        finished[secId] = true;
        if (node) node.textContent = '时间到（已锁定）';
        var sb = document.querySelector('[data-sec="' + secId + '"]');
        if (sb) {
          var ins = sb.querySelectorAll('input');
          for (var k = 0; k < ins.length; k++) ins[k].disabled = true;
          var lock = el('div', 'mock-note', '本项时间到，答案已锁定；可继续其他分项。');
          sb.appendChild(lock);
        }
        return;
      }
      left -= 1;
    }
    tick();
    timers[secId] = setInterval(tick, 1000);
  }
  sections.forEach(function (sec) {
    var box = el('section', 'mock-sec');
    box.setAttribute('data-sec', String(sec.id));
    var head = el('div', 'mock-head');
    head.appendChild(el('span', 'mock-name', sec.name || '分项'));
    head.appendChild(el('span', 'mock-note',
      '满分 ' + (sec.max_score || 0) + ' · 限时 ' + (sec.minutes || 0) + ' 分钟'));
    var timer = el('span', 'mock-timer', fmt(Number(sec.minutes || 0) * 60));
    timer.setAttribute('data-timer', String(sec.id));
    head.appendChild(timer);
    var start = el('button', 'btn btn-mini', '开始本项');
    start.type = 'button';
    start.addEventListener('click', function () { start.added = true; start.disabled = true; startTimer(sec.id); });
    head.appendChild(start);
    box.appendChild(head);
    (sec.questions || []).forEach(function (q, qi) {
      var qb = el('div', 'mock-q');
      qb.appendChild(el('div', 'mock-prompt', (qi + 1) + '. ' + (q.prompt || '')));
      if (q.audio_text) {
        var play = el('button', 'btn btn-mini', '听题目（TTS）');
        play.type = 'button';
        play.addEventListener('click', function () {
          if (!window.speechSynthesis) { play.textContent = '此浏览器不支持朗读'; return; }
          var u = new SpeechSynthesisUtterance(q.audio_text);
          u.lang = 'ja-JP'; u.rate = 0.95;
          window.speechSynthesis.cancel(); window.speechSynthesis.speak(u);
        });
        qb.appendChild(play);
      }
      var opts = el('div', 'mock-opts');
      (q.options || []).forEach(function (o, oi) {
        var lab = el('label', 'mock-opt');
        var input = document.createElement('input');
        input.type = 'radio'; input.name = 'q-' + sec.id + '-' + q.id + '-' + qi;
        input.value = String(oi);
        lab.appendChild(input);
        lab.appendChild(el('span', '', o));
        opts.appendChild(lab);
      });
      if (!(q.options || []).length) {
        var ti = document.createElement('input');
        ti.type = 'text';
        ti.className = 'mock-text';
        ti.name = 'q-' + sec.id + '-' + q.id + '-' + qi;
        ti.placeholder = '在此输入答案';
        ti.style.cssText = 'width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:7px;background:var(--surface);color:var(--ink)';
        opts.appendChild(ti);
      }
      qb.appendChild(opts);
      box.appendChild(qb);
    });
    wrap.appendChild(box);
  });
  document.getElementById('mock-submit').addEventListener('click', function () {
    var total = 0, rows = [];
    sections.forEach(function (sec) {
      var qs = sec.questions || [];
      var right = 0;
      qs.forEach(function (q, qi) {
        var name = 'q-' + sec.id + '-' + q.id + '-' + qi;
        var field = document.querySelector('[name="' + name + '"]');
        if (field && field.type === 'text') {
          if (norm(field.value) === norm(q.answer_text)) right += 1;
        } else {
          var picked = document.querySelector('input[name="' + name + '"]:checked');
          if (picked && Number(picked.value) === Number(q.answer)) right += 1;
        }
      });
      var score = qs.length ? Math.round(Number(sec.max_score || 0) * right / qs.length) : 0;
      total += score;
      rows.push({ name: sec.name || '分项', score: score, max: Number(sec.max_score || 0),
                  pass_min: Number(sec.pass_min || 19), right: right, total: qs.length });
    });
    var ok = total >= Number(data.pass_total || 95) && rows.every(function (r) {
      return r.score >= Number(r.pass_min || data.pass_section || 19);
    });
    resultBox.innerHTML = '';
    var box = el('div', 'mock-result');
    box.appendChild(el('div', 'mock-name', '模拟估分：' + total + ' / ' +
      rows.reduce(function (a, r) { return a + r.max; }, 0) + ' · ' + (ok ? '达到模拟合格线' : '未达到模拟合格线')));
    rows.forEach(function (r) {
      box.appendChild(el('div', 'mock-note',
        r.name + '：' + r.score + ' / ' + r.max + '（答对 ' + r.right + ' / ' + r.total + '）'));
    });
    box.appendChild(el('div', 'mock-note',
      '判定口径：总分 ≥ ' + (data.pass_total || 95) + ' 且每项 ≥ ' + (data.pass_section || 19) +
      '。这是模拟估分，不是 JLPT 官方判定。'));
    resultBox.appendChild(box);
  });
})();
</script>
</body>
</html>
"""


def _mock_answer_index(ans, options):
    if isinstance(ans, bool):
        return -1
    if isinstance(ans, int):
        return ans if 0 <= ans < len(options) else -1
    s = str(ans if ans is not None else "").strip()
    if not options:
        return -1
    if s.isdigit():
        i = int(s)
        if 0 <= i < len(options):
            return i
        if 0 <= i - 1 < len(options):
            return i - 1
    if s in options:
        return options.index(s)
    if len(s) == 1 and s.upper() in "ABCDEFGH":
        i = "ABCDEFGH".index(s.upper())
        return i if i < len(options) else -1
    return -1


def _first(d, names, default=None):
    for n in names:
        if isinstance(d, dict) and d.get(n) not in (None, ""):
            return d[n]
    return default


def normalize_mock(data, tables=None):
    """把 knowledge/mock_n3.json 归一到渲染所需结构；字段名不一致也不报错。

    v4：支持 `question_ids`（按题库 id 引用），并把非选择题的参考答案带进页面，
    让「文字・語彙 / 文法・読解 / 聴解」三组都能真正作答，而不是只剩选择题。
    """
    if not isinstance(data, dict):
        data = {}
    defaults = [("文字・語彙", 30), ("文法・読解", 70), ("聴解", 40)]
    raw = data.get("sections") or data.get("parts") or data.get("groups")
    if not isinstance(raw, list) or not raw:
        raw = []
        for key in ("vocab", "grammar_reading", "listening"):
            v = data.get(key)
            if isinstance(v, list):
                raw.append({"id": key, "name": key, "questions": v})
            elif isinstance(v, dict):
                item = dict(v)
                item.setdefault("id", key)
                raw.append(item)
        if not raw and isinstance(data.get("questions"), list):
            raw = [{"id": "all", "name": data.get("title") or "模拟题", "questions": data["questions"]}]

    sections = []
    for i, s in enumerate(raw if isinstance(raw, list) else []):
        if not isinstance(s, dict):
            continue
        name = _first(s, ("name", "label", "title", "kind"),
                      defaults[i][0] if i < len(defaults) else "分项")
        qsrc = s.get("questions") or s.get("items") or []
        ids = s.get("question_ids") or []
        if ids and isinstance(tables, dict):
            qsrc = [tables[i] for i in ids if i in tables]
        questions = []
        for j, q in enumerate(qsrc if isinstance(qsrc, list) else []):
            if not isinstance(q, dict):
                continue
            opts = _first(q, ("options", "choices"), [])
            opts = [_sval(x) for x in opts] if isinstance(opts, list) else []
            prompt = _sval(_first(q, ("prompt", "prompt_ja", "question", "text"), ""))
            ans = _first(q, ("answer", "correct", "answer_index"), None)
            questions.append({
                "id": _sval(q.get("id")) or ("q%d" % (j + 1)),
                "type": _sval(q.get("type")),
                "prompt": prompt,
                "prompt_zh": _sval(q.get("prompt_zh")),
                "audio_text": _sval(q.get("audio_text")),
                "options": opts,
                "answer": _mock_answer_index(ans, opts),
                "answer_text": _sval(ans),
            })
        sections.append({
            "id": _sval(_first(s, ("id", "key"), "sec%d" % (i + 1))),
            "name": _sval(name),
            "minutes": int(_first(s, ("minutes", "time_limit_min", "limit_min"), 60) or 60),
            "max_score": int(_first(s, ("max_score", "points", "score"),
                                    defaults[i][1] if i < len(defaults) else 25) or 0),
            "pass_min": int(_first(s, ("pass_min", "pass_score"), 19) or 19),
            "questions": questions,
        })
    return {
        "title": _sval(data.get("title")) or "N3 分项模拟（模拟估分）",
        "pass_total": int(data.get("pass_total") or 95),
        "pass_section": int(data.get("pass_section") or 19),
        "sections": sections,
    }


def load_mock(root):
    p = root / "knowledge" / "mock_n3.json"
    if not p.is_file():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def render_mock_page(mock):
    mins = sum(int(s.get("minutes") or 0) for s in mock["sections"])
    note = "共 %d 个分项、%d 道题、合计 %d 分钟；模拟估分，不是 JLPT 官方判定。" % (
        len(mock["sections"]), sum(len(s["questions"]) for s in mock["sections"]), mins)
    return (MOCK_HTML
            .replace("@@TITLE@@", html.escape(mock["title"]))
            .replace("@@NOTE@@", note)
            .replace("@@JSON@@", json_for_script(mock)))


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
    ko = load_ko_analogy(root)   # 资料层可缺失；缺失时页面各卡不显示韩语对照，不崩溃
    # 复习队列统一（REVISION_CONTRACT §4）：只读 state.db；不存在则 page 只显示预习建议。
    review_ctx = load_review_context(root)
    knowledge_idx = _knowledge_index(tables)
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
    mock_raw = load_mock(root)
    if mock_raw is not None:
        sw_assets.append("n3-mock.html")
    (web_dir / "manifest.webmanifest").write_text(
        MANIFEST_TEMPLATE.lstrip("\n"), encoding="utf-8")
    (web_dir / "icon.svg").write_text(ICON_SVG.lstrip("\n"), encoding="utf-8")
    sw_text = (SW_TEMPLATE
               .replace("@@BUILD_ID@@", build_id)
               .replace("@@ASSETS_JSON@@", json.dumps(sw_assets, ensure_ascii=False)))
    (web_dir / "sw.js").write_text(sw_text.lstrip("\n"), encoding="utf-8")

    generated = []
    for d in target_days:
        day_data = assemble_day(d, tables, all_ids, ko)
        day_data["review"] = build_review(day_data["day"], day_data,
                                          review_ctx, knowledge_idx)
        daynum = day_data["day"]
        stem = "day-%03d" % daynum
        (data_dir / (stem + ".json")).write_text(
            json.dumps(day_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        title = "第 %03d 天 · %s | Nihongo 80" % (daynum, day_data["theme"] or "当日学习")
        (web_dir / (stem + ".html")).write_text(
            render_page(title, day_data, site), encoding="utf-8")
        generated.append(stem)

    # 服务端重判用的标准答案键：只含题目 id / 类型 / 答案，不含掌握状态。
    # Worker 的 POST /api/events 必须用它与本地 learning.grade_objective 同口径重判，
    # 不接受客户端上报的 correct（REVISION_CONTRACT §3.2、§10）。
    open_types = {"free_production", "dialogue", "translate"}
    answer_key = {
        "schema": 1,
        "generated_at": _now_iso(),
        "answers": {
            qid: {
                "id": qid,
                "type": q.get("type", ""),
                "answer": q.get("answer") or "",
                "open": (q.get("type") in open_types) or not (q.get("answer") or ""),
            }
            for qid, q in sorted(tables["questions"].items())
        },
    }
    (data_dir / "answer-key.json").write_text(
        json.dumps(answer_key, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")

    # N3 分项模拟页：knowledge/mock_n3.json 不存在时静默跳过（可能由别的任务生成）。
    if mock_raw is not None:
        mock = normalize_mock(mock_raw, tables["questions"])
        (web_dir / "n3-mock.html").write_text(render_mock_page(mock), encoding="utf-8")
        print("build_site.py: 已生成 n3-mock.html（%d 个分项）" % len(mock["sections"]))

    print("build_site.py: root=%s" % root)
    print("build_site.py: 已生成 %d 个每日页面与数据：%s%s" %
          (len(generated), ", ".join(generated[:6]), " ..." if len(generated) > 6 else ""))
    print("build_site.py: 共享文件：index.html, 404.html, assets/app.css, assets/app.js")
    print("build_site.py: PWA：manifest.webmanifest, icon.svg, sw.js (build=%s, %d 个预缓存条目)"
          % (build_id, len(sw_assets)))


if __name__ == "__main__":
    raise SystemExit("v4 构建入口已停用；请运行 python3 scripts/nh80.py build")
    main(sys.argv[1:])
