#!/usr/bin/env python3
"""Web ↔ 本地权威侧契约测试（REVISION_CONTRACT §3/4/5/6）。

覆盖：
1. 回传码谎报 correct=true：服务端重判后 attempts.correct=0，掌握状态不推进；
2. revealed_before_submit 强制 hinted，正确也只到 hinted_recall；
3. 无卡知识点复习自评只建预习卡（不增长稳定度）；
4. finish-day 未通过 → status=incomplete，不计完成天数；
5. 构建出的 day-001.json 含 review.source；
6. 前后端字符串归一（norm）同构。

运行：python3 -m unittest tests.test_web_contract -v
所有写入都在临时 root，不污染真实 data/state.db。
"""
from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import core  # noqa: E402
import curriculum as curr  # noqa: E402
import learning  # noqa: E402

CLI = ROOT / "scripts" / "nh80.py"
BUILD = ROOT / "scripts" / "build_site.py"
TMP = Path(tempfile.mkdtemp(prefix="nh80-webcontract-"))
CURRICULUM_OK = False
CURRICULUM_ERR = ""


def b64code(payload):
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    return "NH80R1." + base64.urlsafe_b64encode(raw).decode().rstrip("=")


def payload(day, results=None, ratings=None, session=None):
    return {
        "v": 1, "day": day, "session": session or ("session-test-%03d" % day),
        "ts": core.iso(), "results": results or [], "minutes": 10, "source": "web",
        "review_ratings": ratings or [],
    }


def run_cli(*args, expect_ok=True):
    p = subprocess.run([sys.executable, str(CLI), "--root", str(TMP), *args],
                       capture_output=True, text=True, cwd=str(ROOT))
    if expect_ok and p.returncode != 0:
        raise AssertionError("CLI 失败 %s: %s" % (args, (p.stderr or p.stdout)[-900:]))
    return p


def jrun(*args):
    p = run_cli(*args)
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        raise AssertionError("CLI 输出不是 JSON: %s" % p.stdout[-500:])


def db():
    return core.connect(TMP)


def setUpModule():
    global CURRICULUM_OK, CURRICULUM_ERR
    for d in ("config", "knowledge/seeds", "curriculum", "data/backups",
              "web/assets", "web/data", "sessions", "reports"):
        (TMP / d).mkdir(parents=True, exist_ok=True)
    for f in (ROOT / "knowledge" / "seeds").glob("*.jsonl"):
        shutil.copy2(f, TMP / "knowledge" / "seeds" / f.name)
    core.init_db(TMP)
    core.import_seeds(TMP)
    conn = db()
    try:
        # curriculum 正在被别的任务修改时，数据层测试仍要能跑；只有依赖课程的天级用例跳过。
        try:
            b = curr.build(TMP)
            v = curr.validate(b["data"], b["seeds"])
            if not v["ok"]:
                raise ValueError("课程校验失败：%s" % v["errors"][:3])
            curr.write_all(TMP, b["data"], v, b["seeds"])
            core.import_curriculum(conn, b["data"])
            conn.commit()
            CURRICULUM_OK = True
        except Exception as e:   # noqa: BLE001 - 记录原因，相关用例 skip
            CURRICULUM_ERR = "%s: %s" % (type(e).__name__, e)
            conn.rollback()
    finally:
        conn.close()


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def pick_objective(exclude=()):
    conn = db()
    try:
        rows = conn.execute("SELECT id,type,answer,raw FROM questions ORDER BY id").fetchall()
    finally:
        conn.close()
    for r in rows:
        if r["id"] in exclude:
            continue
        if r["type"] in learning.OPEN_TYPES:
            continue
        ans = r["answer"] or ""
        if not ans or "/" in ans:
            continue
        return {"id": r["id"], "type": r["type"], "answer": ans,
                "raw": json.loads(r["raw"] or "{}")}
    raise unittest.SkipTest("题库里没有可用的客观题")


def _seed_ids():
    out = {}
    for key, fname in (("vocab", "vocabulary.jsonl"), ("grammar", "grammar.jsonl"),
                       ("kanji", "kanji.jsonl"), ("questions", "questions.jsonl"),
                       ("materials", "materials.jsonl")):
        ids = []
        p = TMP / "knowledge" / "seeds" / fname
        if p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    ids.append(json.loads(line)["id"])
        out[key] = sorted(ids)
    return out


