# 外部生态与复用清单 (Ecosystem)

> 本文件汇总开发 `live-media-ops` 时参考的 GitHub 同类项目，标注「可复用 / 仅参考」，避免重复造轮子。本 Skill 聚焦三大核心（招主播 + 通用文案框架 + 视频生产路线），平台细分能力优先复用下列生态。

## 可直接复用的 Skill / 合集

| 项目 | 地址 | 类型 | 复用方式 |
|---|---|---|---|
| **lqmeter/awesome-social-media-skills** | github.com/lqmeter/awesome-social-media-skills | 自媒体运营 Skill 合集，跨宿主通用（WorkBuddy / Claude Code / Codex / 千问 / 豆包 …） | **优先复用**：公众号排版发布、抖音 / 视频号文案、剪辑等平台细分 Skill，不本 Skill 内重造 |
| songguoxs/seedance-prompt-skill | github.com/songguoxs/seedance-prompt-skill | 即梦 / Seedance 视频提示词工程 skill | 借鉴其时间戳分镜、负向提示词、多段拼接，已折入 `video-gen.md` 路线 B1 |
| smixs/visual-skills（video） | github.com/smixs/visual-skills | 导演 / 编剧 / 剪辑三合一，薄 SKILL.md + 厚 references | **结构范式**：本 Skill 已采用 |
| RichardBray/skills | github.com/RichardBray/skills | 细粒度单功能（shorts-writer / video-script / short-edit / title-score …） | 颗粒度参考 |

## 仅作参考（不直接依赖）

| 项目 | 地址 | 说明 | 备注 |
|---|---|---|---|
| harry0703/MoneyPrinterTurbo（137k★） | github.com/harry0703/MoneyPrinterTurbo | 一键短视频流水线：脚本→素材(Pexels)→配音(EdgeTTS)→字幕→合成 | 可选自托管整链路，已作为 `video-gen.md` 路线 C 提及；要求本地 ffmpeg / ImageMagick |
| Utopai-Research/pai-pro | github.com/Utopai-Research/pai-pro | workflow skill 编排 capability skills | "工作流 vs 能力 skill" 拆分思路参考 |
| AIPMAndy/Andy-Video-SKill | github.com/AIPMAndy/Andy-Video-SKill | 12 个视频方法 skill 的内容库 | 内容库模式参考 |

## 数字人开源方案（仅背景知识，禁止本地依赖）

下列是数字人 / 口型驱动的开源项目，通常是数字人平台背后的技术。**本 Skill 一律走"平台 / 服务"，不应假设最终用户本地部署这些模型**：

- **LatentSync**（bytedance）：高精度音频驱动口型同步，字节开源。
- **Hallo3**（fudan-generative-vision）：高保真面部驱动，复旦出品。
- **EchoMimic V2**（阿里蚂蚁）：表情与动作模仿，拟真人。
- **MuseTalk / MuseV / LiveTalking**（TMElyralab 等）：口型同步 + 实时交互数字人生态。
- **AigcPanel / HeyGem**：一站式数字人 / 声音克隆桌面工具（仍属本地部署，非必需）。

> 结论：数字人能力在用户侧应体现为"平台 API / 网页服务"，而非本机跑模型。视频生成平台若原生支持口型（Kling 3.0 / Veo / 即梦）也归入"服务调用"范畴，见 `video-gen.md` 路线 A2。
