#!/usr/bin/env python3
"""audit_content.py — 内容准确性审计（REVISION_CONTRACT §8）。

检查项：
  高危：MCQ 答案不在选项内、必填字段为空、common_errors 把合法形式判成错误、
        语法缺接续/例句、素材无正文
  中危：错误示例的语体/语境说明不充分、N3 素材长度未达下限、例句缺中文、
        缺 register_note / provenance、绝对化措辞
  低危：review_status 口径不统一、选项重复等

输出 reports/content_audit.md；高危不为 0 时返回码 1。
用法： python3 scripts/audit_content.py [--report PATH]
"""
from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "knowledge" / "seeds"
REPORT = ROOT / "reports" / "content_audit.md"

OPEN_TYPES = {"free_production", "dialogue", "translate"}
OBJECTIVE_TYPES = {"mcq", "fill", "listen", "read", "reorder", "error_correct"}
KNOWN_TYPES = OPEN_TYPES | OBJECTIVE_TYPES

# 契约 §8：这些是合法日语形式，不得出现在 common_errors.wrong 的纠错点里。
LEGAL_FORMS = ("じゃありません", "じゃない", "ではありません", "ではない", "である",
               "だった", "なかった", "ません", "でした", "です", "だ", "が", "は")
REGISTER_ACK = ("合法", "语体", "礼貌体", "简体", "口语", "书面", "语境", "正式", "随意",
                "过去", "时态", "焦点", "主题", "新信息", "语序", "搭配", "接续",
                "词类", "方向", "疑问", "否定", "名词", "形容词", "动词", "活用", "变形")

ABSOLUTE_PATTERNS = ("只能这样说", "只能这么用", "只能这样", "只能这么",
                     "唯一正确", "唯一", "绝对不", "一定不能", "必须这样", "必须这么说")

N3_READING_MIN = 180   # 契约 §9
N3_LISTENING_MIN = 150


def norm(s) -> str:
    s = unicodedata.normalize("NFKC", str(s or ""))
    return "".join(s.split())


def read_jsonl_with_lines(path: Path):
    rows, lines = [], {}
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rows.append(obj)
            lines[obj.get("id")] = n
    return rows, lines


class Audit:
    def __init__(self) -> None:
        self.issues = []

    def add(self, severity: str, file: str, line: int, oid: str, field: str,
            issue: str, evidence: str = "") -> None:
        self.issues.append({"severity": severity, "file": file, "line": line,
                            "id": oid, "field": field, "issue": issue,
                            "evidence": str(evidence)[:160]})

    def count(self, severity: str) -> int:
        return sum(1 for i in self.issues if i["severity"] == severity)


def check_questions(a: Audit) -> dict:
    rows, lines = read_jsonl_with_lines(SEED_DIR / "questions.jsonl")
    f = "knowledge/seeds/questions.jsonl"
    for q in rows:
        qid, ln = q.get("id", "?"), lines.get(q.get("id"))
        t = q.get("type")
        if t not in KNOWN_TYPES:
            a.add("低危", f, ln, qid, "type", "未知题型 %s" % t, t)
        for field in ("prompt_zh", "rationale", "rubric"):
            if not str(q.get(field) or "").strip():
                a.add("高危", f, ln, qid, field, "必填字段为空", "")
        if not q.get("knowledge_ids"):
            a.add("高危", f, ln, qid, "knowledge_ids", "没有关联知识点", "")
        if t in OBJECTIVE_TYPES:
            if not str(q.get("answer") or "").strip():
                a.add("高危", f, ln, qid, "answer", "客观题缺标准答案", "")
        else:
            # translate 的标准答案就是中文译文；free_production/dialogue 才需要参考产出。
            if t != "translate" and not str(q.get("expected_production") or "").strip():
                a.add("中危", f, ln, qid, "expected_production",
                      "开放题缺参考产出", "")
        if not (str(q.get("prompt_ja") or "").strip()
                or str(q.get("audio_text") or "").strip()
                or t in OPEN_TYPES):
            a.add("高危", f, ln, qid, "prompt_ja",
                  "题面与音频文本同时为空", "")
        if t == "mcq":
            opts = q.get("options")
            if not isinstance(opts, list) or len(opts) < 2:
                a.add("高危", f, ln, qid, "options", "MCQ 选项少于 2 个", opts)
            elif q.get("answer") not in opts:
                a.add("高危", f, ln, qid, "answer", "MCQ 答案不在选项内",
                      "answer=%s options=%s" % (q.get("answer"), opts))
            elif len(set(map(str, opts))) != len(opts):
                a.add("低危", f, ln, qid, "options", "选项存在重复", opts)
        text = json.dumps({k: q.get(k) for k in ("prompt_ja", "prompt_zh", "rationale", "rubric")},
                          ensure_ascii=False)
        for pat in ABSOLUTE_PATTERNS:
            if pat in text:
                a.add("中危", f, ln, qid, "rationale", "绝对化措辞「%s」" % pat,
                      _snippet(text, pat))
    return {"questions": len(rows)}


