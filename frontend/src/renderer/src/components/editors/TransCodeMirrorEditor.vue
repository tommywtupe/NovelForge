<template>
	<div class="chapter-studio">
	<div class="toolbar">
		<div class="toolbar-row">
			<!-- 编辑功能组 -->
			<div class="toolbar-group">
				<span class="group-label">编辑</span>
				<el-dropdown @command="(c:any) => fontSize = c" size="small">
					<el-button size="small">
						{{ fontSize }}px
						<el-icon class="el-icon--right"><arrow-down /></el-icon>
					</el-button>
					<template #dropdown>
						<el-dropdown-menu>
							<el-dropdown-item :command="14">小 (14px)</el-dropdown-item>
							<el-dropdown-item :command="16">中 (16px)</el-dropdown-item>
							<el-dropdown-item :command="18">大 (18px)</el-dropdown-item>
							<el-dropdown-item :command="20">特大 (20px)</el-dropdown-item>
						</el-dropdown-menu>
					</template>
				</el-dropdown>

				<el-dropdown @command="(c:any) => lineHeight = c" size="small">
					<el-button size="small">
						{{ lineHeight }}
						<el-icon class="el-icon--right"><arrow-down /></el-icon>
					</el-button>
					<template #dropdown>
						<el-dropdown-menu>
							<el-dropdown-item :command="1.4">紧凑</el-dropdown-item>
							<el-dropdown-item :command="1.6">适中</el-dropdown-item>
							<el-dropdown-item :command="1.8">舒适</el-dropdown-item>
							<el-dropdown-item :command="2.0">宽松</el-dropdown-item>
						</el-dropdown-menu>
					</template>
				</el-dropdown>
			</div>

			<div class="toolbar-divider"></div>

			<!-- AI功能组 - 翻译专用 -->
			<div class="toolbar-group toolbar-group-ai">
				<span class="group-label">AI</span>
				<div class="ai-action-bar">
					<el-button type="primary" size="small" :loading="aiLoading" :disabled="reviewLoading" @click="executeTranslation">
						<el-icon><MagicStick /></el-icon> 翻译
					</el-button>

					<el-dropdown
						split-button
						type="primary"
						size="small"
						popper-class="review-prompt-dropdown"
						:disabled="aiLoading || reviewLoading"
						:loading="reviewLoading"
						@command="handleReviewPromptChange"
						@click="executeReview"
					>
						<span class="review-button-label">
							<el-icon v-if="reviewLoading" class="review-loading-icon"><Loading /></el-icon>
							<el-icon v-else><List /></el-icon>
							{{ reviewLoading ? '审核中...' : '审核' }}
						</span>
						<template #dropdown>
							<el-dropdown-menu>
								<el-dropdown-item
									v-for="prompt in reviewPrompts"
									:key="prompt"
									:command="prompt"
								>
									<div class="prompt-item">
										<span>{{ prompt }}</span>
										<el-icon v-if="prompt === currentReviewPrompt" class="check-icon"><Select /></el-icon>
									</div>
								</el-dropdown-item>
							</el-dropdown-menu>
						</template>
					</el-dropdown>

					<AIPerCardParams
						:card-id="props.card.id"
						:card-type-name="props.card.card_type?.name"
						class="ai-config-entry"
					/>

					<el-button
						type="danger"
						plain
						size="small"
						:disabled="!canInterruptAiTask"
						@click="interruptStream"
					>
						<el-icon><CircleClose /></el-icon> 中断
					</el-button>
				</div>
			</div>
		</div>
		<div class="toolbar-status-row">
			<div class="toolbar-status-spacer"></div>
			<div class="ai-status-strip">
				<span class="status-pill">模型 · {{ selectedModelName || '未设置' }}</span>
				<el-select
					v-model="localCard.content.target_language"
					size="small"
					placeholder="选择目标语言"
					class="target-lang-select"
					@change="handleTargetLanguageChange"
				>
					<el-option
						v-for="lang in targetLanguageOptions"
						:key="lang.value"
						:label="lang.label"
						:value="lang.value"
					/>
				</el-select>

				<el-select
					v-model="selectedGlossaryId"
					size="small"
					placeholder="选择术语表"
					class="glossary-select"
					clearable
					@change="handleGlossaryChange"
				>
					<el-option
						v-for="glossary in glossaryOptions"
						:key="glossary.id"
						:label="glossary.title"
						:value="glossary.id"
					/>
				</el-select>
			</div>
		</div>
	</div>

	<div class="editor-content-wrapper">
		<!-- 标题区域 -->
	<div class="chapter-header">
		<div class="title-section">
			<h1
				class="chapter-title"
				contenteditable="true"
				@blur="handleTitleBlur"
				@keydown.enter.prevent="handleTitleEnter"
				ref="titleElement"
			>{{ localCard.title }}</h1>
			<div class="title-meta">
				<el-icon class="word-count-icon"><Timer /></el-icon>
				<span class="word-count-text">{{ wordCount }} 字</span>
				<span class="separator">|</span>
				<span class="line-count-text">{{ lineCount }} 行</span>
			</div>
		</div>
	</div>

		<!-- CodeMirror 容器 -->
		<div ref="cmRoot" class="editor-content"></div>
	</div>

	<!-- 审核对话框 -->
	<el-dialog v-model="reviewDialogVisible" title="翻译审核结果" width="72%">
			<div v-if="reviewText" class="review-dialog-body">
				<div class="review-overview">
					<div class="review-overview-main">
						<el-tag
							v-if="reviewDraft"
							:type="getReviewVerdictTagType(reviewDraft.quality_gate)"
							effect="dark"
						>
							{{ formatReviewVerdict(reviewDraft.quality_gate) }}
						</el-tag>
						<span v-if="reviewDraft" class="review-score">
							{{ reviewDraft.review_profile }}
						</span>
					</div>
					<p class="review-summary">这是本次审核草稿。</p>
				</div>

				<div class="review-text-block">
					<SimpleMarkdown
						:markdown="reviewText || '（暂无内容）'"
						class="review-markdown"
					/>
				</div>
			</div>
			<template #footer>
				<div class="review-dialog-footer">
					<el-button @click="reviewDialogVisible = false">关闭</el-button>
				</div>
			</template>
		</el-dialog>
	</div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { storeToRefs } from 'pinia'
