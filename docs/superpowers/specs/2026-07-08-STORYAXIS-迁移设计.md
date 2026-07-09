# StoryAxis 迁移设计

## 目标

在当前 `origin/main` 基线上，移植 `self` 分支中的 StoryAxis 相关能力。迁移结果必须满足以下三个目标：

1. 保留 `main` 现有更先进的底层能力与主干交互方式。
2. 全量承接 `self` 的 StoryAxis 核心能力，尤其是深层角色建模、节拍链路、重上下文链路、翻译与术语表能力、DeepSeek 适配。
3. 尽量把 StoryAxis 设计成一套与 `main` 主干创作链并行的内置工作流体系，以减少后续跟进 `origin/main` 更新时的冲突。

## 已确认约束

### 真源

- `StoryAxis` 属于“仓库随代码发布的内置工作流”。
- `StoryAxis` 工作流的真源是仓库中的 `.wf` 文件，而不是数据库中的工作流行。
- `StoryAxis` 对应的项目模板标识固定为 `storyaxis`。

### 集成方式

- `StoryAxis` 不是独立产品入口。
- `StoryAxis` 不是单纯复用并改名当前主干工作流。
- `StoryAxis` 应建立在 `main` 已存在的代码式自定义工作流体系上：
  - `Workflow` 表
  - `definition_code`
  - `triggers_cache`
  - 工作流编辑器
  - 触发器执行链
- `StoryAxis` 可以保留专用编辑器组件，例如：
  - `GlossaryEditor.vue`
  - `TransCodeMirrorEditor.vue`
  但这些组件应服务于 StoryAxis 卡片类型，而不是取代 `main` 的默认主流程。

### 全量迁移范围

必须迁移的 `self` 能力包括：

- ChatDeepSeek 底层适配
- 角色深层画像字段
- `beat_list` / `beat_main_perspective` 链路
- 重上下文与强约束 prompt 链路
- 翻译卡 / 术语表 / 对应专用编辑器
- 拆书与阶段化相关 StoryAxis 工作流能力

## 现状判断

### `main` 现有优势

当前 `main` 已经具备成熟的工作流基础设施：

- 代码式 DSL 工作流
- 工作流编辑器与执行面板
- `Trigger.ProjectCreated`
- `Trigger.CardSaved`
- `Card.Create`
- `Card.BatchUpsert`
- `Prompt.Load`
- `AI.BatchStructured`
- `AI.SequentialStructured`

同时，当前 `main` 的 LLM 配置体系比 `self` 更先进，已经包含：

- `api_protocol`
- `custom_request_path`
- `models_path`
- `user_agent`
- capability probe
- assistant mode recommendation
- stream downgrade behavior

这些能力不能被回退。

### `self` 现有优势

`self` 的增量价值主要集中在以下部分：

1. 更重的创作上下文链路。
2. 更深的人物画像字段。
3. 更细的章节节拍与续写视角约束。
4. 翻译卡 / 术语表 / 专用编辑器。
5. DeepSeek provider 的低层兼容实现。

## 设计原则

### 原则 1：以 `origin/main` 为基线

主干 UI、主干工作流引擎、LLM 配置 UX、能力探测逻辑均以当前 `origin/main` 为准，不回退到 `self` 的旧实现。

### 原则 2：StoryAxis 作为并行内置工作流体系存在

StoryAxis 不是把 `main` 当前的 `阶段大纲 / 章节大纲 / 章节正文` 链直接改掉，而是作为一组独立的内置资源存在：

- 独立工作流
- 独立卡片类型
- 独立 prompts
- 独立上下文模板
- 必要时独立编辑器组件

### 原则 3：低层基础设施可以共享

凡属于通用 runtime / compatibility 的能力，可以直接并入公共层，例如：

- `ChatDeepSeek`
- continuation runtime 对 `beat_list_json` 的支持
- 通用 schema / response model
- workflow engine

### 原则 4：业务行为尽量收敛到 StoryAxis 命名空间

StoryAxis 的业务资源应尽量以 StoryAxis 命名存在，避免和 `main` 主干既有资源混名。

## StoryAxis 最终形态

### 1. StoryAxis 工作流

StoryAxis 工作流使用 `backend/app/bootstrap/workflows/*.wf` 作为发布载体，并通过现有 bootstrap 机制同步到数据库。

命名规则统一为：

- `StoryAxis·项目初始化`
- `StoryAxis·阶段生成`
- `StoryAxis·章节蓝图生成`
- `StoryAxis·正文生成`
- `StoryAxis·术语表同步`
- `StoryAxis·术语待翻译补全`
- `StoryAxis·翻译派生`
- `StoryAxis·增强拆书`

其中项目初始化工作流应使用：

```python
Trigger.ProjectCreated(template="storyaxis")
```

这样 StoryAxis 可以直接接入 `main` 已有的项目模板选择与项目创建触发链。

其他 StoryAxis 过程型工作流应使用 StoryAxis 自有卡片类型触发，例如：

- `Trigger.CardSaved(card_type="StoryAxis阶段卡")`
- `Trigger.CardSaved(card_type="StoryAxis章节蓝图卡")`
- `Trigger.CardSaved(card_type="StoryAxis正文卡")`

### 2. StoryAxis 卡片类型

StoryAxis 不应直接借用 `main` 现有核心卡片名称作为主业务载体，而应使用一组独立卡片类型。

原因：

1. 避免和 `main` 当前主干创作链耦合。
2. 降低未来跟进 `origin/main` 时的 merge 冲突面。
3. 允许 StoryAxis 自由承载更重的字段、更专门的上下文与编辑器。

建议的卡片类别包括：