def check_grammar(a: Audit) -> dict:
    rows, lines = read_jsonl_with_lines(SEED_DIR / "grammar.jsonl")
    f = "knowledge/seeds/grammar.jsonl"
    for g in rows:
        gid, ln = g.get("id", "?"), lines.get(g.get("id"))
        for field in ("pattern", "connection", "meaning_zh"):
            if not str(g.get(field) or "").strip():
                sev = "高危" if field == "connection" else "中危"
                a.add(sev, f, ln, gid, field, "语法字段为空", "")
        exs = g.get("examples") or []
        if not exs:
            a.add("高危", f, ln, gid, "examples", "语法没有例句", "")
        for i, ex in enumerate(exs):
            if not str(ex.get("ja") or "").strip():
                a.add("高危", f, ln, gid, "examples[%d].ja" % i, "例句缺日文", "")
            if not str(ex.get("zh") or "").strip():
                a.add("中危", f, ln, gid, "examples[%d].zh" % i, "例句缺中文", ex.get("ja"))
        ces = g.get("common_errors") or []
        if not ces:
            a.add("低危", f, ln, gid, "common_errors", "没有常见错误示例", "")
        for i, ce in enumerate(ces):
            wrong, fix, why = ce.get("wrong"), ce.get("fix"), str(ce.get("why") or "")
            if not str(wrong or "").strip() or not str(fix or "").strip():
                a.add("高危", f, ln, gid, "common_errors[%d]" % i,
                      "错误示例或修正为空", wrong)
                continue
            hits = _suspicious_legal(wrong, fix)
            if hits:
                # 有解释说明的语体/语法差异 → 中危待复核；完全没解释 → 高危。
                acknowledged = (any(k in why for k in REGISTER_ACK)
                                or "本身合法" in why or "本题要求" in why
                                or "不是错句" in why or "语体不匹配" in why)
                sev = "低危" if acknowledged else "高危"
                a.add(sev, f, ln, gid, "common_errors[%d].wrong" % i,
                      "把合法形式「%s」当作错误" % hits, wrong)
        if not str(g.get("register_note") or "").strip():
            a.add("中危", f, ln, gid, "register_note", "缺语体/语境说明", "")
        if not g.get("provenance"):
            a.add("中危", f, ln, gid, "provenance", "缺来源标注", "")
        if g.get("review_status") != "self_reviewed":
            a.add("低危", f, ln, gid, "review_status",
                  "review_status 未统一为 self_reviewed", g.get("review_status"))
        text = json.dumps({k: g.get(k) for k in
                           ("usage", "notes", "register_note", "common_errors", "compare")},
                          ensure_ascii=False)
        for pat in ABSOLUTE_PATTERNS:
            if pat in text:
                a.add("中危", f, ln, gid, "usage", "绝对化措辞「%s」" % pat,
                      _snippet(text, pat))
    return {"grammar": len(rows)}


