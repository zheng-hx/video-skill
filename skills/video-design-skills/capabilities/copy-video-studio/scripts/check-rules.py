#!/usr/bin/env python3
"""check-rules.py — 检查规则快照是否过期。

快照放在 ~/.video-design/rules/latest.md（或 --file 指定）。
超过 --max-age 天就提醒刷新——旧清单会让文案照着旧规则写，照样被限流。

用法：
    python3 scripts/check-rules.py
    python3 scripts/check-rules.py --file assets/rules-snapshot.md --max-age 7

退出码：0 = 新鲜，1 = 过期/缺失，3 = 用法错误
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from datetime import date, datetime

DEFAULT = pathlib.Path.home() / ".video-design" / "rules" / "latest.md"
DATE_PAT = re.compile(r"抓取日期[：:]\s*(\d{4}-\d{2}-\d{2})")


def main() -> int:
    ap = argparse.ArgumentParser(description="检查规则快照新鲜度")
    ap.add_argument("--file", default="")
    ap.add_argument("--platform", default="", help="按平台找快照，如 抖音 / 快手 / 小红书 / 视频号")
    ap.add_argument("--max-age", type=int, default=7)
    args = ap.parse_args()

    if args.file:
        target = args.file
    elif args.platform:
        target = str(pathlib.Path.home() / ".video-design" / "rules" / f"{args.platform}.md")
    else:
        target = str(DEFAULT)
    p = pathlib.Path(target).expanduser()
    if not p.is_file():
        print(f"[缺失] 没有规则快照：{p}")
        print("生成文案前先刷一次：见 references/rules-refresh.md")
        return 1

    text = p.read_text(encoding="utf-8", errors="ignore")
    m = DATE_PAT.search(text)
    if not m:
        print(f"[过期] {p} 里找不到「抓取日期」，无法判断新鲜度")
        return 1

    grabbed = datetime.strptime(m.group(1), "%Y-%m-%d").date()
    age = (date.today() - grabbed).days
    if age > args.max_age:
        print(f"[过期] 快照 {age} 天前抓的（上限 {args.max_age} 天），生成前先刷新")
        return 1

    print(f"[新鲜] 快照 {age} 天前抓的，可用")
    return 0


if __name__ == "__main__":
    sys.exit(main())
