#!/usr/bin/env python3
"""session_v5.py — 文件协议：STATE / brief / report / task / daily。

不依赖 WorkBuddy 专有 API；任何能读文件、跑 Python 的 agent 都能接手。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUR = ROOT / "curriculum/curriculum.json"
PROGRESS = ROOT / "data/progress.json"
STATE = ROOT / "STATE.md"
DAYS = ROOT / "days"
TASKS = ROOT / "tasks"
INBOX = ROOT / "inbox"
PLAN = ROOT / "plan"


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="minutes")


def read_jsonl(p):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def load_cur():
    return {d["day"]: d for d in json.loads(CUR.read_text(encoding="utf-8"))["days"]}


def progress():
    if PROGRESS.is_file():
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    return {"day": 1}


def save_progress(p):
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS.write_text(json.dumps(p, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def page_link(day):
    return "https://nihongo80.cmjfire.workers.dev/day-%03d.html" % day


def ensure_dirs():
    for d in (DAYS, TASKS / "open", TASKS / "claimed", TASKS / "done", INBOX, PLAN):
        d.mkdir(parents=True, exist_ok=True)


def brief(day: int, force=False):
    ensure_dirs()
    d = load_cur()[day]
    vocab = {x["id"]: x for x in read_jsonl(ROOT / "knowledge/seeds/vocabulary.jsonl")}
    grammar = {x["id"]: x for x in read_jsonl(ROOT / "knowledge/seeds/grammar.jsonl")}
    kanji = {x["id"]: x for x in read_jsonl(ROOT / "knowledge/seeds/kanji.jsonl")}
    out = DAYS / ("day-%03d" % day)
    out.mkdir(parents=True, exist_ok=True)
    p = out / "brief.md"
    L = ["# Day %03d 任务书" % day, "",
         "- 阶段：%s｜%d 分钟｜%s" % (d["phase"], d["minutes"], "听力日" if d.get("listening") else "常规日"),
         "- 今日页面：%s" % page_link(day),
         "- Can-do：%s" % d["can_do"], "",
         "## 今天要学", ""]
    L.append("### 新词 %d" % len(d["new_vocab_ids"]))
    for vid in d["new_vocab_ids"]:
        v = vocab[vid]
        ko = "｜朝鲜语：%s" % v["ko_hanja"] if v.get("ko_hanja") else ""
        L.append("- **%s**（%s）%s%s" % (v["surface"], v["kana"], v["meaning_zh"], ko))
    L += ["", "### 语法 %d" % len(d["new_grammar_ids"])]
    for gid in d["new_grammar_ids"]:
        g = grammar[gid]
        L.append("- **%s**：%s｜接续：%s" % (g["pattern"], g["meaning_zh"], g.get("connection", "")))
        if g.get("ko_equiv"):
            L.append("  - 朝鲜语：%s（%s）" % (g["ko_equiv"], g.get("ko_diff", "")))
    L += ["", "### 汉字 %d" % len(d["new_kanji_ids"])]
    for kid in d["new_kanji_ids"]:
        k = kanji[kid]
        L.append("- **%s** %s｜音：%s｜训：%s" % (k["char"], k["meaning_zh"],
                                                "、".join(k.get("onyomi") or []),
                                                "、".join(k.get("kunyomi") or [])))
    L += ["", "## 复习到期", ""]
    L.append("见页面「今日复习」；上限 80 张，超出顺延。")
    L += ["", "## 会话流程（18 分钟）", "",
          "1. **先发页面链接**，等学生看完，不要一上来讲课。",
          "2. 只回答学生问的，不复述页面。",
          "3. 抽查 3 个旧词（造句，不是认读）。",
          "4. 让学生用今天语法造 2 句，现场改。",
          "5. 逐句改 10 句翻译（先让他读自己写的）。",
          "6. 写 `days/day-%03d/report.md`，然后跑：" % day,
          "   `python3 scripts/nh80.py finish-day %d`" % day,
          "   `python3 scripts/session_v5.py task done day-%03d-tutor --owner <你的名字>`" % day,
          "", "## 禁止", "",
          "- 不改 `plan/`、`STATE.md`、`knowledge/seeds/`。",
          "- 不把答案写进本文件。",
          "- 不因为「感觉学会了」跳过练习。"]
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p


def report(day: int, force=False):
    out = DAYS / ("day-%03d" % day)
    out.mkdir(parents=True, exist_ok=True)
    p = out / "report.md"
    if p.exists() and not force:
        return p
    p.write_text("""# Day %03d 日报

## 摘要（≤5 行，主会话只读这段）
- 完成：—/6 块｜练习 —/6｜复习 — 张
- 真正学会：
- 仍然卡：
- 明日建议：

## 教学记录
-

## 错题与错因
| 题 | 学生答案 | 正确答案 | 错因 |
|---|---|---|---|

## 句子批改
| # | 学生译文 | 修改 | 错因 |
|---|---|---|---|

