# StoryAxis Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `origin/main` 现有 UI、工作流引擎、LLM transport/probe 基线不回退的前提下，新增式集成 StoryAxis 与 DeepSeek 兼容能力。

**Architecture:** 共享层只接入真正通用的 DeepSeek provider、续写 runtime、schema 基础模型与 glossary API；StoryAxis 业务资源收敛到独立卡片类型、独立 prompt、独立 `.wf` 工作流、独立 editor component。已有主干卡片与主干工作流保留不替换，只增加并行 StoryAxis 入口。

**Tech Stack:** FastAPI, SQLModel, LangChain, Vue 3, Electron, CodeMirror, built-in workflow DSL

---

### Task 1: DeepSeek Compatibility

**Files:**
- Modify: `backend/app/services/ai/core/chat_model_factory.py`
- Modify: `backend/app/services/ai/core/llm_capability_probe.py`
- Modify: `backend/app/api/endpoints/llm_configs.py`
- Modify: `backend/app/services/llm_config_service.py`
- Modify: `backend/app/schemas/llm_config.py`
- Modify: `backend/app/db/models.py`
- Modify: `backend/requirements.txt`
- Modify: `frontend/src/renderer/src/components/setting/LLMConfigForm.vue`
- Test: `backend/tests/test_deepseek_compat.py`

- [x] Step 1: 写 `backend/tests/test_deepseek_compat.py`，覆盖 `deepseek` provider 走模型工厂、`disabled_params={"tool_choice": None}`、模型列表获取、capability probe 的 openai-family 兼容入口。
- [x] Step 2: 运行 `python -m pytest backend/tests/test_deepseek_compat.py -q`，确认先失败，失败点应来自 `deepseek` 还未被支持。
- [x] Step 3: 在后端保留现有 `api_protocol/custom_request_path/models_path/user_agent/capability probe/recommended_assistant_mode/disable_stream` 逻辑的前提下，新增 `deepseek` provider 分支与 `ChatDeepSeek`，并补齐 schema / DB / API / UI provider 选项。
- [x] Step 4: 重新运行 `python -m pytest backend/tests/test_deepseek_compat.py -q`，再运行 `cd frontend && npm run typecheck`，确认 DeepSeek 兼容批次通过。
- [x] Step 5: 提交 `feat: add deepseek compatibility for StoryAxis`

### Task 2: StoryAxis Schema And Shared Runtime

**Files:**
- Modify: `backend/app/schemas/entity.py`
- Modify: `backend/app/schemas/wizard.py`
- Modify: `backend/app/schemas/ai.py`
- Modify: `backend/app/schemas/response_registry.py`
- Modify: `backend/app/schemas/memory.py`
- Modify: `backend/app/bootstrap/card_types.py`
- Modify: `backend/app/services/ai/core/llm_service.py`
- Modify: `backend/app/services/ai/generation/continuation_budget_runtime.py`
- Modify: `backend/app/services/ai/generation/continuation_context_service.py`
- Modify: `backend/app/api/endpoints/ai.py`
- Test: `backend/tests/test_storyaxis_schema_runtime.py`

- [x] Step 1: 写 `backend/tests/test_storyaxis_schema_runtime.py`，覆盖深层角色字段、`DynamicInfoItem.chapter`、`BeatItem/beat_list/beat_main_perspective`、`ContinuationRequest.beat_list_json` 与 budget hint / prompt 注入。
- [x] Step 2: 运行 `python -m pytest backend/tests/test_storyaxis_schema_runtime.py -q`，确认先红。
- [x] Step 3: 把 `self` 的深层角色、节拍结构、translation/glossary schema 请求模型迁入共享 schema，并把 continuation runtime 接到 `beat_list_json`、主视角锁定、角色画像自然语言注入。
- [x] Step 4: 重新运行 `python -m pytest backend/tests/test_storyaxis_schema_runtime.py -q`，必要时补 `python -m pytest backend/tests -q` 做后端回归。
- [x] Step 5: 提交 `feat: add StoryAxis schemas and runtime support`

