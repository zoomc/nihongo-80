#!/usr/bin/env python3
"""课程对齐回归测试（REVISION_CONTRACT 第 7 节 / P1-2）。

锁定三件事：
1) 点名日（Day 30 医院问诊、Day 46 市政通知）的素材 topic 与 scene_topic_key 一致，
   且 lesson_core 至少一句直接来自该素材正文；
2) 全 80 天 exact 命中率、Can-do 场景标签、新语法在当天素材/例句中有证据；
3) 全量 validate 0 error。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import curriculum as curr  # noqa: E402


class TestCurriculumAlignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = curr.build(ROOT)
        cls.data = cls.built["data"]
        cls.seeds = cls.built["seeds"]
        cls.days = {d["day"]: d for d in cls.data["days"]}
        cls.mmap = {m["id"]: m for m in cls.seeds["materials"]}
        cls.gmap = {g["id"]: g for g in cls.seeds["grammar"]}
        cls.vmap = {v["id"]: v for v in cls.seeds["vocabulary"]}
        cls.validation = curr.validate(cls.data, cls.seeds)

    def _mats(self, day):
        return [self.mmap[mid] for mid in self.days[day].get("material_ids") or []
                if mid in self.mmap]

    def _assert_day(self, day, topic_key, topic_zh):
        d = self.days[day]
        self.assertEqual(d.get("scene_topic_key"), topic_key)
        self.assertEqual(d.get("scene_topic"), topic_zh)
        self.assertEqual(d.get("topic_match"), "exact", "点名日必须是 exact 对齐")
        mats = self._mats(day)
        same = [m for m in mats if m.get("topic") == topic_key]
        self.assertTrue(same, "Day %d 没有 topic=%s 的素材" % (day, topic_key))
        lc = d.get("lesson_core") or []
        self.assertTrue(lc, "Day %d 缺 lesson_core" % day)
        self.assertEqual(lc[0].get("origin"), "material", "Day %d 第一句必须来自素材" % day)
        material_lines = [s for s in lc if s.get("origin") == "material"]
        self.assertTrue(material_lines, "Day %d 无素材句" % day)
        if material_lines[0].get("source_id"):
            src = self.mmap.get(material_lines[0]["source_id"]) or {}
            self.assertEqual(src.get("topic"), topic_key,
                             "Day %d 第一句素材 topic 与场景不一致" % day)

    def test_day30_hospital_matches_material(self):
        self._assert_day(30, "health", "医院问诊")

    def test_day46_notice_matches_material(self):
        self._assert_day(46, "notice", "市政通知")

    def test_exact_ratio_at_least_70_percent(self):
        exact = sum(1 for d in self.days.values() if d.get("topic_match") == "exact")
        ratio = exact / len(self.days)
        self.assertGreaterEqual(ratio, 0.7,
                                "exact 仅 %d/%d = %.2f" % (exact, len(self.days), ratio))

    def test_can_do_contains_scene_topic_every_day(self):
        for day, d in self.days.items():
            topic = d.get("scene_topic") or ""
            self.assertTrue(topic, "Day %d 缺 scene_topic" % day)
            self.assertIn(topic, d.get("can_do") or "",
                          "Day %d Can-do 未包含场景标签「%s」" % (day, topic))

    def test_new_grammar_has_context_evidence_every_day(self):
        for day, d in self.days.items():
            mats = self._mats(day)
            for gid in d.get("new_grammar_ids") or []:
                self.assertTrue(
                    curr._grammar_supported(gid, mats, d.get("new_vocab_ids") or [],
                                            self.gmap, self.vmap),
                    "Day %d 语法 %s 未出现在素材/例句中" % (day, gid))

    def test_lesson_core_and_review_plan_contract(self):
        for day, d in self.days.items():
            lc = d.get("lesson_core") or []
            self.assertEqual(len(lc), 3, "Day %d lesson_core 不是 3 句" % day)
            self.assertTrue(all(s.get("origin") in
                                ("material", "grammar", "vocab", "fallback") for s in lc),
                            "Day %d lesson_core origin 非法" % day)
            for it in d.get("review_plan") or []:
                self.assertIs(it.get("planned_only"), True,
                              "Day %d review_plan 未标 planned_only" % day)

    def test_validate_zero_errors(self):
        self.assertTrue(self.validation["ok"], self.validation["errors"][:10])
        self.assertEqual(self.validation["error_count"], 0)
        al = self.validation.get("alignment") or {}
        self.assertEqual(al.get("exact", 0) + al.get("partial", 0) + al.get("review", 0), 80)
        self.assertGreater(al.get("material_lines", 0), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
