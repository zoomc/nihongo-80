#!/usr/bin/env python3
"""契约测试：题目目标/语境分离 + 内容准确性（REVISION_CONTRACT §1、§8）。"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "knowledge" / "seeds"
sys.path.insert(0, str(ROOT / "scripts"))

import audit_content  # noqa: E402

CAPABILITIES = {"meaning", "reading", "listening", "usage", "production"}
ABSOLUTE = ("只能这样说", "只能这么用", "唯一正确", "绝对不", "一定不能", "必须这样")


def read_jsonl(name):
    return [json.loads(line) for line in (SEED / name).read_text(encoding="utf-8").splitlines()
            if line.strip()]


class TestQuestionTargets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = read_jsonl("questions.jsonl")

    def test_all_questions_have_targets(self):
        # v4 题库扩到 395 道（332 原有 + 63 道 N3）；只要求每条都有 targets。
        self.assertGreaterEqual(len(self.questions), 332)
        for q in self.questions:
            with self.subTest(qid=q["id"]):
                targets = q.get("targets") or []
                self.assertTrue(targets, "targets 不得为空")
                ids = q.get("knowledge_ids") or []
                tids = [t["id"] for t in targets]
                self.assertTrue(set(tids) <= set(ids))
                self.assertTrue(all(t["capability"] in CAPABILITIES for t in targets))
                self.assertEqual(set(q["target_knowledge_ids"]), set(tids))
                self.assertEqual(len(tids) + len(q["context_knowledge_ids"]), len(ids))
                self.assertEqual(set(tids) | set(q["context_knowledge_ids"]), set(ids))
                self.assertFalse(set(tids) & set(q["context_knowledge_ids"]))

    def test_q0001_target_is_grammar(self):
        q1 = next(q for q in self.questions if q["id"] == "Q0001")
        self.assertEqual([t["id"] for t in q1["targets"]], ["G0001"])
        self.assertEqual(q1["targets"][0]["capability"], "usage")
        self.assertIn("V0001", q1["context_knowledge_ids"])


class TestContentAccuracy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = {q["id"]: q for q in read_jsonl("questions.jsonl")}
        cls.grammar = read_jsonl("grammar.jsonl")

    def test_q0006_register_not_wrong_sentence(self):
        q = self.questions["Q0006"]
        self.assertIn("语体", q["prompt_zh"])
        self.assertIn("礼貌体", q["prompt_zh"])
        self.assertIn("合法", q["rationale"])
        self.assertIn("礼貌体", q["rubric"])
        self.assertNotIn("错句", q["rationale"])

    def test_g0002_jya_arimasen_is_legal(self):
        g = next(x for x in self.grammar if x["id"] == "G0002")
        wrongs = [ce["wrong"] for ce in g["common_errors"]]
        self.assertFalse(any("じゃありません" in w for w in wrongs),
                         "じゃありません 是合法口语礼貌否定")
        self.assertTrue(any("ないです" in w for w in wrongs), "必须保留真正错误的示例")

    def test_g0005_ga_is_focus_not_error(self):
        g = next(x for x in self.grammar if x["id"] == "G0005")
        self.assertFalse(any("これが本ですか" in ce["wrong"] for ce in g["common_errors"]))
        self.assertIn("焦点", g.get("notes", ""))

    def test_grammar_register_and_provenance(self):
        # v4 起 N3 语法扩到 96 条；只要求数量只增不减，且每条都带审计字段。
        self.assertGreaterEqual(len(self.grammar), 85)
        for g in self.grammar:
            with self.subTest(gid=g["id"]):
                self.assertTrue(str(g.get("register_note") or "").strip())
                self.assertEqual(g.get("review_status"), "self_reviewed")
                self.assertEqual(g.get("provenance"), "self_reviewed")
                self.assertFalse(str(g.get("connection") or "").strip() == "")

    def test_no_absolute_wording(self):
        for g in self.grammar:
            text = json.dumps(g, ensure_ascii=False)
            for pat in ABSOLUTE:
                self.assertNotIn(pat, text, "%s 含绝对化措辞 %s" % (g["id"], pat))

    def test_content_audit_has_zero_high(self):
        report = Path(tempfile.mkdtemp(prefix="nh80-audit-")) / "content_audit.md"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = audit_content.main(["--report", str(report)])
        self.assertEqual(code, 0, "高危项必须为 0")
        text = report.read_text(encoding="utf-8")
        self.assertIn("高危 0", text)


if __name__ == "__main__":
    unittest.main()
