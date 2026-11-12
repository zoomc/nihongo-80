#!/usr/bin/env python3
"""把 skills/nh80-progress/SKILL.md 同步到全部 4 个加载位置，或校验它们一致。

为什么要这个：WorkBuddy 在不同层（用户级 / 工作区级 / 子目录）都会加载 skill，
四份一旦漂移，就会出现「PC 上能触发、换台机器不触发」的诡异问题。
源真本只有一份：nihongo-80/skills/nh80-progress/SKILL.md。

用法：
    python3 scripts/skill_sync.py --check     # 只校验，不一致退出 1（CI / release_guard 用）
    python3 scripts/skill_sync.py --write     # 以源真本覆盖其余三处
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "skills" / "nh80-progress" / "SKILL.md"

TARGETS = [
    ("repo/.workbuddy", ROOT / ".workbuddy/skills/nh80-progress/SKILL.md"),
    ("workspace/.workbuddy", ROOT.parent / ".workbuddy/skills/nh80-progress/SKILL.md"),
    ("user", Path.home() / ".workbuddy/skills/nh80-progress/SKILL.md"),
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="同步 / 校验 nh80-progress skill 的四份副本")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="只校验一致性")
    g.add_argument("--write", action="store_true", help="以源真本覆盖其余副本")
    args = ap.parse_args(argv)

    if not SOURCE.is_file():
        print("源真本缺失: %s" % SOURCE, file=sys.stderr)
        return 2

    want = digest(SOURCE)

    if args.write:
        for label, target in TARGETS:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE, target)
            print("已同步 %-20s %s" % (label, target))
        return 0

    bad = []
    for label, target in TARGETS:
        if not target.is_file():
            bad.append((label, target, "缺失"))
        elif digest(target) != want:
            bad.append((label, target, "内容不一致"))

    if bad:
        print("skill 副本与源真本不一致（源: %s）" % SOURCE.relative_to(ROOT))
        for label, target, why in bad:
            print("  - %-20s %s  [%s]" % (label, target, why))
        print("\n修复：python3 scripts/skill_sync.py --write")
        return 1

    print("skill 四份一致（sha256 %s…）" % want[:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
