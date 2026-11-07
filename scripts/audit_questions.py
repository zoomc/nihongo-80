#!/usr/bin/env python3
"""audit_questions.py — 题目目标/语境分离（REVISION_CONTRACT §1）。

按 §1.1 的确定性规则，为 knowledge/seeds/questions.jsonl 每题生成：
  target_knowledge_ids / context_knowledge_ids / targets

规则优先级（全部可复现，不含随机、不含模型）：
  R1 答案与某语法例句完全相等                  → 该语法 usage
  R2 答案等于某词 surface 或 kana              → 该词 usage / listening / meaning / reading
  R3 答案等于某汉字的音读/训读，且题面问读音   → 该汉字 reading
  R4 答案出现在某语法 pattern 中               → 该语法 usage
  R5 答案（≥3 字符）出现在某语法例句中         → 该语法 usage
  R6 free_production/dialogue/translate        → 第一个语法 production
  R7 无命中                                    → knowledge_ids[0]，报告标 fallback

写入保持 JSONL 一行一条、ensure_ascii=False、字段顺序稳定：
原字段顺序不变，三个新字段紧跟 knowledge_ids 之后。

用法：
  python3 scripts/audit_questions.py            # 回写种子 + 报告
  python3 scripts/audit_questions.py --check    # 只检查，不写文件
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "knowledge" / "seeds"
REPORT = ROOT / "reports" / "question_targets.md"
CAPABILITIES = ("meaning", "reading", "listening", "usage", "production")
OPEN_TYPES = {"free_production", "dialogue", "translate"}
NEW_FIELDS = ("target_knowledge_ids", "context_knowledge_ids", "targets")

READING_HINTS = ("读音", "读法", "怎么读", "发音", "假名")
MEANING_HINTS = ("中文", "意思", "含义", "释义")


def norm(s) -> str:
    """与 learning.norm_answer / web/app.js norm 同构。"""
    s = unicodedata.normalize("NFKC", str(s or ""))
    s = "".join(s.split())
    s = s.rstrip("。．.！!？?")
    return s.replace("，", ",")


def kata_to_hira(s: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def read_jsonl(path: Path) -> list[dict]:
    out = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError("JSONL 解析失败 %s:%d %s" % (path, n, e)) from e
    return out


class Index:
    def __init__(self) -> None:
        self.grammar = {g["id"]: g for g in read_jsonl(SEED_DIR / "grammar.jsonl")}
        self.vocab = {v["id"]: v for v in read_jsonl(SEED_DIR / "vocabulary.jsonl")}
        self.kanji = {k["id"]: k for k in read_jsonl(SEED_DIR / "kanji.jsonl")}


def asks_reading(q: dict) -> bool:
    text = str(q.get("prompt_zh") or "") + str(q.get("prompt_ja") or "")
    return any(h in text for h in READING_HINTS)


def asks_meaning(q: dict) -> bool:
    text = str(q.get("prompt_zh") or "")
    return any(h in text for h in MEANING_HINTS)


def vocab_capability(q: dict) -> str:
    if q.get("type") == "listen":
        return "listening"
    if asks_meaning(q):
        return "meaning"
    if asks_reading(q):
        return "reading"
    return "usage"


def fallback_capability(q: dict) -> str:
    t = q.get("type")
    if t in OPEN_TYPES:
        return "production"
    if t == "listen":
        return "listening"
    if t == "read":
        # 読解题检验的是篇章理解，归 reading；不再误记为 meaning。
        return "reading"
    if asks_reading(q):
        return "reading"
    if asks_meaning(q):
        return "meaning"
    return "usage"


def choose_target(q: dict, idx: Index) -> dict:
    """返回 {kid, capability, reason, fallback}。"""
    answer = norm(q.get("answer"))
    ids = list(q.get("knowledge_ids") or [])
    if not ids:
        raise ValueError("题目 %s 没有 knowledge_ids" % q.get("id"))
    if q.get("type") in OPEN_TYPES:
        for kid in ids:
            if kid.startswith("G"):
                return {"kid": kid, "capability": "production",
                        "reason": "R6 type=production → 首个语法", "fallback": False}
    cands = []
    for order, kid in enumerate(ids):
        if not answer:
            continue
        if kid.startswith("G"):
            g = idx.grammar.get(kid) or {}
            examples = [norm(e.get("ja")) for e in g.get("examples") or []]
            pattern = norm(g.get("pattern"))
            if answer in examples:
                cands.append((1000, -order, kid, "usage",
                              "R1 答案与例句完全一致"))
            elif pattern and answer in pattern:
                cands.append((200 + len(answer), -order, kid, "usage",
                              "R4 答案命中 pattern"))
            elif len(answer) >= 3 and any(answer in e for e in examples):
                cands.append((400 + len(answer), -order, kid, "usage",
                              "R5 答案命中例句片段"))
        elif kid.startswith("V"):
            v = idx.vocab.get(kid) or {}
            surface, kana = norm(v.get("surface")), norm(v.get("kana"))
            if answer and answer in (surface, kana):
                which = "surface" if answer == surface else "kana"
                cands.append((900, -order, kid, vocab_capability(q),
                              "R2 答案等于词 %s" % which))
        elif kid.startswith("K"):
            if not asks_reading(q):
                continue
            k = idx.kanji.get(kid) or {}
            readings = [norm(x) for x in (k.get("onyomi") or []) + (k.get("kunyomi") or [])]
            flat = [kata_to_hira(x) for x in readings]
            if answer in readings or kata_to_hira(answer) in flat:
                cands.append((800, -order, kid, "reading",
                              "R3 答案等于汉字音读/训读"))
    if cands:
        score, _order, kid, cap, reason = max(cands)
        return {"kid": kid, "capability": cap, "reason": reason, "fallback": False}
    if q.get("type") in OPEN_TYPES:
        return {"kid": ids[0], "capability": "production",
                "reason": "R6 type=production（无语法，取首项）", "fallback": True}
    return {"kid": ids[0], "capability": fallback_capability(q),
            "reason": "R7 无命中，回退 knowledge_ids[0]", "fallback": True}


def reorder_fields(q: dict, target: dict) -> dict:
    kid = target["kid"]
    ids = list(q.get("knowledge_ids") or [])
    context = [k for k in ids if k != kid]
    out = {}
    for key, value in q.items():
        if key in NEW_FIELDS:
            continue
        out[key] = value
        if key == "knowledge_ids":
            out["target_knowledge_ids"] = [kid]
            out["context_knowledge_ids"] = context
            out["targets"] = [{"id": kid, "capability": target["capability"]}]
    if "targets" not in out:
        out["target_knowledge_ids"] = [kid]
        out["context_knowledge_ids"] = context
        out["targets"] = [{"id": kid, "capability": target["capability"]}]
    return out


def validate_row(q: dict) -> list[str]:
    errs = []
    ids = list(q.get("knowledge_ids") or [])
    targets = q.get("targets") or []
    tids = [t.get("id") for t in targets]
    ctx = list(q.get("target_knowledge_ids") or [])
    context = list(q.get("context_knowledge_ids") or [])
    if not targets:
        errs.append("%s targets 为空" % q.get("id"))
    for t in targets:
        if t.get("capability") not in CAPABILITIES:
            errs.append("%s capability 非法 %s" % (q.get("id"), t.get("capability")))
    if any(tid not in ids for tid in tids):
        errs.append("%s targets 不在 knowledge_ids 内" % q.get("id"))
    if set(ctx) != set(tids):
        errs.append("%s target_knowledge_ids 与 targets 不一致" % q.get("id"))
    if set(tids) & set(context):
        errs.append("%s target/context 重叠" % q.get("id"))
    if set(tids) | set(context) != set(ids) or len(tids) + len(context) != len(ids):
        errs.append("%s target+context != knowledge_ids" % q.get("id"))
    return errs


def shuffle_options(q: dict) -> dict:
    """确定性打乱选项顺序，消除「正确答案永远在 A」的位置偏差。

    用题号做种子，同一题每次审计得到同一顺序（可复现、可 diff）。
    `answer` 存的是文本，因此只需换 options 顺序，不改答案本身。
    """
    import hashlib
    import random

    opts = list(q.get("options") or [])
    ans = q.get("answer")
    if len(opts) < 2 or ans not in opts:
        return q
    seed = int(hashlib.sha256(str(q.get("id")).encode()).hexdigest()[:8], 16)
    pos = seed % len(opts)            # 正确答案落在哪个位置，由题号决定
    others = [o for o in opts if o != ans]
    random.Random(seed).shuffle(others)
    q["options"] = others[:pos] + [ans] + others[pos:]
    return q


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="题目目标/语境分离审计")
    ap.add_argument("--check", action="store_true", help="只校验，不回写")
    ap.add_argument("--report", default=str(REPORT))
    args = ap.parse_args(argv)

    idx = Index()
    path = SEED_DIR / "questions.jsonl"
    rows = read_jsonl(path)
    assigned, errs = [], []
    for q in rows:
        try:
            t = choose_target(q, idx)
        except ValueError as e:
            errs.append(str(e))
            continue
        row = shuffle_options(reorder_fields(q, t))
        errs.extend(validate_row(row))
        assigned.append((row, t))

    if errs:
        print("校验失败：", file=sys.stderr)
        for e in errs[:20]:
            print(" -", e, file=sys.stderr)
        return 2

    q1 = next((a for a in assigned if a[0]["id"] == "Q0001"), None)
    if q1 and q1[0]["targets"][0]["id"] != "G0001":
        print("Q0001 target 必须是 G0001，实际 %s" % q1[0]["targets"][0]["id"], file=sys.stderr)
        return 2

    cap_counter = Counter(t["capability"] for _, t in assigned)
    fallbacks = [(row["id"], row["type"], t) for row, t in assigned if t["fallback"]]

    if not args.check:
        lines = [json.dumps(row, ensure_ascii=False) for row, _ in assigned]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = [
        "# 题目目标 / 语境分离报告",
        "",
        "- 生成脚本：`scripts/audit_questions.py`（契约 1.1，确定性规则）",
        "- 题目数：%d｜target 非空：%d｜fallback：%d"
        % (len(assigned), sum(1 for r, _ in assigned if r["targets"]), len(fallbacks)),
        "- 能力分布：%s"
        % "、".join("%s=%d" % (k, cap_counter[k]) for k in CAPABILITIES),
        "- 校验：target+context == knowledge_ids 全部通过；Q0001 target = `%s`"
        % (q1[0]["targets"][0]["id"] if q1 else "N/A"),
        "",
        "## 规则",
        "",
        "R1 例句完全一致 → 语法 usage；R2 等于词 surface/kana → 词（listen=listening，"
        "问中文=meaning，问读音=reading）；R3 汉字音读/训读且问读音 → reading；"
        "R4 命中 pattern、R5 命中例句片段 → 语法 usage；R6 产出题 → 首个语法 production；"
        "R7 无命中 → knowledge_ids[0]（fallback）。",
        "",
        "## fallback 清单（需人工复核）",
        "",
    ]
    if fallbacks:
        report.append("| 题目 | 类型 | 回退目标 | 能力 | 原 knowledge_ids |")
        report.append("|---|---|---|---|---|")
        for qid, qtype, t in fallbacks:
            row = next(r for r, _ in assigned if r["id"] == qid)
            report.append("| %s | %s | %s | %s | %s |"
                          % (qid, qtype, t["kid"], t["capability"],
                             "、".join(row["knowledge_ids"])))
    else:
        report.append("无。")
    report += ["", "## 全量明细", "",
               "| 题目 | 类型 | 答案 | target | 能力 | context | 命中理由 |",
               "|---|---|---|---|---|---|---|"]
    for row, t in assigned:
        report.append("| %s | %s | %s | %s | %s | %s | %s%s |"
                      % (row["id"], row["type"], norm(row.get("answer")) or "—",
                         t["kid"], t["capability"],
                         "、".join(row["context_knowledge_ids"]) or "—",
                         t["reason"], "（fallback）" if t["fallback"] else ""))
    rp = Path(args.report)
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text("\n".join(report) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "questions": len(assigned),
                      "fallback": len(fallbacks),
                      "capabilities": dict(cap_counter),
                      "report": str(rp), "written": not args.check},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
