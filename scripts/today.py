#!/usr/bin/env python3
"""today.py — 新会话唯一入口：一条命令回答「今天学什么、我学到哪了」。

设计原则
--------
1. **只读 + 生成一个文件**：读课程、本机 SQLite、云端自报快照，写 `TODAY.md`。
   不推进完成、不改掌握状态、不碰 seeds。
2. **合并两个进度源**：本机 `data/state.db` 的 finish-day（权威）+ 云端
   `study_progress`（网页「完成」按钮自报）。任何一边有记录都算「学过」，
   避免「网页学完了、新会话还说 Day 1」。
3. **离线可降级**：云端不通时只用本机记录，并在文件里明确写「云端未连上」，
   不假装知道。
4. **任何 agent 可用**：纯标准库，无依赖；只要会读文件、跑 Python。

用法
----
    python3 scripts/today.py                # 生成 TODAY.md 并打印开场包
    python3 scripts/today.py --offline      # 不联网
    python3 scripts/today.py --day 12       # 指定某天（补课/回看）
    python3 scripts/today.py --json         # 机器可读
    python3 scripts/today.py --no-write     # 只看，不写文件

给会话的开场白（直接粘）：
    读 TODAY.md，按里面的「今天要做什么」和「会话怎么做」执行。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUR = ROOT / "curriculum/curriculum.json"
DB = ROOT / "data/state.db"
SEED = ROOT / "knowledge/seeds"
OUT = ROOT / "TODAY.md"
BASE = "https://nihongo80.cmjfire.workers.dev"

sys.path.insert(0, str(ROOT / "scripts"))


# ---------------------------------------------------------------------------
# 读取
# ---------------------------------------------------------------------------

def read_jsonl(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def load_course():
    data = json.loads(CUR.read_text(encoding="utf-8"))
    days = {int(d["day"]): d for d in data["days"]}
    total = int((data.get("meta") or {}).get("days") or max(days))
    return days, total


def local_done() -> set[int]:
    """本机权威：finish-day 写入且 passed=1。"""
    if not DB.is_file():
        return set()
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
        try:
            rows = conn.execute(
                "SELECT day FROM sessions s WHERE status='finished' AND passed=1 AND (day=1 OR EXISTS (SELECT 1 FROM attempts a WHERE a.day=s.day AND a.qid LIKE 'D16-%'))").fetchall()
        finally:
            conn.close()
        return {int(r[0]) for r in rows}
    except sqlite3.Error:
        return set()


def local_review():
    """Read live FSRS and outstanding prerequisites without opening a writer."""
    if not DB.is_file():
        return [], [], ""
    from learning import due_queue, pending_prerequisites
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            return due_queue(conn, limit=6), pending_prerequisites(conn, limit=3), ""
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return [], [], type(exc).__name__


def cloud_items(total: int, base: str = BASE):
    """云端自报快照。返回 (items, error)。不带密钥时 error='no_key'。"""
    try:
        import progress_read  # 复用已有实现，不重复造轮子
    except Exception as e:  # pragma: no cover
        return [], "import_failed:%s" % e
    key = progress_read.load_key(None)
    if not key:
        return [], "no_key"
    try:
        data = progress_read.fetch(base, key, {"latest": 1, "limit": 150})
    except progress_read.ProgressError as e:
        return [], e.reason
    except Exception as e:  # 网络异常不能阻塞学习
        return [], "error:%s" % type(e).__name__
    items = [x for x in (data.get("items") or []) if isinstance(x, dict) and (x.get("v") == 4 or x.get("day") == 1) and 1 <= int(x.get("day", 0)) <= total]
    return items, ""


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------

def resolve(kid: str, vocab, grammar, kanji) -> str:
    """把 V0123 / G0045 / K0012 变成人能读的形式。"""
    if kid in vocab:
        v = vocab[kid]
        return "%s（%s，%s）" % (v["surface"], v["kana"], v["meaning_zh"])
    if kid in grammar:
        g = grammar[kid]
        return "%s（%s）" % (g["pattern"], g["meaning_zh"])
    if kid in kanji:
        k = kanji[kid]
        return "%s（%s）" % (k["char"], k["meaning_zh"])
    return kid


def build(day=None, offline=False, base=BASE):
    course, total = load_course()
    vocab = {x["id"]: x for x in read_jsonl(SEED / "vocabulary.jsonl")}
    grammar = {x["id"]: x for x in read_jsonl(SEED / "grammar.jsonl")}
    kanji = {x["id"]: x for x in read_jsonl(SEED / "kanji.jsonl")}

    done_local = local_done()
    due_review, prerequisites, review_error = local_review()
    items, cloud_err = ([], "offline") if offline else cloud_items(total, base)
    done_cloud = {int(x["day"]) for x in items}

    done = done_local | done_cloud
    if day is not None:
        day = max(1, min(int(day), total))
    else:
        day = next((d for d in range(1, total + 1) if d not in done), total)
    finished_all = all(d in done for d in range(1, total + 1))

    d = course[day]
    # 「上次」按完成时间取，不按最大天数：回看旧课时不会把进度误判成最后一课。
    ordered = sorted(items, key=lambda y: str(y.get("server_ts") or ""), reverse=True)
    last_item = ordered[0] if ordered else None
    last_day = int(last_item["day"]) if last_item and last_item.get("day") else (max(done) if done else 0)

    core_ids = d.get("core_vocab_ids") or d.get("new_vocab_ids") or []
    ext_ids = d.get("extension_vocab_ids") or []
    grammar_ids = d.get("new_grammar_ids") or []
    kanji_ids = d.get("new_kanji_ids") or []

    recent = []
    for it in ordered[:3]:
        recent.append({
            "day": int(it["day"]),
            "accuracy": it.get("accuracy"),
            "completed_at": (it.get("completed_at") or "")[:10],
            "server_ts": (it.get("server_ts") or "")[:16],
        })
    weak = []
    if last_item:
        for w in last_item.get("wrong_summary") or []:
            for kid in (w.get("knowledge_ids") or []):
                weak.append(resolve(str(kid), vocab, grammar, kanji))
        for kid, rating in (last_item.get("self_rating") or {}).items():
            if str(rating) in ("again", "hard"):
                weak.append(resolve(str(kid), vocab, grammar, kanji))
        weak = list(dict.fromkeys(weak))[:6]

    report_lines = []
    if last_day:
        rp = ROOT / "days" / ("day-%03d" % last_day) / "report.md"
        if rp.is_file():
            try:
                import re as _re
                txt = rp.read_text(encoding="utf-8")
                m = _re.search(r"## 摘要[^\n]*\n(.*?)(\n## |\Z)", txt, _re.S)
                if m:
                    report_lines = [x.strip("- ").strip() for x in m.group(1).splitlines()
                                    if x.strip()][:5]
            except OSError:
                report_lines = []

    return {
        "day": day,
        "last_report": report_lines,
        "total": total,
        "done_count": len(done),
        "done_local": sorted(done_local),
        "done_cloud": sorted(done_cloud),
        "last_day": last_day,
        "last_accuracy": (last_item or {}).get("accuracy"),
        "weak": weak,
        "due_review": [dict(card, label=resolve(card["kid"], vocab, grammar, kanji)) for card in due_review],
        "prerequisite_review": [dict(item, label=resolve(item["kid"], vocab, grammar, kanji))
                                for item in prerequisites],
        "review_error": review_error,
        "recent": recent,
        "remaining": total - len(done),
        "cloud_error": cloud_err,
        "finished_all": finished_all,
        "phase": d.get("phase"),
        "phase_name": d.get("phase_name"),
        "can_do": d.get("can_do"),
        "minutes": d.get("minutes"),
        "listening": bool(d.get("listening")),
        "assessment": d.get("assessment"),
        "core_ids": core_ids,
        "extra_ids": ext_ids,
        "grammar_ids": grammar_ids,
        "kanji_ids": kanji_ids,
        "core_words": [
            "%s（%s）%s" % (vocab[i]["surface"], vocab[i]["kana"], vocab[i]["meaning_zh"])
            for i in core_ids[:8] if i in vocab
        ],
        "grammar_lines": [
            "%s：%s" % (grammar[i]["pattern"], grammar[i]["meaning_zh"])
            for i in grammar_ids if i in grammar
        ],
        "kanji_line": "、".join(kanji[i]["char"] for i in kanji_ids if i in kanji),
    }


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

def page_link(day: int, base: str = BASE) -> str:
    return "%s/day-%03d.html" % (base.rstrip("/"), day)


def render_md(s, base: str = BASE) -> str:
    day, total = s["day"], s["total"]
    cloud = {"": "已连上", "no_key": "本机缺密钥，仅用本地记录",
             "offline": "本次跳过（--offline）"}.get(s["cloud_error"],
                                                   "未连上（%s），仅用本地记录" % s["cloud_error"])
    L = [
        "# 今天：Day %03d / %d" % (day, total),
        "",
        "<!-- 新会话第一步读这个文件；不要问用户「学到哪了」，这里就是答案。 -->",
        "",
        "## 你在哪",
        "",
        "- 已完成 **%d / %d** 天，还剩 %d 天（本机 finish-day %d 天｜云端自报 %d 天）" % (
            s["done_count"], total, s["remaining"], len(s["done_local"]), len(s["done_cloud"])),
        "- 云端：%s" % cloud,
        "- 最近一次：%s" % (
            "Day %03d，自报正确率 %s" % (s["last_day"], _pct(s["last_accuracy"]))
            if s["last_day"] else "还没有完成记录，从 Day 1 开始"),
    ]
    if s["recent"]:
        L.append("- 最近记录：%s" % "；".join(
            "Day %03d %s%s" % (r["day"], _pct(r["accuracy"]),
                               "（%s）" % r["completed_at"] if r["completed_at"] else "")
            for r in s["recent"]))
    L.append("- 上次卡点：%s" % ("；".join(s["weak"]) if s["weak"] else "无（还没开始，或上次没有错题）"))
    capability_names = {"meaning": "释义", "reading": "读音", "listening": "听辨",
                        "usage": "用法", "production": "独立输出"}
    if s["review_error"]:
        L.append("- 本机 FSRS 到期：本次读取失败（%s）。" % s["review_error"])
    else:
        L.append("- 本机 FSRS 到期（最多列 6 张）：%s" % ("；".join(
            item["label"] + " · " + capability_names.get(item["capability"], item["capability"])
            for item in s["due_review"]) or "当前无到期卡"))
        if s["prerequisite_review"]:
            L.append("- 本机待补先修：" + "；".join(item["label"] for item in s["prerequisite_review"]))
    if s.get("last_report"):
        L.append("- 上次会话记录：%s" % "；".join(s["last_report"]))
    if s["finished_all"]:
        L += ["", "> %d 天课程已全部有记录。今天默认回到最后一天做总复习；用 `--day N` 回看任意一天。" % total]
    L += [
        "",
        "## 今天要做什么",
        "",
        "- 页面：%s" % page_link(day, base),
        "- 阶段：%s %s｜约 %s 分钟｜%s%s" % (
            s["phase"], s["phase_name"], s["minutes"],
            "听力日" if s["listening"] else "常规日",
            "｜测评日（%s）" % s["assessment"] if s["assessment"] and s["assessment"] != "none" else ""),
        "- 今天一句话目标：%s" % (s["can_do"] or "—"),
        "",
        "### 必学新词 %d 个（另有拓展 %d 个，自选）" % (len(s["core_ids"]), len(s["extra_ids"])),
        "",
    ]
    L += ["- " + w for w in s["core_words"]]
    if len(s["core_ids"]) > len(s["core_words"]):
        L.append("- …其余 %d 个在页面词卡里" % (len(s["core_ids"]) - len(s["core_words"])))
    L += ["", "### 语法 %d 条" % len(s["grammar_lines"]), ""]
    L += ["- " + g for g in s["grammar_lines"]]
    if s["kanji_line"]:
        L += ["", "### 今日汉字", "", "- " + s["kanji_line"]]
    L += [
        "",
        "## 会话怎么做（不要复述页面）",
        "",
        "1. 先把页面链接发给学生，等他看完再来。",
        "2. 先做每日记忆曲线单选，再结合本机到期卡、待补先修及上次错题讲解。",
        "3. 先看今天 %d 条语法的韩语对应，按需解释日语接续、助词和语体。" % len(s["grammar_lines"]),
        "4. 做完新词与语法单选后，从页面重练错题。",
        "5. 收尾写 `days/day-%03d/report.md`：摘要 ≤5 行（完成度 / 真正学会 / 仍然卡 / 明日建议）。" % day,
        "",
        "## 完成与记录",
        "",
        "- 学生学完点网页底部「完成」→ 写入云端 `study_progress`（自报快照）。",
        "- 会话要复核就跑 `python3 scripts/progress_read.py --day %d`；要跨天看就跑 `--latest 7`。" % day,
        "- 本机权威仍是 `python3 scripts/nh80.py finish-day`；云端记录不等于掌握判定。",
        "",
        "## 禁止",
        "",
        "- 不改 `knowledge/seeds/`、`plan/`、`STATE.md`。",
        "- 不把答案写进 `days/` 或 `TODAY.md`。",
        "",
        "_由 `scripts/today.py` 生成于 %s_" % dt.datetime.now().astimezone().isoformat(timespec="minutes"),
        "",
    ]
    return "\n".join(L)


def _pct(v):
    if isinstance(v, (int, float)):
        return "%.0f%%" % (v * 100)
    return "—"


def print_opening(s, base: str = BASE):
    """打印给会话的最小开场包（不动文件也能用）。"""
    print("Day %03d / %d｜已完成 %d｜%s" % (
        s["day"], s["total"], s["done_count"],
        "听力日" if s["listening"] else "常规日"))
    print("页面：%s" % page_link(s["day"], base))
    if s["last_day"]:
        print("上次：Day %03d，正确率 %s%s" % (
            s["last_day"], _pct(s["last_accuracy"]),
            "；卡点 " + "、".join(s["weak"][:3]) if s["weak"] else ""))
    print("今天：%d 词 / %d 语法 / %s" % (
        len(s["core_ids"]), len(s["grammar_lines"]),
        ("%d 汉字" % len(s["kanji_ids"])) if s["kanji_ids"] else "无汉字"))
    if s["grammar_lines"]:
        print("语法：" + "；".join(s["grammar_lines"]))
    print("下一步：读 TODAY.md，按「会话怎么做」执行。")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="新会话唯一入口：今天学什么、学到哪了")
    ap.add_argument("--day", type=int, help="指定某天（默认自动推算下一天）")
    ap.add_argument("--offline", action="store_true", help="不读云端，只用本机记录")
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--no-write", action="store_true", help="不写 TODAY.md，只打印")
    ap.add_argument("--base", default=BASE, help="站点根地址（默认 production；测试可指 preview）")
    args = ap.parse_args(argv)

    try:
        s = build(args.day, args.offline, args.base)
    except FileNotFoundError as e:
        print(json.dumps({"ok": False, "reason": "missing_file", "detail": str(e)},
                         ensure_ascii=False), file=sys.stderr)
        return 2
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(json.dumps({"ok": False, "reason": "bad_course", "detail": str(e)},
                         ensure_ascii=False), file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0

    md = render_md(s, args.base)
    if not args.no_write:
        OUT.write_text(md, encoding="utf-8")
        # 任务书 / STATE 与今天保持一致（session_v5 若可用）；失败不影响主流程。
        try:
            from session_v5 import brief, state_write
            brief(s["day"], force=True)
            state_write(s["day"])
        except Exception:
            pass
    print_opening(s, args.base)
    if not args.no_write:
        print("\n已写入 %s（%d 行）" % (OUT.relative_to(ROOT), md.count("\n")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
