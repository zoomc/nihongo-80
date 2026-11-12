"""Daily web practice derived from the assigned vocabulary and grammar seeds."""
from __future__ import annotations

from difflib import SequenceMatcher
from functools import lru_cache
import random
import re
import unicodedata

from quiz_v5 import fnv


@lru_cache(maxsize=8192)
def compact(text):
    return "".join(unicodedata.normalize("NFKC", text).split())


@lru_cache(maxsize=None)
def meanings(text):
    text = re.sub(r"（[^）]*）|\([^)]*\)", "", text)
    parts = re.split(r"[；;／/、，,]", compact(text))
    return {part.strip(".…") for part in parts if part.strip(".…")}


@lru_cache(maxsize=None)
def pos(label):
    return label.translate(str.maketrans("詞動連體", "词动连体")).split("/")[0].split("(")[0]


def hiragana(text):
    return "".join(chr(ord(c) - 96) if "ァ" <= c <= "ヶ" else c for c in compact(text))


def question(day, kid, kind, prompt, answer, distractors, capability):
    qid = f"D13-{day:03d}-{kid}-{kind}"
    options = [answer]
    seen = {fnv(answer)}
    for option in distractors:
        key = fnv(option)
        if option and key not in seen and compact(option) not in compact(prompt):
            options.append(option)
            seen.add(key)
        if len(options) == 4:
            break
    if len(options) != 4 or not answer or compact(answer) in compact(prompt):
        raise ValueError(f"{qid}: unusable options for {prompt!r} ({options!r})")
    random.Random(qid).shuffle(options)
    return {
        "id": qid, "qid": qid, "type": "mcq", "day": day, "prompt": prompt,
        "options": options, "h": fnv(answer), "oh": [fnv(o) for o in options],
        "knowledge_ids": [kid], "capability": capability,
        "group": "vocab" if kid.startswith("V") else "grammar",
    }


def vocabulary_display(word):
    """Keep legacy quiz glosses intact while separating translations and readings."""
    meaning, kana = word["meaning_zh"], word["kana"]
    readings = [kana]
    note = re.search(r"（([ぁ-ゖァ-ヶー]+(?:／[ぁ-ゖァ-ヶー]+)+)）$", meaning)
    if note and kana in note[1].split("／"):
        readings.extend(k for k in note[1].split("／") if k != kana)
        meaning = meaning[:note.start()]
    # A usage note may include a Japanese example before the Chinese explanation.
    meaning = re.sub(r"（[^（）]*[ぁ-ゖァ-ヶ][^（）]*＝", "（后缀用法：", meaning)
    return meaning, readings


def vocabulary_questions(day, word, words, today):
    kid = word["id"]
    surface, kana = word["surface"], word["kana"]
    meaning, _ = vocabulary_display(word)
    glosses = meanings(meaning)
    # Avoid alternate senses of the same spelling and explicit synonyms in the glosses.
    pool = [w for w in words if w["id"] != kid and w["surface"] != surface
            and not (glosses & meanings(w["meaning_zh"]))]
    random.Random(kid).shuffle(pool)
    pool.sort(key=lambda w: (w["id"] in today, pos(w["pos"]) == pos(word["pos"]),
                             w["jlpt"] == word["jlpt"]), reverse=True)
    cue = kana if compact(meaning) in compact(surface) else surface
    yield question(day, kid, "meaning", f"「{cue}」的中文释义？", meaning,
                   (vocabulary_display(w)[0] for w in pool if hiragana(w["kana"]) != hiragana(cue)), "meaning")

    other_readings = {hiragana(k) for w in words if w["surface"] == surface
                      for k in vocabulary_display(w)[1]}
    clean_gloss = re.sub(r"（[^）]*）|\([^)]*\)", "", meaning).strip() or meaning
    # Kana-only words get a recall question instead of copying the reading from the stem.
    if hiragana(surface) == hiragana(kana) or compact(surface) in compact(meaning):
        yield question(day, kid, "recall", f"「{clean_gloss}」对应哪个日语词？", kana,
                       (w["kana"] for w in pool if hiragana(w["kana"]) not in other_readings), "meaning")
    else:
        other_readings.update(hiragana(s) for s in re.findall(r"[ぁ-ゖァ-ヶー]+", meaning))
        readings = [w for w in pool if hiragana(w["kana"]) not in other_readings]
        readings.sort(key=lambda w: (w["kana"][:1] == kana[:1],
                                     abs(len(w["kana"]) - len(kana)) <= 1), reverse=True)
        gloss = f"（{clean_gloss}）" if compact(kana) not in compact(clean_gloss) else ""
        yield question(day, kid, "reading", f"「{surface}」{gloss}的假名读音是哪一项？", kana,
                       (w["kana"] for w in readings), "reading")


