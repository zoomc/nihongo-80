"""learning.py — 复习数学与掌握判定（全部确定性，AI 不参与）。

FSRS 使用 scripts/vendor/fsrs（官方 py-fsrs 6.3.1, MIT），不自造公式。
五阶段掌握门控、错误分类、补救映射、计划调整见 CONTRACTS.md 第 11/12 节。
"""
from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
from fsrs import Card, Rating, Scheduler  # noqa: E402  (官方实现, MIT)

from core import audit, iso, jdump, now_utc  # noqa: E402

STAGES = ["unseen", "initial_understanding", "hinted_recall",
          "independent_recall", "delayed_recall", "transfer"]
MASTERY_THRESHOLD = 0.85   # Bloom/Guskey 常用建议区间 0.80-0.90，非官方规定
DELAY_MIN_DAYS = 2
TRANSFER_MIN_DELAYED = 3
TRANSFER_MIN_CONTEXTS = 2
TRANSFER_MIN_SPAN_DAYS = 7

ERROR_TYPES = {"forgetting", "meaning_confusion", "particle", "conjugation",
               "listening", "comprehension", "kanji_reading", "orthography", "other"}

REMEDY = {
    "forgetting": "缩短间隔重排 + 无提示主动回忆卡（不给提示）",
    "meaning_confusion": "易混词最小对立对练习（confusables）",
    "particle": "助词填空 + 场景替换，同语法交错练习",
    "conjugation": "变形表重现 + 变形题组，并回退检查前置变形语法",
    "listening": "降速 TTS 复听 + 听写 audio_text",
    "comprehension": "降级素材（更低 level / 更高 known_ratio）",
    "kanji_reading": "音读训读对照 + 词汇语境验证",
    "orthography": "假名→汉字书写选择",
    "other": "回到原题讲解后重做同类题",
}


def scheduler() -> Scheduler:
    s = Scheduler()
    s.enable_fuzzing = False   # 确定性，可复现、可测试
    return s


def _question(conn, qid):
    r = conn.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
    if r is None:
        raise ValueError("未知题目 id: %s（拒绝编造）" % qid)
    return dict(r), json.loads(r["raw"])


def _norm(s) -> str:
    return "".join(str(s or "").strip().replace("　", " ").split()).replace("。", "").replace("、", ",")


def grade_objective(q: dict, answer: str) -> bool | None:
    """客观题判分；开放题返回 None，必须由 AI 判定（不得自动判对）。"""
    t = q.get("type")
    if t in ("free_production", "dialogue"):
        return None
    correct = q.get("answer")
    if t == "reorder":
        return _norm(answer).replace(",", "") == _norm(correct).replace(",", "")
    if t == "mcq":
        return _norm(answer) == _norm(correct)
    if t == "fill":
        return _norm(answer) == _norm(correct)
    return _norm(answer) == _norm(correct)


def infer_error_type(q: dict, answer: str, seconds: int, state: dict | None) -> str:
    """启发式归因；AI 可通过 --error-type 覆盖。此函数只是兜底，不宣称准确。"""
    t = q.get("type")
    kids = q.get("knowledge_ids") or []
    if t == "listen":
        return "listening"
    if any(k.startswith("K") for k in kids) and ("読" in str(q.get("prompt_zh", "")) or "读音" in str(q.get("prompt_zh", ""))):
        return "kanji_reading"
    pattern = str(q.get("pattern", "")) + str(q.get("prompt_ja", ""))
    if any(p in pattern for p in ("は", "が", "を", "に", "で", "助词")):
        return "particle"
    if any(w in pattern for w in ("形", "変化", "变形", "活用")):
        return "conjugation"
    if t in ("read", "translate", "dialogue"):
        return "comprehension"
    if state and state.get("last_review_at"):
        try:
            from datetime import datetime
            last = datetime.fromisoformat(state["last_review_at"])
            if (now_utc() - last).days >= 7:
                return "forgetting"
        except Exception:
            pass
    if seconds and seconds > 90:
        return "forgetting"
    return "other"


