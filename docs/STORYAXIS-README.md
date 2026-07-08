# StoryAxis 集成说明

## 概览

StoryAxis 现在以“内置工作流家族”的方式并行集成在主干产品中，不是独立应用壳，也不会替换主干默认写作流程。

- 主干 UI、工作流引擎和新的 LLM transport / capability probe 体系保持不回退
- StoryAxis 使用独立的 `StoryAxis·...` 工作流、prompt、卡片类型和编辑器
- StoryAxis 项目模板标识固定为 `storyaxis`

## 项目创建

创建项目时选择 `storyaxis` 模板，会自动触发 `StoryAxis·项目创建` 工作流，初始化以下基础资产：

- `StoryAxis·作品标签`
- `StoryAxis·金手指`
- `StoryAxis·一句话梗概`
- `StoryAxis·故事大纲`
- `StoryAxis·世界观设定`
- `StoryAxis·核心蓝图`
- 4 张 `StoryAxis·翻译术语表`（繁體中文 / 英文 / 日文 / 韓文）

## 工作流家族

当前内置的 StoryAxis 工作流真源位于 `backend/app/bootstrap/workflows/`：

- `StoryAxis·项目创建`
- `StoryAxis·世界观派生`
- `StoryAxis·核心蓝图派生`
- `StoryAxis·分卷大纲派生`
- `StoryAxis·阶段大纲派生`

这些工作流只操作 StoryAxis namespaced 资源，不覆盖主干默认工作流名称。

## StoryAxis 数据与运行时

StoryAxis 共享层已接入以下结构与 runtime：

- 深层角色画像字段：`physique`、`aura`、`appearance`、`dressing`、`core_desire`、`core_fear`、`defense_mechanism`、`psychological_trauma`、`public_persona`、`private_persona`、`the_shadow_self`
- 动态信息章节来源：`DynamicInfoItem.chapter`
- 章节节拍：`BeatItem`、`beat_list`、`beat_main_perspective`
- continuation runtime 中的节拍预算、主视角锁定、角色画像自然语言注入
- 正文保存前自动清理 StoryAxis 控制标记

## 专属卡片与编辑器

StoryAxis 使用独立卡片类型，不和主干默认类型重名。

关键卡片包括：

- `StoryAxis·章节正文`
- `StoryAxis·正文翻译卡`
- `StoryAxis·翻译术语表`
- `StoryAxis·角色卡`
- `StoryAxis·阶段大纲`
- `StoryAxis·章节大纲`

对应专属编辑器：

- `TransCodeMirrorEditor.vue`
  用于 `StoryAxis·正文翻译卡`，支持目标语言切换、术语表选择和一键生成译文
- `GlossaryEditor.vue`
  用于 `StoryAxis·翻译术语表`，支持术语新增、扫描、补全翻译和全量重建

## 翻译与术语表流程

推荐流程：

1. 先完成 `StoryAxis·章节正文`
2. 使用 `StoryAxis·阶段大纲派生` 自动生成对应 `StoryAxis·正文翻译卡`
3. 在 `StoryAxis·翻译术语表` 中执行术语扫描或补全翻译
4. 在 `StoryAxis·正文翻译卡` 中选择目标术语表后生成译文

术语表服务支持：

- 扫描 StoryAxis namespaced 实体卡
- 只补全待翻译术语
- 扫描并自动补全翻译
- 全量重建译名

## DeepSeek 配置

主干 LLM 配置界面已新增 `deepseek` provider，并保留现有兼容链：

- `api_protocol`
- `custom_request_path`
- `models_path`
- `user_agent`
- capability probe
- assistant mode recommendation
- stream downgrade behavior

DeepSeek 兼容层包含：

- `ChatDeepSeek`
- `disabled_params={"tool_choice": None}`
- DeepSeek 模型列表拉取

## 已知限制

- StoryAxis 翻译卡默认通过 `StoryAxis·正文翻译` prompt 生成译文，若项目未完成 bootstrap，生成会失败
- 术语自动翻译依赖可用的 LLM 配置；若当前卡未配置模型，会退回到可用列表中的第一项
- 数据库中的工作流记录仍然只是 bootstrap 后镜像；内置真源仍然是仓库内 `.wf` 文件
