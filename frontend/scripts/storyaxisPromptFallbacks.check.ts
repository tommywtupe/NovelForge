import * as assert from 'node:assert/strict'

import {
  getStoryAxisChapterContinuationTargetWordCount,
  getStoryAxisChapterEditorPromptDefaults,
  getStoryAxisGenerationPreset,
  getStoryAxisReviewPrompt,
  shouldStoryAxisUseExistingContentByDefault,
} from '../src/renderer/src/services/storyaxisPromptFallbacks.ts'

const storyaxisCardTypes = [
  'StoryAxis·金手指',
  'StoryAxis·一句话梗概',
  'StoryAxis·故事大纲',
  'StoryAxis·世界观设定',
  'StoryAxis·核心蓝图',
  'StoryAxis·分卷大纲',
  'StoryAxis·写作指南',
  'StoryAxis·阶段大纲',
  'StoryAxis·章节大纲',
  'StoryAxis·章节正文',
  'StoryAxis·角色卡',
  'StoryAxis·场景卡',
  'StoryAxis·组织卡',
  'StoryAxis·正文翻译卡',
] as const

assert.deepEqual(getStoryAxisGenerationPreset('StoryAxis·章节正文'), {
  prompt_name: 'StoryAxis·内容生成',
  response_model_name: 'Chapter',
  temperature: 0.7,
  max_tokens: 200193,
  timeout: 600,
})

for (const typeName of storyaxisCardTypes) {
  const preset = getStoryAxisGenerationPreset(typeName)
  assert.ok(preset, `${typeName} should expose a StoryAxis preset`)
  assert.equal(preset.max_tokens, 200193, `${typeName} should use the StoryAxis max token limit`)
  assert.equal(preset.timeout, 600, `${typeName} should use the StoryAxis timeout`)
}

assert.equal(getStoryAxisReviewPrompt('StoryAxis·阶段大纲'), 'StoryAxis·阶段审核')

assert.deepEqual(getStoryAxisChapterEditorPromptDefaults('StoryAxis·章节正文'), {
  generation: 'StoryAxis·内容生成',
  polish: 'StoryAxis·润色',
  expand: 'StoryAxis·扩写',
  review: 'StoryAxis·章节审核',
})

assert.equal(shouldStoryAxisUseExistingContentByDefault('StoryAxis·章节大纲'), true)
assert.equal(shouldStoryAxisUseExistingContentByDefault('章节大纲'), false)
assert.equal(getStoryAxisChapterContinuationTargetWordCount('StoryAxis·章节正文'), 4000)
assert.equal(getStoryAxisChapterContinuationTargetWordCount('章节正文'), undefined)

assert.equal(getStoryAxisGenerationPreset('章节正文'), undefined)
assert.equal(getStoryAxisReviewPrompt('阶段大纲'), undefined)
assert.equal(getStoryAxisChapterEditorPromptDefaults('章节正文'), undefined)

console.log('storyaxis prompt fallbacks ok')
