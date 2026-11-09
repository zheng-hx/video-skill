#!/usr/bin/env python3
"""live-media-ops 技能自检。

用法：
    python3 scripts/check-skill.py            # 检查本技能
    python3 scripts/check-skill.py <技能目录>  # 检查指定技能

检查项：frontmatter / description 长度 / 引用是否存在 / TODO 残留 /
       _meta.json 一致性 / shell 脚本语法与可执行位 / 顶层目录规范。
退出码：有 FAIL 时为 1。
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(HERE)

SHOULD_EXIST = {"SKILL.md", "_meta.json", "_icon.svg", "references", "assets", "scripts"}
ALLOWED_TOP = SHOULD_EXIST | {"README.md"}
DESC_LIMIT = 300

results = []


def add(level, msg):
    results.append((level, msg))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def md_files():
    out = []
    if os.path.exists(os.path.join(ROOT, "SKILL.md")):
        out.append(os.path.join(ROOT, "SKILL.md"))
    for sub in ("references", "assets"):
        d = os.path.join(ROOT, sub)
        if os.path.isdir(d):
            for name in sorted(os.listdir(d)):
                if name.endswith(".md"):
                    out.append(os.path.join(d, name))
    return out


def main():
    if not os.path.isdir(ROOT):
        print(f"[FAIL] 目录不存在：{ROOT}")
        return 1

    # ---- frontmatter ----
    fm = {}
    skill_md = os.path.join(ROOT, "SKILL.md")
    if not os.path.exists(skill_md):
        add("FAIL", "缺少 SKILL.md")
    else:
        text = read(skill_md)
        m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
        if not m:
            add("FAIL", "SKILL.md 缺少 frontmatter")
        else:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
            for key in ("name", "description"):
                if not fm.get(key):
                    add("FAIL", f"frontmatter 缺少 {key}")
            if fm.get("name"):
                base = os.path.basename(os.path.normpath(ROOT))
                if fm["name"] != base:
                    add("WARN", f"frontmatter name({fm['name']}) 与目录名({base}) 不一致")
            desc = fm.get("description", "")
            if desc:
                if len(desc) > DESC_LIMIT:
                    add("WARN", f"description 长度 {len(desc)} 字符，超过 {DESC_LIMIT}，会占用技能索引")
                else:
                    add("PASS", f"description 长度 {len(desc)} 字符")
            extra = set(fm) - {"name", "description"}
            if extra:
                add("WARN", f"frontmatter 有非标准字段：{', '.join(sorted(extra))}（跨宿主时可能被忽略）")

    # ---- 引用完整性 ----
    refs = set()
    for path in md_files():
        for match in re.findall(r"`((?:references|assets|scripts)/[^`\s]+)`", read(path)):
            refs.add(match.rstrip("，。,.;"))
    if refs:
        missing = [r for r in sorted(refs) if not os.path.exists(os.path.join(ROOT, r))]
        if missing:
            for r in missing:
                add("FAIL", f"引用的文件不存在：{r}")
        else:
            add("PASS", f"{len(refs)} 处文件引用全部存在")

    # ---- TODO 残留（只查方法论层；assets/ 是模板，【TODO】是填充位不算） ----
    todo = 0
    for path in md_files():
        if os.path.basename(path) == "SKILL.md" or os.sep + "references" + os.sep in path:
            content = read(path)
            todo += len(re.findall(r"TODO[（(]|【TODO", content))
    if todo:
        add("WARN", f"方法论层残留 {todo} 处 TODO")
    else:
        add("PASS", "方法论层无 TODO 残留")

    # ---- _meta.json ----
    meta_p = os.path.join(ROOT, "_meta.json")
    if not os.path.exists(meta_p):
        add("WARN", "缺少 _meta.json（WorkBuddy 等宿主用；纯文件分发时可不要）")
    else:
        try:
            meta = json.loads(read(meta_p))
            for key in ("slug", "version"):
                if not meta.get(key):
                    add("FAIL", f"_meta.json 缺少 {key}")
            if meta.get("slug") and fm.get("name") and meta["slug"] != fm["name"]:
                add("FAIL", f"_meta.json slug({meta['slug']}) 与 frontmatter name({fm['name']}) 不一致")
            if meta.get("version"):
                add("PASS", f"版本 {meta['version']}")
        except json.JSONDecodeError as e:
            add("FAIL", f"_meta.json 不是合法 JSON：{e}")

    # ---- shell 脚本 ----
    scripts_dir = os.path.join(ROOT, "scripts")
    if os.path.isdir(scripts_dir):
        for name in sorted(os.listdir(scripts_dir)):
            if not name.endswith(".sh"):
                continue
            path = os.path.join(scripts_dir, name)
            proc = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
            if proc.returncode != 0:
                add("FAIL", f"{name} 语法错误：{proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else '未知'}")
            else:
                add("PASS", f"{name} 语法通过")
            if not os.access(path, os.X_OK):
                add("WARN", f"{name} 没有可执行位")

    # ---- 顶层目录规范 ----
    unexpected = [i for i in sorted(os.listdir(ROOT))
                  if not i.startswith(".") and i not in ALLOWED_TOP]
    if unexpected:
        add("WARN", f"顶层有未预期条目：{', '.join(unexpected)}")

    # ---- 输出 ----
    order = {"FAIL": 0, "WARN": 1, "PASS": 2}
    for level, msg in sorted(results, key=lambda x: order[x[0]]):
        mark = {"FAIL": "✗", "WARN": "!", "PASS": "✓"}[level]
        print(f"[{level}] {mark} {msg}")

    fails = sum(1 for l, _ in results if l == "FAIL")
    warns = sum(1 for l, _ in results if l == "WARN")
    passes = sum(1 for l, _ in results if l == "PASS")
    print(f"\n汇总：{passes} 通过 / {warns} 警告 / {fails} 失败  （{ROOT}）")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
