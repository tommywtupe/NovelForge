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

/** 更新术语表的术语和元数据 */
export async function updateGlossaryTerms(
  glossaryCardId: number,
  terms: GlossaryTerm[],
  name?: string,
  target_language?: string
): Promise<TranslationGlossaryContent> {
  return request.put<TranslationGlossaryContent>(`/glossary/${glossaryCardId}/terms`, {
    terms,
    name,
    target_language,
  })
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
