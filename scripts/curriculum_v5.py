#!/usr/bin/env python3
"""curriculum_v5.py — 生成 150 天课程骨架（v5）。

只依赖 seeds，不依赖旧 curriculum。输出：
  curriculum/curriculum.json
  curriculum/day-001.md ... day-150.md
  curriculum/coverage_v5.md

设计要点：
- 每天 60 分钟，5 块：复习/新词/语法/听力(可选)/练习
- 听力从 Day 47 起，每 7 天 3 次（学习日 %7 ∈ {1,3,5}）
- 新词：常规日约 17，听力日约 12，总量精确等于入库新增数
- 语法：每天 1 条，30 天各 2 条
- 汉字：每天 3 个，30 天各 4 个
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "knowledge/seeds"
OUT = ROOT / "curriculum"

DAYS = 150
PHASES = [
    ("P0", 1, 3, "发音诊断"),
    ("P1", 4, 45, "N5 核心"),
    ("P2", 46, 95, "N4 主体"),
    ("P3", 96, 130, "N3 前半"),
    ("P4", 131, 150, "N3 后半 + 真题"),
]



def read(name):
    return [json.loads(x) for x in (SEED / name).read_text(encoding="utf-8").splitlines() if x.strip()]


def phase_of(day):
    for code, a, b, _ in PHASES:
        if a <= day <= b:
            return code, a, b
    return "P4", 131, 150


def is_listening_day(day):
    return day >= 46 and day % 7 in (1, 3, 5)


def level_of_day(day):
    if day <= 45:
        return "N5"
    if day <= 95:
        return "N4"
    return "N3"


def allocate(items, weights):
    """按权重把 items 顺序分配到 150 天，返回 day -> [item]。"""
    total_w = sum(weights.values())
    counts = {d: max(0, round(len(items) * weights[d] / total_w)) for d in weights}
    diff = len(items) - sum(counts.values())
    for i, d in enumerate(sorted(counts)):
        if diff == 0:
            break
        counts[d] += 1 if diff > 0 else -1
        diff += -1 if diff > 0 else 1
    out, pos = defaultdict(list), 0
    for d in sorted(counts):
        out[d] = items[pos:pos + counts[d]]
        pos += counts[d]
    if pos < len(items):          # 余数给最后一天，保证不丢
        out[150].extend(items[pos:])
    return out


def build():
    vocab = sorted(read("vocabulary.jsonl"), key=lambda x: ("N5 N4 N3".index(x.get("jlpt", "N5")), int(x["id"][1:])))
    grammar = sorted(read("grammar.jsonl"), key=lambda x: ("N5 N4 N3".index(x.get("jlpt", "N5")), int(x["id"][1:])))
    kanji = sorted(read("kanji.jsonl"), key=lambda x: ("N5 N4 N3".index(x.get("jlpt", "N5")), int(x["id"][1:])))
    materials = read("materials.jsonl")

    # v5：从 0 基础开始，全部 2700 词 / 276 语法 / 620 汉字都要排进 150 天，
    # 不能只排「新增」，否则旧 340 词永远不教（复审 P0）。
    new_vocab = list(vocab)
    new_grammar = list(grammar)
    new_kanji = list(kanji)

    def weight(d):
        if d <= 3:
            return 0.5          # 发音诊断期，词量减半
        if is_listening_day(d):
            return 0.7
        if d >= 131:
            return 1.1          # 冲刺期略加压
        return 1.0
    weights = {d: weight(d) for d in range(1, DAYS + 1)}
    vby = allocate(new_vocab, weights)

    # 语法：先按先修拓扑排序，再按天分配；同一天的第二条不能依赖同一天第一条，
    # 否则 start-day 的门控会把它推迟，造成「排了但永远不教」。
    by_id = {g["id"]: g for g in new_grammar}
    order, temp, done = [], set(), set()

    def visit(gid):
        if gid in done or gid in temp:
            return
        temp.add(gid)
        for p in (by_id.get(gid, {}).get("prerequisites") or []):
            if p in by_id:
                visit(p)
        temp.discard(gid)
        done.add(gid)
        order.append(by_id[gid])

    for g in new_grammar:
        visit(g["id"])
    gday = {}
    gby = defaultdict(list)
    pending = list(order)
    for d in range(1, DAYS + 1):
        n = 2 if d <= 126 else 1
        for _ in range(n):
            pick = None
            for cand in pending:
                pre = [p for p in (cand.get("prerequisites") or []) if p in by_id]
                if all(p in gday and gday[p] < d for p in pre):
                    pick = cand
                    break
            if pick is None:
                break
            gby[d].append(pick)
            gday[pick["id"]] = d
            pending.remove(pick)
    for cand in pending:      # 兜底：拓扑异常时放最后，validate 会报
        gby[DAYS].append(cand)
        gday[cand["id"]] = DAYS

    # 汉字：620 / 150 ≈ 4.1，每天 4 个，最后几天补 5
    kby, ki = defaultdict(list), 0
    for d in range(1, DAYS + 1):
        n = 5 if d <= 20 else 4
        kby[d] = new_kanji[ki:ki + n]; ki += n
    while ki < len(new_kanji):
        kby[DAYS].append(new_kanji[ki]); ki += 1

    # 只使用带三题的 v5 原创听力；按级别顺序一次性分配，不循环复用。
    listening_pool = sorted([m for m in materials if m.get("kind") == "listening"
                             and len(m.get("questions", [])) == 3],
                            key=lambda m: (m.get("level", "N4"), m["id"]))
    listening_days = [d for d in range(1, DAYS + 1) if is_listening_day(d)]
    if len(listening_pool) < len(listening_days):
        raise ValueError("听力材料不足，拒绝重复填充")
    mby = {d: [m["id"]] for d, m in zip(listening_days, listening_pool)}

    days = []
    learned_v, learned_g = [], []
    for d in range(1, DAYS + 1):
        ph, a, b = phase_of(d)
        nv = vby.get(d, [])
        ng = gby.get(d, [])
        nk = kby.get(d, [])
        listening = is_listening_day(d)
        # 复习：T+1 / T+3 / T+7
        rev = []
        for back in (1, 3, 7):
            if d - back >= 1:
                rev += [v["id"] for v in vby.get(d - back, [])][:4]
        rev = list(dict.fromkeys(rev))[:12]
        gpat = ng[0]["pattern"] if ng else ""
        patterns = "、".join(g["pattern"] for g in ng)
        meanings = "；".join(g["meaning_zh"] for g in ng)
        scene_key = "grammar-" + "-".join(g["id"] for g in ng)
        scene_zh = patterns or "词句复习"
        can_do_scene = meanings or "用当天新词组织句子"
        can_do = "用「%s」造两句自己的话，表达：%s" % (scene_zh, can_do_scene)
        budgets = [("复习", 10), ("新词", 14 if not listening else 8),
                   ("语法", 6), ("听力", 8 if listening else 0),
                   ("句子输出", 6 if not listening else 5), ("练习", 6 if not listening else 5),
                   ("会话", 18)]
        blocks = [{"type": kind, "min": minutes, "desc": {
            "复习": "到期项优先；未完成顺延，不追赶",
            "新词": "%d 个新词；实际用时超预算时记录未完成" % len(nv),
            "语法": patterns, "听力": "原创 TTS + 3 道理解题；时长为估计，非真人音频",
            "句子输出": "先独立写，再交会话批改", "练习": "6 题即时自评",
            "会话": "抽词、造句、批改"}[kind]} for kind, minutes in budgets if minutes]
        days.append({
            "day": d, "phase": ph, "phase_name": next(name for code, _, _, name in PHASES if code == ph),
            "theme": scene_zh,
            "scene": can_do_scene, "scene_tag": scene_key, "scene_topic_key": scene_key,
            "scene_topic": scene_zh, "can_do": can_do,
            "focus": ["词汇", "语法", "输出"] if not listening else ["词汇", "听力", "输出"],
            "minutes": 60, "blocks": blocks,
            "new_vocab_ids": [v["id"] for v in nv],
            "new_grammar_ids": [g["id"] for g in ng],
            "new_kanji_ids": [k["id"] for k in nk],
            "review_knowledge_ids": rev,
            "material_ids": mby.get(d, []),
            "question_ids": ["web-%03d" % d],
            "listening": listening,
            "assessment": ("diagnostic" if d == 1 else "weekly" if d % 7 == 0 else
                           "stage" if d in (45, 95, 130) else "mock" if d in (110, 132, 148) else "none"),
            "objectives": [
                "认出并读出今天的 %d 个新词" % len(nv),
                "用 %s 造 2 句自己的话" % ("、".join(g["pattern"] for g in ng) or "今天语法"),
                "听完当天素材并回答 3 题" if listening else "独立写当天句子，记录不会的表达",
            ],
            "lesson_core": [
                {"ja": e.get("ja", ""), "zh": e.get("zh", ""), "origin": "grammar_example"}
                for g in ng for e in (g.get("examples") or [])[:2]
            ][:3],
            "review_plan": [],
            "teaching_notes": [],
            "completion": "当天客观题全部作答且正确率 ≥70%；复习与独立输出另由教师核对",
            "review_status": "generated",
        })
        learned_v += [v["id"] for v in nv]
        learned_g += [g["id"] for g in ng]

    data = {
        "meta": {
            "version": "5.0", "days": DAYS, "minutes_per_day": 60,
            "total_hours": DAYS, "listening_from": 47,
            "target": "N3 范围覆盖 85%，真题 55–65%",
            "honesty": "2,700 词覆盖 N3 高频约 85%，不是全量 3,700；不承诺 N3 合格。",
            "generated_at": "2026-11-07",
            "generator": "scripts/curriculum_v5.py",
            "license_note": "词/语法/汉字骨架来自 OpenJLPT（CC-BY-SA-4.0），中文释义与例句翻译为 AI 草稿。",
        },
        "days": days,
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "curriculum.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # 覆盖报告
    c = Counter()
    for d in days:
        c["vocab"] += len(d["new_vocab_ids"])
        c["grammar"] += len(d["new_grammar_ids"])
        c["kanji"] += len(d["new_kanji_ids"])
        c["listening_days"] += 1 if d["listening"] else 0
    lines = ["# v5 覆盖报告", "",
             "- 天数：%d｜总时长：%d 小时" % (DAYS, DAYS),
             "- 新词：%d｜新语法：%d｜新汉字：%d" % (c["vocab"], c["grammar"], c["kanji"]),
             "- 听力日：%d 天（Day 47 起，每周 3 次）" % c["listening_days"],
             "- 词库总量：%d｜语法：%d｜汉字：%d" % (len(vocab), len(grammar), len(kanji)),
             "", "## 每天新词分布", ""]
    dist = Counter(len(d["new_vocab_ids"]) for d in days)
    for n, k in sorted(dist.items()):
        lines.append("- %d 词/天：%d 天" % (n, k))
    (OUT / "coverage_v5.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 每日 md（简版，细节在网页）
    for d in days:
        v = {x["id"]: x for x in vocab}
        g = {x["id"]: x for x in grammar}
        k = {x["id"]: x for x in kanji}
        md = ["# Day %03d · %s" % (d["day"], d["theme"]), "",
              "- 阶段：%s｜%d 分钟｜%s" % (d["phase"], d["minutes"], "听力日" if d["listening"] else "常规日"),
              "- Can-do：%s" % d["can_do"], "",
              "## 新词 %d" % len(d["new_vocab_ids"]), ""]
        for vid in d["new_vocab_ids"]:
            x = v[vid]
            ko = "｜朝鲜语：%s" % x["ko_hanja"] if x.get("ko_hanja") else ""
            ex = x["examples"][0] if x.get("examples") else {"ja": "", "zh": ""}
            md.append("- **%s**（%s）%s%s<br>" % (x["surface"], x["kana"], x["meaning_zh"], ko))
            if ex.get("ja"):
                md.append("  例：%s（%s）" % (ex["ja"], ex.get("zh", "")))
        md += ["", "## 语法", ""]
        for gid in d["new_grammar_ids"]:
            x = g[gid]
            md.append("- **%s**：%s" % (x["pattern"], x["meaning_zh"]))
            md.append("  接续：%s" % x.get("connection", ""))
            if x.get("ko_equiv"):
                md.append("  朝鲜语：%s（%s）" % (x["ko_equiv"], x.get("ko_diff", "")))
        md += ["", "## 汉字 %d" % len(d["new_kanji_ids"]), ""]
        for kid in d["new_kanji_ids"]:
            x = k[kid]
            md.append("- **%s** %s｜音：%s｜训：%s" % (x["char"], x["meaning_zh"],
                                                      "、".join(x.get("onyomi") or []),
                                                      "、".join(x.get("kunyomi") or [])))
        (OUT / ("day-%03d.md" % d["day"])).write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({
        "days": len(days), "new_vocab": c["vocab"], "new_grammar": c["grammar"],
        "new_kanji": c["kanji"], "listening_days": c["listening_days"],
        "vocab_per_day": dict(sorted(Counter(len(d["new_vocab_ids"]) for d in days).items())),
        "total_vocab": len(vocab), "total_grammar": len(grammar), "total_kanji": len(kanji),
    }, ensure_ascii=False, indent=1))
    return data


if __name__ == "__main__":
    build()
