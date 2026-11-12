"""v10 回归：页面只留内容、练习一整块、小日语文字与注音、完成按钮→云端→skill。

这些断言锁住 2026-11-08 的重构，防止后续又把顶部控件、分段练习、学习口令加回来。
"""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def page(day):
    return (ROOT / ("web/day-%03d.html" % day)).read_text(encoding="utf-8")


def data(day):
    return json.loads((ROOT / ("web/data/day-%03d.json" % day)).read_text(encoding="utf-8"))


class TestSimplifiedPage(unittest.TestCase):
    def test_no_top_or_bottom_junk_on_every_day(self):
        junk = ("modeBtn", "背诵模式", "网页 42 分钟", "id=\"sentences\"", "综合小测",
                "再练7题", "翻页练习", "学习口令", "导出待同步记录", "导出作答",
                "保存本次作答", "lesson-nav", "study.js", "data-view", "studySync",
                "错题与复习集</a>", "id=\"quiz\"")
        for day in (1, 7, 45, 47, 99, 100):
            h = page(day)
            for word in junk:
                self.assertNotIn(word, h, "Day %d 仍含 %s" % (day, word))

    def test_only_four_blocks_and_one_finish_button(self):
        h = page(47)
        self.assertEqual(re.findall(r'<section class="card" id="([^"]+)"', h),
                         ["review", "vocab", "grammar", "questions"])
        self.assertEqual(h.count('id="finish"'), 1)
        self.assertEqual(h.count('<button class="btn primary" id="finish"'), 1)
        self.assertIn("完成</button>", h)
        self.assertNotIn("accessKey", h)

    def test_masking_is_local_to_vocab_and_grammar(self):
        h = page(47)
        self.assertEqual(h.count('class="mask-switch"'), 2)
        vocab = h[h.index('id="vocab"'):h.index('id="grammar"')]
        grammar = h[h.index('id="grammar"'):h.index('id="questions"')]
        self.assertIn('data-mask="zh"', vocab)
        self.assertIn('data-mask="ja"', grammar)
        self.assertEqual(vocab.count('class="mask-switch"'), 1)
        self.assertEqual(grammar.count('class="mask-switch"'), 1)
        # 复习与练习不受遮盖开关影响
        review = h[h.index('id="review"'):h.index('id="vocab"')]
        self.assertNotIn("mask-switch", review)

    def test_small_japanese_above_chinese_and_speakable_examples(self):
        h = page(47)
        self.assertGreater(h.count('class="kana-line"'), 5, "汉字词缺平假读音行")
        self.assertGreater(h.count("<ruby>"), 5, "例句里的汉字词缺 ruby 假名")
        self.assertNotIn("data-speak=", h)
        # v12 起假名行在词形上方（原来在中文上方），中文之前改由韩语读音行占位
        self.assertRegex(h, r'class="kana-line"[^>]*>[^<]*</div><div class="jp"')


class TestMergedQuestions(unittest.TestCase):
    def test_all_days_cover_every_new_word_and_grammar(self):
        cur = json.loads((ROOT / "curriculum/curriculum.json").read_text(encoding="utf-8"))
        for d in cur["days"]:
            qs = data(d["day"])["questions"]
            covered = {k for q in qs for k in (q.get("knowledge_ids") or [])}
            need = set(d["new_vocab_ids"]) | set(d["new_grammar_ids"])
            self.assertFalse(need - covered, "Day %d 未覆盖：%s" % (d["day"], sorted(need - covered)[:5]))
            self.assertLessEqual(len(qs), 62)
            self.assertEqual(len({q["qid"] for q in qs}), len(qs))
            for q in qs:
                self.assertNotIn("answer", q)
                self.assertNotIn("rationale", q)
                self.assertEqual(len(q["options"]), 4)
                self.assertIn(q["h"], q["oh"])

    def test_daily_question_quota_per_knowledge_point(self):
        from collections import Counter
        for day in (1, 47, 100):
            c = Counter(k for q in data(day)["questions"] for k in (q.get("knowledge_ids") or []))
            d = data(day)
            expected = {**{v["id"]: 2 for v in d["vocab"]}, **{g["id"]: 3 for g in d["grammar"]}}
            self.assertEqual(c, expected, "Day %d 每个考点题数" % day)

    def test_questions_are_one_flat_block_in_html(self):
        h = page(47)
        self.assertEqual(h.count('id="questions"'), 1)
        self.assertNotIn("data-view-panel", h)
        self.assertNotIn("上一题", h)
        self.assertNotIn("下一题", h)
        self.assertGreaterEqual(h.count('class="q"'), 30)
        self.assertEqual(h.count('class="q"'), len(data(47)["questions"]))
        self.assertNotIn('"answer"', h, "页面里不能出现明文答案")


class TestProgressChain(unittest.TestCase):
    def test_finish_posts_to_progress_api_without_user_key(self):
        js = (ROOT / "web/assets/app.js").read_text(encoding="utf-8")
        self.assertIn("/api/progress", js)
        self.assertNotIn("X-NH80-Key", js, "页面不该再要求学习口令或密钥")
        self.assertNotIn("/api/events", js)
        self.assertIn("self_rating", js)
        self.assertIn("wrong_summary", js)
        self.assertIn("completed_at", js)

    def test_worker_and_migration_exist(self):
        ts = (ROOT / "deploy/worker/src/index.ts").read_text(encoding="utf-8")
        self.assertIn("/api/progress", ts)
        self.assertIn("study_progress", ts)
        self.assertTrue((ROOT / "deploy/migrations/0006_progress_120.sql").is_file())
        sql = (ROOT / "deploy/migrations/0006_progress_120.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS study_progress", sql)
        self.assertRegex(sql, r"day\s+INTEGER PRIMARY KEY")

    def test_skill_and_cli_available_to_any_agent(self):
        skill = ROOT / "skills/nh80-progress/SKILL.md"
        self.assertTrue(skill.is_file())
        self.assertTrue((ROOT / ".workbuddy/skills/nh80-progress/SKILL.md").is_file())
        self.assertTrue((Path.home() / ".workbuddy/skills/nh80-progress/SKILL.md").is_file())
        self.assertIn("name: nh80-progress", skill.read_text(encoding="utf-8"))
        self.assertIn("self_reported", skill.read_text(encoding="utf-8"))
        self.assertTrue((ROOT / "scripts/progress_read.py").is_file())
        r = subprocess.run([sys.executable, str(ROOT / "scripts/progress_read.py"), "--help"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("--latest", r.stdout)
        self.assertIn("--day", r.stdout)
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("nh80-progress", agents)

    def test_no_plaintext_answer_key_in_git(self):
        tracked = subprocess.run(["git", "ls-files", "deploy/worker/src/generated-key.json"],
                                 cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(tracked.stdout.strip(), "", "明文答案表不应入库")
        self.assertIn("generated-key.json", (ROOT / ".gitignore").read_text(encoding="utf-8"))

    def test_service_worker_bumped(self):
        sw = (ROOT / "web/sw.js").read_text(encoding="utf-8")
        self.assertRegex(sw, r"nh80-v15-[0-9a-f]{12}")
        self.assertNotIn("nh80-v5.1-", sw)
        self.assertIn("/api/", sw)

    def test_release_guard_passes(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/release_guard.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"paid_features": false', r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
