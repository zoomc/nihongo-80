#!/usr/bin/env python3
"""progress_read.py — 读取 Nihongo-80 云端「当天完成快照」并生成复习摘要。

只做一件事：带 X-NH80-Key 发 GET /api/progress，把结果渲染成人类可读摘要
（或 --json 原样输出）。任何能跑 Python 3 的 agent 都能用，无需依赖、

无需安装、不改任何文件、不回写本机状态。

    python3 scripts/progress_read.py --latest          # 最近 7 天
    python3 scripts/progress_read.py --latest 3        # 最近 3 天
    python3 scripts/progress_read.py --day 47
    python3 scripts/progress_read.py --day 47 --json
    python3 scripts/progress_read.py --latest --base https://nihongo80-preview.cmjfire.workers.dev

重要边界：云端 study_progress 是**网页「完成」按钮自报的当天快照**，
questions[].correct / accuracy 由客户端自算，服务端不重判、整体标 self_reported=1。
它**不是掌握判定的权威**；唯一权威是本机 data/state.db（只经
`python3 scripts/nh80.py finish-day` 写入）。本脚本只读，不据此推进完成或判掌握。

密钥：默认读 <repo>/deploy/.sync-key（gitignore，不入库、不打印）；
也可用 --key 或环境变量 NH80_SYNC_KEY。密钥绝不出现在输出或错误信息里。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE = "https://nihongo80.cmjfire.workers.dev"
DEFAULT_KEY_FILE = ROOT / "deploy" / ".sync-key"
DEFAULT_LATEST = 7
MAX_LIMIT = 120

EXIT_OK = 0
EXIT_ARG = 2
EXIT_HTTP = 3
EXIT_EMPTY = 4


class ProgressError(Exception):
    def __init__(self, reason: str, detail: str = "", status: int = 0):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail
        self.status = status


def emit(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def fail(reason: str, detail: str = "") -> dict:
    payload = {"ok": False, "reason": reason}
    if detail:
        payload["detail"] = detail
    return payload


# ---------------------------------------------------------------------------
# 密钥 / HTTP
# ---------------------------------------------------------------------------

def load_key(explicit: str | None) -> str:
    """按 --key > 环境变量 > deploy/.sync-key 顺序取密钥；返回空串表示缺失。"""
    if explicit and explicit.strip():
        return explicit.strip()
    env = os.environ.get("NH80_SYNC_KEY", "").strip()
    if env:
        return env
    try:
        return DEFAULT_KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def fetch(base: str, key: str, params: dict, timeout: float = 20.0) -> dict:
    url = "%s/api/progress?%s" % (base.rstrip("/"), urllib.parse.urlencode(params))
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "X-NH80-Key": key,
            "User-Agent": "nh80-progress-read/1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        reason = "http_%d" % e.code
        try:
            parsed = json.loads(e.read().decode("utf-8", "replace"))
            if isinstance(parsed, dict) and parsed.get("reason"):
                reason = str(parsed["reason"])
        except (ValueError, OSError):
            pass
        # 只回显服务端 reason，绝不回显请求头/密钥。
        raise ProgressError(reason, "GET /api/progress 失败", e.code) from None
    except urllib.error.URLError as e:
        raise ProgressError("network_error", str(e.reason)) from None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ProgressError("bad_response", "响应不是合法 JSON") from None
    if not isinstance(data, dict):
        raise ProgressError("bad_response", "响应不是 JSON 对象") from None
    return data


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

def _day(value) -> str:
    try:
        return "%03d" % int(value)
    except (TypeError, ValueError):
        return "???"


def _str_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    return []


def _uniq(seq) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        s = str(x)
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def render_one(item: dict) -> str:
    day = item.get("day")
    completed_at = item.get("completed_at") or "（未提供）"
    server_ts = item.get("server_ts") or "（未知）"
    accuracy = item.get("accuracy")
    required = _str_list(item.get("required_ids"))
    extra = _str_list(item.get("extra_ids"))
    grammar = _str_list(item.get("grammar_ids"))
    questions = item.get("questions") if isinstance(item.get("questions"), list) else []
    wrong = item.get("wrong_summary") if isinstance(item.get("wrong_summary"), list) else []
    self_rating = item.get("self_rating") if isinstance(item.get("self_rating"), dict) else {}
    note = str(item.get("note") or "").strip()

    lines = [
        "# Day %s 学习进度（云端自报 · 非权威）" % _day(day),
        "",
        "- 完成时间：%s（server_ts：%s）" % (completed_at, server_ts),
        "- 自报正确率：%s（客户端自算；权威以本机 finish-day 为准）"
        % ("%s" % accuracy if isinstance(accuracy, (int, float)) else "—"),
        "- 当天范围：必学 %s ｜ 拓展 %s ｜ 语法 %s"
        % ("、".join(required) or "—", "、".join(extra) or "—", "、".join(grammar) or "—"),
        "- 数据标记：self_reported=%s（服务端不采信客户端 correct 为权威）"
        % item.get("self_reported", 1),
    ]

    # 错题（wrong_summary 为主，补充 questions 里自报答错/被提示的题）
    wrong_lines: list[str] = []
    wrong_kids: list[str] = []
    for w in wrong:
        if not isinstance(w, dict):
            continue
        qid = str(w.get("qid") or "?")
        kids = _str_list(w.get("knowledge_ids"))
        wrong_kids.extend(kids)
        wrong_lines.append("  - %s → %s" % (qid, "、".join(kids) or "—"))
    self_wrong = [str(q.get("qid")) for q in questions
                  if isinstance(q, dict) and q.get("correct") is False]
    hinted = [str(q.get("qid")) for q in questions
              if isinstance(q, dict) and (q.get("hinted") is True or q.get("revealed") is True)]
    lines.append("- 错题（%d 条）：" % len(wrong_lines))
    lines.extend(wrong_lines or ["  - （无错题摘要）"])
    if self_wrong:
        lines.append("  - 自报答错：%s" % "、".join(_uniq(self_wrong)))
    if hinted:
        lines.append("  - 用提示/看答案：%s" % "、".join(_uniq(hinted)))

    # 自评
    lines.append("- 自评：")
    if self_rating:
        for kid, rating in self_rating.items():
            lines.append("  - %s：%s" % (kid, rating))
    else:
        lines.append("  - （无自评）")

    # 复习重点：错题优先 + 自评 again/hard 优先 + 当天新词/语法
    bad_self = [k for k, v in self_rating.items() if str(v) in ("again", "hard")]
    new_ids = _uniq(required + extra + grammar)
    lines.append("- 复习重点（供当天家教会话）：")
    lines.append("  1. 错题优先：%s" % ("、".join(_uniq(wrong_kids)) or "—"))
    lines.append("  2. 自评 again/hard 优先：%s" % ("、".join(_uniq(bad_self)) or "—"))
    lines.append("  3. 当天新词/语法回顾：%s" % ("、".join(new_ids) or "—"))

    if note:
        lines.append("- 备注：%s" % note)
    lines.append("")
    lines.append("（数据来源：云端自报 / 本机 SQLite 权威；不据此推进完成或判掌握）")
    return "\n".join(lines)


def render(items: list) -> str:
    if not items:
        return "（云端暂无进度数据）"
    return "\n\n".join(render_one(it) if isinstance(it, dict) else str(it) for it in items)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="progress_read.py",
        description="读取 Nihongo-80 云端当天完成快照（自报、非权威），输出复习摘要。",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--day", type=int, metavar="N", help="读取指定 Day（新版 1..100，兼容旧版至 120）")
    group.add_argument("--latest", nargs="?", const=DEFAULT_LATEST, type=int,
                       metavar="N", help="读取最近 N 天（默认 %d，最大 %d）" % (DEFAULT_LATEST, MAX_LIMIT))
    parser.add_argument("--base", default=DEFAULT_BASE, help="站点根地址（默认 production）")
    parser.add_argument("--key", default=None,
                        help="X-NH80-Key；默认读 deploy/.sync-key 或环境变量 NH80_SYNC_KEY（不打印）")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="原样输出服务端 JSON 结构（供其它程序解析）")
    args = parser.parse_args(argv)

    if args.day is not None and not (1 <= args.day <= MAX_LIMIT):
        emit(fail("bad_day", "--day 需在 1..%d" % MAX_LIMIT))
        return EXIT_ARG
    if args.latest is not None and not (1 <= args.latest <= MAX_LIMIT):
        emit(fail("bad_limit", "--latest 需在 1..%d" % MAX_LIMIT))
        return EXIT_ARG

    key = load_key(args.key)
    if not key:
        emit(fail("no_key", "需要 --key、环境变量 NH80_SYNC_KEY，或 deploy/.sync-key"))
        return EXIT_ARG

    params = {"day": args.day} if args.day is not None else {"latest": 1, "limit": args.latest}
    try:
        data = fetch(args.base, key, params)
    except ProgressError as e:
        emit(fail(e.reason, e.detail))
        return EXIT_HTTP

    if not data.get("ok"):
        emit(fail(str(data.get("reason") or "bad_response")))
        return EXIT_HTTP

    if args.as_json:
        emit(data)
    else:
        print(render(data.get("items") if isinstance(data.get("items"), list) else []))

    items = data.get("items")
    return EXIT_OK if isinstance(items, list) and items else EXIT_EMPTY


if __name__ == "__main__":
    sys.exit(main())
