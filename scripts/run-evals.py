#!/usr/bin/env python3
"""run-evals.py — 技能行为评测的判定器（只判机器可判断言）。

前提：**产物必须由宿主 / 人真的跑出来**，本脚本只负责判卷。
没有产物就记「未跑」，不算失败（CI 不会因此变红）。

产物放在：evals/runs/<评测文件名去掉 .md>/
判定器读取该目录下所有 .md，按评测里的 ```json 块逐条判定。

判据语义：
    exists     文件（按 glob，相对 run-dir）至少匹配到 1 个
    sections   每个关键词都要出现在某个标题行
    match      每个正则至少命中 1 次
    not_match  任一正则命中即失败
    if_match   命中任一 pattern 时，then_match 必须也命中
    min_count  [{pattern, min}] 命中次数不得少于 min
    optional   true 时，文件不存在就跳过该条

用法：
    python3 scripts/run-evals.py --list
    python3 scripts/run-evals.py --eval evals/copy-recruit.md --run-dir evals/runs/copy-recruit
    python3 scripts/run-evals.py --all

退出码：0 = 全部通过（或没有产物可判）；1 = 有失败；3 = 用法错误
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
RUNS = EVALS / "runs"
JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)


def eval_files() -> list[pathlib.Path]:
    return sorted(p for p in EVALS.glob("*.md")
                  if p.name not in {"README.md", "triggers.md"})


def load_checks(path: pathlib.Path) -> list[dict]:
    m = JSON_BLOCK.search(path.read_text(encoding="utf-8"))
    if not m:
        return []
    try:
        return json.loads(m.group(1)).get("checks", [])
    except json.JSONDecodeError:
        return []


def collect(run_dir: pathlib.Path, pattern: str | None) -> list[pathlib.Path]:
    if not run_dir.is_dir():
        return []
    if not pattern:
        return sorted(p for p in run_dir.rglob("*.md") if p.is_file())
    return sorted(p for p in run_dir.rglob(pattern) if p.is_file())


def joined(files: list[pathlib.Path], heads_only: bool = False) -> str:
    parts = []
    for p in files:
        text = p.read_text(encoding="utf-8", errors="ignore")
        if heads_only:
            text = "\n".join(l for l in text.splitlines() if re.match(r"^#{1,6}\s", l))
        parts.append(text)
    return "\n".join(parts)


def judge(check: dict, run_dir: pathlib.Path) -> list[str]:
    fails: list[str] = []
    pattern = check.get("file")
    files = collect(run_dir, pattern)

    if not files:
        if check.get("optional"):
            return []
        if check.get("exists"):
            return [f"找不到文件 {pattern or '*'}"]
        return [f"找不到文件 {pattern or '*'}，无法判定"]

    if check.get("exists"):
        return fails

    text = joined(files)

    if "sections" in check:
        heads = joined(files, heads_only=True)
        for kw in check["sections"]:
            if kw not in heads:
                fails.append(f"标题里缺少「{kw}」")

    if "match" in check:
        for pat in check["match"]:
            if not re.search(pat, text, re.M):
                fails.append(f"未命中 /{pat}/")

    if "not_match" in check:
        for pat in check["not_match"]:
            if re.search(pat, text, re.M):
                fails.append(f"出现禁语 /{pat}/")

    if "if_match" in check:
        if re.search(check["if_match"], text, re.M):
            then = check.get("then_match", "")
            if not re.search(then, text, re.M):
                fails.append(f"命中 /{check['if_match']}/ 但缺少 /{then}/")

    if "min_count" in check:
        for item in check["min_count"]:
            pat, need = item.get("pattern", ""), item.get("min", 1)
            got = len(re.findall(pat, text, re.M))
            if got < need:
                fails.append(f"/{pat}/ 出现 {got} 次，至少 {need} 次")

    return fails


def run_one(path: pathlib.Path) -> tuple[str, list[str]]:
    checks = load_checks(path)
    run_dir = RUNS / path.stem
    if not checks:
        return "no-checks", ["评测里没有机器可判块"]
    if not run_dir.is_dir() or not any(run_dir.rglob("*.md")):
        return "unrun", []
    problems: list[str] = []
    for c in checks:
        problems.extend(judge(c, run_dir))
    return ("pass" if not problems else "fail"), problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--eval")
    ap.add_argument("--run-dir")
    args = ap.parse_args()

    if args.list:
        for p in eval_files():
            print(p.name)
        return 0

    if args.eval and args.run_dir:
        target = ROOT / args.eval if not pathlib.Path(args.eval).is_absolute() else pathlib.Path(args.eval)
        if not target.is_file():
            print(f"ERROR: 找不到评测 {target}")
            return 3
        run_dir = pathlib.Path(args.run_dir)
        checks = load_checks(target)
        problems: list[str] = []
        for c in checks:
            problems.extend(judge(c, run_dir))
        for p in problems:
            print(f"  ✗ {p}")
        print("通过" if not problems else f"失败 {len(problems)} 条")
        return 0 if not problems else 1

    if args.all:
        total = {"pass": 0, "fail": 0, "unrun": 0, "no-checks": 0}
        for p in eval_files():
            status, problems = run_one(p)
            total[status] += 1
            mark = {"pass": "✓", "fail": "✗", "unrun": "·", "no-checks": "!"}[status]
            print(f"[{status}] {mark} {p.name}")
            for item in problems:
                print(f"       - {item}")
        print(f"\n通过 {total['pass']} / 失败 {total['fail']} / 未跑 {total['unrun']}")
        return 1 if total["fail"] else 0

    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
