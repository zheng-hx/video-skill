#!/usr/bin/env python3
"""reconcile-skills.py — 把工作台里的技能注册到本机 AI 工具的 skills 目录。

只对**已经存在**的工具目录动手；不存在的不建空目录。
同名冲突时：指向我们的就更新，指向别处的报冲突不动。

用法：
    python3 scripts/reconcile-skills.py
    python3 scripts/reconcile-skills.py --dry-run
    python3 scripts/reconcile-skills.py --workdir ~/somewhere

退出码：0 = 成功（允许无工具），1 = 有冲突，3 = 用法错误
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
TOOL_DIRS = PKG / "tool-dirs.json"
DEFAULT_WB = Path.home() / ".video-design"


def load_targets() -> list[dict]:
    return json.loads(TOOL_DIRS.read_text(encoding="utf-8"))["targets"]


def link(target: Path, src: Path, mode: str) -> str:
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)
    if mode == "copy":
        shutil.copytree(src, target)
        return "copied"
    try:
        target.symlink_to(src, target_is_directory=True)
        return "linked"
    except OSError:
        shutil.copytree(src, target)
        return "copied (symlink failed)"


def main() -> int:
    ap = argparse.ArgumentParser(description="注册技能到 AI 工具目录")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--workdir", default=str(DEFAULT_WB), help="工作台目录")
    ap.add_argument("--tool", default="", help="只装到指定工具（label 或目录）")
    ap.add_argument("--all", action="store_true", help="装到所有探测到的工具")
    ap.add_argument("--list", action="store_true", help="只探测，不安装")
    args = ap.parse_args()

    wb = Path(os.path.expanduser(args.workdir))
    skills_src = wb / "skills"
    if not skills_src.is_dir():
        print(f"工作台还没渲染：{skills_src}")
        print("先跑 render-package.py")
        return 3

    skills = sorted(d for d in skills_src.iterdir() if d.is_dir())
    if not skills:
        print("工作台里没有技能")
        return 3

    available = []
    for t in load_targets():
        raw = os.path.expanduser(t["dir"])
        if Path(raw).is_dir():
            available.append(t)
        else:
            print(f"  {t['label']}: 没装（跳过 {raw}）")

    if args.list:
        print(f"\n探测到 {len(available)} 个可用的工具目录：")
        for t in available:
            print(f"  - {t['label']}: {t['dir']}")
        print("\n用 --tool <label> 选一个，或 --all 全装")
        return 0

    if args.tool:
        chosen = [t for t in available
                  if args.tool.lower() in (t["label"].lower(), t["dir"].lower())]
        if not chosen:
            print(f"找不到工具：{args.tool}")
            print("可用的：" + ", ".join(t["label"] for t in available))
            return 3
    elif args.all:
        chosen = available
    else:
        chosen = available[:1]

    found = 0
    conflicts: list[str] = []
    for t in chosen:
        label = t["label"]
        raw = os.path.expanduser(t["dir"])
        tool_dir = Path(raw)
        print(f"  {label}: {raw}")
        for src in skills:
            target = tool_dir / src.name
            if target.is_symlink() and target.resolve() == src.resolve():
                print(f"    {src.name}: 已就绪")
                continue
            if target.exists() and not target.is_symlink():
                if target.is_dir() and (target / "SKILL.md").is_file():
                    conflicts.append(f"{label}/{src.name}")
                    print(f"    {src.name}: ⚠️ 已存在且不是我们的软链，跳过")
                    continue
            if args.dry_run:
                print(f"    {src.name}: would {t.get('mode', 'symlink')}")
                continue
            act = link(target, src, t.get("mode", "symlink"))
            print(f"    {src.name}: {act}")

    if found == 0:
        print("\n没探测到任何 AI 工具的技能目录。")
        print("把 SKILL.md 内容贴进你的 AI 工具的系统提示词也能用。")
    elif not args.all and not args.tool:
        others = [t["label"] for t in available[1:]]
        if others:
            print(f"\n只装了 {chosen[0]['label']}。要装全部加 --all，只列可用工具加 --list。")

    if conflicts:
        print(f"\n{len(conflicts)} 处冲突（同名但不是我们装的）：")
        for c in conflicts:
            print(f"  - {c}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
