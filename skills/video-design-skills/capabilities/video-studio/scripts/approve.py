#!/usr/bin/env python3
"""approve.py — 记录「用户看过并且说了可以」，写入带内容指纹的审批记录。

为什么要有这个脚本：`meta.review` 是模型写的，模型自己填 true 就绕过去了。
这个脚本把用户的**原话**和**内容指纹**一起写进去，模型事后改一句提示词就对不上号。

谁来跑：**技能自己跑**。用户只说「可以」，不需要开终端、不需要敲命令。
    python3 scripts/approve.py --file <storyboard.json> --chat --quote "可以，就按这个来"
    —— --quote 必须是用户原话，不许编；检查脚本会验里面有没有肯定词。

用户自己想亲自签，才让他开终端跑（可选，不是必需）：
    python3 scripts/approve.py --file <storyboard.json>
    python3 scripts/approve.py --file ... --stage story     # 只审故事
    python3 scripts/approve.py --file ... --stage prompts   # 只审提示词

退出码：0 = 已记录审批，1 = 用户取消 / 原话没有肯定词，3 = 用法错误
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _review import content_hash  # noqa: E402

CONFIRM_WORDS = {"可以", "好", "确认", "没问题", "继续", "行", "ok", "OK"}
STAGES = {"story": "story_approved", "prompts": "prompts_approved"}


def excerpt(text: str, n: int = 46) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n] + "…"


def main() -> int:
    ap = argparse.ArgumentParser(description="确认分镜 / 提示词（终端交互或对话审批）")
    ap.add_argument("--file", required=True, help="storyboard.json 路径")
    ap.add_argument("--stage", choices=("story", "prompts", "both"), default="both")
    ap.add_argument("--chat", action="store_true", help="对话宿主：不用 TTY，凭用户原话审批")
    ap.add_argument("--quote", default="", help="配合 --chat：用户说「可以」的那句原话")
    args = ap.parse_args()

    path = pathlib.Path(args.file).expanduser()
    if not path.is_file():
        print(f"找不到文件：{path}")
        return 3

    quote = (args.quote or "").strip()
    if args.chat and not quote:
        print("✗ --chat 必须带 --quote「用户的原话」，不许留空")
        return 3

    if not args.chat and not sys.stdin.isatty():
        print("✗ 这里没有真终端，读不到用户的输入。")
        print("  用户在聊天里已经说「可以」的话，带上他的原话跑：")
        print(f"    python3 {sys.argv[0]} --file {args.file} --chat --quote \"可以，就按这个来\"")
        print("  （用户没说「可以」就别跑这个脚本——那是替他点通过）")
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

    if args.chat:
        print(f"对话审批：用户原话「{quote}」")
        if not any(w in quote for w in CONFIRM_WORDS):
            print("✗ 这句原话里没有明确的肯定词（可以 / 好 / 确认 / 没问题 / 继续 / 行 / ok）")
            return 1
    else:
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
    if args.chat:
        review["approved_by"] = "user-chat"
        review["confirmed_quote"] = quote
    else:
        review["approved_by"] = "user-tty"
        review.pop("confirmed_quote", None)
    meta["review"] = review
    data["meta"] = meta

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n✓ 已记录审批：{', '.join(stages)}（指纹 {h[:16]}…）")
    print("  改任何提示词后请重跑本脚本，否则门禁会报「审批后内容被改过」。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
