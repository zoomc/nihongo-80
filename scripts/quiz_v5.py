"""Shared deterministic v5 questions; private records never serialized to web."""
import json

def fnv(text):
    """与前端一致的 FNV-1a（按 Unicode 码点），用于避免把答案明文写进 HTML。"""
    h = 2166136261
    import re as _re
    import unicodedata as _ud
    for ch in _re.sub(r"\s+", "", _ud.normalize("NFKC", str(text))):
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return format(h, "x")


def build_quiz(day, vocab, grammar, kanji, rnd):
    """按当天新词/汉字/语法出 6 题，保证与课程对齐；答案只存哈希。"""
    import random as _r
    qs = []
    vids = list(day["new_vocab_ids"])
    kids = list(day["new_kanji_ids"])
    gids = list(day["new_grammar_ids"])
    pool = [v for k, v in vocab.items() if v.get("meaning_zh")]

    def add(prompt, options, answer, rationale, qid, kids):
        opts = list(dict.fromkeys([o for o in options if o]))
        if answer not in opts:
            opts.insert(0, answer)
        opts = opts[:4]
        rnd.shuffle(opts)
        import hashlib
        digest = hashlib.sha256(json.dumps([prompt, opts, answer, kids], ensure_ascii=False).encode()).hexdigest()[:12]
        qid += "-" + digest
        qs.append({"qid": qid, "id": qid, "type": "mcq", "answer": answer,
                   "knowledge_ids": kids, "prompt": prompt, "options": opts,
                   "h": fnv(answer), "oh": [fnv(o) for o in opts],
                   "rationale": rationale})

    for vid in vids[:3]:
        v = vocab[vid]
        distract = [x["meaning_zh"] for x in rnd.sample(
            [x for x in pool if x["id"] != vid and x.get("jlpt") == v.get("jlpt")], 3)] if len(pool) > 4 else []
        add("「%s」是什么意思？" % v["surface"], [v["meaning_zh"]] + distract, v["meaning_zh"],
            "%s（%s）＝%s" % (v["surface"], v["kana"], v["meaning_zh"]), "Q-%03d-V%d" % (day["day"], len(qs)), [vid])
    for kid in kids[:1]:
        k = kanji[kid]
        correct = (k.get("onyomi") or k.get("kunyomi") or [""])[0]
        if not correct:
            continue
        others = []
        for x in rnd.sample([y for y in kanji.values() if y.get("onyomi") or y.get("kunyomi")], 8):
            r = (x.get("onyomi") or x.get("kunyomi") or [""])[0]
            if r and r not in (k.get("onyomi", []) + k.get("kunyomi", [])):
                others.append(r)
        add("汉字「%s」的一个常用读音是？" % k["char"], [correct] + others[:3], correct,
            "%s：音 %s｜训 %s" % (k["char"], "、".join(k.get("onyomi") or []) or "无",
                                 "、".join(k.get("kunyomi") or []) or "无"),
            "Q-%03d-K" % day["day"], [kid])
    for gid in gids[:1]:
        g = grammar[gid]
        others = [x["meaning_zh"] for x in rnd.sample(
            [y for y in grammar.values() if y.get("meaning_zh") and y["id"] != gid], 3)]
        add("句型「%s」的意思是？" % g["pattern"], [g["meaning_zh"]] + others, g["meaning_zh"],
            "%s＝%s" % (g["pattern"], g["meaning_zh"]), "Q-%03d-G" % day["day"], [gid])
    # 先用当天其余新词补足 6 题
    for vid in vids[3:]:
        if len(qs) >= 6:
            break
        v = vocab[vid]
        distract = [x["meaning_zh"] for x in rnd.sample([x for x in pool if x["id"] != vid], 3)]
        add("「%s」是什么意思？" % v["surface"], [v["meaning_zh"]] + distract,
            v["meaning_zh"], "%s（%s）＝%s" % (v["surface"], v["kana"], v["meaning_zh"]),
            "Q-%03d-V%d" % (day["day"], len(qs)), [vid])
    # 再用复习词补足
    for vid in (day.get("review_knowledge_ids") or []):
        if len(qs) >= 6:
            break
        v = vocab.get(vid)
        if not v or not v.get("meaning_zh"):
            continue
        distract = [x["meaning_zh"] for x in rnd.sample(
            [x for x in pool if x["id"] != vid], 3)]
        add("复习：「%s」是什么意思？" % v["surface"], [v["meaning_zh"]] + distract,
            v["meaning_zh"], "%s＝%s" % (v["surface"], v["meaning_zh"]), "Q-%03d-R%d" % (day["day"], len(qs)), [vid])
    return qs[:6]



def listening_quiz(day, material):
    import hashlib
    import random
    out = []
    for i, item in enumerate(material.get("questions", [])):
        q = dict(item)
        q["type"] = "mcq"
        q["knowledge_ids"] = []  # 理解题是练习证据，不推断不相关知识卡已掌握
        digest = hashlib.sha256(json.dumps([material["text_ja"], item], ensure_ascii=False).encode()).hexdigest()[:12]
        q["qid"] = q["id"] = "L-%03d-%d-%s" % (day["day"], i, digest)
        q["options"] = list(q["options"])
        random.Random(day["day"] * 10 + i).shuffle(q["options"])
        q["h"] = fnv(q["answer"])
        q["oh"] = [fnv(o) for o in q["options"]]
        out.append(q)
    return out


def public_question(q):
    return {k: q[k] for k in ("qid", "prompt", "options", "h", "oh")}


def day_questions(day, vocab, grammar, kanji, materials):
    import random
    qs = build_quiz(day, vocab, grammar, kanji, random.Random(20261107 + day["day"]))
    if day.get("listening"):
        qs += listening_quiz(day, materials[day["material_ids"][0]])
    return qs
