#!/usr/bin/env python3
"""Nihongo 80 验收测试：静态完整性 + 学习引擎 + Day 1-3 端到端演练。

运行： python3 tests/test_all.py
所有状态写入 /tmp/nh80-test-<pid>，不污染真实项目。
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
TMP = Path(tempfile.mkdtemp(prefix="nh80-test-"))
CLI = ROOT / "scripts" / "nh80.py"

import core  # noqa: E402
import curriculum as curr  # noqa: E402
import learning  # noqa: E402
from fsrs import Card, Rating  # noqa: E402


def run(*args, expect_ok=True):
    import subprocess
    p = subprocess.run([sys.executable, str(CLI), "--root", str(TMP), *args],
                       capture_output=True, text=True, cwd=str(ROOT))
    if expect_ok and p.returncode != 0:
        raise AssertionError("CLI 失败 %s: %s" % (args, (p.stderr or p.stdout)[-900:]))
    return p


def jrun(*args, expect_ok=True):
    p = run(*args, expect_ok=expect_ok)
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"raw": p.stdout[-500:], "returncode": p.returncode, "stderr": p.stderr[-500:]}


def b64code(payload):
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    return "NH80R1." + base64.urlsafe_b64encode(raw).decode().rstrip("=")


def setUpModule():
    for d in ("config", "knowledge/seeds", "curriculum", "agents", "student",
              "data/backups", "scripts", "tests", "reports", "docs", "web/assets",
              "deploy/worker/src", "sessions"):
        (TMP / d).mkdir(parents=True, exist_ok=True)
    for f in (ROOT / "knowledge" / "seeds").glob("*.jsonl"):
        shutil.copy2(f, TMP / "knowledge" / "seeds" / f.name)
    res = jrun("init")
    assert res.get("ok"), "init 失败: %s" % res


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


class TestAStatic(unittest.TestCase):
    """1) 真实资源构建可检索知识库  2) 全部 80 天详细课程  3) 检索方式对比"""

    def test_01_db_and_fts(self):
        conn = core.connect(TMP, readonly=True)
        try:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn("search_fts", tables)
            # 种子数量从真实文件动态读取：补齐 N4/N3 后不再硬编码旧数字
            for f in sorted((ROOT / "knowledge" / "seeds").glob("*.jsonl")):
                n = sum(1 for line in f.read_text(encoding="utf-8").splitlines() if line.strip())
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM %s" % f.stem).fetchone()[0], n, f.stem)
            self.assertGreater(conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0], 500)
        finally:
            conn.close()

    def test_01b_framework_delivery(self):
        """v2 框架：分级兑现与去模板化必须被强校验，而不是只查覆盖率。"""
        v = jrun("validate")
        self.assertTrue(v["ok"], "课程校验失败: %s" % v.get("errors"))
        self.assertGreaterEqual(v["level_delivery"].get("P4", {}).get("N3", 0), 40,
                                "P4 标称 N3 冲刺却没引入 N3 知识")
        self.assertGreaterEqual(v["level_delivery"].get("P3", {}).get("N4", 0), 20)
        self.assertGreaterEqual(v["teaching_design"]["distinct_objectives"], 70)
        self.assertGreaterEqual(v["teaching_design"]["distinct_can_do"], 55)
        days = json.loads((TMP / "curriculum" / "curriculum.json").read_text(encoding="utf-8"))["days"]
        self.assertTrue(all(d.get("can_do") and d.get("focus") for d in days))
        self.assertTrue(any(d["phase"] == "P4" and d["new_vocab_ids"] for d in days))

    def test_02_keyword_relation_semantic(self):
        kw = core.search(TMP, "食べる", "keyword")
        self.assertTrue(any(x["id"] == "V0101" for x in kw["keyword"]), "FTS5 应命中 食べる")
        rel = core.search(TMP, "V0001", "relation")
        self.assertTrue(rel["relation"], "结构化关系检索应有结果")
        sem = core.search(TMP, "吃饭", "semantic")
        self.assertFalse(sem["enabled"], "语义检索必须明确标注未启用")
        conn = core.connect(TMP, readonly=True)
        try:
            chain = core.relation_chain(conn, "V0001")
            self.assertTrue(any(s[0].startswith("example") or s[1] for s in chain["steps"]))
        finally:
            conn.close()

    def test_03_80_days_complete(self):
        data = json.loads((TMP / "curriculum" / "curriculum.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["days"]), 80)
        self.assertEqual([d["day"] for d in data["days"]], list(range(1, 81)))
        for d in data["days"]:
            p = TMP / "curriculum" / ("day-%03d.md" % d["day"])
            self.assertTrue(p.exists() and p.stat().st_size > 500, "Day %d md 过小" % d["day"])
            w = TMP / "web" / ("day-%03d.html" % d["day"])
            self.assertTrue(w.exists(), "缺少网页 Day %d" % d["day"])
            self.assertEqual(sum(b["min"] for b in d["blocks"]), 60)
            self.assertGreaterEqual(len(d["question_ids"]), 5)
            self.assertTrue(d["scene"] and d["completion"] and d["objectives"])
        self.assertTrue((TMP / "curriculum" / "roadmap.md").exists())
        self.assertTrue((TMP / "curriculum" / "coverage_report.md").exists())

    def test_04_prerequisites_and_no_spoilers(self):
        v = jrun("validate")
        self.assertTrue(v["ok"], v.get("errors"))
        self.assertEqual(v["error_count"], 0)
        self.assertTrue(all(v["coverage"][k]["unused_count"] == 0 for k in v["coverage"]))
        self.assertEqual(v["assessments"]["1"], "diagnostic")
        self.assertEqual(v["assessments"]["80"], "final")
        self.assertEqual(v["assessments"]["40"], "midterm")
        self.assertEqual(v["assessments"]["60"], "n3_readiness")
        # 同一天只有一个 assessment（不叠加）
        day1 = json.loads((TMP / "curriculum" / "curriculum.json").read_text(encoding="utf-8"))["days"][0]
        self.assertEqual(day1["assessment"], "diagnostic")
        self.assertEqual(len(day1["question_ids"]), 8)

    def test_05_external_materials_have_no_body(self):
        mats = [json.loads(x) for x in (TMP / "knowledge/seeds/materials.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        for m in mats:
            if m.get("review_status") == "index_only":
                self.assertFalse(m.get("text_ja"), "%s 不应内嵌外部正文" % m["id"])


class TestBEngine(unittest.TestCase):
    """4) FSRS 确定性  5) 五阶段掌握  6) 错误补救"""

    def test_01_fsrs_official_and_deterministic(self):
        s = learning.scheduler()
        self.assertEqual(len(s.parameters), 21, "应为官方 FSRS 21 参数")
        self.assertEqual(s.desired_retention, 0.9)
        self.assertFalse(s.enable_fuzzing)
        t = datetime(2026, 11, 6, 8, 0, tzinfo=timezone.utc)
        a = s.review_card(Card(), Rating.Good, t)[0]
        b = learning.scheduler().review_card(Card(), Rating.Good, t)[0]
        self.assertEqual(a.to_dict()["due"], b.to_dict()["due"], "同输入必须同 due")
        self.assertNotEqual(a.to_dict()["due"], t.isoformat())

    def test_02_one_correct_is_not_mastered(self):
        conn = core.connect(TMP)
        try:
            st = learning._knowledge_state(conn, "VTEST1", "vocabulary")
            t = datetime(2026, 11, 6, tzinfo=timezone.utc)
            st = learning._update_mastery(st, day=1, correct=True, hinted=False,
                                          context="mcq:1", error_type=None, at=t)
            self.assertEqual(st["stage"], "independent_recall")
            self.assertEqual(st["mastered"], 0, "一次答对绝不能认定掌握")
            # 构造满足 transfer 的全部条件
            for i, (ctx, days) in enumerate((("fill:3", 2), ("listen:5", 4),
                                             ("dialogue:9", 8), ("read:12", 10))):
                st = learning._update_mastery(st, day=1 + days, correct=True, hinted=False,
                                              context=ctx, error_type=None, at=t + timedelta(days=days))
            self.assertEqual(st["stage"], "transfer")
            self.assertEqual(st["mastered"], 1)
            # 遗忘必须退回
            st = learning._update_mastery(st, day=12, correct=False, hinted=False,
                                          context="mcq:12", error_type="forgetting",
                                          at=t + timedelta(days=11))
            self.assertEqual(st["stage"], "hinted_recall")
            self.assertEqual(st["mastered"], 0)
        finally:
            conn.rollback(); conn.close()

    def test_03_error_remedy_mapping(self):
        for e, r in learning.REMEDY.items():
            self.assertTrue(r and isinstance(r, str))
        self.assertIn("主动回忆", learning.REMEDY["forgetting"])
        self.assertIn("助词", learning.REMEDY["particle"])
        self.assertIn("听写", learning.REMEDY["listening"])


class TestCFlow(unittest.TestCase):
    """Day 1-3 端到端：3) 启动 4) 批改 5) 错误持久化 6) 复习 7) 次日读取
       8) 计划调整 9) 周报 10) 关会话重开不丢状态"""

    def test_01_start_day1(self):
        p = run("start-day", "1")
        self.assertIn("Day 001", p.stdout)
        self.assertIn("Q0181", p.stdout)
        self.assertTrue((TMP / "sessions" / "day-001-brief.md").exists())

    def test_02_answer_and_grade(self):
        good = jrun("answer", "--day", "1", "--q", "Q0181", "--answer", "は")
        self.assertTrue(good["ok"] and good["correct"] is True)
        # v4：状态按「知识点|能力」分卡，stages 的键是 G0001|usage 这类复合键。
        self.assertTrue(any(k.startswith("G0001") for k in good["stages"]),
                        "答对助词题必须推进对应语法能力卡：%s" % good["stages"])
        bad = jrun("answer", "--day", "1", "--q", "Q0182", "--answer", "だ",
                   "--error-type", "particle")
        self.assertFalse(bad["correct"])
        self.assertEqual(bad["error_type"], "particle")
        self.assertTrue(bad["remedy"])
        # 开放题挂起 -> AI 判定补录
        pend = jrun("answer", "--day", "1", "--q", "Q0187", "--answer", "私は李です。", "--pending")
        self.assertTrue(pend["open_pending"])
        graded = jrun("grade-open", "--q", "Q0187", "--correct", "1")
        self.assertTrue(graded["ok"] and graded["correct"] is True)

    def test_03_finish_day1_and_persist(self):
        res = jrun("finish-day", "1", "--minutes", "58")
        self.assertTrue(res["ok"])
        self.assertIn("未达标", res["summary"], "未完成全部题不得标记达标")
        conn = core.connect(TMP, readonly=True)
        try:
            self.assertGreaterEqual(conn.execute("SELECT COUNT(*) FROM attempts WHERE day=1").fetchone()[0], 3)
            self.assertGreaterEqual(conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0], 1)
            self.assertGreater(conn.execute("SELECT COUNT(*) FROM fsrs_cards").fetchone()[0], 0)
            self.assertIsNotNone(conn.execute("SELECT summary FROM daily_summary WHERE day=1").fetchone()[0])
        finally:
            conn.close()
        self.assertTrue((TMP / "student" / "mistakes.json").exists())

    def test_04_day2_reads_previous_summary(self):
        p = run("start-day", "2")
        self.assertIn("上一日总结", p.stdout)
        self.assertNotIn("**无**（首日或尚未 finish-day）", p.stdout, "次日必须读到昨日总结")
        self.assertIn("Day 1 完成", p.stdout, "必须读到上一日真实记录")
        self.assertIn("复习候选池：V0001", p.stdout, "次日必须带出旧知识复习")

    def test_05_fsrs_due_and_remedy_tasks(self):
        conn = core.connect(TMP, readonly=True)
        try:
            due = conn.execute("SELECT COUNT(*) FROM fsrs_cards WHERE due IS NOT NULL").fetchone()[0]
            self.assertGreater(due, 0, "必须安排下一次复习")
            tasks = conn.execute("SELECT COUNT(*) FROM review_tasks WHERE remedy!=''").fetchone()[0]
            self.assertGreater(tasks, 0, "错误必须有补救任务")
        finally:
            conn.close()

    def test_06_web_result_import_idempotent(self):
        payload = {"v": 1, "day": 2, "session": "session-20261106-002",
                   "ts": "2026-11-06T16:00:00+08:00", "minutes": 18, "source": "web",
                   "results": [
                       {"qid": "Q0189", "answer": "ではありません", "correct": True,
                        "hinted": False, "seconds": 11, "error_type": None},
                       {"qid": "Q0188", "answer": "こんにちは。私は李です。", "correct": True,
                        "hinted": False, "seconds": 40, "error_type": None},
                   ]}
        code = b64code(payload)
        r1 = jrun("import-web-result", code)
        self.assertTrue(r1["ok"])
        self.assertIn("Q0189", r1["applied"])
        self.assertIn("Q0188", r1["open_pending_need_ai_grade"], "开放题必须挂起等 AI 判定")
        r2 = jrun("import-web-result", code)
        self.assertEqual(sorted(r2["duplicate_skipped"]), ["Q0188", "Q0189"], "重复导入必须幂等")
        bad = run("import-web-result", b64code({**payload, "results": [
            {"qid": "Q9999", "answer": "x", "correct": True}]}), expect_ok=False)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("未知题目", bad.stderr)

    def test_06b_review_ratings_drive_fsrs(self):
        """v3：网页「今日复习」三档自评必须真正写回 FSRS，且不得判定掌握。"""
        payload = {"v": 1, "day": 2, "session": "session-20261106-review",
                   "ts": "2026-11-06T17:00:00+08:00", "minutes": 6, "source": "web",
                   "results": [],
                   "review_ratings": [{"kid": "V0260", "rating": "good"},
                                      {"kid": "V0259", "rating": "again"}]}
        code = b64code(payload)
        r1 = jrun("import-web-result", code)
        self.assertTrue(r1["ok"])
        self.assertEqual(sorted(r1["review_ratings_applied"]), ["V0259", "V0260"])
        r2 = jrun("import-web-result", code)
        self.assertEqual(sorted(r2["review_ratings_duplicate"]), ["V0259", "V0260"],
                         "同一会话重复导入必须幂等，不能把复习时间推进两次")
        bad = jrun("import-web-result", b64code({**payload, "session": "session-review-bad",
                   "review_ratings": [{"kid": "V0260", "rating": "unknown"}]}))
        self.assertEqual(len(bad["review_ratings_rejected"]), 1, "非法档位必须拒绝")
        conn = core.connect(TMP, readonly=True)
        try:
            for kid in ("V0259", "V0260"):
                card = conn.execute(
                    "SELECT reps,due FROM fsrs_cards WHERE knowledge_id LIKE ?",
                    (kid + "%",)).fetchone()
                self.assertIsNotNone(card, "复习自评必须落一张卡（无作答记录时为预习卡）")
                # v4：没有真实作答记录的“记住了”只能建预习卡，不能算一次成功复习。
                self.assertEqual(card["reps"], 0,
                                 "无作答记录的自评不得推进 FSRS 复习次数，只能排到明天预习")
                self.assertTrue(card["due"], "必须算出下次复习时间")
                st = conn.execute("SELECT mastered,stage FROM knowledge_state WHERE knowledge_id=?",
                                  (kid,)).fetchone()
                if st is not None:   # v4 允许完全不建掌握状态行：自评不等于学习证据
                    self.assertEqual(st["mastered"], 0, "自评不得判定掌握")
                    self.assertEqual(st["stage"], "unseen", "自评不得推进掌握阶段")
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM attempts WHERE day=2 AND qid IN ('V0259','V0260')")
                            .fetchone()[0], 0, "复习自评不是题目作答，不得写 attempts")
        finally:
            conn.close()

    def test_07_day3_and_adjust(self):
        jrun("grade-open", "--q", "Q0188", "--correct", "1")
        jrun("answer", "--day", "2", "--q", "Q0190", "--answer", "ございます")
        jrun("finish-day", "2", "--minutes", "61")
        adj = jrun("adjust", "--day", "2")
        self.assertTrue(adj["ok"])
        self.assertIn("仅调整动态任务", adj["note"])
        conn = core.connect(TMP, readonly=True)
        try:
            self.assertGreater(conn.execute("SELECT COUNT(*) FROM plan_adjustments").fetchone()[0], 0)
        finally:
            conn.close()
        p = run("start-day", "3")
        self.assertIn("Day 003", p.stdout)

    def test_08_weekly_report_real_data(self):
        rep = jrun("report", "--week", "1")
        self.assertTrue(rep["ok"] and rep["has_data"])
        text = (TMP / "reports" / "week-01.md").read_text(encoding="utf-8")
        self.assertIn("已判分作答", text)
        self.assertIn("不是 JLPT 官方样题成绩", text)
        empty = jrun("report", "--week", "12")
        self.assertFalse(empty["has_data"], "无数据的周必须如实说明")
        self.assertIn("无任何已判分作答", (TMP / "reports" / "week-12.md").read_text(encoding="utf-8"))

    def test_09_backup_restore_audit(self):
        bk = jrun("backup")
        self.assertTrue(bk["ok"] and Path(bk["backup"]).exists())
        a = jrun("audit", "--limit", "5")
        self.assertEqual(len(a), 5)
        # 关掉所有连接后重新读：状态不丢
        st1 = jrun("status")
        self.assertGreaterEqual(st1["metrics"]["attempts"], 5)
        st2 = jrun("status")
        self.assertEqual(st1["metrics"]["attempts"], st2["metrics"]["attempts"])
        self.assertGreater(st2["metrics"]["knowledge_seen"], 0)
        self.assertGreater(st2["metrics"]["mastered"], -1)

    def test_10_new_session_prompt_reads_real_state(self):
        import subprocess
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "new_session_prompt.py"), "3"],
                           capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(p.returncode, 0)
        self.assertIn("Day 3", p.stdout)   # 文档脚本默认读真实项目根；此处只验证不崩溃


if __name__ == "__main__":
    print("测试根目录:", TMP)
    unittest.main(verbosity=2)