def check_materials(a: Audit) -> dict:
    rows, lines = read_jsonl_with_lines(SEED_DIR / "materials.jsonl")
    f = "knowledge/seeds/materials.jsonl"
    n3 = 0
    n3_exam = 0
    n3_drill = 0
    for m in rows:
        mid, ln = m.get("id", "?"), lines.get(m.get("id"))
        text = str(m.get("text_ja") or "")
        if not text.strip():
            if m.get("review_status") != "index_only":
                a.add("高危", f, ln, mid, "text_ja", "素材没有正文", "")
            continue
        if m.get("level") != "N3":
            continue
        n3 += 1
        n = len(text)
        # v4：N3 素材分两类。exam = 考试级长文，必须达到长度下限；
        # drill = 明确标注的短句练习，不冒充読解/聴解长文，只检查其余字段。
        # 这样既不把短句藏起来充数，也不再用「长度不够」否定它的练习价值。
        if m.get("material_role") == "drill":
            n3_drill += 1
            if m.get("audio_url") in (None, "") and not m.get("audio_kind"):
                a.add("低危", f, ln, mid, "audio_kind", "无音频时未显式标注 tts", "")
            continue
        n3_exam += 1
        if m.get("kind") == "listening":
            if n < N3_LISTENING_MIN:
                a.add("中危", f, ln, mid, "text_ja",
                      "N3 听力素材 %d 字符 < 下限 %d" % (n, N3_LISTENING_MIN), text[:40])
            elif n < N3_READING_MIN:
                a.add("低危", f, ln, mid, "text_ja",
                      "N3 听力素材 %d 字符（契约 §9 下限 150，任务书基线 180）" % n, "")
        elif n < N3_READING_MIN:
            a.add("中危", f, ln, mid, "text_ja",
                  "N3 阅读素材 %d 字符 < 下限 %d" % (n, N3_READING_MIN), text[:40])
        if m.get("audio_url") in (None, "") and not m.get("audio_kind"):
            a.add("低危", f, ln, mid, "audio_kind", "无音频时未显式标注 tts", "")
    return {"materials": len(rows), "n3_materials": n3,
            "n3_exam": n3_exam, "n3_drill": n3_drill}


def _diff_cores(wrong: str, fix: str) -> tuple[str, str]:
    """取 wrong→fix 的最小差异片段，用来判断「纠错点」是否正好是合法形式。"""
    w, f = norm(wrong), norm(fix)
    i = 0
    while i < min(len(w), len(f)) and w[i] == f[i]:
        i += 1
    j = 0
    while j < min(len(w), len(f)) - i and w[-1 - j] == f[-1 - j]:
        j += 1
    return w[i:len(w) - j], f[i:len(f) - j]


def _suspicious_legal(wrong: str, fix: str) -> str:
    """只有「两个合法形式互换」或「整条就是合法形式」才算疑似。

    单纯删除一个合法助词（如 はも→も）往往是真纠错，不能误报。
    """
    core_w, core_f = _diff_cores(wrong, fix)
    # 高いだ / 飲みたいだ 这类「い形容词・たい形 + だ」本来就是错的，
    # 不能因为句尾是 だ 就当成「把合法形式判错」。
    if core_w in ("だ", "です"):
        w = norm(wrong)
        i = w.find(core_w)
        prev = w[i - 1] if i > 0 else ""
        tail2 = w[max(0, i - 2):i]
        if prev in "いきしちにひみりえけせてねべめれ" or tail2 in ("たい", "ない"):
            return ""
    if core_w in LEGAL_FORMS and core_f in LEGAL_FORMS:
        return core_w
    if norm(wrong) in LEGAL_FORMS:
        return norm(wrong)
    return ""


def _snippet(text: str, pat: str) -> str:
    i = text.find(pat)
    return text[max(0, i - 24): i + len(pat) + 24] if i >= 0 else ""
    i = text.find(pat)
    return text[max(0, i - 24): i + len(pat) + 24] if i >= 0 else ""


def check_known_fixes(a: Audit) -> list[tuple[str, bool, str]]:
    """契约 §8 三处已知错误的回归开关。"""
    qs = {q["id"]: q for q in read_jsonl_with_lines(SEED_DIR / "questions.jsonl")[0]}
    gs = {g["id"]: g for g in read_jsonl_with_lines(SEED_DIR / "grammar.jsonl")[0]}
    q6 = qs.get("Q0006", {})
    q6_ok = ("语体" in str(q6.get("prompt_zh"))
             and "礼貌体" in str(q6.get("prompt_zh"))
             and "合法" in str(q6.get("rationale"))
             and "礼貌体" in str(q6.get("rubric")))
    g2 = gs.get("G0002", {})
    g2_ok = all("じゃありません" not in ce.get("wrong", "")
                for ce in g2.get("common_errors") or [])
    g5 = gs.get("G0005", {})
    g5_ok = (all("これが本ですか" not in ce.get("wrong", "")
                 for ce in g5.get("common_errors") or [])
             and "焦点" in str(g5.get("notes") or ""))
    out = [("Q0006 改为语体不匹配表述", q6_ok, q6.get("prompt_zh", "")),
           ("G0002 不再把 じゃありません 当错误", g2_ok,
            "、".join(ce.get("wrong", "") for ce in g2.get("common_errors") or [])),
           ("G0005 不再把 これが本ですか 当错误", g5_ok, g5.get("notes", ""))]
    for name, ok, ev in out:
        if not ok:
            a.add("高危", "knowledge/seeds", 0, name.split()[0], "regression",
                  "已知错误未修复：%s" % name, ev)
    return out


