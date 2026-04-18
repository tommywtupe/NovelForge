<template>
	<div class="glossary-editor">
		<!-- 工具栏 -->
		<div class="toolbar">
			<div class="toolbar-row">
				<div class="toolbar-group">
					<span class="group-label">术语表</span>
					<el-select
						v-model="localContent.target_language"
						size="small"
						placeholder="选择目标语言"
						class="target-lang-select"
						@change="handleTargetLanguageChange"
					>
						<el-option label="繁體中文" value="繁體中文" />
						<el-option label="日文" value="日文" />
						<el-option label="英文" value="英文" />
						<el-option label="韓文" value="韓文" />
					</el-select>
				</div>

				<div class="toolbar-spacer"></div>

				<div class="toolbar-group">
					<el-button size="small" @click="handleAddTerm">
						<el-icon><Plus /></el-icon> 添加术语
					</el-button>

					<el-dropdown @command="handleUpdateMode">
						<el-button type="primary" size="small">
							<el-icon><Refresh /></el-icon> 更新术语表
							<el-icon class="el-icon--right"><arrow-down /></el-icon>
						</el-button>
						<template #dropdown>
							<el-dropdown-menu>
								<el-dropdown-item command="scan_new_concepts">
									仅检测新概念
									<p class="dropdown-desc">扫描项目中新增的专有名词</p>
								</el-dropdown-item>
								<el-dropdown-item command="translate_new_concepts">
									仅为新概念更新翻译
									<p class="dropdown-desc">只翻译新检测到的术语</p>
								</el-dropdown-item>
								<el-dropdown-item command="full_rebuild_translations">
									全量重建翻译
									<p class="dropdown-desc">重新扫描所有概念并翻译</p>
								</el-dropdown-item>
								<el-dropdown-item command="scan_and_translate">
									检测并翻译
									<p class="dropdown-desc">同时检测新概念和自动完成翻译</p>
								</el-dropdown-item>
							</el-dropdown-menu>
						</template>
					</el-dropdown>
				</div>
			</div>

			<div class="toolbar-status-row">
				<span class="status-info">
					共 {{ localContent.terms?.length || 0 }} 个术语
					<span v-if="pendingTerms.length > 0">，{{ pendingTerms.length }} 个待翻译</span>
				</span>
			</div>
		</div>

		<!-- 术语列表 -->
		<div class="terms-container">
			<el-table
				:data="localContent.terms || []"
				border
				stripe
				style="width: 100%"
				size="small"
			>
				<el-table-column label="术语分类" width="120">
					<template #default="{ row }">
						<el-tag size="small" :type="getCategoryTagType(row.category)">
							{{ getCategoryLabel(row.category) }}
						</el-tag>
					</template>
				</el-table-column>

				<el-table-column label="术语来源" prop="source" min-width="150">
					<template #default="{ row }">
						<span v-if="!row.source_card_id" class="manual-term">{{ row.source }}</span>
						<el-link v-else type="primary" @click="openSourceCard(row.source_card_id)">
							{{ row.source }}
						</el-link>
					</template>
				</el-table-column>

				<el-table-column label="翻译" min-width="150">
					<template #default="{ row, $index }">
						<el-input
							v-model="row.translated"
							size="small"
							placeholder="输入翻译"
							@change="handleTermChange($index)"
						/>
					</template>
				</el-table-column>

				<el-table-column label="备注" min-width="120">
					<template #default="{ row, $index }">
						<el-input
							v-model="row.notes"
							size="small"
							placeholder="备注"
							@change="handleTermChange($index)"
						/>
					</template>
				</el-table-column>

				<el-table-column label="操作" width="80" fixed="right">
					<template #default="{ $index }">
						<el-button
							type="danger"
							size="small"
							text
							@click="handleDeleteTerm($index)"
						>
							<el-icon><Delete /></el-icon>
						</el-button>
					</template>
				</el-table-column>
			</el-table>
		</div>

		<!-- 添加术语对话框 -->
		<el-dialog v-model="addTermDialogVisible" title="添加术语" width="500px">
			<el-form :model="newTerm" label-width="80px">
				<el-form-item label="术语">
					<el-input v-model="newTerm.source" placeholder="输入原文" />
				</el-form-item>
				<el-form-item label="翻译">
					<el-input v-model="newTerm.translated" placeholder="输入翻译" />
				</el-form-item>
				<el-form-item label="分类">
					<el-select v-model="newTerm.category" placeholder="选择分类">
						<el-option label="角色" value="character" />
						<el-option label="场景" value="scene" />
						<el-option label="组织" value="organization" />
						<el-option label="物品" value="item" />
						<el-option label="概念" value="concept" />
						<el-option label="其他" value="other" />
					</el-select>
				</el-form-item>
				<el-form-item label="备注">
					<el-input v-model="newTerm.notes" type="textarea" placeholder="备注说明" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="addTermDialogVisible = false">取消</el-button>
				<el-button type="primary" @click="confirmAddTerm">确定</el-button>
			</template>
		</el-dialog>

		<!-- 更新进度对话框 -->
		<el-dialog v-model="updateDialogVisible" title="更新术语表" width="600px">
			<div v-if="updateLoading" class="update-progress">
				<el-icon class="is-loading" :size="24"><Loading /></el-icon>
				<span>正在{{ updateStatus }}...</span>
			</div>
			<div v-else-if="updateResult" class="update-result">
				<el-result
					icon="success"
					:title="updateResult.glossary_card_id ? '更新成功' : '更新失败'"
				>
					<template #sub-title>
						<div class="result-details">
							<p>新增术语: {{ updateResult.new_terms_count }}</p>
							<p>更新术语: {{ updateResult.updated_terms_count }}</p>
							<p>移除术语: {{ updateResult.removed_terms_count }}</p>
						</div>
					</template>
				</el-result>
			</div>
			<template #footer>
				<el-button @click="updateDialogVisible = false">关闭</el-button>
				<el-button v-if="updateResult?.new_terms_count && updateResult.new_terms_count > 0" type="primary" @click="handleTranslateNewTerms">
					翻译新术语
				</el-button>
			</template>
		</el-dialog>
	</div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
	Plus, Delete, Refresh, ArrowDown, Loading
} from '@element-plus/icons-vue'
import type { CardRead } from '@renderer/api/cards'
import {
	listGlossaries,
	extractAndUpdateGlossary,
	updateGlossaryTerms,
	deleteGlossary,
	buildGlossaryContext,
	type GlossaryTerm,
	type UpdateMode,
} from '@renderer/api/glossary'
import { useProjectStore } from '@renderer/stores/useProjectStore'

