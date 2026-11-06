#!/usr/bin/env python3
"""生成可粘贴到「新建 WorkBuddy 独立会话」的 Day N 开场提示词。

只读数据源（全部容错，不存在不崩溃、不编造）：
  - curriculum/curriculum.json     当天课程（由别的任务生成，本脚本不创建）
  - student/*.json                 export_state 生成的只读镜像
  - data/state.db                 唯一可写真源，这里仅以只读方式查询（可不存在）
  - sessions/                     可选的上一日总结 / 会话日志
输出：一段 Markdown 提示词，含绝对路径清单、当天目标、预算、到期复习、
最近错题、上一日总结、必须调用的命令、结束时必须回写的命令。

纯标准库；不写任何文件、不改状态。缺少的数据一律标注「未就绪 / 降级」，
绝不编造课程、复习队列、错题或总结。

用法：python3 scripts/new_session_prompt.py <day>
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUR = ROOT / "curriculum" / "curriculum.json"
STUDENT = ROOT / "student"
DB = ROOT / "data" / "state.db"
SESSIONS = ROOT / "sessions"

DUE_KEYS = {"due", "due_queue", "review_queue", "due_reviews", "today_review"}
ERR_KEYS = {"mistakes", "recent_errors", "error_history", "recent_wrong", "errors"}
SUM_KEYS = {
    "last_summary", "previous_day_summary", "daily_summary", "summary", "last_day_summary"
}


def rel(*parts: str) -> str:
    """返回 ROOT 下的绝对路径字符串。"""
    return str(ROOT.joinpath(*parts))


def read_json(path: Path):
    """返回 (对象, 错误字符串)；出错时对象为 None。"""
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, "文件不存在"
    except json.JSONDecodeError as e:
        return None, "JSON 解析失败（%s）" % e
    except OSError as e:
        return None, "读取失败（%s）" % e


def first_col(cols, names):
    for n in names:
        if n in cols:
            return n
    return None


def table_cols(conn, table):
    return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}


def is_wrong(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return value == 0
    return str(value).strip().lower() in {"0", "false", "no", "wrong", "fail", "again"}


def parse_dt(raw):
    if raw is None:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def brief(items, limit: int = 10):
    """把列表项压成简短可读字符串，避免提示词爆炸。"""
    out = []
    for x in items[:limit]:
        if isinstance(x, dict):
            keep = {
                k: x[k]
                for k in ("id", "knowledge_id", "qid", "error_type", "due", "stage", "type")
                if x.get(k) not in (None, "")
            }
            out.append(json.dumps(keep or x, ensure_ascii=False, default=str)[:160])
        else:
            out.append(str(x)[:160])
    return out


def brief_scalar(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, default=str)[:600]
    return str(v)[:600]


# ---------------------------------------------------------------------------
# 课程
# ---------------------------------------------------------------------------
def read_lesson(day: int):
    obj, err = read_json(CUR)
    if obj is None:
        return None, "curriculum/curriculum.json %s" % err
    if not isinstance(obj, dict) or not isinstance(obj.get("days"), list):
        return None, "curriculum.json 结构异常（缺少 days 数组）"
    for d in obj["days"]:
        if isinstance(d, dict) and d.get("day") == day:
            return d, None
    return None, "curriculum.json 中未找到 day=%d 的课程" % day


def render_lesson(lesson):
    if lesson is None:
        return "（未就绪：见第 0 节降级提示，本提示词不编造课程数据）"
    lines = []
    fields = [
        ("phase", "阶段"), ("theme", "主题"), ("scene", "场景"),
        ("assessment", "测评类型"), ("minutes", "预算(分钟)"),
        ("rubric", "评分准则"), ("completion", "完成标准"),
    ]
    for key, label in fields:
        if lesson.get(key) not in (None, ""):
            lines.append("- %s：%s" % (label, lesson[key]))
    objs = lesson.get("objectives") or []
    if objs:
        lines.append("- 目标：")
        lines.extend(["  - %s" % o for o in objs])
    blocks = lesson.get("blocks") or []
    if blocks:
        lines.append("- 时间块（合计须等于 minutes）：")
        for b in blocks:
            lines.append("  - %s 分钟 · %s · %s" % (b.get("min", "?"), b.get("type", "?"), b.get("desc", "")))
    for key, label in [
        ("new_vocab_ids", "新词汇"), ("new_grammar_ids", "新语法"),
        ("new_kanji_ids", "新汉字"), ("review_knowledge_ids", "复习知识点"),
        ("material_ids", "素材"), ("question_ids", "题目"),
    ]:
        ids = lesson.get(key) or []
        if ids:
            shown = ", ".join(str(i) for i in ids[:20])
            if len(ids) > 20:
                shown += " …（共 %d 项）" % len(ids)
            lines.append("- %s：%s" % (label, shown))
    return "\n".join(lines) if lines else "（课程条目存在但无可读字段）"


# ---------------------------------------------------------------------------
# 状态库（只读、容错）
# ---------------------------------------------------------------------------
def read_db(day: int):
    out = {
        "exists": False, "reason": "", "tables": [],
        "due_ok": False, "due": [], "due_note": "",
        "errors_ok": False, "errors": [], "errors_note": "",
        "summary": None, "summary_source": "",
    }
    if not DB.exists():
        out["reason"] = "data/state.db 不存在（尚未初始化）"
        return out
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        out["reason"] = "只读打开失败（%s）" % e
        return out
    try:
        tables = [
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        tset = set(tables)
        out["exists"] = True
        out["tables"] = tables
        now = datetime.now(timezone.utc)

        # ---- 到期复习 ----
        if "fsrs_cards" in tset:
            cols = table_cols(conn, "fsrs_cards")
            idc = first_col(cols, ["knowledge_id", "card_id", "item_id", "id"])
            duec = first_col(cols, ["due", "due_at", "due_date", "next_review"])
            stagec = first_col(cols, ["stage", "state", "mastery_state"])
            if idc and duec:
                rows = conn.execute(
                    'SELECT * FROM "fsrs_cards" WHERE "%s" IS NOT NULL '
                    'ORDER BY "%s" ASC LIMIT 300' % (duec, duec)
                ).fetchall()
                unparsed = 0
                for r in rows:
                    dt = parse_dt(r[duec])
                    if dt is None:
                        unparsed += 1
                        continue
                    if dt <= now:
                        out["due"].append({
                            "id": str(r[idc]),
                            "due": str(r[duec]),
                            "stage": str(r[stagec]) if stagec and r[stagec] else "",
                        })
                out["due_ok"] = True
                note = "来自 fsrs_cards（按 %s <= 当前 UTC 筛选；扫描 %d 行，命中 %d 条" % (
                    duec, len(rows), len(out["due"])
                )
                if unparsed:
                    note += "；%d 条 due 格式未识别已跳过" % unparsed
                out["due_note"] = note + "；权威队列以 nh80.py 为准）"
            else:
                out["due_note"] = "fsrs_cards 存在但缺少 id / due 列，未做到期筛选"
        else:
            out["due_note"] = "state.db 中无 fsrs_cards 表，无法读取到期队列"

        # ---- 最近错题 ----
        if "attempts" in tset:
            cols = table_cols(conn, "attempts")
            correctc = first_col(cols, ["correct", "is_correct"])
            ratingc = "rating" if "rating" in cols else None
            qidc = first_col(cols, ["qid", "question_id", "knowledge_id", "item_id"])
            errc = first_col(cols, ["error_type", "error_category"])
            tsc = first_col(cols, ["ts", "created_at", "answered_at", "timestamp"])
            order = 'ORDER BY "%s" DESC' % tsc if tsc else ""
            rows = conn.execute(
                'SELECT * FROM "attempts" %s LIMIT 300' % order
            ).fetchall()
            for r in rows:
                if correctc:
                    wrong = is_wrong(r[correctc])
                elif ratingc:
                    wrong = str(r[ratingc]).strip() == "1"  # Again
                else:
                    wrong = False
                if wrong:
                    out["errors"].append({
                        "qid": str(r[qidc]) if qidc and r[qidc] else "",
                        "error_type": str(r[errc]) if errc and r[errc] else "未分类",
                        "ts": str(r[tsc]) if tsc and r[tsc] else "",
                    })
                if len(out["errors"]) >= 10:
                    break
            out["errors_ok"] = True
            basis = correctc or (ratingc + "=1(Again)" if ratingc else "无（表内无正确/评分列）")
            out["errors_note"] = "来自 attempts（判错依据：%s；最多 10 条）" % basis
        else:
            out["errors_note"] = "state.db 中无 attempts 表，无法读取最近错题"

        # ---- 上一日总结 ----
        out["summary"], out["summary_source"] = summary_from_db(conn, tset, day)
    except sqlite3.Error as e:
        out["reason"] = "查询出错（%s）" % e
    finally:
        conn.close()
    return out


def summary_from_db(conn, tset, day: int):
    for t in ("daily_summary", "day_summaries", "sessions", "session_log"):
        if t not in tset:
            continue
        cols = table_cols(conn, t)
        dayc = first_col(cols, ["day", "day_no", "day_number"])
        textc = first_col(cols, ["summary", "text", "content", "note", "report"])
        orderc = first_col(cols, ["day", "ts", "created_at", "id"])
        try:
            if dayc and textc:
                row = conn.execute(
                    'SELECT * FROM "%s" WHERE "%s" < ? ORDER BY "%s" DESC LIMIT 1'
                    % (t, dayc, dayc), (day,)
                ).fetchone()
            elif orderc:
                row = conn.execute(
                    'SELECT * FROM "%s" ORDER BY "%s" DESC LIMIT 1' % (t, orderc)
                ).fetchone()
            else:
                row = conn.execute('SELECT * FROM "%s" LIMIT 1' % t).fetchone()
            if row is None:
                continue
            if textc and row[textc]:
                return str(row[textc])[:600], "state.db 表 %s" % t
            data = {k: row[k] for k in row.keys() if row[k] not in (None, "")}
            return json.dumps(data, ensure_ascii=False, default=str)[:600], "state.db 表 %s" % t
        except sqlite3.Error:
            continue
    return None, ""


# ---------------------------------------------------------------------------
# 只读镜像 / 会话目录
# ---------------------------------------------------------------------------
def read_student():
    out = {"files": [], "due": [], "errors": [], "summary": None, "summary_source": ""}
    if not STUDENT.is_dir():
        return out
    for f in sorted(STUDENT.glob("*.json")):
        obj, err = read_json(f)
        if obj is None:
            out["files"].append("%s（%s）" % (f.name, err))
            continue
        out["files"].append(f.name)
        if not isinstance(obj, dict):
            continue
        for k, v in obj.items():
            kl = k.lower()
            if kl in DUE_KEYS and isinstance(v, list):
                out["due"].extend(brief(v))
            elif kl in ERR_KEYS and isinstance(v, list):
                out["errors"].extend(brief(v))
            elif kl in SUM_KEYS and out["summary"] is None:
                out["summary"] = brief_scalar(v)
                out["summary_source"] = "student/%s : %s" % (f.name, k)
    return out


def read_sessions_summary(day: int):
    prev = day - 1
    if prev < 1:
        return None, ""
    candidates = [
        SESSIONS / ("day-%03d.json" % prev),
        SESSIONS / ("day-%d.json" % prev),
        SESSIONS / "summary.json",
        SESSIONS / "session-log.jsonl",
    ]
    for c in candidates:
        if not c.exists():
            continue
        if c.suffix == ".jsonl":
            try:
                lines = [ln for ln in c.read_text(encoding="utf-8").splitlines() if ln.strip()]
                if lines:
                    return json.dumps(json.loads(lines[-1]), ensure_ascii=False)[:600], \
                        "sessions/%s 末行" % c.name
            except (OSError, json.JSONDecodeError):
                return "（%s 末行解析失败）" % c.name, "sessions/%s" % c.name
        else:
            obj, err = read_json(c)
            if obj is not None:
                return brief_scalar(obj), "sessions/%s" % c.name
    return None, ""


# ---------------------------------------------------------------------------
# 汇总 + 渲染
# ---------------------------------------------------------------------------
def gather(day: int):
    lesson, lesson_note = read_lesson(day)
    db = read_db(day)
    stu = read_student()
    sess_sum, sess_src = read_sessions_summary(day)

    notes = []
    if lesson is None:
        notes.append("课程未就绪：%s（该文件由别的任务生成，本脚本不创建、不编造）。" % lesson_note)
    if not db["exists"]:
        notes.append("状态库未就绪：%s。" % db["reason"])
    elif db["reason"]:
        notes.append("状态库查询异常：%s。" % db["reason"])
    if not 1 <= day <= 80:
        notes.append("day=%d 超出 1–80 计划范围，请确认天数。" % day)

    # 到期复习：优先状态库，其次只读镜像
    if db["due_ok"]:
        due, due_src, due_note = db["due"], "data/state.db", db["due_note"]
    elif stu["due"]:
        due, due_src, due_note = stu["due"], "student/*.json（只读镜像）", "来自只读镜像；权威队列以 nh80.py 为准"
    else:
        due, due_src, due_note = [], "无", db["due_note"] or "无可用到期队列数据"

    # 最近错题：优先状态库，其次只读镜像
    if db["errors_ok"]:
        errors, errors_src, errors_note = db["errors"], "data/state.db", db["errors_note"]
    elif stu["errors"]:
        errors, errors_src, errors_note = stu["errors"], "student/*.json（只读镜像）", "来自只读镜像"
    else:
        errors, errors_src, errors_note = [], "无", db["errors_note"] or "无可用错题数据"

    # 上一日总结：状态库 > 只读镜像 > sessions/
    if db["summary"]:
        summary, summary_src = db["summary"], db["summary_source"]
    elif stu["summary"]:
        summary, summary_src = stu["summary"], stu["summary_source"]
    elif sess_sum:
        summary, summary_src = sess_sum, sess_src
    else:
        summary, summary_src = None, ""

    return {
        "day": day, "lesson": lesson, "lesson_note": lesson_note, "notes": notes,
        "db": db, "student_files": stu["files"],
        "due": due, "due_src": due_src, "due_note": due_note,
        "errors": errors, "errors_src": errors_src, "errors_note": errors_note,
        "summary": summary, "summary_src": summary_src,
    }


def render_list(items, empty_text):
    if not items:
        return "- %s" % empty_text
    return "\n".join("- %s" % x for x in items)


def build_prompt(g) -> str:
    day = g["day"]
    db = g["db"]
    lines = []
    A = lines.append

    A("# Nihongo 80 · Day %d 独立会话开场提示词" % day)
    A("")
    A("> 由 `scripts/new_session_prompt.py` 生成，复制到 WorkBuddy **新建独立会话**。")
    A("> 这是全新会话：平台不会自动把昨日教学状态传进来，一切以项目文件为准。")
    A("> 本提示词只读生成，未写入任何状态；缺失数据已标注，不含编造内容。")
    A("")

    # 0. 数据来源状态
    A("## 0. 数据来源状态（先读，含降级提示）")
    A("")
    A("- 项目根 ROOT：`%s`（以下命令均在 ROOT 下执行）" % ROOT)
    if g["lesson"] is not None:
        A("- `curriculum/curriculum.json`：可用（已找到 day=%d）" % day)
    else:
        A("- `curriculum/curriculum.json`：未就绪 —— %s" % g["lesson_note"])
    if db["exists"]:
        tnames = ", ".join(db["tables"]) if db["tables"] else "（无表）"
        A("- `data/state.db`：可用（只读查询；表：%s）" % tnames)
    else:
        A("- `data/state.db`：未就绪 —— %s" % db["reason"])
    if g["student_files"]:
        A("- `student/*.json`：发现 %d 个文件（%s）" % (
            len(g["student_files"]), ", ".join(g["student_files"])))
    else:
        A("- `student/*.json`：无文件（只读镜像，通常由 start-day / finish-day 流程生成）")
    A("- `sessions/`：上一日总结来源之一（存在则读取，缺失不影响运行）")
    A("")
    if g["notes"]:
        A("[降级提示] 本提示词存在未就绪数据，请勿据此编造课程 / 复习 / 错题 / 总结：")
        for n in g["notes"]:
            A("  - %s" % n)
        A("  处理：先在本地运行 `python3 scripts/nh80.py start-day %d`；"
          "`curriculum.json` 由对应任务生成后再重新运行 "
          "`python3 scripts/new_session_prompt.py %d` 得到完整提示词。" % (day, day))
    else:
        A("[数据来源状态] 主要数据源已就绪；仍以脚本 / 文件为唯一真源，不依赖平台记忆。")
    A("")

    # 1. 绝对路径清单
    A("## 1. 先读（绝对路径清单，按顺序）")
    A("")
    for label, parts in [
        ("项目总入口", ["AGENTS.md"]),
        ("数据契约（重点 §0/§10/§11/§12/§13/§14）", ["CONTRACTS.md"]),
        ("平台能力核实结论 §6", ["research", "platform_capabilities.md"]),
        ("学习科学可执行逻辑", ["research", "learning_science.md"]),
        ("每日教师（本会话主体）", ["agents", "teacher.md"]),
        ("复习官（复习块 / 归因）", ["agents", "reviewer.md"]),
        ("考官（当天 assessment != none 时）", ["agents", "examiner.md"]),
        ("教学总监（周度参考）", ["agents", "director.md"]),
        ("课程真源", ["curriculum", "curriculum.json"]),
        ("只读状态镜像", ["student"]),
        ("唯一可写真源（只读查询）", ["data", "state.db"]),
        ("当日页面数据（可选）", ["web", "data", "day-%03d.json" % day]),
        ("每日闭环手册", ["docs", "DAILY_SESSION.md"]),
    ]:
        A("- `%s` —— %s" % (rel(*parts), label))
    A("")
    A("读状态用文件读取能力直接读上述路径；**不要用平台记忆 / 聊天历史当数值依据**")
    A("（FSRS 的 D/S/R/due 等精确数值不进记忆，平台也不自动传递每日状态）。")
    A("")

    # 2. 今日目标
    A("## 2. 今日目标（Day %d）" % day)
    A("")
    A(render_lesson(g["lesson"]))
    A("")

    # 3. 预算
    A("## 3. 预算")
    A("")
    A("- 每天 60 分钟；默认结构：10 复习 / 20 新知 / 15 听说读互动 / 10 测验 / 5 反馈记录。")
    A("- 可随当天 assessment 动态调整，但一周内听 / 说 / 读 / 写 / 词汇 / 语法各项能力都要训练到。")
    A("- 同一天多个测试合并为一个 assessment，总时长不超过 60 分钟（见 agents/examiner.md）。")
    A("- 不砍学生独立产出；不把「读完 AI 内容 / 页面」当完成，必须有 attempts 记录。")
    A("")

    # 4. 到期复习
    A("## 4. 到期复习（FSRS 队列）")
    A("")
    A("- 来源：%s" % g["due_src"])
    A("- 说明：%s" % g["due_note"])
    if g["due"]:
        A(render_list(
            ["%s | due=%s | stage=%s" % (d["id"], d["due"], d["stage"] or "-") for d in g["due"][:10]],
            "（无到期项）"))
        A("- 复习策略见 `agents/reviewer.md`：先答后揭示、产出式；交错只用于易混语法/助词/变形，词汇汉字走分块+SRS。")
    else:
        A("- 未取得到期项或队列为空；若属「未就绪」，按第 0 节降级提示处理，不要自行编造。")
    A("")

    # 5. 最近错题
    A("## 5. 最近错题（error_type）")
    A("")
    A("- 来源：%s；%s" % (g["errors_src"], g["errors_note"]))
    if g["errors"]:
        A(render_list(
            ["qid=%s | error_type=%s | %s" % (e["qid"] or "-", e["error_type"], e["ts"])
             for e in g["errors"][:10]],
            "（无错题记录）"))
        A("- 答错必须归因到 `CONTRACTS.md` §12 具体类别；补救映射见 `agents/reviewer.md`。")
    else:
        A("- 未取到错题或暂无错题；若属「未就绪」，按第 0 节降级提示处理，不要自行编造。")
    A("")

    # 6. 上一日总结
    A("## 6. 上一日总结")
    A("")
    if g["summary"]:
        A("- 来源：%s" % g["summary_src"])
        A("```")
        A(g["summary"])
        A("```")
    elif day == 1:
        A("- Day 1 为首日，无上一日总结；若 `assessment=diagnostic`，按 `agents/examiner.md` 做摸底。")
    else:
        A("- 未读到上一日总结（数据未就绪）。按第 0 节降级提示处理；不要凭聊天历史杜撰昨日进度。")
    A("")

    # 7. 会话中必须调用的命令
    A("## 7. 会话中必须调用 / 遵守的命令（均在 ROOT 下执行）")
    A("")
    A("1. 读状态：直接读第 1 节绝对路径清单；不依赖平台记忆。")
    A("2. 网页结果写回（必须）：把页面给出的 `NH80R1.<base64url>` 回传码原样交回本会话并运行：")
    A("   `python3 scripts/nh80.py import-web-result '<回传码>'`")
    A("   该命令做结构校验、按 `session+qid` 幂等去重、写 `attempts` 并触发 FSRS 排期；"
      "手写 / 篡改 / 未知 qid / 重复导入的码会被拒绝（CONTRACTS.md §10）。")
    A("3. 会话内口头 / 文本作答：AI 只输出「rating 建议 / error_type / 讲解措辞」，"
      "状态数值一律经 `scripts/nh80.py` 写入；不直接改 `data/state.db` 或 `student/*.json`。")
    A("4. 契约已定义的命令字（不要改写、不要臆造未列出的子命令）：")
    A("   - `python3 scripts/nh80.py start-day %d`（本地，会话前已执行）" % day)
    A("   - `python3 scripts/new_session_prompt.py %d`（本地，生成本提示词）" % day)
    A("   - `python3 scripts/nh80.py import-web-result '<码>'`（会话内）")
    A("   - `python3 scripts/nh80.py finish-day %d`（会话末，见第 8 节）" % day)
    A("")

    # 8. 结束时必须回写
    A("## 8. 结束时必须回写（否则次日读不到今日）")
    A("")
    A("- `python3 scripts/nh80.py finish-day %d`" % day)
    A("  落盘当日总结 / 进度 / `audit_log`；未执行则当日作答不计入可读状态。")
    A("- `student/*.json` 只读镜像由 `start-day` / `finish-day` 流程经 `export_state` 刷新；本会话不手改镜像。")
    A("- 次日：新建独立会话，重跑第 7 节第 4 条前两条命令，从文件读昨日记录（见 `docs/DAILY_SESSION.md`）。")
    A("")

    # 9. 教学硬规则
    A("## 9. 教学硬规则（摘要，详见 agents/teacher.md）")
    A("")
    for rule in [
        "先思考再揭示答案：作答前不渲染选项/答案/词表，产出式主动回忆（mode=produce）。",
        "必须有足够学生独立输出；不把「读完 AI 内容 / 页面」当完成，必须有 attempts 记录。",
        "逐步讲解；用故事 / 角色扮演 / 情境推理；场景覆盖生活、科技、旅行、工作。",
        "中国学习者专项：は/が、を/に、动词变形、汉字音读、敬体简体、汉字词望文生义。",
        "连续答对提高难度，但掌握判定由脚本（一次答对最多到 independent_recall）。",
        "答错归因到具体 error_type（§12 九类）；反馈三要素（目标/当前/下一步）。",
        "不靠夸奖制造虚假成就感；不降低测试难度；进度落后只减内容/补基础/调任务。",
        "AI 不写状态数值；不声称平台自动传递状态或自动调度教学。",
    ]:
        A("- %s" % rule)
    A("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="生成 Day N 的 WorkBuddy 独立会话开场提示词（只读、纯标准库、容错）。"
    )
    ap.add_argument("day", type=int, help="天数，例如 1")
    args = ap.parse_args()
    try:
        g = gather(args.day)
        print(build_prompt(g))
    except Exception as e:  # 兜底：任何意外都不崩溃，给出明确降级提示
        print("# Nihongo 80 · Day %d 开场提示词（降级）" % args.day)
        print("")
        print("[降级提示] 生成完整提示词时发生异常：%s: %s" % (type(e).__name__, e))
        print("本脚本未编造任何课程 / 复习 / 错题 / 总结数据。")
        print("请先确认已运行 `python3 scripts/nh80.py start-day %d`，"
              "且 `curriculum/curriculum.json` 已由对应任务生成。" % args.day)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
