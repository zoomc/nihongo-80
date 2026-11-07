"""learning.py — 复习数学与掌握判定（全部确定性，AI 不参与）。

FSRS 使用 scripts/vendor/fsrs（官方 py-fsrs 6.3.1, MIT），不自造公式。
五阶段掌握门控、错误分类、补救映射、计划调整见 CONTRACTS.md 第 11/12 节。
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
from fsrs import Card, Rating, Scheduler  # noqa: E402  (官方实现, MIT)

from core import audit, iso, jdump, now_utc  # noqa: E402

STAGES = ["unseen", "initial_understanding", "hinted_recall",
          "independent_recall", "delayed_recall", "transfer"]
CAPABILITIES = ("meaning", "reading", "listening", "usage", "production")
OPEN_TYPES = ("free_production", "dialogue", "translate")
MASTERY_THRESHOLD = 0.85   # Bloom/Guskey 常用建议区间 0.80-0.90，非官方规定
DELAY_MIN_DAYS = 2
TRANSFER_MIN_DELAYED = 3
TRANSFER_MIN_CONTEXTS = 2
TRANSFER_MIN_SPAN_DAYS = 7
MASTERED_MIN_CAPABILITIES = 2

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


def norm_answer(s) -> str:
    """契约 3.2：NFKC → 去所有空白（含全角空格）→ 去句末标点 → ，转 ,。

    与 web/assets/app.js 的 norm() 同构；tests/test_grading_contract.py 锁定用例表。
    """
    s = unicodedata.normalize("NFKC", str(s or ""))
    s = re.sub(r"\s+", "", s)
    s = s.rstrip("。．.！!？?")
    return s.replace("，", ",")


def grade_objective(q: dict, answer: str) -> bool | None:
    """客观题判分；开放题返回 None，必须由 AI 判定（不得自动判对）。

    判分只看题库标准答案 + 原始作答，绝不接受调用方传入的 correct。
    """
    t = q.get("type")
    if t in OPEN_TYPES:
        return None
    return norm_answer(answer) == norm_answer(q.get("answer"))


def _kind_of(kid: str) -> str:
    if kid.startswith("V"):
        return "vocabulary"
    if kid.startswith("G"):
        return "grammar"
    if kid.startswith("K"):
        return "kanji"
    return "knowledge"


def default_capability(kid: str) -> str:
    """契约 2：旧卡无 `|` 时的默认能力。"""
    return {"V": "meaning", "G": "usage", "K": "reading"}.get((kid or "")[:1], "usage")


def card_key(kid: str, capability: str) -> str:
    return "%s|%s" % (kid, capability)


def split_card_key(key: str) -> tuple[str, str]:
    """`V0001|meaning` → (V0001, meaning)；无 `|` 时按旧数据补默认能力。"""
    raw = str(key or "")
    if "|" in raw:
        kid, cap = raw.split("|", 1)
        return kid, (cap if cap in CAPABILITIES else default_capability(kid))
    return raw, default_capability(raw)


def question_targets(q: dict) -> list[tuple[str, str]]:
    """题目目标 (kid, capability)。新种子读 targets，旧种子按类型回退。"""
    out = []
    for t in q.get("targets") or []:
        if isinstance(t, dict) and t.get("id") and t.get("capability") in CAPABILITIES:
            out.append((t["id"], t["capability"]))
    if out:
        return out
    kids = q.get("knowledge_ids") or []
    if not kids:
        return []
    t = q.get("type")
    if t in OPEN_TYPES:
        cap = "production"
    elif t == "listen":
        cap = "listening"
    else:
        cap = "usage"
    return [(kids[0], cap)]


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


def _capability_row(conn, kid: str, capability: str) -> dict:
    r = conn.execute("SELECT * FROM capability_state WHERE kid=? AND capability=?",
                     (kid, capability)).fetchone()
    if r:
        return dict(r)
    conn.execute("INSERT INTO capability_state(kid,capability,stage,updated_at) VALUES(?,?,?,?)",
                 (kid, capability, "unseen", iso()))
    return {"kid": kid, "capability": capability, "stage": "unseen", "attempts": 0,
            "correct_attempts": 0, "hinted_count": 0, "independent_count": 0,
            "delayed_count": 0, "distinct_contexts": "[]", "last_review_day": None,
            "last_review_at": None, "rolling": "[]", "rolling_accuracy": 0.0,
            "updated_at": None}


def _bump_capability(st: dict, *, kind_first_at, day: int, correct: bool, hinted: bool,
                     context: str, error_type: str | None, at) -> dict:
    """按能力推进五阶段。契约 3：hinted 正确的阶段上限是 hinted_recall。"""
    st = dict(st)
    prior = STAGES.index(st.get("stage") or "unseen")
    st["attempts"] = int(st.get("attempts") or 0) + 1
    rolling = json.loads(st.get("rolling") or "[]")
    rolling.append(1 if correct else 0)
    rolling = rolling[-10:]
    st["rolling"] = jdump(rolling)
    st["rolling_accuracy"] = round(sum(rolling) / len(rolling), 4)
    span_days = max(0, (at - kind_first_at).days) if kind_first_at else 0
    if correct:
        st["correct_attempts"] = int(st.get("correct_attempts") or 0) + 1
    ctxs = set(json.loads(st.get("distinct_contexts") or "[]"))
    ctxs.add(context)
    st["distinct_contexts"] = jdump(sorted(ctxs))
    stage = prior
    stage = max(stage, 1)  # 首次暴露最多到「初次理解」
    if correct and hinted:
        st["hinted_count"] = int(st.get("hinted_count") or 0) + 1
        stage = max(stage, 2)
        if prior < 3:
            stage = min(stage, 2)  # 本次是提示学习，不得单独推到独立回忆
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
    trailing_errors = 0
    for x in reversed(rolling):
        if x:
            break
        trailing_errors += 1
    if not correct and (error_type == "forgetting" or trailing_errors >= 2):
        stage = min(stage, 2)
    st["stage"] = STAGES[max(0, min(stage, 5))]
    st["last_review_day"] = day
    st["last_review_at"] = iso(at)
    st["updated_at"] = iso(at)
    return st


def _save_capability(conn, st: dict) -> None:
    conn.execute("""INSERT OR REPLACE INTO capability_state
        (kid,capability,stage,attempts,correct_attempts,hinted_count,independent_count,
         delayed_count,distinct_contexts,last_review_day,last_review_at,rolling,
         rolling_accuracy,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (st["kid"], st["capability"], st["stage"], st["attempts"],
                  st["correct_attempts"], st["hinted_count"], st["independent_count"],
                  st["delayed_count"], st["distinct_contexts"], st["last_review_day"],
                  st["last_review_at"], st["rolling"], st["rolling_accuracy"],
                  st["updated_at"]))


