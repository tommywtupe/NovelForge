# StoryAxis 迁移约束

## 目标

在当前 `origin/main` 基线上迁移 `self` 分支中的 StoryAxis 相关能力，同时尽量保留 `main` 现有 UI、工作流引擎以及较新的 LLM 兼容基础设施。

## 真源

- `origin/main` 是核心产品 UI、工作流引擎、LLM 配置体验与运行时基础设施的基线。
- `StoryAxis` 是一套随代码发布的内置工作流系统。
- `StoryAxis` 工作流定义位于 `backend/app/bootstrap/workflows/*.wf`。
- 对于 `StoryAxis` 工作流，仓库中的定义文件是真源；数据库中的工作流记录只是 bootstrap 后的运行镜像。
- `StoryAxis` 的项目创建模板标识固定为 `storyaxis`。

## 架构边界

- `StoryAxis` 不是独立产品壳，也不是独立全局入口。
- `StoryAxis` 是建立在 `main` 已有代码式工作流系统之上的一套独立内置工作流族。
- `StoryAxis` 必须与 `main` 当前默认的内置卡片链路、工作流链路保持区隔。
- `StoryAxis` 可以增加专用编辑器组件，例如 `GlossaryEditor.vue` 与 `TransCodeMirrorEditor.vue`，但这些组件应挂载到 StoryAxis 专属卡片类型上，而不是替换 `main` 的默认写作流程。

## 必须迁移的范围

### 1. 底层 LLM 兼容能力

`self` 分支中的 DeepSeek 兼容能力必须迁移到 `main`，且不能破坏 `main` 当前较新的 transport / probe 体系。

必须保留的结果：

- 保留 `main` 当前的传输兼容链：
  - `api_protocol`
  - `custom_request_path`
  - `models_path`
  - `user_agent`
  - capability probe
  - assistant mode recommendation
  - stream downgrade behavior
- 引入 `self` 的 `ChatDeepSeek` 支持
- 增加 `deepseek` provider 分支
- 保留 `disabled_params={"tool_choice": None}` 这一 DeepSeek 专属兼容行为
- 确保模型列表获取支持 `deepseek`

禁止用 `self` 的旧版 LLM 配置体系整体替换 `main` 当前实现。

### 2. StoryAxis 数据模型

StoryAxis 必须完整承接 `self` 的深层角色建模与章节节拍建模。

至少包括：

- 扩展后的 `role_type`
- `DynamicInfoItem.chapter`
- 深层角色画像字段：
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
- 章节节拍结构：
  - `BeatItem`
  - `beat_list`
  - `beat_main_perspective`

### 3. StoryAxis 运行时链路

StoryAxis 必须迁移这些结构真正生效所需的运行时链路，而不是只迁存储字段。

至少包括：

- `beat_list_json` 在续写请求中的支持
- 节拍列表在续写/生成服务中的解析
- 深层角色画像在生成时的自然语言格式化与提示注入
- continuation runtime 中的节拍预算与主视角锁定逻辑
- 让上述字段真正影响输出的 prompt / context 接线

### 4. StoryAxis 重上下文链路

`self` 中更重的创作上下文是必须迁移的重点。

需要迁移 StoryAxis 专属的上下文模板与提示约束，用于：

- 分卷规划
- 写作指南生成
- 阶段生成
- 章节蓝图生成
- 正文生成
- 审核约束

必须保留的效果包括：

- 更严格地遵守章节大纲
- 更严格地限制新实体引入
- 更重地使用世界观 / 实体 / 阶段 / 章节上下文
- 保证章节大纲密度足以支撑长篇正文扩写

### 5. StoryAxis 翻译与术语表

StoryAxis 必须保留 `self` 的翻译与术语表能力集。

必须达到的结果：

- StoryAxis 术语表卡片类型
- StoryAxis 翻译卡片类型
- StoryAxis 术语表专用编辑器支持
- StoryAxis 翻译专用编辑器支持
- StoryAxis 项目初始化工作流可自动准备翻译资产
- StoryAxis 工作流可完成术语同步 / 术语补全 / 翻译派生

## StoryAxis 隔离规则

- StoryAxis 卡片类型必须与 `main` 当前核心卡片类型区分开。
- StoryAxis 工作流命名必须统一收口到 `StoryAxis` 家族下。
- StoryAxis 工作流应主要操作 StoryAxis 自有卡片与 prompt。
- 除非是必须共享的底层 runtime 修复，否则避免大面积改写 `main` 默认工作流链。

## 命名规则

- 项目模板标识：`storyaxis`
- 工作流命名：`StoryAxis·...`
- StoryAxis 专属卡片类型应采用清晰的命名空间，避免与 `main` 基线卡片体系重名。

## 集成原则

- 优先采用新增式集成，而不是替换 `main` 现有行为。
- 只有真正属于底层兼容与运行时基础设施的修复，才允许进入共享公共层。
- StoryAxis 的业务行为应尽量隔离在 StoryAxis 自有资源中：
  - 卡片类型
  - prompts
  - 工作流
  - 编辑器组件
  - schemas

## 非目标

- 不把 StoryAxis 做成独立应用壳。
- 不回退 `main` 当前的 capability probe 与较新的 LLM 配置 UX。
- 不把 StoryAxis 收缩成对 `main` 现有卡片与工作流名字的简单复用。
- 不把数据库里手工编辑过的工作流定义当作 StoryAxis 内置工作流的长期真源。

## 交付顺序

1. 保留并迁移 DeepSeek 底层兼容能力。
2. 引入 StoryAxis schema / model 支持。
3. 引入 StoryAxis 卡片类型、prompts 与上下文模板。
4. 引入位于 `backend/app/bootstrap/workflows` 下的 StoryAxis 内置工作流。
5. 接好 StoryAxis 所需的专用编辑器组件。
6. 验证 StoryAxis 对 `main` 是新增式并行集成，并尽量减少未来跟进 `origin/main` 时的冲突。
