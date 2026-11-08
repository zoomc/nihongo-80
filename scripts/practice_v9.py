"""Deterministic optional practice from the existing course seeds.

The private result contains answers; callers must project it before publication.
These questions supplement, and never replace, the required v5 questions.
"""
import hashlib
import json
import random
import re
import unicodedata

from quiz_v5 import fnv


def _normal(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value)))


def _digest(*parts):
    data = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:12]


def _options(answer, candidates, seed, forbidden=()):
    """Pick reproducible distinct options, excluding known alternatives and collisions."""
    rnd = random.Random(seed)
    pool = list(candidates)
    rnd.shuffle(pool)
    result = [answer]
    seen = {_normal(answer)} | {_normal(v) for v in forbidden}
    hashes = {fnv(answer)} | {fnv(v) for v in forbidden}
    for value in pool:
        if not value:
            continue
        norm, h = _normal(value), fnv(value)
        if norm in seen or h in hashes:
            continue
        result.append(value)
        seen.add(norm)
        hashes.add(h)
        if len(result) == 4:
            rnd.shuffle(result)
            return result
    raise ValueError("not enough distinct options for %r" % answer)


def _make(day, source_day, group, capability, kid, prompt, answer, candidates,
          forbidden=(), scope="daily"):
    seed = int(_digest(day, source_day, group, capability, kid), 16)
    options = _options(answer, candidates, seed, forbidden)
    qid = "%s-%03d-%s-%s-%s" % ("U" if scope == "unit" else "P", day, kid, capability[0],
                                 _digest(prompt, options, answer, kid, source_day))
    assert len(qid) <= 48
    return {"id": qid, "qid": qid, "type": "mcq", "day": day,
            "prompt": prompt, "options": options, "answer": answer,
            "h": fnv(answer), "oh": [fnv(o) for o in options],
            "knowledge_ids": [kid], "capability": capability, "group": group,
            "source_day": source_day, "optional": True}


def _meaning_candidates(answer, records):
    # Avoid obvious synonym/partial-definition overlap; these are prompts about
    # the stored course gloss, not a claim that other translations are invalid.
    norm = _normal(answer)
    def parts(text):
        return [p for p in re.split(r"[；;/／、，,（）()\s]+", _normal(text)) if p]
    target = parts(answer)
    for value in records:
        n = _normal(value)
        if not n or n == norm or n in norm or norm in n:
            continue
        if any(a in b or b in a for a in target for b in parts(value)):
            continue
        yield value


def _vocab_questions(day, source_day, kid, vocab, scope="daily"):
    v = vocab[kid]
    surface, kana, meaning = v["surface"], v["kana"], v["meaning_zh"]
    all_vocab = sorted(vocab.values(), key=lambda x: x["id"])
    # Other entries with the same written form are known alternative readings.
    same_surface = [x["kana"] for x in all_vocab if x["surface"] == surface]
    readings = [x["kana"] for x in all_vocab if x["surface"] != surface]
    glosses = _meaning_candidates(meaning, (x["meaning_zh"] for x in all_vocab
                                             if x["surface"] != surface))
    example = next((x for x in v.get("examples", []) if x.get("zh")), {})
    context = "（例句语境：%s）" % example["zh"] if example else ""
    meaning_q = _make(day, source_day, "vocab", "meaning", kid,
                      "本课词条「%s」%s的释义是哪一项？" % (surface, context),
                      meaning, glosses, scope=scope)
    reading_q = _make(day, source_day, "vocab", "reading", kid,
                      "本课词条「%s」（%s）的假名读音是哪一项？" % (surface, meaning),
                      kana, readings, forbidden=same_surface, scope=scope)
    return [meaning_q, reading_q]


def _grammar_questions(day, source_day, kid, grammar, scope="daily"):
    g = grammar[kid]
    all_grammar = sorted(grammar.values(), key=lambda x: x["id"])
    others = [x for x in all_grammar if x["id"] != kid and x["pattern"] != g["pattern"]]
    example = next((x for x in g.get("examples", []) if x.get("ja") and x.get("zh")), {})
    context = " 例句：%s（%s）" % (example["ja"], example["zh"]) if example else ""
    meaning = _make(day, source_day, "grammar", "meaning", kid,
                    "本课句型「%s」在以下语境中的释义是哪一项？%s" % (g["pattern"], context),
                    g["meaning_zh"], _meaning_candidates(g["meaning_zh"],
                                                         (x["meaning_zh"] for x in others)), scope=scope)
    # Ask for the exact source description, not which of several potentially
    # grammatical Japanese sentences is correct.
    connection = _make(day, source_day, "grammar", "usage", kid,
                       "课程中「%s」的接续说明是哪一项？%s" % (g["pattern"], context),
                       g["connection"], (x["connection"] for x in others), scope=scope)
    return [meaning, connection]


def build_daily(day, vocab, grammar, kanji):
    """Return private optional MCQs for every core word and new grammar item."""
    number = day["day"]
    questions = []
    for kid in day.get("core_vocab_ids", day["new_vocab_ids"]):
        questions.extend(_vocab_questions(number, number, kid, vocab))
    for kid in day["new_grammar_ids"]:
        questions.extend(_grammar_questions(number, number, kid, grammar))
    return questions


def build_unit(end_day, days, vocab, grammar, kanji):
    """Return an optional five-day unit with 20 sampled private MCQs and full IDs."""
    start_day = end_day - 4
    selected = sorted((d for d in days if start_day <= d["day"] <= end_day),
                      key=lambda d: d["day"])
    if start_day < 1 or [d["day"] for d in selected] != list(range(start_day, end_day + 1)):
        raise ValueError("unit requires five consecutive days ending at end_day")
    vocab_ids = list(dict.fromkeys(kid for d in selected for kid in d["new_vocab_ids"]))
    grammar_ids = list(dict.fromkeys(kid for d in selected for kid in d["new_grammar_ids"]))
    questions = []
    # Each day contributes two vocabulary and two grammar questions; vary word
    # and capability so the sample spans five days and both knowledge types.
    for d in selected:
        words = d.get("core_vocab_ids", d["new_vocab_ids"])
        gs = d["new_grammar_ids"]
        if not words or not gs:
            raise ValueError("unit sampling requires vocabulary and grammar each day")
        source = d["day"]
        word_a = words[(source - 1) % len(words)]
        word_b = words[(source + 3) % len(words)]
        questions.append(_vocab_questions(end_day, source, word_a, vocab, scope="unit")[0])
        questions.append(_vocab_questions(end_day, source, word_b, vocab, scope="unit")[1])
        questions.append(_grammar_questions(end_day, source, gs[0], grammar, scope="unit")[0])
        questions.append(_grammar_questions(end_day, source, gs[-1], grammar, scope="unit")[1])
    return {"start_day": start_day, "end_day": end_day, "new_vocab_ids": vocab_ids,
            "new_grammar_ids": grammar_ids, "questions": questions}
