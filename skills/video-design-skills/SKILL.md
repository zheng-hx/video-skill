---
name: video-design-skills
slug: video-design-skills
displayName: 自媒体 / 直播技能包（唯一入口）
version: 1.0.5
description: 自媒体 / 直播技能包的唯一入口：初始化时装出文案、视频、招募、路由四个技能，注册到本机 AI 工具目录；更新 / 诊断也走这里。当用户说「初始化视频技能 / 安装自媒体技能 / 技能没生效 / 更新视频技能」时使用。
---

# 自媒体 / 直播技能包 · 唯一入口

> **对外只有一个技能。** 装的是它，它负责把四个技能装到你的机器上。
> 你说「初始化」或「安装技能」，它就干活。

## 一句话分流

| 用户说 | 走哪段 |
|---|---|
| 初始化 / 安装 / 装一下技能 | ① 渲染工作台 |
| 技能没生效 / 换个工具也要用 | ② 注册到工具目录 |
| 更新 / 升级 / 重装 | ③ 更新 |

## 这套东西有什么

装完你会得到四个技能：

| 技能 | 管什么 |
|---|---|
| `copy-video-studio` | 写文案：招募 / 带货 / 种草 / 秀场话术 |
| `video-studio` | 文案 → 完整故事 → 分镜 → 逐镜提示词 → 衔接 → 生成或交接 |
| `live-media-ops` | 招主播：JD / 渠道话术 / 筛选 / 面试 |
| `live-media-router` | 领域入口：意图识别与分流 |

## 工作台

所有技能渲染到用户全局，只存一份：

```text
~/.video-design/
├── video.json              # 版本 / 渲染时间 / 技能清单
└── skills/
    ├── copy-video-studio/
    ├── video-studio/
    ├── live-media-ops/
    └── live-media-router/
```

**为什么放全局**：技能是通用能力，一份就够；放项目里每个项目都要重装。

## ① 初始化：渲染工作台

```bash
# 先进入技能目录（装在哪就进哪，比如 ~/.claude/skills/video-design-skills）
cd <技能所在目录>
python3 scripts/render-package.py
```

它做三件事：

1. 把 `capabilities/` 下四个技能复制到 `~/.video-design/skills/`；
2. 把 `shared/` 里的公共参考分发到需要的技能目录；
3. 写 `~/.video-design/video.json`（版本、时间、清单）。

已存在且版本相同就跳过；版本不同就覆盖，**不碰用户的产物**（`output/` 目录一律不动）。

## ② 注册：接到你的 AI 工具上

先探测本机有哪些工具目录：

```bash
cd <技能所在目录>
python3 scripts/reconcile-skills.py --list
```

**只装用户正在用的那一个**：

```bash
cd <技能所在目录>
python3 scripts/reconcile-skills.py --tool "Claude Code"
```

默认不装全部——往用户不用的工具里塞技能是污染。确实要装全部才加 `--all`。

它按 `tool-dirs.json` 探测本机装了哪些 AI 工具，把四个技能软链进选中的那个：

| 工具 | 目录 |
|---|---|
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.codex/skills/` |
| WorkBuddy | `~/.workbuddy/skills/` |
| Cursor | `~/.cursor/skills/` |
| 其他 | 查该工具的 skills 目录约定 |

**只对探测到的工具动手**，不存在的不建空目录。软链失败（比如跨盘）就复制。

## ③ 更新

```bash
cd <技能所在目录>
python3 scripts/render-package.py --force
python3 scripts/reconcile-skills.py
```

两步都跑一遍。升级只覆盖技能目录，不覆盖用户东西。

## 诊断

用户说「装了没反应」时，按这个查：

1. `~/.video-design/video.json` 在不在 → 不在就是没渲染
2. `~/.video-design/skills/` 下有四个目录吗 → 少了就重跑渲染
3. 他的 AI 工具目录里有没有软链 → 没有就重跑注册
4. 他的工具支不支持 skills 目录 → 不支持就把 SKILL.md content 贴进系统提示词

## 边界

- 只写 `~/.video-design/` 和探测到的工具技能目录。
- 不写工具根目录，不写别的工具的旧版路径。
- 不碰用户已有的技能（只增删自己产出的那四个）。
- 没有确认「用户要装」之前，不动手。

## 参考

- `scripts/render-package.py`：渲染
- `scripts/reconcile-skills.py`：注册与对账
- `tool-dirs.json`：工具目录规则
- `capabilities/`：四个技能的完整内容
