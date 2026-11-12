#!/usr/bin/env python3
"""v5 验收：120 天 / 2700 词 / 276 语法 / 620 汉字 / 5 块网页 / 会话协议。"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "knowledge" / "seeds"


def read(name):
    return [json.loads(x) for x in (SEED / name).read_text(encoding="utf-8").splitlines() if x.strip()]


class TestSeeds(unittest.TestCase):
    def test_counts(self):
        self.assertGreaterEqual(len(read("vocabulary.jsonl")), 2700)
        self.assertGreaterEqual(len(read("grammar.jsonl")), 276)
        self.assertGreaterEqual(len(read("kanji.jsonl")), 620)
        self.assertGreaterEqual(len(read("questions.jsonl")), 900)
        self.assertGreaterEqual(len(read("sentences.jsonl")), 1500)

    def test_vocab_fields(self):
        bad = []
        for v in read("vocabulary.jsonl"):
            if not v.get("meaning_zh") or not v.get("kana") or not v.get("jlpt"):
                bad.append(v.get("id"))
        self.assertEqual(bad, [], "词条缺释义/假名/级别：%s" % bad[:8])

    def test_grammar_korean_and_errors(self):
        g = read("grammar.jsonl")
        self.assertGreaterEqual(sum(1 for x in g if x.get("ko_equiv")), 180)
        for x in g:
            self.assertTrue(x.get("pattern") and x.get("meaning_zh"), x.get("id"))
            self.assertTrue(x.get("common_errors"), "%s 缺易错点" % x.get("id"))
        # 不允许 wrong == fix 的自相矛盾
        for x in g:
            for ce in x.get("common_errors") or []:
                self.assertNotEqual((ce.get("wrong") or "").strip(), (ce.get("fix") or "").strip(),
                                    "%s 的 wrong 与 fix 相同" % x.get("id"))

    def test_kanji(self):
        k = read("kanji.jsonl")
        self.assertGreaterEqual(sum(1 for x in k if x.get("ko_hanja")), 450)
        for x in k:
            self.assertTrue(x.get("char") and x.get("meaning_zh"), x.get("id"))


class TestCurriculum(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = json.loads((ROOT / "curriculum/curriculum.json").read_text(encoding="utf-8"))
        cls.days = cls.cur["days"]

    def test_120_days(self):
        self.assertEqual(len(self.days), 120)
        self.assertEqual([d["day"] for d in self.days], list(range(1, 121)))

    def test_blocks_sum_60(self):
        for d in self.days:
            self.assertEqual(sum(b["min"] for b in d["blocks"]), 60, "Day %d 时间块不等于 60" % d["day"])
            self.assertGreaterEqual(len(d["blocks"]), 5)

    def test_new_content_totals(self):
        v = sum(len(d["new_vocab_ids"]) for d in self.days)
        g = sum(len(d["new_grammar_ids"]) for d in self.days)
        k = sum(len(d["new_kanji_ids"]) for d in self.days)
        self.assertEqual(v, 2700)
        self.assertEqual(g, 276)
        self.assertEqual(k, 620)

    def test_listening_schedule(self):
        days = [d["day"] for d in self.days if d.get("listening")]
        self.assertGreaterEqual(len(days), 40)
        self.assertEqual(sum(31 <= d <= 60 for d in days), 18)
        self.assertEqual(sum(61 <= d <= 120 for d in days), 27)

    def test_no_duplicate_new_ids(self):
        seen_v, seen_g, seen_k = set(), set(), set()
        for d in self.days:
            for vid in d["new_vocab_ids"]:
                self.assertNotIn(vid, seen_v, "重复排课 %s" % vid)
                seen_v.add(vid)
            for gid in d["new_grammar_ids"]:
                self.assertNotIn(gid, seen_g, "重复排课 %s" % gid)
                seen_g.add(gid)
            for kid in d["new_kanji_ids"]:
                self.assertNotIn(kid, seen_k, "重复排课 %s" % kid)
                seen_k.add(kid)


class TestWeb(unittest.TestCase):
    def test_120_pages(self):
        pages = sorted((ROOT / "web").glob("day-*.html"))
        self.assertEqual(len(pages), 120)

    def test_no_dashboard_junk(self):
        for p in list((ROOT / "web").glob("day-*.html"))[:20]:
            h = p.read_text(encoding="utf-8")
            for kw in ("热力图", "雷达", "时间块", "能力雷达"):
                self.assertNotIn(kw, h, "%s 仍含仪表盘元素 %s" % (p.name, kw))

    def test_four_content_blocks_and_local_masking(self):
        """v10：页面只有 4 个内容块 + 完成按钮，遮盖只在新词与语法模块内。"""
        h = (ROOT / "web/day-001.html").read_text(encoding="utf-8")
        for sec in ("review", "vocab", "grammar", "questions"):
            self.assertIn('id="%s"' % sec, h)
        self.assertIn('id="finish"', h)
        self.assertEqual(h.count('class="mask-switch"'), 2)
        self.assertIn('data-role="ja"', h)
        self.assertIn('data-role="zh"', h)
        for junk in ("modeBtn", "背诵模式", "网页 42 分钟", 'id="sentences"', "综合小测",
                     "翻页练习", "学习口令", "导出作答", "保存本次作答", "lesson-nav", "study.js"):
            self.assertNotIn(junk, h, "每日页仍含被移除的元素：" + junk)

    def test_listening_day_has_section(self):
        h = (ROOT / "web/day-048.html").read_text(encoding="utf-8")
        self.assertIn('id="listening"', h)

    def test_quiz_aligned_and_no_plain_answer(self):
        d = json.loads((ROOT / "web/data/day-050.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(d["quiz"]), 4)
        for q in d["quiz"]:
            self.assertIn("h", q)
            self.assertIn("oh", q)
            self.assertNotIn("answer", q, "题目不应把答案明文写进页面")
            self.assertGreaterEqual(len(q["options"]), 2)

    def test_mobile_meta(self):
        h = (ROOT / "web/day-001.html").read_text(encoding="utf-8")
        self.assertIn("width=device-width", h)
        self.assertIn("@media", (ROOT / "web/assets/app.css").read_text(encoding="utf-8"))


class TestCli(unittest.TestCase):
    def test_validate_v5(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/nh80.py"), "validate"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"days": 120', r.stdout)
        self.assertIn('"v": 2700', r.stdout)


class TestSessionProtocol(unittest.TestCase):
    def test_daily_generates_state_and_brief(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/session_v5.py"), "daily", "--day", "1"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((ROOT / "STATE.md").is_file())
        self.assertTrue((ROOT / "days/day-001/brief.md").is_file())

    def test_task_claim_done(self):
        tid = "day-001-tutor"
        subprocess.run([sys.executable, str(ROOT / "scripts/session_v5.py"), "task", "new", "--day", "1"],
                       check=True, capture_output=True)
        r = subprocess.run([sys.executable, str(ROOT / "scripts/session_v5.py"), "task", "claim", tid,
                            "--owner", "test"], capture_output=True, text=True)
        self.assertIn('"ok": true', r.stdout.replace("True", "true").lower())
        r2 = subprocess.run([sys.executable, str(ROOT / "scripts/session_v5.py"), "task", "done", tid,
                             "--owner", "test"], capture_output=True, text=True)
        self.assertIn('"ok": true', r2.stdout.replace("True", "true").lower())

    def test_brief_has_link_and_korean(self):
        b = (ROOT / "days/day-001/brief.md").read_text(encoding="utf-8")
        self.assertIn("day-001.html", b)
        self.assertIn("朝鲜语", b)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestReviewRegressions(unittest.TestCase):
    """2026-11-07 修复前冻结的缺陷复现；不随实现调整。"""

    def test_no_minute_labels_on_page(self):
        """v10 页面不显示时间块；课程表仍保留 60 分钟结构。"""
        cur = json.loads((ROOT / 'curriculum/curriculum.json').read_text())['days']
        for d in cur:
            page = (ROOT / ('web/day-%03d.html' % d['day'])).read_text()
            self.assertNotIn('class="min">', page, d['day'])
            self.assertEqual(sum(b['min'] for b in d['blocks'] if b['type'] != '会话'), 42)
            self.assertEqual(sum(b['min'] for b in d['blocks']), 60)

    def test_listening_distinct_and_three_questions(self):
        cur = json.loads((ROOT / 'curriculum/curriculum.json').read_text())['days']
        seen = set()
        for d in cur:
            if not d['listening']:
                continue
            p = json.loads((ROOT / ('web/data/day-%03d.json' % d['day'])).read_text())
            m = p['listening_material']
            self.assertNotIn(m['id'], seen)
            seen.add(m['id'])
            self.assertEqual(len(m.get('questions', [])), 3)
            self.assertGreaterEqual(len(m['transcript']), 300)
            html = (ROOT / ('web/day-%03d.html' % d['day'])).read_text()
            self.assertIn('id="listening"', html)
            self.assertIn('id="questions"', html)
            self.assertLess(html.index('id="listening"'), html.index('class="q"'))

    def test_no_plain_solution_in_public_exercises(self):
        p = json.loads((ROOT / 'web/data/day-001.json').read_text())
        for q in p['quiz']:
            self.assertNotIn('rationale', q)
        for s in p['sentences']:
            self.assertNotIn('answer_ja', s)
            self.assertNotIn('answer_zh', s)

    def test_daily_refreshes_stale_brief_preserves_report(self):
        import tempfile
        from unittest.mock import patch
        sys.path.insert(0, str(ROOT / 'scripts'))
        import session_v5 as s
        with tempfile.TemporaryDirectory() as td:
            days = Path(td)
            folder = days / 'day-001'; folder.mkdir()
            (folder / 'brief.md').write_text('stale')
            (folder / 'report.md').write_text('student work')
            with patch.object(s, 'DAYS', days):
                s.brief(1)
                self.assertNotEqual((folder / 'brief.md').read_text(), 'stale')
                s.report(1)
                self.assertEqual((folder / 'report.md').read_text(), 'student work')

    def test_all_web_questions_registered_for_import(self):
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(ROOT / 'data/state.db')) as db:
            ids = {r[0] for r in db.execute('select id from questions')}
        p = json.loads((ROOT / 'web/data/day-047.json').read_text())
        for q in p['quiz']:
            self.assertIn(q['qid'], ids)

    def test_distinct_sessions_do_not_collapse_into_day_session(self):
        import tempfile
        import sqlite3
        import argparse
        import io
        from contextlib import redirect_stdout
        sys.path.insert(0, str(ROOT / 'scripts'))
        import nh80
        import cloud_sync
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'data').mkdir()
            (root / 'knowledge').symlink_to(ROOT / 'knowledge')
            src = sqlite3.connect(ROOT / 'data/state.db')
            dst = sqlite3.connect(root / 'data/state.db')
            src.backup(dst)
            src.close(); dst.close()
            page = json.loads((ROOT / 'web/data/day-120.json').read_text())
            qid = page['quiz'][0]['qid']
            key = json.loads((ROOT / 'deploy/worker/src/generated-key.json').read_text())['answers']
            results = []
            for sid in ('codex-test-first', 'codex-test-retake'):
                payload = {'v': 1, 'day': 120, 'session': sid, 'ts': '2026-11-07T00:00:00Z',
                           'minutes': None, 'source': 'test',
                           'results': [{'qid': qid, 'answer': key[qid]['answer']}]}
                with redirect_stdout(io.StringIO()) as buf:
                    nh80.cmd_import_web(argparse.Namespace(root=str(root), code=cloud_sync.encode_payload(payload)))
                results.append(json.loads(buf.getvalue()))
            self.assertEqual(len(results[0]['applied']), 1)
            self.assertEqual(len(results[1]['applied']), 1)
            self.assertNotEqual(results[0]['session_id'], results[1]['session_id'])