import SimpleMarkdown from '../common/SimpleMarkdown.vue'
import { useCardStore } from '@renderer/stores/useCardStore'
import { useProjectStore } from '@renderer/stores/useProjectStore'
import { usePerCardAISettingsStore, type PerCardAIParams } from '@renderer/stores/usePerCardAISettingsStore'
import { useEditorStore } from '@renderer/stores/useEditorStore'
import { useAppStore } from '@renderer/stores/useAppStore'
import { type CardRead, type CardUpdate } from '@renderer/api/cards'
import { generateContinuationStreaming, type ContinuationRequest, getAIConfigOptions, type AIConfigOptions } from '@renderer/api/ai'
import { runReview, type QualityGate, type ReviewDraftResult } from '@renderer/api/chapterReviews'
import { listGlossaries, type TranslationGlossaryContent } from '@renderer/api/glossary'
import { getCardAIParams } from '@renderer/api/setting'
import { ArrowDown, MagicStick, CircleClose, List, Timer, Select, Loading } from '@element-plus/icons-vue'
import AIPerCardParams from '../common/AIPerCardParams.vue'
import { resolveTemplate } from '@renderer/services/contextResolver'
import { getCardContextTemplates, getContextTemplateByKind, normalizeContextTemplateKind, type ContextTemplateKind, type ContextTemplates } from '@renderer/services/contextSlots'

import { EditorState, StateEffect, StateField } from '@codemirror/state'
import { EditorView, keymap, Decoration, DecorationSet, lineNumbers } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap, insertNewline } from '@codemirror/commands'

const props = defineProps<{
	card: CardRead
	prefetched?: any | null
	contextTemplates?: ContextTemplates
	generationContextKind?: ContextTemplateKind
	reviewContextKind?: ContextTemplateKind
}>()

const emit = defineEmits<{
	(e: 'save'): void
	(e: 'switch-tab', tab: string): void
	(e: 'update:dirty', value: boolean): void
	(e: 'update:generation-context-kind', value: ContextTemplateKind): void
	(e: 'update:review-context-kind', value: ContextTemplateKind): void
}>()

const cardStore = useCardStore()
const projectStore = useProjectStore()
const perCardStore = usePerCardAISettingsStore()
const editorStore = useEditorStore()
const appStore = useAppStore()
const { cards } = storeToRefs(cardStore)
const isDarkMode = computed(() => appStore.isDarkMode)

const ready = ref(false)
const cmRoot = ref<HTMLElement | null>(null)
const titleElement = ref<HTMLElement | null>(null)
let view: EditorView | null = null

// 自定义高亮系统
type HighlightEffectPayload =
	| { mode: 'single'; from: number; to: number }
	| { mode: 'compare'; originalFrom: number; originalTo: number; previewFrom: number; previewTo: number }
	| null

const setHighlightEffect = StateEffect.define<HighlightEffectPayload>()

const highlightField = StateField.define<DecorationSet>({
	create() {
		return Decoration.none
	},
	update(highlights, tr) {
		highlights = highlights.map(tr.changes)
		for (const effect of tr.effects) {
			if (effect.is(setHighlightEffect)) {
				if (effect.value === null) {
					highlights = Decoration.none
				} else if (effect.value.mode === 'single') {
					const decoration = Decoration.mark({
						class: 'cm-ai-highlight'
					}).range(effect.value.from, effect.value.to)
					highlights = Decoration.set([decoration])
				} else {
					const originalDecoration = Decoration.mark({
						class: 'cm-ai-original-highlight'
					}).range(effect.value.originalFrom, effect.value.originalTo)
					const previewDecoration = Decoration.mark({
						class: 'cm-ai-preview-highlight'
					}).range(effect.value.previewFrom, effect.value.previewTo)
					highlights = Decoration.set([originalDecoration, previewDecoration])
				}
			}
		}
		return highlights
	},
	provide: f => EditorView.decorations.from(f)
})

const localCard = reactive({
	...props.card,
	content: {
		...(props.card.content as any || {}),
		content: typeof (props.card.content as any)?.content === 'string'
			? (props.card.content as any).content
			: '',
		word_count: typeof (props.card.content as any)?.word_count === 'number'
			? (props.card.content as any).word_count
			: 0,
		title: (props.card.content as any)?.title ?? props.card.title ?? '',
		target_language: (props.card.content as any)?.target_language || '繁體中文',
	}
})

const generationContextKindValue = computed(() => normalizeContextTemplateKind(props.generationContextKind, 'generation'))
const reviewContextKindValue = computed(() => normalizeContextTemplateKind(props.reviewContextKind, 'review'))

