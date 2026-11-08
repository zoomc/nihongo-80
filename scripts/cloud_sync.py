#!/usr/bin/env python3
"""cloud_sync.py — 把 Cloudflare D1 里的网页原始作答事件拉回本地 SQLite。

流程（docs/REVISION_CONTRACT.md 第 10 节）：

    GET /api/events?since=<id>   （需 X-NH80-Key）
        └─ 按 (day, session) 聚合为 NH80R1 等价 payload
             └─ 交给 scripts/nh80.py 的 cmd_import_web 导入（同一套幂等与判分）

硬约束：
- 只把 answer / hinted / seconds 交给导入路径，**不带 correct**；判分由本地
  `learning.grade_objective()` 依据题库标准答案完成（不信任任何客户端/服务端结论）。
- 幂等：本地 attempts 由 session+qid 去重，重复 pull 不会重复记分，因此默认 since=0 全量拉取即可。
- 断网 / 401 / 503 一律输出 JSON 错误并以非 0 退出，绝不静默成功。

用法：
    python3 scripts/cloud_sync.py pull --base https://nihongo80.cmjfire.workers.dev \
        --key "$NH80_SYNC_KEY" --root /Users/mj/Documents/learn/jp/nihongo-80

可选：--since <id> 增量拉取；--limit 200；--max-pages 50。
"""

from __future__ import annotations

import argparse
import base64
import inspect
import json
import os
import sys
import urllib.error
import urllib.request
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

EXIT_UNAUTHORIZED = 2
EXIT_UNAVAILABLE = 3
EXIT_NETWORK = 4
EXIT_IMPORT_BLOCKED = 5
EXIT_IMPORT_FAILED = 6


