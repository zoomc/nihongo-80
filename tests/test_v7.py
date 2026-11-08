"""v7 核心不变量测试：锁住本轮修复的真 bug，防止回归。

只测「最不能坏的逻辑」：题目契约、课程难度递进、复习三类复现、
听力题原创度、音频文本一致性、答案表与数据库对齐、真人听力页的合规口径。
"""
import hashlib
import json
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name):
    return [json.loads(x) for x in (ROOT / "knowledge/seeds" / (name + ".jsonl")).read_text(
        encoding="utf-8").splitlines() if x.strip()]


class TestQuestionContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from quiz_v5 import day_questions
        cls.vocab = {x["id"]: x for x in load("vocabulary")}
        cls.grammar = {x["id"]: x for x in load("grammar")}
        cls.kanji = {x["id"]: x for x in load("kanji")}
        cls.materials = {x["id"]: x for x in load("materials")}
        cls.cur = json.loads((ROOT / "curriculum/curriculum.json").read_text(encoding="utf-8"))
        cls.by_day = {d["day"]: day_questions(d, cls.vocab, cls.grammar,
                                              cls.kanji, cls.materials)
                      for d in cls.cur["days"]}
        cls.all_q = [q for qs in cls.by_day.values() for q in qs]

    def test_every_question_has_four_unique_options(self):
        from quiz_v5 import fnv
        seen = set()
        self.assertEqual(len(self.all_q), 1035)
        for q in self.all_q:
            self.assertNotIn(q["qid"], seen, "重复题号 " + q["qid"])
            seen.add(q["qid"])
            self.assertEqual(len(q["options"]), 4, q["qid"])
            self.assertIn(q["answer"], q["options"], q["qid"])
            self.assertIn(q["h"], q["oh"], q["qid"])
            self.assertEqual(len({fnv(o) for o in q["options"]}), 4, q["qid"])

    def test_no_answer_spoiler_for_identical_kanji_words(self):
        """题干里出现的词形不应出现在任何选项文本中（否则答案等于写在题干里）。"""
        same = {v["surface"] for v in self.vocab.values()
                if v["surface"] and (v["meaning_zh"] == v["surface"]
                                     or v["meaning_zh"].startswith(v["surface"]))}
        for q in self.all_q:
            if "「" not in q["prompt"]:
                continue
            shown = q["prompt"].split("「")[1].split("」")[0]
            if shown not in same:
                continue
            self.assertFalse(any(shown in o for o in q["options"]),
                             "同形词把答案写进题干：" + q["qid"])

    def test_assessment_days_still_practice_new_kanji_and_grammar(self):
        for day in (45, 95, 110, 130, 132, 148):
            tags = [q["qid"].split("-")[2] for q in self.by_day[day]
                    if q["qid"].startswith("Q-")]
            self.assertTrue(any(t.startswith("K") for t in tags),
                            "Day %d 丢了汉字题" % day)
            self.assertTrue(any(t.startswith("G") for t in tags),
                            "Day %d 丢了语法题" % day)


class TestCurriculumQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = json.loads((ROOT / "curriculum/curriculum.json").read_text(encoding="utf-8"))
        cls.materials = {x["id"]: x for x in load("materials")}

    def test_listening_difficulty_never_goes_backwards(self):
        rank = {"N5": 0, "N4": 1, "N3": 2}
        pairs = [(d["day"], rank.get(self.materials[d["material_ids"][0]]["level"], 1))
                 for d in self.cur["days"] if d.get("listening")]
        self.assertEqual(len(pairs), 45)
        self.assertEqual([r for _, r in pairs], sorted(r for _, r in pairs),
                         "听力素材难度倒挂")
        self.assertFalse(any(day > 95 and r < 2 for day, r in pairs),
                         "N3 阶段仍在用 N4 素材")

    def test_review_snapshot_covers_all_three_kinds(self):
        kinds = {i[0] for d in self.cur["days"] for i in d["review_knowledge_ids"]}
        self.assertEqual(kinds, {"V", "G", "K"})

    def test_grammar_prerequisites_and_synonym_spacing(self):
        days = self.cur["days"]
        gday, last = {}, {}
        for d in days:
            for gid in d["new_grammar_ids"]:
                gday[gid] = d["day"]
        g = {x["id"]: x for x in load("grammar")}
        for gid, day in gday.items():
            for pre in g[gid].get("prerequisites") or []:
                if pre in gday:
                    self.assertLess(gday[pre], day, "%s 先修 %s 不在更早的天" % (gid, pre))
        for d in days:
            for gid in d["new_grammar_ids"]:
                m = g[gid].get("meaning_zh")
                if m and m in last:
                    self.assertGreaterEqual(d["day"] - last[m], 7,
                                            "同义句型连着教：Day %d %s" % (d["day"], gid))
                if m:
                    last[m] = d["day"]


class TestListeningAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selected = [x for x in load("materials") if x["id"] >= "M0096"]
        cls.manifest = json.loads((ROOT / "web/audio/manifest.json").read_text(encoding="utf-8"))

    def test_q3_answers_globally_unique(self):
        answers = [x["questions"][2]["answer"] for x in self.selected]
        self.assertEqual(len(self.selected), 45)
        self.assertEqual(len(set(answers)), 45, "模板变体 Q3 答案重复，可凭记忆作答")

    def test_every_question_valid(self):
        for m in self.selected:
            self.assertEqual(len(m["questions"]), 3, m["id"])
            for q in m["questions"]:
                self.assertEqual(len(q["options"]), 4, m["id"])
                self.assertIn(q["answer"], q["options"], m["id"])
                self.assertEqual(len(set(q["options"])), 4, m["id"])

    def test_audio_text_matches_manifest(self):
        for m in self.selected:
            item = self.manifest["items"][m["id"]]
            digest = hashlib.sha256(m["audio_text"].encode()).hexdigest()
            self.assertEqual(digest, item["text_sha256"], m["id"])
            self.assertTrue((ROOT / "web" / item["url"].lstrip("/")).is_file(), m["id"])


class TestContentFixes(unittest.TestCase):
    def test_legitimate_japanese_not_marked_wrong(self):
        g = {x["id"]: x for x in load("grammar")}
        for gid in ("G0148", "G0066"):
            for ce in g[gid]["common_errors"]:
                self.assertNotIn("によって、落ち着いて避難", ce["wrong"])
                self.assertNotIn("行ったことがあります", ce["wrong"])
        self.assertIn("従いて", g["G0148"]["common_errors"][0]["wrong"])
        self.assertIn("あるです", g["G0066"]["common_errors"][0]["wrong"])

    def test_vocabulary_examples_use_the_headword(self):
        v = {x["id"]: x for x in load("vocabulary")}
        self.assertIn("粗", v["V1469"]["examples"][0]["ja"])
        self.assertIn("務め", v["V2462"]["examples"][0]["ja"])
        self.assertNotIn("近づきにやすい", v["V1117"]["examples"][0]["ja"])

    def test_kanji_readings_and_korean_hint_fixed(self):
        k = {x["id"]: x for x in load("kanji")}
        for kid, bad in (("K0372", "ダース"), ("K0172", "リットル"), ("K0296", "メエトル")):
            self.assertNotIn(bad, k[kid]["onyomi"])
        v = {x["id"]: x for x in load("vocabulary")}
        self.assertTrue(v["V0349"]["ko_hint"].startswith("열다"))
        self.assertEqual(v["V0349"]["ko_status"], "ai_gloss")
        self.assertEqual(v["V0349"]["ko_source_ids"], [])
        self.assertEqual(sum(1 for x in v.values() if x.get("pos") == "词"), 0)