def _aggregate_knowledge(conn, kid: str, *, day: int, correct: bool, at) -> dict:
    """契约 2：knowledge_state 是按 kid 的聚合视图，不直接承载能力细节。"""
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM capability_state WHERE kid=?", (kid,)).fetchall()]
    if not rows:
        return _knowledge_state(conn, kid, _kind_of(kid))
    ks = _knowledge_state(conn, kid, _kind_of(kid))
    first_at = ks.get("first_seen_at") or iso(at)
    first_day = ks.get("first_seen_day") if ks.get("first_seen_day") is not None else day
    stage = max(STAGES.index(r.get("stage") or "unseen") for r in rows)
    ctxs = set()
    for r in rows:
        ctxs.update(json.loads(r.get("distinct_contexts") or "[]"))
    rolling = json.loads(ks.get("rolling") or "[]")
    rolling.append(1 if correct else 0)
    rolling = rolling[-10:]
    acc = round(sum(rolling) / len(rolling), 4)
    advanced = sum(1 for r in rows
                   if STAGES.index(r.get("stage") or "unseen") >= STAGES.index("independent_recall"))
    mastered = int(stage == STAGES.index("transfer")
                   and advanced >= MASTERED_MIN_CAPABILITIES
                   and acc >= MASTERY_THRESHOLD)
    conn.execute("""UPDATE knowledge_state SET
        stage=?,first_seen_day=?,first_seen_at=?,last_review_day=?,last_review_at=?,
        hinted_count=?,independent_count=?,delayed_count=?,distinct_contexts=?,
        attempts=?,correct_attempts=?,rolling=?,rolling_accuracy=?,mastered=?,updated_at=?
        WHERE knowledge_id=?""",
                 (STAGES[stage], first_day, first_at, day, iso(at),
                  sum(int(r.get("hinted_count") or 0) for r in rows),
                  sum(int(r.get("independent_count") or 0) for r in rows),
                  sum(int(r.get("delayed_count") or 0) for r in rows),
                  jdump(sorted(ctxs)),
                  sum(int(r.get("attempts") or 0) for r in rows),
                  sum(int(r.get("correct_attempts") or 0) for r in rows),
                  jdump(rolling), acc, mastered, iso(at), kid))
    return {"knowledge_id": kid, "stage": STAGES[stage], "mastered": mastered,
            "rolling_accuracy": acc, "capabilities": len(rows)}


