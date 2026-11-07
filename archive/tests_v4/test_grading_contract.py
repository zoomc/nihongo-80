#!/usr/bin/env python3
"""契约测试：判分 / 能力分卡 / 提示学习 / 预习卡（REVISION_CONTRACT §1-§3）。"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import core  # noqa: E402
import learning  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="nh80-grading-"))
AT = datetime(2026, 11, 7, 8, 0, tzinfo=timezone.utc)


def setUpModule():
    (TMP / "knowledge" / "seeds").mkdir(parents=True)
    for f in (ROOT / "knowledge" / "seeds").glob("*.jsonl"):
        shutil.copy2(f, TMP / "knowledge" / "seeds" / f.name)
    core.init_db(TMP)
    core.import_seeds(TMP)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


class TestGradingContract(unittest.TestCase):
    def connect(self):
        conn = core.connect(TMP)
        self.addCleanup(conn.close)
        return conn

    def attempt(self, conn, **kw):
        kw.setdefault("at", AT)
        res = learning.record_attempt(conn, **kw)
        conn.commit()
        return res

    def test_01_q0001_only_advances_g0001(self):
        conn = self.connect()
        res = self.attempt(conn, day=1, session_id="t01", qid="Q0001",
                           answer="です", correct=False)   # 谎报 False 也应按答案判对
        self.assertTrue(res["correct"])
        self.assertEqual(res["targets"], [{"id": "G0001", "capability": "usage"}])
        self.assertIn("V0001", res["contexts"])
        cap = conn.execute(
            "SELECT stage FROM capability_state WHERE kid='G0001' AND capability='usage'"
        ).fetchone()
        self.assertEqual(cap["stage"], "independent_recall")
        ks = conn.execute("SELECT stage FROM knowledge_state WHERE knowledge_id='G0001'").fetchone()
        self.assertEqual(ks["stage"], "independent_recall")
        for kid in ("V0001", "K0036"):
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM knowledge_state WHERE knowledge_id=?", (kid,)
            ).fetchone()[0], 0, "%s 是 context，不得写掌握状态" % kid)
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM capability_state WHERE kid=?", (kid,)
            ).fetchone()[0], 0)
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM fsrs_cards WHERE knowledge_id LIKE ?", (kid + "|%",)
            ).fetchone()[0], 0, "%s 是 context，不得建卡" % kid)
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM review_tasks WHERE knowledge_id=?", (kid,)
            ).fetchone()[0], 0, "%s 是 context，不得进 review_tasks" % kid)
        cards = [r[0] for r in conn.execute(
            "SELECT knowledge_id FROM fsrs_cards WHERE knowledge_id LIKE 'G0001%'").fetchall()]
        self.assertEqual(cards, ["G0001|usage"])

    def test_02_hinted_correct_caps_at_hinted_recall(self):
        conn = self.connect()
        res = self.attempt(conn, day=1, session_id="t02", qid="Q0189",
                           answer="ではありません", hinted=True)
        self.assertTrue(res["correct"])
        stage = conn.execute(
            "SELECT stage FROM capability_state WHERE kid='G0002' AND capability='usage'"
        ).fetchone()["stage"]
        self.assertEqual(stage, "hinted_recall")
        row = conn.execute("SELECT rating,hinted FROM attempts WHERE session_id='t02'").fetchone()
        self.assertEqual(row["hinted"], 1)
        self.assertLessEqual(row["rating"], 2, "提示学习的 FSRS 评分最多 Hard(2)")
        # 提示不能把已有独立回忆降级，也不能单独升级
        card = conn.execute(
            "SELECT stage FROM fsrs_cards WHERE knowledge_id='G0002|usage'").fetchone()
        self.assertEqual(card["stage"], "hinted_recall")

    def test_03_frontend_lie_is_regraded(self):
        conn = self.connect()
        res = self.attempt(conn, day=1, session_id="t03", qid="Q0010",
                           answer="だ", correct=True)
        self.assertFalse(res["correct"], "记录层必须按题库答案重判")
        row = conn.execute("SELECT correct FROM attempts WHERE session_id='t03'").fetchone()
        self.assertEqual(row["correct"], 0)
        self.assertTrue(conn.execute(
            "SELECT COUNT(*) FROM mistakes WHERE session_id='t03'").fetchone()[0] >= 1)

    def test_04_two_capabilities_have_independent_cards(self):
        conn = self.connect()
        raw = {"id": "QTEST01", "type": "mcq", "prompt_ja": "___", "prompt_zh": "测试题",
               "options": ["あ", "い"], "answer": "あ", "rubric": "1",
               "rationale": "测试", "knowledge_ids": ["V0010"],
               "target_knowledge_ids": ["V0010"],
               "context_knowledge_ids": [],
               "targets": [{"id": "V0010", "capability": "meaning"},
                           {"id": "V0010", "capability": "usage"}],
               "difficulty": 1, "source": "test", "review_status": "original",
               "audio_text": "", "expected_production": None}
        conn.execute("""INSERT OR REPLACE INTO questions
            (id,type,prompt_ja,prompt_zh,options,answer,rubric,rationale,knowledge_ids,
             difficulty,source,review_status,audio_text,expected_production,raw)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     ("QTEST01", "mcq", "___", "测试题", json.dumps(["あ", "い"], ensure_ascii=False),
                      "あ", "1", "测试", json.dumps(["V0010"], ensure_ascii=False),
                      1, "test", "original", "", None, json.dumps(raw, ensure_ascii=False)))
        conn.commit()
        res = self.attempt(conn, day=1, session_id="t04", qid="QTEST01", answer="あ")
        self.assertTrue(res["correct"])
        caps = {r["capability"]: r["stage"] for r in conn.execute(
            "SELECT capability,stage FROM capability_state WHERE kid='V0010'").fetchall()}
        self.assertEqual(caps, {"meaning": "independent_recall", "usage": "independent_recall"})
        cards = {r["knowledge_id"]: r["due"] for r in conn.execute(
            "SELECT knowledge_id,due FROM fsrs_cards WHERE knowledge_id LIKE 'V0010|%'").fetchall()}
        self.assertEqual(set(cards), {"V0010|meaning", "V0010|usage"})
        before = dict(cards)
        learning.apply_review_rating(conn, kid="V0010|meaning", label="good",
                                     day=2, session_id="t04r", at=AT + timedelta(hours=2))
        conn.commit()
        after = {r["knowledge_id"]: r["due"] for r in conn.execute(
            "SELECT knowledge_id,due FROM fsrs_cards WHERE knowledge_id LIKE 'V0010|%'").fetchall()}
        self.assertNotEqual(after["V0010|meaning"], before["V0010|meaning"],
                            "被自评的能力卡必须独立推进")
        self.assertEqual(after["V0010|usage"], before["V0010|usage"],
                         "另一个能力的卡不得被带动")

    def test_05_review_rating_without_card_is_preview_only(self):
        conn = self.connect()
        self.assertEqual(conn.execute(
            "SELECT COUNT(*) FROM fsrs_cards WHERE knowledge_id LIKE 'V0250|%'").fetchone()[0], 0)
        n_attempts = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        res = learning.apply_review_rating(conn, kid="V0250", label="good",
                                           day=2, session_id="t05", at=AT)
        conn.commit()
        self.assertTrue(res["preview_only"])
        card = conn.execute(
            "SELECT due,stability,reps FROM fsrs_cards WHERE knowledge_id='V0250|meaning'"
        ).fetchone()
        self.assertIsNone(card["stability"], "预习卡不得产生稳定度")
        self.assertEqual(card["due"], (AT + timedelta(days=1)).isoformat())
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0], n_attempts,
                         "复习自评不得写 attempts")
        self.assertEqual(conn.execute(
            "SELECT COUNT(*) FROM knowledge_state WHERE knowledge_id='V0250'").fetchone()[0], 0,
            "预习卡不得改掌握状态")
        detail = conn.execute(
            "SELECT detail FROM audit_log WHERE action='web_review_rating' ORDER BY id DESC"
        ).fetchone()[0]
        self.assertIn('"preview_only":true', detail)

    def test_06_norm_answer_matches_contract_table(self):
        cases = [
            ("　です　", "です"),            # 全角空格
            ("学生 です。", "学生です"),      # 半角空格 + 句末句号
            ("ですか？", "ですか"),           # 全角问号
            ("はい、そうです！", "はい、そうです"),  # 全角感叹号
            ("Ａ，Ｂ", "A,B"),               # NFKC + 全角逗号转半角
            ("です。。。", "です"),           # 连续句末标点
            ("", ""),
        ]
        for raw, expected in cases:
            self.assertEqual(learning.norm_answer(raw), expected, raw)

    def test_07_grade_objective_ignores_caller(self):
        q = {"type": "fill", "answer": "です"}
        self.assertTrue(learning.grade_objective(q, " です。 "))
        self.assertFalse(learning.grade_objective(q, "だ"))
        self.assertIsNone(learning.grade_objective({"type": "translate", "answer": None}, "x"))

    def test_08_due_queue_shape(self):
        conn = self.connect()
        due = learning.due_queue(conn, at=AT + timedelta(days=30), limit=50)
        self.assertTrue(due)
        item = due[0]
        for key in ("kid", "capability", "card_key", "due", "stage", "stability"):
            self.assertIn(key, item)
        self.assertEqual(item["card_key"], "%s|%s" % (item["kid"], item["capability"]))


if __name__ == "__main__":
    unittest.main()