const props = defineProps<{
	card: CardRead
}>()

const emit = defineEmits<{
	(e: 'save'): void
	(e: 'update:dirty', value: boolean): void
}>()

const projectStore = useProjectStore()

interface GlossaryContent {
	name: string
	target_language: string
	terms: GlossaryTerm[]
	updated_at?: string
}

const localContent = reactive<GlossaryContent>({
	name: '',
	target_language: '繁體中文',
	terms: [],
})

const isDirty = ref(false)
const addTermDialogVisible = ref(false)
const updateDialogVisible = ref(false)
const updateLoading = ref(false)
const updateStatus = ref('')
const updateResult = ref<any>(null)
const pendingTerms = ref<GlossaryTerm[]>([])

const newTerm = reactive<GlossaryTerm>({
	source: '',
	translated: '',
	category: 'other',
	source_card_id: null,
	notes: '',
})

const categoryMap: Record<string, string> = {
	character: '角色',
	scene: '场景',
	organization: '组织',
	item: '物品',
	concept: '概念',
	other: '其他',
}

function getCategoryLabel(category: string): string {
	return categoryMap[category] || '其他'
}

function getCategoryTagType(category: string): string {
	const typeMap: Record<string, any> = {
		character: '',
		scene: 'success',
		organization: 'warning',
		item: 'info',
		concept: 'danger',
		other: 'info',
	}
	return typeMap[category] || 'info'
}

function loadGlossary() {
	if (!props.card?.content) return

	const content = props.card.content as any
	localContent.name = content.name || props.card.title || ''
	localContent.target_language = content.target_language || '繁體中文'
	localContent.terms = content.terms || []
	localContent.updated_at = content.updated_at

	pendingTerms.value = localContent.terms.filter((t: GlossaryTerm) => !t.translated)
}

async function handleSave() {
	try {
		const updatedContent = {
			...localContent,
			updated_at: new Date().toISOString(),
		}
		const cardUpdate = {
			id: props.card.id,
			title: localContent.name,
			content: updatedContent,
		}
		await updateGlossaryTerms(props.card.id, localContent.terms)
		isDirty.value = false
		emit('update:dirty', false)
		emit('save')
		ElMessage.success('保存成功')
	} catch (e) {
		console.error('Save failed:', e)
		ElMessage.error('保存失败')
	}
}

function handleTermChange(index: number) {
	isDirty.value = true
	emit('update:dirty', true)
	pendingTerms.value = localContent.terms.filter((t: GlossaryTerm) => !t.translated)
}

function handleTargetLanguageChange() {
	isDirty.value = true
	emit('update:dirty', true)
}

function handleAddTerm() {
	newTerm.source = ''
	newTerm.translated = ''
	newTerm.category = 'other'
	newTerm.source_card_id = null
	newTerm.notes = ''
	addTermDialogVisible.value = true
}

function confirmAddTerm() {
	if (!newTerm.source.trim()) {
		ElMessage.warning('请输入术语')
		return
	}

	localContent.terms.push({
		source: newTerm.source.trim(),
		translated: newTerm.translated.trim(),
		category: newTerm.category,
		source_card_id: null,
		notes: newTerm.notes?.trim() || '',
	})

	isDirty.value = true
	emit('update:dirty', true)
	addTermDialogVisible.value = false
	ElMessage.success('术语已添加')
}