# Contrast the forms taught at the start, using the same vocabulary across options.
INTRO = {
    "G0001": ("「这是书。」选出礼貌体句末。\nこれは本（　）。", "です",
              ["でした", "ではありません", "ではありませんでした"],
              "これは本です。", ["这不是书。", "这是书吗？", "那曾经是书。"]),
    "G0002": ("「我不是学生。」选出礼貌体句末。\n私は学生（　）。", "ではありません",
              ["です", "でした", "ではありませんでした"],
              "私は先生ではありません。", ["我是老师。", "我以前是老师。", "我以前不是老师。"]),
    "G0003": ("「昨天是周日。」选出礼貌体句末。\n昨日は日曜日（　）。", "でした",
              ["です", "ではありません", "ではありませんでした"],
              "先週は休みでした。", ["上周休息。", "上周没有休息。", "这周休息。", "下周休息。"]),
    "G0261": ("「坐公交车或出租车去车站。」选出连接两个备选项的助词。\n駅までバス（　）タクシーで行きます。",
              "か", ["と", "も", "の"], "土曜日か日曜日に買い物に行きます。",
              ["我星期六和星期天都去买东西。", "我星期六以前去买东西。", "我只在星期天去买东西。"]),
}
INTRO_TRANSLATIONS = {
    "G0001": "这是书。", "G0002": "我不是老师。", "G0003": "上周休息。",
    "G0261": "我星期六或星期天去买东西。",
}


def grammar_forms(pattern):
    pattern = re.sub(r"（[^）]*）|\([^)]*\)", "", pattern)
    return set(re.findall(r"[ぁ-ゖァ-ヶ]{2,}", compact(pattern)))


def grammar_questions(day, item, grammar):
    kid = item["id"]
    pattern, meaning = item["pattern"], item["meaning_zh"]
    examples = item["examples"]
    peers = [g for g in grammar if g["id"] != kid and g["pattern"] != pattern]
    random.Random(kid).shuffle(peers)
    tags = set(item["tags"])
    peers.sort(key=lambda g: (g["jlpt"] == item["jlpt"], len(tags & set(g["tags"]))), reverse=True)
    cue = pattern if compact(meaning) not in compact(pattern) else examples[0]["ja"]
    forms = grammar_forms(pattern)
    glosses = meanings(meaning)
    contrasts = (g["meaning_zh"] for g in peers
                 if not glosses & meanings(g["meaning_zh"]) and not forms & grammar_forms(g["pattern"]))
    yield question(day, kid, "meaning", f"请选择「{cue}」所用句型的主要含义。", meaning,
                   contrasts, "meaning")

    if kid in INTRO:
        prompt, answer, distractors, sentence, translations = INTRO[kid]
        yield question(day, kid, "form", prompt, answer, distractors, "usage")
        yield question(day, kid, "context", f"请选择「{sentence}」的中文意思。", INTRO_TRANSLATIONS[kid],
                       [t for t in translations if t != INTRO_TRANSLATIONS[kid]], "usage")
        return

    example = examples[-1]
    # Keep translations and Japanese examples separate. Use nearby grammar as
    # distractors, excluding entries that share the target's explicit examples.
    own_examples = {compact(e["ja"]) for e in examples}
    other_examples = [e for g in peers if not own_examples & {compact(e["ja"]) for e in g["examples"]}
                      for e in g["examples"]]
    def nearby_examples(example):
        # Favor lexical overlap so a familiar noun alone is less useful as a clue.
        text = compact(example["zh"])
        pairs = {text[i:i + 2] for i in range(len(text) - 1)}
        ranked = sorted(other_examples, key=lambda e: sum(pair in e["zh"] for pair in pairs), reverse=True)
        for candidate in ranked:
            if all(SequenceMatcher(None, compact(example[k]), compact(candidate[k])).ratio() < .75
                   for k in ("ja", "zh")):
                yield candidate

    yield question(day, kid, "context", f"请选择「{example['ja']}」的中文意思。", example["zh"],
                   (e["zh"] for e in nearby_examples(example)), "usage")
    example = examples[0]
    yield question(day, kid, "form", f"选出符合下列意思的日语句子。\n{example['zh']}", example["ja"],
                   (e["ja"] for e in nearby_examples(example) if compact(e["zh"]) != compact(example["zh"])), "usage")


def build_daily_questions(day, vocab, grammar):
    number = day["day"]
    core, extra = [], []
    optional = set(day["extension_vocab_ids"])
    today = set(day["new_vocab_ids"])
    for kid in day["new_vocab_ids"]:
        bucket = extra if kid in optional else core
        bucket.extend(vocabulary_questions(number, vocab[kid], vocab.values(), today))
    for kid in day["new_grammar_ids"]:
        core.extend(grammar_questions(number, grammar[kid], grammar.values()))
    rng = random.Random(f"daily-v13-{number}")
    for bucket in (core, extra):
        rng.shuffle(bucket)
    return core + extra
