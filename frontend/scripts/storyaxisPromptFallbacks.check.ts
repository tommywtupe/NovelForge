import * as assert from 'node:assert/strict'

import {
  getStoryAxisChapterEditorPromptDefaults,
  getStoryAxisGenerationPreset,
  getStoryAxisReviewPrompt,
} from '../src/renderer/src/services/storyaxisPromptFallbacks'

assert.deepEqual(getStoryAxisGenerationPreset('StoryAxis·章节正文'), {
  prompt_name: 'StoryAxis·内容生成',
  response_model_name: 'Chapter',
  temperature: 0.7,
  max_tokens: 8192,
  timeout: 60,
})

assert.equal(getStoryAxisReviewPrompt('StoryAxis·阶段大纲'), 'StoryAxis·阶段审核')

assert.deepEqual(getStoryAxisChapterEditorPromptDefaults('StoryAxis·章节正文'), {
  generation: 'StoryAxis·内容生成',
  polish: 'StoryAxis·润色',
  expand: 'StoryAxis·扩写',
  review: 'StoryAxis·章节审核',
})

assert.equal(getStoryAxisGenerationPreset('章节正文'), undefined)
assert.equal(getStoryAxisReviewPrompt('阶段大纲'), undefined)
assert.equal(getStoryAxisChapterEditorPromptDefaults('章节正文'), undefined)

console.log('storyaxis prompt fallbacks ok')
