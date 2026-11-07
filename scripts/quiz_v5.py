"""Shared deterministic v7 questions; private records never serialized to web.

出题契约（v7 修复）：
- 每题恰好 4 个选项，答案在选项内，4 个选项的 FNV 哈希互异；
- 干扰项排除与正确答案相同的中文释义，避免「双答案」或选项变少；
- 词形与中文释义完全相同时改用假名出题，避免答案写在题干里；
- 题目顺序为「汉字→语法→词汇→复现」，阶段测替换尾部题时仍保留当天汉字/语法题；
- 语法按天轮换，复现题在词汇/语法/汉字之间轮换，提升抽样覆盖。
"""
import hashlib
import json


def fnv(text):
    """与前端一致的 FNV-1a（按 Unicode 码点），用于避免把答案明文写进 HTML。"""
    import re as _re
    import unicodedata as _ud
    h = 2166136261
    for ch in _re.sub(r"\s+", "", _ud.normalize("NFKC", str(text))):
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return format(h, "x")


def _digest(*parts):
    return hashlib.sha256(json.dumps(list(parts), ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()[:12]


def _pick(values, answer, rnd, count=3):
    """取 count 个互异、且不等于答案的干扰项。"""
    vals = [v for v in values if v and v != answer]
    rnd.shuffle(vals)
    out = []
    for v in vals:
        if v not in out:
            out.append(v)
        if len(out) >= count:
            break
    return out


def build_quiz(day, vocab, grammar, kanji, rnd):
    """按当天新词/汉字/语法出 6 题；答案只存哈希，公开投影再剥离。"""
    qs = []
    vids = list(day.get("core_vocab_ids") or day["new_vocab_ids"])
    kids = list(day["new_kanji_ids"])
    gids = list(day["new_grammar_ids"])
    d = day["day"]

    vpool = [v for v in vocab.values() if v.get("meaning_zh")]
    gpool = [g for g in grammar.values() if g.get("meaning_zh")]
    kpool = [k for k in kanji.values() if (k.get("onyomi") or k.get("kunyomi"))]
    readings = sorted({r for k in kpool
                       for r in (k.get("onyomi") or []) + (k.get("kunyomi") or [])})
    meanings = [v["meaning_zh"] for v in vpool]
    gmeanings = [g["meaning_zh"] for g in gpool]

    def add(prompt, options, answer, rationale, tag, knowledge_ids, fill=None):
        opts = list(dict.fromkeys([o for o in options if o]))
        if answer not in opts:
            opts.insert(0, answer)
        # 不足 4 项时用同类候选补齐（v6 的汉字题曾出现 3 选项）
        for extra in (fill or []):
            if len(opts) >= 4:
                break
            if extra and extra not in opts:
                opts.append(extra)
        opts = opts[:4]
        assert len(opts) == 4, "选项不足 4：%s %s" % (tag, opts)
        assert answer in opts, "答案不在选项：%s" % tag
        assert len({fnv(o) for o in opts}) == len(opts), "归一化后选项重复：%s" % tag
        rnd.shuffle(opts)
        qid = "Q-%03d-%s-%s" % (d, tag, _digest(prompt, opts, answer, knowledge_ids))
        qs.append({"qid": qid, "id": qid, "type": "mcq", "answer": answer,
                   "knowledge_ids": knowledge_ids, "prompt": prompt, "options": opts,
                   "h": fnv(answer), "oh": [fnv(o) for o in opts],
                   "rationale": rationale})

    # ① 汉字读音 2 题：干扰项从全局读音池取，排除该字所有合法读音
    for i, kid in enumerate(kids[:2]):
        k = kanji[kid]
        correct = (k.get("onyomi") or k.get("kunyomi") or [""])[0]
        if not correct:
            continue
        banned = set((k.get("onyomi") or []) + (k.get("kunyomi") or []))
        fill = [r for r in readings if r not in banned and r != correct]
        others = _pick(fill, correct, rnd, 3)
        add("汉字「%s」的一个常用读音是？" % k["char"], [correct] + others, correct,
            "%s：音 %s｜训 %s" % (k["char"], "、".join(k.get("onyomi") or []) or "无",
                                 "、".join(k.get("kunyomi") or []) or "无"),
            "K%d" % i, [kid], fill=fill)

    # ② 语法释义 1 题：按天轮换当天新语法，避免永远只考第 1 条
    if gids:
        gid = gids[d % len(gids)]
        g = grammar[gid]
        others = _pick([x["meaning_zh"] for x in gpool
                        if x["id"] != gid and x["meaning_zh"] != g["meaning_zh"]],
                       g["meaning_zh"], rnd, 3)
        add("句型「%s」的意思是？" % g["pattern"], [g["meaning_zh"]] + others,
            g["meaning_zh"], "%s＝%s" % (g["pattern"], g["meaning_zh"]), "G", [gid],
            fill=[x for x in gmeanings if x != g["meaning_zh"]])

    # ③ 词汇释义 2 题：中日同形词改用假名出题
    def spoiler(v):
        """中文释义里直接出现词形（如「四」→「四（し／よん）」），看题干就能猜答案。"""
        surf, mean = v["surface"], v["meaning_zh"]
        if not surf:
            return False
        return mean == surf or mean.startswith(surf) or (
            surf in mean and all("\u4e00" <= c <= "\u9fff" for c in surf))

    surfaces = [v["surface"] for v in vpool]

    def vocab_question(vid, tag, prefix=""):
        v = vocab[vid]
        if spoiler(v):
            # 改成「假名 → 词形」，选项全是日文词形，必须真的会读才能选
            others = _pick([x["surface"] for x in vpool if x["id"] != vid],
                           v["surface"], rnd, 3)
            add(prefix + "假名「%s」对应的词形是？" % v["kana"],
                [v["surface"]] + others, v["surface"],
                "%s＝%s" % (v["kana"], v["surface"]), tag, [vid],
                fill=[x for x in surfaces if x != v["surface"]])
            return
        others = _pick([x["meaning_zh"] for x in vpool
                        if x["id"] != vid and x["meaning_zh"] != v["meaning_zh"]],
                       v["meaning_zh"], rnd, 3)
        add(prefix + "「%s」是什么意思？" % v["surface"], [v["meaning_zh"]] + others,
            v["meaning_zh"], "%s（%s）＝%s" % (v["surface"], v["kana"], v["meaning_zh"]),
            tag, [vid], fill=[x for x in meanings if x != v["meaning_zh"]])

    for i, vid in enumerate(vids[:2]):
        vocab_question(vid, "V%d" % i)

    # ④ 复现题 1 道：在词汇/语法/汉字之间按天轮换，覆盖静态复习快照里的三类知识
    rev = list(day.get("review_knowledge_ids") or [])
    want = ("V", "G", "K")[d % 3]
    picked = next((x for x in rev if x.startswith(want)), None) or next(
        (x for x in rev if x.startswith(("V", "G", "K"))), None)
    if picked and picked.startswith("V") and picked in vocab:
        vocab_question(picked, "R", prefix="复习：")
    elif picked and picked.startswith("G") and picked in grammar:
        g = grammar[picked]
        others = _pick([x["meaning_zh"] for x in gpool
                        if x["id"] != picked and x["meaning_zh"] != g["meaning_zh"]],
                       g["meaning_zh"], rnd, 3)
        add("复习：句型「%s」的意思是？" % g["pattern"], [g["meaning_zh"]] + others,
            g["meaning_zh"], "%s＝%s" % (g["pattern"], g["meaning_zh"]), "R", [picked],
            fill=[x for x in gmeanings if x != g["meaning_zh"]])
    elif picked and picked.startswith("K") and picked in kanji:
        k = kanji[picked]
        correct = (k.get("onyomi") or k.get("kunyomi") or [""])[0]
        if correct:
            banned = set((k.get("onyomi") or []) + (k.get("kunyomi") or []))
            fill = [r for r in readings if r not in banned and r != correct]
            add("复习：汉字「%s」的读音是？" % k["char"],
                [correct] + _pick(fill, correct, rnd, 3), correct,
                "%s：音 %s｜训 %s" % (k["char"], "、".join(k.get("onyomi") or []) or "无",
                                     "、".join(k.get("kunyomi") or []) or "无"),
                "R", [picked], fill=fill)

    # ⑤ 不足 6 题时按新词顺序补足
    for vid in vids[2:]:
        if len(qs) >= 6:
            break
        vocab_question(vid, "V%d" % len(qs))
    return qs[:6]


def listening_quiz(day, material):
    import random
    out = []
    for i, item in enumerate(material.get("questions", [])):
        q = dict(item)
        q["type"] = "mcq"
        q["knowledge_ids"] = []  # 理解题是练习证据，不推断不相关知识卡已掌握
        assert len(q["options"]) == 4 and q["answer"] in q["options"], \
            "听力题必须 4 选项：%s" % material["id"]
        digest = _digest(material["text_ja"], item)
        q["qid"] = q["id"] = "L-%03d-%d-%s" % (day["day"], i, digest)
        q["options"] = list(q["options"])
        random.Random(day["day"] * 10 + i).shuffle(q["options"])
        q["h"] = fnv(q["answer"])
        q["oh"] = [fnv(o) for o in q["options"]]
        assert q["h"] in q["oh"]
        out.append(q)
    return out


def public_question(q):
    return {k: q[k] for k in ("qid", "prompt", "options", "h", "oh", "passage") if k in q}


def day_questions(day, vocab, grammar, kanji, materials):
    import random
    qs = build_quiz(day, vocab, grammar, kanji, random.Random(20261108 + day["day"]))
    from assessment_v6 import build_for_day
    assessment = build_for_day(day)
    if assessment:
        # 题目顺序为 K/K/G/V/V/R，截掉尾部后仍保留当天汉字与语法题
        qs = qs[:6 - len(assessment)] + assessment
    if day["day"] == 1:
        diagnostics = [
            ("假名诊断：「きゃ」的读法是？", ["kya", "kiya", "sha", "cha"], "kya"),
            ("假名诊断：「ざ」的读法是？", ["za", "sa", "da", "ta"], "za"),
            ("助词诊断：「私は学生です」中的「は」读作？", ["wa", "ha", "ga", "o"], "wa")]
        # 替换尾部 3 题，保留 2 汉字 + 1 语法
        for i, (prompt, options, answer) in enumerate(diagnostics):
            qid = "D-001-%d-%s" % (i, _digest(prompt, options, answer))
            item = {"id": qid, "qid": qid, "type": "mcq", "prompt": prompt,
                    "options": options, "answer": answer, "knowledge_ids": [],
                    "h": fnv(answer), "oh": [fnv(o) for o in options]}
            if 3 + i < len(qs):
                qs[3 + i] = item
            else:
                qs.append(item)
    if day.get("listening"):
        qs += listening_quiz(day, materials[day["material_ids"][0]])

    # 全量不变量：任何一天的题都必须满足，防止回归
    ids = set()
    for q in qs:
        assert q["qid"] not in ids, "重复题号 %s" % q["qid"]
        ids.add(q["qid"])
        assert len(q["options"]) == 4, "选项数不是 4：%s" % q["qid"]
        assert q["answer"] in q["options"], "答案不在选项：%s" % q["qid"]
        assert q["h"] in q["oh"], "哈希与选项不一致：%s" % q["qid"]
        assert len({fnv(o) for o in q["options"]}) == 4, "选项归一化重复：%s" % q["qid"]
    return qs
