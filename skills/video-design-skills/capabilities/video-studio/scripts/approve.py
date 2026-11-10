#!/usr/bin/env python3
"""approve.py — 由**用户本人**在终端里确认「故事 / 提示词」，写入审批记录。

为什么要有这个脚本：分镜里的 `meta.review` 是模型写的，模型自己填 true 就绕过去了。
这个脚本只有真人在终端里能跑完——AI 的 shell 没有 TTY，`input()` 拿不到人，直接退出。
审批记录还带**内容指纹**：审批之后改任何一句提示词，指纹就对不上，门禁会把审批判为失效。

用法（用户自己在终端里跑，不是让 AI 跑）：
    python3 scripts/approve.py --file output/2026-11-10-xxx/storyboard.json
    python3 scripts/approve.py --file ... --stage story     # 只审故事
    python3 scripts/approve.py --file ... --stage prompts   # 只审提示词

退出码：0 = 已记录审批，1 = 用户取消，3 = 用法错误 / 没有真终端
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _review import content_hash  # noqa: E402

CONFIRM_WORDS = {"可以", "好", "确认", "ok", "OK"}
STAGES = {"story": "story_approved", "prompts": "prompts_approved"}


def excerpt(text: str, n: int = 46) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n] + "…"


def main() -> int:
    ap = argparse.ArgumentParser(description="用户本人确认分镜 / 提示词")
    ap.add_argument("--file", required=True, help="storyboard.json 路径")
    ap.add_argument("--stage", choices=("story", "prompts", "both"), default="both")
    args = ap.parse_args()

    path = pathlib.Path(args.file).expanduser()
    if not path.is_file():
        print(f"找不到文件：{path}")
        return 3

    if not sys.stdin.isatty():
        print("✗ 这里不是真终端，不能替你点通过。")
        print("  请用户自己在终端里执行：")
        print(f"    python3 {sys.argv[0]} --file {args.file}")
        print("  （AI 的 shell 没有 TTY，跑不了这个脚本——这是故意的）")
        return 3

    data = json.loads(path.read_text(encoding="utf-8"))
    meta = data.get("meta") or {}
    shots = data.get("shots") or []
    h = content_hash(data)

    print("=" * 60)
    print(f"待确认：{path.name}")
    print(f"平台 {meta.get('platform', '?')} · 时长 {meta.get('duration', '?')} 秒 · "
          f"{len(shots)} 镜 · 风格 {meta.get('style', '?')}")
    print(f"风格锚：{excerpt(data.get('style_anchor', ''), 60)}")
    for s in shots:
        tag = "静音" if s.get("silent") else "有台词"
        print(f"  {s.get('id', '?')}  {s.get('duration', '?')}s  [{tag}]  {excerpt(s.get('prompt', ''))}")
    print(f"内容指纹：{h[:16]}…")
    print("=" * 60)
    print("确认这些内容你已经看过、可以进入下一步？")
    print("（审批后若再改提示词，指纹会变，这次审批自动失效，需要重审）")

    try:
        answer = input("输入「可以」确认，其他任意内容取消：").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消，没有写入任何审批记录。")
        return 1

    if answer not in CONFIRM_WORDS:
        print("已取消，没有写入任何审批记录。")
        return 1

    review = meta.get("review")
    if not isinstance(review, dict):
        review = {}
    stages = STAGES.keys() if args.stage == "both" else (args.stage,)
    for stage in stages:
        review[STAGES[stage]] = True
    review["content_hash"] = h
    review["approved_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    review["approved_by"] = "user-tty"
    meta["review"] = review
    data["meta"] = meta

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n✓ 已记录审批：{', '.join(stages)}（指纹 {h[:16]}…）")
    print("  改任何提示词后请重跑本脚本，否则门禁会报「审批后内容被改过」。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
