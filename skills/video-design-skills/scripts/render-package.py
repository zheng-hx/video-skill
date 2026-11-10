#!/usr/bin/env python3
"""render-package.py — 把 capabilities/ 里的技能渲染到用户工作台。

    ~/.video-design/
    ├── video.json
    └── skills/
        ├── copy-video-studio/
        └── video-studio/

用法：
    python3 scripts/render-package.py            # 渲染（已是最新就跳过）
    python3 scripts/render-package.py --force    # 强制重渲染
    python3 scripts/render-package.py --dry-run  # 只看会做什么
    python3 scripts/render-package.py --workdir ~/somewhere

退出码：0 = 成功，1 = 有问题，3 = 用法错误
"""
from __future__ import annotations

import argparse
import hashlib
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


def default_workbench() -> Path:
    """工作台位置以 tool-dirs.json 的 workbench 为准，配置缺失才回退默认值。"""
    cfg = PKG / "tool-dirs.json"
    if cfg.is_file():
        try:
            raw = json.loads(cfg.read_text(encoding="utf-8")).get("workbench", "")
            if raw:
                return Path(os.path.expanduser(raw))
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_WB


def content_fingerprint() -> str:
    """capabilities/ 的内容指纹：版本号不变、内容变了也能识别出来。"""
    h = hashlib.sha256()
    for path in sorted(CAPS.rglob("*")):
        if path.is_dir() or path.name in SKIP or "__pycache__" in path.parts:
            continue
        if path.suffix == ".pyc":
            continue
        h.update(path.relative_to(CAPS).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


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
    ap.add_argument("--workdir", default="", help="工作台目录（默认读 tool-dirs.json 的 workbench）")
    args = ap.parse_args()

    wb = Path(os.path.expanduser(args.workdir)) if args.workdir else default_workbench()
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

    # 已装版本：与当前包相同才跳过；不同（升级/降级）就覆盖技能目录，用户的 output/ 不动
    fingerprint = content_fingerprint()
    installed_ver = ""
    installed_fp = ""
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            installed_ver = manifest.get("version", "")
            installed_fp = manifest.get("contentHash", "")
        except (json.JSONDecodeError, OSError):
            pass
    if installed_ver and installed_ver != ver:
        print(f"已装版本：{installed_ver}（将覆盖为 {ver}）")
    elif installed_ver and installed_fp != fingerprint:
        print("版本没变，但技能内容变了（将覆盖）—— 防止「改了没生效」")

    if not args.dry_run:
        skills_dst.mkdir(parents=True, exist_ok=True)

    actions: dict[str, str] = {}
    for d in dirs:
        dst = skills_dst / d.name
        if dst.exists() and not args.force and installed_ver == ver and installed_fp == fingerprint:
            actions[d.name] = "skipped (same version + same content)"
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
            "contentHash": fingerprint,
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
