#!/usr/bin/env python3
"""render-package.py — 把 capabilities/ 里的技能渲染到用户工作台。

    ~/.video-design/
    ├── video.json
    └── skills/
        ├── copy-video-studio/
        ├── video-studio/
        ├── live-media-ops/
        └── live-media-router/

用法：
    python3 scripts/render-package.py            # 渲染（已是最新就跳过）
    python3 scripts/render-package.py --force    # 强制重渲染
    python3 scripts/render-package.py --dry-run  # 只看会做什么
    python3 scripts/render-package.py --workdir ~/somewhere

退出码：0 = 成功，1 = 有问题，3 = 用法错误
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
CAPS = PKG / "capabilities"
DEFAULT_WB = Path.home() / ".video-design"
SKIP = {"__pycache__", ".DS_Store"}


def package_version() -> str:
    p = PKG / "version.json"
    if p.is_file():
        try:
            return json.loads(p.read_text())["version"]
        except (json.JSONDecodeError, KeyError):
            pass
    return "1.0.0"


def skill_dirs() -> list[Path]:
    return sorted(d for d in CAPS.iterdir() if d.is_dir() and (d / "SKILL.md").is_file())


def render_one(src: Path, dst: Path, dry: bool) -> str:
    if dst.exists():
        if dry:
            return "would replace"
        shutil.rmtree(dst)
    if dry:
        return "would create"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*SKIP))
    return "created"


def main() -> int:
    ap = argparse.ArgumentParser(description="渲染技能到用户工作台")
    ap.add_argument("--force", action="store_true", help="已存在也覆盖")
    ap.add_argument("--dry-run", action="store_true", help="只报告，不写盘")
    ap.add_argument("--workdir", default=str(DEFAULT_WB), help="工作台目录")
    args = ap.parse_args()

    wb = Path(os.path.expanduser(args.workdir))
    skills_dst = wb / "skills"
    ver = package_version()
    manifest_path = wb / "video.json"

    if not CAPS.is_dir():
        print(f"找不到 capabilities：{CAPS}")
        return 3

    dirs = skill_dirs()
    if not dirs:
        print("capabilities/ 下没有任何技能")
        return 3

    print(f"工作台：{wb}")
    print(f"版本：{ver}")

    if not args.dry_run:
        skills_dst.mkdir(parents=True, exist_ok=True)

    actions: dict[str, str] = {}
    for d in dirs:
        dst = skills_dst / d.name
        if dst.exists() and not args.force:
            actions[d.name] = "skipped (exists)"
            continue
        actions[d.name] = render_one(d, dst, args.dry_run)

    for name, act in actions.items():
        print(f"  {name}: {act}")

    # 规则快照同步到工作台
    rules_src = CAPS / "copy-video-studio" / "assets" / "rules-snapshot.md"
    if rules_src.is_file():
        rules_dst = wb / "rules"
        if not args.dry_run:
            rules_dst.mkdir(parents=True, exist_ok=True)
            shutil.copy(rules_src, rules_dst / "latest.md")
            shutil.copy(rules_src, rules_dst / "抖音.md")
        print(f"  规则快照: {'would copy' if args.dry_run else 'copied'} → {rules_dst}")

    if not args.dry_run:
        manifest = {
            "package": "video-design-skills",
            "version": ver,
            "renderedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "workbench": str(wb),
            "skills": [d.name for d in dirs],
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n已写 {manifest_path}")

    skipped = sum(1 for a in actions.values() if a.startswith("skipped"))
    print(f"\n完成：{len(dirs)} 个技能，跳过 {skipped} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
