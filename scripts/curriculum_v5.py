#!/usr/bin/env python3
"""Build the 100-day course and its lesson notes from the knowledge seeds."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "knowledge/seeds"
OUT = ROOT / "curriculum"

DAYS = 100
DAILY_VOCAB = 25
PHASES = [
    ("P0", 1, 3, "N5 入门"),
    ("P1", 4, 26, "N5 核心"),
    ("P2", 27, 50, "N4 主体"),
    ("P3", 51, 84, "N3 词汇与语法"),
    ("P4", 85, 100, "N3 综合与 N2 衔接"),
]
LEVEL_RANGES = {"N5": (1, 26), "N4": (27, 50), "N3": (51, DAYS)}
LEGACY_RANGES = {"N5": (1, 30, 0), "N4": (31, 60, 18), "N3": (61, 120, 27)}


def source_day(day):
    """Map seed-era lessons to the current course numbering."""
    return (day * DAYS + 149) // 150


def legacy_core(words, level):
    """Recover the former mandatory vocabulary before choosing optional words."""
    start, end, count = LEGACY_RANGES[level]
    listening = {start + ((2 * i + 1) * (end - start + 1)) // (2 * count) for i in range(count)}
    weights = {d: 6 if d <= 3 else 9 if d in listening else 10 for d in range(start, end + 1)}
    return {w["id"] for d, batch in allocate(words, weights).items()
            for w in batch[:16 if d in listening else 20]}


def read(name):
    return [json.loads(x) for x in (SEED / name).read_text(encoding="utf-8").splitlines() if x.strip()]


def phase_of(day):
    for code, a, b, _ in PHASES:
        if a <= day <= b:
            return code, a, b
    raise ValueError("day outside course")

def level_of_day(day):
    return next(level for level, (start, end) in LEVEL_RANGES.items() if start <= day <= end)

def allocate(items, weights):
    """按权重把 items 顺序分配到指定课日，返回 day -> [item]。"""
    total = sum(weights.values())
    out, cumulative, previous = {}, 0, 0
    for day, weight in sorted(weights.items()):
        cumulative += weight
        end = round(len(items) * cumulative / total)
        out[day] = items[previous:end]
        previous = end
    return out


def build():
    vocab = sorted(read("vocabulary.jsonl"), key=lambda x: ("N5 N4 N3 N2".index(x.get("jlpt", "N5")), int(x["id"][1:])))
    grammar = sorted(read("grammar.jsonl"), key=lambda x: ("N5 N4 N3 N2".index(x.get("jlpt", "N5")), int(x["id"][1:])))
    kanji = sorted(read("kanji.jsonl"), key=lambda x: ("N5 N4 N3 N2".index(x.get("jlpt", "N5")), int(x["id"][1:])))
    vby, gby, kby = {}, defaultdict(list), {}
    scheduled, last_meaning = {}, {}
    selected_ids = set()
    for level, (start, end) in LEVEL_RANGES.items():
        level_words = [v for v in vocab if v["jlpt"] == level]
        mandatory = legacy_core(level_words, level)
        weights = {d: (14 if d == 1 else DAILY_VOCAB) for d in range(start, end + 1)}
        capacity = sum(weights.values())
        if not len(mandatory) <= capacity <= len(level_words):
            raise ValueError(f"{level}: invalid vocabulary capacity {capacity}")
        promoted = [v["id"] for v in level_words if v["id"] not in mandatory][:capacity - len(mandatory)]
        chosen = mandatory | set(promoted)
        selected_ids.update(chosen)
        vby.update(allocate([v for v in level_words if v["id"] in chosen], weights))
        characters = [k for k in kanji if k["jlpt"] == level]
        if start == 1:
            kby[1], characters = characters[:3], characters[3:]
        kby.update(allocate(characters, {d: 1 for d in weights if d != 1}))
        pending = [g for g in grammar if g["jlpt"] == level]
        if start == 1:
            gby[1] = [next(g for g in pending if g["id"] == gid) for gid in ("G0001", "G0261")]
            for g in gby[1]:
                scheduled[g["id"]] = 1
                pending.remove(g)
        slots = allocate(pending, {d: 1 for d in weights if d != 1})
        for day in slots:
            for _ in slots[day]:
                ready = [g for g in pending if all(scheduled.get(p, DAYS) < day
                                                   for p in g.get("prerequisites", []))]
                if not ready:
                    break
                pick = next((g for g in ready if day - last_meaning.get(g["meaning_zh"], -7) >= 7), ready[0])
                gby[day].append(pick)
                scheduled[pick["id"]] = day
                last_meaning[pick["meaning_zh"]] = day
                pending.remove(pick)
        if pending:
            raise ValueError("语法排课缺少先修或课时：" + ", ".join(g["id"] for g in pending))

    bridge = [g for g in grammar if g["jlpt"] == "N2"]
    bridge_days = list(range(85, 101))
    for i, g in enumerate(bridge):
        gby[bridge_days[i * len(bridge_days) // len(bridge)]].append(g)

    days = []
    for d in range(1, DAYS + 1):
        ph, a, b = phase_of(d)
        nv = vby.get(d, [])
        ng = gby.get(d, [])
        nk = kby.get(d, [])
        rev = []
        for back in (1, 3, 7):
            if d > back:
                previous = d - back
                offset = {1: 0, 3: 2, 7: 4}[back]
                words, grammar_items, characters = vby[previous], gby[previous], kby[previous]
                rev.extend(words[(offset + i) % len(words)]["id"] for i in range(2))
                rev.append(grammar_items[offset % len(grammar_items)]["id"])
                rev.append(characters[offset % len(characters)]["id"])
        patterns = "、".join(g["pattern"] for g in ng)
        scene_key = "grammar-" + "-".join(g["id"] for g in ng)
        can_do_scene = "；".join(g["meaning_zh"] for g in ng)
        can_do = "在单选题中辨认今天的词义、读音和句型用法。"
        blocks = [
            {"type": "记忆曲线复习", "min": 10, "desc": "先做已到期的复习题"},
            {"type": "新词", "min": 16, "desc": f"{len(nv)} 个新词"},
            {"type": "语法", "min": 9, "desc": patterns},
            {"type": "练习", "min": 25, "desc": "单选题，答完可重练错题"},
        ]
        days.append({
            "day": d, "phase": ph, "phase_name": next(name for code, _, _, name in PHASES if code == ph),
            "theme": patterns,
            "scene": can_do_scene, "scene_tag": scene_key, "scene_topic_key": scene_key,
            "scene_topic": patterns, "can_do": can_do,
            "focus": ["词汇", "语法", "单选"],
            "minutes": 60, "blocks": blocks,
            "new_vocab_ids": [v["id"] for v in nv],
            "core_vocab_ids": [v["id"] for v in nv],
            "extension_vocab_ids": [],
            "new_grammar_ids": [g["id"] for g in ng],
            "new_kanji_ids": [k["id"] for k in nk],
            "review_knowledge_ids": rev,
            "review_snapshot_note": "静态预览；权威 FSRS 到期队列见 learning.due_queue()",
            "material_ids": [],
            "question_ids": [],
            "practice_mode": "choice",
            "listening": False,
            "assessment": "none",
            "objectives": [can_do],
            "lesson_core": [
                {"ja": e.get("ja", ""), "zh": e.get("zh", ""), "origin": "grammar_example"}
                for g in ng for e in (g.get("examples") or [])[:2]
            ][:6],
            "review_plan": [],
            "teaching_notes": [],
            "completion": "当天单选题全部作答且正确率 ≥70%",
            "review_status": "generated",
        })

    data = {
        "meta": {
            "version": "15.0", "days": DAYS, "minutes_per_day": 60,
            "total_hours": DAYS,
            "target": "N3 词汇与语法，后段增加 N2 衔接",
            "honesty": "主课 2489 词，选学词单独查阅；N2 条目为衔接练习。",
            "generated_at": "2026-11-08",
            "generator": "scripts/curriculum_v5.py",
            "license_note": "词/语法/汉字骨架来自 OpenJLPT（CC-BY-SA-4.0），中文释义与例句翻译为 AI 草稿。",
        },
        "days": days,
        "optional_vocab_ids": [v["id"] for v in vocab if v["id"] not in selected_ids],
    }
    if not OUT.is_dir():
        OUT.mkdir(parents=True)
    (OUT / "curriculum.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # 覆盖报告
    c = Counter()
    for d in days:
        c["vocab"] += len(d["new_vocab_ids"])
        c["grammar"] += len(d["new_grammar_ids"])
        c["kanji"] += len(d["new_kanji_ids"])
        c["listening_days"] += 1 if d["listening"] else 0
    lines = ["# v7 覆盖报告", "",
             "- 天数：%d｜总时长：%d 小时" % (DAYS, DAYS),
             "- 新词：%d｜新语法：%d｜新汉字：%d" % (c["vocab"], c["grammar"], c["kanji"]),
             "- 主课听力日：%d 天；选学词：%d 个" % (c["listening_days"], len(data["optional_vocab_ids"])),
             "- 词库总量：%d｜语法：%d｜汉字：%d" % (len(vocab), len(grammar), len(kanji)),
             "", "## 每天新词分布", ""]
    dist = Counter(len(d["new_vocab_ids"]) for d in days)
    for n, k in sorted(dist.items()):
        lines.append("- %d 词/天：%d 天" % (n, k))
    (OUT / "coverage_v5.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    for path in OUT.glob("day-[0-9][0-9][0-9].md"):
        if int(path.stem[4:]) > DAYS:
            path.unlink()

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
            ko = "｜韩语参考：%s" % (x.get("ko_hint") or x.get("ko_hanja")) if (x.get("ko_hint") or x.get("ko_hanja")) else ""
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