def _fsrs_review(conn, kid: str, rating: int, at, st: dict) -> dict:
    """kid 参数是卡片键 `kid|capability`（旧数据也接受纯 kid）。"""
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


def migrate_v4(conn) -> dict:
    """契约 2 的幂等迁移：旧 fsrs 卡补 `|默认能力`，旧聚合状态回填默认能力。

    可以重复调用（init_db 每次都调），不会重复迁移。
    """
    conn.execute("""CREATE TABLE IF NOT EXISTS capability_state (
        kid TEXT NOT NULL, capability TEXT NOT NULL, stage TEXT DEFAULT 'unseen',
        attempts INTEGER DEFAULT 0, correct_attempts INTEGER DEFAULT 0,
        hinted_count INTEGER DEFAULT 0, independent_count INTEGER DEFAULT 0,
        delayed_count INTEGER DEFAULT 0, distinct_contexts TEXT DEFAULT '[]',
        last_review_day INTEGER, last_review_at TEXT, rolling TEXT DEFAULT '[]',
        rolling_accuracy REAL DEFAULT 0.0, updated_at TEXT,
        PRIMARY KEY (kid, capability))""")
    fsrs_migrated = 0
    for r in conn.execute(
            "SELECT knowledge_id FROM fsrs_cards WHERE instr(knowledge_id,'|')=0").fetchall():
        old = r["knowledge_id"]
        key = card_key(old, default_capability(old))
        if conn.execute("SELECT 1 FROM fsrs_cards WHERE knowledge_id=?", (key,)).fetchone():
            conn.execute("DELETE FROM fsrs_cards WHERE knowledge_id=?", (old,))
        else:
            conn.execute("UPDATE fsrs_cards SET knowledge_id=? WHERE knowledge_id=?", (key, old))
        fsrs_migrated += 1
    backfilled = 0
    for r in conn.execute("SELECT * FROM knowledge_state").fetchall():
        cap = default_capability(r["knowledge_id"])
        cur = conn.execute(
            "INSERT OR IGNORE INTO capability_state"
            "(kid,capability,stage,attempts,correct_attempts,hinted_count,independent_count,"
            "delayed_count,distinct_contexts,last_review_day,last_review_at,rolling,"
            "rolling_accuracy,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["knowledge_id"], cap, r["stage"] or "unseen", r["attempts"] or 0,
             r["correct_attempts"] or 0, r["hinted_count"] or 0, r["independent_count"] or 0,
             r["delayed_count"] or 0, r["distinct_contexts"] or "[]",
             r["last_review_day"], r["last_review_at"], r["rolling"] or "[]",
             r["rolling_accuracy"] or 0.0, r["updated_at"]))
        backfilled += cur.rowcount
    return {"ok": True, "fsrs_migrated": fsrs_migrated, "capability_backfilled": backfilled}


REVIEW_RATING_MAP = {"good": 3, "hard": 2, "again": 1}