- StoryAxis角色卡
- StoryAxis阶段卡
- StoryAxis章节蓝图卡
- StoryAxis正文卡
- StoryAxis翻译术语表
- StoryAxis正文翻译卡

这些卡片需要承接 `self` 中的深层字段和生成上下文。

### 3. StoryAxis 专用编辑器

以下组件允许保留：

- `GlossaryEditor.vue`
- `TransCodeMirrorEditor.vue`

但它们的定位应调整为：

- StoryAxis 特定卡片类型的 `editor_component`
- 为 StoryAxis 卡片提供专用编辑能力
- 不改变 `main` 默认卡片编辑主流程

## 详细迁移内容

### A. DeepSeek 兼容迁移

### 目标

在不回退 `main` 现有 LLM transport / capability 架构的前提下，引入 `self` 的 DeepSeek provider 支持。

### 必须保留

- `ChatDeepSeek` import 与 provider 分支
- `disabled_params={"tool_choice": None}`
- `deepseek` 的 models 获取支持
- `reasoning_effort` / thinking 相关兼容透传

### 禁止事项

- 禁止用 `self` 的旧版 LLMConfig 模型替换 `main` 当前模型
- 禁止移除 `main` 的 capability probe 与推荐逻辑

### B. 深层角色画像迁移

### 必须迁移字段

- `physique`
- `aura`
- `appearance`
- `dressing`
- `core_desire`
- `core_fear`
- `defense_mechanism`
- `psychological_trauma`
- `public_persona`
- `private_persona`
- `the_shadow_self`

同时迁移：

- 扩展 `role_type`
- `DynamicInfoItem.chapter`

### 迁移层级

这些字段不能只停留在 schema 层，必须完整进入：

- schema / response model
- card type schema
- 上下文模板
- generation runtime
- continuation runtime

### C. 章节节拍链路迁移

### 必须迁移内容

- `BeatItem`
- `ChapterOutline.beat_list`
- `beat_main_perspective`
- `ContinuationRequest.beat_list_json`
- continuation runtime 中基于 beat 的字数预算与主视角约束

### 原因

如果只迁移数据字段，不迁移 runtime，StoryAxis 会丢失 `self` 的关键生成特征，等于名义迁移而非实质迁移。

### D. 重上下文链路迁移

### 必须迁移内容

迁移 `self` 中 StoryAxis 所依赖的 card context template 与 prompts 约束，覆盖以下阶段：

- 分卷规划
- 写作指南
- 阶段生成
- 章节蓝图生成
- 正文生成
- review / audit

### 必须保留的行为特征

- 严格受章节大纲约束
- 严格控制实体引入
- 使用更重的角色、组织、场景、物品、概念上下文
- 使用写作指南与阶段上下文共同约束正文
- 保证章节大纲足够支撑长篇正文扩写

### E. 翻译与术语表迁移

### StoryAxis 翻译能力应保留

- StoryAxis翻译术语表
- StoryAxis正文翻译卡
- StoryAxis 术语表专用编辑器
- StoryAxis 翻译专用编辑器

### 工作流建议

- `StoryAxis·项目初始化`
  - 创建 StoryAxis 基础卡与多语种术语表
- `StoryAxis·术语表同步`
  - 从实体卡抽取术语
- `StoryAxis·术语待翻译补全`
  - 为待翻译术语补全目标语言
- `StoryAxis·翻译派生`
  - 从 StoryAxis 正文卡生成翻译卡

### F. StoryAxis 增强拆书

不直接覆盖 `main` 当前 `拆书工作流.wf`。

应以 StoryAxis 名义引入增强版工作流，保留 `self` 的核心思路：

1. 提取章节摘要
2. 按 chunk 生成阶段候选
3. 归并阶段
4. 输出阶段分析与全案拆解

这条链应作为 StoryAxis 专属内置工作流存在，避免直接污染 `main` 当前拆书流。

## 不做的事

以下内容不属于本次迁移方向：

1. 不把 StoryAxis 做成独立应用入口。
2. 不回退 `main` 的 capability probe。
3. 不用 `self` 覆盖 `main` 的 LLMConfig UX。
4. 不把 StoryAxis 收缩成仅复用 `main` 现有卡片与工作流名字。

## 冲突控制策略

为最大程度适配后续 `origin/main` 更新，采取如下策略：

1. 主干基础设施以 `origin/main` 为准。
2. StoryAxis 业务能力尽量新增，不就地改主干默认业务流。
3. 真正共享的通用能力只放在：
   - LLM provider 兼容层
   - continuation runtime
   - schema 基础模型
   - workflow engine
4. StoryAxis 的大部分业务冲突应集中在新增资源文件，而不是 `main` 的现有核心 UI 文件。

## 实施顺序

建议后续实现顺序如下：

1. 迁移 DeepSeek 兼容层。
2. 迁移 StoryAxis schema / response model / card schema。
3. 迁移 StoryAxis context template 与 prompts。
4. 迁移 StoryAxis runtime 链路：
   - beat
   - deep character profile
   - continuation support
5. 迁移 StoryAxis card types 与专用 editor component 接线。
6. 迁移 StoryAxis 内置 `.wf` 工作流。
7. 验证 StoryAxis 与 `main` 并行存在，且不破坏 `main` 当前主干体验。

## 设计结论

最终采用的方案是：

- `origin/main` 作为主干基线
- `StoryAxis` 作为随代码发布的内置工作流体系
- `StoryAxis` 使用独立工作流与独立卡片类型
- `StoryAxis` 复用 `main` 现有工作流引擎与编辑器能力
- `StoryAxis` 全量迁移 `self` 的 DeepSeek、深层角色画像、章节节拍、重上下文、翻译与术语表能力
- `StoryAxis` 与 `main` 主干创作流并行存在，以最小化后续同步 `origin/main` 的冲突成本
