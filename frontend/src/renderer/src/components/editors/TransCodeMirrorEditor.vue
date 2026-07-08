<template>
  <div class="translation-editor">
    <div class="toolbar">
      <div class="toolbar-row">
        <div class="toolbar-group">
          <el-button type="primary" size="small" :loading="aiLoading" @click="executeTranslation">
            <el-icon><MagicStick /></el-icon>
            生成译文
          </el-button>
          <el-button plain size="small" :disabled="!aiLoading" @click="interruptStream">
            中断
          </el-button>
        </div>
        <div class="toolbar-group toolbar-group-right">
          <AIPerCardParams :card-id="props.card.id" :card-type-name="props.card.card_type?.name" />
        </div>
      </div>
      <div class="toolbar-row">
        <div class="toolbar-group">
          <el-select v-model="localContent.target_language" size="small" class="lang-select" @change="handleTargetLanguageChange">
            <el-option v-for="lang in targetLanguageOptions" :key="lang" :label="lang" :value="lang" />
          </el-select>
          <el-select
            v-model="selectedGlossaryId"
            size="small"
            class="glossary-select"
            clearable
            filterable
            placeholder="选择术语表"
          >
            <el-option
              v-for="glossary in glossaryOptions"
              :key="glossary.id"
              :label="glossary.title"
              :value="glossary.id"
            />
          </el-select>
        </div>
        <div class="toolbar-meta">
          <span>原文字数 {{ sourceWordCount }}</span>
          <span>译文字数 {{ translatedWordCount }}</span>
          <span v-if="selectedGlossaryName">术语表 {{ selectedGlossaryName }}</span>
        </div>
      </div>
    </div>

    <div ref="editorRoot" class="editor-root"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'
import { EditorState } from '@codemirror/state'
import { EditorView, keymap, lineNumbers } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands'

import { generateContinuationStreaming, getAIConfigOptions, type ContinuationRequestExtended } from '@renderer/api/ai'
import type { CardRead } from '@renderer/api/cards'
import type { GlossaryCard, GlossaryTerm, TargetLanguage } from '@renderer/api/glossary'
import { listGlossaries } from '@renderer/api/glossary'
import { getCardAIParams } from '@renderer/api/setting'
import { useCardStore } from '@renderer/stores/useCardStore'
import { useProjectStore } from '@renderer/stores/useProjectStore'
import { resolveTemplate } from '@renderer/services/contextResolver'
import {
  getCardContextTemplates,
  getContextTemplateByKind,
  normalizeContextTemplateKind,
  type ContextTemplateKind,
  type ContextTemplates,
} from '@renderer/services/contextSlots'
import AIPerCardParams from '../common/AIPerCardParams.vue'

const props = defineProps<{
  card: CardRead
  prefetched?: any | null
  contextTemplates?: ContextTemplates
  generationContextKind?: ContextTemplateKind
}>()

const emit = defineEmits<{
  (e: 'update:dirty', value: boolean): void
}>()

const projectStore = useProjectStore()
const cardStore = useCardStore()

const targetLanguageOptions: TargetLanguage[] = ['繁體中文', '日文', '英文', '韓文']

const editorRoot = ref<HTMLElement | null>(null)
let view: EditorView | null = null
let streamHandle: { cancel: () => void } | null = null

const aiLoading = ref(false)
const isDirty = ref(false)
const selectedGlossaryId = ref<number | null>(null)
const glossaryOptions = ref<GlossaryCard[]>([])
const originalText = ref('')

const localContent = reactive({
  content: '',
  target_language: '繁體中文' as TargetLanguage,
  glossary_card_id: null as number | null,
})

const sourceCard = computed(() => {
  return cardStore.cards.find(card => card.id === props.card.parent_id) || null
})

const sourceText = computed(() => {
  return String((sourceCard.value?.content as any)?.content || '')
})

const sourceWordCount = computed(() => computeWordCount(sourceText.value))
const translatedWordCount = computed(() => computeWordCount(getText()))
const selectedGlossary = computed(() => glossaryOptions.value.find(card => card.id === selectedGlossaryId.value) || null)
const selectedGlossaryName = computed(() => selectedGlossary.value?.title || '')