def _knowledge_state(conn, kid: str, kind: str) -> dict:
    r = conn.execute("SELECT * FROM knowledge_state WHERE knowledge_id=?", (kid,)).fetchone()
    if r:
        return dict(r)
    conn.execute("INSERT INTO knowledge_state(knowledge_id,kind,stage,updated_at) VALUES(?,?,?,?)",
                 (kid, kind, "unseen", iso()))
    return {"knowledge_id": kid, "kind": kind, "stage": "unseen",
            "first_seen_day": None, "first_seen_at": None, "last_review_day": None,
            "last_review_at": None, "hinted_count": 0, "independent_count": 0,
            "delayed_count": 0, "distinct_contexts": "[]", "correct_streak": 0,
            "error_streak": 0, "attempts": 0, "correct_attempts": 0,
            "rolling": "[]", "rolling_accuracy": 0.0, "mastered": 0}


def _update_mastery(st: dict, *, day: int, correct: bool, hinted: bool,
                    context: str, error_type: str | None, at) -> dict:
    """CONTRACTS 第 11 节。一次答对绝不能直接 mastered。"""
    st = dict(st)
    st["attempts"] = int(st.get("attempts") or 0) + 1
    rolling = json.loads(st.get("rolling") or "[]")
    rolling.append(1 if correct else 0)
    rolling = rolling[-10:]
    st["rolling"] = jdump(rolling)
    st["rolling_accuracy"] = round(sum(rolling) / len(rolling), 4)
    first_at = st.get("first_seen_at")
    if not first_at:
        st["first_seen_at"] = iso(at)
        st["first_seen_day"] = day
        first_dt = at
    else:
        try:
            from datetime import datetime
            first_dt = datetime.fromisoformat(first_at)
        except Exception:
            first_dt = at
    span_days = max(0, (at - first_dt).days)
    if correct:
        st["correct_attempts"] = int(st.get("correct_attempts") or 0) + 1
        st["correct_streak"] = int(st.get("correct_streak") or 0) + 1
        st["error_streak"] = 0
    else:
        st["correct_streak"] = 0
        st["error_streak"] = int(st.get("error_streak") or 0) + 1
    ctxs = set(json.loads(st.get("distinct_contexts") or "[]"))
    ctxs.add(context)
    st["distinct_contexts"] = jdump(sorted(ctxs))
    stage = STAGES.index(st.get("stage") or "unseen")
    # 首次暴露：最多到「初次理解」，不看对错
    stage = max(stage, 1)
    if correct and hinted:
        st["hinted_count"] = int(st.get("hinted_count") or 0) + 1
        stage = max(stage, 2)
    if correct and not hinted:
        st["independent_count"] = int(st.get("independent_count") or 0) + 1
        stage = max(stage, 3)
        if span_days >= DELAY_MIN_DAYS:
            st["delayed_count"] = int(st.get("delayed_count") or 0) + 1
            stage = max(stage, 4)
    if (int(st.get("delayed_count") or 0) >= TRANSFER_MIN_DELAYED
            and len(ctxs) >= TRANSFER_MIN_CONTEXTS
            and span_days >= TRANSFER_MIN_SPAN_DAYS):
        stage = 5
    # 退回规则
    if (not correct and (error_type == "forgetting" or int(st.get("error_streak") or 0) >= 2)):
        stage = min(stage, 2)
        st["mastered"] = 0
    st["stage"] = STAGES[max(0, min(stage, 5))]
    st["mastered"] = 1 if (st["stage"] == "transfer"
                           and st["rolling_accuracy"] >= MASTERY_THRESHOLD) else 0
    st["last_review_day"] = day
    st["last_review_at"] = iso(at)
    st["updated_at"] = iso(at)
    return st


