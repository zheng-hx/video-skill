#!/usr/bin/env python3
"""library.py — 文案知识库：入库 / 检索 / 规则变更 / 复审。

    ~/.video-design/library/
    ├── index.json
    ├── entries/001.md
    ├── rules-log.json
    └── style.md

用法：
    # 入库（用户说「这条不错」时才用）
    python3 library.py add --file copy.md --type 择业 --platform 抖音 \\
        --tags 短平快,口语 --why "钩子狠，接地气"

    # 检索（生成前，只取最像的）
    python3 library.py search --type 择业 --platform 抖音 --limit 3

    # 平台规则变了：记一笔 + 批量标 stale
    python3 library.py rule --platform 抖音 --change "招聘类限流收紧" --tags 择业

    # 复审
    python3 library.py review --id 001 --status active
    python3 library.py review --id 001 --status retired

    # 看全库
    python3 library.py list

退出码：0 = 成功，1 = 有问题，3 = 用法错误
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
from datetime import date

DEFAULT_DIR = pathlib.Path.home() / ".video-design" / "library"


def load_json(p: pathlib.Path, default):
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return default


def save_json(p: pathlib.Path, data) -> None:
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure(root: pathlib.Path) -> None:
    (root / "entries").mkdir(parents=True, exist_ok=True)
    idx = root / "index.json"
    if not idx.is_file():
        save_json(idx, {"entries": []})
    log = root / "rules-log.json"
    if not log.is_file():
        save_json(log, [])


def today() -> str:
    return date.today().isoformat()


def cmd_add(args) -> int:
    root = pathlib.Path(args.dir).expanduser()
    ensure(root)
    idx_path = root / "index.json"
    idx = load_json(idx_path, {"entries": []})
    entries = idx["entries"]
    nid = f"{len(entries) + 1:03d}"
    src = pathlib.Path(args.file)
    if not src.is_file():
        print(f"找不到文件：{src}")
        return 3
    dst = root / "entries" / f"{nid}.md"
    shutil.copy(src, dst)
    entries.append({
        "id": nid,
        "type": args.type,
        "platform": args.platform,
        "tags": [t.strip() for t in (args.tags or "").split(",") if t.strip()],
        "why": args.why or "",
        "date": today(),
        "status": "active",
        "reviewedAt": today(),
    })
    save_json(idx_path, idx)
    print(f"已入库：{nid} → {dst}")
    if not args.why:
        print("提醒：没填「好在哪」，以后引用时学不到东西。补一下 --why。")
    return 0


def cmd_result(args) -> int:
    """记录发布结果：被限流 / 正常 / 爆了。"""
    root = pathlib.Path(args.dir).expanduser()
    ensure(root)
    idx_path = root / "index.json"
    idx = load_json(idx_path, {"entries": []})
    for e in idx["entries"]:
        if e["id"] != args.id:
            continue
        e.setdefault("results", []).append({
            "date": today(),
            "result": args.result,
            "note": args.note or "",
        })
        if args.result == "throttled":
            e["status"] = "stale"
            save_json(idx_path, idx)
            print(f"{args.id} 被限流 → 标 stale，先复审再引用")
        elif args.result == "hit":
            save_json(idx_path, idx)
            print(f"{args.id} 爆了 → 以后检索优先用这条")
        else:
            save_json(idx_path, idx)
            print(f"{args.id} 正常 → 记录，不改状态")
        return 0
    print(f"找不到条目 {args.id}")
    return 1


def hit_count(entry: dict) -> int:
    return sum(1 for r in entry.get("results", []) if r.get("result") == "hit")


def cmd_search(args) -> int:
    root = pathlib.Path(args.dir).expanduser()
    ensure(root)
    idx = load_json(root / "index.json", {"entries": []})
    hits = []
    for e in idx["entries"]:
        if e.get("status") != "active":
            continue
        if args.type and e.get("type") != args.type:
            continue
        if args.platform and e.get("platform") != args.platform:
            continue
        if getattr(args, "q", ""):
            body = root / "entries" / (e["id"] + ".md")
            blob = " ".join([
                e.get("type", ""), e.get("platform", ""), e.get("why", ""),
                " ".join(e.get("tags", [])),
                body.read_text(encoding="utf-8", errors="ignore") if body.is_file() else "",
            ])
            if args.q.lower() not in blob.lower():
                continue
        hits.append(e)
    hits.sort(key=lambda e: (hit_count(e), e.get("date", "")), reverse=True)
    hits = hits[: args.limit]
    if not hits:
        print("没有匹配的可用条目")
        return 0
    for e in hits:
        print(f"[{e['id']}] {e['type']} · {e['platform']} · {e['date']} · {e.get('why','')}")
        print(f"    {root / 'entries' / (e['id'] + '.md')}")
    return 0


def cmd_rule(args) -> int:
    root = pathlib.Path(args.dir).expanduser()
    ensure(root)
    tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
    log_path = root / "rules-log.json"
    log = load_json(log_path, [])
    log.append({
        "date": today(),
        "platform": args.platform,
        "change": args.change,
        "tags": tags,
    })
    save_json(log_path, log)

    idx_path = root / "index.json"
    idx = load_json(idx_path, {"entries": []})
    marked = 0
    for e in idx["entries"]:
        if e.get("status") != "active":
            continue
        if args.platform and e.get("platform") != args.platform:
            continue
        if tags:
            entry_tags = set(e.get("tags", [])) | {e.get("type", "")}
            if not set(tags) & entry_tags:
                continue
        e["status"] = "stale"
        marked += 1
    save_json(idx_path, idx)
    print(f"已记录规则变更：{args.platform} · {args.change}")
    print(f"标 stale {marked} 条")
    if marked:
        print("这些条目暂时不要引用，先复审或改写。")
    return 0


def cmd_review(args) -> int:
    root = pathlib.Path(args.dir).expanduser()
    ensure(root)
    idx_path = root / "index.json"
    idx = load_json(idx_path, {"entries": []})
    for e in idx["entries"]:
        if e["id"] != args.id:
            continue
        e["status"] = args.status
        e["reviewedAt"] = today()
        save_json(idx_path, idx)
        print(f"{args.id} → {args.status}（复审于 {today()}）")
        return 0
    print(f"找不到条目 {args.id}")
    return 1


def cmd_list(args) -> int:
    root = pathlib.Path(args.dir).expanduser()
    ensure(root)
    idx = load_json(root / "index.json", {"entries": []})
    if not idx["entries"]:
        print("库是空的")
        return 0
    for e in idx["entries"]:
        flag = "✓" if e.get("status") == "active" else "⚠"
        print(f"{flag} [{e['id']}] {e['type']} · {e['platform']} · {e['status']} · {e.get('date','')}")
    stale = sum(1 for e in idx["entries"] if e.get("status") == "stale")
    if stale:
        print(f"\n{stale} 条 stale，需要复审")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="文案知识库")
    ap.add_argument("--dir", default=str(DEFAULT_DIR), help="库目录")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="入库")
    a.add_argument("--file", required=True)
    a.add_argument("--type", required=True)
    a.add_argument("--platform", required=True)
    a.add_argument("--tags", default="")
    a.add_argument("--why", default="")

    s = sub.add_parser("search", help="检索可用条目（可给关键词）")
    s.add_argument("q", nargs="?", default="", help="关键词，匹配标题 / 正文 / 标签 / 原因")
    s.add_argument("--type", default="")
    s.add_argument("--platform", default="")
    s.add_argument("--limit", type=int, default=3)

    r = sub.add_parser("rule", help="记录平台规则变更并标 stale")
    r.add_argument("--platform", required=True)
    r.add_argument("--change", required=True)
    r.add_argument("--tags", default="")

    v = sub.add_parser("review", help="复审")
    v.add_argument("--id", required=True)
    v.add_argument("--status", choices=["active", "retired"], required=True)

    res = sub.add_parser("result", help="记录发布结果")
    res.add_argument("--id", required=True)
    res.add_argument("--result", choices=["throttled", "normal", "hit"], required=True)
    res.add_argument("--note", default="")

    sub.add_parser("list", help="列出全库")

    args = ap.parse_args()
    return {
        "add": cmd_add, "search": cmd_search, "rule": cmd_rule,
        "review": cmd_review, "list": cmd_list, "result": cmd_result,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
