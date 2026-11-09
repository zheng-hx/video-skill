---
name: live-media-ops
slug: live-media-ops
displayName: 主播招募
version: 0.4.2
description: 主播招募专项。招主播、写主播 JD、设计渠道话术、筛选简历、面试评估、候选人打分。当用户提到招主播 / 主播招募 / 主播 JD / 主播面试 / 候选人筛选 / 面试打分时使用。写文案交给 copy-video-studio，做视频交给 video-studio。
---

# 直播运营工作室 · 招募线 (live-media-ops)

> 本技能现在的定位是**招募线**：招主播、写 JD、渠道话术、筛选、面试。
> 文案已经拆到 `copy-video-studio`，视频已经拆到 `video-studio`。下面「写文案」「生成视频」两节保留作旧版参考，不再作为触发入口。

## 通用 Skill 说明（重要）

**本 Skill 零依赖**：不绑定任何 AI 宿主、不需要装任何软件、不需要任何账号。最极端的情况——用户机上什么都没有——把 `SKILL.md` 和 `references/` 读一遍，里面的模板、清单、话术也能直接用；哪怕没有一个 AI 宿主，人工照着做也成立。

- 交付物分两种形态：**有工具给成品，没工具给能直接执行的制作包**（详见 `references/no-tools.md`）。
- 三大环节的**核心是可移植的方法论 + 模板 + 清单**，与具体工具无关。
- 涉及「生图 / 生视频 / 数字人」时，只规定**做什么、产出什么、可选的服务路线**，工具由两处提供：
  1. **当前 AI 宿主自带的能力**：若所在环境提供生图 / 生视频 / 数字人工具，直接调用；
  2. **用户侧外部服务**：否则引导用户使用外部平台（见 `references/video-gen.md` 的路线清单：剪映 / 即梦 / HeyGen / 腾讯智影 / D-ID / 可灵 等）。
- **不假设用户机装了 ffmpeg / torch / 任何本地模型，也不假设装了剪映**。`scripts/composite_digital_human.sh` 仅是**可选**的本地合成助手；没有 ffmpeg 时它会给出替代路线，不会中断流程。
- **真·数字人对口型有两条路**（详见 `references/video-gen.md`）：① 数字人平台（HeyGen / 腾讯智影 / 即梦 / 剪映 / D-ID 等）；② 部分高端视频生成平台已原生支持口型同步（Kling 3.0 / Veo / 即梦）。通用生视频工具做不到精确对口型。

## 最快上手

- **有 AI 宿主**：把本目录作为技能加载，说「按 live-media-ops 帮我做 XX」。
- **没有宿主**：直接打开 `SKILL.md` 照着走；模板在 `assets/`，方法论在 `references/`。
- **什么都没有**：把 `references/no-tools.md` 给对方看，照着剪映步骤也能做出片。

## 何时使用本 Skill

- **招主播**：主播招募、写主播 JD、设计渠道话术、简历筛选、面试评估、候选人打分
- **写文案**：抖音 / 快手 / 视频号 / 小红书的口播脚本、短视频脚本、种草文案、带货话术
- **生成视频**：把文案转分镜 / 制作 brief、数字人口播、视频剪辑规范
- **串联**：从主播招募一路走到视频产出

## 外部生态与复用（可选，不重复造轮子）

本 Skill 聚焦「招主播 + 通用文案框架 + 视频生产路线」三大核心。平台细分能力（公众号排版、抖音 / 视频号文案、剪辑等）已有成熟第三方 Skill 合集，直接复用即可，见 `references/ecosystem.md`：

- **`lqmeter/awesome-social-media-skills`**：自媒体运营 Skill 合集，跨宿主通用（WorkBuddy / Claude Code / Codex / 千问 / 豆包…），覆盖各平台选题、写稿、配图、发布、数据——按需取用，不要在本 Skill 内重造。
- **`smixs/visual-skills`**：视频 Skill 结构范式（薄 SKILL.md + 厚 references），本 Skill 已采用。
- **数字人开源方案（LatentSync / Hallo3 / EchoMimic / MuseTalk）**：仅作平台背后技术背景，**不本地依赖**。

## 核心约定

- **跨环节上下文**：主播画像（host profile）→ 决定文案调性；文案（script）→ 直接生成视频 brief。串联时自动向下游传递，不重复索要。
- **约束遵循**：若用户给定品牌 / 平台 / 合规等约束则严格遵循；未给定时按通用写法，但合规红线始终生效（见注意事项）。
- **模板驱动**：交付物基于 `assets/` 下的模板填充（JD 模板、脚本模板、视频 brief 模板）。
- **合规优先**：涉及广告法 / 平台规则（极限词、医疗宣称、导流等）必须显式标红提示，不得遗漏。