def _fsrs_review(conn, kid: str, rating: int, at, st: dict) -> dict:
    row = conn.execute("SELECT card_json FROM fsrs_cards WHERE knowledge_id=?", (kid,)).fetchone()
    card = Card.from_dict(json.loads(row["card_json"])) if row and row["card_json"] else Card()
    s = scheduler()
    new_card, _log = s.review_card(card, Rating(rating), at)
    d = new_card.to_dict()
    prev = conn.execute("SELECT reps,lapses FROM fsrs_cards WHERE knowledge_id=?", (kid,)).fetchone()
    reps = int(prev["reps"] or 0) if prev else 0
    lapses = int(prev["lapses"] or 0) if prev else 0
    conn.execute("""INSERT OR REPLACE INTO fsrs_cards
        (knowledge_id,stage,due,stability,difficulty,state,step,reps,lapses,last_review,card_json)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                 (kid, st["stage"], d["due"], d["stability"], d["difficulty"],
                  int(d["state"]), d["step"], reps + 1,
                  lapses + (1 if rating == 1 else 0),
                  d["last_review"], jdump(d)))
    return d


REVIEW_RATING_MAP = {"good": 3, "hard": 2, "again": 1}


def apply_review_rating(conn, *, kid: str, label: str, day: int,
                        session_id: str, at=None) -> dict:
    """网页「今日复习」三档自评 → FSRS 排期（REDESIGN_PLAN §5）。

    严格边界：只推进 FSRS 的 due/stability，**不**写 attempts、**不**改 stage、
    **不**判 mastered。学员点「记住了」不等于系统认定掌握，掌握仍由
    `record_attempt` 的五阶段门控判定。
    幂等：同一 session 对同一知识点只生效一次，用 review_tasks.reason 去重。
    """
    rating = REVIEW_RATING_MAP.get(str(label))
    if rating is None:
        raise ValueError("未知复习自评 %s" % label)
    known = any(conn.execute("SELECT 1 FROM %s WHERE id=?" % t, (kid,)).fetchone()
                for t in ("vocabulary", "grammar", "kanji"))
    if not known:
        raise ValueError("未知知识点 %s，拒绝复习自评" % kid)
    reason = "web_self_rating:%s" % session_id
    if conn.execute("SELECT 1 FROM review_tasks WHERE knowledge_id=? AND reason=?",
                    (kid, reason)).fetchone():
        return {"ok": True, "duplicate": True, "kid": kid, "reason": "同一会话重复自评"}
    at = at or now_utc()
    kind = ("vocabulary" if kid.startswith("V") else "grammar" if kid.startswith("G")
            else "kanji" if kid.startswith("K") else "knowledge")
    st = _knowledge_state(conn, kid, kind)
    d = _fsrs_review(conn, kid, rating, at, st)
    conn.execute("""UPDATE knowledge_state
        SET last_review_day=?, last_review_at=?, updated_at=? WHERE knowledge_id=?""",
                 (day, iso(at), iso(at), kid))
    conn.execute("""INSERT INTO review_tasks
        (knowledge_id,day,due,reason,remedy,status,created_at) VALUES(?,?,?,?,?,?,?)""",
                 (kid, day, d["due"], reason,
                  "网页复习自评：仅重排复习时间，不判定掌握", "pending", iso(at)))
    audit(conn, "web_review_rating",
          {"day": day, "kid": kid, "label": label, "rating": rating, "due": d["due"]})
    return {"ok": True, "kid": kid, "rating": rating, "due": d["due"]}


def record_attempt(conn, *, day: int, session_id: str, qid: str, answer: str,
                   correct: bool | None = None, hinted: bool = False, seconds: int = 0,
                   error_type: str | None = None, feedback: str = "",
                   source: str = "cli", at=None) -> dict:
    """记录一次作答并推进掌握状态与 FSRS 排期。开放题 correct=None 会挂起等 AI 判分。"""
    at = at or now_utc()
    row, q = _question(conn, qid)
    dup = conn.execute("SELECT id FROM attempts WHERE session_id=? AND qid=?",
                       (session_id, qid)).fetchone()
    if dup:
        return {"ok": True, "duplicate": True, "qid": qid, "reason": "session+qid 幂等去重"}
    if correct is None:
        auto = grade_objective(q, answer)
        correct = auto
    open_pending = correct is None
    if open_pending:
        correct = False   # 未判分的开放题不记为正确，也不推进掌握
    et = error_type or (None if correct else infer_error_type(q, answer, seconds, None))
    if et and et not in ERROR_TYPES:
        raise ValueError("未知 error_type: %s" % et)
    kids = q.get("knowledge_ids") or []
    context = "%s:%s" % (q.get("type"), day)
    states = {}
    for kid in kids:
        kind = ("vocabulary" if kid.startswith("V") else "grammar" if kid.startswith("G")
                else "kanji" if kid.startswith("K") else "knowledge")
        st = _knowledge_state(conn, kid, kind)
        if open_pending:
            st["updated_at"] = iso(at)
            states[kid] = st["stage"]
            continue
        st = _update_mastery(st, day=day, correct=bool(correct), hinted=bool(hinted),
                             context=context, error_type=et, at=at)
        rating = (1 if not correct else 2 if hinted else 4
                  if st["stage"] == "transfer" else 3)
        _fsrs_review(conn, kid, rating, at, st)
        conn.execute("""UPDATE knowledge_state SET
            stage=?,first_seen_day=?,first_seen_at=?,last_review_day=?,last_review_at=?,
            hinted_count=?,independent_count=?,delayed_count=?,distinct_contexts=?,
            correct_streak=?,error_streak=?,attempts=?,correct_attempts=?,rolling=?,
            rolling_accuracy=?,mastered=?,updated_at=? WHERE knowledge_id=?""",
                     (st["stage"], st["first_seen_day"], st["first_seen_at"],
                      st["last_review_day"], st["last_review_at"], st["hinted_count"],
                      st["independent_count"], st["delayed_count"], st["distinct_contexts"],
                      st["correct_streak"], st["error_streak"], st["attempts"],
                      st["correct_attempts"], st["rolling"], st["rolling_accuracy"],
                      st["mastered"], st["updated_at"], kid))
        states[kid] = st["stage"]
        conn.execute("INSERT OR REPLACE INTO review_tasks(knowledge_id,day,due,reason,remedy,status,created_at) "
                     "VALUES(?,?,?,?,?,?,?)",
                     (kid, day, conn.execute("SELECT due FROM fsrs_cards WHERE knowledge_id=?", (kid,)).fetchone()["due"],
                      "answer_%s" % ("correct" if correct else "wrong"),
                      REMEDY.get(et, "") if not correct else "FSRS 正常排期", "pending", iso(at)))
    if not correct and not open_pending:
        conn.execute("""INSERT INTO mistakes(day,session_id,qid,knowledge_ids,error_type,answer,remedy,created_at)
            VALUES(?,?,?,?,?,?,?,?)""",
                     (day, session_id, qid, jdump(kids), et, str(answer),
                      REMEDY.get(et, REMEDY["other"]), iso(at)))
    conn.execute("""INSERT INTO attempts(day,session_id,qid,question_id,knowledge_ids,answer,
        correct,error_type,hinted,seconds,rating,created_at,source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (day, session_id, qid, qid, jdump(kids), str(answer),
                  None if open_pending else int(bool(correct)), et, int(bool(hinted)),
                  seconds, None if open_pending else (1 if not correct else 2 if hinted else 3),
                  iso(at), source))
    audit(conn, "record_attempt", {"day": day, "qid": qid, "correct": correct,
                                   "open_pending": open_pending, "error_type": et})
    return {"ok": True, "qid": qid, "correct": None if open_pending else bool(correct),
            "open_pending": open_pending, "error_type": et,
            "remedy": REMEDY.get(et, REMEDY["other"]) if not correct else "",
            "stages": states, "rationale": q.get("rationale", ""), "feedback": feedback}


def grade_open(conn, *, session_id: str, qid: str, correct: bool,
               error_type: str = "other", feedback: str = "", at=None) -> dict:
    """AI 判完开放作答后补录：删除挂起记录再按真实评分走一遍。"""
    at = at or now_utc()
    row = conn.execute("SELECT * FROM attempts WHERE session_id=? AND qid=? AND correct IS NULL",
                       (session_id, qid)).fetchone()
    if not row:
        return {"ok": False, "reason": "没有待判分的开放题记录"}
    with conn:
        conn.execute("DELETE FROM attempts WHERE id=?", (row["id"],))
        audit(conn, "grade_open", {"qid": qid, "correct": bool(correct)})
    return record_attempt(conn, day=row["day"], session_id=session_id, qid=qid,
                          answer=row["answer"], correct=bool(correct),
                          hinted=bool(row["hinted"]), seconds=row["seconds"] or 0,
                          error_type=None if correct else error_type,
                          feedback=feedback, source=row["source"], at=at)


def due_queue(conn, at=None, limit=50) -> list[dict]:
    at = at or now_utc()
    rows = conn.execute("SELECT * FROM fsrs_cards WHERE due<=? ORDER BY due LIMIT ?",
                        (iso(at), limit)).fetchall()
    return [dict(r) for r in rows]


def metrics(conn, upto_day: int | None = None) -> dict:
    where = "WHERE day<=?" if upto_day else ""
    args = (upto_day,) if upto_day else ()
    att = [dict(r) for r in conn.execute(
        "SELECT * FROM attempts %s ORDER BY id" % where, args).fetchall()]
    graded = [a for a in att if a["correct"] is not None]
    acc = round(sum(a["correct"] for a in graded) / len(graded), 4) if graded else None
    delayed = [a for a in graded if a["correct"] and a["created_at"]]
    ks = [dict(r) for r in conn.execute("SELECT * FROM knowledge_state").fetchall()]
    total_k = conn.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0] + \
              conn.execute("SELECT COUNT(*) FROM grammar").fetchone()[0] + \
              conn.execute("SELECT COUNT(*) FROM kanji").fetchone()[0]
    seen = sum(1 for k in ks if k["stage"] != "unseen")
    errdist = {}
    for a in graded:
        if not a["correct"]:
            errdist[a["error_type"] or "other"] = errdist.get(a["error_type"] or "other", 0) + 1
    sessions = [dict(r) for r in conn.execute("SELECT * FROM sessions WHERE status='finished' %s"
                                              % ("AND day<=?" if upto_day else ""), args).fetchall()]
    return {"attempts": len(att), "graded": len(graded), "accuracy": acc,
            "knowledge_total": total_k, "knowledge_seen": seen,
            "knowledge_coverage": round(seen / total_k, 4) if total_k else 0,
            "mastered": sum(1 for k in ks if k["mastered"]),
            "delayed_recall_correct": sum(1 for k in ks if (k["delayed_count"] or 0) > 0),
            "error_distribution": errdist, "completed_days": len(sessions),
            "minutes_total": sum(s["minutes"] or 0 for s in sessions)}


