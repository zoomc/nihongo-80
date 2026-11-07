#!/usr/bin/env python3
"""prep_v5.py — 从 OpenJLPT（CC-BY-SA-4.0）生成 v5 待翻译骨架与分批切片。

只做「选词/去重/编号/字段映射」，不写中文释义；中文由后续批次补齐。
输出到 data/build/，不进 seeds，避免半成品污染知识库。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/build/openjlpt"
OUT = ROOT / "data/build"
SEED = ROOT / "knowledge/seeds"

TARGET_VOCAB = 2700
TARGET_GRAMMAR_NEW = 180
TARGET_KANJI_TOTAL = 620

POS_ZH = {
    "n": "名词", "pn": "代名词", "adj-i": "い形容词", "adj-na": "な形容词",
    "adj-no": "连体词", "adv": "副词", "prt": "助词", "conj": "接续词",
    "int": "感叹词", "num": "数词", "ctr": "量词", "pref": "前缀", "suf": "后缀",
    "v1": "动词(一段)", "v5u": "动词(五段)", "v5k": "动词(五段)", "v5s": "动词(五段)",
    "v5t": "动词(五段)", "v5n": "动词(五段)", "v5b": "动词(五段)", "v5m": "动词(五段)",
    "v5r": "动词(五段)", "v5g": "动词(五段)", "v5z": "动词(五段)", "v5aru": "动词(五段)",
    "vs": "动词(サ变)", "vk": "动词(カ变)", "vi": "自动词", "vt": "他动词",
    "exp": "惯用表达", "aux": "助动词",
}


def load(name):
    return json.loads((SRC / name).read_text(encoding="utf-8"))


def read_jsonl(p):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def norm_key(word, reading):
    w = re.sub(r"\s+", "", str(word or ""))
    r = re.sub(r"\s+", "", str(reading or ""))
    return (w, r)


def pos_zh(codes):
    out = []
    for c in codes or []:
        z = POS_ZH.get(c)
        if z and z not in out:
            out.append(z)
    return "/".join(out) or "词"


def pick_example(examples):
    for e in examples or []:
        ja = (e.get("ja") or "").strip()
        if ja and len(ja) <= 60:
            return ja, (e.get("en") or "").strip()
    for e in examples or []:
        if e.get("ja"):
            return e["ja"].strip(), (e.get("en") or "").strip()
    return "", ""


def build_vocab():
    existing = read_jsonl(SEED / "vocabulary.jsonl")
    seen = {norm_key(v.get("surface"), v.get("kana")) for v in existing}
    seen_words = {re.sub(r"\s+", "", str(v.get("surface") or "")) for v in existing}
    rows = []
    for lvl_file in ("n5", "n4", "n3"):
        for e in load("vocab-%s.json" % lvl_file):
            w, r = e.get("word"), e.get("reading")
            if not w or not r:
                continue
            k = norm_key(w, r)
            if k in seen or (w not in seen_words and w in seen_words):
                continue
            # 同一个词形不同读音（如 空 そら/から）保留，但完全同形同音只留一个
            seen.add(k)
            ja, en = pick_example(e.get("examples"))
            rows.append({
                "word": w,
                "reading": r,
                "romaji": e.get("romaji") or "",
                "pos_en": e.get("pos") or [],
                "pos_zh": pos_zh(e.get("pos")),
                "level": e.get("level") or lvl_file.upper(),
                "en_meanings": e.get("meanings") or [],
                "example_ja": ja,
                "example_en": en,
                "jmdict_id": e.get("jmdict_id"),
                "source": "OpenJLPT",
                "license": "CC-BY-SA-4.0",
            })
    # 只取到目标总数（现有 + 新增）
    keep = max(0, TARGET_VOCAB - len(existing))
    rows = rows[:keep]
    for i, r in enumerate(rows, start=len(existing) + 1):
        r["id"] = "V%04d" % i
    (OUT / "vocab_src.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return existing, rows


def slice_rows(rows, n, prefix):
    size = (len(rows) + n - 1) // n
    paths = []
    for i in range(n):
        part = rows[i * size:(i + 1) * size]
        if not part:
            continue
        p = OUT / ("%s_slice_%02d.json" % (prefix, i + 1))
        p.write_text(json.dumps(part, ensure_ascii=False, indent=1), encoding="utf-8")
        paths.append(p)
    return paths


def build_grammar():
    existing = read_jsonl(SEED / "grammar.jsonl")

    def norm_pattern(p):
        s = re.sub(r"[〜～\s（）()]", "", str(p or ""))
        s = s.replace("Ｖ", "V").replace("Ｎ", "N")
        return s

    covered = {norm_pattern(g.get("pattern")) for g in existing}
    rows = []
    for lvl_file in ("n5", "n4", "n3"):
        for e in load("grammar-%s.json" % lvl_file):
            p = e.get("pattern") or ""
            if not p or norm_pattern(p) in covered:
                continue
            covered.add(norm_pattern(p))
            ex = []
            for x in (e.get("examples") or [])[:3]:
                if x.get("ja"):
                    ex.append({"ja": x["ja"].strip(), "en": (x.get("en") or "").strip()})
            rows.append({
                "pattern": p,
                "level": e.get("level") or lvl_file.upper(),
                "en_meaning": e.get("meaning") or "",
                "en_formation": e.get("formation") or "",
                "examples": ex,
                "tags": e.get("tags") or [],
                "notes_en": e.get("notes") or "",
                "source": "OpenJLPT",
                "license": "CC-BY-SA-4.0",
            })
    rows = rows[:TARGET_GRAMMAR_NEW]
    for i, r in enumerate(rows, start=len(existing) + 1):
        r["id"] = "G%04d" % i
    (OUT / "grammar_src.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return existing, rows


def build_kanji():
    existing = read_jsonl(SEED / "kanji.jsonl")
    have = {k.get("char") for k in existing}
    rows = []
    for lvl_file in ("n5", "n4", "n3"):
        for e in load("kanji-%s.json" % lvl_file):
            c = e.get("character")
            if not c or c in have:
                continue
            have.add(c)
            rows.append({
                "char": c,
                "level": e.get("level") or lvl_file.upper(),
                "onyomi": e.get("onyomi") or [],
                "kunyomi": e.get("kunyomi") or [],
                "en_meanings": e.get("meanings") or [],
                "strokes": e.get("strokes"),
                "radical": e.get("radical"),
                "words": e.get("words") or [],
                "source": "OpenJLPT",
                "license": "CC-BY-SA-4.0",
            })
    keep = max(0, TARGET_KANJI_TOTAL - len(existing))
    rows = rows[:keep]
    for i, r in enumerate(rows, start=len(existing) + 1):
        r["id"] = "K%04d" % i
    (OUT / "kanji_src.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return existing, rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ev, v = build_vocab()
    eg, g = build_grammar()
    ek, k = build_kanji()
    vp = slice_rows(v, 8, "vocab")
    gp = slice_rows(g, 2, "grammar")
    kp = slice_rows(k, 2, "kanji")
    print(json.dumps({
        "vocab_existing": len(ev), "vocab_new": len(v), "vocab_total": len(ev) + len(v),
        "grammar_existing": len(eg), "grammar_new": len(g), "grammar_total": len(eg) + len(g),
        "kanji_existing": len(ek), "kanji_new": len(k), "kanji_total": len(ek) + len(k),
        "vocab_slices": [p.name for p in vp],
        "grammar_slices": [p.name for p in gp],
        "kanji_slices": [p.name for p in kp],
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
