#!/usr/bin/env python3
"""check-copy.py — 文案的违规词与限流词扫描。

只查词，不判语义。「违规」= 法律/平台明令禁止；「限流」= 不违法但平台不推。
两类都要过，但处理方式不同：违规要删，限流要换说法。

用法：
    python3 scripts/check-copy.py 文案.txt
    echo "招主播，保底6000" | python3 scripts/check-copy.py -
    python3 scripts/check-copy.py --self-test   # 验证扫描器本身，不扫你的文案

退出码：0 = 干净 / 自测通过，1 = 命中 / 自测失败，3 = 用法错误
"""
from __future__ import annotations

import pathlib
import re
import sys
import unicodedata

SNAPSHOT = pathlib.Path(__file__).resolve().parents[1] / "assets" / "rules-snapshot.md"

# 违规：法律或平台明文禁止，出现就要改
ILLEGAL = {
    "绝对化用语": ["最好", "第一品牌", "国家级", "世界级", "最高级", "最佳", "最优",
                   "最强", "最大", "顶级", "唯一", "独家", "100%", "百分百", "永久"],
    "医疗功效": ["根治", "治疗", "祛斑", "药妆", "医学护肤", "药效"],
    "金融承诺": ["稳赚", "保本", "保收益", "无风险", "日入过万"],
}

# 限流：不违法，但平台会压流量
THROTTLED = {
    "招工用工": ["招聘", "招人", "底薪", "保底", "月入", "包吃住", "薪资面议", "提成", "五险一金"],
    "站外导流": ["加微信", "加v", "加V", "vx", "VX", "二维码", "留电话", "加我好友"],
    "诱导互动": ["点关注抽奖", "不转不是", "领红包", "点赞抽"],
    "夸大收益": ["轻松月入", "躺赚", "财富自由"],
}

SELF_TEST = "招主播，保底 6000，月入过万，全网最好，加微信详聊。"
SELF_TEST_CLEAN = "今天天气不错，我们去公园走走。"
# 加空格 / 全角空格 / 间隔号 的规避写法，扫描器必须也能抓到
SELF_TEST_EVASION = ["招 主 播", "招　聘", "加·微·信", "最 好 用", "加ｖ详聊"]


def _block_words(text: str, title: str) -> list[str]:
    m = re.search(rf"#+\s*{re.escape(title)}.*?```(?:text)?\n(.*?)\n```", text, re.S)
    if not m:
        return []
    return [w.strip() for w in m.group(1).splitlines() if w.strip()]


def load_snapshot_words() -> tuple[list[str], list[str]]:
    """从规则快照读词表——快照是单一事实源。"""
    if not SNAPSHOT.is_file():
        return [], []
    text = SNAPSHOT.read_text(encoding="utf-8", errors="ignore")
    return _block_words(text, "当前红线词"), _block_words(text, "当前限流词")


def _normalize(text: str) -> str:
    """抹平规避写法：全角转半角，去掉空白和视觉分隔符（招 聘 / 招　聘 / 加·微·信）。"""
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"[\s·・\-_/|*]+", "", text).lower()


def _hit(normalized: str, word: str) -> bool:
    return _normalize(word) in normalized


def scan(text: str) -> list[tuple[str, str, str]]:
    snap_illegal, snap_throttled = load_snapshot_words()
    normalized = _normalize(text)
    hits: list[tuple[str, str, str]] = []
    if snap_illegal:
        for w in snap_illegal:
            if _hit(normalized, w):
                hits.append(("违规", "快照·红线", w))
    else:
        for group, words in ILLEGAL.items():
            for w in words:
                if _hit(normalized, w):
                    hits.append(("违规", group, w))
    if snap_throttled:
        for w in snap_throttled:
            if _hit(normalized, w):
                hits.append(("限流", "快照·限流", w))
    else:
        for group, words in THROTTLED.items():
            for w in words:
                if _hit(normalized, w):
                    hits.append(("限流", group, w))
    return hits


def self_test() -> int:
    """验证扫描器本身：脏样本该命中，干净样本不该误报。"""
    hits = scan(SELF_TEST)
    for kind, group, word in hits:
        print(f"[命中] {kind} · {group}: {word}")

    illegal = [h for h in hits if h[0] == "违规"]
    throttled = [h for h in hits if h[0] == "限流"]
    clean_hits = scan(SELF_TEST_CLEAN)

    problems: list[str] = []
    if not illegal:
        problems.append("自测样本含「最好」，却未命中任何违规词")
    if not throttled:
        problems.append("自测样本含限流词，却未命中任何限流词")
    if clean_hits:
        problems.append("干净样本被误报：" + "、".join(w for _, _, w in clean_hits))

    for sample in SELF_TEST_EVASION:
        if not scan(sample):
            problems.append(f"规避写法「{sample}」漏检")

    if problems:
        print("\n[SELF-TEST FAIL]")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"\n[SELF-TEST PASS] 违规 {len(illegal)} 处、限流 {len(throttled)} 处全部命中；"
          f"干净样本 0 误报；{len(SELF_TEST_EVASION)} 种规避写法全部识破")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("用法：check-copy.py <文件|-> [--self-test]")
        return 3
    if args[0] == "--self-test":
        return self_test()
    elif args[0] == "-":
        text = sys.stdin.read()
    else:
        p = pathlib.Path(args[0])
        if not p.is_file():
            print(f"找不到文件：{p}")
            return 3
        text = p.read_text(encoding="utf-8", errors="ignore")

    hits = scan(text)
    if not hits:
        print("[PASS] 没命中违规词或限流词")
        return 0

    for kind, group, word in hits:
        print(f"[{kind}] {group}: {word}")

    illegal = sum(1 for k, _, _ in hits if k == "违规")
    throttled = len(hits) - illegal
    print(f"\n违规 {illegal} 处，限流 {throttled} 处")
    print("违规要删；限流要换说法（见 compliance.md §5.5）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
