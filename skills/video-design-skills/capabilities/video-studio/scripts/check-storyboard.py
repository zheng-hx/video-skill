#!/usr/bin/env python3
"""check-storyboard.py — 分镜与衔接门禁。

只查机器能查的东西：字段齐不齐、时长对不对、衔接合同有没有写、
首尾状态是不是空话。不评价画面好不好看。

用法：
    python3 scripts/check-storyboard.py storyboard.json
    python3 scripts/check-storyboard.py --sample   # 校验自带模板

退出码：0 = 通过，1 = 有问题，3 = 用法错误
"""
from __future__ import annotations

import json
import re
import pathlib
import sys

MODES = {"single", "multi"}
STYLES = {"realistic", "anime", "3d", "illustration", "mixed"}
ENDINGS = {"brand_card", "cta", "freeze", "loop"}
# 这些词证明不了任何可见事实，出现在 end_state / next_start_state 里等于没写
VAGUE = ["保持连续", "同上", "延续上一镜", "延续", "不变", "照旧", "同前", "保持不变"]
DURATION_TOLERANCE = 1.0
# 提示词详细度：太短、没有镜头、没有光线，都算没写细
DETAIL_MIN = 60
CAMERA_WORDS = ["特写", "近景", "中景", "全景", "远景", "半身", "全身", "推", "拉", "摇",
                "移", "跟拍", "升降", "环绕", "固定", "静止", "俯拍", "仰拍",
                "低角度", "高角度", "等效"]
LIGHT_WORDS = ["自然光", "侧光", "逆光", "顶光", "柔光", "硬光", "灯光", "窗光",
               "光比", "色温", "光源", "冷光", "暖光"]
# 评价性模糊词：是判断不是描述，模型拿不到参数
VAGUE_WORDS = ["好看", "电影感", "大片感", "高级感", "氛围感", "有质感",
               "震撼", "唯美", "高大上", "绝了"]
# 画面红线：负向词里必须拦住的东西
RED_LINE_NEG = ["二维码", "logo", "水印"]
# 提示词里出现这些词，要人确认不是医疗对比 / 血腥 / 擦边
DANGER_PROMPT = ["伤口", "血迹", "前后对比", "裸露", "低胸", "床戏"]
# 授权表必填字段
AUTH_FIELDS = ["real_person", "minor", "brand_logo", "medical_claim"]
# 每一镜都要推进剧情，且相邻镜的景别/运镜不能一样
BEAT_REQUIRED = True
# 首镜完整，后续续接：非首镜必须写衔接，且不能重复上一镜开头
CONTINUE_WORDS = ["接上一镜", "从上一镜", "接着上一镜", "衔接上一镜"]
REPEAT_PREFIX = 15
# 有台词就必须在说话：画面里嘴不动，后配音也救不回来
SPEAK_WORDS = ["说话", "开口", "张口", "口型", "对白", "念白", "说道", "嘴唇微动", "正在说"]
# 构图 / 质感：提示词里必须写到，不然画面是飘的
COMPOSITION_WORDS = ["构图", "居中", "留白", "三分", "前景", "背景", "占"]
TEXTURE_WORDS = ["质感", "颗粒", "毛孔", "锐度", "磨皮", "反光", "材质", "调色"]
# 约束层（防崩）：每条提示词至少要有一句
CONSTRAINT_WORDS = ["结构正常", "不变形", "不抖动", "稳定", "不僵硬", "比例自然", "无畸变"]
HERE = pathlib.Path(__file__).resolve().parent
SAMPLE = HERE.parent / "assets" / "storyboard.template.json"


PUNCT_CHARS = set(" \t\n，。！？、；：\"'（）()【】[]「」『』""")


