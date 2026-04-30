<template>
	<div class="chapter-tools-panel">
		<div class="panel-toolbar">
			<el-popover
				v-model:visible="settingsVisible"
				placement="bottom-end"
				trigger="click"
				:width="360"
				@show="syncEditingConfigFromSaved"
			>
				<template #reference>
					<el-button class="config-trigger" type="primary" plain>
						<template #icon>
							<el-icon><Setting /></el-icon>
						</template>
						模型：{{ selectedModelName || '未设置' }}
					</el-button>
				</template>

				<el-form label-width="96px" size="small" class="config-form">
					<el-form-item label="模型">
						<el-select
							v-model="editingConfig.llm_config_id"
							placeholder="选择模型"
							filterable
							style="width: 100%;"
							:teleported="false"
						>
							<el-option
								v-for="llm in llmConfigs"
								:key="llm.id"
								:label="llm.display_name"
								:value="Number(llm.id)"
							/>
						</el-select>
					</el-form-item>
					<el-form-item label="温度">
						<el-input-number v-model="editingConfig.temperature" :min="0" :max="2" :step="0.1" />
					</el-form-item>
					<el-form-item label="最大tokens">
						<el-input-number v-model="editingConfig.max_tokens" :min="256" :max="131072" :step="256" />
					</el-form-item>
					<el-form-item label="超时(秒)">
						<el-input-number v-model="editingConfig.timeout" :min="10" :max="6000" :step="10" />
					</el-form-item>
					<el-form-item>
						<div class="config-actions">
							<el-button type="primary" size="small" @click="saveConfig">保存</el-button>
							<el-button size="small" @click="resetEditingConfigToPreset">重置为预设</el-button>
						</div>
					</el-form-item>
				</el-form>
			</el-popover>
		</div>

		<div v-if="isBusy" class="busy-banner">
			<el-icon class="busy-icon is-loading"><Loading /></el-icon>
			<span>正在{{ runningActionLabel }}，完成后会自动打开预览。</span>
		</div>

		<el-card class="tool-card" shadow="never">
			<template #header>
				<div class="card-header">
					<el-icon><User /></el-icon>
					<span>角色动态信息</span>
				</div>
			</template>
			<div class="card-body">
				<el-button
					type="primary"
					class="action-button"
					:loading="runningAction === 'dynamic'"
					:disabled="isBusy && runningAction !== 'dynamic'"
					@click="handleExtractDynamicInfo"
				>
					提取角色动态
				</el-button>
			</div>
		</el-card>

		<el-card class="tool-card" shadow="never">
			<template #header>
				<div class="card-header">
					<el-icon><Connection /></el-icon>
					<span>关系提取入图</span>
				</div>
			</template>
			<div class="card-body">
				<el-button
					type="primary"
					class="action-button"
					:loading="runningAction === 'relations'"
					:disabled="isBusy && runningAction !== 'relations'"
					@click="handleExtractRelations"
				>
					提取关系入图
				</el-button>
			</div>
		</el-card>

		<el-card class="tool-card" shadow="never">
			<template #header>
				<div class="card-header">
					<el-icon><Box /></el-icon>
					<span>拓展记忆</span>
					<el-tag type="warning" size="small" style="margin-left: auto;">一站式</el-tag>
				</div>
			</template>
			<div class="card-body">
				<div class="memory-actions">
					<el-button
						type="primary"
						plain
						class="memory-button"
						:loading="runningAction === 'scene_state'"
						:disabled="isBusy && runningAction !== 'scene_state'"
						@click="handleExtractSceneState"
					>
						提取场景状态
					</el-button>
					<el-button
						type="primary"
						plain
						class="memory-button"
						:loading="runningAction === 'organization_state'"
						:disabled="isBusy && runningAction !== 'organization_state'"
						@click="handleExtractOrganizationState"
					>
						提取组织状态
					</el-button>
					<el-button
						type="primary"
						plain
						class="memory-button"
						:loading="runningAction === 'item_state'"
						:disabled="isBusy && runningAction !== 'item_state'"
						@click="handleExtractItemState"
					>
						提取物品状态
					</el-button>
					<el-button
						type="primary"
						plain
						class="memory-button"
						:loading="runningAction === 'concept_state'"
						:disabled="isBusy && runningAction !== 'concept_state'"
						@click="handleExtractConceptState"
					>
						提取概念掌握
					</el-button>
					<el-divider style="margin: 8px 0;" />
					<el-button
						type="warning"
						class="memory-button"
						:loading="runningAction === 'extract_all'"
						:disabled="isBusy"
						@click="handleExtractAll"
					>
						一站式提取
					</el-button>
				</div>
			</div>
		</el-card>

		<!-- 一站式提取预览弹窗 -->
		<el-dialog
			v-model="extractAllPreviewVisible"
			title="一站式提取结果"
			width="80%"
			:close-on-click-modal="true"
		>
			<div v-if="extractAllPreviewData" class="extract-all-preview">
				<el-alert
					title="以下内容已写入数据库"
					type="info"
					:closable="false"
					show-icon
					style="margin-bottom: 16px;"
				/>
				<el-tabs>
					<el-tab-pane
						v-for="result in extractAllPreviewData.results"
						:key="result.task"
						:label="result.name"
						:name="result.task"
					>
						<template v-if="result.success && hasPreviewContent(result.preview_data)">
							<el-table :data="getPreviewTableData(result)" stripe border size="small" max-height="400">
								<el-table-column
									v-for="col in getPreviewColumns(result)"
									:key="col.prop"
									:prop="col.prop"
									:label="col.label"
									:min-width="col.width || 120"
									show-overflow-tooltip
								/>
							</el-table>
							<div class="preview-summary">
								共 {{ getPreviewTableData(result).length }} 条记录
							</div>
						</template>
						<el-empty v-else-if="result.success" description="本次无内容提取" />
						<el-alert v-else :title="result.message" type="error" :closable="false" />
					</el-tab-pane>
				</el-tabs>
			</div>
		</el-dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Box, Connection, Lightning, Loading, Setting, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { getAIConfigOptions } from '@renderer/api/ai'