def minimal_day(day=1):
    """不依赖 curriculum.build 的最小日 payload：只引用真实种子 id，便于数据层独立验证。"""
    ids = _seed_ids()
    return {
        "day": day, "phase": "P1", "theme": "契约测试日", "scene": "测试场景",
        "scene_tag": "test", "can_do": "完成契约测试", "focus": ["grammar"],
        "objectives": ["验证构建注入"], "new_vocab_ids": ids["vocab"][:2],
        "new_grammar_ids": ids["grammar"][:1], "new_kanji_ids": ids["kanji"][:1],
        "review_knowledge_ids": [], "material_ids": ids["materials"][:1],
        "lesson_core": [], "review_plan": ([{
            "kid": ids["vocab"][0], "surface": "テスト", "kana": "てすと",
            "zh": "测试", "reason_zh": "契约测试", "learned_day": 1,
            "next_hint_zh": "旧文案",
        }] if ids["vocab"] else []),
        "teaching_notes": [], "blocks": [{"min": 60, "type": "input", "desc": "测试"}],
        "question_ids": ids["questions"][:3], "minutes": 60,
        "completion": "完成 3 题", "assessment": "none",
    }


def ensure_day_payload(day):
    conn = db()
    try:
        row = conn.execute("SELECT payload FROM curriculum_days WHERE day=?", (day,)).fetchone()
        if row:
            return json.loads(row["payload"])
        d = minimal_day(day)
        conn.execute("INSERT OR REPLACE INTO curriculum_days(day,phase,theme,assessment,review_status,payload) "
                     "VALUES(?,?,?,?,?,?)",
                     (day, d["phase"], d["theme"], d["assessment"], "self_reviewed",
                      json.dumps(d, ensure_ascii=False)))
        conn.commit()
        return d
    finally:
        conn.close()


