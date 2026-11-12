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

from curriculum_v5 import DAYS as COURSE_DAYS, source_day

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
    # Canonical completion comes from SQLite, never the last page viewed.
    db = ROOT / "data/state.db"
    if db.is_file():
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect("file:%s?mode=ro" % db, uri=True)) as conn:
            completed = {r[0] for r in conn.execute("SELECT day FROM sessions WHERE status='finished' AND passed=1")}
        return {"day": next((n for n in range(1, COURSE_DAYS + 1) if n not in completed), COURSE_DAYS)}
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
    template = out / "output-review.json"
    if not template.exists():
        sentence_ids = [x["id"] for x in read_jsonl(ROOT / "knowledge/seeds/sentences.jsonl") if source_day(x["day"]) == day][:3]
        template.write_text(json.dumps({"sentences":[{"id":sid,"text":"","feedback":""} for sid in sentence_ids],
            "grammar_sentences":[{"grammar_id":gid,"text":"","feedback":"","correct":False} for gid in (d["new_grammar_ids"]*2)[:2]],
            "vocab_check":[{"id":vid,"text":"","feedback":""} for vid in d.get("core_vocab_ids",d["new_vocab_ids"])[:3]]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    p = out / "brief.md"
    L = ["# Day %03d 任务书" % day, "",
         "- 阶段：%s｜%d 分钟｜%s" % (d["phase"], d["minutes"], "听力日" if d.get("listening") else "常规日"),
         "- 今日页面：%s" % page_link(day),
         "- Can-do：%s" % d["can_do"], "",
         "## 今天要学", ""]
    if d.get("practice_note"):
        L.extend([d["practice_note"], ""])
    L.append("### 必学新词 %d · 拓展 %d（自选）" % (len(d.get("core_vocab_ids", d["new_vocab_ids"])),len(d.get("extension_vocab_ids", []))))
    for vid in d.get("core_vocab_ids", d["new_vocab_ids"]):
        v = vocab[vid]
        ko = "｜韩语参考：%s" % (v.get("ko_hint") or v.get("ko_hanja")) if (v.get("ko_hint") or v.get("ko_hanja")) else ""
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
    L.append("会话开始同步后读取 `data/review/CONTEXT.md` 和 `data/review/context.json`，优先真实 FSRS 到期项；页面内容是课程复习资源。")
    L += ["", "## 会话流程（18 分钟）", "",
          "1. **先发页面链接**，等学生看完，不要一上来讲课。",
          "2. 只回答学生问的，不复述页面。",
          "3. 网页练习均为选择题：以当天网页整块练习为准；时间不足先做必学内容，余题回头补。",
          "4. 拉取或导入choice模式作答后，CLI自动按必做题完整性和70%正确率计算当天完成，不要求手写或confirm-output。",
          "5. 会话优先解释错题；有余力可口头复述或造句，不作为网页完成的前置条件。",
          "6. 写 `days/day-%03d/report.md` 记录难点；未答齐或未达标就补做，不降低难度。" % day,
          "7. 会话结束执行 `python3 scripts/nh80.py study-sync --push-only`，检查发布结果。",
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
          "  - data/review/CONTEXT.md", "  - data/review/context.json",
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


def state_write(day_override=None):
    ensure_dirs()
    p = progress()
    day = day_override or int(p.get("day") or 1)
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
         "- 当前：Day %03d / %d（%s %s）" % (day, COURSE_DAYS, d["phase"], d["phase_name"]),
         "- 今日：days/day-%03d/brief.md ｜ %d 分钟 ｜ %s" % (day, d["minutes"], "听力日" if d.get("listening") else "常规日"),
         "- 今日页面：%s" % page_link(day),
         "- Can-do：%s" % d["can_do"],
         "- 本日摘要：%s" % ("；".join(summary) if summary else "无（还没写日报）"),
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
    dd.add_argument("--sync", action="store_true", help="先从云端拉取，使用本机密钥，不回显")
    def _daily(a):
        if a.sync:
            import subprocess, sys
            subprocess.run([sys.executable,str(ROOT/"scripts/nh80.py"),"study-sync"],check=True)
        p = progress()
        day = a.day or int(p.get("day") or 1)
        p["day"] = day; save_progress(p)
        print(brief(day)); print(state_write(day)); print(page_link(day))
        print("复习上下文：data/review/CONTEXT.md；data/review/context.json（需显式读取）")
        print("会话结束：python3 scripts/nh80.py study-sync --push-only")
    dd.set_defaults(fn=_daily)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
