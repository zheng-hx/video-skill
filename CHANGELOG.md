# 变更记录

## 2.0.0 — 2026-11-10

### 文档与包一致性修复（随 2.0.0 一起发）

- **README 重写**：删掉 `live-media-ops` / `live-media-router` 和「四个技能」的说法，改为两个能力；评测数 7 → 10；补 `check-copy` 与 `rules/` 工作台目录。
- **docs 对齐 v2.0**：`安装与分发.md`（四个→两个技能、补 Trae CN）、`交付形态.md`（4 个 markdown 技能→2、修正 capabilities 路径）、`测试方法.md`（L3 基线 7 条→10 条）、`工作流协议.md`（三段→四段流水线，表里有四行）。
- **修 `reconcile-skills.py` 计数 bug**：`found` 初始化为 0 后再未累加，导致注册成功也打印「没探测到任何 AI 工具的技能目录」，且「只装了 X」提示永远不执行。改为按 `chosen` 是否为空判断。
- **修 `check-copy.py --self-test`**：原来它对着含违规词的样本扫描并返回 1，等于自测恒失败，`npm run check:all` 一直是红的。改为真自测：脏样本必须命中违规 + 限流，干净样本不得误报。
- **评测参考产物对齐黑名单**：`copy-recruit` / `copy-script-file` 正文的「底薪加提成」改为「固定加分成」，不再违反 v2.0 的限流词规则。
- **修 `render-package.py` 版本判断**：文档写「版本相同跳过、不同覆盖」，代码实际是「目录存在就跳过」。改成读 `video.json` 的已装版本比对——同版本跳过，跨版本自动覆盖技能目录（`output/` 仍不动）。
- **清残留**：`ecosystem.md` / `check-skill.py` 里的旧技能名、`copy-video-studio/SKILL.md` 重复的 `check-copy.py` 引用行。
- `dist/` 补 2.0.0 分发包；`0.4.3` / `1.0.0` / `1.0.1` 三个旧包保留作历史。

### 审计修复（2026-11-10）

- **漫剧示例恢复合格**：`assets/storyboard.anime.json` 的 s2/s3 补「全局保持」行，重新过门禁。
- **工作流协议收进技能**：正文移到 `video-studio/references/workflow-protocol.md`，`docs/工作流协议.md` 改成索引。原来两处引用指向项目根 `docs/`，`render` 不拷 `docs/`，装完必断。
- **快照与黑名单对齐**：`rules-snapshot.md` 补「月薪 / 工资 / 高薪」；「简历 / 投递 / 入职」明确标为**人工判断项**，不进扫描词表（否则会误伤 §0 要求的「投了三十份简历」这类具体细节）。
- **补上 v2.0 核心修复的评测**：`multi-shot-handoff` 增加「全局保持 / 接上一镜」断言，参考产物按新格式重写。此前 10 条评测没有任何一条覆盖这个修复。
- **门禁清单与脚本对齐**：`video-studio/SKILL.md` 门禁节补齐脚本实际在查的项（授权四字段、时间轴连续、构图/质感/约束层、台词写进 prompt、负向三红线、单镜上限）。
- **触发词金标集修解析**：`check-triggers.py` 支持「`a` / `b`」双技能单元格，金标集从「15 条」恢复为真实的 16 条。
- **删掉 `shared/` 的空承诺**（空目录、无实现、未入库）；孤儿文件接线：`no-tools.md`、`brief-template.md`、`storyboard.anime.json`。
- **`library.py search` 支持关键词**（原来只能按 type / platform 过滤，实际搜不了内容）。
- **`tool-dirs.json` 的 `workbench` 真正生效**：`render` / `reconcile` 默认值改读它，不再硬编码。
- **`validate-package.py` 注释与实现对齐**：不再声称会比对 package 与 `_meta.json` 版本（两者本就该不同）。
- **收紧文案评测**：`copy-recruit` / `copy-script-file` 的 `not_match` 补「招聘 / 底薪 / 提成 / 月入」，参考产物去掉「合规招聘 / 目标投递」这类标签。
- **示例对齐红线**：`docs/示例-深圳择业文案.md` 去掉「一个月能拿一万多」「一个月到底能拿多少」等收入数字与承诺。
- **技能级自检进 CI**：新增 `npm run check-skills`，`video-studio` 补上 `scripts/check-skill.py`，纳入 `check:all`。