import { extractAll, type ExtractAllResponse } from '@renderer/api/memory'
import { useEditorStore, type ChapterExtractRunOptions } from '@renderer/stores/useEditorStore'

type ExtractionAction =
	| ''
	| 'dynamic'
	| 'relations'
	| 'scene_state'
	| 'organization_state'
	| 'item_state'
	| 'concept_state'
	| 'extract_all'

interface ChapterExtractConfigState {
	llm_config_id: number | null
	temperature: number
	max_tokens: number
	timeout: number
}

const EXTRACT_CONFIG_STORAGE_KEY = 'nf:chapter:extract-panel-config'
const DEFAULT_EXTRACT_CONFIG = {
	llm_config_id: null,
	temperature: 0.7,
	max_tokens: 8192,
	timeout: 120,
} satisfies ChapterExtractConfigState

const editorStore = useEditorStore()

const llmConfigs = ref<Array<{ id: number; display_name: string }>>([])
const runningAction = ref<ExtractionAction>('')
const settingsVisible = ref(false)
const extractConfig = reactive<ChapterExtractConfigState>({ ...DEFAULT_EXTRACT_CONFIG })
const editingConfig = reactive<ChapterExtractConfigState>({ ...DEFAULT_EXTRACT_CONFIG })

// 一站式提取预览相关状态
const extractAllPreviewVisible = ref(false)
const extractAllPreviewData = ref<ExtractAllResponse | null>(null)
const extractAllPendingOptions = ref<ChapterExtractRunOptions | null>(null)

const isBusy = computed(() => runningAction.value !== '')
const selectedModelName = computed(() => {
	const found = llmConfigs.value.find(item => Number(item.id) === Number(extractConfig.llm_config_id))
	return found?.display_name || ''
})

const runningActionLabel = computed(() => {
	switch (runningAction.value) {
		case 'dynamic':
			return '提取角色动态'
		case 'relations':
			return '提取关系入图'
		case 'scene_state':
			return '提取场景状态'
		case 'organization_state':
			return '提取组织状态'
		case 'item_state':
			return '提取物品状态'
		case 'concept_state':
			return '提取概念掌握'
		case 'extract_all':
			return '一站式提取'
		default:
			return '提取'
	}
})

function resolvePresetConfig(): ChapterExtractConfigState {
	return {
		...DEFAULT_EXTRACT_CONFIG,
		llm_config_id: llmConfigs.value.length > 0 ? Number(llmConfigs.value[0].id) : null,
	}
}

function sanitizeConfig(source?: Partial<ChapterExtractConfigState> | null): ChapterExtractConfigState {
	const modelIds = new Set(llmConfigs.value.map(item => Number(item.id)))
	const preset = resolvePresetConfig()
	const requestedModelId = source?.llm_config_id == null ? preset.llm_config_id : Number(source.llm_config_id)
	const llm_config_id =
		requestedModelId != null && modelIds.has(Number(requestedModelId))
			? Number(requestedModelId)
			: preset.llm_config_id

	return {
		llm_config_id,
		temperature:
			typeof source?.temperature === 'number'
				? Math.max(0, Math.min(2, source.temperature))
				: preset.temperature,
		max_tokens:
			typeof source?.max_tokens === 'number'
				? Math.max(256, Math.round(source.max_tokens))
				: preset.max_tokens,
		timeout:
			typeof source?.timeout === 'number'
				? Math.max(10, Math.round(source.timeout))
				: preset.timeout,
	}
}

