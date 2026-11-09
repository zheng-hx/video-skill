# 自媒体 / 直播技能包（video-design-skills）

> 给「做文案、做视频、招主播」这几件活配的一套技能。
>
> **装一个，得到四个。** 对外只有一个入口技能，初始化时自动装出四个。
>
> **零依赖**：不绑定任何 AI 宿主、不需要装任何软件、不需要任何账号。
> 有工具给成品，没工具给「照着就能做」的制作包——两种都算完成。

## 装一次，得到四个技能

| 技能 | 管什么 |
|---|---|
| **`copy-video-studio`** | 文案：招募 / 带货 / 种草 / 人设 / 秀场话术 |
| **`video-studio`** | 文案 → 完整故事 → 分镜 → 逐镜提示词 → 衔接 → 生成或交接 |
| **`live-media-ops`** | 招主播：JD / 渠道话术 / 筛选 / 面试打分 |
| **`live-media-router`** | 领域入口：意图识别与分流，不出稿 |

## 安装

```bash
# 1. 装入口技能（或直接把仓库放好）
skillhub install video-design-skills

# 2. 初始化：渲染四个技能到 ~/.video-design/
cd <技能所在目录>          # 装在哪进哪，比如 ~/.claude/skills/video-design-skills
python3 scripts/render-package.py

# 3. 注册：只接到你在用的那个工具上
python3 scripts/reconcile-skills.py --list
python3 scripts/reconcile-skills.py --tool "Claude Code"
```

装完在工作台里：

```text
~/.video-design/
├── video.json
└── skills/
    ├── copy-video-studio/
    ├── video-studio/
    ├── live-media-ops/
    └── live-media-router/
```

**没有宿主也行**：直接打开对应技能的 `SKILL.md` 照着走，模板在 `assets/`，方法论在 `references/`。

## 目录

```text
video-design-skills/
├── skills/
│   └── video-design-skills/          # 唯一入口
│       ├── SKILL.md                  # 初始化 / 注册 / 诊断
│       ├── capabilities/             # 四个技能
│       │   ├── copy-video-studio/
│       │   ├── video-studio/
│       │   ├── live-media-ops/
│       │   └── live-media-router/
│       ├── shared/                   # 预留：公共参考
│       ├── scripts/
│       │   ├── render-package.py     # 渲染到工作台
│       │   └── reconcile-skills.py   # 注册到工具目录
│       └── tool-dirs.json
├── evals/                            # 7 条行为评测 + 参考产物
├── scripts/                          # 公共校验
├── docs/                             # 给人看的文档
├── package.json
└── CHANGELOG.md
```

## 校验

```bash
npm run check             # 结构：frontmatter / 引用完整性 / description 长度
npm run check-evals       # 评测定义本身是否完整
npm run check-triggers    # 触发词金标集覆盖
npm run check-storyboard  # 分镜与衔接门禁（拿自带模板验）
npm run run-evals         # 判卷（evals/runs/ 里有参考产物，应当 7 条全过）
npm run render            # 渲染到 ~/.video-design/
npm run reconcile         # 注册到本机 AI 工具
npm run check:all         # 全跑
```

## 设计原则

1. **知道就不问，不知道就问**：已知或能推断的不问，标假设；不知道且缺了会返工的必须问清楚。文案改一版便宜，视频生成贵，所以视频的必问项更多。
2. **一个动作**：用的人可能不懂技术，每轮只让他做一个动作。
3. **两种交付**：有工具出成片，没工具给制作包，不假装、也不卡住。
4. **衔接靠合同，不靠形容词**：首尾状态写成可见事实，禁止「保持连续」「同上」。
5. **门禁能脚本查的交给脚本**：查不了的写成人查清单，不硬装自动。
6. **可验证**：评测写「怎么算对」，不写「写得好」。
