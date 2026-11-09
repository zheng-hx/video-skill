#!/usr/bin/env python3
"""check-evals.py — 评测定义的结构校验。

它不评价技能产出好坏，只保证**评测定义本身是完整的**：
有输入、有可断言的期望、有反例、有机器可判块。

校验每个 evals/*.md（README.md 与 triggers.md 除外）：
  1) 标题形如 `# Eval:`
  2) 元信息含 `> **技能**:` 与 `> **目的**:`
  3) 必备小节：## 输入 / ## 期望 / ### 结构断言 / ### 门禁断言 / ### 过程断言 / ### 反例 / ## 判定
  4) 结构断言、门禁断言、反例各至少 3 条 `- [ ]`；过程断言至少 2 条
  5) 含一个合法 ```json 机器可判块，且 checks 非空

退出码：0 = 通过，1 = 有问题，3 = 用法错误
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"

REQUIRED = ["## 输入", "## 期望", "### 结构断言", "### 门禁断言",
            "### 过程断言", "### 反例", "## 判定"]
MIN_ITEMS = {"### 结构断言": 3, "### 门禁断言": 3, "### 过程断言": 2, "### 反例": 3}
JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)
ALLOWED_KEYS = {"file", "exists", "sections", "match", "not_match",
                "if_match", "then_match", "min_count", "optional"}


def eval_files() -> list[pathlib.Path]:
    if not EVALS.is_dir():
        return []
    return sorted(p for p in EVALS.glob("*.md")
                  if p.name not in {"README.md", "triggers.md"})


def section_body(text: str, title: str) -> str | None:
    """取某小节正文（到下一个同级或更高级标题为止）。

    标题允许带说明后缀，如 `## 输入（固定场景）`。
    """
    m = re.search(rf"^{re.escape(title)}[^\n]*$", text, re.M)
    if not m:
        return None
    rest = text[m.end():]
    nxt = re.search(r"^#{2,3}\s", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def count_items(body: str) -> int:
    return len(re.findall(r"^- \[ \]", body, re.M))


def check_one(path: pathlib.Path) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")

    if not re.match(r"^# Eval:\s*\S", text):
        problems.append("标题不是 `# Eval: ...`")
    if "> **技能**:" not in text:
        problems.append("元信息缺少 `> **技能**:`")
    if not re.search(r"\*\*目的\*\*\s*:", text):
        problems.append("元信息缺少 `> **目的**:`")

    for title in REQUIRED:
        body = section_body(text, title)
        if body is None:
            problems.append(f"缺少小节 `{title}`")
            continue
        need = MIN_ITEMS.get(title)
        if need and count_items(body) < need:
            problems.append(f"`{title}` 只有 {count_items(body)} 条，至少 {need} 条")

    m = JSON_BLOCK.search(text)
    if not m:
        problems.append("缺少 ```json 机器可判块")
    else:
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            problems.append(f"json 块不是合法 JSON：{e}")
        else:
            checks = data.get("checks")
            if not isinstance(checks, list) or not checks:
                problems.append("json 块里 checks 为空")
            else:
                for i, c in enumerate(checks):
                    if not isinstance(c, dict):
                        problems.append(f"checks[{i}] 不是对象")
                        continue
                    unknown = set(c) - ALLOWED_KEYS
                    if unknown:
                        problems.append(f"checks[{i}] 有未知键：{sorted(unknown)}")
                    if "file" not in c:
                        problems.append(f"checks[{i}] 缺少 file")
                    has_rule = any(k in c for k in
                                   {"exists", "sections", "match", "not_match",
                                    "if_match", "min_count"})
                    if not has_rule:
                        problems.append(f"checks[{i}] 没有任何判据")
                    if "if_match" in c and "then_match" not in c:
                        problems.append(f"checks[{i}] 有 if_match 却没有 then_match")
    return problems


def main() -> int:
    if not EVALS.is_dir():
        print("ERROR: 缺少 evals/ 目录")
        return 1
    files = eval_files()
    if not files:
        print("ERROR: evals/ 下没有任何评测用例")
        return 1
    failed = 0
    for path in files:
        problems = check_one(path)
        if problems:
            failed += 1
            print(f"[FAIL] {path.name}")
            for p in problems:
                print(f"       - {p}")
        else:
            print(f"[PASS] {path.name}")
    print(f"\n{len(files) - failed}/{len(files)} 个评测定义通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