def emit(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def fail(reason: str, detail: str = "", code: int = 1, **extra) -> int:
    payload = {"ok": False, "reason": reason}
    if detail:
        payload["detail"] = detail
    payload.update(extra)
    emit(payload)
    return code


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def fetch_events(base: str, key: str, since: int, limit: int, timeout: float = 20.0) -> list[dict]:
    """拉一页事件；失败抛 SyncError（带 exit code）。"""
    url = "%s/api/events?since=%d&limit=%d" % (base.rstrip("/"), since, limit)
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "X-NH80-Key": key,
            "User-Agent": "nh80-cloud-sync/1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        reason = "http_%d" % e.code
        try:
            reason = json.loads(body).get("reason") or reason
        except Exception:
            pass
        if e.code == 401:
            raise SyncError("unauthorized", "X-NH80-Key 与 Worker 的 NH80_SYNC_KEY 不一致", EXIT_UNAUTHORIZED)
        if e.code == 503:
            raise SyncError(reason or "unavailable", "Worker 未绑定 D1 或未配置 NH80_SYNC_KEY", EXIT_UNAVAILABLE)
        raise SyncError(reason, body[:300], EXIT_NETWORK if e.code >= 500 else 1)
    except urllib.error.URLError as e:
        raise SyncError("network", "无法连接 %s：%s" % (url, e.reason), EXIT_NETWORK)
    except TimeoutError:
        raise SyncError("network", "请求超时：%s" % url, EXIT_NETWORK)

    if status != 200:
        raise SyncError("http_%d" % status, raw[:300], EXIT_NETWORK)

    try:
        data = json.loads(raw)
    except Exception as e:
        raise SyncError("bad_response", "服务端返回的不是 JSON：%s" % e, 1)

    # 兼容裸数组与 {ok,events} 两种形状
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if data.get("ok") is False:
            reason = str(data.get("reason") or "server_error")
            code = EXIT_UNAUTHORIZED if reason == "unauthorized" else EXIT_UNAVAILABLE
            raise SyncError(reason, str(data.get("detail") or ""), code)
        events = data.get("events")
        if isinstance(events, list):
            return events
    raise SyncError("bad_response", "缺少 events 数组", 1)


class SyncError(Exception):
    def __init__(self, reason: str, detail: str = "", code: int = 1):
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail
        self.code = code


def pull_all(base: str, key: str, since: int, limit: int, max_pages: int) -> tuple[list[dict], int]:
    events: list[dict] = []
    cursor = since
    for _ in range(max_pages):
        page = fetch_events(base, key, cursor, limit)
        if not page:
            break
        events.extend(page)
        last = cursor
        for ev in page:
            try:
                last = max(last, int(ev.get("id") or 0))
            except (TypeError, ValueError):
                continue
        if last <= cursor:
            # 服务端未返回可用 id，避免死循环
            break
        cursor = last
        if len(page) < limit:
            break
    return events, cursor


# ---------------------------------------------------------------------------
# 事件 -> NH80R1 等价 payload
# ---------------------------------------------------------------------------

def build_payload(session_events: list[dict]) -> dict:
    """只保留 answer / hinted / seconds；**绝不放 correct**（判分在本地）。"""
    first = session_events[0]
    results = []
    for ev in session_events:
        qid = str(ev.get("qid") or "")
        if not qid:
            continue
        hinted = bool(ev.get("hinted")) or bool(ev.get("revealed"))
        seconds = ev.get("seconds")
        try:
            seconds = int(seconds) if seconds is not None else 0
        except (TypeError, ValueError):
            seconds = 0
        results.append({
            "qid": qid,
            "answer": str(ev.get("answer") or ""),
            "hinted": hinted,
            "seconds": max(0, seconds),
        })
    ts = ""
    for ev in session_events:
        if ev.get("client_ts"):
            ts = str(ev["client_ts"])
            break
    metadata = {}
    for ev in session_events:
        try:
            raw = json.loads(ev.get("session_payload") or "{}")
            if isinstance(raw, dict):
                metadata = raw
        except (ValueError, TypeError):
            continue
    return {
        "practice_mode": metadata.get("practice_mode", "teacher"),
        "review_ratings": metadata.get("review_ratings", []),
        "sentences": metadata.get("sentences", []),
        "v": 1,
        "day": int(first.get("day")),
        "session": str(first.get("session") or ""),
        "ts": ts or _now_iso(),
        "results": results,
        # events 表不存 minutes（只存作答事实），本地导入时保持 NULL 而不是伪造成 0。
        "minutes": None,
        "source": "web-sync",
    }


def encode_payload(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "NH80R1." + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def group_events(events: list[dict]) -> "OrderedDict[tuple[int, str], list[dict]]":
    grouped: "OrderedDict[tuple[int, str], list[dict]]" = OrderedDict()
    for ev in events:
        try:
            day = int(ev.get("day"))
        except (TypeError, ValueError):
            continue
        session = str(ev.get("session") or "")
        if not session:
            continue
        grouped.setdefault((day, session), []).append(ev)
    return grouped


# ---------------------------------------------------------------------------
# 导入：优先复用 nh80.cmd_import_web 的既有路径
# ---------------------------------------------------------------------------

def _nh80_supports_regrade(nh80) -> bool:
    """确认 nh80 的导入路径会**本地重判**而不是照抄客户端 correct。

    v3 的 cmd_import_web 直接把 `bool(x.get("correct"))` 写进 record_attempt，
    若云端事件不带 correct 会被判成全部错误。契约 v4 §3.2 要求改为服务端重判；
    这里只在源码里能看到重判痕迹时才放行，否则明确拒绝而不是写脏数据。
    """
    fn = getattr(nh80, "import_payload", None)
    if callable(fn):
        return True
    try:
        src = inspect.getsource(nh80.cmd_import_web)
    except (OSError, TypeError):
        return False
    # 注意：v3 里也有 `correct=None if is_open else ...` 字样，不能作为判据。
    # 只认「真正会本地重判」的痕迹：调用 grade_objective / 存在 regrade 逻辑 / 输出 regraded 字段。
    return any(token in src for token in ("grade_objective", "regrade", "regraded"))


def import_session(root: Path, payload: dict, nh80) -> dict:
    code = encode_payload(payload)
    args = argparse.Namespace(root=str(root), code=code)
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            nh80.cmd_import_web(args)
    except ValueError as e:
        raise SyncError("import_rejected", str(e), EXIT_IMPORT_FAILED)
    except Exception as e:  # sqlite / 结构错误
        raise SyncError("import_failed", "%s: %s" % (type(e).__name__, e), EXIT_IMPORT_FAILED)

    text = buf.getvalue().strip()
    if not text:
        return {"ok": True, "raw": ""}
    try:
        return json.loads(text)
    except Exception:
        return {"ok": True, "raw": text[:1000]}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_pull(args) -> int:
    root = Path(args.root).resolve() if args.root else DEFAULT_ROOT
    key = args.key or os.environ.get("NH80_SYNC_KEY", "")
    if not key:
        return fail("no_key", "需要 --key 或环境变量 NH80_SYNC_KEY；密钥只存在于 Worker secret，不在仓库里", 1)
    if not args.base:
        return fail("no_base", "需要 --base，例如 https://nihongo80.cmjfire.workers.dev", 1)

    try:
        events, cursor = pull_all(args.base, key, since=max(0, args.since), limit=args.limit,
                                  max_pages=args.max_pages)
    except SyncError as e:
        return fail(e.reason, e.detail, e.code, base=args.base)

    if not events:
        emit({"ok": True, "pulled": 0, "sessions": [], "next_since": cursor})
        return 0

    try:
        import nh80  # noqa: WPS433 — 延迟导入，避免 --help 时依赖项目数据
    except Exception as e:
        return fail("nh80_unavailable", "无法导入 scripts/nh80.py：%s" % e, EXIT_IMPORT_FAILED)

    if not _nh80_supports_regrade(nh80):
        return fail(
            "regrade_not_ready",
            "scripts/nh80.py 的 cmd_import_web 仍是 v3 行为（直接信任客户端 correct）。"
            "云端事件不含 correct，此时导入会把客观题全部误判为错。"
            "请先把 import 路径改为本地重判（REVISION_CONTRACT §3.2），或由主控接线 import_payload(root, data)。",
            EXIT_IMPORT_BLOCKED,
        )

    grouped = group_events(events)
    summary = []
    failures = []
    for (day, session), rows in grouped.items():
        payload = build_payload(rows)
        try:
            result = import_session(root, payload, nh80)
            summary.append({
                "day": day,
                "session": session,
                "events": len(rows),
                "applied": result.get("applied", []),
                "duplicates": result.get("duplicate_skipped", []),
                "open_pending": result.get("open_pending_need_ai_grade", []),
                "regraded": result.get("regraded"),
            })
        except SyncError as e:
            failures.append({"day": day, "session": session, "reason": e.reason, "detail": e.detail})

    if failures:
        emit({"ok": False, "reason": "partial_import_failed", "imported": summary,
              "failures": failures, "next_since": cursor})
        return EXIT_IMPORT_FAILED

    emit({"ok": True, "pulled": len(events), "sessions": summary, "next_since": cursor})
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="cloud_sync.py",
        description="把 D1 里的网页作答事件拉回本地 SQLite（判分/掌握只在本地完成）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("pull", help="拉取事件并导入 data/state.db")
    p.add_argument("--base", required=True, help="站点根地址，如 https://nihongo80.cmjfire.workers.dev")
    p.add_argument("--key", default="", help="与 Worker 的 NH80_SYNC_KEY 一致；也可用环境变量")
    p.add_argument("--root", default="", help="项目根目录（含 data/state.db），默认脚本上级")
    p.add_argument("--since", type=int, default=0, help="起始事件 id（不含），默认 0 全量")
    p.add_argument("--limit", type=int, default=200, help="每页条数，1..500，默认 200")
    p.add_argument("--max-pages", type=int, default=50, help="最多翻页数，默认 50")
    p.set_defaults(fn=cmd_pull)

    args = parser.parse_args(argv)
    if getattr(args, "limit", 200) < 1 or args.limit > 500:
        return fail("bad_limit", "--limit 需在 1..500", 1)
    if getattr(args, "max_pages", 1) < 1:
        return fail("bad_max_pages", "--max-pages 需 ≥ 1", 1)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