function getResolvedContext(kind: ContextTemplateKind | string, fallbackKind: ContextTemplateKind) {
	const currentCardWithContent = {
		...props.card,
		content: {
			...(props.card.content as any || {}),
			...(localCard.content as any || {}),
		},
	}
	const template = getContextTemplateByKind(
		props.card,
		props.contextTemplates || getCardContextTemplates(props.card),
		kind,
		fallbackKind
	)
	return template
		? resolveTemplate({
			template,
			cards: cards.value,
			currentCard: currentCardWithContent as any,
		})
		: ''
}

// 每卡片参数
const editingParams = ref<PerCardAIParams>({})
const aiOptions = ref<AIConfigOptions | null>(null)
async function loadAIOptions() { try { aiOptions.value = await getAIConfigOptions() } catch {} }
const perCardParams = computed(() => perCardStore.getByCardId(props.card.id))
const selectedModelName = computed(() => {
	try {
		const id = (perCardParams.value || editingParams.value)?.llm_config_id
		const list = aiOptions.value?.llm_configs || []
		const found = list.find(m => m.id === id)
		return found?.display_name || (id != null ? String(id) : '')
	} catch { return '' }
})

watch(() => props.card, async (newCard) => {
	if (!newCard) return
	await loadAIOptions()
	try {
		const resp = await getCardAIParams(newCard.id)
		const eff = (resp as any)?.effective_params
		if (eff && Object.keys(eff).length) {
			editingParams.value = { ...eff }
			perCardStore.setForCard(newCard.id, { ...eff })
			return
		}
	} catch {}
	const saved = perCardStore.getByCardId(newCard.id)
	if (saved) editingParams.value = { ...saved }
	else {
		const preset = getPresetForType(newCard.card_type?.name) || {}
		if (!preset.llm_config_id) { const first = aiOptions.value?.llm_configs?.[0]; if (first) preset.llm_config_id = first.id }
		editingParams.value = { ...preset }
		perCardStore.setForCard(newCard.id, editingParams.value)
	}
}, { immediate: true })

function getPresetForType(typeName?: string): PerCardAIParams | undefined {
	const map: Record<string, PerCardAIParams> = {
		'正文翻译卡': { prompt_name: '正文翻译', llm_config_id: 1, temperature: 0.3, max_tokens: 8192, timeout: 120 },
	}
	return map[typeName || '']
}

function computeWordCount(text: string): number {
	return (text || '').replace(/\s+/g, '').length
}

function computeLineCount(text: string): number {
	return ((text || '').match(/\n/g) || []).length + 1  // 行数 = 换行符数量 + 1
}

const wordCount = ref(0)
const lineCount = ref(0)
const aiLoading = ref(false)
let streamHandle: { cancel: () => void } | null = null
const canInterruptAiTask = computed(() => aiLoading.value || reviewLoading.value || Boolean(reviewAbortController.value))

const pendingAiEdit = ref<{
	originalFrom: number
	originalTo: number
	originalText: string
	previewFrom: number
	previewTo: number
	generating: boolean
} | null>(null)

// 跟踪原始内容以检测dirty状态
const originalContent = ref<string>('')
const isDirty = ref(false)
const reviewLoading = ref(false)
const reviewDialogVisible = ref(false)
const reviewText = ref('')
const reviewDraft = ref<ReviewDraftResult | null>(null)
const reviewAbortController = ref<AbortController | null>(null)

// 字号/行距
const fontSize = ref<number>(20)
const lineHeight = ref<number>(1.8)
const fontSizePx = computed(() => `${fontSize.value}px`)
const lineHeightStr = computed(() => String(lineHeight.value))

const reviewPrompts = ref<string[]>([])
const currentReviewPrompt = ref('章节审核')

// 目标语言选项
const targetLanguageOptions = [
	{ value: '繁體中文', label: '繁體中文' },
	{ value: '日文', label: '日文' },
	{ value: '英文', label: '英文' },
	{ value: '韓文', label: '韓文' },
]

function handleTargetLanguageChange(lang: string) {
	isDirty.value = true
	emit('update:dirty', true)
}

// 术语表相关
interface GlossaryOption {
	id: number
	title: string
	content: TranslationGlossaryContent
}

const glossaryOptions = ref<GlossaryOption[]>([])
const selectedGlossaryId = ref<number | null>(null)
const selectedGlossary = ref<TranslationGlossaryContent | null>(null)

async function loadGlossaries() {
	if (!projectStore.currentProject?.id) {
		glossaryOptions.value = []
		return
	}

	try {
		const targetLang = (localCard.content as any)?.target_language
		const cards = await listGlossaries(projectStore.currentProject.id, targetLang)
		glossaryOptions.value = cards.map((c: any) => ({
			id: c.id,
			title: c.title || (c.content?.name) || '未命名术语表',
			content: c.content || {},
		}))

		// 自动选择与当前目标语言匹配的术语表
		if (selectedGlossaryId.value === null && glossaryOptions.value.length > 0) {
			// 优先选择当前语言的术语表
			const match = glossaryOptions.value.find(g => g.content.target_language === targetLang)
			if (match) {
				selectedGlossaryId.value = match.id
				selectedGlossary.value = match.content
			}
		}
	} catch (e) {
		console.error('Failed to load glossaries:', e)
		glossaryOptions.value = []
	}
}