## 工作流分流

| 用户意图 | 走哪个工作流 | 参考 | 模板 |
|---|---|---|---|
| 招主播 / JD / 面试 / 筛选 | ① 招主播 | `references/host-recruit.md` | `assets/host-jd-template.md` |
| 写文案 / 脚本 / 话术 | ② 写文案 | `references/copywriting.md` | `assets/script-template.md` |
| 生成视频 / brief / 分镜 | ③ 生成视频 | `references/video-gen.md` | `assets/brief-template.md` |
| 招完直接做内容 | ① → ② → ③ 串联 | 依次加载上述 | 依次填充 |

## 工作流程

### ① 招主播 (host-recruit)

详细方法论、画像维度、筛选规则、面试评估表见 `references/host-recruit.md`。简版步骤：

1. 明确岗位类型（带货 / 秀场 / 知识 / 本地生活 …）与主播画像。
2. 套 `assets/host-jd-template.md` 生成招募 JD。
3. 产出渠道招募话术、简历筛选 checklist、面试评估表与打分卡。
4. 沉淀候选人档案（人设、调性、适配平台），落 `output/<日期>-<主题>/host-profile.md`。

### ② 写文案 / ③ 生成视频（已迁出）

这两个环节已拆成独立技能：

- **写文案** → `copy-video-studio`，产出 `script.md`
- **做视频** → `video-studio`，读 `script.md` 出分镜和提示词

本技能不执行这两步。旧版方法留在 `references/copywriting.md` 和 `references/video-gen.md`，仅作参考，不作为触发入口。

### 串联流水线

用户说「从招人一直到出片」时，按顺序交接：

1. 本技能：招主播 → JD / 档案 / 面试
2. `copy-video-studio`：写文案 → `script.md`
3. `video-studio`：分镜 + 提示词 + 生成

每段产物落盘到 `output/<YYYY-MM-DD>-<一句话主题>/`，下游读文件，不靠对话记忆。

### 输出约定

```text
output/<YYYY-MM-DD>-<一句话主题>/
├── handoff.md       # 环节交接单
├── host-jd.md       # ① 招募 JD
├── host-profile.md  # ① 候选人档案
├── script.md        # ② 脚本（copy-video-studio 产出）
└── storyboard.json  # ③ 分镜（video-studio 产出）
```

> 环境存不了文件时，跳过落盘，直接在对话里给完整成品并说明「复制走」。

## Resources

### references/

- `host-recruit.md`：招主播全流程方法论与评估维度
- `copywriting.md`：分平台文案范式与话术库
- `video-gen.md`：视频生产路线（数字人平台 / 支持口型的视频生成平台 / 通用生视频 / 可选本地合成）与分镜规范
- `no-tools.md`：**零工具降级路线**——没有 ffmpeg / 数字人平台 / 文件写入权限时怎么交付
- `compliance.md`：合规红线（极限词 / 功效宣称 / 导流 / 用工）与**统一标红格式**
- `ecosystem.md`：外部生态与复用清单（GitHub 同类参考、平台细分 Skill、数字人背景）

### assets/

- `host-jd-template.md`：主播招募 JD 模板
- `script-template.md`：口播 / 短视频脚本模板
- `brief-template.md`：视频制作 brief 模板
- `handoff-template.md`：环节交接单模板（串联时必填，下游靠它取上下文）

### scripts/

- `composite_digital_human.sh`：**可选**本地合成助手（需用户机有 ffmpeg）。把「数字人层 + 公司视频」合成为成片，支持 `pip` / `split` / `background` 三种布局，可选配音与字幕。非必需，详见 `references/video-gen.md`。
- `check-skill.py`：自检脚本。校验 frontmatter、引用是否都存在、TODO 残留、脚本语法、版本号一致性。改完技能跑一遍：`python3 scripts/check-skill.py`。

## 注意事项

- 广告法 / 平台合规红线见 `references/compliance.md`：极限词、功效宣称、站外导流、用工承诺。所有合规问题一律按该文件的统一格式标红（`【合规·禁用/风险/待确认】原句 → 改法`），不得各写各的。
- 本 Skill **不假定任何宿主内置工具或用户机本地软件**；生图/生视频/数字人按 `references/video-gen.md` 的路线清单由环境或用户侧提供。
- 引用模板与参考时，走相对路径 `assets/...` / `references/...`，保持技能可移植。
