#!/usr/bin/env python3
"""merge_sources.py — 合并三份真实调研清单，生成统一机器可读来源表与总表。

同时修正种子数据的来源标注：把全部 `["S001"]` 占位改为 `S000`（项目原创整理），
避免把「按通用大纲整理的词表」虚构成引用了 IRODORI 教材；外部索引素材按 URL 映射到真实来源。

运行： python3 scripts/merge_sources.py
"""
from __future__ import annotations

import json
from pathlib import Path

from core import iso, root_of

FIELDS = ["id", "sid", "name", "url", "category", "content_type", "coverage",
          "languages", "access_method", "download_url", "update_status", "license",
          "usage_scope", "role_in_project", "quality_risks", "fetch_status",
          "http_status", "checked_at", "evidence", "notes", "claim", "verified",
          "source_file"]


def load(path):
    if not path.exists():
        print("! 缺少 %s，跳过" % path.name)
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(o, source_file):
    d = {k: o.get(k, "" if k not in ("languages", "verified") else
                  ([] if k == "languages" else None)) for k in FIELDS}
    d["source_file"] = source_file
    d["sid"] = ""            # 稍后分配
    if isinstance(d["languages"], str):
        d["languages"] = [x for x in d["languages"].split(",") if x]
    if o.get("claim"):
        d["content_type"] = d["content_type"] or ("研究结论/平台能力核实：%s" % str(o["claim"])[:120])
        d["role_in_project"] = d["role_in_project"] or "学习机制与平台能力的设计依据"
        d["fetch_status"] = d["fetch_status"] or ("OK" if o.get("verified") else "UNVERIFIED")
    return d