### 审核闸门与声音门禁（2026-11-10）

- **删掉「用户 10 秒内没说改就自动 approve」**：模型没法计 10 秒，这条和协议 §7「必须确认」直接冲突，实际使用中就是跳过审核的开关。
- **审核改成硬闸门**：故事（Stage 1）和提示词（3b）必须给用户看、拿到明确「可以」；过审前不许出现生成选项 / 操作卡 / 「复制这段丢进即梦」。`check-storyboard.py` 新增 `meta.review.story_approved` / `prompts_approved`，没置 true 直接红。
- **声音三件套进门禁**：每镜 prompt 必须有「声音」段 + 配乐（或 `no_music_reason`）；标了 `silent` 必须写 `silent_reason`。
- **输出格式加停点**：「等你审」写在生成选项之前，「怎么操作」后移到过审之后。
- **协议 §7 对齐**：文案 → 故事也要确认（故事定方向，方向错了后面全废）。
- **资产补齐**：模板、漫剧示例、32 岁会计参考产物补 `review` / 声音；两个视频评测参考产物补 BGM + 环境音，断言加「配乐 / 环境音」和「先审后生成」过程项。

### 架构重组：四个技能收缩为两个

- 从四个技能（文案 + 视频 + 招募 + 路由）收缩为**两个技能**（文案 + 视频）。
- `live-media-ops`（招募）和 `live-media-router`（路由）两个技能删除。
- 路由逻辑内置进入口 SKILL.md，变成一句话分流。
- JD 模板从 live-media-ops/assets/host-jd-template.md 移到 `copy-video-studio/assets/host-jd-template.md`（放 scripts/ 是放错位置，已纠正）。
- 主播筛选/面试方法论移到 copy-video-studio/references/host-recruit.md 作为行业参考。

### 文案能力（copy-video-studio v0.3.0）

- **删除"招募（硬）"类型**：所有对外内容统一走**故事型骨架**（§0）。钩子→痛点→卖点骨架降级为带货/种草可选。
- **限流词黑名单**：骨架生成时自动替换"招主播""底薪""月入过万""简历""加微信"等词，不再事后扫。
- **结果段硬红线**：故事里的"结果"段禁止具体数字，只保留"够交房租""能顾家"这类可感知但不承诺的说法。
- recruit-playbook.md 去招人绑定，升级为**故事型文案通用方法论**。
- story-types.md 去绑定化，九种主角套路适用于任何对外内容场景。

### 视频能力（video-studio v0.4.0）—— 修复三个实际使用问题

- **故事承接：展开模式 vs 从零补写**：story-from-copy.md 先判断文案类型——故事型文案（copy-video-studio 默认产出）直接**展开不重写**；只有广告型文案才从零补故事。
- **多段视频串不起来（核心修复）**：解决了 14 字段骨架和"后续镜不再重述外貌"的内部矛盾。
  - 字段分两层：**全片共享**（风格锚、身份锚点、光线基调）+ **每镜独有**（造型、动作、场景、构图、镜头）
  - 首镜完整写共享字段；后续镜开头固定格式：`全局保持：<共享锚点>，接上一镜：<结束状态>，现在<本镜动作>`
  - 门禁脚本同步更新：首镜查完整共享字段，后续镜查"全局保持"和"接上一镜"行存在
- **提示词看不到（核心修复）**：storyboard-and-prompt.md 明确**提示词是第一交付物**——每段用代码块包出来，标"复制这段丢进 [即梦/可灵/Veo]"。storyboard.json 是备份不是主交付。
- check-storyboard.py 升级门禁规则匹配新分层。
- storyboard.template.json 更新为新格式。
- **参考文件拆分**：949 行的 `storyboard-and-prompt.md` 拆成四份——主流程（约 500 行）+ `pre-production.md`（角色卡 / 参考图预生成 / 摄影级风格锚）+ `prompt-templates.md`（即梦 / Seedance / 可灵 / 混元官方语序）+ `sound-design.md`（声音两段模板 + 台词语言标签）；顺带修掉重复的章节编号。

