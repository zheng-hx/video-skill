#!/usr/bin/env python3
"""check-storyboard.py — 分镜与衔接门禁。

只查机器能查的东西：字段齐不齐、时长对不对、衔接合同有没有写、
首尾状态是不是空话。不评价画面好不好看。

v2.0 更新（2026-11-10）：配合共享/独有字段分层。
  - 首镜：必须包含完整 style_anchor + identity_anchor + 光线关键词（共享字段）
  - 后续镜：必须包含「全局保持」行（重申共享锚点）+「接上一镜」行（衔接动作）
  - 旧版要求每镜都完整风格锚 → 改为后续镜只查「全局保持」行里有就行
  - 旧版检查后续镜开头不能和上一镜重复 → 改为检查「全局保持」行之后的独有内容
  - 审核：meta.review.story_approved / prompts_approved 必须为 true
  - 声音：每镜「声音」段 + 配乐（或 no_music_reason）；silent 必须写 silent_reason
  - 全片无台词：必须写 meta.no_dialogue_reason

用法：
    python3 scripts/check-storyboard.py storyboard.json   # 完整门禁（含审核 / 声音）
    python3 scripts/check-storyboard.py --sample          # 只验模板结构，跳过 review 门禁
    python3 scripts/check-storyboard.py --self-test       # 验证门禁本身

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
               "光比", "色温", "光源", "冷光", "暖光", "光线"]
# 评价性模糊词：是判断不是描述，模型拿不到参数
VAGUE_WORDS = ["好看", "电影感", "大片感", "高级感", "氛围感", "有质感",
               "震撼", "唯美", "高大上", "绝了"]
# 画面红线：负向词里必须拦住的东西
RED_LINE_NEG = ["二维码", "logo", "水印"]
# 提示词里出现这些词，要人确认不是医疗对比 / 血腥 / 擦边
DANGER_PROMPT = ["伤口", "血迹", "前后对比", "裸露", "低胸", "床戏"]
# 授权表必填字段
AUTH_FIELDS = ["real_person", "minor", "brand_logo", "medical_claim"]
# 声音三件套：台词（或 silent_reason）+ 环境音 + 配乐（或 no_music_reason）
SOUND_WORDS = ["声音", "音效", "环境音", "底噪"]
MUSIC_WORDS = ["BGM", "配乐", "音乐", "non_diegetic"]
# 每一镜都要推进剧情
BEAT_REQUIRED = True
# 后续镜必须有「接上一镜」衔接
CONTINUE_WORDS = ["接上一镜", "从上一镜", "接着上一镜", "衔接上一镜"]
# 后续镜必须有「全局保持」重申共享锚点
GLOBAL_HOLD_WORDS = ["全局保持"]
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


def has_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def extract_global_hold_line(prompt: str) -> str | None:
    """从后续镜 prompt 开头提取「全局保持：...」这一行。"""
    for line in (prompt or "").split("\n")[:5]:
        if "全局保持" in line:
            return line
    return None


def strip_global_hold(prompt: str) -> str:
    """去掉「全局保持」行，取后续独有内容。"""
    return "\n".join(
        line for line in (prompt or "").split("\n")
        if "全局保持" not in line
    )


def check(data: dict, require_review: bool = True) -> list[str]:
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

    review = meta.get("review")
    if not require_review:
        pass
    elif not isinstance(review, dict):
        problems.append("meta.review 缺失：故事和提示词都得先给用户看，过了再置 true")
    else:
        for key, label in (("story_approved", "故事"), ("prompts_approved", "提示词")):
            if review.get(key) is not True:
                problems.append(
                    f"meta.review.{key} 不是 true —— {label}还没给用户看、或用户还没说「可以」；先回去让他审"
                )

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

    global_identity = (data.get("global_identity_anchor") or "").strip()
    global_light = (data.get("global_light_base") or "").strip()

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
        is_first = bool(s.get("is_first")) or (i == 0)

        if BEAT_REQUIRED and not beat:
            problems.append(f"{where}: 缺少 beat（这一镜推进了什么剧情），容易变成并列画面")

        # ===== 新门禁逻辑：首镜 vs 后续镜 =====

        if is_first:
            # 首镜：必须包含完整共享字段
            if style_anchor and style_anchor not in prompt:
                problems.append(f"{where}: 首镜 prompt 必须包含完整风格锚「{style_anchor}」")
            if global_identity and global_identity not in prompt:
                problems.append(f"{where}: 首镜 prompt 必须包含完整身份锚点「{global_identity}」")
            # 光线关键词：至少有一个
            if not has_any(prompt, LIGHT_WORDS):
                problems.append(f"{where}: 首镜 prompt 里没有光线关键词")
        else:
            # 后续镜：必须有「全局保持」行 + 「接上一镜」行
            global_hold = extract_global_hold_line(prompt)
            if not global_hold:
                problems.append(
                    f"{where}: 后续镜没有「全局保持」行——模型不知道这是同一个人、同一个世界"
                )
            else:
                # 全局保持行里至少有共享锚点的关键词
                if style_anchor:
                    anchor_keywords = [w for w in style_anchor.split("、") if w.strip()]
                    if not any(kw in global_hold for kw in anchor_keywords[:2]):
                        problems.append(
                            f"{where}: 「全局保持」行里没有风格锚关键词——必须重申共享锚点"
                        )
                if not has_any(global_hold, LIGHT_WORDS):
                    problems.append(
                        f"{where}: 「全局保持」行里没有光线关键词——必须重申光线基调"
                    )

            if not has_any(prompt[:200], CONTINUE_WORDS):
                problems.append(f"{where}: 后续镜没写「接上一镜」，动作接不上")

            # 检查"全局保持"之后的独有内容，不能和上一镜独有内容重复
            curr_unique = strip_global_hold(prompt).strip()[:60]
            prev_unique = strip_global_hold(prev_prompt).strip()[:60]
            if curr_unique and curr_unique == prev_unique:
                problems.append(
                    f"{where}: 独有内容和上一镜重复——换动作、换构图、换景别"
                )

        prev_prompt = prompt

        # ===== 危险词 / 详细度（所有镜） =====

        for word in DANGER_PROMPT:
            if word in prompt:
                problems.append(f"{where}: prompt 出现「{word}」，确认不是医疗对比/血腥/擦边镜头")
        if not prompt:
            problems.append(f"{where}: 缺少 prompt")
        else:
            if len(prompt) < DETAIL_MIN:
                problems.append(f"{where}: prompt 只有 {len(prompt)} 字，至少 {DETAIL_MIN} 字才算写细")
            if not has_any(prompt, CAMERA_WORDS):
                problems.append(f"{where}: prompt 里没有镜头词（景别或运镜）")
            if not has_any(prompt, LIGHT_WORDS):
                problems.append(f"{where}: prompt 里没有光线词")
            if not has_any(prompt, COMPOSITION_WORDS):
                problems.append(f"{where}: prompt 里没有构图（主体位置 / 留白 / 前景）")
            if not has_any(prompt, TEXTURE_WORDS):
                problems.append(f"{where}: prompt 里没有质感（材质 / 颗粒 / 锐度 / 调色）")
            for w in VAGUE_WORDS:
                if w in prompt:
                    problems.append(f"{where}: 出现模糊词「{w}」，换成可拍参数")
            if not has_any(prompt, CONSTRAINT_WORDS):
                problems.append(f"{where}: prompt 里没有约束层（防崩），至少写一句")

        # ===== 台词检查 =====

        line = (s.get("line") or "").strip()
        silent = bool(s.get("silent"))
        if not line and not silent:
            problems.append(f"{where}: 缺少 line（台词），视频会没声音；没有台词就标 silent: true")
        if line and not silent and norm(line) not in norm(prompt):
            problems.append(f"{where}: 台词没写进 prompt，生成时模型不知道说什么；把台词原文放进「声音」段")
        if line and not silent and not (s.get("character_refs") or []):
            problems.append(f"{where}: 有台词但没写 character_refs，不知道谁在说")
        if line and not silent and not has_any(prompt, SPEAK_WORDS):
            problems.append(
                f"{where}: 有台词，但画面没写「在说话」——生成出来人不会张嘴，后配音也对不上"
            )

        # ===== 声音三件套 =====
        if not has_any(prompt, SOUND_WORDS):
            problems.append(f"{where}: prompt 里没有「声音」段——台词 / 环境音 / 配乐都得写")
        says_no_music = any(w in prompt for w in ("无配乐", "无音乐", "不要配乐", "不要音乐", "不加配乐"))
        has_music = has_any(prompt, MUSIC_WORDS) and not says_no_music
        if not has_music and not (s.get("no_music_reason") or "").strip():
            problems.append(f"{where}: 没写配乐（BGM / 配乐 / 音乐）；真不要音乐就写 no_music_reason")
        if silent and not (s.get("silent_reason") or "").strip():
            problems.append(f"{where}: 标了 silent 但没写 silent_reason——为什么这一镜没台词？")

        # ===== 负向词 / 角色引用 =====

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
            match_on = h.get("match_on") or []
            if len(match_on) < 2:
                problems.append(
                    f"{tag}: match_on 至少写 2 个（wardrobe + lighting 几乎永远要有），否则模型换脸/换衣服"
                )
    elif handoffs:
        problems.append("单条模式不需要 handoffs，删掉或改成 multi")

    if shots and all(
        bool(s.get("silent")) or not (s.get("line") or "").strip() for s in shots
    ):
        if not (meta.get("no_dialogue_reason") or "").strip():
            problems.append(
                "全片没有一个镜头有台词——故事里真没人说话就写 meta.no_dialogue_reason，"
                "否则回去把 story.md 里的台词补成 line（常见错误：把「她说了两句」当动作）"
            )

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


def self_test() -> int:
    """验证门禁本身：模板结构合法；未审核的分镜必须被拦住。"""
    data = load(SAMPLE)
    baseline = check(data, require_review=False)
    if baseline:
        print("[SELF-TEST FAIL] 模板结构本身不过门禁：")
        for p in baseline:
            print(f"  - {p}")
        return 1

    data.setdefault("meta", {})["review"] = {"story_approved": False, "prompts_approved": False}
    problems = check(data, require_review=True)
    review_hits = [p for p in problems if "meta.review" in p]
    others = [p for p in problems if "meta.review" not in p]
    if others or len(review_hits) != 2:
        print("[SELF-TEST FAIL] 未审核的分镜应该只报 2 条 review 问题：")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("[SELF-TEST PASS] 模板结构合法；未审核的分镜被拦住（2 条 review 问题）")
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if "--self-test" in argv:
        return self_test()
    require_review = "--sample" not in argv
    args = [a for a in argv if not a.startswith("-")]
    if "--sample" in argv or not args:
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

    if not require_review:
        print("[INFO] --sample：只验结构，跳过 review 门禁")
    problems = check(data, require_review=require_review)
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
