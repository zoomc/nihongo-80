#!/usr/bin/env python3
"""curriculum_v5.py — 生成 120 天课程骨架（v5）。

只依赖 seeds，不依赖旧 curriculum。输出：
  curriculum/curriculum.json
  curriculum/day-001.md ... day-120.md
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

DAYS = 120
PHASES = [
    ("P0", 1, 3, "假名与听辨"),
    ("P1", 4, 30, "N5 核心"),
    ("P2", 31, 60, "N4 主体"),
    ("P3", 61, 95, "N3 词句与听读"),
    ("P4", 96, 120, "N3 综合与自测"),
]
LEVEL_RANGES = {"N5": (1, 30), "N4": (31, 60), "N3": (61, DAYS)}
READING_DAYS = {10:"M0001", 20:"M0009", 40:"M0017", 55:"M0036",
                65:"M0037", 75:"M0041", 85:"M0045", 95:"M0063",
                105:"M0067", 115:"M0075"}
PRACTICE_NOTES = {
    1: "听辨与跟读：先认识五个元音 あ・い・う・え・お（片假名 ア・イ・ウ・エ・オ），按五个拍子读一遍。再听 か・が，比较清音和浊音。",
    2: "听辨与跟读：比较 きて（き・て）和 きって（き・っ・て），小っ占一拍；再比较 きや（き・や）和 きゃ（一拍）。",
    3: "听辨与跟读：比较 おばさん 和 おばあさん，长音多一拍；把 こんにちは 分成 こ・ん・に・ち・は，ん 单独占一拍，末尾 は 读 wa。",
    30: "阶段回顾：从 Day 26–30 的复习单元挑出五个容易混的词，先听读，再用两条句型各说一句。",
    60: "阶段回顾：从本阶段选一篇听力，听完复述谁、何时、要做什么，再回看脚本核对遗漏。",
    90: "N3 题型练习：做官方词汇样题，标出读音、语境选词、近义改写和用法中最容易失分的一类。",
    100: "N3 题型练习：做官方句子排序和文章语法样题。先找句尾谓语，再用指示词、接续词核对上下文。",
    110: "N3 题型练习：做官方长文、信息检索和即时应答样题。检索先圈条件，应答先听句末意图。",
    120: "N3 自测安排：在课外单独留出官方练习卷的计时段，按词汇 30、语法与阅读 70、听力 40 分钟完成；将错题按题型带回会话。",
}
EARLY_AUDIO = {1: "あ、い、う、え、お。か、が。", 2: "きて。きって。きや。きゃ。", 3: "おばさん。おばあさん。こんにちは。"}

def source_day(day):
    """Map a v10 source row to its new lesson without editing the seed."""
    return (day * DAYS + 149) // 150

def listening_schedule(start, end, count):
    return {start + ((2 * i + 1) * (end - start + 1)) // (2 * count) for i in range(count)}

LISTENING_DAYS = listening_schedule(31, 60, 18) | listening_schedule(61, DAYS, 27)

def read(name):
    return [json.loads(x) for x in (SEED / name).read_text(encoding="utf-8").splitlines() if x.strip()]


def phase_of(day):
    for code, a, b, _ in PHASES:
        if a <= day <= b:
            return code, a, b
    raise ValueError("day outside course")

def is_listening_day(day):
    return day in LISTENING_DAYS

def level_of_day(day):
    return next(level for level, (start, end) in LEVEL_RANGES.items() if start <= day <= end)

def core_vocab_limit(listening):
    return 16 if listening else 20


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
    vocab = sorted(read("vocabulary.jsonl"), key=lambda x: ("N5 N4 N3".index(x.get("jlpt", "N5")), int(x["id"][1:])))
    grammar = sorted(read("grammar.jsonl"), key=lambda x: ("N5 N4 N3".index(x.get("jlpt", "N5")), int(x["id"][1:])))
    kanji = sorted(read("kanji.jsonl"), key=lambda x: ("N5 N4 N3".index(x.get("jlpt", "N5")), int(x["id"][1:])))
    materials = read("materials.jsonl")

    vby, gby, kby = {}, defaultdict(list), {}
    scheduled = {}
    last_meaning = {}
    for level, (start, end) in LEVEL_RANGES.items():
        weights = {d: (6 if d <= 3 else 9 if is_listening_day(d) else 10)
                   for d in range(start, end + 1)}
        vby.update(allocate([v for v in vocab if v["jlpt"] == level], weights))
        kby.update(allocate([k for k in kanji if k["jlpt"] == level], dict.fromkeys(weights, 1)))
        pending = [g for g in grammar if g["jlpt"] == level]
        slots = allocate(pending, dict.fromkeys(weights, 1))
        for day in weights:
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

    assessment_by_day = {source_day(x["day"]): x["assessment"] for x in read("assessments.jsonl")}
    # 只使用带三题的 v5 原创听力；按级别顺序一次性分配，不循环复用。
    rank = {"N5": 0, "N4": 1, "N3": 2}
    listening_pool = sorted([m for m in materials if m.get("kind") == "listening"
                             and len(m.get("questions", [])) == 3],
                            key=lambda m: (rank.get(m.get("level"), 1), m["id"]))
    listening_days = [d for d in range(1, DAYS + 1) if is_listening_day(d)]
    if len(listening_pool) < len(listening_days):
        raise ValueError("听力材料不足，拒绝重复填充")
    mby = {d: [m["id"]] for d, m in zip(listening_days, listening_pool)}

    days = []
    for d in range(1, DAYS + 1):
        ph, a, b = phase_of(d)
        nv = vby.get(d, [])
        ng = gby.get(d, [])
        nk = kby.get(d, [])
        listening = is_listening_day(d)
        core_limit = core_vocab_limit(listening)
        essential = nv[:core_limit]
        extension = nv[core_limit:]
        # 复习快照：T+1 / T+3 / T+7，词汇 + 语法 + 汉字三类都要复现。
        # 这是公开页的静态预览；权威到期队列仍由 learning.due_queue() 在私人会话里给出。
        rev = []
        for back in (1, 3, 7):
            if d - back >= 1:
                words = vby[d - back]
                grammar_items = gby[d - back]
                characters = kby[d - back]
                start = {1: 0, 3: 2, 7: 4}[back]
                rev.extend(words[(start + i) % len(words)]["id"] for i in range(2))
                rev.append(grammar_items[start % len(grammar_items)]["id"])
                rev.append(characters[start % len(characters)]["id"])
        gpat = ng[0]["pattern"] if ng else ""
        patterns = "、".join(g["pattern"] for g in ng)
        meanings = "；".join(g["meaning_zh"] for g in ng)
        scene_key = "grammar-" + "-".join(g["id"] for g in ng)
        scene_zh = patterns or "词句复习"
        can_do_scene = meanings or "用当天新词组织句子"
        can_do = "用「%s」各造一句自己的话，表达：%s" % (scene_zh, can_do_scene)
        budgets = [("复习", 5 if listening else 6), ("新词", 8 if listening else 11),
                   ("语法", 5 if listening else 6), ("听力", 7 if listening else 0),
                   ("句子输出", 4), ("练习", 13 if listening else 15),
                   ("会话", 18)]
        blocks = [{"type": kind, "min": minutes, "desc": {
            "复习": "到期项优先；未完成顺延，不追赶",
            "新词": "%d 个必学词；%d 个选学拓展" % (len(essential), len(extension)),
            "语法": patterns, "听力": "先听并复述主旨，再找两个细节，最后核对脚本（原创合成语音）",
            "句子输出": "每条新语法独立说一句，和例句对照", "练习": "优先做当天必学词与语法，答完重练错题",
            "会话": "抽词、造句、批改"}[kind]} for kind, minutes in budgets if minutes]
        days.append({
            "day": d, "phase": ph, "phase_name": next(name for code, _, _, name in PHASES if code == ph),
            "theme": scene_zh,
            "scene": can_do_scene, "scene_tag": scene_key, "scene_topic_key": scene_key,
            "scene_topic": scene_zh, "can_do": can_do,
            "focus": ["词汇", "语法", "输出"] if not listening else ["词汇", "听力", "输出"],
            "minutes": 60, "blocks": blocks,
            "new_vocab_ids": [v["id"] for v in nv],
            "core_vocab_ids": [v["id"] for v in essential],
            "extension_vocab_ids": [v["id"] for v in extension],
            "new_grammar_ids": [g["id"] for g in ng],
            "new_kanji_ids": [k["id"] for k in nk],
            "review_knowledge_ids": rev,
            "review_snapshot_note": "静态预览；权威 FSRS 到期队列见 learning.due_queue()",
            "material_ids": mby.get(d, []),
            "question_ids": ["web-%03d" % d],
            "listening": listening,
            "assessment": "diagnostic" if d == 1 else assessment_by_day.get(d, "none"),
            "reading_id": READING_DAYS.get(d),
            "practice_note": PRACTICE_NOTES.get(d, ""),
            "early_audio": EARLY_AUDIO.get(d, ""),
            "objectives": [
                "认出并读出今天的 %d 个必学词；其余拓展自选" % len(essential),
                "用 %s 造 2 句自己的话" % ("、".join(g["pattern"] for g in ng) or "今天语法"),
                "听完当天素材并回答 3 题" if listening else "独立写当天句子，记录不会的表达",
            ],
            "lesson_core": [
                {"ja": e.get("ja", ""), "zh": e.get("zh", ""), "origin": "grammar_example"}
                for g in ng for e in (g.get("examples") or [])[:2]
            ][:6],
            "review_plan": [],
            "teaching_notes": [],
            "completion": "当天 6 题（抽样）全部作答且正确率 ≥70%；复习与独立输出另由教师核对",
            "review_status": "generated",
        })

    data = {
        "meta": {
            "version": "11.0", "days": DAYS, "minutes_per_day": 60,
            "total_hours": DAYS, "listening_from": min(LISTENING_DAYS),
            "target": "N3词句学习、读解听解训练与官方样题自测",
            "honesty": "2700词完整资源；必学与拓展分开；6题为当天新内容抽样，不覆盖全部条目；成绩以官方试题自测为准。",
            "generated_at": "2026-11-08",
            "generator": "scripts/curriculum_v5.py",
            "license_note": "词/语法/汉字骨架来自 OpenJLPT（CC-BY-SA-4.0），中文释义与例句翻译为 AI 草稿。",
        },
        "days": days,
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
             "- 听力日：%d 天（N4 18 篇、N3 27 篇）" % c["listening_days"],
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