### docs / evals / triggers

- docs/技能总览.md：四个→两个，边界重新写。
- docs/工作流协议.md：四段→三段，去掉意图路由段。
- evals/triggers.md：更新金标集，移除指向已删除技能的用例。
- package.json 版本号同步更新。

## 1.0.5 — 2026-11-10

（无变更，版本号对齐）

## 1.0.0 — 2026-11-09

### 改成单入口

- 对外只保留一个技能 `video-design-skills`：初始化时把四个技能渲染到 `~/.video-design/skills/`，再注册到本机 AI 工具目录。
- 新增 `scripts/render-package.py`：渲染，支持 `--force` / `--dry-run` / `--workdir`。
- 新增 `scripts/reconcile-skills.py`：只对已存在的工具目录动手，同名冲突不覆盖。
- 新增 `tool-dirs.json`：Claude Code / Codex / WorkBuddy / Cursor 四类目录规则。
- 四个技能迁入 `capabilities/`，结构校验与触发词检查同步支持两层扫描。
- `README` / `docs/安装与分发.md` / `docs/技能总览.md` 改为单入口说明。

### 已发布

- SkillHub：`video-design-skills`（入口，skillId 314681）。
- 之前发的 `copy2video` / `live-media-router` / `copy-video-studio` 三个独立技能与新入口重复，建议在后台下架。

## 0.4.3 — 2026-11-09

### 外包层

- 新增 `references/outsourcing.md`：把生成任务外包给别的 AI——API 直调 / 浏览器自动化 / 桌面自动化 / 用户手动，四通道按稳定性排，带外包契约模板（任务、通道、输入、期望、验收、兜底）。
- `production-route.md` 能力探测从三层扩到四层：宿主自己 → 外包 → 用户手动喊话 → 制作包。
- 明确规定：没有 Key 不许假装能调；用第三方服务自动化要提示条款；外包产物必须落 `media/` 并回填 `storyboard.json`。

### 实测记录

- 当前环境 `browser_tabs` 连不上真实浏览器（CDP 9222 无响应），浏览器通道暂不可用；api 通道需用户提供 Key。

## 0.4.1 — 2026-11-09

### 评测首次真跑

- 7 条评测全部跑出参考产物，`run-evals` 从「0 通过 / 7 未跑」变成 **7 通过**。
- 产物放在 `evals/runs/<评测名>/`，作为参考基线入库，不再被 `.gitignore` 排除。
- 新增漫剧示例 `assets/storyboard.anime.json`：3 镜、anime 风格、2 条 handoff、freeze 收尾，能过门禁。

### 修了一个真 bug

- 多段判定公式只算了字数、没算总时长——30 秒视频按 15 秒上限必须拆两段，旧公式会算成 1 段。改成两个判据取大：`max(ceil(总时长÷上限), ceil(字数÷(上限×4.5)))`。

## 0.4.0 — 2026-11-09

### 前提改了：用的人不懂技术

之前整套东西默认用户「会用 AI、会跑命令、看得懂提示词」。这个假设错了。用的人不懂开发、不懂 AI，只想用。

- `video-studio` 新增「用这套东西的人可能什么都不懂」：术语不出门、一轮一个动作、不让用户跑命令、不问他技术问题。
- 新增 `assets/howto-card.md`：傻瓜操作卡模板——打开哪个 App、粘哪段、发回什么，三步以内。
- 交付形态从「提示词包」改成三选一：能直接出视频就给视频；他自己能生成就给操作卡；什么都没有就给拍摄清单。
- 门禁改为技能自己跑，不把报错给用户看。
- `copy-video-studio` 加「交付要人话」。

### 新增交付文档

- `docs/交付形态.md`：装进现成 AI 助手 / 做网页小程序 / 微信机器人三种形态，写清谁做、他做什么、限制在哪。