function handleGlossaryChange(glossaryId: number | null) {
	if (!glossaryId) {
		selectedGlossary.value = null
		return
	}

	const glossary = glossaryOptions.value.find(g => g.id === glossaryId)
	selectedGlossary.value = glossary?.content || null
	isDirty.value = true
	emit('update:dirty', true)
}

function formatReviewVerdict(verdict?: QualityGate | null | string): string {
	switch (verdict) {
		case 'pass':
			return '基本通过'
		case 'block':
			return '高风险拦截'
		default:
			return '建议修改'
	}
}

function getReviewVerdictTagType(verdict?: QualityGate | null | string): 'success' | 'warning' | 'danger' {
	switch (verdict) {
		case 'pass':
			return 'success'
		case 'block':
			return 'danger'
		default:
			return 'warning'
	}
}

function setText(text: string) {
	if (!view) return
	view.dispatch({
		changes: { from: 0, to: view.state.doc.length, insert: text || '' }
	})
}

function getText(): string {
	return view?.state.doc.toString() || ''
}

// 高亮管理
const currentHighlight = ref<{ mode: 'single'; from: number; to: number } | { mode: 'compare' } | null>(null)

function clearHighlight() {
	if (!view) return
	currentHighlight.value = null
	view.dispatch({
		effects: setHighlightEffect.of(null)
	})
}

function updateHighlight(from: number, to: number) {
	if (!view) return
	if (from >= to) return
	currentHighlight.value = { mode: 'single', from, to }
	view.dispatch({
		effects: setHighlightEffect.of({ mode: 'single', from, to })
	})
}

function setCompareHighlight(originalFrom: number, originalTo: number, previewFrom: number, previewTo: number) {
	if (!view) return
	if (originalFrom >= originalTo || previewFrom >= previewTo) return
	currentHighlight.value = { mode: 'compare' }
	view.dispatch({
		effects: setHighlightEffect.of({
			mode: 'compare',
			originalFrom,
			originalTo,
			previewFrom,
			previewTo
		})
	})
}

function handleTitleBlur() {
	const newTitle = titleElement.value?.textContent?.trim()
	if (newTitle && newTitle !== localCard.title) {
		localCard.title = newTitle
		isDirty.value = true
	}
}

function handleTitleEnter() {
	titleElement.value?.blur()
}

async function handleSave(newTitle?: string) {
	try {
		// 优先使用传入的 newTitle（来自 titleProxy），确保保存用户输入的最新标题
		// 如果 newTitle 为空或无效，则从 localCard.content.title 获取（这是 v-model 绑定的值）
		const titleToSave = (typeof newTitle === 'string' && newTitle.trim())
			? newTitle.trim()
			: (localCard.content.title || localCard.title || props.card.title || '')

		// 更新 localCard.title 和 localCard.content.title
		if (titleToSave) {
			localCard.title = titleToSave
			localCard.content.title = titleToSave
		}

		const savedContent = {
			...((props.card.content as any) || {}),
			...localCard.content,
			content: getText(),
			word_count: wordCount.value,
			title: titleToSave,
			target_language: localCard.content.target_language,
		}

		const updatePayload: CardUpdate = {
			title: titleToSave,
			content: savedContent,
			needs_confirmation: false,
		}
		await cardStore.modifyCard(props.card.id, updatePayload)

		originalContent.value = getText()
		isDirty.value = false
		emit('update:dirty', false)
		return savedContent
	} catch (e) {
		console.error('Save failed:', e)
		ElMessage.error('保存失败')
		throw e
	}
}

function resolveLlmConfigId(): number | undefined {
	const p = perCardParams.value || editingParams.value
	return p?.llm_config_id
}

function resolvePromptName(): string | undefined {
	const p = perCardParams.value || editingParams.value
	return p?.prompt_name
}

function resolveSampling() {
	const src: any = perCardParams.value || editingParams.value || {}
	return { temperature: src.temperature, max_tokens: src.max_tokens, timeout: src.timeout }
}

// 翻译功能
// 根据目标语言选择对应的翻译 prompt
function getTranslationPromptName(targetLanguage: string | undefined): string {
	const promptMap: Record<string, string> = {
		'繁體中文': '正文翻译-繁體中文',  // 使用繁体，与术语表 target_language 一致
		'日文': '正文翻译-日文',
		'英文': '正文翻译-英文',
		'韓文': '正文翻译-韓文',  // 使用繁体，与术语表 target_language 一致
	}
	return promptMap[targetLanguage || ''] || '正文翻译'
}

// 从翻译结果中解析标题和正文
// 格式：第一行是标题，后面是正文
function parseTranslationResult(fullText: string): { title: string; body: string } {
	const lines = fullText.split('\n')
	// 找到第一个非空行作为标题
	let titleLineIndex = 0
	for (let i = 0; i < lines.length; i++) {
		const trimmed = lines[i].trim()
		if (trimmed) {
			titleLineIndex = i
			break
		}
	}
	const title = lines[titleLineIndex]?.trim() || ''
	// 去掉标题行和标题后的空行，剩下的作为正文
	const bodyLines = lines.slice(titleLineIndex + 1)
	// 跳过开头的空行
	let bodyStartIndex = 0
	for (let i = 0; i < bodyLines.length; i++) {
		if (bodyLines[i].trim()) {
			bodyStartIndex = i
			break
		}
	}
	const body = bodyLines.slice(bodyStartIndex).join('\n').trim()
	return { title, body }
}

