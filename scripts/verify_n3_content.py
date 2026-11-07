#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 nihongo-80 的 N3 新增内容与模拟考试配置。

只读；发现任何问题以退出码 1 结束，并在 stdout 输出 JSON 摘要。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEEDS = ROOT / "knowledge" / "seeds"

READ_MIN = 180
LISTEN_MIN = 150
GROUPS = {"言語知識", "読解", "聴解"}
KANA_RE = re.compile(r"^[\u3040-\u309f\u30a0-\u30ff\u30fc]+$")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
SENT_SPLIT = re.compile(r"(?<=[。！？])")


def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path.name}:{ln}: JSON 解析失败: {e}")
    return rows


def sentences(text):
    return [p.strip() for p in SENT_SPLIT.split(text) if p.strip()]


def is_new_material(m):
    return m.get("id", "") >= "M0061" and m.get("level") == "N3"


def main():
    problems = []
    summary = {}

    materials = load_jsonl(SEEDS / "materials.jsonl")
    vocab = load_jsonl(SEEDS / "vocabulary.jsonl")
    grammar = load_jsonl(SEEDS / "grammar.jsonl")
    # v4：N3 题目已合并进 questions.jsonl（Q0333 起），不再保留单独文件。
    all_questions = load_jsonl(SEEDS / "questions.jsonl")
    old_questions = [q for q in all_questions if str(q.get("id", "")) < "Q0333"]
    new_questions = [q for q in all_questions if str(q.get("id", "")) >= "Q0333"]

    vmap = {x["id"]: x for x in vocab}
    gmap = {x["id"]: x for x in grammar}
    mmap = {x["id"]: x for x in materials}
    qmap = {x["id"]: x for x in old_questions}
    for x in new_questions:
        if x["id"] in qmap:
            problems.append(f"题目 id 重复: {x['id']}")
        qmap[x["id"]] = x

    # ---------- id 唯一 ----------
    for name, rows in (("materials", materials), ("vocabulary", vocab), ("grammar", grammar)):
        ids = [x.get("id") for x in rows]
        if len(ids) != len(set(ids)):
            dup = sorted({i for i in ids if ids.count(i) > 1})
            problems.append(f"{name} 存在重复 id: {dup}")
    if len(qmap) != len(old_questions) + len(new_questions):
        problems.append("questions.jsonl 存在重复题目 id")

    # ---------- 素材 ----------
    nm = [m for m in materials if is_new_material(m)]
    summary["new_materials"] = {
        "total": len(nm),
        "reading": sum(1 for m in nm if m.get("kind") == "reading"),
        "listening": sum(1 for m in nm if m.get("kind") == "listening"),
        "reading_min_len": min((len(m["text_ja"]) for m in nm if m.get("kind") == "reading"), default=0),
        "listening_min_len": min((len(m["text_ja"]) for m in nm if m.get("kind") == "listening"), default=0),
    }
    for m in nm:
        mid = m["id"]
        kind = m.get("kind")
        threshold = READ_MIN if kind == "reading" else LISTEN_MIN
        if kind not in ("reading", "listening"):
            problems.append(f"{mid}: kind 必须是 reading/listening")
            continue
        if len(m.get("text_ja", "")) < threshold:
            problems.append(f"{mid}: {kind} 长度 {len(m.get('text_ja',''))} < {threshold}")
        if m.get("audio_text") != m.get("text_ja"):
            problems.append(f"{mid}: audio_text 必须等于 text_ja")
        if m.get("audio_url") != "":
            problems.append(f"{mid}: 原创 TTS 素材 audio_url 必须为空")
        if m.get("audio_kind") != "tts":
            problems.append(f"{mid}: audio_kind 必须为 tts")
        if not (0.85 <= float(m.get("known_ratio", 0)) <= 0.95):
            problems.append(f"{mid}: known_ratio 必须在 0.85–0.95")
        if m.get("license") != "original" or m.get("review_status") != "original":
            problems.append(f"{mid}: license/review_status 必须为 original")
        if m.get("source_ids") != ["S000"] or m.get("url") != "":
            problems.append(f"{mid}: source_ids/url 不符合原创约定")
        if not m.get("focus_zh") or len(m["focus_zh"]) < 12:
            problems.append(f"{mid}: focus_zh 过短或为空")
        for vid in m.get("vocab_ids") or []:
            if vid not in vmap:
                problems.append(f"{mid}: vocab_id 不存在 {vid}")
        for gid in m.get("grammar_ids") or []:
            if gid not in gmap:
                problems.append(f"{mid}: grammar_id 不存在 {gid}")
        if not m.get("vocab_ids") or not m.get("grammar_ids"):
            problems.append(f"{mid}: vocab_ids/grammar_ids 不能为空")

        ja = m.get("text_ja", "")
        kana = m.get("text_kana", "")
        zh = m.get("text_zh", "")
        if CJK_RE.search(kana):
            problems.append(f"{mid}: text_kana 混入汉字: {''.join(sorted(set(CJK_RE.findall(kana))))}")
        if not kana:
            problems.append(f"{mid}: text_kana 为空")
        a, b, c = len(sentences(ja)), len(sentences(kana)), len(sentences(zh))
        if not (a == b == c):
            problems.append(f"{mid}: 句数不对齐 ja/kana/zh = {a}/{b}/{c}")
        expect = len(ja) / 5.0
        dur = float(m.get("duration_sec") or 0)
        if not (0.6 * expect <= dur <= 1.4 * expect):
            problems.append(f"{mid}: duration_sec={dur} 与 ~5字/秒估算不符（期望约 {expect:.1f}s）")
        if kind == "listening":
            if "A：" not in ja or "B：" not in ja:
                problems.append(f"{mid}: 听力必须是 A：/B：两人对话")
            if not any(k in ja for k in ("ではなく", "違います", "あ、", "ただ", "実は", "すみません")):
                problems.append(f"{mid}: 未检出改口/更正类信息干扰")
            if "关系" not in m.get("focus_zh", "") and "関係" not in m.get("focus_zh", ""):
                problems.append(f"{mid}: focus_zh 未写明人物关系")

    # ---------- 词汇 ----------
    nv = [v for v in vocab if v.get("id", "") >= "V0261" and v.get("jlpt") == "N3"]
    summary["new_vocab"] = {"total": len(nv)}
    for v in nv:
        vid = v["id"]
        if not v.get("surface") or not v.get("meaning_zh"):
            problems.append(f"{vid}: surface/meaning_zh 不能为空")
        if not KANA_RE.match(v.get("kana", "")):
            problems.append(f"{vid}: kana 只能是平假名/片假名/长音符: {v.get('kana')!r}")
        if not re.match(r"^[a-z]+$", v.get("romaji", "")):
            problems.append(f"{vid}: romaji 必须是小写罗马字: {v.get('romaji')!r}")
        if v.get("jlpt") != "N3":
            problems.append(f"{vid}: jlpt 必须为 N3")
        if not (1 <= int(v.get("frequency") or 0) <= 5):
            problems.append(f"{vid}: frequency 必须在 1–5")
        if len(v.get("notes_for_zh") or "") < 20:
            problems.append(f"{vid}: notes_for_zh 过短，需写中国人易错点")
        ex = v.get("examples") or []
        if not ex:
            problems.append(f"{vid}: 缺少例句")
        for e in ex:
            if not e.get("ja") or not e.get("zh"):
                problems.append(f"{vid}: 例句缺日文或中文")
            for gid in e.get("grammar_ids") or []:
                if gid not in gmap:
                    problems.append(f"{vid}: 例句 grammar_id 不存在 {gid}")

    # ---------- 语法 ----------
    ng = [g for g in grammar if g.get("id", "") >= "G0086"]
    summary["new_grammar"] = {"total": len(ng)}
    for g in ng:
        gid = g["id"]
        for k in ("pattern", "meaning_zh", "connection", "usage", "register_note"):
            if not g.get(k):
                problems.append(f"{gid}: 缺少 {k}")
        if g.get("jlpt") != "N3":
            problems.append(f"{gid}: jlpt 必须为 N3")
        if g.get("review_status") != "self_reviewed" or g.get("provenance") != "self_reviewed":
            problems.append(f"{gid}: review_status/provenance 必须为 self_reviewed")
        if g.get("source_ids") != ["S000"]:
            problems.append(f"{gid}: source_ids 必须是 [S000]")
        ex = g.get("examples") or []
        if len(ex) < 2:
            problems.append(f"{gid}: 例句少于 2 条")
        for e in ex:
            if not e.get("ja") or not e.get("zh"):
                problems.append(f"{gid}: 例句缺日文或中文")
            vids = e.get("vocab_ids") or []
            if not vids:
                problems.append(f"{gid}: 例句缺 vocab_ids")
            for vid in vids:
                if vid not in vmap:
                    problems.append(f"{gid}: 例句 vocab_id 不存在 {vid}")
        for pid in g.get("prerequisites") or []:
            if pid not in gmap:
                problems.append(f"{gid}: prerequisite 不存在 {pid}")
        for c in g.get("compare") or []:
            if c.get("id") not in gmap:
                problems.append(f"{gid}: compare id 不存在 {c.get('id')}")
        ce = g.get("common_errors") or []
        if not ce:
            problems.append(f"{gid}: 缺少 common_errors")
        for e in ce:
            if not e.get("wrong") or not e.get("fix"):
                problems.append(f"{gid}: common_errors 缺 wrong/fix")
            elif e.get("wrong") == e.get("fix"):
                problems.append(f"{gid}: common_errors 的 wrong 与 fix 相同")
            if not e.get("why"):
                problems.append(f"{gid}: common_errors 缺 why")

    # ---------- 新题 ----------
    summary["new_questions"] = {
        "total": len(new_questions),
        "by_group": {g: sum(1 for q in new_questions if q.get("group") == g) for g in sorted(GROUPS)},
    }
    if len(new_questions) < 60:
        problems.append(f"新增题目 {len(new_questions)} < 60")
    for q in new_questions:
        qid = q["id"]
        g = q.get("group")
        if g not in GROUPS:
            problems.append(f"{qid}: group 必须是 {sorted(GROUPS)} 之一")
        elif f"【{g}】" not in q.get("prompt_zh", ""):
            problems.append(f"{qid}: prompt_zh 未注明组别【{g}】")
        if q.get("type") != "mcq":
            problems.append(f"{qid}: 新题必须是 mcq")
        opts = q.get("options") or []
        if len(opts) < 2:
            problems.append(f"{qid}: 选项少于 2 个")
        if q.get("answer") not in opts:
            problems.append(f"{qid}: answer 不在 options 内")
        if not q.get("rationale") or not q.get("rubric"):
            problems.append(f"{qid}: 缺 rationale 或 rubric")
        if not (4 <= int(q.get("difficulty") or 0) <= 5):
            problems.append(f"{qid}: difficulty 必须在 4–5")
        kids = q.get("knowledge_ids") or []
        if not kids:
            problems.append(f"{qid}: knowledge_ids 为空")
        for kid in kids:
            if kid not in vmap and kid not in gmap:
                problems.append(f"{qid}: knowledge_id 不存在 {kid}")
        mid = q.get("material_id")
        if g == "読解":
            if not mid or mid not in mmap:
                problems.append(f"{qid}: 読解题未引用有效素材")
            else:
                m = mmap[mid]
                if m.get("kind") != "reading" or not is_new_material(m):
                    problems.append(f"{qid}: 読解题必须引用新增 N3 阅读素材")
                ref = set(m.get("vocab_ids") or []) | set(m.get("grammar_ids") or [])
                if not ref & set(kids):
                    problems.append(f"{qid}: knowledge_ids 未包含素材 vocab/grammar")
            if "第" not in q.get("prompt_zh", "") or "句" not in q.get("prompt_zh", ""):
                problems.append(f"{qid}: 読解题题干未写明依据第几句")
            if q.get("audio_text"):
                problems.append(f"{qid}: 読解题不应有 audio_text")
        elif g == "聴解":
            if not mid or mid not in mmap:
                problems.append(f"{qid}: 聴解题未引用有效素材")
            else:
                m = mmap[mid]
                if m.get("kind") != "listening" or not is_new_material(m):
                    problems.append(f"{qid}: 聴解题必须引用新增 N3 听力素材")
                if not q.get("audio_text") or q["audio_text"] not in m.get("audio_text", ""):
                    problems.append(f"{qid}: audio_text 不是新听力素材的片段")
                ref = set(m.get("vocab_ids") or []) | set(m.get("grammar_ids") or [])
                if not ref & set(kids):
                    problems.append(f"{qid}: knowledge_ids 未包含素材 vocab/grammar")
        elif g == "言語知識":
            if mid:
                problems.append(f"{qid}: 言語知識题不应绑定素材")

    # ---------- 模考 ----------
    mock_path = ROOT / "knowledge" / "mock_n3.json"
    summary["mock"] = {}
    if not mock_path.exists():
        problems.append("缺少 knowledge/mock_n3.json")
    else:
        mock = json.loads(mock_path.read_text(encoding="utf-8"))
        if mock.get("version") != 1:
            problems.append("mock: version 必须为 1")
        if mock.get("disclaimer") != "模拟估分，不是 JLPT 官方判定":
            problems.append("mock: disclaimer 文案不符")
        if mock.get("total_minutes") != 140:
            problems.append("mock: total_minutes 必须为 140")
        if mock.get("total_points") != 180:
            problems.append("mock: total_points 必须为 180")
        if mock.get("pass_total") != 95:
            problems.append("mock: pass_total 必须为 95")
        expected = [
            ("language", "文字・語彙", 30, 60, 19),
            ("reading", "文法・読解", 70, 60, 19),
            ("listening", "聴解", 40, 60, 19),
        ]
        sections = mock.get("sections") or []
        if len(sections) != 3:
            problems.append("mock: 必须正好 3 个 section")
        seen = set()
        point_sum = 0
        for sec, (sid, name, minutes, points, pass_min) in zip(sections, expected):
            if (sec.get("id"), sec.get("name"), sec.get("minutes"), sec.get("points"), sec.get("pass_min")) != (sid, name, minutes, points, pass_min):
                problems.append(f"mock: section {sid} 字段不符")
            qids = sec.get("question_ids") or []
            dist = sec.get("distribution") or {}
            per = dist.get("per_question")
            if per not in (1, 2):
                problems.append(f"mock: {sid} 每题权重必须为 1–2 分")
            if dist.get("count") != len(qids) or dist.get("total") != points:
                problems.append(f"mock: {sid} distribution 与实际题数/分值不符")
            if per and per * len(qids) != points:
                problems.append(f"mock: {sid} 题数×权重 != {points}")
            point_sum += points
            for qid in qids:
                if qid not in qmap:
                    problems.append(f"mock: 题目不存在 {qid}")
                    continue
                if qid in seen:
                    problems.append(f"mock: 题目跨 section 重复 {qid}")
                seen.add(qid)
                q = qmap[qid]
                if qid >= "Q0333":
                    if q.get("group") != {"language": "言語知識", "reading": "読解", "listening": "聴解"}[sid]:
                        problems.append(f"mock: {qid} 组别与 {sid} 不符")
                else:
                    # 旧题没有 group 字段，按 section 归属即视为有组别
                    if q.get("type") not in ("mcq", "fill", "read", "listen"):
                        problems.append(f"mock: 旧题 {qid} 不是可自动判分的客观题型")
                    opts = q.get("options") or []
                    if opts and q.get("answer") not in opts:
                        problems.append(f"mock: 旧题 {qid} answer 不在 options 内")
        if point_sum != 180:
            problems.append(f"mock: 三分项合计 {point_sum} != 180")
        if len(seen) != sum(len(s.get("question_ids") or []) for s in sections):
            problems.append("mock: 题目总数与各 section 之和不一致")
        summary["mock"] = {
            "sections": [{"id": s.get("id"), "count": len(s.get("question_ids") or []),
                          "points": s.get("points"), "per_question": (s.get("distribution") or {}).get("per_question")}
                         for s in sections],
            "unique_questions": len(seen),
            "point_sum": point_sum,
        }

    summary["problems"] = problems
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
