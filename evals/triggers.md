# 触发层金标集

> **目的**：技能的唯一发现依据是 `description`。这里回答两个问题：
> ① 用户说这句话，**期望的技能**描述里到底有没有能命中它的词？
> ② 两个技能的触发词有没有重叠（会互相抢触发）？

**说明**：本表是**词面覆盖**检查（`scripts/check-triggers.py`），不是「真跑模型看它选哪个技能」。
真跑需要宿主；本表同时也是**人工回归清单**——把「用户会说」原样投喂，看是否命中「期望技能」。

---

## 怎么用

1. **自动（CI）**：`npm run check-triggers` —— 校验每条用例的期望技能描述里确实含关键词之一；并打印各技能的触发短语供人看重叠。
2. **人工 / 宿主**：逐条把「用户会说」投喂一次，记录实际命中的技能；命中 ≠ 期望就回来修 description。

---

## 金标集

| # | 用户会说 | 期望技能 | 关键词（其一命中即算覆盖） |
|---|---|---|---|
| 1 | 帮我写条招主播的文案 | `copy-video-studio` | 写条文案 / 写个口播 / 文案 |
| 2 | 抖音带货口播给我来一条 | `copy-video-studio` | 写个口播 / 文案 |
| 3 | 这个面膜的种草文案怎么写 | `copy-video-studio` | 写条文案 / 文案 |
| 4 | 帮我做条视频，30 秒 | `video-studio` | 做个视频 / 视频 |
| 13 | 把这段文案做成视频 | `video-studio` | 把这段文案做成视频 / 做个视频 |
| 14 | 出个分镜我看看 | `video-studio` | 出个分镜 |
| 15 | 帮我生成视频提示词 | `video-studio` | 生成视频提示词 |
| 16 | 多段视频怎么接才不会跳 | `video-studio` | 多段怎么接 |
| 5 | 我新招了个女主播，帮我写条开播话术 | `copy-video-studio` | 写条文案 / 文案 |
| 6 | 再来一条，活泼点 | `copy-video-studio` | 再来一条 |
| 7 | 帮我招个主播，要能带货的 | `live-media-ops` | 招主播 |
| 8 | 写个主播招募 JD | `live-media-ops` | 招主播 / JD |
| 9 | 这三个候选人帮我排个序 | `live-media-ops` | 招主播 / 面试 |
| 10 | 我想做自媒体，从哪开始 | `live-media-router` | 自媒体 / 起号 |
| 11 | 这个账号该怎么运营 | `live-media-router` | 账号定位 / 起号 |
| 12 | 这活该找哪个技能 | `live-media-router` | 不确定该找哪个技能 / 领域入口 |

---

## 已知重叠（人工确认过再动）

- **`copy-video-studio` 与 `video-studio`**：文案归前者，视频归后者。
  `copy-video-studio` 的 description 里不再保留「做个视频」；`video-studio` 也不许写「写条文案」。
  串联靠中间产物：`copy-video-studio` 出 `script.md`，`video-studio` 读它。

- **`copy-video-studio` 与 `live-media-ops`**：两边都涉及「文案」「视频」。
  边界约定：**所有文案和视频归 `copy-video-studio` 与 `video-studio`**；`live-media-ops` 只管招主播与招聘流程。
  如果 `live-media-ops` 的 description 里还写着「写文案 / 生成视频」，就是重叠，要收掉。