function readSavedConfig(): Partial<ChapterExtractConfigState> {
	try {
		const raw = localStorage.getItem(EXTRACT_CONFIG_STORAGE_KEY)
		return raw ? JSON.parse(raw) : {}
	} catch {
		return {}
	}
}

function writeSavedConfig(config: ChapterExtractConfigState) {
	try {
		localStorage.setItem(EXTRACT_CONFIG_STORAGE_KEY, JSON.stringify(config))
	} catch {}
}

function hydrateConfig() {
	Object.assign(extractConfig, sanitizeConfig(readSavedConfig()))
	syncEditingConfigFromSaved()
}

function syncEditingConfigFromSaved() {
	Object.assign(editingConfig, extractConfig)
}

function resetEditingConfigToPreset() {
	Object.assign(editingConfig, resolvePresetConfig())
}

function saveConfig() {
	const nextConfig = sanitizeConfig(editingConfig)
	if (!nextConfig.llm_config_id) {
		ElMessage.warning('请先选择模型')
		return
	}
	Object.assign(extractConfig, nextConfig)
	writeSavedConfig(nextConfig)
	settingsVisible.value = false
	ElMessage.success('提取模型配置已保存到本地')
}

function buildExtractOptions(): ChapterExtractRunOptions | null {
	if (!extractConfig.llm_config_id) {
		ElMessage.warning('请先选择模型')
		return null
	}
	return {
		llm_config_id: Number(extractConfig.llm_config_id),
		temperature: extractConfig.temperature,
		max_tokens: Math.round(extractConfig.max_tokens),
		timeout: Math.round(extractConfig.timeout),
	}
}

async function runExtraction(
	action: Exclude<ExtractionAction, ''>,
	runner: (options: ChapterExtractRunOptions) => Promise<void>
) {
	if (runningAction.value) return
	const options = buildExtractOptions()
	if (!options) return
	runningAction.value = action
	try {
		await runner(options)
	} catch (error) {
		console.error(`[ChapterToolsPanel] ${action} failed:`, error)
	} finally {
		runningAction.value = ''
	}
}

async function handleExtractDynamicInfo() {
	await runExtraction('dynamic', options => editorStore.triggerExtractDynamicInfo(options))
}

async function handleExtractRelations() {
	await runExtraction('relations', options => editorStore.triggerExtractRelations(options))
}

async function handleExtractSceneState() {
	await runExtraction('scene_state', options => editorStore.triggerExtractSceneState(options))
}

async function handleExtractOrganizationState() {
	await runExtraction('organization_state', options => editorStore.triggerExtractOrganizationState(options))
}

async function handleExtractItemState() {
	await runExtraction('item_state', options => editorStore.triggerExtractItemState(options))
}

async function handleExtractConceptState() {
	await runExtraction('concept_state', options => editorStore.triggerExtractConceptState(options))
}

async function handleExtractAll() {
	await runExtraction('extract_all', async options => {
		const result = await editorStore.triggerExtractAll(options)
		// 直接使用返回的 result，不再检查 store（避免时序歧义）
		if (result) {
			extractAllPreviewData.value = result
			extractAllPendingOptions.value = options
			extractAllPreviewVisible.value = true
		}
	})
}

// 判断预览数据是否有内容
function hasPreviewContent(previewData: Record<string, any> | undefined): boolean {
	if (!previewData) return false
	// 检查常见的列表字段
	return ['scenes', 'organizations', 'items', 'concepts', 'relations', 'info_list'].some(
		key => Array.isArray(previewData[key]) && previewData[key].length > 0
	)
}

// 获取预览表格数据
function getPreviewTableData(result: ExtractAllResponse['results'][0]): Record<string, any>[] {
	const data = result.preview_data
	if (!data) return []
	// 根据任务类型返回对应数组
	if (result.task === 'scene_state') return data.scenes || []
	if (result.task === 'organization_state') return data.organizations || []
	if (result.task === 'item_state') return data.items || []
	if (result.task === 'concept_state') return data.concepts || []
	if (result.task === 'relation') return data.relations || []
	if (result.task === 'character_dynamic') {
		// 将 dynamic_info 对象转换为可读字符串
		// 原始: { name: "角色A", dynamic_info: { "状态": [{info:"受伤"}], "情绪": [{info:"高兴"}] } }
		// 转换后: { name: "角色A", dynamic_info: "状态: 受伤; 情绪: 高兴" }
		return (data.info_list || []).map((item: Record<string, any>) => {
			const infoEntries = Object.entries(item.dynamic_info || {})
				.map(([category, items]) => {
					const infoTexts = (items as Array<{ info?: string }>).map(i => i.info).filter(Boolean).join('、')
					return infoTexts ? `${category}: ${infoTexts}` : null
				})
				.filter(Boolean)
			return {
				name: item.name,
				dynamic_info: infoEntries.join('; ') || '(无)',
			}
		})
	}
	return []
}