## 需要主会话决策
- 无
""" % day, encoding="utf-8")
    return p


def task_new(day: int, role="tutor"):
    ensure_dirs()
    tid = "day-%03d-%s" % (day, role)
    p = TASKS / "open" / (tid + ".md")
    if p.exists():
        return p
    fm = ["---", "id: " + tid, "role: " + role, "day: %d" % day, "owner: null",
          "status: open", "depends_on: []",
          "inputs:", "  - STATE.md", "  - days/day-%03d/brief.md" % day, "  - data/state.db",
          "outputs:", "  - days/day-%03d/report.md" % day,
          "acceptance:", "  - 6 块完成或明确记录未完成原因", "  - 报告含「摘要」≤5 行",
          "created_at: %s" % now(), "claimed_at: null", "done_at: null", "---", "",
          "## 今日任务", "", "按 `brief.md` 教 Day %03d；先发页面链接。" % day, "",
          "## 禁止", "", "- 不改 plan/、STATE.md、seeds。", ""]
    p.write_text("\n".join(fm), encoding="utf-8")
    return p


def task_list():
    rows = []
    for sub in ("open", "claimed"):
        for p in sorted((TASKS / sub).glob("*.md")):
            txt = p.read_text(encoding="utf-8")
            tid = re.search(r"^id:\s*(.+)$", txt, re.M)
            owner = re.search(r"^owner:\s*(.+)$", txt, re.M)
            status = re.search(r"^status:\s*(.+)$", txt, re.M)
            rows.append({"id": tid.group(1).strip() if tid else p.stem,
                         "dir": sub, "owner": (owner.group(1).strip() if owner else "null"),
                         "status": status.group(1).strip() if status else "?"})
    return rows


def task_claim(tid, owner):
    src = TASKS / "open" / (tid + ".md")
    if not src.exists():
        return {"ok": False, "error": "not_open"}
    lock = TASKS / "claimed" / (tid + ".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, now().encode())
        os.close(fd)
    except FileExistsError:
        return {"ok": False, "error": "already_claimed"}
    txt = src.read_text(encoding="utf-8")
    txt = re.sub(r"^owner:.*$", "owner: " + owner, txt, flags=re.M)
    txt = re.sub(r"^status:.*$", "status: claimed", txt, flags=re.M)
    txt = re.sub(r"^claimed_at:.*$", "claimed_at: " + now(), txt, flags=re.M)
    dst = TASKS / "claimed" / (tid + ".md")
    dst.write_text(txt, encoding="utf-8")
    src.unlink()
    return {"ok": True, "task": str(dst)}


def task_done(tid, owner):
    src = TASKS / "claimed" / (tid + ".md")
    if not src.exists():
        src = TASKS / "open" / (tid + ".md")
    if not src.exists():
        return {"ok": False, "error": "not_found"}
    txt = src.read_text(encoding="utf-8")
    txt = re.sub(r"^status:.*$", "status: done", txt, flags=re.M)
    txt = re.sub(r"^owner:.*$", "owner: " + owner, txt, flags=re.M)
    txt = re.sub(r"^done_at:.*$", "done_at: " + now(), txt, flags=re.M)
    dst = TASKS / "done" / (tid + ".md")
    dst.write_text(txt, encoding="utf-8")
    src.unlink()
    lock = TASKS / "claimed" / (tid + ".lock")
    if lock.exists():
        lock.unlink()
    return {"ok": True, "task": str(dst)}


def state_write():
    ensure_dirs()
    p = progress()
    day = int(p.get("day") or 1)
    cur = load_cur()
    d = cur.get(day) or cur[1]
    rep = DAYS / ("day-%03d" % day) / "report.md"
    summary = []
    if rep.is_file():
        txt = rep.read_text(encoding="utf-8")
        m = re.search(r"## 摘要[^\n]*\n(.*?)(\n## |\Z)", txt, re.S)
        if m:
            summary = [x.strip("- ").strip() for x in m.group(1).strip().splitlines() if x.strip()][:5]
    L = ["# 学习状态", "",
         "- 更新：%s（scripts/session_v5.py state 生成，勿手改）" % now(),
         "- 当前：Day %03d / 150（%s %s）" % (day, d["phase"], d["phase_name"]),
         "- 今日：days/day-%03d/brief.md ｜ %d 分钟 ｜ %s" % (day, d["minutes"], "听力日" if d.get("listening") else "常规日"),
         "- 今日页面：%s" % page_link(day),
         "- Can-do：%s" % d["can_do"],
         "- 昨日摘要：%s" % ("；".join(summary) if summary else "无（还没写日报）"),
         "- 待办：%s" % (", ".join(t["id"] for t in task_list() if t["dir"] == "open") or "无"),
         "- 学生下一步：先打开页面，学完再进会话",
         "", "## 文件索引", "",
         "- 任务卡：`tasks/open/`", "- 日报：`days/day-%03d/report.md`" % day,
         "- 周计划：`plan/`", "- 收件箱：`inbox/to-main.md`", ""]
    STATE.write_text("\n".join(L), encoding="utf-8")
    return STATE


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("state"); s.set_defaults(fn=lambda a: print(state_write()))
    b = sub.add_parser("brief"); b.add_argument("--day", type=int, required=True)
    b.add_argument("--force", action="store_true"); b.set_defaults(fn=lambda a: print(brief(a.day, a.force)))
    r = sub.add_parser("report"); r.add_argument("--day", type=int, required=True)
    r.add_argument("--force", action="store_true"); r.set_defaults(fn=lambda a: print(report(a.day, a.force)))
    t = sub.add_parser("task"); t.add_argument("action", choices=["new", "list", "claim", "done"])
    t.add_argument("id", nargs="?"); t.add_argument("--owner", default="workbuddy")
    t.add_argument("--day", type=int, default=1)
    def _task(a):
        if a.action == "new": print(task_new(a.day))
        elif a.action == "list": print(json.dumps(task_list(), ensure_ascii=False, indent=1))
        elif a.action == "claim": print(json.dumps(task_claim(a.id, a.owner), ensure_ascii=False))
        else: print(json.dumps(task_done(a.id, a.owner), ensure_ascii=False))
    t.set_defaults(fn=_task)
    dd = sub.add_parser("daily")
    dd.add_argument("--day", type=int)
    def _daily(a):
        p = progress()
        day = a.day or int(p.get("day") or 1)
        p["day"] = day; save_progress(p)
        print(brief(day)); print(state_write()); print(page_link(day))
    dd.set_defaults(fn=_daily)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
