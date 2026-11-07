#!/usr/bin/env python3
"""curriculum_v5.py — 生成 150 天课程骨架（v5）。

只依赖 seeds，不依赖旧 curriculum。输出：
  curriculum/curriculum.json
  curriculum/day-001.md ... day-150.md
  curriculum/coverage_v5.md

设计要点：
- 每天 60 分钟，5 块：复习/新词/语法/听力(可选)/练习
- 听力从 Day 46 起，每 7 天 3 次（学习日 %7 ∈ {1,3,5}）
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

SCENES = [
    ("greeting", "问候与自我介绍", "第一次见面，介绍自己是谁、从哪来"),
    ("family", "家人与朋友", "说清家里有谁、做什么工作"),
    ("food", "吃饭与点单", "在店里点餐、说忌口、结账"),
    ("shopping", "购物与价格", "问价、比较、决定买哪个"),
    ("transport", "电车与问路", "问怎么走、几点到、在哪换乘"),
    ("health", "医院与身体", "说症状、从什么时候开始、拿药"),
    ("work", "打工与职场", "请假、汇报进度、接电话"),
    ("housing", "租房与邻居", "看房、问条件、和邻居打招呼"),
    ("study", "学校与学习", "选课、问作业、和同学商量"),
    ("travel", "旅行与住宿", "订房、办手续、问观光信息"),
    ("notice", "通知与手续", "读市政/公司通知，找出截止时间和要办的事"),
    ("news", "新闻与天气", "听懂大意、抓时间地点数字"),
    ("emotion", "心情与评价", "说喜欢/担心/后悔，评价事物"),
    ("request", "请求与帮助", "请人帮忙、拒绝、提条件"),
    ("plan", "计划与约定", "约时间、改计划、说明理由"),
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
    questions = read("questions.jsonl")

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
        n = 4 if d < DAYS else 8
        kby[d] = new_kanji[ki:ki + n]; ki += n
    while ki < len(new_kanji):
        kby[DAYS].append(new_kanji[ki]); ki += 1

    # 素材：按级别分池，听力日优先 listening
    pool = defaultdict(lambda: {"reading": [], "listening": []})
    for m in materials:
        lvl = m.get("level") or "N5"
        kind = m.get("kind")
        if kind in ("reading", "listening") and m.get("text_ja"):
            pool[lvl][kind].append(m["id"])
    for lvl in pool:
        for k in pool[lvl]:
            pool[lvl][k].sort()

    used_m = Counter()
    mby = {}
    for d in range(1, DAYS + 1):
        lvl = level_of_day(d)
        cand = pool.get(lvl) or pool.get("N3") or pool.get("N4")
        if not cand:
            mby[d] = []; continue
        kind = "listening" if is_listening_day(d) else "reading"
        ids = cand.get(kind) or cand.get("reading") or []
        if not ids:
            mby[d] = []
            continue
        ids = sorted(ids, key=lambda x: (used_m[x], x))
        pick = ids[0]
        used_m[pick] += 1
        mby[d] = [pick]

    # 题目：按级别分池，每天 6 题
    qpool = defaultdict(list)
    for q in questions:
        lv = q.get("jlpt") or q.get("level") or "N5"
        qpool[lv].append(q["id"])
    qby, qidx = {}, defaultdict(int)
    for d in range(1, DAYS + 1):
        lv = level_of_day(d)
        ids = qpool.get(lv) or qpool.get("N5") or []
        if not ids:
            qby[d] = []; continue
        take = [ids[(qidx[lv] + i) % len(ids)] for i in range(6)]
        qidx[lv] += 6
        qby[d] = take

    days = []
    learned_v, learned_g = [], []
    for d in range(1, DAYS + 1):
        ph, a, b = phase_of(d)
        scene_key, scene_zh, can_do_scene = SCENES[(d - 1) % len(SCENES)]
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
        can_do = "在「%s」场景里，用 %s 说清一件事" % (scene_zh, gpat) if gpat else can_do_scene
        blocks = [
            {"min": 12, "type": "复习", "desc": "FSRS 到期 ≤80 张，三档自评"},
            {"min": 14 if not listening else 8, "type": "新词", "desc": "%d 个新词 + 朝鲜语汉字词对照" % len(nv)},
            {"min": 7, "type": "语法", "desc": "、".join(g["pattern"] for g in ng) + "（含韩语对照）"},
            {"min": 8 if listening else 0, "type": "听力", "desc": "1 段 60–90 秒 + 3 题" if listening else ""},
            {"min": 6 if not listening else 4, "type": "练习", "desc": "6 题，交错混合"},
        ]
        blocks = [x for x in blocks if x["min"] > 0]
        blocks.append({"min": 60 - sum(x["min"] for x in blocks), "type": "会话", "desc": "抽词/改句子/讲错题"})
        days.append({
            "day": d, "phase": ph, "phase_name": phase_of(d)[0],
            "theme": "%s｜%s" % (scene_zh, "、".join(g["pattern"] for g in ng[:2])),
            "scene": can_do_scene, "scene_tag": scene_key, "scene_topic_key": scene_key,
            "scene_topic": scene_zh, "can_do": can_do,
            "focus": ["词汇", "语法", "输出"] if not listening else ["词汇", "听力", "输出"],
            "minutes": 60, "blocks": blocks,
            "new_vocab_ids": [v["id"] for v in nv],
            "new_grammar_ids": [g["id"] for g in ng],
            "new_kanji_ids": [k["id"] for k in nk],
            "review_knowledge_ids": rev,
            "material_ids": mby.get(d, []),
            "question_ids": qby.get(d, []),
            "listening": listening,
            "assessment": ("diagnostic" if d == 1 else "weekly" if d % 7 == 0 else
                           "stage" if d in (45, 95, 130) else "mock" if d in (110, 132, 148) else "none"),
            "objectives": [
                "认出并读出今天的 %d 个新词" % len(nv),
                "用 %s 造 2 句自己的话" % ("、".join(g["pattern"] for g in ng) or "今天语法"),
                "听懂/读懂今天的素材并答对 3 题",
            ],
            "lesson_core": [
                {"ja": e.get("ja", ""), "zh": e.get("zh", ""), "origin": "grammar_example"}
                for g in ng for e in (g.get("examples") or [])[:2]
            ][:3],
            "review_plan": [],
            "teaching_notes": [],
            "completion": "复习完成 + 新词自评 + 语法造句 2 句 + 练习 ≥4/6",
            "review_status": "generated",
        })
        learned_v += [v["id"] for v in nv]
        learned_g += [g["id"] for g in ng]

    data = {
        "meta": {
            "version": "5.0", "days": DAYS, "minutes_per_day": 60,
            "total_hours": DAYS, "listening_from": 46,
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
             "- 听力日：%d 天（Day 46 起，每周 3 次）" % c["listening_days"],
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
            md.append("- **%s**（%s）%s%s  " % (x["surface"], x["kana"], x["meaning_zh"], ko))
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