def adjust_plan(conn, day: int) -> dict:
    """确定性调整：只改动态任务（复习/练习/时间分配），不动知识骨架、不降低测验难度。"""
    m = metrics(conn, upto_day=day)
    recent = [dict(r) for r in conn.execute(
        "SELECT * FROM attempts WHERE day>? AND day<=? AND correct IS NOT NULL",
        (max(0, day - 7), day)).fetchall()]
    acc = round(sum(a["correct"] for a in recent) / len(recent), 4) if recent else None
    due = due_queue(conn, limit=1000)
    actions = []
    if acc is not None and acc < 0.60:
        actions.append({"type": "reduce_low_value",
                        "detail": "近 7 天正确率 %.2f < 0.60：下一天把 15 分钟自由表达块改为基础补救与旧题重做；"
                                  "新知识目标不变，测验难度不变。" % acc})
    top_err = max(m["error_distribution"].items(), key=lambda x: x[1])[0] if m["error_distribution"] else None
    if top_err and m["error_distribution"][top_err] >= 3:
        actions.append({"type": "targeted_remedy", "error_type": top_err,
                        "detail": "高频错误 %s：追加 %s" % (top_err, REMEDY[top_err])})
        rows = conn.execute("SELECT DISTINCT knowledge_ids FROM mistakes WHERE error_type=? LIMIT 10",
                            (top_err,)).fetchall()
        for r in rows:
            for kid in json.loads(r["knowledge_ids"] or "[]"):
                conn.execute("INSERT INTO review_tasks(knowledge_id,day,due,reason,remedy,status,created_at) "
                             "VALUES(?,?,?,?,?,?,?)",
                             (kid, day + 1, iso(now_utc()), "targeted_remedy",
                              REMEDY[top_err], "pending", iso()))
    if len(due) > 20:
        actions.append({"type": "review_backlog",
                        "detail": "到期积压 %d 项：下一天复习块从 10 分钟扩到 20 分钟，互动块压缩，总时长仍 60 分钟。" % len(due)})
    if acc is not None and acc > 0.90 and len(recent) >= 8:
        actions.append({"type": "raise_difficulty",
                        "detail": "近 7 天正确率 %.2f > 0.90：把下一天练习中 difficulty<=2 的题替换为 difficulty+1 的同类题（不降低测验标准）。" % acc})
    if not actions:
        actions.append({"type": "keep", "detail": "数据不足以触发调整，保持固定骨架。"})
    before = {"accuracy_7d": acc, "due": len(due), "error_distribution": m["error_distribution"]}
    with conn:
        conn.execute("INSERT INTO plan_adjustments(day,reason,before_json,after_json,created_at) VALUES(?,?,?,?,?)",
                     (day, "weekly_or_manual_audit", jdump(before), jdump(actions), iso()))
        conn.execute("UPDATE sessions SET adjustments=? WHERE day=?", (jdump(actions), day))
        audit(conn, "adjust_plan", {"day": day, "actions": len(actions)})
    return {"ok": True, "day": day, "accuracy_7d": acc, "actions": actions,
            "note": "仅调整动态任务；知识骨架与测验难度未改动"}
