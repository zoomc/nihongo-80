"""report.py — 基于真实落盘数据的周报 / 阶段评估 / 最终报告。

没有数据就明确写「无数据」，绝不编造成绩或鼓励性话术。
"""
from __future__ import annotations

import json
from pathlib import Path

from core import iso, jdump, root_of
from learning import metrics


def _completed(conn):
    """完成天数口径：status='finished' AND passed=1；passed=0 的不算完成。"""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
    if "passed" in cols:
        done = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE status='finished' AND passed=1").fetchone()[0]
    else:
        done = conn.execute("SELECT COUNT(*) FROM sessions WHERE status='finished'").fetchone()[0]
    inc = conn.execute("SELECT COUNT(*) FROM sessions WHERE status='incomplete'").fetchone()[0]
    return int(done or 0), int(inc or 0)


def _acc_by_day(conn, upto=None):
    q = "SELECT day,correct FROM attempts WHERE correct IS NOT NULL"
    args = ()
    if upto:
        q += " AND day<=?"; args = (upto,)
    rows = conn.execute(q, args).fetchall()
    d = {}
    for r in rows:
        d.setdefault(r["day"], []).append(r["correct"])
    return {k: round(sum(v) / len(v), 3) for k, v in sorted(d.items())}


def _sparkline(vals):
    if not vals:
        return "（无数据）"
    blocks = "▁▂▃▄▅▆▇█"
    return " ".join("%s %.2f" % (blocks[min(7, int(v * 8))], v) for v in vals)


def _split_scores(conn, day_lo, day_hi):
    """五维分项：按题目 type 归到能力维度（近似，明确标注为估算）。"""
    rows = conn.execute("""SELECT a.correct,q.type FROM attempts a
        LEFT JOIN questions q ON q.id=a.question_id
        WHERE a.day>=? AND a.day<=? AND a.correct IS NOT NULL""", (day_lo, day_hi)).fetchall()
    dim = {"词汇": [], "语法": [], "阅读": [], "听力": [], "实际表达": []}
    mapping = {"mcq": "词汇", "fill": "语法", "error_correct": "语法", "reorder": "语法",
               "read": "阅读", "listen": "听力", "translate": "实际表达",
               "free_production": "实际表达", "dialogue": "实际表达"}
    for r in rows:
        dim[mapping.get(r["type"], "词汇")].append(r["correct"])
    return {k: (round(sum(v) / len(v), 3) if v else None, len(v)) for k, v in dim.items()}