async function handleDeleteTerm(index: number) {
	try {
		await ElMessageBox.confirm('确定要删除这个术语吗？', '确认删除', {
			confirmButtonText: '确定',
			cancelButtonText: '取消',
			type: 'warning',
		})
		localContent.terms.splice(index, 1)
		isDirty.value = true
		emit('update:dirty', true)
		ElMessage.success('术语已删除')
	} catch {
		// 用户取消
	}
}

async function handleUpdateMode(mode: UpdateMode) {
	if (!projectStore.currentProject?.id) {
		ElMessage.error('未找到项目')
		return
	}

	updateDialogVisible.value = true
	updateLoading.value = true
	updateResult.value = null
	updateStatus.value = getUpdateStatusText(mode)

	try {
		const result = await extractAndUpdateGlossary({
			project_id: projectStore.currentProject.id,
			target_language: localContent.target_language as any,
			glossary_card_id: props.card.id,
			update_mode: mode,
		})

		updateResult.value = result

		// 重新加载术语表
		if (mode === 'scan_and_translate' || mode === 'full_rebuild_translations') {
			const cards = await listGlossaries(projectStore.currentProject.id, localContent.target_language)
			const updatedCard = cards.find((c: any) => c.id === props.card.id)
			if (updatedCard) {
				localContent.terms = updatedCard.content?.terms || []
			}
		} else if (mode === 'scan_new_concepts' || mode === 'translate_new_concepts') {
			// 仅当返回的新术语列表有内容时才更新，避免覆盖已有术语
			if (result.terms && result.terms.length > 0) {
				localContent.terms = result.terms
			}
		}

		pendingTerms.value = localContent.terms.filter((t: GlossaryTerm) => !t.translated)
	} catch (e) {
		console.error('Update glossary failed:', e)
		ElMessage.error('更新术语表失败')
		updateResult.value = { glossary_card_id: null }
	} finally {
		updateLoading.value = false
	}
}

function getUpdateStatusText(mode: UpdateMode): string {
	const statusMap: Record<UpdateMode, string> = {
		'scan_new_concepts': '检测新概念',
		'translate_new_concepts': '提取待翻译术语',
		'full_rebuild_translations': '扫描并翻译',
		'scan_and_translate': '扫描并翻译所有概念',
	}
	return statusMap[mode] || '处理中'
}

function handleTranslateNewTerms() {
	// 触发翻译流程
	updateDialogVisible.value = false
	// TODO: 调用翻译服务翻译待翻译的术语
	ElMessage.info('翻译功能开发中')
}

function openSourceCard(cardId: number) {
	// TODO: 打开源卡片
	console.log('Open source card:', cardId)
}

onMounted(() => {
	loadGlossary()
})

watch(() => props.card, () => {
	loadGlossary()
}, { deep: true })

defineExpose({
	handleSave,
})
</script>

<style scoped>
.glossary-editor {
	display: flex;
	flex-direction: column;
	height: 100%;
	background: var(--el-bg-color);
}

.toolbar {
	flex-shrink: 0;
	padding: 12px 16px;
	border-bottom: 1px solid var(--el-border-color-light);
	background: var(--el-fill-color-lighter);
}

.toolbar-row {
	display: flex;
	align-items: center;
	gap: 12px;
}

.toolbar-group {
	display: flex;
	align-items: center;
	gap: 8px;
}

.toolbar-spacer {
	flex: 1;
}

.group-label {
	font-size: 14px;
	font-weight: 600;
	color: var(--el-text-color-primary);
}

.glossary-name {
	font-size: 14px;
	color: var(--el-text-color-primary);
}

.target-lang-select {
	width: 120px;
}

.target-lang-select :deep(.el-input__wrapper) {
	background: var(--el-fill-color-light);
	border-radius: 6px;
	padding-left: 10px;
	padding-right: 10px;
}

.target-lang-select :deep(.el-input__inner) {
	font-size: 13px;
	color: var(--el-text-color-primary);
}

.toolbar-status-row {
	margin-top: 8px;
	padding-top: 8px;
	border-top: 1px solid var(--el-border-color-lighter);
}

.status-info {
	font-size: 12px;
	color: var(--el-text-color-secondary);
}

.terms-container {
	flex: 1;
	overflow: auto;
	padding: 16px;
}

.manual-term {
	color: var(--el-text-color-secondary);
	font-style: italic;
}

.dropdown-desc {
	font-size: 12px;
	color: var(--el-text-color-secondary);
	margin: 2px 0 0 0;
}

.update-progress {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 12px;
	padding: 24px;
}

.update-result {
	padding: 16px;
}

.result-details {
	text-align: left;
}

.result-details p {
	margin: 4px 0;
	color: var(--el-text-color-secondary);
}
</style>
