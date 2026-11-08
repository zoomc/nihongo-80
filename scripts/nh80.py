#!/usr/bin/env python3
"""nh80.py — Nihongo 80 唯一状态写入入口 / 命令行。

用法速查：
  python3 scripts/nh80.py init      # 150 天 v5
  python3 scripts/nh80.py build
  python3 scripts/nh80.py start-day 1
  python3 scripts/nh80.py answer --day 1 --q Q0001 --answer "です"
  python3 scripts/nh80.py grade-open --q Q0010 --correct 1
  python3 scripts/nh80.py import-web-result 'NH80R1.xxxx'
  python3 scripts/nh80.py finish-day 1 --minutes 58
  python3 scripts/nh80.py gate --day 7
  python3 scripts/nh80.py sync-web
  python3 scripts/nh80.py adjust --day 7
  python3 scripts/nh80.py report --week 1
  python3 scripts/nh80.py status
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import core  # noqa: E402
import curriculum as curr  # noqa: E402
import learning  # noqa: E402
import report as rpt  # noqa: E402
from core import audit, connect, export_state, iso, jdump, now_utc, root_of  # noqa: E402

OPEN_TYPES = {"free_production", "dialogue", "translate"}


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def _curriculum_payload(conn, day):
    r = conn.execute("SELECT payload FROM curriculum_days WHERE day=?", (day,)).fetchone()
    if not r:
        raise ValueError("curriculum_days 无 Day %d，请先运行 build" % day)
    return json.loads(r["payload"])


def ensure_session_schema(conn):
    """sessions.passed 兜底迁移（幂等）：core.SCHEMA 尚未加列时也不会崩。

    完成状态契约（REVISION_CONTRACT §6）：passed=1 → finished；passed=0 → incomplete。
    """
    conn.execute("CREATE TABLE IF NOT EXISTS output_reviews(day INTEGER PRIMARY KEY, reviewed_at TEXT NOT NULL, payload TEXT NOT NULL)")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
    if "passed" not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN passed INTEGER")
        conn.commit()


def completion_counts(conn):
    """(completed_days, incomplete_days)，只认 status='finished' AND passed=1。"""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
    if "passed" in cols:
        done = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE status='finished' AND passed=1").fetchone()[0]
    else:
        done = conn.execute("SELECT COUNT(*) FROM sessions WHERE status='finished'").fetchone()[0]
    inc = conn.execute("SELECT COUNT(*) FROM sessions WHERE status='incomplete'").fetchone()[0]
    return int(done or 0), int(inc or 0)


def _gate(conn, day, payload):
    """调用 learning.gate；别的任务尚未实现时降级为空 blocked，不阻断 start-day。"""
    fn = getattr(learning, "gate", None)
    if not callable(fn):
        return {"blocked": [], "deferred_grammar_ids": [], "actions": [],
                "available": False, "reason": "learning.gate 尚未实现"}
    try:
        conn.execute("SAVEPOINT nh80_gate")
        sp = True
    except Exception:
        sp = False
    try:
        g = fn(conn, day, payload)
    except Exception as e:   # 课程/状态字段未就绪时也不许阻断当天开始
        if sp:
            try:
                conn.execute("ROLLBACK TO nh80_gate")
                conn.execute("RELEASE nh80_gate")
            except Exception:
                pass
        return {"blocked": [], "deferred_grammar_ids": [], "actions": [],
                "available": False, "reason": "learning.gate 调用失败：%s" % e}
    if sp:
        try:
            conn.execute("RELEASE nh80_gate")
        except Exception:
            pass
    if not isinstance(g, dict):
        return {"blocked": [], "deferred_grammar_ids": [], "actions": [],
                "available": False, "reason": "learning.gate 返回结构不合法"}
    g.setdefault("blocked", [])
    g.setdefault("deferred_grammar_ids", [])
    g.setdefault("actions", [])
    g["available"] = True
    return g


def _norm_answer(s):
    """与前端 norm() 同构；优先使用 learning.norm_answer()，缺失时本地兜底。"""
    fn = getattr(learning, "norm_answer", None)
    if callable(fn):
        try:
            return fn(s)
        except Exception:
            pass
    v = unicodedata.normalize("NFKC", str(s if s is not None else ""))
    v = re.sub(r"[\s\u3000]+", "", v).replace("，", ",")
    return re.sub(r"[。．.！!？?]+$", "", v)


def _grade_objective(raw, answer):
    """服务端权威判分；前端 correct 一律不采信（契约 §3.2）。"""
    fn = getattr(learning, "grade_objective", None)
    if callable(fn):
        return fn(raw, answer)
    t = raw.get("type")
    if t in OPEN_TYPES:
        return None
    std = raw.get("answer")
    if std is None or std == "":
        return None
    return _norm_answer(answer) == _norm_answer(std)


def record_open_pending(conn, *, day, session_id, qid, raw, answer, hinted,
                        seconds, source):
    """开放题挂起：只写 correct=NULL 的原始作答，不推进掌握、不建卡。

    直接写库是为了覆盖 translate（learning.grade_objective 可能仍会对有
    standard answer 的翻译题自动判分）；等 grade-open 再走权威判分。
    """
    dup = conn.execute("SELECT id FROM attempts WHERE session_id=? AND qid=?",
                       (session_id, qid)).fetchone()
    if dup:
        return {"duplicate": True, "open_pending": True, "qid": qid}
    kids = raw.get("knowledge_ids") or []
    conn.execute("""INSERT INTO attempts(day,session_id,qid,question_id,knowledge_ids,answer,
        correct,error_type,hinted,seconds,rating,created_at,source)
        VALUES(?,?,?,?,?,?,NULL,NULL,?,?,NULL,?,?)""",
                 (day, session_id, qid, qid, jdump(kids), str(answer),
                  int(bool(hinted)), int(seconds or 0), iso(), source))
    audit(conn, "record_attempt", {"day": day, "qid": qid, "correct": None,
                                   "open_pending": True, "error_type": None})
    return {"ok": True, "qid": qid, "correct": None, "open_pending": True}


def _learn_sections(d):
    """从课程 payload 生成三段「可学内容」briefing：
    今天要会的 3 句话 / 今日复习清单（具体词 + 原因） / 中文难点提示。
    与网页首屏读到的 lesson_core / review_plan / teaching_notes 同源，不在此编造日语。
    用 .get 兜底，旧 payload 缺字段时也能优雅降级。"""
    lines = ["## 今天要会的 3 句话", ""]
    core = d.get("lesson_core") or []
    if core:
        for i, s in enumerate(core[:3], 1):
            kana = s.get("kana", "")
            lines.append("- 第 %d 句：%s%s" % (
                i, s.get("ja", ""), ("（读音：%s）" % kana) if kana else ""))
            lines.append("    - 中文：%s" % s.get("zh", ""))
            if s.get("note_zh"):
                lines.append("    - 提示：%s" % s["note_zh"])
            if s.get("audio_text"):
                lines.append("    - 朗读（TTS）：%s" % s["audio_text"])
    else:
        lines.append("- （课程未提供，请打开网页查看）")
    lines += ["", "## 今日预习建议（非 FSRS 到期项）", ""]
    rp = d.get("review_plan") or []
    if rp:
        for it in rp:
            kana = it.get("kana", "")
            word = it.get("surface", "") + (("（%s）" % kana) if kana else "")
            lines.append("- %s ｜ 中文：%s ｜ %s ｜ Day %d 学的 ｜ %s" % (
                word, it.get("zh", ""), it.get("reason_zh", ""),
                it.get("learned_day", 0), it.get("next_hint_zh", "")))
    else:
        lines.append("- 今天没有预习建议；真实复习以「动态任务」里的 FSRS 到期为准。")
    lines += ["", "## 中文难点提示", ""]
    tn = d.get("teaching_notes") or []
    if tn:
        for t in tn:
            lines.append("- " + t)
    else:
        lines.append("- 今天没有额外的中文难点提示。")
    lines.append("")
    return lines


def _ensure_session(conn, day, session_id=None):
    ensure_session_schema(conn)
    r = conn.execute("SELECT * FROM sessions WHERE day=?", (day,)).fetchone()
    if r:
        return r["session_id"]
    sid = session_id or ("session-%s-%03d" % (now_utc().strftime("%Y%m%d"), day))
    conn.execute("""INSERT INTO sessions(day,session_id,started_at,planned_minutes,status,attempts,summary,payload,passed)
        VALUES(?,?,?,?,?,?,?,?,NULL)""",
                 (day, sid, iso(), 60, "in_progress", 0, "", jdump({})))
    audit(conn, "start_session", {"day": day, "session_id": sid})
    return sid


def cmd_init(args):
    r = root_of(args.root)
    d = core.init_db(r)
    s = core.import_seeds(r)
    cfg = r / "config"; cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "settings.json").write_text(json.dumps({
        "schema": 1, "minutes_per_day": 60, "desired_retention": 0.9,
        "mastery_threshold": learning.MASTERY_THRESHOLD, "fsrs": "py-fsrs 6.3.1 (MIT, vendored)",
        "enable_fuzzing": False, "delay_min_days": learning.DELAY_MIN_DAYS,
        "transfer_min_delayed": learning.TRANSFER_MIN_DELAYED,
        "transfer_min_contexts": learning.TRANSFER_MIN_CONTEXTS,
        "transfer_min_span_days": learning.TRANSFER_MIN_SPAN_DAYS,
        "semantic_search": "disabled by design (see CONTRACTS.md 14.6)",
        "native_language": "zh", "other_languages": ["ko"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    conn = connect(r)
    try:
        ensure_session_schema(conn)
        data = _build_v5(r, conn)
        export_state(conn, r)
    finally:
        conn.close()
    site = cmd_build(args, quiet=True)
    out({"ok": True, "db": d["db"], "seeds": s,
         "curriculum": {"days": len(data["days"]), "validation": True},
         "site": site})


def _build_v5(root, conn):
    """v5 生成 150 天课程并写入 DB；返回 curriculum data。"""
    import hashlib
    import curriculum_v5 as c5
    data = c5.build()
    from quiz_v5 import day_questions
    from sentence_choices import build_for_day as sentence_questions
    from practice_v9 import build_daily, build_unit
    sentence_rows = core.read_jsonl(root / "knowledge/seeds/sentences.jsonl")
    tables = {name: {x["id"]: x for x in core.read_jsonl(root / "knowledge/seeds" / (name + ".jsonl"))}
              for name in ("vocabulary", "grammar", "kanji", "materials")}
    keys = {}
    grade_shards = {}
    with conn:
        for day in data["days"]:
            qs = day_questions(day, tables["vocabulary"], tables["grammar"], tables["kanji"], tables["materials"])
            sqs = sentence_questions(day, sentence_rows)
            day["question_ids"] = [q["qid"] for q in qs] + [q["qid"] for q in sqs if not q["optional"]]
            practice = build_daily(day, tables["vocabulary"], tables["grammar"], tables["kanji"])
            if day["day"] % 5 == 0:
                practice += build_unit(day["day"], data["days"], tables["vocabulary"],
                                       tables["grammar"], tables["kanji"])["questions"]
            shard = {}
            grade_shards[day["day"]] = shard
            for q in qs + sqs + practice:
                q["prompt_ja"] = q["prompt"]
                q["source"] = "v5-generated"
                q["review_status"] = "ai_draft"
                q["day"] = day["day"]
                if q["knowledge_ids"]:
                    q["targets"] = [{"id": kid, "capability": q.get("capability") or ("reading" if kid.startswith("K") else "meaning")}
                                    for kid in q["knowledge_ids"]]
                else:
                    q["evidence_only"] = True
                core._insert_kind(conn, "questions", q)
                keys[q["qid"]] = {"day": day["day"], "type": "mcq", "answer": q["answer"]}
                shard[q["qid"]] = {"day": day["day"], "type": "mcq",
                                   "answer_hash": hashlib.sha256(_norm_answer(q["answer"]).encode("utf-8")).hexdigest(),
                                   "knowledge_ids": q["knowledge_ids"],
                                   "capability": q.get("capability")}
        audit(conn, "build_v5_questions", {"count": len(keys)})
        # 清掉历史题库/旧构建遗留的孤儿题，避免 import-web-result 接受不在本次答案表里的题号。
        stale = [row[0] for row in conn.execute("SELECT id FROM questions").fetchall()
                 if row[0] not in keys]
        if stale:
            conn.executemany("DELETE FROM questions WHERE id=?", [(qid,) for qid in stale])
            audit(conn, "purge_stale_questions", {"count": len(stale)})
        core.import_curriculum(conn, data)
    (root / "curriculum/curriculum.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (root / "deploy/worker/src/generated-key.json").write_text(jdump({"answers": keys}) + "\n", encoding="utf-8")
    grade_dir = root / "web/data/grade"
    grade_dir.mkdir(parents=True, exist_ok=True)
    for day, answers in grade_shards.items():
        (grade_dir / ("day-%03d.json" % day)).write_text(jdump({"answers": answers}) + "\n", encoding="utf-8")
    return data


def cmd_build(args, quiet=False):
    r = root_of(args.root)
    conn = connect(r)
    try:
        ensure_session_schema(conn)
        data = _build_v5(r, conn)
    finally:
        conn.close()
    import build_v5_site as s5
    s5.main()
    if not quiet:
        out({"ok": True, "curriculum_days": len(data["days"]), "validation_errors": 0,
             "site_output": "v5: %d 天页面" % len(data["days"])})
    return {"ok": True, "days": len(data["days"])}


def cmd_start_day(args):
    r = root_of(args.root); day = args.day
    conn = connect(r)
    try:
        d = _curriculum_payload(conn, day)
        sid = _ensure_session(conn, day)
        due = learning.due_queue(conn, limit=30)
        recent_err = [dict(x) for x in conn.execute(
            "SELECT qid,error_type,remedy,created_at FROM mistakes ORDER BY id DESC LIMIT 8").fetchall()]
        prev = conn.execute("SELECT summary FROM daily_summary WHERE day<? ORDER BY day DESC LIMIT 1",
                            (day,)).fetchone()
        mastered = [x["knowledge_id"] for x in conn.execute(
            "SELECT knowledge_id FROM knowledge_state WHERE mastered=1 LIMIT 40").fetchall()]
        adj = conn.execute("SELECT after_json FROM plan_adjustments ORDER BY id DESC LIMIT 1").fetchone()
        g = _gate(conn, day, d)   # 先修门控：缺实现时降级为空 blocked（不阻断开课）
        conn.commit()
        blocked = g.get("blocked") or []
        gate_lines = []
        if blocked:
            for b in blocked:
                if not isinstance(b, dict):
                    continue
                gate_lines.append("- 被推迟的新语法：`%s`｜先修 `%s` 目前 `%s`，需先到 `independent_recall`" % (
                    b.get("kid", "?"), b.get("prereq", "?"),
                    b.get("prereq_stage", "unseen")))
            gate_lines.append("- 处理：**先补先修，当天不推进被推迟的新语法**；" 
                              "`finished` 判定不因推迟而放水（仍需完成原定题量与正确率）。")
        else:
            gate_lines.append("- 无被推迟的新语法（或门控尚未启用），按原计划推进。")
        for a in (g.get("actions") or [])[:6]:
            if isinstance(a, dict):
                gate_lines.append("- 调整建议：%s — %s" % (a.get("type", "action"), a.get("detail", "")))
        brief = [
            "# Day %03d 教学 Briefing（由脚本生成，不是 AI 编的）" % day, "",
            "- 会话 ID：`%s`｜预算：%d 分钟｜测试：%s" % (sid, d["minutes"], d["assessment"]),
            "- 主题：%s" % d["theme"], "- 场景：%s" % d["scene"], "",
            "- **Can-do（本日真实任务）**：%s" % d.get("can_do", ""),
            "- 能力侧重：%s｜方法论：`research/nh80_framework.md`" % "、".join(d.get("focus", [])),
            "", * _learn_sections(d),
            "## 门控（先补先修）", "", *gate_lines, "",
            "## 固定骨架（curriculum.json）", "",
            *["- " + x for x in d["objectives"]],
            "- 新知识 ID：%s" % ("、".join(d["new_vocab_ids"] + d["new_grammar_ids"] + d["new_kanji_ids"]) or "无"),
            "- 复习候选池：%s" % ("、".join(d["review_knowledge_ids"]) or "无"),
            "- 素材 ID：%s" % ("、".join(d["material_ids"]) or "无"),
            ("- 练习：网页内按当天内容生成（6 题，答案哈希校验）"
             if d.get("question_ids") and str(d["question_ids"][0]).startswith("web-")
             else "- 测验题 ID：%s" % "、".join(d["question_ids"])),
            "", "## 动态任务（state.db，权威）", "",
            "- FSRS 到期：%d 项" % len(due),
            *["  - `%s` due=%s stage=%s" % (x["knowledge_id"], x["due"], x["stage"]) for x in due[:12]],
            "- 最近错题：%d 条" % len(recent_err),
            *["  - %s / %s → %s" % (x["qid"], x["error_type"], x["remedy"]) for x in recent_err[:5]],
            "- 已判定掌握：%d 项（%s）" % (len(mastered), "、".join(mastered[:8])),
            "- 上一日总结：%s" % (prev["summary"][:300] if prev else "**无**（首日或尚未 finish-day）"),
            "- 最近调整：%s" % (adj["after_json"][:300] if adj else "无"),
            "", "## 时间块", "",
            *["- %d 分钟 · %s — %s" % (b["min"], b["type"], b["desc"]) for b in d["blocks"]],
            "", "## 教师必须执行", "",
            "1. 先让学生思考/作答，再揭示答案与解析；每次只推进一步，不一次输出几十屏。",
            "2. 每次作答经 `answer` / `import-web-result` 写库；开放题必须 `grade-open` 补录判定。",
            "3. 错误必须标注 error_type；连续答对提高难度；保证足够独立输出。",
            "4. 结束运行 `finish-day %d`，状态才会落盘供次日会话读取。" % day,
            "5. 完成条件：%s" % d["completion"], "",
        ]
        p = r / "sessions" / ("day-%03d-brief.md" % day)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(brief), encoding="utf-8")
        if not args.json:
            print("\n".join(brief))
        else:
            out({"ok": True, "day": day, "session_id": sid, "brief": str(p),
                 "due": len(due), "assessment": d["assessment"],
                 "gate": {"blocked": g.get("blocked") or [],
                          "deferred_grammar_ids": g.get("deferred_grammar_ids") or [],
                          "available": bool(g.get("available"))}})
    finally:
        conn.close()


def _session_for(conn, day=None, session=None):
    if session:
        return session
    if day:
        r = conn.execute("SELECT session_id FROM sessions WHERE day=?", (day,)).fetchone()
        if r:
            return r["session_id"]
    r = conn.execute("SELECT session_id FROM sessions ORDER BY day DESC LIMIT 1").fetchone()
    if r:
        return r["session_id"]
    raise ValueError("无会话，请先运行 start-day")


def cmd_answer(args):
    r = root_of(args.root)
    conn = connect(r)
    try:
        sid = _session_for(conn, args.day, args.session)
        res = learning.record_attempt(
            conn, day=args.day or 1, session_id=sid, qid=args.q,
            answer=args.answer, correct=None if args.pending else args.correct,
            hinted=args.hinted, seconds=args.seconds, error_type=args.error_type,
            feedback=args.feedback or "", source="cli")
        conn.commit()
        out(res)
    finally:
        conn.close()


def cmd_grade_open(args):
    r = root_of(args.root)
    conn = connect(r)
    try:
        if args.session:
            sid = args.session
        else:
            row = conn.execute("SELECT session_id FROM attempts WHERE qid=? AND correct IS NULL LIMIT 1",
                               (args.q,)).fetchone()
            if not row:
                out({"ok": False, "reason": "没有待判分的开放题"}); return
            sid = row["session_id"]
        res = learning.grade_open(conn, session_id=sid, qid=args.q,
                                  correct=bool(args.correct),
                                  error_type=args.error_type or "other",
                                  feedback=args.feedback or "")
        conn.commit()
        out(res)
    finally:
        conn.close()


def _decode_payload(code: str) -> dict:
    if not code.startswith("NH80R1."):
        raise ValueError("回传码必须以 NH80R1. 开头")
    raw = code[len("NH80R1."):]
    pad = "=" * (-len(raw) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(raw + pad).decode("utf-8"))
    except Exception as e:
        raise ValueError("回传码无法解码：%s" % e) from e
    if not isinstance(data, dict) or data.get("v") != 1:
        raise ValueError("回传码版本/结构不合法")
    for k in ("day", "session", "ts", "results", "minutes", "source"):
        if k not in data:
            raise ValueError("回传码缺字段 %s" % k)
    if not isinstance(data["results"], list) or isinstance(data["day"], bool) or not isinstance(data["day"], int) or not 1 <= data["day"] <= 150:
        raise ValueError("回传码字段类型不合法")
    if not isinstance(data["session"], str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{3,96}", data["session"]):
        raise ValueError("会话ID不合法")
    if len(data["results"]) > 40 or any(not isinstance(x, dict) or not isinstance(x.get("qid"), str) for x in data["results"]):
        raise ValueError("作答结构不合法")
    return data


def cmd_import_web(args):
    r = root_of(args.root)
    data = _decode_payload(args.code.strip().strip("'\""))
    conn = connect(r)
    try:
        ensure_session_schema(conn)
        qmap = {}
        for x in conn.execute("SELECT id,type,raw FROM questions").fetchall():
            try:
                raw = json.loads(x["raw"] or "{}")
            except (TypeError, ValueError):
                raw = {}
            if not isinstance(raw, dict):
                raw = {}
            raw.setdefault("type", x["type"])
            qmap[x["id"]] = {"type": x["type"], "raw": raw}
        unknown = [x.get("qid") for x in data["results"] if x.get("qid") not in qmap]
        if unknown:
            raise ValueError("回传码含未知题目 id，拒绝导入：%s" % unknown[:5])
        # 没有 day 的题（历史题库残留）一律拒绝，不再用 payload 的 day 兜底。
        wrong_day = [x["qid"] for x in data["results"]
                     if qmap[x["qid"]]["raw"].get("day") != data["day"]]
        if wrong_day:
            raise ValueError("题目不属于当天，拒绝导入")
        _ensure_session(conn, data["day"], data["session"])
        sid = data["session"]  # 原始浏览器会话不能被按天的日程会话覆盖
        applied, dup, pending = [], [], []
        regraded, disagreements, hinted_forced = [], [], []
        valid_err = getattr(learning, "ERROR_TYPES", None) or set()
        for x in data["results"]:
            qid = x["qid"]
            qtype = qmap[qid]["type"]
            is_open = qtype in OPEN_TYPES
            answer = str(x.get("answer", ""))
            client_correct = x.get("correct")
            revealed = bool(x.get("revealed_before_submit"))
            client_hinted = bool(x.get("hinted"))
            # hinted 只能被上调：揭示过答案就一定是提示学习（契约 §3.2-3）。
            hinted = bool(client_hinted or revealed)
            if revealed and not client_hinted:
                hinted_forced.append(qid)
            if is_open:
                server_correct = None
            else:
                server_correct = _grade_objective(qmap[qid]["raw"], answer)
                if server_correct is None:
                    is_open = True   # 无标准答案：保守挂起，等 grade-open
                elif client_correct is not None and bool(client_correct) != bool(server_correct):
                    disagreements.append({"qid": qid, "client_correct": bool(client_correct),
                                          "server_correct": bool(server_correct),
                                          "answer": answer[:120]})
            et = x.get("error_type") or None
            if et and valid_err and et not in valid_err:
                et = None
            if is_open:
                res = record_open_pending(
                    conn, day=data["day"], session_id=sid, qid=qid,
                    raw=qmap[qid]["raw"], answer=answer, hinted=hinted,
                    seconds=int(x.get("seconds") or 0), source="web")
            elif qmap[qid]["raw"].get("evidence_only"):
                duplicate = conn.execute("SELECT 1 FROM attempts WHERE session_id=? AND qid=?", (sid, qid)).fetchone()
                if not duplicate:
                    conn.execute("""INSERT INTO attempts(day,session_id,qid,question_id,knowledge_ids,answer,
                        correct,hinted,seconds,created_at,source) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (data["day"], sid, qid, qid, "[]", answer, int(bool(server_correct)), int(hinted),
                         int(x.get("seconds") or 0), iso(), "web"))
                    audit(conn, "record_comprehension", {"day": data["day"], "qid": qid, "correct": server_correct})
                res = {"duplicate": bool(duplicate)}
            else:
                res = learning.record_attempt(
                    conn, day=data["day"], session_id=sid, qid=qid, answer=answer,
                    correct=bool(server_correct), hinted=hinted,
                    seconds=int(x.get("seconds") or 0), error_type=et, source="web")
            regraded.append({"qid": qid, "client_correct": None if client_correct is None else bool(client_correct),
                             "server_correct": server_correct, "open_pending": bool(is_open)})
            (dup if res.get("duplicate") else pending if (is_open or res.get("open_pending")) else applied).append(qid)
        # 原始草稿仅供教师批改，不自动评分或计完成。
        drafts = data.get("sentences") or []
        valid_sentences = {x["id"] for x in core.read_jsonl(r / "knowledge/seeds/sentences.jsonl")
                           if x.get("day") == data["day"]}
        drafts = [{"id": x["id"], "text": str(x.get("text") or "")}
                  for x in drafts if isinstance(x, dict) and x.get("id") in valid_sentences]
        if drafts:
            path = r / "days" / ("day-%03d" % data["day"])
            path.mkdir(parents=True, exist_ok=True)
            (path / "web-drafts.json").write_text(jdump({"session": sid, "drafts": drafts}) + "\n", encoding="utf-8")
            audit(conn, "import_web_drafts", {"day": data["day"], "count": len(drafts)})
        # v3：网页「今日复习」三档自评 → FSRS 排期（只排期，不判掌握）
        review_applied, review_dup, review_bad = [], [], []
        rate_fn = getattr(learning, "apply_review_rating", None)
        for x in data.get("review_ratings") or []:
            if not isinstance(x, dict):
                continue
            kid = str(x.get("kid") or "")
            label = str(x.get("rating") or "")
            if not kid or not label:
                continue
            if not callable(rate_fn):
                review_bad.append("%s(learning.apply_review_rating 尚未实现)" % kid)
                continue
            try:
                res = rate_fn(conn, kid=kid, label=label, day=data["day"], session_id=sid)
                (review_dup if res.get("duplicate") else review_applied).append(kid)
            except (ValueError, KeyError, TypeError) as e:
                review_bad.append("%s(%s)" % (kid, e))
        if data.get("practice_mode") == "choice":
            # Explicit v8 web choice mode; never label this evidence as independent production.
            prior = conn.execute("SELECT payload FROM sessions WHERE day=?", (data["day"],)).fetchone()
            session_payload = json.loads(prior["payload"] or "{}")
            session_payload["practice_mode"] = "choice"
            conn.execute("UPDATE sessions SET payload=? WHERE day=?", (jdump(session_payload), data["day"]))
        conn.execute("UPDATE sessions SET minutes=? WHERE day=?", (data["minutes"], data["day"]))
        audit(conn, "import_web_result", {"day": data["day"], "session": data["session"],
                                          "n": len(data["results"]), "applied": len(applied),
                                          "pending": len(pending), "disagreements": len(disagreements),
                                          "hinted_forced": len(hinted_forced),
                                          "review_ratings": len(review_applied)})
        if disagreements:
            audit(conn, "import_web_disagreement", {"day": data["day"], "items": disagreements})
        conn.commit()
        choice_completion = None
        if data.get("practice_mode") == "choice":
            import io
            from contextlib import redirect_stdout
            with redirect_stdout(io.StringIO()) as completion_buffer:
                cmd_finish_day(argparse.Namespace(root=str(r),day=data["day"],minutes=data["minutes"]))
            choice_completion = json.loads(completion_buffer.getvalue())
        out({"ok": True, "day": data["day"], "session_id": sid,
             "choice_completion": choice_completion,
             "applied": applied, "duplicate_skipped": dup,
             "open_pending_need_ai_grade": pending,
             "regraded": regraded,
             "disagreements": disagreements,
             "hinted_forced": hinted_forced,
             "review_ratings_applied": review_applied,
             "review_ratings_duplicate": review_dup,
             "review_ratings_rejected": review_bad,
             "note": "服务端已用题库标准答案重新判分，前端 correct 只用于对账；"
                     "开放题一律挂起，需 grade-open 由 AI 判定；"
                     "复习三档自评只重排 FSRS 复习时间，不写 correct、不判掌握。"})
    finally:
        conn.close()