### Task 3: StoryAxis Resources And Built-In Workflows

**Files:**
- Create: `backend/app/bootstrap/prompts/StoryAxis·*.txt`
- Create: `backend/app/bootstrap/workflows/StoryAxis·*.wf`
- Modify: `backend/app/bootstrap/prompts.py`
- Modify: `backend/app/bootstrap/workflows.py`
- Modify: `backend/app/bootstrap/card_types.py`
- Modify: `backend/app/services/workflow/triggers.py` (仅当需要共享触发修复时)
- Test: `backend/tests/test_storyaxis_bootstrap_resources.py`

- [x] Step 1: 写 `backend/tests/test_storyaxis_bootstrap_resources.py`，断言 StoryAxis prompts/workflows 被加载，`Trigger.ProjectCreated(template="storyaxis")` 出现在项目初始化工作流，工作流名统一为 `StoryAxis·...`。
- [x] Step 2: 运行 `python -m pytest backend/tests/test_storyaxis_bootstrap_resources.py -q`，确认先失败。
- [x] Step 3: 以 `self` 旧 prompt / workflow 逻辑为内容来源，但新增为 StoryAxis namespaced 资源，不覆盖 `main` 现有 prompt/workflow 名称；同时让项目初始化工作流自动准备翻译资产。
- [x] Step 4: 重新运行 `python -m pytest backend/tests/test_storyaxis_bootstrap_resources.py -q`。
- [x] Step 5: 提交 `feat: add StoryAxis built-in workflows`

### Task 4: StoryAxis Editors And Glossary/Translation Flow

**Files:**
- Create: `frontend/src/renderer/src/components/editors/GlossaryEditor.vue`
- Create: `frontend/src/renderer/src/components/editors/TransCodeMirrorEditor.vue`
- Create: `frontend/src/renderer/src/api/glossary.ts`
- Modify: `frontend/src/renderer/src/components/cards/CardEditorHost.vue`
- Modify: `frontend/src/renderer/src/components/cards/GenericCardEditor.vue`
- Modify: `frontend/src/renderer/src/components/editors/CodeMirrorEditor.vue`
- Modify: `frontend/src/renderer/src/api/ai.ts`
- Create/Modify: `backend/app/api/endpoints/glossary.py`
- Create/Modify: `backend/app/services/glossary_service.py`
- Modify: `backend/app/schemas/entity.py`

- [x] Step 1: 从 `origin/self` 迁入 glossary/translation editor 与 API，但只挂载到 StoryAxis 专属卡片类型，例如 `StoryAxis术语表卡` / `StoryAxis翻译卡`，不要改写主干默认章节正文编辑器。
- [x] Step 2: 接通术语扫描、术语补全、翻译派生的后端 API 与前端 editor。
- [x] Step 3: 运行 `cd frontend && npm run typecheck`，再对 glossary API 做最小后端验证 `python -m pytest backend/tests/test_storyaxis_schema_runtime.py -q`。
- [x] Step 4: 提交 `feat: add StoryAxis editors and glossary flow`

### Task 5: Documentation And Verification

**Files:**
- Create: `docs/STORYAXIS-README.md`
- Modify: `docs/superpowers/plans/2026-07-08-storyaxis-migration.md` (勾选完成项)

- [x] Step 1: 编写 `docs/STORYAXIS-README.md`，覆盖改动概览、StoryAxis 与主干关系、`storyaxis` 项目创建、工作流触发、卡片类型、DeepSeek 配置、翻译/术语表、已知限制。
- [x] Step 2: 运行最终验证命令：`python -m pytest backend/tests -q`、`cd frontend && npm run typecheck`、必要时 `git diff --stat` 检查改动面。
- [x] Step 3: 汇总本地 commits、验证结果、未完成项与剩余风险。
- [x] Step 4: 提交 `docs: add StoryAxis usage readme`
