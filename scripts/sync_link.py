#!/usr/bin/env python3
"""sync_link.py — 生成「打开即自动同步」的链接，把多端绑定变成点一次链接。

做三件事：
1. 本机凭证 `deploy/.sync-code`（64 位十六进制，gitignore，权限 600）不存在就生成；
2. 确保云端 `course_accounts` 里已有这个账号（没有就建一个）；
3. 输出 `https://<站点>/#s=<凭证>`。

在任意设备（手机浏览器、WorkBuddy 内置浏览器）打开这条链接一次：页面读片段里的
凭证、自动建立会话、把凭证存进该设备、再从地址栏抹掉片段。之后那台设备每次打开
都会自动同步完成日与续课位置，不需要任何设置。

    python3 scripts/sync_link.py              # 生成/复用凭证并打印链接
    python3 scripts/sync_link.py --show       # 只打印，不联网校验账号
    python3 scripts/sync_link.py --base https://nihongo80-preview.cmjfire.workers.dev

边界：链接本身就是凭证。不要贴到公开渠道、不要提交进 git。凭证不入库、不写进
TODAY.md 以外的任何生成物；服务端只存它的 SHA-256 摘要。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE_FILE = ROOT / "deploy" / ".sync-code"
DEFAULT_BASE = "https://nihongo80.cmjfire.workers.dev"
CODE_RE = re.compile(r"^[0-9a-f]{64}$")


def load_code(create: bool = False) -> str:
    """读本机凭证；create=True 时不存在就生成一个（0600，只在本机）。"""
    if CODE_FILE.is_file():
        code = CODE_FILE.read_text(encoding="utf-8").strip().lower()
        if CODE_RE.fullmatch(code):
            return code
    if not create:
        return ""
    code = secrets.token_hex(32)
    CODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CODE_FILE.write_text(code + "\n", encoding="utf-8")
    os.chmod(CODE_FILE, 0o600)
    return code


def post(base: str, path: str, payload: dict, timeout: float = 15.0):
    """POST JSON；返回 (status, body)。Worker 要求同源 Origin，这里显式补上。"""
    url = base.rstrip("/") + path
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"content-type": "application/json", "origin": base.rstrip("/"),
                 # Cloudflare 会对空 UA 返 1010；带一个明确的自助 UA 才能进门。
                 "user-agent": "nihongo80-sync/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read() or b"{}")
        except Exception:
            body = {}
        return error.code, body


def ensure_account(base: str, code: str) -> str:
    """确保云端有该账号。返回 exists / created / rate_limit / offline:<原因>。"""
    status, _ = post(base, "/api/account/login", {"code": code})
    if status == 200:
        return "exists"
    if status == 401:
        status, body = post(base, "/api/account/login", {"code": code, "create": True})
        if status == 200:
            return "created"
        if status == 409:
            return "exists"
        if status == 429:
            return "rate_limit"
        return "offline:create_%s" % status
    if status == 429:
        return "rate_limit"
    if status == 0:
        return "offline:network"
    return "offline:login_%s" % status


def link(base: str, code: str) -> str:
    return "%s/#s=%s" % (base.rstrip("/"), code)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="生成多端自动同步链接")
    parser.add_argument("--base", default=DEFAULT_BASE, help="站点根地址")
    parser.add_argument("--show", action="store_true", help="只打印链接，不联网校验账号")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    code = load_code(create=True)
    if not code:
        print("无法生成同步凭证：deploy/ 不可写。", file=sys.stderr)
        return 2

    state = "skipped" if args.show else ensure_account(args.base, code)
    url = link(args.base, code)

    if args.as_json:
        print(json.dumps({"ok": state in ("exists", "created", "skipped"),
                          "account": state, "link": url}, ensure_ascii=False, indent=2))
        return 0 if state in ("exists", "created", "skipped") else 3

    label = {"exists": "已在云端", "created": "已在云端新建", "skipped": "未校验（--show）",
             "rate_limit": "云端建号次数已达今日上限，明天再跑一次",
             "offline:network": "网络不通，先跳过校验"}.get(state, "云端校验失败（%s）" % state)
    print("同步账号：%s" % label)
    print("同步链接（等于凭证，勿外发、勿提交）：")
    print("  %s" % url)
    print()
    print("在手机或另一台电脑打开上面这条链接一次即完成绑定；之后自动同步完成日与续课位置。")
    print("已绑定的设备可在网页「多端同步」里点「复制同步链接」再取一次。")
    return 0 if state in ("exists", "created", "skipped") else 3


if __name__ == "__main__":
    raise SystemExit(main())