def cmd_import_file(args):
    import cloud_sync
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("导入文件必须为 JSON 对象")
    if "pending" in data:
        return _import_pending(args, data)
    data.setdefault("ts", iso()); data.setdefault("minutes", None); data.setdefault("source", "web-export")
    return cmd_import_web(argparse.Namespace(root=args.root, code=cloud_sync.encode_payload(data)))


def _import_pending(args, data):
    """导入 v9 离线队列；先核验全部记录，再交给既有判分路径。"""
    import cloud_sync
    from collections import OrderedDict
    from datetime import datetime

    items = data.get("pending")
    if data.get("version") != 1 or not isinstance(items, list) or len(items) > 20000:
        raise ValueError("离线队列版本或结构不合法")
    root = root_of(args.root)
    conn = connect(root, readonly=True)
    groups, ratings, sessions, result_ids, rating_ids = OrderedDict(), [], {}, {}, {}
    try:
        questions = {}
        for row in conn.execute("SELECT id,raw FROM questions"):
            raw = json.loads(row["raw"] or "{}")
            questions[row["id"]] = raw
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("离线队列记录不合法")
            if item.get("kind") == "attempt":
                day, session, result = item.get("day"), item.get("session"), item.get("result")
                if type(day) is not int or not 1 <= day <= 150 or not isinstance(session, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{3,96}", session) or not isinstance(result, dict):
                    raise ValueError("离线作答字段不合法")
                if session in sessions and sessions[session] != day:
                    raise ValueError("离线会话对应多个学习日")
                sessions[session] = day
                qid, answer = result.get("qid"), result.get("answer")
                if not isinstance(qid, str) or qid not in questions or questions[qid].get("day") != day:
                    raise ValueError("离线作答包含未知或非当天题目")
                if not isinstance(answer, str) or len(answer) > 2000:
                    raise ValueError("离线作答答案不合法")
                seconds = result.get("seconds")
                if seconds is not None and (type(seconds) is not int or not 0 <= seconds <= 86400):
                    raise ValueError("离线作答时间不合法")
                if any(k in result and not isinstance(result[k], bool) for k in ("hinted", "revealed_before_submit")):
                    raise ValueError("离线提示标记不合法")
                clean = {"qid": qid, "answer": answer, "hinted": result.get("hinted", False),
                         "revealed_before_submit": result.get("revealed_before_submit", False), "seconds": seconds}
                identity = (session, qid)
                if identity in result_ids and result_ids[identity] != (day, clean):
                    raise ValueError("同一会话题目出现冲突作答")
                result_ids[identity] = (day, clean)
                groups.setdefault((day, session), []).append(clean)
            elif item.get("kind") == "rating":
                row = item.get("review")
                if not isinstance(row, dict):
                    raise ValueError("离线自评字段不合法")
                kid, event_id, day, label = (row.get(x) for x in ("kid", "event_id", "day", "rating"))
                if not isinstance(kid, str) or not re.fullmatch(r"[VGK]\d{4}", kid) or not isinstance(event_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{3,96}", event_id) or type(day) is not int or not 1 <= day <= 150 or label not in ("again", "hard", "good"):
                    raise ValueError("离线自评字段不合法")
                table = {"V": "vocabulary", "G": "grammar", "K": "kanji"}[kid[0]]
                if not conn.execute("SELECT 1 FROM %s WHERE id=?" % table, (kid,)).fetchone():
                    raise ValueError("离线自评包含未知知识点")
                values = (kid, day, label)
                if event_id in rating_ids and rating_ids[event_id] != values:
                    raise ValueError("同一自评事件出现冲突")
                rating_ids[event_id] = values
                card = conn.execute("SELECT last_review FROM fsrs_cards WHERE knowledge_id=?", (learning.card_key(kid, learning.default_capability(kid)),)).fetchone()
                if card and card["last_review"]:
                    last = datetime.fromisoformat(card["last_review"].replace("Z", "+00:00"))
                    if last.tzinfo is None or last > learning.now_utc():
                        raise ValueError("FSRS last_review 晚于导入时间或缺少时区")
                ratings.append(row)
            else:
                raise ValueError("未知离线队列记录类型")
        for day, _session in groups:
            if not conn.execute("SELECT 1 FROM curriculum_days WHERE day=?", (day,)).fetchone():
                raise ValueError("离线作答对应的课程不存在")
    finally:
        conn.close()
    sessions_out = []
    for (day, session), rows in groups.items():
        for offset in range(0, len(rows), 40):
            payload = {"v": 1, "day": day, "session": session, "ts": iso(), "minutes": None,
                       "source": "web-export", "practice_mode": "teacher" if session.startswith("replay-") else "choice",
                       "results": rows[offset:offset + 40]}
            sessions_out.append(cloud_sync.import_session(root, payload, sys.modules[__name__]))
    conn = connect(root)
    try:
        applied, duplicates = 0, 0
        with conn:
            for row in ratings:
                result = learning.apply_review_rating(conn, kid=row["kid"], label=row["rating"], day=row["day"],
                            session_id="rating-" + row["event_id"], at=learning.now_utc())
                if result.get("duplicate"):
                    duplicates += 1
                else:
                    applied += 1
            audit(conn, "import_offline_queue", {"attempts": sum(map(len, groups.values())), "ratings": len(ratings),
                                                "ratings_applied": applied, "ratings_duplicate": duplicates})
    finally:
        conn.close()
    out({"ok": True, "attempts": sum(map(len, groups.values())), "sessions": sessions_out,
         "ratings_applied": applied, "ratings_duplicate": duplicates})


def cmd_confirm_output(args):
    """教师录入真实独立产出与反馈；不接受只有完成勾选。"""
    r = root_of(args.root)
    payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
    conn = connect(r)
    try:
        ensure_session_schema(conn)
        d = _curriculum_payload(conn, args.day)
        valid = {x["id"] for x in core.read_jsonl(r / "knowledge/seeds/sentences.jsonl") if x["day"] == args.day}
        for field, count in (("sentences", 3), ("grammar_sentences", 2), ("vocab_check", 3)):
            rows = payload.get(field, [])
            if not isinstance(rows, list) or len(rows) < count:
                raise ValueError("%s 至少%d条真实产出" % (field, count))
            for item in rows:
                if not isinstance(item, dict) or not str(item.get("text", "")).strip() or not str(item.get("feedback", "")).strip():
                    raise ValueError("产出原文与教师反馈不能为空")
        ids = [x.get("id") for x in payload["sentences"]]
        if len(set(ids)) < 3 or not set(ids) <= valid:
            raise ValueError("需要当天三道不同句子及批改")
        sid = "output-%03d-%s" % (args.day, __import__("hashlib").sha256(jdump(payload).encode()).hexdigest()[:12])
        with conn:
            _ensure_session(conn, args.day)
            for i, item in enumerate(payload["grammar_sentences"][:2]):
                gid = d["new_grammar_ids"][min(i, len(d["new_grammar_ids"])-1)]
                qid = "O-%03d-%d" % (args.day, i)
                raw = {"id": qid, "type": "free_production", "knowledge_ids": [gid],
                       "targets": [{"id": gid, "capability": "production"}], "day": args.day,
                       "rubric": "教师核对语法接续、意义及独立产出"}
                core._insert_kind(conn, "questions", raw)
                if not isinstance(item.get("correct"), bool):
                    raise ValueError("每条语法造句须有教师correct布尔评分")
                learning.record_attempt(conn, day=args.day, session_id=sid, qid=qid,
                                        answer=item["text"], correct=item["correct"],
                                        feedback=item["feedback"], source="teacher")
            payload["accepted"] = all(x["correct"] for x in payload["grammar_sentences"][:2])
            conn.execute("INSERT OR REPLACE INTO output_reviews VALUES(?,?,?)", (args.day, iso(), jdump(payload)))
            audit(conn, "confirm_output", {"day": args.day, "sentences": len(ids), "grammar": 2, "vocab_check": 3})
        out({"ok": True, "day": args.day, "output_confirmed": payload["accepted"]})
    finally:
        conn.close()


def cmd_finish_day(args):
    r = root_of(args.root); day = args.day
    conn = connect(r)
    try:
        ensure_session_schema(conn)
        sid = _session_for(conn, day, None)
        rows = [dict(x) for x in conn.execute("SELECT * FROM attempts WHERE day=? ORDER BY id", (day,)).fetchall()]
        graded = [x for x in rows if x["correct"] is not None]
        pending = [x["qid"] for x in rows if x["correct"] is None]
        acc = round(sum(x["correct"] for x in graded) / len(graded), 4) if graded else None
        errs = {}
        for x in rows:
            if x["correct"] == 0:
                errs[x["error_type"] or "other"] = errs.get(x["error_type"] or "other", 0) + 1
        d = _curriculum_payload(conn, day)
        expected = set(d["question_ids"])
        answered = {x["qid"] for x in graded}
        # 只按当前课程每题最新一次作答判定，历史重做不稀释本次结果。
        latest = {}
        for row in rows:
            if row["qid"] in expected:
                latest[row["qid"]] = row
        scored = [x for x in latest.values() if x["correct"] is not None]
        acc = round(sum(x["correct"] for x in scored) / len(scored), 4) if scored else None
        output_review = conn.execute("SELECT payload FROM output_reviews WHERE day=?", (day,)).fetchone()
        output_confirmed = bool(output_review and json.loads(output_review["payload"]).get("accepted"))
        daily_payload = json.loads(conn.execute("SELECT payload FROM sessions WHERE day=?", (day,)).fetchone()["payload"] or "{}")
        choice_mode = daily_payload.get("practice_mode") == "choice"
        passed = (acc is not None and acc >= 0.70 and bool(expected) and expected <= {x["qid"] for x in scored}
                  and (choice_mode or output_confirmed))
        status = "finished" if passed else "incomplete"
        summary = ("Day %d 完成：作答 %d（已判分 %d），正确率 %s，错误 %s。"
                   "完成条件 %s。%s") % (
            day, len(rows), len(graded),
            ("%.2f" % acc) if acc is not None else "无",
            (", ".join("%s:%d" % kv for kv in errs.items()) or "无"),
            "达标" if passed else "**未达标（status=incomplete，不计完成天数；需 adjust 生成补救，不降低难度）**",
            ("待 AI 判分开放题：%s" % "、".join(pending)) if pending else "")
        with conn:
            conn.execute("""UPDATE sessions SET finished_at=?,minutes=?,status=?,passed=?,accuracy=?,attempts=?,summary=?
                WHERE day=?""", (iso(), args.minutes, status, 1 if passed else 0, acc, len(rows), summary, day))
            conn.execute("INSERT OR REPLACE INTO daily_summary(day,summary,ts,payload) VALUES(?,?,?,?)",
                         (day, summary, iso(), jdump({"accuracy": acc, "errors": errs,
                                                      "passed": passed, "status": status,
                                                      "pending": pending})))
            audit(conn, "finish_day", {"day": day, "attempts": len(rows), "accuracy": acc,
                                       "passed": bool(passed), "status": status})
        export_state(conn, r)
        completed, incomplete = completion_counts(conn)
        bk = None
        if day % 7 == 0:
            bk = core.backup(r)
        out({"ok": True, "day": day, "session_id": sid, "attempts": len(rows),
             "accuracy": acc, "passed": passed, "status": status,
             "completed_days": completed, "incomplete_days": incomplete,
             "pending_open": pending, "output_confirmed": output_confirmed, "practice_mode": "choice" if choice_mode else "teacher",
             "summary": summary, "backup": bk["backup"] if bk else None,
             "next": ("python3 scripts/nh80.py start-day %d" % (day + 1)) if day < 150 else "打开 resources.html 进行 N3 官方自测与薄弱项复习"})
    finally:
        conn.close()


def cmd_gate(args):
    r = root_of(args.root)
    conn = connect(r)
    try:
        d = _curriculum_payload(conn, args.day)
        g = _gate(conn, args.day, d)
        conn.commit()
        out({"ok": True, "day": args.day, "available": bool(g.get("available")),
             "blocked": g.get("blocked") or [],
             "deferred_grammar_ids": g.get("deferred_grammar_ids") or [],
             "actions": g.get("actions") or [],
             "reason": g.get("reason")})
    finally:
        conn.close()


def cmd_pull_cloud(args):
    """把云端 D1 的原始作答事件拉回本地重判入库（REVISION_CONTRACT §10）。"""
    r = root_of(args.root)
    import cloud_sync  # 延迟导入：没配 D1 的项目照常运行
    argv = ["pull", "--base", args.base, "--root", str(r)]
    import os
    keyfile = r / "deploy/.sync-key"
    if not args.key and not os.environ.get("NH80_SYNC_KEY") and keyfile.is_file():
        os.environ["NH80_SYNC_KEY"] = keyfile.read_text().strip()
    if args.key:
        argv += ["--key", args.key]
    if args.since:
        argv += ["--since", str(args.since)]
    if args.limit:
        argv += ["--limit", str(args.limit)]
    code = cloud_sync.main(argv)
    if code:
        raise SystemExit(code)


def cmd_study_sync(args):
    """Sync personal study records using the local key, never a command-line secret."""
    import study_sync
    r = root_of(args.root)
    keyfile = r / "deploy/.sync-key"
    try:
        key = keyfile.read_text(encoding="utf-8").strip()
    except OSError:
        raise ValueError("无法读取本机同步密钥 deploy/.sync-key") from None
    if not key:
        raise ValueError("本机同步密钥为空")
    out(study_sync.run(r, args.base, key, push_only=args.push_only))


def cmd_sync_web(args):
    """写库后重建站点：build 的显式别名（REVISION_CONTRACT §4）。"""
    res = cmd_build(args, quiet=True)
    out({"ok": True, "synced": True, "stdout": res.get("stdout", "")})


def cmd_status(args):
    r = root_of(args.root)
    conn = connect(r, readonly=True)
    try:
        m = learning.metrics(conn)
        completed, incomplete = completion_counts(conn)
        m["completed_days"] = completed
        m["incomplete_days"] = incomplete
        due = learning.due_queue(conn, limit=1000)
        cols = {x[1] for x in conn.execute("PRAGMA table_info(sessions)").fetchall()}
        sel = "day,status,accuracy,minutes" + (",passed" if "passed" in cols else "")
        sess = [dict(x) for x in conn.execute(
            "SELECT %s FROM sessions ORDER BY day" % sel).fetchall()]
        out({"ok": True, "metrics": m, "due_count": len(due),
             "sessions": sess[-10:], "db": str(core.db_path(r))})
    finally:
        conn.close()


def cmd_adjust(args):
    r = root_of(args.root)
    conn = connect(r)
    try:
        res = learning.adjust_plan(conn, args.day)
        conn.commit()
        out(res)
    finally:
        conn.close()


def cmd_report(args):
    r = root_of(args.root)
    conn = connect(r, readonly=True)
    try:
        if args.week:
            out(rpt.weekly(conn, args.week, r))
        elif args.stage:
            out(rpt.stage(conn, args.stage, r))
        elif args.final:
            out(rpt.final(conn, r))
        else:
            out({"ok": False, "reason": "需指定 --week / --stage / --final"})
    finally:
        conn.close()


def cmd_search(args):
    out(core.search(args.root, args.query, args.mode, args.limit))


def cmd_relation(args):
    conn = connect(args.root, readonly=True)
    try:
        out(core.relation_chain(conn, args.kid))
    finally:
        conn.close()


def cmd_validate(args):
    r = root_of(args.root)
    path = r / "curriculum/curriculum.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    days = data.get("days") or []
    errs, warns = [], []
    if len(days) != 150:
        errs.append("天数应为 150，实际 %d" % len(days))
    seeds = {name: {x["id"]: x for x in core.read_jsonl(r / "knowledge/seeds" / (name + ".jsonl"))}
             for name in ("vocabulary", "grammar", "kanji", "materials")}
    listening_seen = set()
    grammar_days = {gid: d["day"] for d in days for gid in d["new_grammar_ids"]}
    seen = {"v": set(), "g": set(), "k": set()}
    for d in days:
        if sum(b.get("min", 0) for b in d.get("blocks") or []) != 60:
            errs.append("Day %s 时间块不等于 60" % d.get("day"))
        if sum(b["min"] for b in d["blocks"] if b["type"] != "会话") != 42:
            errs.append("Day %s 网页预算不等于42" % d["day"])
        for gid in d["new_grammar_ids"]:
            for pre in seeds["grammar"].get(gid, {}).get("prerequisites", []):
                if pre not in grammar_days or grammar_days[pre] >= d["day"]:
                    errs.append("Day %s 先修未满足 %s -> %s" % (d["day"], gid, pre))
        if d.get("listening"):
            for mid in d["material_ids"]:
                m = seeds["materials"].get(mid, {})
                if mid in listening_seen or len(m.get("questions", [])) != 3 or len(m.get("text_ja", "")) < 300:
                    errs.append("Day %s 听力重复或缺内容/三题" % d["day"])
                listening_seen.add(mid)
        for key, field in (("v", "new_vocab_ids"), ("g", "new_grammar_ids"), ("k", "new_kanji_ids")):
            for kid in d.get(field) or []:
                table = {"v": "vocabulary", "g": "grammar", "k": "kanji"}[key]
                if kid not in seeds[table]:
                    errs.append("未知知识 id %s" % kid)
                if kid in seen[key]:
                    errs.append("Day %s 重复排课 %s" % (d.get("day"), kid))
                seen[key].add(kid)
    totals = {k: len(v) for k, v in seen.items()}
    if totals["v"] < 2700: errs.append("词汇排课不足 2700：%d" % totals["v"])
    if totals["g"] < 276: errs.append("语法排课不足 276：%d" % totals["g"])
    if totals["k"] < 620: errs.append("汉字排课不足 620：%d" % totals["k"])
    out({"ok": not errs, "error_count": len(errs), "errors": errs[:20], "warnings": warns,
         "days": len(days), "totals": totals,
         "listening_days": sum(1 for d in days if d.get("listening"))})
    if errs:
        raise ValueError("课程校验失败")


def cmd_backup(args): out(core.backup(args.root))
def cmd_restore(args): out(core.restore(args.root, args.path))
def cmd_audit(args): out(core.audit_tail(args.root, args.limit))


def main():
    p = argparse.ArgumentParser(description="Nihongo 80 唯一状态写入入口")
    p.add_argument("--root", default=None, help="项目根目录（默认脚本上级目录；测试可指临时目录）")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init").set_defaults(fn=cmd_init)
    sub.add_parser("build").set_defaults(fn=cmd_build)
    q = sub.add_parser("start-day"); q.add_argument("day", type=int); q.add_argument("--json", action="store_true"); q.set_defaults(fn=cmd_start_day)
    a = sub.add_parser("answer")
    a.add_argument("--day", type=int); a.add_argument("--q", required=True)
    a.add_argument("--answer", default=""); a.add_argument("--hinted", action="store_true")
    a.add_argument("--seconds", type=int, default=0); a.add_argument("--error-type", default=None)
    a.add_argument("--feedback", default=""); a.add_argument("--session", default=None)
    a.add_argument("--correct", type=int, default=None, choices=[0, 1])
    a.add_argument("--pending", action="store_true", help="开放题挂起等 AI 判分")
    a.set_defaults(fn=cmd_answer)
    g = sub.add_parser("grade-open")
    g.add_argument("--q", required=True); g.add_argument("--correct", type=int, required=True, choices=[0, 1])
    g.add_argument("--error-type", default="other"); g.add_argument("--feedback", default="")
    g.add_argument("--session", default=None); g.set_defaults(fn=cmd_grade_open)
    i = sub.add_parser("import-web-result"); i.add_argument("code"); i.set_defaults(fn=cmd_import_web)
    f = sub.add_parser("finish-day"); f.add_argument("day", type=int)
    f.add_argument("--minutes", type=int, default=60); f.set_defaults(fn=cmd_finish_day)
    gt = sub.add_parser("gate"); gt.add_argument("--day", type=int, required=True)
    gt.set_defaults(fn=cmd_gate)
    sub.add_parser("sync-web").set_defaults(fn=cmd_sync_web)
    pc = sub.add_parser("pull-cloud")
    pc.add_argument("--base", required=True, help="站点根地址，如 https://nihongo80.cmjfire.workers.dev")
    pc.add_argument("--key", default="", help="与 Worker 的 NH80_SYNC_KEY 一致，或设 NH80_SYNC_KEY")
    pc.add_argument("--since", type=int, default=0)
    pc.add_argument("--limit", type=int, default=200)
    pc.set_defaults(fn=cmd_pull_cloud)
    ss = sub.add_parser("study-sync", help="同步个人作答和自评，生成并发布复习建议")
    ss.add_argument("--base", default="https://nihongo80.cmjfire.workers.dev", help="站点根地址")
    ss.add_argument("--push-only", action="store_true", help="仅根据本地状态生成和发布复习建议")
    ss.set_defaults(fn=cmd_study_sync)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    ad = sub.add_parser("adjust"); ad.add_argument("--day", type=int, required=True); ad.set_defaults(fn=cmd_adjust)
    rp = sub.add_parser("report"); rp.add_argument("--week", type=int); rp.add_argument("--stage", type=int)
    rp.add_argument("--final", action="store_true"); rp.set_defaults(fn=cmd_report)
    se = sub.add_parser("search"); se.add_argument("query"); se.add_argument("--mode", default="hybrid",
        choices=["keyword", "relation", "hybrid", "semantic"]); se.add_argument("--limit", type=int, default=20)
    se.set_defaults(fn=cmd_search)
    re_ = sub.add_parser("relation"); re_.add_argument("kid"); re_.set_defaults(fn=cmd_relation)
    im = sub.add_parser("import-file", help="导入网页导出的原始JSON作答")
    im.add_argument("--file", required=True); im.set_defaults(fn=cmd_import_file)
    co = sub.add_parser("confirm-output", help="教师录入三句批改、两句自主造句及三词回忆")
    co.add_argument("--day", type=int, required=True); co.add_argument("--file", required=True)
    co.set_defaults(fn=cmd_confirm_output)
    sub.add_parser("validate").set_defaults(fn=cmd_validate)
    sub.add_parser("backup").set_defaults(fn=cmd_backup)
    rs = sub.add_parser("restore"); rs.add_argument("path"); rs.set_defaults(fn=cmd_restore)
    au = sub.add_parser("audit"); au.add_argument("--limit", type=int, default=30); au.set_defaults(fn=cmd_audit)
    args = p.parse_args()
    try:
        args.fn(args)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e), "type": type(e).__name__}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
