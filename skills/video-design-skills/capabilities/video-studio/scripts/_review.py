"""_review.py — 审批内容的指纹（approve.py 与 check-storyboard.py 共用）。

指纹只覆盖「用户要审的东西」：风格锚、角色卡、每镜提示词/台词/负向词/时长、
衔接合同、收尾。改任何一处，指纹就变——审批自动失效。
"""
from __future__ import annotations

import hashlib
import json

SHOT_FIELDS = ("id", "prompt", "line", "silent", "silent_reason",
               "negative", "duration", "start", "end", "beat")


def reviewed_payload(data: dict) -> str:
    keep = {
        "style_anchor": data.get("style_anchor"),
        "characters": data.get("characters"),
        "shots": [{k: s.get(k) for k in SHOT_FIELDS} for s in data.get("shots", [])],
        "handoffs": data.get("handoffs"),
        "ending": data.get("ending"),
    }
    return json.dumps(keep, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(data: dict) -> str:
    return hashlib.sha256(reviewed_payload(data).encode("utf-8")).hexdigest()
