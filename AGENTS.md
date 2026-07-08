# StoryAxis Migration Guardrails

## Objective

Migrate the `self` branch's StoryAxis-related capabilities onto the current `origin/main` baseline while preserving `main`'s existing UI, workflow engine, and newer LLM compatibility infrastructure as much as possible.

## Source Of Truth

- `origin/main` is the baseline for core product UI, workflow engine, LLM config UX, and runtime infrastructure.
- `StoryAxis` is a code-shipped built-in workflow system.
- `StoryAxis` workflow definitions live in `backend/app/bootstrap/workflows/*.wf`.
- For `StoryAxis` workflows, repository files are the source of truth; database workflow rows are runtime mirrors populated by bootstrap.
- The project creation template id for StoryAxis is fixed to `storyaxis`.

## Architecture Boundary

- `StoryAxis` is not a separate product shell and not a separate global UI entry.
- `StoryAxis` is a distinct built-in workflow family implemented on top of the existing code-based workflow system already present in `main`.
- `StoryAxis` must remain distinct from the current built-in card/workflow chain used by `main`.
- `StoryAxis` may add dedicated editor components such as `GlossaryEditor.vue` and `TransCodeMirrorEditor.vue`, but these should be attached to StoryAxis-specific card types rather than replacing `main`'s default authoring flow.

## Required Migration Scope

### 1. Low-Level LLM Compatibility

The `self` branch's DeepSeek compatibility is mandatory and must be ported into `main` without regressing `main`'s newer transport/probe stack.

Required outcomes:

- Preserve `main`'s current transport compatibility chain:
  - `api_protocol`
  - `custom_request_path`
  - `models_path`
  - `user_agent`
  - capability probe
  - assistant mode recommendation
  - stream downgrade behavior
- Add `ChatDeepSeek` support from `self`
- Add the `deepseek` provider branch in chat model construction
- Preserve the `disabled_params={"tool_choice": None}` DeepSeek-specific behavior
- Ensure model listing supports `deepseek`

Do not replace `main`'s LLM config system wholesale with `self`'s older variant.

### 2. StoryAxis Data Model

StoryAxis must carry over `self`'s deeper character modeling and chapter beat modeling in full.

This includes, at minimum:

- extended `role_type`
- `DynamicInfoItem.chapter`
- character deep-profile fields:
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
- chapter beat structures:
  - `BeatItem`
  - `beat_list`
  - `beat_main_perspective`

### 3. StoryAxis Runtime Chain

StoryAxis must carry over the runtime path required to actually use the above structures, not just store them.

This includes:

- continuation request support for `beat_list_json`
- beat parsing in continuation/generation services
- character deep-profile text formatting used for generation/runtime hints
- beat-budget and perspective-lock behavior in continuation runtime
- prompt/context wiring required for these fields to influence output

### 4. StoryAxis Heavy Context Chain

`self`'s heavier authoring context is a required migration area.

Port the StoryAxis-specific context templates and related prompt constraints for:

- volume-level planning
- writing guide generation
- stage generation
- chapter outline generation
- chapter writing
- review constraints

These should preserve:

- stricter chapter-outline adherence
- stricter entity introduction limits
- heavier use of world/entity/stage/chapter context
- support for dense enough outlines to sustain long-form chapter generation

### 5. StoryAxis Translation And Glossary

StoryAxis must keep the `self` translation/glossary capability set.

Required outcomes:

- StoryAxis glossary card types
- StoryAxis translation card types
- StoryAxis glossary editor support
- StoryAxis translation editor support
- StoryAxis project initialization workflow that prepares translation assets
- StoryAxis workflows for glossary sync / glossary completion / translation derivation

## StoryAxis Isolation Rules

- StoryAxis card types must be distinct from `main`'s current core card types.
- StoryAxis workflows must be named under the `StoryAxis` family.
- StoryAxis workflows should primarily operate on StoryAxis-owned card types and prompts.
- Avoid invasive rewrites of `main`'s current default workflow chain unless a shared low-level runtime fix is required.

## Naming Rules

- Project template id: `storyaxis`
- Workflow names: `StoryAxis·...`
- StoryAxis-specific card types should use clearly namespaced names to avoid collision with `main`'s baseline card ecosystem.

## Integration Principles

- Prefer additive integration over replacing `main` behavior.
- Shared low-level fixes are allowed when they are true compatibility/runtime infrastructure.
- Business-specific StoryAxis behavior should be isolated into StoryAxis resources:
  - card types
  - prompts
  - workflows
  - editor components
  - schemas

## Non-Goals

- Do not treat StoryAxis as a separate app shell.
- Do not revert `main`'s capability probe or newer LLM config UX.
- Do not collapse StoryAxis into `main`'s existing card/workflow names.
- Do not rely on database-edited workflow definitions as the long-term source of truth for StoryAxis built-in workflows.

## Delivery Sequence

1. Preserve/port DeepSeek low-level compatibility.
2. Introduce StoryAxis schema/model support.
3. Introduce StoryAxis card types, prompts, and context templates.
4. Introduce StoryAxis built-in workflows under `backend/app/bootstrap/workflows`.
5. Wire StoryAxis-specific editor components where required.
6. Verify that StoryAxis remains additive to `main`, with minimal conflict against future `origin/main` updates.
