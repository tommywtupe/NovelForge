import request from './request'

export type GlossaryTerm = {
  source: string
  translated: string
  category: 'character' | 'scene' | 'organization' | 'item' | 'concept' | 'other'
  source_card_id: number | null
  notes?: string
}

export type TranslationGlossaryContent = {
  name: string
  target_language: '繁體中文' | '日文' | '英文' | '韓文'
  terms: GlossaryTerm[]
  updated_at?: string
}

export type UpdateMode =
  | 'scan_new_concepts'      // 仅检测新概念
  | 'translate_new_concepts'  // 仅为新概念更新翻译
  | 'full_rebuild_translations'  // 全量重建翻译
  | 'scan_and_translate'     // 同时检测新概念和自动完成后续翻译

export interface GlossaryTermExtractionRequest {
  project_id: number
  target_language: '繁體中文' | '日文' | '英文' | '韓文'
  glossary_card_id?: number
  llm_config_id?: number
  update_mode: UpdateMode
}

export interface GlossaryTermExtractionResponse {
  terms: GlossaryTerm[]
  new_terms_count: number
  updated_terms_count: number
  removed_terms_count: number
  glossary_card_id: number
}

/** 获取项目的术语表列表 */
export async function listGlossaries(
  projectId: number,
  targetLanguage?: string
): Promise<any[]> {
  const params = new URLSearchParams({ project_id: String(projectId) })
  if (targetLanguage) {
    params.set('target_language', targetLanguage)
  }
  return request.get<any[]>(`/glossary/list?${params.toString()}`)
}

/** 提取并更新术语表 */
export async function extractAndUpdateGlossary(
  extractionRequest: GlossaryTermExtractionRequest
): Promise<GlossaryTermExtractionResponse> {
  return request.post<GlossaryTermExtractionResponse>('/glossary/extract', extractionRequest)
}

/** 更新术语表的术语 */
export async function updateGlossaryTerms(
  glossaryCardId: number,
  terms: GlossaryTerm[]
): Promise<TranslationGlossaryContent> {
  return request.put<TranslationGlossaryContent>(`/glossary/${glossaryCardId}/terms`, terms)
}

/** 删除术语表 */
export async function deleteGlossary(glossaryCardId: number): Promise<{ success: boolean }> {
  return request.delete<{ success: boolean }>(`/glossary/${glossaryCardId}`)
}

/** 翻译术语表中的术语 */
export interface TranslateTermsRequest {
  terms: string[]
  target_language: '繁體中文' | '日文' | '英文' | '韓文'
  llm_config_id: number
  glossary_card_id: number
  project_id: number
}

export interface TranslateTermsResponse {
  translations: { source: string; translated: string }[]
}

export async function translateGlossaryTerms(
  terms: string[],
  targetLanguage: '繁體中文' | '日文' | '英文' | '韓文',
  llmConfigId: number,
  glossaryCardId: number,
  projectId: number
): Promise<{ source: string; translated: string }[]> {
  const req: TranslateTermsRequest = {
    terms,
    target_language: targetLanguage,
    llm_config_id: llmConfigId,
    glossary_card_id: glossaryCardId,
    project_id: projectId,
  }
  const resp = await request.post<TranslateTermsResponse>('/glossary/translate-terms', req)
  return resp.translations
}

/** 获取术语表的上下文字符串 */
export function buildGlossaryContext(glossary: TranslationGlossaryContent): string {
  if (!glossary.terms || glossary.terms.length === 0) {
    return ''
  }

  const lines: string[] = []
  for (const term of glossary.terms) {
    if (term.translated) {
      lines.push(`${term.source} → ${term.translated}`)
    }
  }

  if (lines.length === 0) {
    return ''
  }

  return `【翻译术语表 - ${glossary.target_language}】\n${lines.join('\n')}\n\n请在翻译时优先使用上述术语表的翻译。`
}