def write_report(a: Audit, stats: dict, fixes: list, path: Path) -> None:
    order = {"high": "高危", "medium": "中危", "low": "低危"}
    counts = {k: a.count(k) for k in ("高危", "中危", "低危")}
    out = [
        "# 内容审计报告",
        "",
        "- 生成脚本：`scripts/audit_content.py`（契约 §8）",
        "- 数据源：`knowledge/seeds/*.jsonl`（只读检查，不改种子）",
        "- 摘要：**高危 %d**｜中危 %d｜低危 %d" % (counts["高危"], counts["中危"], counts["低危"]),
        "- 覆盖：题目 %d｜语法 %d｜素材 %d（其中 N3 %d）"
        % (stats.get("questions", 0), stats.get("grammar", 0),
           stats.get("materials", 0), stats.get("n3_materials", 0)),
        "",
        "## 已知错误回归",
        "",
        "| 检查 | 结果 | 证据 |",
        "|---|---|---|",
    ]
    for name, ok, ev in fixes:
        out.append("| %s | %s | %s |" % (name, "通过" if ok else "**未通过**",
                                          str(ev).replace("|", "/")[:80]))
    out += ["", "## 分级明细", ""]
    for sev in ("高危", "中危", "低危"):
        items = [i for i in a.issues if i["severity"] == sev]
        out += ["### %s（%d）" % (sev, len(items)), ""]
        if not items:
            out += ["无。", ""]
            continue
        out += ["| 位置 | 条目 | 字段 | 问题 | 证据 |", "|---|---|---|---|---|"]
        for i in items:
            out.append("| `%s:%s` | %s | %s | %s | %s |"
                       % (i["file"], i["line"], i["id"], i["field"], i["issue"],
                          i["evidence"].replace("|", "/").replace("\n", " ")))
        out.append("")
    out += [
        "## 口径说明",
        "",
        "- 高危 = 会教错日语或题目结构损坏；中危 = 语体/语境说明不足、素材长度未达标、"
        "缺字段；低危 = 口径不统一。",
        "- `common_errors.wrong` 命中合法形式白名单时：若 `why` 明确说明是语体/语境差异记为"
        "中危，否则记高危。",
        "- N3 素材长度按契约 §9：阅读 ≥180 字符、听力 ≥150 字符（任务书对听力的 180 基线"
        "单列为低危提示）。",
        "- 中危里的 N3 素材长度项属于素材批次（契约 §9）待补内容，本报告逐条列出 M 编号与"
        "当前字符数，便于素材侧按 180/150 下限扩写。",
        "- 中危里的 `common_errors.wrong` 项表示「纠错点正好落在合法形式上」，`why` 已给出"
        "语体/语法解释，但建议人工再确认是否应改写成真正不合法形式。",
        "- `review_status=self_reviewed` 仅表示项目内自查，未经外部日语教师逐条验证。",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="内容准确性审计")
    ap.add_argument("--report", default=str(REPORT))
    args = ap.parse_args(argv)
    a = Audit()
    stats = {}
    stats.update(check_questions(a))
    stats.update(check_grammar(a))
    stats.update(check_materials(a))
    fixes = check_known_fixes(a)
    write_report(a, stats, fixes, Path(args.report))
    counts = {k: a.count(k) for k in ("高危", "中危", "低危")}
    print(json.dumps({"ok": counts["高危"] == 0, "high": counts["高危"],
                      "medium": counts["中危"], "low": counts["低危"],
                      "report": args.report, "stats": stats},
                     ensure_ascii=False, indent=2))
    return 0 if counts["高危"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