class TestWebContract(unittest.TestCase):
    def test_01_client_correct_true_but_wrong_is_regraded(self):
        q = pick_objective()
        code = b64code(payload(31, [{
            "qid": q["id"], "answer": "__definitely_wrong__", "correct": True,
            "hinted": False, "revealed_before_submit": False, "seconds": 3,
        }]))
        res = jrun("import-web-result", code)
        self.assertTrue(res.get("ok"), res)
        self.assertTrue(res.get("disagreements"), "前端谎报 correct 必须进入 disagreements")
        item = [x for x in res["regraded"] if x["qid"] == q["id"]][0]
        self.assertIs(item["server_correct"], False)
        self.assertIs(item["client_correct"], True)

        conn = db()
        try:
            att = conn.execute(
                "SELECT correct,hinted,source FROM attempts WHERE day=? AND qid=?",
                (31, q["id"])).fetchone()
            self.assertIsNotNone(att)
            self.assertEqual(att["correct"], 0, "服务端重判后必须写 0")
            self.assertEqual(att["source"], "web")
            for kid, cap in learning.question_targets(q["raw"]):
                cap_row = conn.execute(
                    "SELECT stage,independent_count FROM capability_state "
                    "WHERE kid=? AND capability=?", (kid, cap)).fetchone()
                if cap_row:
                    self.assertLessEqual(learning.STAGES.index(cap_row["stage"]), 1,
                                         "%s|%s 不得因答错被推进" % (kid, cap))
                    self.assertEqual(cap_row["independent_count"] or 0, 0)
                ks = conn.execute(
                    "SELECT stage,mastered,correct_attempts FROM knowledge_state "
                    "WHERE knowledge_id=?", (kid,)).fetchone()
                if ks:
                    self.assertLessEqual(learning.STAGES.index(ks["stage"]), 1)
                    self.assertEqual(ks["mastered"], 0)
                    self.assertEqual(ks["correct_attempts"] or 0, 0)
        finally:
            conn.close()

    def test_02_revealed_forces_hinted_and_caps_stage(self):
        q = pick_objective(exclude=())
        code = b64code(payload(32, [{
            "qid": q["id"], "answer": q["answer"], "correct": True, "hinted": False,
            "revealed_before_submit": True, "pre_reveal_answer": "先写的",
            "seconds": 2,
        }]))
        res = jrun("import-web-result", code)
        self.assertIn(q["id"], res.get("hinted_forced") or [])

        conn = db()
        try:
            att = conn.execute(
                "SELECT correct,hinted FROM attempts WHERE day=? AND qid=?",
                (32, q["id"])).fetchone()
            self.assertIsNotNone(att)
            self.assertEqual(att["hinted"], 1, "揭示答案后 hinted 必须被强制为 1")
            self.assertEqual(att["correct"], 1, "答案本身正确，只是记为提示学习")
            for kid, cap in learning.question_targets(q["raw"]):
                row = conn.execute(
                    "SELECT stage FROM capability_state WHERE kid=? AND capability=?",
                    (kid, cap)).fetchone()
                if row:
                    self.assertLessEqual(learning.STAGES.index(row["stage"]), 2,
                                         "提示学习最高只到 hinted_recall")
        finally:
            conn.close()

    def test_03_review_rating_without_card_only_preview(self):
        conn = db()
        try:
            used = {r["knowledge_id"].split("|")[0]
                    for r in conn.execute("SELECT knowledge_id FROM fsrs_cards").fetchall()}
            row = conn.execute(
                "SELECT id FROM vocabulary ORDER BY id").fetchall()
            kid = None
            for r in row:
                if r["id"] not in used:
                    kid = r["id"]
                    break
        finally:
            conn.close()
        if not kid:
            self.skipTest("所有词汇都已有 FSRS 卡，无法测试预习卡分支")

        code = b64code(payload(33, [], [{"kid": kid, "rating": "good"}]))
        res = jrun("import-web-result", code)
        self.assertIn(kid, res.get("review_ratings_applied") or [])

        conn = db()
        try:
            card = conn.execute(
                "SELECT knowledge_id,due,stability FROM fsrs_cards "
                "WHERE knowledge_id IN (?,?)", (kid, kid + "|meaning")).fetchone()
            self.assertIsNotNone(card, "无卡自评应建立预习卡")
            self.assertTrue(card["due"], "预习卡必须有 due")
            self.assertIsNone(card["stability"], "预习卡不得产生稳定度增长")
            n_att = conn.execute(
                "SELECT COUNT(*) FROM attempts WHERE day=33").fetchone()[0]
            self.assertEqual(n_att, 0, "复习自评不得写 attempts")
            hit = conn.execute(
                "SELECT action,detail FROM audit_log WHERE action LIKE '%review%' "
                "ORDER BY id DESC LIMIT 1").fetchone()
            self.assertIsNotNone(hit)
            self.assertTrue("preview" in (hit["detail"] or "") or "web_review" in hit["action"])
        finally:
            conn.close()

    def test_04_finish_day_incomplete_not_counted(self):
        ensure_day_payload(34)   # 不依赖 curriculum.build；课程在改也能验证完成状态
        run_cli("start-day", "34")
        res = jrun("finish-day", "34")
        self.assertFalse(res.get("passed"))
        self.assertEqual(res.get("status"), "incomplete")
        self.assertEqual(res.get("completed_days"), 0)

        conn = db()
        try:
            s = conn.execute(
                "SELECT status,passed FROM sessions WHERE day=34").fetchone()
            self.assertEqual(s["status"], "incomplete")
            self.assertEqual(s["passed"], 0)
        finally:
            conn.close()
        st = jrun("status")
        self.assertEqual(st["metrics"]["completed_days"], 0,
                         "incomplete 不得计入 completed_days")
        self.assertGreaterEqual(st["metrics"]["incomplete_days"], 1)

    def test_05_built_day_json_has_review_source(self):
        # 课程正在改时用最小 curriculum.json 驱动 build_site；只验证 data 载荷与 review 注入。
        cp = TMP / "curriculum" / "curriculum.json"
        used_minimal = not CURRICULUM_OK
        if used_minimal:
            d = minimal_day(1)
            cp.write_text(json.dumps({"meta": {"days": 1, "minutes_per_day": 60, "version": "test"},
                                      "days": [d]}, ensure_ascii=False, indent=2), encoding="utf-8")
        p = subprocess.run([sys.executable, str(BUILD), "--root", str(TMP), "--day", "1"],
                           capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-900:])
        data = json.loads((TMP / "web" / "data" / "day-001.json").read_text(encoding="utf-8"))
        self.assertIn("review", data)
        self.assertIn(data["review"].get("source"), ("fsrs", "planned"))
        self.assertIsInstance(data["review"].get("due"), list)
        if used_minimal:
            self.assertTrue(data["review"].get("planned"), "最小日应带一条预习建议")
        for item in data["review"].get("planned") or []:
            self.assertTrue(item.get("planned_only"), "旧 review_plan 必须标 planned_only")

    def test_06_norm_isomorphic(self):
        src = (ROOT / "web" / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertIn("normalize('NFKC')", src, "JS norm() 必须做 NFKC")
        self.assertIn("\\u3000", src, "JS norm() 必须处理全角空格")

        cases = ["  ＡＢＣ　。", "はい！", "a，b.", "テスト？", "  ,  ", "です。", "です!!"]

        def py_norm(s):
            v = unicodedata.normalize("NFKC", str(s or ""))
            v = re.sub(r"[\s\u3000]+", "", v).replace("，", ",")
            return re.sub(r"[。．.！!？?]+$", "", v)

        for c in cases:
            self.assertEqual(py_norm(c), learning.norm_answer(c), "Python norm 口径不一致：%r" % c)

        node = shutil.which("node")
        if not node:
            self.skipTest("无 node，跳过 JS 侧同构执行验证（已用 Python 复算）")
        script = ("require(%s);const f=globalThis.NH80.norm;"
                  "process.stdout.write(JSON.stringify(%s.map(f)));"
                  % (json.dumps(str(ROOT / "web" / "assets" / "app.js")),
                     json.dumps(cases, ensure_ascii=False)))
        p = subprocess.run([node, "-e", script], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr[-500:])
        got = json.loads(p.stdout)
        self.assertEqual(got, [learning.norm_answer(c) for c in cases])


if __name__ == "__main__":
    unittest.main(verbosity=2)
