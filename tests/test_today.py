"""today.py 的回归：新会话入口必须稳定回答「今天学什么、学到哪了」。

不依赖网络：默认走 --offline 或打桩 cloud_items，避免测试挂在外站可用性上。
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import today  # noqa: E402


class TestToday(unittest.TestCase):
    def test_offline_returns_valid_day(self):
        s = today.build(offline=True)
        self.assertGreaterEqual(s["day"], 1)
        self.assertLessEqual(s["day"], s["total"])
        self.assertTrue(s["grammar_lines"], "当天必须有语法")
        self.assertTrue(s["core_ids"], "当天必须有必学词")
        self.assertEqual(s["cloud_error"], "offline")

    def test_day_override(self):
        for day in (1, 30, 60, 120):
            s = today.build(day=day, offline=True)
            self.assertEqual(s["day"], day, "显式 --day 必须生效")

    def test_render_has_sections_and_no_answers(self):
        md = today.render_md(today.build(day=1, offline=True))
        for key in ("## 你在哪", "## 今天要做什么", "## 会话怎么做", "## 完成与记录", "## 禁止"):
            self.assertIn(key, md)
        self.assertIn("today.py", md)
        self.assertNotIn("答案：", md)
        self.assertNotIn("正确答案", md)

    def test_cloud_merge_advances_day(self):
        """云端有 1..3 的完成快照，今天必须是第一个未完成天。"""
        done_local = today.local_done()
        fake = [{"day": d, "accuracy": 0.75} for d in (1, 2, 3)]
        original = today.cloud_items
        today.cloud_items = lambda total, base=None: (fake, "")
        try:
            s = today.build(offline=False)
        finally:
            today.cloud_items = original
        expected = next((d for d in range(1, s["total"] + 1)
                         if d not in (done_local | {1, 2, 3})), s["total"])
        self.assertEqual(s["day"], expected)
        self.assertEqual(s["done_count"], len(done_local | {1, 2, 3}))
        self.assertTrue(s["done_cloud"])

    def test_weak_points_are_readable(self):
        fake = [{"day": 5, "accuracy": 0.5,
                 "wrong_summary": [{"qid": "Q-005-V0", "knowledge_ids": ["V0001"]}],
                 "self_rating": {"G0001": "hard"}}]
        original = today.cloud_items
        today.cloud_items = lambda total, base=None: (fake, "")
        try:
            s = today.build(day=6, offline=False)
        finally:
            today.cloud_items = original
        self.assertTrue(any("私" in w for w in s["weak"]), s["weak"])
        self.assertTrue(any("N は N です" in w for w in s["weak"]), s["weak"])

    def test_today_prioritizes_due_cards_and_pending_prerequisites(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "state.db"
            with closing(sqlite3.connect(db)) as conn:
                conn.executescript("""
                    CREATE TABLE sessions (day, status, passed);
                    CREATE TABLE fsrs_cards (knowledge_id, due, stage, stability, difficulty, reps, lapses, last_review);
                    CREATE TABLE review_tasks (id, knowledge_id, due, reason, status);
                    CREATE TABLE knowledge_state (knowledge_id, stage);
                    INSERT INTO fsrs_cards VALUES
                        ('V0001|reading','2020-01-01T00:00:00+00:00','independent_recall',1,2,1,0,NULL),
                        ('V0002|meaning','2099-01-01T00:00:00+00:00','unseen',1,2,1,0,NULL);
                    INSERT INTO review_tasks VALUES (1,'G0001','2020-01-01T00:00:00+00:00','gate_defer:2','pending'),
                        (2,'G0002','2020-01-01T00:00:00+00:00','gate_defer:3','pending');
                    INSERT INTO knowledge_state VALUES ('G0002','transfer');
                """)
            with patch.object(today, "DB", db):
                result = today.build(day=2, offline=True)
            self.assertEqual([card["card_key"] for card in result["due_review"]], ["V0001|reading"])
            self.assertEqual([item["kid"] for item in result["prerequisite_review"]], ["G0001"])
            self.assertIn("本机 FSRS 到期", today.render_md(result))

    def test_json_cli_is_parseable(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/today.py"),
                            "--offline", "--no-write", "--json"],
                           capture_output=True, text=True, check=True)
        d = json.loads(r.stdout)
        self.assertEqual(d["day"], today.build(offline=True)["day"])
        self.assertIn("core_ids", d)

    def test_no_write_does_not_touch_file(self):
        p = ROOT / "TODAY.md"
        before = p.stat().st_mtime if p.exists() else None
        subprocess.run([sys.executable, str(ROOT / "scripts/today.py"),
                        "--offline", "--no-write"], capture_output=True, check=True)
        after = p.stat().st_mtime if p.exists() else None
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