def apply_review_rating(conn, *, kid: str, label: str, day: int,
                        session_id: str, at=None) -> dict:
    """网页「今日复习」三档自评 → FSRS 排期（REDESIGN_PLAN §5）。

    严格边界：只推进 FSRS 的 due/stability，**不**写 attempts、**不**改 stage、
    **不**判 mastered。学员点「记住了」不等于系统认定掌握，掌握仍由
    `record_attempt` 的五阶段门控判定。
    无既有卡片时只建「预习卡」：due=+1 天，不产生稳定度增长，审计标 preview_only。
    幂等：同一 session 对同一知识点只生效一次，用 review_tasks.reason 去重。
    kid 允许带 `|capability`（如 `V0001|meaning`）。
    """
    rating = REVIEW_RATING_MAP.get(str(label))
    if rating is None:
        raise ValueError("未知复习自评 %s" % label)
    base_kid, capability = split_card_key(kid)
    known = any(conn.execute("SELECT 1 FROM %s WHERE id=?" % t, (base_kid,)).fetchone()
                for t in ("vocabulary", "grammar", "kanji"))
    if not known:
        raise ValueError("未知知识点 %s，拒绝复习自评" % base_kid)
    reason = "web_self_rating:%s:%s" % (session_id, capability)
    if conn.execute("SELECT 1 FROM review_tasks WHERE knowledge_id=? AND reason=?",
                    (base_kid, reason)).fetchone():
        return {"ok": True, "duplicate": True, "kid": base_kid,
                "capability": capability, "reason": "同一会话重复自评"}
    at = at or now_utc()
    key = card_key(base_kid, capability)
    existing = conn.execute(
        "SELECT stage FROM fsrs_cards WHERE knowledge_id=?", (key,)).fetchone()
    preview_only = existing is None
    if preview_only:
        d = Card(due=at + timedelta(days=1)).to_dict()
        conn.execute("""INSERT OR REPLACE INTO fsrs_cards
            (knowledge_id,stage,due,stability,difficulty,state,step,reps,lapses,last_review,card_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                     (key, "unseen", d["due"], None, None, int(d["state"]), d["step"],
                      0, 0, None, jdump(d)))
    else:
        d = _fsrs_review(conn, key, rating, at,
                         {"stage": existing["stage"] or "unseen"})
        conn.execute("""UPDATE knowledge_state
            SET last_review_day=?, last_review_at=?, updated_at=? WHERE knowledge_id=?""",
                     (day, iso(at), iso(at), base_kid))
    conn.execute("""INSERT INTO review_tasks
        (knowledge_id,day,due,reason,remedy,status,created_at) VALUES(?,?,?,?,?,?,?)""",
                 (base_kid, day, d["due"], reason,
                  "网页预习卡：仅排到明天，不产生稳定度增长" if preview_only
                  else "网页复习自评：仅重排复习时间，不判定掌握", "pending", iso(at)))
    audit(conn, "web_review_rating",
          {"day": day, "kid": base_kid, "capability": capability, "card_key": key,
           "label": label, "rating": rating, "due": d["due"],
           "preview_only": preview_only})
    return {"ok": True, "kid": base_kid, "capability": capability, "card_key": key,
            "rating": rating, "due": d["due"], "preview_only": preview_only}


def record_attempt(conn, *, day: int, session_id: str, qid: str, answer: str,
                   correct: bool | None = None, hinted: bool = False, seconds: int = 0,
                   error_type: str | None = None, feedback: str = "",
                   source: str = "cli", at=None) -> dict:
    """记录一次作答。契约 3：

    - 客观题**只**按题库答案重判，调用方传入的 correct 不参与判分；
    - 只更新 targets 的能力卡与 FSRS 卡，context 知识点一律不动；
    - hinted 正确封顶 hinted_recall / FSRS Hard(2)；
    - 同一 session+qid 幂等。
    """
    at = at or now_utc()
    row, q = _question(conn, qid)
    dup = conn.execute("SELECT id FROM attempts WHERE session_id=? AND qid=?",
                       (session_id, qid)).fetchone()
    if dup:
        return {"ok": True, "duplicate": True, "qid": qid, "reason": "session+qid 幂等去重"}
    auto = grade_objective(q, answer)
    if auto is not None:
        correct = auto          # 答案优先：前端谎报的 correct 在这里被覆盖
    open_pending = correct is None
    if open_pending:
        correct = False         # 未判分的开放题不记为正确，也不推进掌握
    hinted = bool(hinted)
    et = error_type or (None if correct else infer_error_type(q, answer, seconds, None))
    if et and et not in ERROR_TYPES:
        raise ValueError("未知 error_type: %s" % et)
    kids = list(q.get("knowledge_ids") or [])
    targets = question_targets(q)
    if not targets:
        raise ValueError("题目 %s 没有 targets，拒绝写入掌握状态" % qid)
    target_ids = {k for k, _ in targets}
    contexts = [k for k in kids if k not in target_ids]
    context = "%s:%s" % (q.get("type"), day)
    stages, caps = {}, []
    for kid, capability in targets:
        st = _capability_row(conn, kid, capability)
        if open_pending:
            st["updated_at"] = iso(at)
            _save_capability(conn, st)
            stages["%s|%s" % (kid, capability)] = st["stage"]
            continue
        ks = conn.execute("SELECT first_seen_at FROM knowledge_state WHERE knowledge_id=?",
                          (kid,)).fetchone()
        first_at = None
        if ks and ks["first_seen_at"]:
            try:
                first_at = datetime.fromisoformat(ks["first_seen_at"])
            except ValueError:
                first_at = None
        st = _bump_capability(st, kind_first_at=first_at, day=day, correct=bool(correct),
                              hinted=hinted, context=context, error_type=et, at=at)
        _save_capability(conn, st)
        rating = (1 if not correct else 2 if hinted else
                  4 if st["stage"] == "transfer" else 3)
        if correct and hinted:
            rating = min(rating, 2)   # 契约 3：提示学习最多 Hard
        key = card_key(kid, capability)
        _fsrs_review(conn, key, rating, at, st)
        stages["%s|%s" % (kid, capability)] = st["stage"]
        caps.append({"target": kid, "capability": capability, "card_key": key,
                     "rating": rating})
    if not open_pending:
        for kid in dict.fromkeys(k for k, _ in targets):
            _aggregate_knowledge(conn, kid, day=day, correct=bool(correct), at=at)
        for c in caps:
            card = conn.execute("SELECT due FROM fsrs_cards WHERE knowledge_id=?",
                                (c["card_key"],)).fetchone()
            conn.execute("INSERT INTO review_tasks(knowledge_id,day,due,reason,remedy,status,created_at) "
                         "VALUES(?,?,?,?,?,?,?)",
                         (c["target"], day, card["due"] if card else None,
                          "answer_%s" % ("correct" if correct else "wrong"),
                          REMEDY.get(et, "") if not correct else "FSRS 正常排期",
                          "pending", iso(at)))
    if not correct and not open_pending:
        conn.execute("""INSERT INTO mistakes(day,session_id,qid,knowledge_ids,error_type,answer,remedy,created_at)
            VALUES(?,?,?,?,?,?,?,?)""",
                     (day, session_id, qid, jdump(sorted(target_ids)), et, str(answer),
                      REMEDY.get(et, REMEDY["other"]), iso(at)))
    conn.execute("""INSERT INTO attempts(day,session_id,qid,question_id,knowledge_ids,answer,
        correct,error_type,hinted,seconds,rating,created_at,source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (day, session_id, qid, qid, jdump(kids), str(answer),
                  None if open_pending else int(bool(correct)), et, int(hinted),
                  seconds, None if open_pending else (1 if not correct else 2 if hinted else 3),
                  iso(at), source))
    audit(conn, "record_attempt",
          {"day": day, "qid": qid, "correct": correct, "hinted": hinted,
           "open_pending": open_pending, "error_type": et,
           "targets": [{"id": k, "capability": c} for k, c in targets],
           "contexts": contexts, "capabilities": caps})
    return {"ok": True, "qid": qid, "correct": None if open_pending else bool(correct),
            "open_pending": open_pending, "error_type": et,
            "remedy": REMEDY.get(et, REMEDY["other"]) if not correct else "",
            "stages": stages, "targets": [{"id": k, "capability": c} for k, c in targets],
            "contexts": contexts,
            "rationale": q.get("rationale", ""), "feedback": feedback}


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
    """契约 2：返回按能力分开的到期卡，带 kid/capability/card_key。"""
    at = at or now_utc()
    rows = conn.execute(
        "SELECT * FROM fsrs_cards WHERE due IS NOT NULL AND due<=? "
        "ORDER BY due, knowledge_id LIMIT ?", (iso(at), limit)).fetchall()
    out = []
    for r in rows:
        kid, capability = split_card_key(r["knowledge_id"])
        out.append({"kid": kid, "capability": capability, "card_key": r["knowledge_id"],
                    "knowledge_id": r["knowledge_id"],   # 兼容旧调用方，等同 card_key
                    "due": r["due"], "stage": r["stage"], "stability": r["stability"],
                    "difficulty": r["difficulty"], "reps": r["reps"],
                    "lapses": r["lapses"], "last_review": r["last_review"]})
    return out


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


def gate(conn, day: int, payload: dict | None = None, at=None) -> dict:
    """掌握门控：先修没到 independent_recall，当天不推进依赖它的新语法。

    只读课程骨架 + 读 knowledge_state 聚合阶段；写入仅限 plan_adjustments 与
    review_tasks（幂等），不降低当天题量/正确率门槛，也不改课程骨架。
    """
    payload = payload or {}
    at = at or now_utc()
    blocked, seen = [], set()
    for gid in payload.get("new_grammar_ids") or []:
        row = conn.execute("SELECT raw FROM grammar WHERE id=?", (gid,)).fetchone()
        if not row:
            continue
        try:
            g = json.loads(row["raw"] or "{}")
        except ValueError:
            continue
        for p in g.get("prerequisites") or []:
            st = conn.execute("SELECT stage FROM knowledge_state WHERE knowledge_id=?",
                              (p,)).fetchone()
            stage = (st["stage"] if st else "unseen") or "unseen"
            try:
                ready = STAGES.index(stage) >= STAGES.index("independent_recall")
            except ValueError:
                ready = False
            if not ready:
                blocked.append({"kid": gid, "prereq": p, "prereq_stage": stage})
                seen.add(gid)
                break
    deferred = sorted(seen)
    actions = []
    if blocked:
        actions.append({"type": "gate_defer",
                        "detail": "先修未达 independent_recall：当天暂不推进 %s；先补 %s"
                                  % ("、".join(deferred),
                                     "、".join(sorted({b["prereq"] for b in blocked})))})
    # 幂等：同一天只记一次门控结果，不因反复 start-day 重复追加任务
    exists = conn.execute(
        "SELECT 1 FROM plan_adjustments WHERE day=? AND reason='gate_check' LIMIT 1",
        (day,)).fetchone()
    if not exists:
        with conn:
            conn.execute("INSERT INTO plan_adjustments(day,reason,before_json,after_json,created_at) "
                         "VALUES(?,?,?,?,?)",
                         (day, "gate_check", jdump({"blocked": len(blocked)}),
                          jdump(actions or [{"type": "gate_pass", "detail": "先修均已达 independent_recall"}]), iso(at)))
            for b in blocked:
                dup = conn.execute(
                    "SELECT 1 FROM review_tasks WHERE knowledge_id=? AND reason=?",
                    (b["prereq"], "gate_defer:%d" % day)).fetchone()
                if not dup:
                    conn.execute("INSERT INTO review_tasks(knowledge_id,day,due,reason,remedy,status,created_at) "
                                 "VALUES(?,?,?,?,?,?,?)",
                                 (b["prereq"], day, iso(at), "gate_defer:%d" % day,
                                  "门控：先补先修到 independent_recall，再推进 " + b["kid"],
                                  "pending", iso(at)))
            audit(conn, "gate_check", {"day": day, "blocked": len(blocked)})
    return {"blocked": blocked, "deferred_grammar_ids": deferred, "actions": actions}


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
        rows = conn.execute("SELECT DISTINCT qid,knowledge_ids FROM mistakes WHERE error_type=? LIMIT 10",
                            (top_err,)).fetchall()
        for r in rows:
            # 契约 3：context 知识点不得进入 review_tasks，只补 target。
            qrow = conn.execute("SELECT raw FROM questions WHERE id=?", (r["qid"],)).fetchone()
            target_ids = set()
            if qrow:
                target_ids = {k for k, _ in question_targets(json.loads(qrow["raw"]))}
            else:
                target_ids = set(json.loads(r["knowledge_ids"] or "[]"))
            for kid in target_ids:
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