## 0.3.4 — 2026-11-09

### 失败诊断与重跑

- 新增 `video-studio/references/failure-diagnosis.md`：12 条「现象 → 根因 → 改哪 → 重跑哪段」对照表，覆盖换脸、色调漂、接不上、动作只做一半、手畸形、字幕对不上等。
- 重跑四条规矩：只跑出问题那一段、先改再跑、同问题最多 2 次、每次记一笔。
- 自动编排契约：技能包跑不了自动重试，但给出宿主有 workflow 能力时的循环契约（生成 → 门禁 → 失败改 → 重跑 ≤2 轮 → 未解决交人）。
- 明确「不该重跑」的三种情况：故事错了、平台不支持、关键项没确认。
- `工作流协议.md` 的失败退回接上诊断表，不裸重试。

## 0.3.3 — 2026-11-09

### 去掉故事字数限制

- 完整故事不再规定 200–400 字，改成「长度按内容定，不凑字也不删细节」。字数上限会逼着删必要细节，下限会逼着凑废话。
- 同步改掉 `story.md` 模板、SKILL.md、docs、评测里的字数断言。

### 委派改成协议

- 新增 `docs/工作流协议.md`：四段流水线（意图 → 文案 → 故事 → 提示词 → 生成），每段有负责技能、输入、交接物、出口门禁。
- 规定三个「必须委派」的条件、委派时必带的三样（交接物 / 已确认设定 / 未决项）、交出去和接过去的自检项、失败只退到出错那一段。
- `video-studio` 和 `copy-video-studio` 各加「委派规则」小节，不再只是一句「交给 X」。

## 0.3.2 — 2026-11-09

### 故事层改实

- **完整故事取代一句话故事**：`story-from-copy.md` 重写——产物是 200–400 字叙事，有开头、转折、结尾，用现在时，能看见画面；一句话只作索引，不能拿去拆分镜。
- **润色与确认**：新增两种路径——用户愿意就逐项确认（人物 / 场景 / 情绪 / 结尾），不愿意就给「我替你定的」清单让他改；故事没确认不进提示词。
- **落 `story.md`**：故事定稿写进 `output/<日期>-<主题>/story.md`，带分场、补写清单、确认表；分镜层读它，不读会话记忆。
- **模板替换**：`assets/story-card.md` 换成 `assets/story.md`。
- **评测同步**：`copy-to-video.md` 的断言从「一句话故事」改成「完整故事 ≥200 字 + 分场」。

## 0.3.1 — 2026-11-09

### 修复（按审查结果）

- **`script.md` 不再是空头承诺**：`copy-video-studio` 增加「输出约定」节，产出固定四块并落 `output/<日期>-<主题>/script.md`；存不了文件才退回对话内交付。
- **模板补齐约束层**：`storyboard.template.json` 三条示例都加了防崩约束句，和 13 字段对齐。
- **门禁加两项**：提示词必须有约束层；`ending.end_state` 也查空话。
- **router 三处改对**：一条龙改为依次交接三个技能；示例句不再让 `live-media-ops` 写口播；平台选型指向 `video-studio`。
- **`live-media-ops` 真正收口**：删掉文案/视频两节正文，改成「已迁出」说明；串联流水线改成三段交接。
- **`video-studio` 补问不问规则**：与 `copy-video-studio` 同一张表，标出五个必问项。
- **新增两条评测**：多段衔接（`multi-shot-handoff.md`）、文案落盘（`copy-script-file.md`），评测总数 7 条。

### 未采纳

- 第 8 条「运镜/景别词库重复」经核查不成立：词库只在 `cinematography.md`，`storyboard-and-prompt.md` 只做字段说明。

## 0.3.0 — 2026-11-09

### 打磨

