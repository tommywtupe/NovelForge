export interface StoryAxisPromptPreset {
  prompt_name: string
  response_model_name?: string
  llm_config_id?: number
  temperature?: number
  max_tokens?: number
  timeout?: number
}

export interface StoryAxisChapterEditorPromptDefaults {
  generation: string
  polish: string
  expand: string
  review: string
}

export const STORYAXIS_MAX_TOKENS = 200193
export const STORYAXIS_TIMEOUT_SECONDS = 600

function withStoryAxisSampling(preset: Omit<StoryAxisPromptPreset, 'max_tokens' | 'timeout'>): StoryAxisPromptPreset {
  return {
    ...preset,
    max_tokens: STORYAXIS_MAX_TOKENS,
    timeout: STORYAXIS_TIMEOUT_SECONDS,
  }
}

const STORYAXIS_GENERATION_PRESETS: Record<string, StoryAxisPromptPreset> = {
  'StoryAxis·金手指': withStoryAxisSampling({ prompt_name: 'StoryAxis·金手指生成', response_model_name: 'SpecialAbilityResponse', temperature: 0.6 }),
  'StoryAxis·一句话梗概': withStoryAxisSampling({ prompt_name: 'StoryAxis·一句话梗概', response_model_name: 'OneSentence', temperature: 0.6 }),
  'StoryAxis·故事大纲': withStoryAxisSampling({ prompt_name: 'StoryAxis·一段话大纲', response_model_name: 'ParagraphOverview', temperature: 0.6 }),
  'StoryAxis·世界观设定': withStoryAxisSampling({ prompt_name: 'StoryAxis·世界观设定', response_model_name: 'WorldBuilding', temperature: 0.6 }),
  'StoryAxis·核心蓝图': withStoryAxisSampling({ prompt_name: 'StoryAxis·核心蓝图', response_model_name: 'Blueprint', temperature: 0.6 }),
  'StoryAxis·分卷大纲': withStoryAxisSampling({ prompt_name: 'StoryAxis·分卷大纲', response_model_name: 'VolumeOutline', temperature: 0.6 }),
  'StoryAxis·阶段大纲': withStoryAxisSampling({ prompt_name: 'StoryAxis·阶段大纲', response_model_name: 'StageLine', temperature: 0.6 }),
  'StoryAxis·章节大纲': withStoryAxisSampling({ prompt_name: 'StoryAxis·章节大纲', response_model_name: 'ChapterOutline', temperature: 0.6 }),
  'StoryAxis·写作指南': withStoryAxisSampling({ prompt_name: 'StoryAxis·写作指南', response_model_name: 'WritingGuide', temperature: 0.7 }),
  'StoryAxis·章节正文': withStoryAxisSampling({ prompt_name: 'StoryAxis·内容生成', response_model_name: 'Chapter', temperature: 0.7 }),
  'StoryAxis·角色卡': withStoryAxisSampling({ prompt_name: 'StoryAxis·角色动态信息提取', response_model_name: 'CharacterCard', temperature: 0.6 }),
  'StoryAxis·场景卡': withStoryAxisSampling({ prompt_name: 'StoryAxis·内容生成', response_model_name: 'SceneCard', temperature: 0.6 }),
  'StoryAxis·组织卡': withStoryAxisSampling({ prompt_name: 'StoryAxis·关系提取', response_model_name: 'OrganizationCard', temperature: 0.6 }),
  'StoryAxis·正文翻译卡': withStoryAxisSampling({ prompt_name: 'StoryAxis·正文翻译', response_model_name: 'TranslationChapter', temperature: 0.3 }),
}

const STORYAXIS_REVIEW_PROMPTS: Record<string, string> = {
  'StoryAxis·阶段大纲': 'StoryAxis·阶段审核',
}

const STORYAXIS_CHAPTER_EDITOR_PROMPTS: Record<string, StoryAxisChapterEditorPromptDefaults> = {
  'StoryAxis·章节正文': {
    generation: 'StoryAxis·内容生成',
    polish: 'StoryAxis·润色',
    expand: 'StoryAxis·扩写',
    review: 'StoryAxis·章节审核',
  },
}

export function getStoryAxisGenerationPreset(typeName?: string): StoryAxisPromptPreset | undefined {
  if (!typeName) return undefined
  const preset = STORYAXIS_GENERATION_PRESETS[typeName]
  return preset ? { ...preset } : undefined
}

export function getStoryAxisReviewPrompt(cardTypeName?: string | null): string | undefined {
  if (!cardTypeName) return undefined
  return STORYAXIS_REVIEW_PROMPTS[cardTypeName]
}

export function getStoryAxisChapterEditorPromptDefaults(
  cardTypeName?: string | null
): StoryAxisChapterEditorPromptDefaults | undefined {
  if (!cardTypeName) return undefined
  const defaults = STORYAXIS_CHAPTER_EDITOR_PROMPTS[cardTypeName]
  return defaults ? { ...defaults } : undefined
}
