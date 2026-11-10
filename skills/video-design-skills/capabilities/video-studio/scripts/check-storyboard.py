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
    python3 scripts/check-storyboard.py storyboard.json              # 默认：强制人工审批（要 content_hash）
    python3 scripts/check-storyboard.py storyboard.json --content-only # 用户审核前自审：只验内容
    python3 scripts/check-storyboard.py storyboard.json --no-strict  # 旧产物过渡：只认 true，不认指纹
    python3 scripts/check-storyboard.py --sample                     # 只验模板结构
    python3 scripts/check-storyboard.py --self-test                  # 验证门禁本身

台词对账：如果 storyboard.json 同目录有 story.md，会自动读它反查台词——
故事里有引号台词 / 口播 / 对白，分镜却一句 line 都没有，直接判台词漏了。

退出码：0 = 通过，1 = 有问题，3 = 用法错误
"""
from __future__ import annotations

import copy
import json
import re
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _review import content_hash  # noqa: E402

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
# 正向 prompt 里也不许「既要又要」：这些词前面没有否定词就是要
NEG_PREFIX = ("无", "不", "别", "没", "禁止", "去除", "去掉", "消除")
# 提示词里不许出现的跨镜空话（衔接靠 handoffs，不靠 prompt）
PROMPT_FILLER = ["保持连续", "同上", "同前", "照旧", "照搬上一镜"]
# ending.end_state 里的收尾空话
ENDING_FILLER = ["画面收尾", "自然收尾", "自然结束", "平稳结束", "完整收尾", "干净收尾"]
# 提示词里出现这些词，要人确认不是医疗对比 / 血腥 / 擦边
DANGER_PROMPT = ["伤口", "血迹", "前后对比", "裸露", "低胸", "床戏"]
# 授权表必填字段
AUTH_FIELDS = ["real_person", "minor", "brand_logo", "medical_claim"]
# 声音三件套：台词（或 silent_reason）+ 环境音 + 配乐（或 no_music_reason）
SOUND_WORDS = ["声音", "音效", "环境音", "底噪"]
MUSIC_WORDS = ["BGM", "配乐", "音乐", "non_diegetic"]
# 通用化理由黑名单：这些话等于没写，模型靠它们绕过台词/配乐门禁
GENERIC_REASON = [
    "无台词", "没台词", "没有台词", "不需要台词", "不用台词",
    "静默", "无声", "没声音", "不需要声音", "不用声音",
    "纯画面", "画面展示", "环境展示", "空镜", "无音乐", "不需要音乐",
    "没配乐", "无配乐", "背景音乐",
]
# 合法理由至少要这么长（写清楚"为什么这一镜没台词/没配乐"，不是一句"无台词"）
REASON_MIN_LEN = 12
# 对话审批时，用户那句确认里至少要出现一个明确的肯定词
CHAT_CONFIRM_WORDS = ("可以", "好", "确认", "没问题", "继续", "行", "ok", "OK")
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


def check(
    data: dict,
    require_review: bool = True,
    strict: bool = True,
    story_text: str | None = None,
) -> list[str]:
    problems: list[str] = []

    if not isinstance(data, dict):
        return ["storyboard 顶层必须是 JSON 对象"]

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
        stored = review.get("content_hash")
        if stored:
            if stored != content_hash(data):
                problems.append(
                    "审批后内容被改过（content_hash 对不上）——这次审批已作废，"
                    "重新给用户看改过的部分，他说「可以」后再跑一次 scripts/approve.py"
                )
        if strict:
            if not stored:
                problems.append(
                    "强制审核要求 meta.review.content_hash —— 没有审批记录。做法："
                    "把故事和提示词摊给用户看，他明确说「可以」后，由技能自己跑 "
                    "scripts/approve.py --chat --quote \"<用户原话>\""
                    "（用户不必开终端；没说「可以」就不许跑）"
                )
            else:
                by = review.get("approved_by")
                if by == "user-tty":
                    pass
                elif by == "user-chat":
                    quote = (review.get("confirmed_quote") or "").strip()
                    if not quote:
                        problems.append(
                            "对话审批缺 confirmed_quote —— 必须原样记录用户说「可以」的那句话，"
                            "不许自己编"
                        )
                    elif not any(w in quote for w in CHAT_CONFIRM_WORDS):
                        problems.append(
                            f"confirmed_quote 里没有明确的肯定词（当前 {quote!r}）——"
                            "用户没说「可以 / 好 / 确认 / 没问题 / 继续」就不算审批通过"
                        )
                else:
                    problems.append(
                        f"meta.review.approved_by 只能是 user-tty 或 user-chat，当前是 {by!r}"
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
    if not isinstance(shots, list):
        return problems + ["shots 必须是数组"]
    bad_shots = [i + 1 for i, s in enumerate(shots) if not isinstance(s, dict)]
    if bad_shots:
        return problems + [
            f"shots 第 {i} 个镜头不是对象（每个镜头必须是 {{...}}）" for i in bad_shots
        ]
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
        if line and not silent and s.get("duration"):
            # 按最长的单句算语速：多人口播合在一起会把平均值拉低，看不出问题
            longest = max(
                (
                    re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", seg.split("：")[-1].split(":")[-1])
                    for seg in line.split()
                ),
                key=len,
                default="",
            )
            rate = len(longest) / float(s["duration"])
            if rate > 8:
                problems.append(
                    f"{where}: 最长一句 {len(longest)} 字塞进 {s['duration']} 秒（每秒 {rate:.1f} 字），"
                    "正常口播 5–6 字/秒，超过 8 字/秒基本说不完；加时长或删字"
                )

        # ===== 声音三件套 =====
        if not has_any(prompt, SOUND_WORDS):
            problems.append(f"{where}: prompt 里没有「声音」段——台词 / 环境音 / 配乐都得写")
        says_no_music = any(w in prompt for w in ("无配乐", "无音乐", "不要配乐", "不要音乐", "不加配乐"))
        has_music = has_any(prompt, MUSIC_WORDS) and not says_no_music
        no_music_reason = (s.get("no_music_reason") or "").strip()
        if not has_music and not no_music_reason:
            problems.append(f"{where}: 没写配乐（BGM / 配乐 / 音乐）；真不要音乐就写 no_music_reason")
        elif not has_music and no_music_reason:
            if len(no_music_reason) < REASON_MIN_LEN or no_music_reason in GENERIC_REASON:
                problems.append(
                    f"{where}: no_music_reason 太敷衍（「{no_music_reason}」）——"
                    "写清楚为什么这一镜不要配乐，比如『全程只有环境音，突出人物独处的压抑感』"
                )
        if silent:
            silent_reason = (s.get("silent_reason") or "").strip()
            if not silent_reason:
                problems.append(f"{where}: 标了 silent 但没写 silent_reason——为什么这一镜没台词？")
            elif len(silent_reason) < REASON_MIN_LEN or silent_reason in GENERIC_REASON:
                problems.append(
                    f"{where}: silent_reason 太敷衍（「{silent_reason}」）——"
                    "写清楚为什么这一镜没人说话，比如『她还没鼓起勇气开口，只有呼吸声』；"
                    "故事里有人在说话就不许标 silent"
                )

        # ===== 负向词 / 角色引用 =====

        negative = (s.get("negative") or "").strip()
        if not negative:
            problems.append(f"{where}: 缺少 negative（负向词）")
        else:
            for word in RED_LINE_NEG:
                if word.lower() not in negative.lower():
                    problems.append(f"{where}: 负向词缺「{word}」（画面红线）")

        prompt_text = s.get("prompt") or ""
        for word in PROMPT_FILLER:
            if word in prompt_text:
                problems.append(
                    f"{where}: prompt 里出现衔接空话「{word}」——"
                    "衔接写进 handoffs 的 end_state/next_start_state，prompt 只写这一镜看得见的内容"
                )
        lower_prompt = prompt_text.lower()
        for word in RED_LINE_NEG:
            idx = lower_prompt.find(word.lower())
            while idx != -1:
                prefix = lower_prompt[max(0, idx - 4):idx]
                if not any(p in prefix for p in NEG_PREFIX):
                    problems.append(
                        f"{where}: prompt 里要「{word}」——负向词说不要、正向词却要，自相矛盾"
                    )
                    break
                idx = lower_prompt.find(word.lower(), idx + 1)
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
        no_dlg = (meta.get("no_dialogue_reason") or "").strip()
        if not no_dlg:
            problems.append(
                "全片没有一个镜头有台词——故事里真没人说话就写 meta.no_dialogue_reason，"
                "否则回去把 story.md 里的台词补成 line（常见错误：把「她说了两句」当动作）"
            )
        elif len(no_dlg) < REASON_MIN_LEN or no_dlg in GENERIC_REASON:
            problems.append(
                f"meta.no_dialogue_reason 太敷衍（「{no_dlg}」）——"
                "全片没人说话是很反常的，必须写清楚为什么："
                "比如『纯风景展示片，无人出镜』；故事里有人在说话就不许全片 silent"
            )

    # 台词对账：拿 story.md 反查，堵住「把整片静默当捷径」的口子
    if story_text and shots:
        quotes = re.findall(r"[「“\"]([^」”\"]{4,})[」”\"]", story_text)
        speech_cue = any(
            k in story_text
            for k in ("口播", "对白", "独白", "对着镜头说", "她说", "他说", "录视频", "说话")
        )
        has_line = any((s.get("line") or "").strip() for s in shots)
        no_dlg_reason = (meta.get("no_dialogue_reason") or "").strip()
        if (len(quotes) >= 2 or speech_cue) and not has_line and not no_dlg_reason:
            problems.append(
                f"story.md 里明显有人说话（引号台词 {len(quotes)} 处 / 口播对白线索），"
                "分镜却一句 line 都没有——台词漏了，回去把 story.md 的话逐句抄进对应镜的 line；"
                "真不说话就在 meta.no_dialogue_reason 写清楚为什么"
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
            for word in ENDING_FILLER:
                if word in end_state:
                    problems.append(f"ending.end_state 出现空话「{word}」，要写成最后一帧看得见的画面")

    return problems


def self_test() -> int:
    """验证门禁本身：结构合法、未审核被拦、伪造 true 在 strict 下被拦、审批后改动失效。"""
    def fail(title: str, problems: list[str]) -> int:
        print(f"[SELF-TEST FAIL] {title}")
        for item in problems:
            print(f"  - {item}")
        return 1

    data = load(SAMPLE)

    baseline = check(data, require_review=False)
    if baseline:
        return fail("模板结构本身不过门禁：", baseline)

    # 坏结构不许崩，要报错
    broken = copy.deepcopy(data)
    broken["shots"][1] = 123
    try:
        broken_problems = check(broken, require_review=False)
    except Exception as e:  # noqa: BLE001
        return fail(f"镜头不是对象时崩了：{type(e).__name__}: {e}", [])
    if not any("不是对象" in p for p in broken_problems):
        return fail("镜头不是对象应被报错：", broken_problems)

    # prompt 里写衔接空话 → 拦
    filler = copy.deepcopy(data)
    filler["shots"][0]["prompt"] += " 保持连续"
    if not any("衔接空话" in p for p in check(filler, require_review=False)):
        return fail("prompt 写「保持连续」应被拦：", check(filler, require_review=False))

    # 正向 prompt 要水印 → 拦；写「无水印」→ 放行
    watermark = copy.deepcopy(data)
    watermark["shots"][0]["prompt"] += " 右下角加个水印"
    if not any("自相矛盾" in p for p in check(watermark, require_review=False)):
        return fail("prompt 要水印应被拦：", check(watermark, require_review=False))
    no_watermark = copy.deepcopy(data)
    no_watermark["shots"][0]["prompt"] += "，无水印、无文字"
    if any("自相矛盾" in p for p in check(no_watermark, require_review=False)):
        return fail("prompt 写「无水印」不应误报：", check(no_watermark, require_review=False))

    # 台词对账：story 有人说话、分镜全静默 → 拦
    silent_board = copy.deepcopy(data)
    for s in silent_board["shots"]:
        s["line"] = ""
        s["silent"] = True
        s["silent_reason"] = "空镜过渡：人物还没入画，只有窗外车流声与远处人声"
    silent_board["meta"].pop("no_dialogue_reason", None)
    story_with_speech = "她说：「今天必须把这条录完。」\n她又说：「不行，再来一次。」"
    hits = check(silent_board, require_review=False, story_text=story_with_speech)
    if not any("台词漏了" in p for p in hits):
        return fail("story 有人说话、分镜全静默应被拦：", hits)
    hits = check(silent_board, require_review=False, story_text="纯风景片，无人出镜。")
    if any("台词漏了" in p for p in hits):
        return fail("story 没有台词线索时不应误报：", hits)

    forged = copy.deepcopy(data)
    forged["meta"]["review"] = {"story_approved": True, "prompts_approved": True}
    forged_problems = check(forged, require_review=True)
    if len(forged_problems) != 1 or "content_hash" not in forged_problems[0]:
        return fail("默认应因缺 content_hash 只报 1 条（伪造 true 不算过）：", forged_problems)

    approved = copy.deepcopy(forged)
    approved["meta"]["review"].update({
        "content_hash": content_hash(approved),
        "approved_by": "user-tty",
        "approved_at": "2026-11-10T17:00:00+08:00",
    })
    if check(approved, require_review=True):
        return fail("带指纹的真人审批应当通过：", check(approved, require_review=True))

    tampered = copy.deepcopy(approved)
    tampered["shots"][0]["prompt"] += "（偷偷改了一句）"
    tampered_problems = check(tampered, require_review=True)
    if len(tampered_problems) != 1 or "content_hash" not in tampered_problems[0]:
        return fail("审批后改内容应当报指纹不符：", tampered_problems)

    legacy = check(forged, require_review=True, strict=False)
    if legacy:
        return fail("--no-strict 应兼容旧的 true 写法：", legacy)

    chat = copy.deepcopy(forged)
    chat["meta"]["review"].update({
        "content_hash": content_hash(chat),
        "approved_by": "user-chat",
        "confirmed_quote": "可以，就按这个来",
    })
    if check(chat, require_review=True):
        return fail("对话审批（带用户原话）应当通过：", check(chat, require_review=True))

    chat_no_quote = copy.deepcopy(forged)
    chat_no_quote["meta"]["review"].update({
        "content_hash": content_hash(chat_no_quote),
        "approved_by": "user-chat",
    })
    problems = check(chat_no_quote, require_review=True)
    if not any("confirmed_quote" in p for p in problems):
        return fail("对话审批缺用户原话应被拦：", problems)

    chat_weak = copy.deepcopy(forged)
    chat_weak["meta"]["review"].update({
        "content_hash": content_hash(chat_weak),
        "approved_by": "user-chat",
        "confirmed_quote": "我再想想",
    })
    problems = check(chat_weak, require_review=True)
    if not any("肯定词" in p for p in problems):
        return fail("对话审批原话没有肯定词应被拦：", problems)

    fast = copy.deepcopy(data)
    fast["shots"][0]["duration"] = 2
    fast["shots"][0]["end"] = fast["shots"][0]["start"] + 2
    fast["shots"][0]["line"] = "我今天必须把这段话全部说完不然真的来不及了你们听清楚了吗"
    hits = check(fast, require_review=False)
    if not any("说不完" in p for p in hits):
        return fail("台词密度过高应被拦：", hits)

    print("[SELF-TEST PASS] 结构合法 / 坏结构不崩 / 衔接空话被拦 / 正向红线自相矛盾被拦 / "
          "story 台词对账生效且不误报 / 台词密度过高被拦 / 未审核被拦 / 伪造 true 被拦 / 审批后改动失效 / "
          "对话审批缺原话被拦 / 对话审批无肯定词被拦 / --no-strict 兼容旧写法")
    return 0


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="分镜 / 衔接 / 声音 / 审核门禁",
        usage="%(prog)s [storyboard.json] [--sample] [--content-only] [--no-strict] [--story story.md] [--self-test]",
    )
    ap.add_argument("file", nargs="?", help="storyboard.json 路径（位置参数）")
    ap.add_argument("--file", dest="file_opt", help="storyboard.json 路径（与位置参数二选一）")
    ap.add_argument("--story", help="story.md 路径（默认自动找同目录 story.md）")
    ap.add_argument("--sample", action="store_true", help="只验模板结构，跳过 review 门禁")
    ap.add_argument("--content-only", action="store_true", help="只验内容，不看审批（用户审核前自审用）")
    ap.add_argument("--no-strict", action="store_true", help="旧产物过渡：只认 true，不认审批记录")
    ap.add_argument("--self-test", action="store_true", help="验证门禁本身")
    try:
        args = ap.parse_args()
    except SystemExit as e:
        return 3 if e.code else 0

    if args.self_test:
        return self_test()

    if args.file and args.file_opt:
        print("✗ 位置参数和 --file 只能给一个")
        return 3

    require_review = not (args.sample or args.content_only)
    strict = not args.no_strict  # 默认就是强制审核；--no-strict 只给旧产物过渡
    target = args.file_opt or args.file
    if args.sample or not target:
        path = SAMPLE
    else:
        path = pathlib.Path(target)
    if not path.is_file():
        print(f"找不到文件：{path}")
        return 3
    try:
        data = load(path)
    except json.JSONDecodeError as e:
        print(f"JSON 不合法：{e}")
        return 3

    if not require_review:
        print("[INFO] 只验内容，跳过 review 门禁")

    story_text = None
    story_path = pathlib.Path(args.story) if args.story else path.parent / "story.md"
    if story_path.is_file():
        try:
            story_text = story_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            story_text = None
        if story_text:
            print(f"[INFO] 台词对账：已读 {story_path.name}")
    elif args.story:
        print(f"⚠ 找不到 --story 指定的文件：{story_path}")

    problems = check(data, require_review=require_review, strict=strict, story_text=story_text)
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
