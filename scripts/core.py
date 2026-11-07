"""core.py — Nihongo 80 的确定性底座。

职责：SQLite 真源、知识种子导入、FTS5 检索、关系检索、状态读写镜像、备份/恢复/审计。
不负责：出题措辞、讲解、开放式答案评价（交给 AI）；不负责复习数学（交给 learning.py）。

CONTRACTS.md 第 0 节：data/state.db 是唯一可写真源，student/*.json 只是只读镜像。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
SEED_FILES = {
    "vocabulary": "vocabulary.jsonl",
    "grammar": "grammar.jsonl",
    "kanji": "kanji.jsonl",
    "questions": "questions.jsonl",
    "materials": "materials.jsonl",
}


def root_of(root=None) -> Path:
    if root is not None:
        return Path(root).resolve()
    return Path(os.environ.get("NH80_ROOT", DEFAULT_ROOT)).resolve()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or now_utc()).isoformat()


def jdump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def db_path(root=None) -> Path:
    return root_of(root) / "data" / "state.db"


def connect(root=None, readonly=False) -> sqlite3.Connection:
    p = db_path(root)
    if readonly:
        if not p.exists():
            raise FileNotFoundError("state.db 不存在，请先运行 init")
        conn = sqlite3.connect("file:%s?mode=ro" % p, uri=True)
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


SCHEMA = r"""
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY, name TEXT, url TEXT, category TEXT, license TEXT,
  fetch_status TEXT, evidence TEXT, raw TEXT
);
CREATE TABLE IF NOT EXISTS vocabulary (
  id TEXT PRIMARY KEY, surface TEXT, kana TEXT, romaji TEXT, pos TEXT,
  meaning_zh TEXT, jlpt TEXT, frequency INTEGER, confusables TEXT,
  notes_for_zh TEXT, source_ids TEXT, review_status TEXT, raw TEXT
);
CREATE TABLE IF NOT EXISTS grammar (
  id TEXT PRIMARY KEY, pattern TEXT, meaning_zh TEXT, connection TEXT,
  usage TEXT, prerequisites TEXT, compare TEXT, common_errors TEXT,
  jlpt TEXT, source_ids TEXT, review_status TEXT, raw TEXT
);
CREATE TABLE IF NOT EXISTS kanji (
  id TEXT PRIMARY KEY, char TEXT, onyomi TEXT, kunyomi TEXT, meaning_zh TEXT,
  vocab_refs TEXT, jlpt TEXT, zh_trap TEXT, source_ids TEXT,
  review_status TEXT, raw TEXT
);
CREATE TABLE IF NOT EXISTS questions (
  id TEXT PRIMARY KEY, type TEXT, prompt_ja TEXT, prompt_zh TEXT, options TEXT,
  answer TEXT, rubric TEXT, rationale TEXT, knowledge_ids TEXT, difficulty INTEGER,
  source TEXT, review_status TEXT, audio_text TEXT, expected_production TEXT, raw TEXT
);
CREATE TABLE IF NOT EXISTS materials (
  id TEXT PRIMARY KEY, kind TEXT, title TEXT, text_ja TEXT, text_zh TEXT,
  audio_text TEXT, audio_url TEXT, duration_sec INTEGER, level TEXT, topic TEXT,
  vocab_ids TEXT, grammar_ids TEXT, known_ratio REAL, source_ids TEXT,
  license TEXT, url TEXT, review_status TEXT, raw TEXT
);
CREATE TABLE IF NOT EXISTS examples (
  id INTEGER PRIMARY KEY AUTOINCREMENT, owner_type TEXT, owner_id TEXT,
  ja TEXT, zh TEXT, knowledge_ids TEXT
);
CREATE TABLE IF NOT EXISTS relations (
  src_type TEXT, src_id TEXT, dst_type TEXT, dst_id TEXT, rel_type TEXT,
  PRIMARY KEY (src_type, src_id, dst_type, dst_id, rel_type)
);
CREATE TABLE IF NOT EXISTS curriculum_days (
  day INTEGER PRIMARY KEY, phase TEXT, theme TEXT, assessment TEXT,
  review_status TEXT, payload TEXT
);
CREATE TABLE IF NOT EXISTS knowledge_state (
  knowledge_id TEXT PRIMARY KEY, kind TEXT, stage TEXT NOT NULL DEFAULT 'unseen',
  first_seen_day INTEGER, first_seen_at TEXT, last_review_day INTEGER,
  last_review_at TEXT, hinted_count INTEGER DEFAULT 0,
  independent_count INTEGER DEFAULT 0, delayed_count INTEGER DEFAULT 0,
  distinct_contexts TEXT DEFAULT '[]', correct_streak INTEGER DEFAULT 0,
  error_streak INTEGER DEFAULT 0, attempts INTEGER DEFAULT 0,
  correct_attempts INTEGER DEFAULT 0, rolling TEXT DEFAULT '[]',
  rolling_accuracy REAL DEFAULT 0.0, mastered INTEGER DEFAULT 0,
  updated_at TEXT
);
CREATE TABLE IF NOT EXISTS capability_state (
  kid TEXT NOT NULL, capability TEXT NOT NULL, stage TEXT DEFAULT 'unseen',
  attempts INTEGER DEFAULT 0, correct_attempts INTEGER DEFAULT 0,
  hinted_count INTEGER DEFAULT 0, independent_count INTEGER DEFAULT 0,
  delayed_count INTEGER DEFAULT 0, distinct_contexts TEXT DEFAULT '[]',
  last_review_day INTEGER, last_review_at TEXT, rolling TEXT DEFAULT '[]',
  rolling_accuracy REAL DEFAULT 0.0, updated_at TEXT,
  PRIMARY KEY (kid, capability)
);
CREATE TABLE IF NOT EXISTS fsrs_cards (
  knowledge_id TEXT PRIMARY KEY, stage TEXT, due TEXT, stability REAL,
  difficulty REAL, state INTEGER, step INTEGER, reps INTEGER DEFAULT 0,
  lapses INTEGER DEFAULT 0, last_review TEXT, card_json TEXT
);
CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, day INTEGER, session_id TEXT,
  qid TEXT, question_id TEXT, knowledge_ids TEXT, answer TEXT,
  correct INTEGER, error_type TEXT, hinted INTEGER DEFAULT 0,
  seconds INTEGER, rating INTEGER, created_at TEXT, source TEXT DEFAULT 'cli',
  UNIQUE (session_id, qid)
);
CREATE TABLE IF NOT EXISTS mistakes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, day INTEGER, session_id TEXT,
  qid TEXT, knowledge_ids TEXT, error_type TEXT, answer TEXT,
  remedy TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS review_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT, knowledge_id TEXT, day INTEGER,
  due TEXT, reason TEXT, remedy TEXT, status TEXT DEFAULT 'pending', created_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
  day INTEGER PRIMARY KEY, session_id TEXT, started_at TEXT, finished_at TEXT,
  planned_minutes INTEGER DEFAULT 60, minutes INTEGER, status TEXT,
  accuracy REAL, attempts INTEGER, summary TEXT, adjustments TEXT, payload TEXT
);
CREATE TABLE IF NOT EXISTS daily_summary (
  day INTEGER PRIMARY KEY, summary TEXT, ts TEXT, payload TEXT
);
CREATE TABLE IF NOT EXISTS plan_adjustments (
  id INTEGER PRIMARY KEY AUTOINCREMENT, day INTEGER, reason TEXT,
  before_json TEXT, after_json TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, action TEXT, actor TEXT,
  payload_hash TEXT, detail TEXT
);
CREATE INDEX IF NOT EXISTS ix_rel_src ON relations(src_type, src_id);
CREATE INDEX IF NOT EXISTS ix_rel_dst ON relations(dst_type, dst_id);
CREATE INDEX IF NOT EXISTS ix_attempt_day ON attempts(day);
CREATE INDEX IF NOT EXISTS ix_fsrs_due ON fsrs_cards(due);
CREATE INDEX IF NOT EXISTS ix_cap_stage ON capability_state(stage);
CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
  kid UNINDEXED, kind UNINDEXED, body, tokenize='unicode61'
);
"""


def init_db(root=None) -> dict:
    r = root_of(root)
    conn = connect(r)
    with conn:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version','4'),('created_at',?)",
            (iso(),),
        )
        # v4：能力分卡迁移（幂等）。core 不 import learning 顶层，避免循环依赖。
        from learning import migrate_v4
        migrate_v4(conn)
        audit(conn, "init_db", {"root": str(r)})
    conn.close()
    return {"ok": True, "db": str(db_path(r)), "tables": 23}


def audit(conn, action: str, payload=None, actor="script") -> None:
    raw = jdump(payload or {})
    conn.execute(
        "INSERT INTO audit_log(ts,action,actor,payload_hash,detail) VALUES(?,?,?,?,?)",
        (iso(), action, actor, hashlib.sha256(raw.encode()).hexdigest()[:16], raw[:400]),
    )


def read_jsonl(path: Path) -> list[dict]:
    out = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError("JSONL 解析失败 %s:%d %s" % (path, n, e)) from e
    return out


def _bigrams(text: str) -> str:
    """中文/日文没有空格，unicode61 会把整句当一个 token。
    用字符 bigram 做确定性子串索引，避免为此引入分词器或向量库。"""
    s = re.sub(r"\s+", "", text or "")
    if len(s) < 2:
        return s
    return " ".join(s[i : i + 2] for i in range(len(s) - 1))


# 中文意图 -> 本项目实际使用的日文/中文检索词。这是可审计的结构化别名表，
# 不是语义检索；用于弥补 FTS5 在自然语言查询上的真实召回缺口（见 docs/TECH_DESIGN.md）。
INTENT_ALIASES = {
    "感谢": ["ありがとうございます", "谢谢"], "道谢": ["ありがとうございます"],
    "道歉": ["すみません", "对不起"], "打招呼": ["こんにちは", "挨拶"],
    "问候": ["こんにちは", "おはようございます", "挨拶"],
    "婉拒": ["すみません", "断り"], "拒绝": ["すみません", "断り"],
    "邀请": ["誘う", "招待"], "问价": ["いくら"], "价格": ["いくら", "円"],
    "助词": ["は", "が", "を", "に"], "自我介绍": ["私は学生です", "自己紹介"],
    "时间": ["時間", "今日", "明日"], "数字": ["一", "二", "三"],
    "星期": ["月曜日", "火曜日", "金曜日"], "否定": ["ではありません"],
    "过去": ["でした"], "变形": ["て形", "た形", "ない形"],
}


def expand_query(q: str) -> list[str]:
    out = []
    for key, vals in INTENT_ALIASES.items():
        if key in q:
            out.extend(vals)
    # 退一步：从中文长问句里切出 2-4 字片段再查，仍只用 FTS
    if not out and len(q) >= 4:
        out = [q[i:i + 3] for i in range(0, min(len(q) - 2, 12), 3)]
    return list(dict.fromkeys(out))[:6]


def _search_body(kind: str, obj: dict) -> str:
    bits = []
    for k in ("surface", "kana", "romaji", "meaning_zh", "pattern", "char",
              "title", "prompt_ja", "prompt_zh", "text_ja", "usage", "zh_trap",
              "notes_for_zh", "connection", "meaning_zh", "rationale"):
        v = obj.get(k)
        if isinstance(v, str):
            bits.append(v)
    for k in ("onyomi", "kunyomi", "options"):
        v = obj.get(k)
        if isinstance(v, list):
            bits.extend(str(x) for x in v)
    for ex in obj.get("examples") or []:
        if isinstance(ex, dict):
            bits.append(str(ex.get("ja", "")))
            bits.append(str(ex.get("zh", "")))
    return _bigrams(" ".join(bits))


def import_seeds(root=None) -> dict:
    """把 knowledge/seeds/*.jsonl 导入 SQLite，并建全文索引 + 关系图。"""
    r = root_of(root)
    conn = connect(r)
    seed_dir = r / "knowledge" / "seeds"
    counts = {}
    with conn:
        conn.execute("DELETE FROM search_fts")
        conn.execute("DELETE FROM relations")
        conn.execute("DELETE FROM examples")
        for kind, fname in SEED_FILES.items():
            rows = read_jsonl(seed_dir / fname)
            counts[kind] = len(rows)
            for obj in rows:
                kid = obj.get("id")
                if not kid:
                    raise ValueError("%s 缺少 id: %s" % (fname, obj))
                _insert_kind(conn, kind, obj)
                conn.execute(
                    "INSERT INTO search_fts(kid,kind,body) VALUES(?,?,?)",
                    (kid, kind, _search_body(kind, obj)),
                )
        _build_relations(conn)
        conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('seeds_imported_at',?)", (iso(),))
        audit(conn, "import_seeds", counts)
    conn.close()
    return {"ok": True, "counts": counts, "total": sum(counts.values())}


def _insert_kind(conn, kind, o):
    raw = jdump(o)
    src = jdump(o.get("source_ids") or [])
    if kind == "vocabulary":
        conn.execute("""INSERT OR REPLACE INTO vocabulary VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (o["id"], o.get("surface"), o.get("kana"), o.get("romaji"), o.get("pos"),
                      o.get("meaning_zh"), o.get("jlpt"), o.get("frequency"),
                      jdump(o.get("confusables") or []), o.get("notes_for_zh"),
                      src, o.get("review_status"), raw))
    elif kind == "grammar":
        conn.execute("""INSERT OR REPLACE INTO grammar VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (o["id"], o.get("pattern"), o.get("meaning_zh"), o.get("connection"),
                      o.get("usage"), jdump(o.get("prerequisites") or []),
                      jdump(o.get("compare") or []), jdump(o.get("common_errors") or []),
                      o.get("jlpt"), src, o.get("review_status"), raw))
    elif kind == "kanji":
        conn.execute("""INSERT OR REPLACE INTO kanji VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                     (o["id"], o.get("char"), jdump(o.get("onyomi") or []),
                      jdump(o.get("kunyomi") or []), o.get("meaning_zh"),
                      jdump(o.get("vocab_refs") or []), o.get("jlpt"),
                      o.get("zh_trap"), src, o.get("review_status"), raw))
    elif kind == "questions":
        conn.execute("""INSERT OR REPLACE INTO questions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (o["id"], o.get("type"), o.get("prompt_ja"), o.get("prompt_zh"),
                      jdump(o.get("options") or []), o.get("answer"), o.get("rubric"),
                      o.get("rationale"), jdump(o.get("knowledge_ids") or []),
                      o.get("difficulty"), o.get("source"), o.get("review_status"),
                      o.get("audio_text"), o.get("expected_production"), raw))
    elif kind == "materials":
        conn.execute("""INSERT OR REPLACE INTO materials VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (o["id"], o.get("kind"), o.get("title"), o.get("text_ja"),
                      o.get("text_zh"), o.get("audio_text"), o.get("audio_url"),
                      o.get("duration_sec"), o.get("level"), o.get("topic"),
                      jdump(o.get("vocab_ids") or []), jdump(o.get("grammar_ids") or []),
                      o.get("known_ratio"), src, o.get("license"), o.get("url"),
                      o.get("review_status"), raw))
    else:
        raise ValueError("未知 kind: %s" % kind)


def _rel(conn, st, sid, dt, did, rel):
    conn.execute("INSERT OR IGNORE INTO relations VALUES(?,?,?,?,?)", (st, sid, dt, did, rel))


def _build_relations(conn):
    """建立 CONTRACTS 要求的链路：词汇 → 例句 → 语法 → 课程 → 题目 → 错题 → 复习任务。"""
    for v in conn.execute("SELECT * FROM vocabulary").fetchall():
        o = json.loads(v["raw"])
        for c in json.loads(v["confusables"] or "[]"):
            _rel(conn, "vocabulary", v["id"], "vocabulary", c, "confusable")
        for i, ex in enumerate(o.get("examples") or []):
            eid = "%s:ex%d" % (v["id"], i)
            conn.execute("INSERT INTO examples(owner_type,owner_id,ja,zh,knowledge_ids) VALUES(?,?,?,?,?)",
                         ("vocabulary", v["id"], ex.get("ja"), ex.get("zh"),
                          jdump(ex.get("grammar_ids") or [])))
            _rel(conn, "vocabulary", v["id"], "example", eid, "has_example")
            for g in ex.get("grammar_ids") or []:
                _rel(conn, "example", eid, "grammar", g, "illustrates")
    for g in conn.execute("SELECT * FROM grammar").fetchall():
        o = json.loads(g["raw"])
        for p in json.loads(g["prerequisites"] or "[]"):
            _rel(conn, "grammar", g["id"], "grammar", p, "prerequisite_of")
        for i, ex in enumerate(o.get("examples") or []):
            eid = "%s:ex%d" % (g["id"], i)
            conn.execute("INSERT INTO examples(owner_type,owner_id,ja,zh,knowledge_ids) VALUES(?,?,?,?,?)",
                         ("grammar", g["id"], ex.get("ja"), ex.get("zh"),
                          jdump(ex.get("vocab_ids") or [])))
            _rel(conn, "grammar", g["id"], "example", eid, "has_example")
            for v in ex.get("vocab_ids") or []:
                _rel(conn, "example", eid, "vocabulary", v, "uses")
    for k in conn.execute("SELECT id,vocab_refs FROM kanji").fetchall():
        for v in json.loads(k["vocab_refs"] or "[]"):
            _rel(conn, "kanji", k["id"], "vocabulary", v, "appears_in")
    for q in conn.execute("SELECT id,knowledge_ids FROM questions").fetchall():
        for kid in json.loads(q["knowledge_ids"] or "[]"):
            _rel(conn, "question", q["id"], "knowledge", kid, "tests")
    for m in conn.execute("SELECT id,vocab_ids,grammar_ids FROM materials").fetchall():
        for kid in json.loads(m["vocab_ids"] or "[]") + json.loads(m["grammar_ids"] or "[]"):
            _rel(conn, "material", m["id"], "knowledge", kid, "uses")


def import_curriculum(conn, data: dict) -> int:
    with conn:
        conn.execute("DELETE FROM curriculum_days")
        conn.execute("DELETE FROM relations WHERE src_type='curriculum_day'")
        for d in data["days"]:
            conn.execute("INSERT OR REPLACE INTO curriculum_days VALUES(?,?,?,?,?,?)",
                         (d["day"], d["phase"], d["theme"], d["assessment"],
                          d["review_status"], jdump(d)))
            for key, typ in (("new_vocab_ids", "vocabulary"), ("new_grammar_ids", "grammar"),
                             ("new_kanji_ids", "kanji")):
                for kid in d.get(key) or []:
                    _rel(conn, "curriculum_day", str(d["day"]), typ, kid, "introduces")
            for qid in d.get("question_ids") or []:
                _rel(conn, "curriculum_day", str(d["day"]), "question", qid, "assigns")
            for mid in d.get("material_ids") or []:
                _rel(conn, "curriculum_day", str(d["day"]), "material", mid, "uses")
        audit(conn, "import_curriculum", {"days": len(data["days"])})
    return len(data["days"])


def search(root=None, query: str = "", mode: str = "hybrid", limit: int = 20) -> dict:
    """三种检索的实证对比入口。

    keyword  : FTS5 字符 bigram（确定性子串），LIKE 兜底
    relation : 沿 relations 表做结构化关系遍历
    hybrid   : 两者合并去重
    semantic : 明确返回未启用及理由（CONTRACTS 第 14 节：不引入向量库）
    """
    if mode == "semantic":
        return {"mode": "semantic", "enabled": False,
                "reason": "本地小规模结构化库，FTS5 + 关系图已覆盖可枚举查询；"
                          "语义检索需嵌入模型/向量库，增加依赖与不可审计性，当前不启用。"
                          "触发重新评估的条件：跨知识点自由文本问答召回率明显不足，且已有真实失败样本。"}
    conn = connect(root, readonly=True)
    try:
        out = {"mode": mode, "query": query, "keyword": [], "relation": []}
        q = (query or "").strip()
        if q and mode in ("keyword", "hybrid"):
            bg = _bigrams(q)
            try:
                phrase = '"%s"' % bg.replace('"', "")
                rows = conn.execute(
                    "SELECT kid,kind,body FROM search_fts WHERE search_fts MATCH ? LIMIT ?",
                    (phrase, limit)).fetchall()
            except sqlite3.OperationalError:
                rows = []
            if not rows:
                # 精确词形没命中时，用结构化中文意图别名兜底（零依赖、可审计）
                hints = expand_query(q)
                found = []
                for h in hints:
                    try:
                        found += conn.execute(
                            "SELECT kid,kind,body FROM search_fts WHERE search_fts MATCH ? LIMIT ?",
                            ('"%s"' % _bigrams(h), limit)).fetchall()
                    except sqlite3.OperationalError:
                        continue
                rows = list({r["kid"]: r for r in found}.values())
                out["intent_aliases"] = hints
            seen = {r["kid"] for r in rows}
            for r in rows:
                out["keyword"].append({"id": r["kid"], "kind": r["kind"]})
            if len(rows) < limit:
                like = "%" + q + "%"
                for tbl in ("vocabulary", "grammar", "kanji", "questions", "materials"):
                    for r in conn.execute("SELECT id,raw FROM %s" % tbl).fetchall():
                        if r["id"] in seen:
                            continue
                        if q in (r["raw"] or ""):
                            out["keyword"].append({"id": r["id"], "kind": tbl})
                            seen.add(r["id"])
                            if len(out["keyword"]) >= limit:
                                break
                    if len(out["keyword"]) >= limit:
                        break
        if mode in ("relation", "hybrid"):
            seeds = ([q] if q else []) + [x["id"] for x in out["keyword"]]
            for kid in seeds[:5]:
                if not kid:
                    continue
                rows = conn.execute(
                    "SELECT * FROM relations WHERE (src_type='knowledge' AND src_id=?) "
                    "OR dst_id=? OR src_id=? LIMIT ?", (kid, kid, kid, limit)).fetchall()
                out["relation"].extend([dict(r) for r in rows])
        return out
    finally:
        conn.close()


def relation_chain(conn, kid: str) -> dict:
    """演示一条完整链路：词汇 → 例句 → 语法 → 课程 → 题目 → 错题 → 复习任务。"""
    def rels(st, sid):
        return [dict(r) for r in conn.execute(
            "SELECT * FROM relations WHERE src_type=? AND src_id=?", (st, sid)).fetchall()]
    chain = {"knowledge_id": kid, "steps": []}
    chain["steps"].append(("knowledge", rels("knowledge", kid) + rels("vocabulary", kid)))
    ex = [r["dst_id"] for r in rels("vocabulary", kid) if r["dst_type"] == "example"]
    grammars = set()
    for e in ex:
        chain["steps"].append(("example:%s" % e, rels("example", e)))
        grammars.update(r["dst_id"] for r in rels("example", e) if r["dst_type"] == "grammar")
    days = set()
    for g in grammars:
        for r in conn.execute("SELECT src_id FROM relations WHERE dst_id=? AND src_type='curriculum_day'", (g,)).fetchall():
            days.add(r["src_id"])
    for d in sorted(days)[:5]:
        chain["steps"].append(("day:%s" % d, [dict(x) for x in conn.execute(
            "SELECT * FROM relations WHERE src_type='curriculum_day' AND src_id=? AND rel_type='assigns'", (d,)).fetchall()]))
    chain["steps"].append(("mistakes", [dict(x) for x in conn.execute(
        "SELECT qid,error_type FROM mistakes WHERE knowledge_ids LIKE ? LIMIT 5", ("%" + kid + "%",)).fetchall()]))
    chain["steps"].append(("review_tasks", [dict(x) for x in conn.execute(
        "SELECT * FROM review_tasks WHERE knowledge_id=? LIMIT 5", (kid,)).fetchall()]))
    return chain


def export_state(conn, root=None) -> dict:
    """把 SQLite 真源导出为 student/*.json 只读镜像（人可读、可 diff、可备份）。"""
    r = root_of(root)
    sd = r / "student"
    sd.mkdir(parents=True, exist_ok=True)
    prof = {"schema": 1, "exported_at": iso(), "native_language": "zh",
            "other_languages": ["ko"], "japanese_level_initial": "unknown",
            "diagnostic_required_day": 1, "minutes_per_day": 60,
            "note": "只读镜像；真源为 data/state.db"}
    sess = [dict(x) for x in conn.execute("SELECT * FROM sessions ORDER BY day").fetchall()]
    ks = [dict(x) for x in conn.execute("SELECT * FROM knowledge_state ORDER BY knowledge_id").fetchall()]
    due = [dict(x) for x in conn.execute("SELECT * FROM fsrs_cards WHERE due IS NOT NULL ORDER BY due").fetchall()]
    progress = {"schema": 1, "exported_at": iso(), "sessions": sess,
                "knowledge_state": ks, "mastered_count": sum(1 for k in ks if k["mastered"]),
                "completed_days": sum(1 for s in sess if s["status"] == "finished")}
    mistakes = [dict(x) for x in conn.execute("SELECT * FROM mistakes ORDER BY id DESC LIMIT 500").fetchall()]
    att = [dict(x) for x in conn.execute("SELECT * FROM attempts ORDER BY id").fetchall()]
    for name, obj in (("profile.json", prof), ("progress.json", progress),
                      ("mistakes.json", {"schema": 1, "exported_at": iso(), "items": mistakes}),
                      ("review_queue.json", {"schema": 1, "exported_at": iso(), "due": due}),
                      ("attempts.json", {"schema": 1, "exported_at": iso(), "items": att})):
        (sd / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "files": 5, "path": str(sd)}


def backup(root=None) -> dict:
    r = root_of(root)
    src = db_path(r)
    if not src.exists():
        raise FileNotFoundError("state.db 不存在")
    bd = r / "data" / "backups"
    bd.mkdir(parents=True, exist_ok=True)
    dst = bd / ("state-%s.db" % now_utc().strftime("%Y%m%dT%H%M%SZ"))
    con = sqlite3.connect(str(src))
    out = sqlite3.connect(str(dst))
    with out:
        con.backup(out)
    con.close()
    out.close()
    return {"ok": True, "backup": str(dst), "bytes": dst.stat().st_size}


def restore(root=None, path: str = "") -> dict:
    r = root_of(root)
    src = Path(path).resolve()
    if not src.exists():
        raise FileNotFoundError(str(src))
    con = sqlite3.connect(str(src))
    con.execute("PRAGMA integrity_check").fetchone()
    con.close()
    backup(r)
    shutil.copy2(src, db_path(r))
    return {"ok": True, "restored_from": str(src)}


def audit_tail(root=None, limit=30):
    conn = connect(root, readonly=True)
    try:
        return [dict(x) for x in conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
    finally:
        conn.close()