def _write(path: Path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def weekly(conn, week: int, root=None) -> dict:
    r = root_of(root)
    lo, hi = (week - 1) * 7 + 1, week * 7
    m = metrics(conn, upto_day=hi)
    completed, incomplete = _completed(conn)
    acc = _acc_by_day(conn, upto=hi)
    week_acc = [v for k, v in acc.items() if lo <= k <= hi]
    splits = _split_scores(conn, lo, hi)
    week_graded = conn.execute(
        "SELECT COUNT(*) FROM attempts WHERE day>=? AND day<=? AND correct IS NOT NULL",
        (lo, hi)).fetchone()[0]
    tasks = [dict(x) for x in conn.execute(
        "SELECT * FROM review_tasks WHERE day>=? AND day<=?", (lo, hi)).fetchall()]
    done = sum(1 for t in tasks if t["status"] == "done")
    errs = [dict(x) for x in conn.execute(
        "SELECT * FROM mistakes WHERE day>=? AND day<=?", (lo, hi)).fetchall()]
    ks = [dict(x) for x in conn.execute("SELECT * FROM knowledge_state").fetchall()]
    lines = [
        "# 第 %d 周学习报告（Day %d–%d）" % (week, lo, hi), "",
        "生成时间：%s｜数据来源：`data/state.db`（`attempts` / `fsrs_cards` / `knowledge_state` / `review_tasks`）" % iso(), "",
        "## 1. 是否真有数据", "",
    ]
    if week_graded == 0:
        lines += ["**本周（Day %d–%d）无任何已判分作答记录。** 不生成成绩、不估算能力、不写鼓励性结论。" % (lo, hi),
                  "累计数据存在也不代表本周发生了学习；请先按 `docs/DAILY_SESSION.md` 完成真实教学与 `finish-day`。", ""]
        return {"ok": True, "has_data": False, "path": _write(r / "reports" / ("week-%02d.md" % week), lines)}
    lines += [
        "## 2. 核心指标", "",
        "| 指标 | 数值 | 说明 |", "|---|---|---|",
        "| 已判分作答 | %d | 开放题未判分不计入 |" % m["graded"],
        "| 累计正确率 | %s | 全部已判分题 |" % (("%.1f%%" % (m["accuracy"] * 100)) if m["accuracy"] is not None else "无"),
        "| 本周正确率 | %s | 按天汇总 |" % (("%.1f%%" % (sum(week_acc) / len(week_acc) * 100)) if week_acc else "无"),
        "| 知识覆盖率 | %.1f%% | %d/%d 个知识点至少接触过一次（不等于掌握） |" %
        (m["knowledge_coverage"] * 100, m["knowledge_seen"], m["knowledge_total"]),
        "| 已判定掌握 | %d | 需 transfer 阶段 + 延迟回忆 + 多语境 + 正确率≥0.85 |" % m["mastered"],
        "| 延迟回忆正确过的知识点 | %d | delayed_count > 0 |" % m["delayed_recall_correct"],
        "| 复习任务完成率 | %s | %d/%d（任务状态由脚本维护） |" %
        (("%.1f%%" % (100 * done / len(tasks))) if tasks else "无任务", done, len(tasks)),
        "| 完成天数 / 累计分钟 | %d / %d | 来自 sessions（只计 finished 且 passed=1；未完成 %d 天） |" %
        (completed, m["minutes_total"], incomplete),
        "", "## 3. 能力提升趋势（按天正确率，估算）", "", "```", _sparkline(week_acc), "```", "",
        "## 4. 五维分项（按题型归类，仅为估算，不等同 JLPT 标准分）", "",
        "| 维度 | 正确率 | 样本数 |", "|---|---|---|",
    ]
    for k, (v, n) in splits.items():
        lines.append("| %s | %s | %d |" % (k, ("%.1f%%" % (v * 100)) if v is not None else "无数据", n))
    lines += ["", "## 5. 错误类型分布", ""]
    if errs:
        dist = {}
        for e in errs:
            dist[e["error_type"] or "other"] = dist.get(e["error_type"] or "other", 0) + 1
        for k, v in sorted(dist.items(), key=lambda x: -x[1]):
            lines.append("- **%s**：%d 次 → 补救：按 `agents/reviewer.md` 的映射执行" % (k, v))
    else:
        lines.append("- 本周无错题记录。")
    lines += ["", "## 6. 计划审计（教学总监）", "",
              "- 覆盖检查：%s" % ("全部知识点均至少引入" if m["knowledge_seen"] == m["knowledge_total"]
                                else "尚有 %d 个知识点未接触" % (m["knowledge_total"] - m["knowledge_seen"])),
              "- 到期队列：%d 项" % len([x for x in conn.execute("SELECT due FROM fsrs_cards")]),
              "- 调整记录：%d 条" % conn.execute("SELECT COUNT(*) FROM plan_adjustments").fetchone()[0],
              "- 进度落后时的处理：减少低价值内容、补足基础、增加针对性练习；**不降低测验难度**。",
              "", "## 7. 分数口径声明", "",
              "- 本报告的正确率来自本项目**原创模拟题**的本地作答记录，是过程性指标。",
              "- 不是 JLPT 官方样题成绩，不是 JLPT 标准分（尺度得点），也不预测真实考试分数。",
              "- 官方样题仅作为题型与能力要求的对齐参照，见 `research/source_registry_official.md`。", ""]
    return {"ok": True, "has_data": True, "path": _write(r / "reports" / ("week-%02d.md" % week), lines),
            "metrics": m}


def stage(conn, day: int, root=None, label=None) -> dict:
    r = root_of(root)
    m = metrics(conn, upto_day=day)
    completed, incomplete = _completed(conn)
    splits = _split_scores(conn, max(1, day - 19), day)
    lines = ["# %s（截至 Day %d）" % (label or "阶段评估", day), "",
             "生成时间：%s｜数据来源：`data/state.db`" % iso(), ""]
    if not m["graded"]:
        lines += ["**无已判分作答记录，不生成评估结果。**", ""]
    else:
        lines += ["| 指标 | 数值 |", "|---|---|",
                  "| 已判分作答 | %d |" % m["graded"],
                  "| 累计正确率 | %.1f%% |" % (m["accuracy"] * 100),
                  "| 知识覆盖率 | %.1f%% |" % (m["knowledge_coverage"] * 100),
                  "| 已判定掌握 | %d |" % m["mastered"],
                  "| 完成天数 | %d（未完成 %d 天） |" % (completed, incomplete), "",
                  "## 近 20 天五维分项（估算，非 JLPT 标准分）", "",
                  "| 维度 | 正确率 | 样本 |", "|---|---|---|"]
        for k, (v, n) in splits.items():
            lines.append("| %s | %s | %d |" % (k, ("%.1f%%" % (v * 100)) if v is not None else "无数据", n))
        lines += ["", "## 口径", "", "- 原创模拟题过程数据，非官方样题、非 JLPT 标准分。",
                  "- 落后时优先补基础与减少低价值内容，测验难度不变。", ""]
    fn = "stage-day%03d.md" % day
    return {"ok": True, "path": _write(r / "reports" / fn, lines), "metrics": m}


def final(conn, root=None) -> dict:
    r = root_of(root)
    m = metrics(conn, upto_day=80)
    completed, incomplete = _completed(conn)
    acc = _acc_by_day(conn, upto=80)
    vals = list(acc.values())
    first = sum(vals[:10]) / len(vals[:10]) if vals[:10] else None
    last = sum(vals[-10:]) / len(vals[-10:]) if vals[-10:] else None
    lines = ["# Day 80 综合模拟与最终报告", "", "生成时间：%s" % iso(), "",
             "## 1. 真实数据", "",
             "| 指标 | 数值 |", "|---|---|",
             "| 已判分作答 | %d |" % m["graded"],
             "| 累计正确率 | %s |" % (("%.1f%%" % (m["accuracy"] * 100)) if m["accuracy"] is not None else "无"),
             "| 知识覆盖率 | %.1f%% |" % (m["knowledge_coverage"] * 100),
             "| 已判定掌握 | %d / %d |" % (m["mastered"], m["knowledge_total"]),
             "| 完成天数 | %d / 80（未完成 %d 天，不计完成） |" % (completed, incomplete),
             "| 累计学习分钟 | %d |" % m["minutes_total"],
             "| 前 10 个有数据日正确率 | %s |" % (("%.2f" % first) if first is not None else "无"),
             "| 后 10 个有数据日正确率 | %s |" % (("%.2f" % last) if last is not None else "无"),
             "", "## 2. 能力提升趋势", "", "```", _sparkline(vals), "```", "",
             "## 3. 诚实结论", ""]
    if not m["graded"]:
        lines.append("**尚无真实作答数据，不能对能力作任何判断。** 80 天课程骨架已就绪，但学习尚未发生。")
    else:
        lines += [
            "- 80 天是首轮学习周期，**不是**「第 80 天必达 N3」的成绩承诺。",
            "- 本项目数据只说明「原创模拟题上的过程表现」，**不等于** JLPT N3 合格判定或标准分。",
            "- 若需真实能力锚定，应使用 JLPT 官方公开样题单独组织一次完整模拟（可选时段，不计入 60 分钟），",
            "  并明确标注为官方样题、估算分数，与真实 JLPT 成绩区分。",
            "- 未判定为 mastered 的知识点应进入下一轮周期，不得当作已掌握。",
        ]
    lines += ["", "## 4. 下一阶段规划（确定性建议）", "",
              "- 覆盖率 %.1f%%，剩余 %d 个知识点进入下一轮。" %
              (m["knowledge_coverage"] * 100, m["knowledge_total"] - m["knowledge_seen"]),
              "- 错误类型 TOP：%s" % (", ".join("%s(%d)" % kv for kv in
                                             sorted(m["error_distribution"].items(), key=lambda x: -x[1])[:5]) or "无"),
              "- 继续保持 FSRS 到期队列清零，再逐步提高自由表达比例。", ""]
    return {"ok": True, "path": _write(r / "reports" / "final.md", lines), "metrics": m}
