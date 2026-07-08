<template>
  <div class="glossary-editor">
    <div class="toolbar">
      <div class="toolbar-row">
        <div class="toolbar-group">
          <el-select
            v-model="localContent.target_language"
            size="small"
            class="lang-select"
            @change="handleTargetLanguageChange"
          >
            <el-option v-for="lang in targetLanguageOptions" :key="lang" :label="lang" :value="lang" />
          </el-select>
          <el-button size="small" @click="openAddTermDialog">
            <el-icon><Plus /></el-icon>
            添加术语
          </el-button>
        </div>
        <div class="toolbar-group toolbar-group-right">
          <AIPerCardParams :card-id="props.card.id" :card-type-name="props.card.card_type?.name" />
          <el-dropdown @command="handleUpdateMode">
            <el-button type="primary" size="small" :loading="updateLoading">
              <el-icon><Refresh /></el-icon>
              术语同步
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="scan_new_concepts">仅扫描新术语</el-dropdown-item>
                <el-dropdown-item command="translate_new_concepts">仅补全待翻译术语</el-dropdown-item>
                <el-dropdown-item command="scan_and_translate">扫描并补全翻译</el-dropdown-item>
                <el-dropdown-item command="full_rebuild_translations">全量重建译名</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
      <div class="toolbar-meta">
        <span>术语数 {{ localContent.terms.length }}</span>
        <span>待翻译 {{ pendingTermCount }}</span>
        <span v-if="lastSyncSummary">{{ lastSyncSummary }}</span>
      </div>
    </div>

    <div class="table-shell">
      <el-table :data="localContent.terms" size="small" border height="100%">
        <el-table-column label="分类" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="categoryTagType(row.category)">
              {{ categoryLabel(row.category) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="原文" min-width="180" />
        <el-table-column label="译名" min-width="200">
          <template #default="{ row }">
            <el-input v-model="row.translated" size="small" placeholder="输入译名" @input="markDirty" />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="180">
          <template #default="{ row }">
            <el-input v-model="row.notes" size="small" placeholder="可选备注" @input="markDirty" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="72" fixed="right">
          <template #default="{ $index }">
            <el-button link type="danger" @click="removeTerm($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="addTermDialogVisible" title="添加术语" width="420px">
      <el-form label-position="top">
        <el-form-item label="原文">
          <el-input v-model="draftTerm.source" />
        </el-form-item>
        <el-form-item label="译名">
          <el-input v-model="draftTerm.translated" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="draftTerm.category">
            <el-option v-for="option in categoryOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="draftTerm.notes" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addTermDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAddTerm">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'

import type { CardRead } from '@renderer/api/cards'
import { getAIConfigOptions } from '@renderer/api/ai'
import type {
  GlossaryCategory,
  GlossaryTerm,
  TargetLanguage,
  TranslationGlossaryContent,
  UpdateMode,
} from '@renderer/api/glossary'
import { extractAndUpdateGlossary } from '@renderer/api/glossary'
import { getCardAIParams } from '@renderer/api/setting'
import { useCardStore } from '@renderer/stores/useCardStore'
import { useProjectStore } from '@renderer/stores/useProjectStore'
import AIPerCardParams from '../common/AIPerCardParams.vue'

const props = defineProps<{
  card: CardRead
}>()

const emit = defineEmits<{
  (e: 'update:dirty', value: boolean): void
}>()

const cardStore = useCardStore()
const projectStore = useProjectStore()

const targetLanguageOptions: TargetLanguage[] = ['繁體中文', '日文', '英文', '韓文']

const categoryOptions: Array<{ value: GlossaryCategory; label: string }> = [
  { value: 'character', label: '角色' },
  { value: 'scene', label: '场景' },
  { value: 'organization', label: '组织' },
  { value: 'item', label: '物品' },
  { value: 'concept', label: '概念' },
  { value: 'other', label: '其他' },
]

const localContent = reactive<TranslationGlossaryContent>({
  name: '',
  target_language: '繁體中文',
  terms: [],
  updated_at: null,
})

const draftTerm = reactive<GlossaryTerm>({
  source: '',
  translated: '',
  category: 'other',
  source_card_id: null,
  notes: '',
})

const addTermDialogVisible = ref(false)
const updateLoading = ref(false)
const isDirty = ref(false)
const lastSyncSummary = ref('')
const lastSavedSignature = ref('')

const pendingTermCount = computed(() => localContent.terms.filter(term => !String(term.translated || '').trim()).length)

function normalizeContent(card: CardRead): TranslationGlossaryContent {
  const content = (card.content || {}) as Partial<TranslationGlossaryContent>
  return {
    name: String(content.name || card.title || ''),
    target_language: (content.target_language as TargetLanguage) || '繁體中文',
    terms: Array.isArray(content.terms)
      ? content.terms.map(term => ({
        source: String(term.source || ''),
        translated: String(term.translated || ''),
        category: (term.category as GlossaryCategory) || 'other',
        source_card_id: typeof term.source_card_id === 'number' ? term.source_card_id : null,
        notes: term.notes ? String(term.notes) : '',
      }))
      : [],
    updated_at: content.updated_at ? String(content.updated_at) : null,
  }
}

function contentSignature(content: TranslationGlossaryContent): string {
  return JSON.stringify(content)
}

function syncFromCard(card: CardRead) {
  const normalized = normalizeContent(card)
  localContent.name = normalized.name
  localContent.target_language = normalized.target_language
  localContent.terms = normalized.terms
  localContent.updated_at = normalized.updated_at
  lastSavedSignature.value = contentSignature(normalized)
  isDirty.value = false
  emit('update:dirty', false)
}

watch(
  () => props.card,
  (card) => {
    if (card) {
      syncFromCard(card)
    }
  },
  { immediate: true, deep: true }
)

function markDirty() {
  const dirty = contentSignature(localContent) !== lastSavedSignature.value
  isDirty.value = dirty
  emit('update:dirty', dirty)
}

function handleTargetLanguageChange() {
  markDirty()
}

function openAddTermDialog() {
  draftTerm.source = ''
  draftTerm.translated = ''
  draftTerm.category = 'other'
  draftTerm.source_card_id = null
  draftTerm.notes = ''
  addTermDialogVisible.value = true
}

function confirmAddTerm() {
  const source = draftTerm.source.trim()
  if (!source) {
    ElMessage.warning('请输入原文术语')
    return
  }
  localContent.terms.push({
    source,
    translated: draftTerm.translated.trim(),
    category: draftTerm.category,
    source_card_id: null,
    notes: draftTerm.notes?.trim() || '',
  })
  addTermDialogVisible.value = false
  markDirty()
}

function removeTerm(index: number) {
  localContent.terms.splice(index, 1)
  markDirty()
}

function categoryLabel(category: GlossaryCategory): string {
  return categoryOptions.find(option => option.value === category)?.label || '其他'
}

function categoryTagType(category: GlossaryCategory): 'success' | 'warning' | 'danger' | 'info' | '' {
  switch (category) {
    case 'character':
      return ''
    case 'scene':
      return 'success'
    case 'organization':
      return 'warning'
    case 'concept':
      return 'danger'
    default:
      return 'info'
  }
}

async function resolveLlmConfigId(): Promise<number | undefined> {
  try {
    const paramsResponse = await getCardAIParams(props.card.id)
    const effective = (paramsResponse as any)?.effective_params || {}
    if (typeof effective.llm_config_id === 'number') {
      return effective.llm_config_id
    }
  } catch {
    // ignore and fallback to first option
  }

  const options = await getAIConfigOptions()
  return options.llm_configs[0]?.id
}

async function handleUpdateMode(command: string) {
  const mode = command as UpdateMode
  const projectId = projectStore.currentProject?.id || props.card.project_id
  if (!projectId) {
    ElMessage.error('缺少项目上下文，无法同步术语表')
    return
  }

  if (isDirty.value) {
    await handleSave()
  }

  updateLoading.value = true
  try {
    const llmConfigId = mode === 'scan_new_concepts' ? undefined : await resolveLlmConfigId()
    const result = await extractAndUpdateGlossary({
      project_id: projectId,
      glossary_card_id: props.card.id,
      target_language: localContent.target_language,
      llm_config_id: llmConfigId,
      update_mode: mode,
    })
    lastSyncSummary.value = `新增 ${result.new_terms_count} / 更新 ${result.updated_terms_count} / 移除 ${result.removed_terms_count}`
    await cardStore.fetchCards(projectId)
    ElMessage.success('术语表已同步')
  } catch (error) {
    console.error('Failed to update glossary:', error)
    ElMessage.error('术语表同步失败')
  } finally {
    updateLoading.value = false
  }
}

async function handleSave(nextTitle?: string) {
  const title = (nextTitle || localContent.name || props.card.title).trim()
  const payload: TranslationGlossaryContent = {
    name: title,
    target_language: localContent.target_language,
    terms: localContent.terms.map(term => ({
      source: term.source.trim(),
      translated: term.translated.trim(),
      category: term.category,
      source_card_id: term.source_card_id ?? null,
      notes: term.notes?.trim() || '',
    })),
    updated_at: new Date().toISOString(),
  }

  await cardStore.modifyCard(props.card.id, {
    title,
    content: payload,
  } as any)

  lastSavedSignature.value = contentSignature(payload)
  isDirty.value = false
  emit('update:dirty', false)
  return payload
}

defineExpose({
  handleSave,
})
</script>

<style scoped>
.glossary-editor {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--el-bg-color);
}

.toolbar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-light);
  background: var(--el-fill-color-extra-light);
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
  gap: 16px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.lang-select {
  width: 140px;
}

.table-shell {
  flex: 1;
  min-height: 0;
  padding: 12px;
}
</style>