async function executeTranslation() {
	const llmConfigId = resolveLlmConfigId()
	if (!llmConfigId) { ElMessage.error('请先设置有效的模型ID'); return }

	// 根据目标语言动态选择翻译 prompt
	const targetLanguage = (localCard.content as any)?.target_language
	const promptName = getTranslationPromptName(targetLanguage)

	aiLoading.value = true

	// 解析上下文（包含父系章节正文等）
	let resolvedContextTemplate = ''
	try {
		resolvedContextTemplate = getResolvedContext(generationContextKindValue.value, 'generation')
	} catch (e) {
		console.error('Failed to resolve context template:', e)
	}

	// 构建上下文信息
	const contextInfoBlock = resolvedContextTemplate
		? `【翻译上下文】\n${resolvedContextTemplate}`
		: ''

	const requestData: any = {
		context_info: contextInfoBlock,
		llm_config_id: llmConfigId,
		stream: true,
		prompt_name: promptName,
		project_id: projectStore.currentProject?.id || (props.card as any)?.project_id,
	}

	// 后端会根据 prompt_name 自动进行术语表匹配，无需前端发送 glossary

	const { temperature, max_tokens, timeout } = resolveSampling()
	if (typeof temperature === 'number') requestData.temperature = temperature
	if (typeof max_tokens === 'number') requestData.max_tokens = max_tokens
	if (typeof timeout === 'number') requestData.timeout = timeout

	if (view) {
		view.focus()
		const end = view.state.doc.length
		view.dispatch({ selection: { anchor: end } })
	}

	// 使用翻译专用的 executeAIGeneration，会自动处理标题提取
	executeTranslationAIGeneration(requestData)
}

// 翻译专用的 AI 生成，会自动提取标题并更新
function executeTranslationAIGeneration(requestData: any) {
	let accumulated = ''

	const onData = (chunk: string) => {
		if (!chunk) return
		let delta = chunk
		if (accumulated && chunk.startsWith(accumulated)) {
			delta = chunk.slice(accumulated.length)
		}
		if (delta) {
			const normalized = String(delta)
				.replace(/\r/g, '')
				.replace(/\n+/g, m => (m.length === 2 ? '\n' : m))

			appendAtEnd(normalized)
		}
		if (chunk.length > accumulated.length) accumulated = chunk
	}

	const onClose = () => {
		aiLoading.value = false
		streamHandle = null
		try {
			let text = getText() || ''
			text = text.replace(/\n+/g, m => (m.length === 2 ? '\n' : m))

			// 解析翻译结果，提取标题和正文
			const { title, body } = parseTranslationResult(text)

			// 更新标题
			if (title) {
				localCard.title = title
				localCard.content.title = title
				if (titleElement.value) {
					titleElement.value.textContent = title
				}
				isDirty.value = true
			}

			// 只保留正文内容（去掉标题）
			if (body) {
				setText(body)
				wordCount.value = computeWordCount(body)
				lineCount.value = computeLineCount(body)
			}
		} catch (e) {
			console.error('Failed to process translation result:', e)
		}
		ElMessage.success('翻译完成！')
	}

	const onError = (error: any) => {
		aiLoading.value = false
		streamHandle = null
		clearHighlight()
		console.error('翻译失败:', error)
		ElMessage.error('翻译失败')
	}

	streamHandle = generateContinuationStreaming(
		requestData as ContinuationRequest,
		onData,
		onClose,
		onError
	)
}

function appendAtEnd(text: string) {
	if (!view) return
	const end = view.state.doc.length
	view.dispatch({
		changes: { from: end, to: end, insert: text },
		selection: { anchor: end + text.length }
	})
	const currentText = view.state.doc.toString()
	wordCount.value = computeWordCount(currentText)
	lineCount.value = computeLineCount(currentText)
	isDirty.value = true
	emit('update:dirty', true)
}

function interruptStream() {
	try { reviewAbortController.value?.abort(); } catch {}
	try { streamHandle?.cancel(); } catch {}
	aiLoading.value = false
}

// 审核功能
async function executeReview() {
	const llmConfigId = resolveLlmConfigId()
	if (!llmConfigId) { ElMessage.error('请先设置有效的模型ID'); return }

	reviewLoading.value = true
	reviewAbortController.value = new AbortController()

	try {
		const chapterText = getText()
		const resolvedContext = getResolvedContext(reviewContextKindValue.value, 'review')

		const { temperature, max_tokens, timeout } = resolveSampling()

		const requestData = {
			card_id: props.card.id,
			title: localCard.title,
			project_id: projectStore.currentProject?.id || (props.card as any)?.project_id,
			chapter_text: chapterText,
			llm_config_id: llmConfigId,
			prompt_name: currentReviewPrompt.value,
			context_info: resolvedContext,
			temperature,
			max_tokens,
			timeout,
		}

		const result = await runReview(requestData, { signal: reviewAbortController.value.signal })
		reviewText.value = result.review_text || ''
		reviewDraft.value = result as unknown as ReviewDraftResult
		reviewDialogVisible.value = true
	} catch (e: any) {
		if (e?.name === 'CanceledError' || e?.message === 'canceled') {
			console.log('Review cancelled')
		} else {
			console.error('Review failed:', e)
			ElMessage.error('审核失败')
		}
	} finally {
		reviewLoading.value = false
		reviewAbortController.value = null
	}
}

function handleReviewPromptChange(promptName: string) {
	currentReviewPrompt.value = promptName
	ElMessage.success(`已切换审核提示词为: ${promptName}`)
}