- **`copy-video-studio` 收干净**：标题、开篇、输出格式里的「视频」全部去掉，只剩文案；「铁律：少问」改成「问不问：看知不知道」，与 video-studio 同一套规则。
- **`live-media-ops` 收窄为招募线**：description 只留招主播 / JD / 面试，不再抢「写文案」「生成视频」；SKILL.md 顶部标明两个环节已拆出。
- **版本号同步**：package 0.3.0；copy-video-studio 0.2.0、video-studio 0.2.0、live-media-ops 0.4.1、live-media-router 0.2.0。
- **触发词不再重叠**：修完后 `check-triggers` 的触发短语清单里，文案、视频、招募各归各的。

### 新增参考

- `video-studio/references/cinematography.md`：全局前置块、分镜公式、运镜/景别词库、八种光影模板、带 dB 的声音公式。
- `video-studio/references/prompt-resources.md`：外部提示词资源库，标了哪些实测能开、哪些抓取失败。

## 0.2.0 — 2026-11-09

### 新增技能

- **`video-studio`**：文案转视频工坊。入口是文案，不是故事——先拆信息点补故事，再判单条还是多条，出分镜、逐镜提示词和衔接合同，最后生成或交付。

### 从 shuhe-role-skills 借来的机制

- **handoff 衔接合同**：每个非最后镜头写 `mode` / `end_state` / `next_start_state` / `match_on` / 首尾帧 / 裁剪余量；禁止「保持连续」「同上」这类空话。
- **首尾帧链**：上一镜尾帧当下一镜首帧，轴线不跳。
- **身份锚点与阶段造型分开**：长相全片锁死，服装按镜头变。
- **渐进补全**：一次只问当前最阻塞的一项，先复述再追问。

### 主动规避的问题

- **入口错位**：role 那套是「故事 → 视频」，这里改成「文案 → 故事 → 视频」。
- **没有转化结构**：故事卡里强制保留卖点、价格、功效、CTA 原文，补写必须标 `【补写】`。
- **太重**：不引入 `project.json`、审阅看板、五态状态机；只留一份 `storyboard.json` 供门禁脚本读。
- **门禁有洞**：新增 `scripts/check-storyboard.py`，能查的交给脚本：字段完整、时长合计、handoff 覆盖、空话词、角色引用、收尾存在。
- **收尾衔接**：新增 `ending` 四选一（落版 / CTA / 定格 / 循环），最后一段必须收住，停留 ≥ 1.5 秒。

### 其他改动

- `copy-video-studio` 收窄为文案技能，视频交给 `video-studio`；description 去掉「做个视频」避免抢触发。
- `evals/triggers.md`：金标集扩到 16 条，补 `video-studio` 的触发词与重叠约定。
- `evals/copy-to-video.md`：新增「文案转视频」评测，含卖点保真、补写标注、衔接空话、收尾四项断言。
- `docs/技能总览.md`：改为四技能职责表，补三段流水线。
- `README.md`：设计原则第 1 条改为「知道就不问，不知道就问」——少问是手段，不是铁律。

## 0.1.0 — 2026-11-09

### 新增技能

- **`copy-video-studio`**：文案 + 视频工坊。核心是「少问」和「进化」——缺的信息按默认假设补齐并标注，不反复追问；偏好存 `profile.md`，下次沿用。
- **`live-media-ops`**：主播招募。JD、渠道话术、筛选 checklist、面试打分卡、候选人档案。
- **`live-media-router`**：自媒体 / 直播领域入口。只做意图识别与分流，不出稿。

### 新增工程设施

- `evals/`：4 条行为评测（招募文案 / 带货文案 / 秀场话术 / 零工具视频），带机器可判断言与反例。
- `evals/triggers.md`：12 条触发词金标集。
- `scripts/validate-package.py`：包结构校验（frontmatter、引用完整性、describe 长度）。
- `scripts/check-evals.py`：评测定义完整性校验。
- `scripts/run-evals.py`：评测判定器，支持 exists / sections / match / not_match / if_match / min_count。
- `scripts/check-triggers.py`：触发词词面覆盖校验。

### 修正

- `composite_digital_human.sh`：修 split 布局奇数宽、字幕 filter 标签复用、双音轨；无 ffmpeg 时给出三条替代路线而不是崩溃。
- 技能职责收口：所有文案与视频归 `copy-video-studio`，`live-media-ops` 只管招主播。