def norm(text: str) -> str:
    """去掉标点和空白，只比字——台词在 prompt 里有点标点差异不算错。"""
    return "".join(ch for ch in (text or "") if ch not in PUNCT_CHARS)


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check(data: dict) -> list[str]:
    problems: list[str] = []

    meta = data.get("meta")
    if not isinstance(meta, dict):
        return ["缺少 meta"]
    for key in ("platform", "duration", "mode"):
        if key not in meta:
            problems.append(f"meta 缺少 `{key}`")
    mode = meta.get("mode")
    if mode not in MODES:
        problems.append(f"meta.mode 必须是 single 或 multi，当前是 {mode!r}")
    if meta.get("style") not in STYLES:
        problems.append(
            "meta.style 必须是 realistic / anime / 3d / illustration / mixed 之一"
        )
    try:
        target = float(meta.get("duration", 0))
    except (TypeError, ValueError):
        target = 0.0
        problems.append("meta.duration 不是数字")

    auth = meta.get("authorization")
    if not isinstance(auth, dict):
        problems.append("meta.authorization 缺失（真人 / 儿童 / 品牌 / 医疗授权）")
    else:
        for field in AUTH_FIELDS:
            val = auth.get(field)
            if val is None:
                problems.append(f"meta.authorization.{field} 未填")
            elif val == "pending":
                problems.append(f"meta.authorization.{field} = pending，先问用户，不许生成")

    style_anchor = (data.get("style_anchor") or "").strip()
    if not style_anchor:
        problems.append("缺少 style_anchor（风格锚）")

    chars = {c.get("id"): c for c in data.get("characters", []) if isinstance(c, dict)}
    for cid, c in chars.items():
        if not cid:
            problems.append("characters 里有一条没有 id")
        if not c.get("identity_anchor"):
            problems.append(f"角色 {cid}: 缺少 identity_anchor（身份锚点）")

    shots = data.get("shots") or []
    if not shots:
        return problems + ["shots 为空"]

    seen = set()
    total = 0.0
    prev_prompt = ""
    expected_start = 0.0
    for i, s in enumerate(shots):
        sid = s.get("id")
        where = f"镜头 {sid or i + 1}"
        if not sid:
            problems.append(f"{where}: 缺少 id")
        elif sid in seen:
            problems.append(f"{where}: id 重复")
        seen.add(sid)
        try:
            dur = float(s.get("duration", 0))
            total += dur
        except (TypeError, ValueError):
            dur = 0.0
            problems.append(f"{where}: duration 不是数字")

        start, end = s.get("start"), s.get("end")
        if start is None or end is None:
            problems.append(f"{where}: 缺时间轴 start / end，剪辑和配音对不上")
        else:
            try:
                start, end = float(start), float(end)
                if abs(start - expected_start) > 0.05:
                    problems.append(
                        f"{where}: 开始时间 {start:g} 秒，接不上上一个镜头结束的 {expected_start:g} 秒"
                    )
                if abs((end - start) - dur) > 0.05:
                    problems.append(f"{where}: {start:g}-{end:g} 秒与 duration {dur:g} 秒对不上")
                expected_start = end
            except (TypeError, ValueError):
                problems.append(f"{where}: start / end 不是数字")
        if float(s.get("duration", 0) or 0) <= 0:
            problems.append(f"{where}: duration 必须大于 0")
        shot_max = float(meta.get("max_shot_duration", 15))
        if float(s.get("duration", 0) or 0) > shot_max:
            problems.append(
                f"{where}: {float(s.get('duration', 0)):g} 秒超过平台单次上限 {shot_max:g} 秒，生成不了，拆镜"
            )
        prompt = (s.get("prompt") or "").strip()
        beat = (s.get("beat") or "").strip()
        if BEAT_REQUIRED and not beat:
            problems.append(f"{where}: 缺少 beat（这一镜推进了什么剧情），容易变成并列画面")
        if i > 0:
            prev = shots[i - 1]
            if s.get("framing") and s.get("framing") == prev.get("framing") and \
               s.get("camera") and s.get("camera") == prev.get("camera"):
                problems.append(f"{where}: 景别和运镜都和上一镜一样，画面会像重复")
            if not any(w in prompt[:80] for w in CONTINUE_WORDS):
                problems.append(f"{where}: 非首镜没写「接上一镜」，动作接不上")
            if prev_prompt and prompt[:REPEAT_PREFIX] == prev_prompt[:REPEAT_PREFIX]:
                problems.append(f"{where}: 开头和上一镜重复，像复制粘贴，等于让模型从零重画")
        prev_prompt = prompt
        for word in DANGER_PROMPT:
            if word in prompt:
                problems.append(f"{where}: prompt 出现「{word}」，确认不是医疗对比/血腥/擦边镜头")
        if not prompt:
            problems.append(f"{where}: 缺少 prompt")
        else:
            if len(prompt) < DETAIL_MIN:
                problems.append(f"{where}: prompt 只有 {len(prompt)} 字，至少 {DETAIL_MIN} 字才算写细")
            if not any(w in prompt for w in CAMERA_WORDS):
                problems.append(f"{where}: prompt 里没有镜头词（景别或运镜）")
            if not any(w in prompt for w in LIGHT_WORDS):
                problems.append(f"{where}: prompt 里没有光线词")
            if not any(w in prompt for w in COMPOSITION_WORDS):
                problems.append(f"{where}: prompt 里没有构图（主体位置 / 留白 / 前景）")
            if not any(w in prompt for w in TEXTURE_WORDS):
                problems.append(f"{where}: prompt 里没有质感（材质 / 颗粒 / 锐度 / 调色）")
            for w in VAGUE_WORDS:
                if w in prompt:
                    problems.append(f"{where}: 出现模糊词「{w}」，换成可拍参数")
            if not any(w in prompt for w in CONSTRAINT_WORDS):
                problems.append(f"{where}: prompt 里没有约束层（防崩），至少写一句")
        line = (s.get("line") or "").strip()
        silent = bool(s.get("silent"))
        if not line and not silent:
            problems.append(f"{where}: 缺少 line（台词），视频会没声音；没有台词就标 silent: true")
        if line and not silent and norm(line) not in norm(prompt):
            problems.append(f"{where}: 台词没写进 prompt，生成时模型不知道说什么；把台词原文放进「声音」段")
        if line and not silent and not (s.get("character_refs") or []):
            problems.append(f"{where}: 有台词但没写 character_refs，不知道谁在说")
        if line and not silent and not any(w in prompt for w in SPEAK_WORDS):
            problems.append(
                f"{where}: 有台词，但画面没写「在说话」——生成出来人不会张嘴，后配音也对不上"
            )

        negative = (s.get("negative") or "").strip()
        if not negative:
            problems.append(f"{where}: 缺少 negative（负向词）")
        else:
            for word in RED_LINE_NEG:
                if word.lower() not in negative.lower():
                    problems.append(f"{where}: 负向词缺「{word}」（画面红线）")
        for ref in s.get("character_refs") or []:
            if ref not in chars:
                problems.append(f"{where}: character_refs 里的 `{ref}` 不在 characters 里")
        if style_anchor and style_anchor not in (s.get("prompt") or ""):
            problems.append(f"{where}: prompt 里没有风格锚「{style_anchor}」")

    if target and abs(total - target) > DURATION_TOLERANCE:
        problems.append(f"时长合计 {total:g} 秒，与 meta.duration {target:g} 秒不一致（允许 ±{DURATION_TOLERANCE:g}）")

    handoffs = data.get("handoffs") or []
    if mode == "multi":
        if len(handoffs) != len(shots) - 1:
            problems.append(
                f"多段模式：{len(shots)} 个镜头应有 {len(shots) - 1} 条 handoff，实际 {len(handoffs)} 条"
            )
        pairs = {(h.get("from"), h.get("to")) for h in handoffs if isinstance(h, dict)}
        for i in range(len(shots) - 1):
            a, b = shots[i].get("id"), shots[i + 1].get("id")
            if (a, b) not in pairs:
                problems.append(f"缺少 {a} → {b} 的 handoff")
        for h in handoffs:
            if not isinstance(h, dict):
                continue
            tag = f"{h.get('from')} → {h.get('to')} 的 handoff"
            if h.get("mode") not in {"continuous", "match_cut", "hard_cut", "fade"}:
                problems.append(f"{tag}: mode 必须是 continuous / match_cut / hard_cut / fade")
            for key in ("end_state", "next_start_state"):
                val = (h.get(key) or "").strip()
                if not val:
                    problems.append(f"{tag}: 缺少 {key}")
                    continue
                for word in VAGUE:
                    if word in val:
                        problems.append(f"{tag}: {key} 出现空话「{word}」，要写成可见事实")
    elif handoffs:
        problems.append("单条模式不需要 handoffs，删掉或改成 multi")

    ending = data.get("ending")
    if not isinstance(ending, dict):
        problems.append("缺少 ending（收尾设计）")
    else:
        if ending.get("type") not in ENDINGS:
            problems.append("ending.type 必须是 brand_card / cta / freeze / loop")
        end_state = (ending.get("end_state") or "").strip()
        if not end_state:
            problems.append("ending 缺少 end_state（最后一帧停在什么画面）")
        else:
            for word in VAGUE:
                if word in end_state:
                    problems.append(f"ending.end_state 出现空话「{word}」，要写成可见画面")

    return problems


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "--sample" in sys.argv[1:] or not args:
        path = SAMPLE
    else:
        path = pathlib.Path(args[0])
    if not path.is_file():
        print(f"找不到文件：{path}")
        return 3
    try:
        data = load(path)
    except json.JSONDecodeError as e:
        print(f"JSON 不合法：{e}")
        return 3

    problems = check(data)
    if problems:
        for p in problems:
            print(f"[FAIL] {p}")
        print(f"\n{len(problems)} 个问题")
        return 1
    shots = data.get("shots") or []
    mode = data.get("meta", {}).get("mode")
    print(f"[PASS] {mode} · {len(shots)} 镜 · 时长 {sum(float(s.get('duration', 0)) for s in shots):g} 秒 · 衔接 {len(data.get('handoffs') or [])} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