// CodeMirror 初始化
function buildExtensions() {
	return [
		lineNumbers(),
		EditorView.lineWrapping,  // 自动换行
		history(),
		keymap.of([...defaultKeymap, ...historyKeymap]),
		highlightField,
		EditorView.updateListener.of((update) => {
			if (update.docChanged) {
				const text = update.state.doc.toString()
				wordCount.value = computeWordCount(text)
				lineCount.value = computeLineCount(text)
				if (text !== originalContent.value) {
					isDirty.value = true
					emit('update:dirty', true)
				}
			}
		}),
		EditorView.theme({
			'&': {
				height: '100%',
				fontSize: `${fontSize.value}px`,
			},
			'.cm-scroller': {
				overflow: 'auto',
				lineHeight: String(lineHeight.value),
			},
			'.cm-content': {
				caretColor: 'var(--el-color-primary)',
				fontFamily: 'var(--el-font-family)',
			},
			'.cm-line': {
				padding: '0 8px',
			},
			'&.cm-focused .cm-cursor': {
				borderLeftColor: 'var(--el-color-primary)',
			},
			'&.cm-focused .cm-selectionBackground, .cm-selectionBackground': {
				backgroundColor: 'var(--el-color-primary-light-5)',
			},
			'.cm-ai-highlight': {
				backgroundColor: 'rgba(64, 158, 255, 0.15)',
				borderRadius: '2px',
			},
			'.cm-ai-original-highlight': {
				backgroundColor: 'rgba(144, 147, 153, 0.2)',
				borderRadius: '2px',
			},
			'.cm-ai-preview-highlight': {
				backgroundColor: 'rgba(64, 158, 255, 0.15)',
				borderRadius: '2px',
			},
		}),
	]
}

onMounted(async () => {
	await nextTick()
	if (!cmRoot.value) return

	const initialText = typeof (props.card.content as any)?.content === 'string'
		? (props.card.content as any).content
		: ''

	originalContent.value = initialText
	wordCount.value = computeWordCount(initialText)
	lineCount.value = computeLineCount(initialText)

	const state = EditorState.create({
		doc: initialText,
		extensions: buildExtensions(),
	})

	view = new EditorView({
		state,
		parent: cmRoot.value,
	})

	// 加载审核提示词列表
	try {
		const config = await getAIConfigOptions()
		reviewPrompts.value = config.prompts
			.filter(p => p.description?.includes('审核') || p.name.includes('审核'))
			.map(p => p.name)
		if (!reviewPrompts.value.length) {
			reviewPrompts.value = ['章节审核']
		}
	} catch {
		reviewPrompts.value = ['章节审核']
	}

	// 加载术语表
	await loadGlossaries()

	ready.value = true
})

onUnmounted(() => {
	view?.destroy()
	view = null
})

// 监听外部内容变化
watch(() => props.card?.content, (newContent) => {
	if (!newContent || !view) return
	const newText = typeof (newContent as any)?.content === 'string'
		? (newContent as any).content
		: ''
	const currentText = getText()
	if (newText !== currentText && newText !== originalContent.value) {
		setText(newText)
		originalContent.value = newText
		isDirty.value = false
		emit('update:dirty', false)
		wordCount.value = computeWordCount(newText)
		lineCount.value = computeLineCount(newText)
	}
}, { deep: true })

defineExpose({
	handleSave,
})
</script>

<style scoped>
/* 最外层容器：固定高度，防止整体滚动 */
.chapter-studio {
	display: flex;
	flex-direction: column;
	height: 100%;
	min-height: 0;
	overflow: hidden; /* 关键：防止整体滚动 */
}

