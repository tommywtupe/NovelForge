<template>
  <el-card shadow="never" class="object-field-card">
    <template #header>
      <div class="card-header">
        <span>{{ label }}</span>
      </div>
    </template>
    <ModelDrivenForm
      :schema="effectiveSchema"
      :modelValue="modelValue || {}"
      @update:modelValue="emit('update:modelValue', $event)"
    />
  </el-card>
</template>

<script setup lang="ts">
import { defineAsyncComponent, computed } from 'vue'
import type { JSONSchema } from '@renderer/api/schema'

// 使用前向声明来处理递归组件。
// 这在模块级别打破了循环依赖。
const ModelDrivenForm = defineAsyncComponent(() => import('../ModelDrivenForm.vue'))

const props = defineProps<{
  modelValue: Record<string, any> | undefined
  label: string
  schema: JSONSchema
}>()

const emit = defineEmits(['update:modelValue'])

// 当 schema 未声明 properties 但数据存在时，按数据键名动态补齐，保证可渲染
const effectiveSchema = computed<JSONSchema>(() => {
  const sch = props.schema || { type: 'object' }
  const hasProps = sch && typeof sch === 'object' && (sch as any).properties && Object.keys((sch as any).properties as any).length > 0
  if (hasProps) return sch
  const dataKeys = Object.keys(props.modelValue || {})
  const itemSchema: JSONSchema = {
    type: 'object',
    title: 'Item',
    properties: {
      id: { type: 'integer', title: 'id' },
      info: { type: 'string', title: '信息' },
      chapter: { type: 'integer', title: '章节' },
    },
  }
  const propsMap: Record<string, JSONSchema> = {}

  // 始终包含所有动态信息类型，即使当前没有数据
  const allDynamicInfoTypes = [
    '系统/模拟器/金手指信息',
    '等级/修为境界',
    '装备/法宝',
    '知识/情报',
    '资产/领地',
    '功法/技能',
    '血脉/体质',
    '心理想法/目标快照',
  ]
  for (const k of allDynamicInfoTypes) {
    propsMap[k] = { type: 'array', items: itemSchema, title: k }
  }
  // 额外添加数据中存在但不在列表中的键
  for (const k of dataKeys) {
    if (!propsMap[k]) {
      propsMap[k] = { type: 'array', items: itemSchema, title: k }
    }
  }
  return { ...sch, type: 'object', properties: propsMap }
})
</script>

<style scoped>
.object-field-card {
  margin-top: 10px;
  margin-bottom: 20px;
  background-color: var(--el-fill-color-lighter);
}
</style> 