#!/usr/bin/env python3
"""v4 回归测试：针对独立复审发现的四个真实缺陷。

1) learning.gate 必须真的存在并会推迟先修未达标的语法
2) 选择题正确答案不能系统性落在 A
3) 无音频素材必须显式标注 audio_kind
4) N3 模考必须真正带题，而不是空壳
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_site  # noqa: E402
import curriculum as curr  # noqa: E402
import learning  # noqa: E402

SEED = ROOT / "knowledge" / "seeds"


def read_jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


class TestGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="nh80-gate-"))
        for d in ("config", "knowledge/seeds", "curriculum", "data", "web/assets", "sessions",
                  "student", "reports", "docs", "agents", "tests", "deploy/worker/src"):
            (cls.tmp / d).mkdir(parents=True, exist_ok=True)
        for f in SEED.glob("*.jsonl"):
            shutil.copy2(f, cls.tmp / "knowledge/seeds" / f.name)
        subprocess.run([sys.executable, str(ROOT / "scripts/nh80.py"), "--root", str(cls.tmp), "init"],
                       check=True, capture_output=True)
        import core
        cls.conn = core.connect(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_gate_exists_and_defers(self):
        self.assertTrue(callable(getattr(learning, "gate", None)), "learning.gate 必须存在")
        # 找一天，其新语法有先修，且先修当前是 unseen
        data = json.loads((self.tmp / "curriculum/curriculum.json").read_text(encoding="utf-8"))
        target = None
        for d in data["days"]:
            for gid in d["new_grammar_ids"]:
                g = next(x for x in read_jsonl(SEED / "grammar.jsonl") if x["id"] == gid)
                if g.get("prerequisites"):
                    target = d
                    break
            if target:
                break
        self.assertIsNotNone(target)
        res = learning.gate(self.conn, target["day"], target)
        self.assertTrue(res["blocked"], "先修未掌握时必须至少推迟一条语法：%s" % res)
        self.assertTrue(res["deferred_grammar_ids"])
        self.assertEqual(res["actions"][0]["type"], "gate_defer")
        # 幂等：同一天重复调用不重复追加
        n1 = self.conn.execute("SELECT COUNT(*) FROM review_tasks WHERE reason LIKE 'gate_defer:%'").fetchone()[0]
        learning.gate(self.conn, target["day"], target)
        n2 = self.conn.execute("SELECT COUNT(*) FROM review_tasks WHERE reason LIKE 'gate_defer:%'").fetchone()[0]
        self.assertEqual(n1, n2)


class TestQuestionOptions(unittest.TestCase):
    def test_no_position_bias(self):
        qs = read_jsonl(SEED / "questions.jsonl")
        pos = []
        for q in qs:
            opts = q.get("options") or []
            ans = q.get("answer")
            if len(opts) >= 2 and ans in opts:
                pos.append(opts.index(ans))
        self.assertGreater(len(pos), 80, "可选项题目太少，样本不足")
        share0 = pos.count(0) / len(pos)
        self.assertLess(share0, 0.40, "正确答案仍有 %.0f%% 落在 A" % (share0 * 100))
        for i in range(max(pos) + 1):
            self.assertLess(pos.count(i) / len(pos), 0.45, "第 %d 个位置占比过高" % i)


class TestMaterialAudio(unittest.TestCase):
    def test_audio_kind_declared(self):
        missing = [m["id"] for m in read_jsonl(SEED / "materials.jsonl")
                   if not m.get("audio_url") and not m.get("audio_kind")]
        self.assertEqual(missing, [], "无音频素材必须标注 audio_kind=tts：%s" % missing[:10])


class TestMockPage(unittest.TestCase):
    def test_mock_has_questions(self):
        data = json.loads((ROOT / "knowledge/mock_n3.json").read_text(encoding="utf-8"))
        tables = {k: {x["id"]: x for x in read_jsonl(SEED / f)}
                  for k, f in (("questions", "questions.jsonl"), ("materials", "materials.jsonl"))}
        mock = build_site.normalize_mock(data, tables["questions"])
        total = sum(len(s["questions"]) for s in mock["sections"])
        self.assertGreaterEqual(total, 60, "模考必须真的带题")
        self.assertEqual(sum(int(s["minutes"]) for s in mock["sections"]), 140)
        self.assertTrue(any(q["audio_text"] for s in mock["sections"] for q in s["questions"]),
                        "聴解分项必须有可播放文本")


if __name__ == "__main__":
    unittest.main(verbosity=2)