.toolbar {
	padding: 8px 8px; /* 灰色区域与内部白框上下左右间距保持一致 */
	border-bottom: 1px solid var(--el-border-color-light);
	background: var(--el-fill-color-lighter);
	display: flex;
	flex-direction: column;
	gap: 8px;
	flex-shrink: 0;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.toolbar-row {
	display: flex;
	align-items: center;
	gap: 12px;
	flex-wrap: nowrap;
	overflow-x: auto;
	overflow-y: hidden;
	scrollbar-width: thin;
}

.toolbar-status-row {
	display: flex;
	align-items: center;
	gap: 12px;
	min-width: 0;
}

.toolbar-status-spacer {
	flex: 1 1 auto;
	min-width: 0;
}

.toolbar-divider {
	width: 1px;
	height: 20px;
	background: var(--el-border-color-light);
	margin: 0 4px;
}

.toolbar-group {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 4px 10px;
	background: var(--el-fill-color-blank);
	border-radius: 6px;
	border: 1px solid var(--el-border-color-lighter);
}

.toolbar-group-ai {
	gap: 8px;
	flex: 0 0 auto;
	min-width: 0;
	padding: 8px 12px;
}

.group-label {
	font-size: 12px;
	color: var(--el-text-color-secondary);
	margin-right: 4px;
	font-weight: 500;
}

.flex-spacer {
	flex-grow: 1;
}

.ai-action-bar {
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: nowrap;
	flex: 0 0 auto;
}

.ai-config-entry {
	max-width: none;
	width: auto;
	margin-right: 0;
}

.ai-status-strip {
	display: flex;
	flex-wrap: nowrap;
	gap: 8px;
	flex: 0 0 auto;
	max-width: 100%;
	overflow-x: auto;
	overflow-y: hidden;
	scrollbar-width: none;
}

.ai-status-strip::-webkit-scrollbar {
	display: none;
}

.status-pill {
	display: inline-flex;
	align-items: center;
	padding: 4px 10px;
	border-radius: 999px;
	border: 1px solid var(--el-border-color-lighter);
	background: var(--el-fill-color-light);
	color: var(--el-text-color-secondary);
	font-size: 12px;
	line-height: 1.5;
	white-space: nowrap;
}

.target-lang-select {
	width: 120px;
}

.target-lang-select :deep(.el-input__wrapper) {
	background: var(--el-fill-color-light);
	border-radius: 999px;
	padding-left: 10px;
	padding-right: 10px;
}

.target-lang-select :deep(.el-input__inner) {
	font-size: 12px;
	color: var(--el-text-color-secondary);
}

.glossary-select {
	width: 160px;
}

.glossary-select :deep(.el-input__wrapper) {
	background: var(--el-fill-color-light);
	border-radius: 999px;
	padding-left: 10px;
	padding-right: 10px;
}

.glossary-select :deep(.el-input__inner) {
	font-size: 12px;
	color: var(--el-text-color-secondary);
}

.review-button-label {
	display: inline-flex;
	align-items: center;
	gap: 6px;
}

.review-loading-icon {
	animation: review-spin 1s linear infinite;
}

.prompt-settings-panel {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.prompt-settings-title {
	font-size: 13px;
	font-weight: 600;
	color: var(--el-text-color-primary);
}

.prompt-settings-item {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.prompt-settings-item label {
	font-size: 12px;
	color: var(--el-text-color-secondary);
}

.editor-content-wrapper {
	flex: 1;
	display: flex;
	flex-direction: column;
	min-height: 0; /* 允许flex子元素正确收缩 */
	overflow: hidden; /* 防止wrapper本身滚动 */
}

.chapter-header {
	padding: 16px 32px 14px;
	border-bottom: 1px solid var(--el-border-color-light);
	background: var(--el-fill-color-lighter);
	display: flex;
	align-items: center;
	flex-shrink: 0;
}

.title-section {
	flex: 1;
	display: flex;
	align-items: center;
	gap: 16px;
}

.chapter-title {
	margin: 0;
	font-size: 28px;
	font-weight: 600;
	color: var(--el-text-color-primary);
	line-height: 1.4;
	outline: none;
	padding: 6px 12px;
	border-radius: 6px;
	transition: all 0.2s ease;
	cursor: text;
	flex: 1;
	caret-color: var(--el-color-primary);
}

.chapter-title:hover {
	background-color: var(--el-fill-color-light);
}

.chapter-title:focus {
	background-color: var(--el-fill-color);
	box-shadow: 0 0 0 2px var(--el-color-primary-light-7);
}

.title-meta {
	display: flex;
	align-items: center;
	gap: 6px;
	color: var(--el-text-color-secondary);
	font-size: 14px;
	white-space: nowrap;
}

.word-count-icon {
	font-size: 16px;
}

.word-count-text {
	font-weight: 500;
}

.separator {
	margin: 0 8px;
	color: var(--el-text-color-disabled);
}

.line-count-text {
	font-weight: 500;
}

.editor-content {
	flex: 1 1 0; /* flex-basis为0，避免被内容撑开 */
	min-height: 0; /* 允许flex子元素正确收缩和滚动 */
	overflow: hidden;
	background-color: var(--el-bg-color);
	position: relative;
}

.ai-replace-review-bar {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 12px;
	padding: 8px 12px;
	border-top: 1px solid var(--el-border-color-light);
	background: var(--el-fill-color-lighter);
}

.review-hint {
	font-size: 12px;
	color: var(--el-text-color-secondary);
}

.review-actions {
	display: flex;
	gap: 8px;
}

.review-dialog-footer {
	display: flex;
	justify-content: flex-end;
	gap: 8px;
}

/* CodeMirror 内部样式 */
.editor-content :deep(.cm-editor) {
	height: 100% !important; /* 强制占满容器高度，不自动扩展 */
	outline: none;
	line-height: 1.8;
	color: var(--el-text-color-primary);
	background-color: transparent;
}

/* 确保 CodeMirror 的滚动容器正确工作 */
.editor-content :deep(.cm-scroller) {
	overflow-y: auto !important; /* 强制垂直滚动 */
	overflow-x: auto !important;
	max-height: 100% !important; /* 防止超出父容器 */
}
.editor-content :deep(.cm-content) {
	padding: 20px;
	color: var(--el-text-color-primary);
	font-size: v-bind(fontSizePx);
	line-height: v-bind(lineHeightStr);
	caret-color: var(--el-color-primary);
}

.editor-content :deep(.cm-line) {
	caret-color: inherit;
}

.editor-content :deep(.cm-gutters) {
	background: var(--el-fill-color-lighter);
	color: var(--el-text-color-secondary);
	border-right: 1px solid var(--el-border-color-light);
}

.editor-content :deep(.cm-lineNumbers .cm-gutterElement) {
	padding: 0 10px 0 8px;
	font-size: 12px;
}

.editor-content :deep(.cm-cursor),
.editor-content :deep(.cm-dropCursor) {
	border-left-color: var(--el-color-primary) !important;
}

.editor-content :deep(.cm-cursorLayer .cm-cursor) {
	border-left-width: 2px !important;
	box-shadow: 0 0 0 1px color-mix(in srgb, var(--el-color-primary) 38%, transparent);
}

.editor-content :deep(.cm-selectionBackground) {
	background: color-mix(in srgb, var(--el-color-primary) 20%, transparent) !important;
}

/* 取消高亮行背景，保证纯文本阅读观感 */
.editor-content :deep(.cm-activeLine) {
	background-color: transparent;
}

.review-dialog-body {
	display: flex;
	flex-direction: column;
	gap: 18px;
	max-height: 72vh;
	overflow: auto;
}

.review-overview {
	padding: 16px;
	border-radius: 10px;
	background: var(--el-fill-color-light);
	border: 1px solid var(--el-border-color-lighter);
}

.review-overview-main {
	display: flex;
	align-items: center;
	gap: 12px;
	margin-bottom: 10px;
}

.review-score {
	font-size: 14px;
	color: var(--el-text-color-secondary);
	font-weight: 600;
}

.review-summary {
	margin: 0;
	line-height: 1.7;
	color: var(--el-text-color-primary);
}

.review-text-block {
	padding: 16px;
	border-radius: 10px;
	border: 1px solid var(--el-border-color-lighter);
	background: var(--el-bg-color);
}

:deep(.review-markdown) {
	color: var(--el-text-color-primary);
	font-size: 14px;
	line-height: 1.8;
	word-break: break-word;
}

:deep(.review-markdown h1),
:deep(.review-markdown h2),
:deep(.review-markdown h3),
:deep(.review-markdown h4),
:deep(.review-markdown h5),
:deep(.review-markdown h6) {
	margin-top: 0;
	color: var(--el-text-color-primary);
}

:deep(.review-markdown p),
:deep(.review-markdown li),
:deep(.review-markdown blockquote) {
	color: var(--el-text-color-primary);
}

:deep(.review-markdown pre) {
	background: var(--el-fill-color-extra-light);
	border: 1px solid var(--el-border-color-lighter);
}

:deep(.review-markdown code) {
	background: var(--el-fill-color-light);
	color: var(--el-text-color-primary);
}

:deep(.chapter-ai-prompt-popper) {
	padding: 10px !important;
}

:deep(.review-prompt-dropdown .el-scrollbar__wrap) {
	max-height: 320px;
	overflow-y: auto;
}

@keyframes review-spin {
	from { transform: rotate(0deg); }
	to { transform: rotate(360deg); }
}

/* 自定义 AI 高亮效果 */
.editor-content :deep(.cm-ai-highlight) {
	background: linear-gradient(120deg,
		rgba(96, 165, 250, 0.2) 0%,
		rgba(129, 140, 248, 0.2) 50%,
		rgba(96, 165, 250, 0.2) 100%);
	background-size: 200% 100%;
	animation: highlightPulse 2s ease-in-out infinite;
	border-radius: 2px;
	padding: 2px 0;
	box-shadow: 0 0 0 1px rgba(96, 165, 250, 0.3);
}

.editor-content :deep(.cm-ai-original-highlight) {
	background: rgba(148, 163, 184, 0.18);
	color: rgba(100, 116, 139, 0.95);
	border-radius: 2px;
	padding: 2px 0;
	box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.3);
}

.editor-content :deep(.cm-ai-preview-highlight) {
	background: rgba(96, 165, 250, 0.18);
	color: rgba(37, 99, 235, 0.98);
	border-radius: 2px;
	padding: 2px 0;
	box-shadow: inset 0 0 0 1px rgba(96, 165, 250, 0.35);
}

@keyframes highlightPulse {
	0%, 100% {
		background-position: 0% 50%;
	}
	50% {
		background-position: 100% 50%;
	}
}

/* 暗色模式下的高亮 */
.dark .editor-content :deep(.cm-ai-highlight) {
	background: linear-gradient(120deg,
		rgba(59, 130, 246, 0.25) 0%,
		rgba(99, 102, 241, 0.25) 50%,
		rgba(59, 130, 246, 0.25) 100%);
	background-size: 200% 100%;
	box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.4);
}

.dark .editor-content :deep(.cm-ai-original-highlight) {
	background: rgba(100, 116, 139, 0.26);
	color: rgba(203, 213, 225, 0.95);
	box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.45);
}