function computeWordCount(text: string): number {
  return String(text || '').replace(/\s+/g, '').length
}

function getText(): string {
  return view ? view.state.doc.toString() : localContent.content
}

function setText(text: string) {
  if (!view) return
  view.dispatch({
    changes: { from: 0, to: view.state.doc.length, insert: text || '' },
  })
}

function appendText(delta: string) {
  if (!view || !delta) return
  const end = view.state.doc.length
  view.dispatch({
    changes: { from: end, to: end, insert: delta },
    selection: { anchor: end + delta.length },
  })
}

function syncFromCard(card: CardRead) {
  const content = (card.content || {}) as Record<string, any>
  localContent.content = typeof content.content === 'string' ? content.content : ''
  localContent.target_language = (content.target_language as TargetLanguage) || '繁體中文'
  localContent.glossary_card_id = typeof content.glossary_card_id === 'number' ? content.glossary_card_id : null
  selectedGlossaryId.value = localContent.glossary_card_id
  originalText.value = localContent.content
  isDirty.value = false
  emit('update:dirty', false)
  if (view) {
    setText(localContent.content)
  }
}

watch(
  () => props.card,
  card => {
    if (card) {
      syncFromCard(card)
      void loadGlossaryOptions()
    }
  },
  { immediate: true, deep: true }
)

watch(selectedGlossaryId, (value) => {
  localContent.glossary_card_id = value
  markDirty()
})

function markDirty() {
  const dirty = (
    getText() !== originalText.value
    || selectedGlossaryId.value !== (typeof (props.card.content as any)?.glossary_card_id === 'number'
      ? (props.card.content as any).glossary_card_id
      : null)
    || localContent.target_language !== (((props.card.content as any)?.target_language as TargetLanguage) || '繁體中文')
  )
  isDirty.value = dirty
  emit('update:dirty', dirty)
}

function initEditor() {
  if (!editorRoot.value) return
  view = new EditorView({
    parent: editorRoot.value,
    state: EditorState.create({
      doc: localContent.content,
      extensions: [
        history(),
        keymap.of([
          {
            key: 'Mod-s',
            run: () => {
              void handleSave()
              return true
            },
          },
          ...defaultKeymap,
          ...historyKeymap,
        ]),
        lineNumbers(),
        EditorView.lineWrapping,
        EditorView.theme({
          '&': { height: '100%' },
          '.cm-scroller': { overflow: 'auto' },
        }),
        EditorView.updateListener.of((update) => {
          if (!update.docChanged) return
          localContent.content = update.state.doc.toString()
          markDirty()
        }),
      ],
    }),
  })
}

onMounted(async () => {
  await nextTick()
  initEditor()
  await loadGlossaryOptions()
})

onBeforeUnmount(() => {
  interruptStream()
  view?.destroy()
  view = null
})

async function loadGlossaryOptions() {
  const projectId = projectStore.currentProject?.id || props.card.project_id
  if (!projectId) {
    glossaryOptions.value = []
    return
  }
  try {
    glossaryOptions.value = await listGlossaries(projectId, localContent.target_language)
    if (!selectedGlossaryId.value) {
      selectedGlossaryId.value = glossaryOptions.value[0]?.id || null
    } else if (!glossaryOptions.value.some(card => card.id === selectedGlossaryId.value)) {
      selectedGlossaryId.value = glossaryOptions.value[0]?.id || null
    }
  } catch (error) {
    console.error('Failed to load glossary cards:', error)
    glossaryOptions.value = []
  }
}

function handleTargetLanguageChange() {
  selectedGlossaryId.value = null
  void loadGlossaryOptions()
  markDirty()
}

function resolveGenerationContext(): string {
  const kind = normalizeContextTemplateKind(props.generationContextKind, 'generation')
  const template = getContextTemplateByKind(
    props.card,
    props.contextTemplates || getCardContextTemplates(props.card),
    kind,
    'generation'
  )
  if (!template) return ''
  const currentCard = {
    ...props.card,
    content: {
      ...(props.card.content as any || {}),
      ...localContent,
    },
  }
  return resolveTemplate({
    template,
    cards: cardStore.cards,
    currentCard: currentCard as any,
  })
}