def main():
    r = root_of()
    groups = [
        ("official", load(r / "research/sources_official.json")),
        ("github", load(r / "research/sources_github.json")),
        ("science", load(r / "research/sources_science.json")),
    ]
    entries = []
    # S000 是项目原创整理，不是外部资料
    entries.append({
        "id": "project-original", "sid": "S000", "name": "项目原创整理（词汇/语法/汉字/题库/原创短文）",
        "url": "(本地 knowledge/seeds/)", "category": "internal",
        "content_type": "基于通用 N5–N3 教学大纲整理并逐条自检的基础语言知识；未逐条引用外部词典",
        "coverage": "150 词 / 55 语法 / 70 汉字 / 212 题 / 29 篇原创短文",
        "languages": ["ja", "zh"], "access_method": "本地 JSONL", "download_url": "",
        "update_status": "随项目维护", "license": "项目内自产内容",
        "usage_scope": "本项目私用；再分发前需自行核对上游词典许可",
        "role_in_project": "课程与练习的实际内容来源",
        "quality_risks": "**未逐条对照 JMdict / KANJIDIC 校核**；6 条已标 needs_review，"
                         "其余为人工整理后的 verified，不等于权威词典认证。",
        "fetch_status": "N/A", "http_status": "", "checked_at": "2026-11-06",
        "evidence": "knowledge/seeds/*.jsonl", "notes": "刻意不虚构外部教材引用关系。",
        "claim": "", "verified": None, "source_file": "internal",
    })
    n = 1
    for group, items in groups:
        for o in items:
            d = normalize(o, "research/sources_%s.json" % ("off" if group == "official" else group))
            d["sid"] = "S%03d" % n
            n += 1
            entries.append(d)
    # 外部索引素材若不在既有多来源 URL 中，追加独立来源条目，绝不回落到 S000（原创）
    by_orig = {e["id"]: e["sid"] for e in entries}
    sid_of = {}
    for e in entries:
        u = str(e["url"] or "")
        for key in ("irodori.jpf.go.jp", "tadoku.org", "jlpt.jp",
                    "nhk.or.jp/lesson", "www3.nhk.or.jp/news/easy"):
            if key in u:
                sid_of.setdefault(key, e["sid"])
    mrows = [json.loads(x) for x in (r / "knowledge/seeds/materials.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    existing_path = r / "config" / "sources.json"
    existing_by_id = {}
    if existing_path.exists():
        try:
            prev = json.loads(existing_path.read_text(encoding="utf-8")).get("sources", [])
            existing_by_id = {e["id"]: e["sid"] for e in prev}
            for e in prev:                       # 重复运行仍保留已追加的外部索引来源
                if str(e.get("id", "")).startswith("extra:") and e["id"] not in by_orig:
                    entries.append(e)
                    by_orig[e["id"]] = e["sid"]
                    dom = e["url"].split("/")[2] if "//" in str(e["url"]) else str(e["url"])
                    sid_of[dom] = e["sid"]
        except Exception:
            pass
    for m in mrows:
        if m.get("review_status") != "index_only":
            continue
        u = str(m.get("url", ""))
        hit = next((sid for k, sid in sid_of.items() if k in u), None)
        if hit:
            continue
        domain = u.split("/")[2] if "//" in u else u
        eid = "extra:" + domain
        if eid in by_orig:
            continue
        if eid in existing_by_id:      # 重复运行时保持 SID 稳定
            sid_of[domain] = existing_by_id[eid]
            continue
        sid = "S%03d" % n; n += 1
        entries.append(normalize({
            "id": eid, "name": m.get("title", domain), "url": u,
            "category": "official_material", "content_type": "外部延伸阅读索引（仅 URL，无正文）",
            "license": m.get("license", ""), "fetch_status": "PARTIAL",
            "notes": "由素材索引子任务核实 URL 与许可证；未纳入 8 个官方站的系统调研，"
                     "故标 PARTIAL，不冒充已完整核实。",
            "role_in_project": "每周延伸阅读索引，不内嵌正文",
            "quality_risks": "版权与再利用范围以官网条款为准；本项目只存链接。",
            "checked_at": "2026-11-06", "source_file": "knowledge/seeds/materials.jsonl",
        }, "knowledge/seeds/materials.jsonl"))
        entries[-1]["sid"] = sid
        by_orig[eid] = sid
        sid_of[domain] = sid

    cfg = r / "config"; cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "sources.json").write_text(json.dumps({
        "schema": 1, "generated_at": iso(), "count": len(entries),
        "note": "S000 为项目原创整理；S001+ 来自 2026-11-06 真实调研，fetch_status=FAIL/PARTIAL 表示未核实。",
        "sources": entries,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # URL 关键词 -> SID（含上一步为未登记外部索引追加的来源）
    def map_url(url):
        for k, sid in sid_of.items():
            if k in url:
                return sid
        return "S000"

    seed_dir = r / "knowledge" / "seeds"
    changed = {}
    for p in sorted(seed_dir.glob("*.jsonl")):
        rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        c = 0
        for o in rows:
            old = o.get("source_ids") or []
            if o.get("review_status") == "index_only":
                new = [map_url(str(o.get("url", "")))]
            elif old == ["S001"] or not old:
                new = ["S000"]          # 原创整理，不再冒充外部教材
            else:
                new = old
            if new != old:
                o["source_ids"] = new; c += 1
        if c:
            p.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n", encoding="utf-8")
        changed[p.name] = c

    # 人读总表
    md = ["# 资料来源总登记表（research/source_registry.md）", "",
          "生成时间：%s｜来源：三份子任务真实调研记录 + 本地知识种子" % iso(), "",
          "> **诚实声明**：下表 `fetch_status` 为 FAIL / PARTIAL / UNVERIFIED 的条目表示**未能核实**，",
          "> 其内容字段为空或仅作旁证，不得当作已确认事实使用。未访问成功的站点没有编造内容。", "",
          "## 1. 统计", ""]
    from collections import Counter
    st = Counter(str(e["fetch_status"] or "UNKNOWN") for e in entries)
    md.append("| 状态 | 数量 | 含义 |")
    md.append("|---|---|---|")
    for k, v in sorted(st.items()):
        md.append("| %s | %d | %s |" % (k, v, {
            "OK": "真实访问并核实", "PARTIAL": "部分页面可访问，主体未核实",
            "FAIL": "无法访问，未核实", "UNVERIFIED": "研究结论未能核实",
            "N/A": "项目内自产内容"}.get(k, "见各条 notes")))
    md += ["", "合计 %d 条（含 S000 原创整理 1 条）。" % len(entries), "",
           "## 2. 官方日语教学资料（8）", "",
           "| SID | 名称 | 状态 | 许可证 | 下载/访问 | 项目作用 | 主要风险 |",
           "|---|---|---|---|---|---|---|"]
    for e in entries:
        if e["category"] == "official_material":
            md.append("| %s | [%s](%s) | %s | %s | %s | %s | %s |" % (
                e["sid"], str(e["name"]).replace("|", "/"), e["url"], e["fetch_status"],
                str(e["license"])[:60].replace("|", "/"), str(e["access_method"])[:70].replace("|", "/"),
                str(e["role_in_project"])[:70].replace("|", "/"),
                str(e["quality_risks"])[:70].replace("|", "/")))
    md += ["", "## 3. GitHub 技术项目与语料（10）", "",
           "| SID | 名称 | 状态 | 许可证 | 数据格式/更新 | 项目作用 |",
           "|---|---|---|---|---|---|"]
    for e in entries:
        if e["category"] in ("github", "corpus"):
            md.append("| %s | [%s](%s) | %s | %s | %s | %s |" % (
                e["sid"], str(e["name"]).replace("|", "/"), e["url"], e["fetch_status"],
                str(e["license"])[:45].replace("|", "/"),
                str(e["content_type"])[:60].replace("|", "/"),
                str(e["role_in_project"])[:65].replace("|", "/")))
    md += ["", "## 4. 学习科学 / 教学 Agent / 平台能力（60 条结论）", "",
           "详见 `research/learning_science.md`、`research/platform_capabilities.md`、",
           "`research/sources_science.json`。其中 `verified=false` 的结论未纳入设计依据。", "",
           "| 项目 | 数值 |", "|---|---|",
           "| 结论总数 | %d |" % sum(1 for e in entries if e["category"] in ("science", "agent", "platform")),
           "| verified=true | %d |" % sum(1 for e in entries if e["verified"] is True),
           "| verified=false / 未核实 | %d |" % sum(1 for e in entries if e["verified"] is False or e["verified"] is None), "",
           "## 5. 关键许可证结论（影响本项目可用范围）", "",
           "- **IRODORI**：官方自定义 Terms of Use，允许私用/教育、自制教材须免费并注明来源；**不是 CC BY-NC**。",
           "- **Tadoku Free Tadoku Books**：CC BY-NC-ND 4.0，需署名 NPO多言語多読；ND 禁止改作后发布。",
           "- **JLPT 官方样题**：可下载 PDF/MP3 用于对齐题型，但页面无开放许可，**只作索引与短句引用，不复制原题**。",
           "- **NHK Lesson**：personal use only；Minato 注册制、条款未核实；Erin 主站访问失败。",
           "- **JMdict / KANJIDIC**：CC BY-SA-4.0 + EDRDG Licence Statement；EDRDG 文档 wiki 已关闭，DTD 细节未能核实。",
           "- **Tatoeba**：CC BY 2.0 FR（部分 CC0）；**Tanaka Corpus 为公有领域**。",
           "- **py-fsrs 6.3.1 / ts-fsrs**：MIT（本项目 vendor 的是 py-fsrs，复习引擎不自造公式）。",
           "- **Anki**：AGPL-3.0-or-later；**yomitan**：GPL-3.0-only —— 均未复制其代码进本项目。",
           "", "## 6. 本项目实际使用方式", "",
           "- 课程内容主体是 `S000` 项目原创整理（不虚构外部教材引用）；",
           "  外部来源只用于 **大纲对齐、题型对齐、延伸阅读索引**。",
           "- 外部版权教材正文一律不入库：`materials.jsonl` 中 `review_status=index_only` 的条目",
           "  只保留 URL 与许可证，`text_ja` 为空，构建时有强校验。",
           "- 听力音频不复制外部 MP3；网页用浏览器 `speechSynthesis(ja-JP)` 朗读题库自带的 `audio_text`。",
           "", "## 7. 未核实 / 剩余风险（如实列出）", "",
           "- Erin 主站 `https://erin.jpf.go.jp/` 两次访问失败；NHK Lesson 主页面返回不完整（PARTIAL）。",
           "- EDRDG 文档 wiki 关闭，JMdict/KANJIDIC 的 DTD 细节未核实（其余字段已交叉补齐）。",
           "- 词频数据存在 LICENSE-BLOCKED 子集（JPDB 系），本项目未使用。",
           "- 平台能力：桌面端定时任务是否支持任意 cron、子 Agent 级上下文隔离机制未能核实，按不可用处理。",
           "- 更多细节见 `research/platform_capabilities.md` 的「未能核实清单」。", ""]
    (r / "research" / "source_registry.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"ok": True, "sources": len(entries), "status": dict(st),
                      "seeds_remapped": changed,
                      "outputs": ["config/sources.json", "research/source_registry.md"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
