#!/usr/bin/env python3
"""check-triggers.py — 触发层金标集的词面覆盖校验。

只回答一个问题（词面层面，不代替真实模型触发测试）：
    金标集里每条用例的「期望技能」，其 description 是否真的包含该用例的关键词之一？
    不含 → 这句用户话很可能命中不了这个技能。

另外打印每个技能的触发短语清单，供人工判断技能之间有没有抢触发。

用法：python3 scripts/check-triggers.py
退出码：0 = 覆盖无缺口；1 = 有缺口；3 = 用法错误
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
TRIGGERS = ROOT / "evals" / "triggers.md"

ROW = re.compile(r"^\|\s*\d+\s*\|([^|]+)\|\s*`([a-z0-9-]+)`\s*\|\s*([^|]+)\|", re.M)
QUOTED = re.compile(r"「([^」]+)」")


def skill_descriptions() -> dict[str, str]:
    out: dict[str, str] = {}
    if not SKILLS.is_dir():
        return out
    skill_mds = []
    for pat in ("*/SKILL.md", "*/capabilities/*/SKILL.md"):
        skill_mds.extend(sorted(SKILLS.glob(pat)))
    for skill_md in skill_mds:
        text = skill_md.read_text(encoding="utf-8")
        m = re.search(r"^description:\s*(.+)$", text, re.M)
        if m:
            out.setdefault(skill_md.parent.name, m.group(1).strip())
    return out


def trigger_phrases(desc: str) -> list[str]:
    phrases: list[str] = []
    for quoted in QUOTED.findall(desc):
        phrases.extend(p.strip() for p in re.split(r"[/、]", quoted) if p.strip())
    return phrases


def main() -> int:
    if not TRIGGERS.is_file():
        print(f"ERROR: 缺少 {TRIGGERS.relative_to(ROOT)}")
        return 3
    descs = skill_descriptions()
    if not descs:
        print("ERROR: skills/ 下没有找到任何 SKILL.md")
        return 3

    rows = ROW.findall(TRIGGERS.read_text(encoding="utf-8"))
    if not rows:
        print("ERROR: triggers.md 里没解析出金标集表格（格式：| 序号 | 用户会说 | `技能` | 关键词 |）")
        return 3

    missing_skill = 0
    uncovered = 0
    for _say, skill, kws in rows:
        say = _say.strip()
        if skill not in descs:
            print(f"[FAIL] 技能不存在：`{skill}`（用例：{say}）")
            missing_skill += 1
            continue
        keywords = [k.strip() for k in re.split(r"[/|、]", kws) if k.strip()]
        if not any(k in descs[skill] for k in keywords):
            print(f"[FAIL] 覆盖缺口：`{skill}` 的 description 里找不到 {keywords}（用例：{say}）")
            uncovered += 1
        else:
            print(f"[PASS] {say[:28]}… → `{skill}`")

    print("\n—— 各技能触发短语（人工看有没有抢触发）——")
    for name, desc in descs.items():
        phrases = trigger_phrases(desc)
        print(f"  {name}: {('、'.join(phrases)) if phrases else '（未用「」标注触发词）'}")

    print(f"\n金标集 {len(rows)} 条：缺口 {uncovered}，技能缺失 {missing_skill}")
    return 1 if (uncovered or missing_skill) else 0


if __name__ == "__main__":
    sys.exit(main())