class TestDatabaseAndPages(unittest.TestCase):
    def test_question_table_matches_answer_key(self):
        keys = json.loads((ROOT / "deploy/worker/src/generated-key.json").read_text(
            encoding="utf-8"))["answers"]
        con = sqlite3.connect(ROOT / "data/state.db")
        try:
            ids = [r[0] for r in con.execute("SELECT id FROM questions")]
        finally:
            con.close()
        self.assertEqual(set(ids), set(keys))
        self.assertEqual(len(ids), 2535)

    def test_real_listening_page_is_honest_and_playable(self):
        h = (ROOT / "web/listening.html").read_text(encoding="utf-8")
        self.assertGreaterEqual(h.count("upload.wikimedia.org"), 2)
        self.assertIn("不托管在本站", h)
        self.assertIn("不复制、不下载、不热链", h)
        day47 = (ROOT / "web/day-047.html").read_text(encoding="utf-8")
        self.assertIn("listening.html", day47)
        self.assertIn("真人听力", day47)
        js = (ROOT / "web/assets/app.js").read_text(encoding="utf-8")
        self.assertIn("lastPassage", js, "共用读解材料会重复渲染")



class TestV7FinalHardening(unittest.TestCase):
    """收尾加固：Safari 音频兼容、preview D1 隔离、配置注释不回退。"""

    def test_inline_audio_has_dual_format_sources(self):
        import re
        data = json.loads((ROOT / "knowledge/resources_v7.json").read_text(encoding="utf-8"))
        inline = [x for x in data["sources"] if x.get("embed") == "inline"]
        self.assertEqual(len(inline), 4)
        for x in inline:
            self.assertTrue(x.get("mp3_url", "").startswith(
                "https://upload.wikimedia.org/wikipedia/commons/transcoded/"), x["id"])
            self.assertTrue(x["mp3_url"].endswith(".mp3"), x["id"])
        h = (ROOT / "web/listening.html").read_text(encoding="utf-8")
        self.assertEqual(h.count('type="audio/mpeg"'), 4)
        self.assertEqual(h.count('type="audio/ogg"'), 4)
        self.assertEqual(h.count("<audio"), 4)
        self.assertNotIn("Safari 请打开", h, "Safari 兼容提示已过时")

    def test_prod_and_preview_use_separate_d1(self):
        import re
        import subprocess
        cfg = (ROOT / "deploy/wrangler.jsonc").read_text(encoding="utf-8")
        ids = re.findall(r'"database_id"\s*:\s*"([0-9a-f-]+)"', cfg)
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2, "preview 不得与 production 共用一个 D1")
        self.assertIn('"database_name": "nihongo80-preview"', cfg)
        self.assertNotIn("REPLACE_WITH_D1_ID", cfg)
        out = subprocess.check_output(
            [sys.executable, str(ROOT / "scripts/release_guard.py")], text=True)
        self.assertIn("isolated", out)
        self.assertIn('"paid_features": false', out)

    def test_release_guard_rejects_shared_d1(self):
        """守卫必须真的会拦住「两环境共用一个库」的回退，而不是只打印口号。"""
        import re
        import tempfile
        import shutil
        import subprocess
        cfg = (ROOT / "deploy/wrangler.jsonc").read_text(encoding="utf-8")
        prod_id = re.findall(r'"database_id"\s*:\s*"([0-9a-f-]+)"', cfg)[0]
        tmp = Path(tempfile.mkdtemp(prefix="nh80-guard-"))
        try:
            shutil.copytree(ROOT / "deploy", tmp / "deploy", ignore=shutil.ignore_patterns("node_modules"))
            shutil.copytree(ROOT / "web", tmp / "web")
            shutil.copytree(ROOT / "knowledge", tmp / "knowledge")
            (tmp / "scripts").mkdir(exist_ok=True)
            shutil.copy2(ROOT / "scripts/release_guard.py", tmp / "scripts/release_guard.py")
            broken = (tmp / "deploy/wrangler.jsonc").read_text(encoding="utf-8").replace(
                "7b4c50be-9b93-4f65-b994-a2aec0d97380", prod_id)
            (tmp / "deploy/wrangler.jsonc").write_text(broken, encoding="utf-8")
            r = subprocess.run([sys.executable, str(tmp / "scripts/release_guard.py")],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("separate free-tier D1", r.stderr)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