.dark .editor-content :deep(.cm-ai-preview-highlight) {
	background: rgba(59, 130, 246, 0.24);
	color: rgba(147, 197, 253, 0.98);
	box-shadow: inset 0 0 0 1px rgba(96, 165, 250, 0.45);
}

.dark .chapter-title {
	caret-color: #93c5fd;
}

.dark .editor-content :deep(.cm-gutters) {
	background: color-mix(in srgb, var(--el-fill-color-darker) 86%, #0f172a);
	color: var(--el-text-color-secondary);
	border-right-color: var(--el-border-color);
}

.dark .editor-content :deep(.cm-selectionBackground) {
	background: rgba(59, 130, 246, 0.28) !important;
}

.dark .editor-content,
.dark .editor-content :deep(.cm-editor),
.dark .editor-content :deep(.cm-scroller) {
	background: #242b36 !important;
}

.dark .editor-content :deep(.cm-content),
.dark .editor-content :deep(.cm-line) {
	caret-color: #ffffff !important;
}

.dark .editor-content :deep(.cm-cursor),
.dark .editor-content :deep(.cm-dropCursor),
.dark .editor-content :deep(.cm-cursorLayer .cm-cursor) {
	border-left-color: #ffffff !important;
	border-left-width: 3px !important;
	box-shadow:
		0 0 0 1px rgba(255, 255, 255, 0.45),
		0 0 12px rgba(191, 219, 254, 0.58);
}
</style>