function buildGlossaryContext(terms: GlossaryTerm[], source: string): string {
  if (!terms.length) return ''
  return terms
    .filter(term => term.translated && (!source || source.includes(term.source)))
    .sort((a, b) => b.source.length - a.source.length)
    .map(term => {
      const note = term.notes ? ` #${term.notes}` : ''
      return `${term.source} -> ${term.translated}${note}`
    })
    .join('\n')
}

async function resolveAiSettings() {
  let effective: Record<string, any> = {}
  try {
    const response = await getCardAIParams(props.card.id)
    effective = (response as any)?.effective_params || {}
  } catch {
    effective = {}
  }
  if (typeof effective.llm_config_id !== 'number') {
    const options = await getAIConfigOptions()
    effective.llm_config_id = options.llm_configs[0]?.id
  }
  return effective
}

async function executeTranslation() {
  const aiSettings = await resolveAiSettings()
  if (typeof aiSettings.llm_config_id !== 'number') {
    ElMessage.error('请先配置可用模型')
    return
  }

  const resolvedContext = resolveGenerationContext()
  const glossaryContext = selectedGlossary.value
    ? buildGlossaryContext(selectedGlossary.value.content?.terms || [], sourceText.value)
    : ''

  const contextParts: string[] = [
    `【翻译任务】\n目标语言：${localContent.target_language}`,
  ]
  if (glossaryContext) {
    contextParts.push(`【术语约束】\n${glossaryContext}`)
  }
  if (resolvedContext.trim()) {
    contextParts.push(`【引用上下文】\n${resolvedContext}`)
  }

  const requestData: ContinuationRequestExtended = {
    previous_content: '',
    context_info: contextParts.join('\n\n'),
    llm_config_id: aiSettings.llm_config_id,
    stream: true,
    project_id: projectStore.currentProject?.id || props.card.project_id,
    prompt_name: String(aiSettings.prompt_name || 'StoryAxis·正文翻译'),
    append_continuous_novel_directive: false,
    temperature: typeof aiSettings.temperature === 'number' ? aiSettings.temperature : undefined,
    max_tokens: typeof aiSettings.max_tokens === 'number' ? aiSettings.max_tokens : undefined,
    timeout: typeof aiSettings.timeout === 'number' ? aiSettings.timeout : undefined,
  }

  aiLoading.value = true
  setText('')
  streamHandle = generateContinuationStreaming(
    requestData,
    (chunk) => {
      appendText(String(chunk || ''))
    },
    () => {
      aiLoading.value = false
      localContent.content = getText()
      markDirty()
      ElMessage.success('译文生成完成')
    },
    (error) => {
      console.error('Translation generation failed:', error)
      aiLoading.value = false
      ElMessage.error('译文生成失败')
    }
  )
}

function interruptStream() {
  if (!streamHandle) return
  streamHandle.cancel()
  streamHandle = null
  aiLoading.value = false
}

async function handleSave(nextTitle?: string) {
  const title = (nextTitle || props.card.title).trim() || props.card.title
  const payload = {
    ...(props.card.content as any || {}),
    title,
    content: getText(),
    target_language: localContent.target_language,
    glossary_card_id: selectedGlossaryId.value,
  }

  await cardStore.modifyCard(props.card.id, {
    title,
    content: payload,
    needs_confirmation: false,
  } as any)

  originalText.value = payload.content
  isDirty.value = false
  emit('update:dirty', false)
  return payload
}

defineExpose({
  handleSave,
})
</script>

<style scoped>
.translation-editor {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--el-bg-color);
}

.toolbar {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-light);
  background: linear-gradient(180deg, var(--el-fill-color-extra-light), var(--el-bg-color));
}

.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-group-right {
  justify-content: flex-end;
}

.toolbar-meta {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.lang-select {
  width: 140px;
}

.glossary-select {
  width: 220px;
}

.editor-root {
  flex: 1;
  min-height: 0;
}
</style>
