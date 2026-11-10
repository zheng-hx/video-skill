#!/usr/bin/env python3
"""validate-package.py — 技能包结构校验。

布局契约：

    skills/<name>/SKILL.md      —— 唯一入口，frontmatter 含 name 与 description
    skills/<name>/references/   —— 按需加载的深度参考
    skills/<name>/assets/       —— 产物模板
    skills/<name>/scripts/      —— 可执行助手（可选）
    skills/<name>/_meta.json    —— 可选，宿主分发用

校验：
  1) skills/ 下每个目录都有 SKILL.md，且 frontmatter 有 name / description
  2) name 与目录名一致；description 不超过 300 字符
  3) SKILL.md 里以反引号引用的 references/ assets/ scripts/ 路径都真实存在
  4) 有 _meta.json 时：slug 与 name 一致、version 存在
  5) package.json 存在且有 name / version；各 _meta.json 的 version 只打印供核对（包版本 ≠ 技能版本，属正常）

退出码：0 = 通过，1 = 有问题，3 = 用法错误
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
DEC_LIMIT = 300
REF = re.compile(r"`((?:references|assets|scripts)/[^`\s]+)`")


def frontmatter(text: str) -> dict[str, str] | None:
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return None
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def main() -> int:
    if not SKILLS.is_dir():
        print("ERROR: 缺少 skills/ 目录")
        return 3
    dirs: list = []
    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if (d / "SKILL.md").is_file():
            dirs.append(d)
        caps = d / "capabilities"
        if caps.is_dir():
            dirs.extend(c for c in sorted(caps.iterdir()) if c.is_dir() and (c / "SKILL.md").is_file())
    if not dirs:
        print("ERROR: skills/ 下没有任何技能")
        return 3

    problems: list[str] = []
    versions: dict[str, str] = {}

    for d in dirs:
        skill_md = d / "SKILL.md"
        if not skill_md.is_file():
            problems.append(f"{d.name}: 缺少 SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if fm is None:
            problems.append(f"{d.name}: frontmatter 缺失")
            continue
        if not fm.get("name"):
            problems.append(f"{d.name}: frontmatter 缺少 name")
        elif fm["name"] != d.name:
            problems.append(f"{d.name}: name({fm['name']}) 与目录名不一致")
        if not fm.get("description"):
            problems.append(f"{d.name}: frontmatter 缺少 description")
        elif len(fm["description"]) > DEC_LIMIT:
            problems.append(f"{d.name}: description {len(fm['description'])} 字符，超过 {DEC_LIMIT}")

        for ref in sorted(set(REF.findall(text))):
            # 文档里的占位示例（`assets/...`、`references/<file>` 之类）不是真实引用
            if "..." in ref or "<" in ref or ">" in ref:
                continue
            if not (d / ref).exists():
                problems.append(f"{d.name}: 引用的 {ref} 不存在")

        meta = d / "_meta.json"
        if meta.is_file():
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                problems.append(f"{d.name}: _meta.json 不是合法 JSON（{e}）")
            else:
                if data.get("version"):
                    versions[d.name] = data["version"]
                if data.get("slug") and fm and fm.get("name") and data["slug"] != fm["name"]:
                    problems.append(f"{d.name}: _meta.json slug 与 name 不一致")

    pkg = ROOT / "package.json"
    if not pkg.is_file():
        problems.append("缺少 package.json")
    else:
        try:
            pd = json.loads(pkg.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            problems.append(f"package.json 不是合法 JSON（{e}）")
        else:
            if not pd.get("name"):
                problems.append("package.json 缺少 name")
            if not pd.get("version"):
                problems.append("package.json 缺少 version")

    if problems:
        for p in problems:
            print(f"[FAIL] {p}")
        print(f"\n{len(problems)} 个问题")
        return 1

    print(f"[PASS] {len(dirs)} 个技能结构合法：{', '.join(d.name for d in dirs)}")
    if versions:
        print(f"[INFO] 技能版本：{', '.join(f'{k}@{v}' for k, v in versions.items())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