// 获取预览表格列
function getPreviewColumns(result: ExtractAllResponse['results'][0]): Array<{ prop: string; label: string; width?: number }> {
	const task = result.task
	if (task === 'scene_state') {
		return [
			{ prop: 'name', label: '名称', width: 100 },
			{ prop: 'description', label: '描述' },
			{ prop: 'function_in_story', label: '作用' },
			{ prop: 'dynamic_state', label: '状态', width: 150 },
		]
	}
	if (task === 'organization_state') {
		return [
			{ prop: 'name', label: '名称', width: 100 },
			{ prop: 'description', label: '描述' },
			{ prop: 'influence', label: '影响力', width: 120 },
			{ prop: 'relationship', label: '关系', width: 150 },
			{ prop: 'dynamic_state', label: '状态', width: 150 },
		]
	}
	if (task === 'item_state') {
		return [
			{ prop: 'name', label: '名称', width: 100 },
			{ prop: 'category', label: '类别', width: 80 },
			{ prop: 'description', label: '描述' },
			{ prop: 'current_state', label: '当前状态', width: 120 },
		]
	}
	if (task === 'concept_state') {
		return [
			{ prop: 'name', label: '名称', width: 100 },
			{ prop: 'category', label: '类别', width: 80 },
			{ prop: 'description', label: '描述' },
			{ prop: 'rule_definition', label: '规则定义' },
		]
	}
	if (task === 'relation') {
		return [
			{ prop: 'a', label: '实体A', width: 100 },
			{ prop: 'kind', label: '关系', width: 80 },
			{ prop: 'b', label: '实体B', width: 100 },
			{ prop: 'fact', label: '事实' },
		]
	}
	if (task === 'character_dynamic') {
		return [
			{ prop: 'name', label: '角色', width: 100 },
			{ prop: 'dynamic_info', label: '动态信息' },
		]
	}
	return []
}

onMounted(async () => {
	try {
		const options = await getAIConfigOptions()
		llmConfigs.value = options?.llm_configs || []
	} catch (error) {
		console.error('Failed to load LLM configs:', error)
	}
	hydrateConfig()
})
</script>

<style scoped>
.chapter-tools-panel {
	padding: 16px;
	display: flex;
	flex-direction: column;
	gap: 14px;
	height: 100%;
	overflow-y: auto;
	background:
		linear-gradient(
			180deg,
			color-mix(in srgb, var(--el-fill-color-light) 55%, transparent) 0%,
			var(--el-bg-color) 100%
		);
}

.panel-toolbar {
	display: flex;
	justify-content: flex-start;
}

.config-trigger {
	min-width: 144px;
}

.config-form {
	padding-top: 4px;
}

.config-actions {
	width: 100%;
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 8px;
}

.tool-card {
	border-radius: 14px;
	border: 1px solid var(--el-border-color-light);
	background: var(--el-bg-color-overlay);
	box-shadow: 0 10px 28px color-mix(in srgb, var(--el-text-color-primary) 6%, transparent);
}

.busy-banner {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 10px 12px;
	border-radius: 12px;
	background: color-mix(in srgb, var(--el-color-primary) 10%, var(--el-fill-color-light));
	color: var(--el-color-primary);
	font-size: 13px;
	border: 1px solid color-mix(in srgb, var(--el-color-primary) 18%, transparent);
}

.busy-icon {
	font-size: 16px;
}

.card-header {
	display: flex;
	align-items: center;
	gap: 8px;
	font-weight: 700;
	color: var(--el-text-color-primary);
}

.card-body {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.action-button {
	width: 100%;
}

.memory-actions {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 10px;
}

.memory-button {
	width: 100%;
	margin-left: 0;
}

@media (max-width: 900px) {
	.panel-toolbar {
		justify-content: stretch;
	}

	.config-trigger {
		width: 100%;
	}

	.memory-actions {
		grid-template-columns: minmax(0, 1fr);
	}
}

.extract-all-preview {
	padding: 8px 0;
}

.preview-summary {
	margin-top: 8px;
	text-align: right;
	color: var(--el-text-color-secondary);
	font-size: 13px;
}
</style>
