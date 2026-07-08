import request from './request'
import type { CardRead } from './cards'

export type GlossaryCategory =
  | 'character'
  | 'scene'
  | 'organization'
  | 'item'
  | 'concept'
  | 'other'

export type TargetLanguage = '繁體中文' | '日文' | '英文' | '韓文'

export interface GlossaryTerm {
  source: string
  translated: string
  category: GlossaryCategory
  source_card_id: number | null
  notes?: string | null
}

export interface TranslationGlossaryContent {
  name: string
  target_language: TargetLanguage
  terms: GlossaryTerm[]
  updated_at?: string | null
}

export type GlossaryCard = CardRead & {
  content: TranslationGlossaryContent
}

export type UpdateMode =
  | 'scan_new_concepts'
  | 'translate_new_concepts'
  | 'full_rebuild_translations'
  | 'scan_and_translate'

export interface GlossaryTermExtractionRequest {
  project_id: number
  target_language: TargetLanguage
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

export interface TranslateTermsResponse {
  translations: Array<{ source: string; translated: string }>
}

export async function listGlossaries(
  projectId: number,
  targetLanguage?: TargetLanguage
): Promise<GlossaryCard[]> {
  const params = new URLSearchParams({ project_id: String(projectId) })
  if (targetLanguage) {
    params.set('target_language', targetLanguage)
  }
  return request.get<GlossaryCard[]>(`/glossary/list?${params.toString()}`)
}

export async function extractAndUpdateGlossary(
  extractionRequest: GlossaryTermExtractionRequest
): Promise<GlossaryTermExtractionResponse> {
  return request.post<GlossaryTermExtractionResponse>('/glossary/extract', extractionRequest)
}

export async function updateGlossaryTerms(
  glossaryCardId: number,
  terms: GlossaryTerm[],
  name?: string,
  targetLanguage?: TargetLanguage
): Promise<TranslationGlossaryContent> {
  return request.put<TranslationGlossaryContent>(`/glossary/${glossaryCardId}/terms`, {
    terms,
    name,
    target_language: targetLanguage,
  })
}

export async function deleteGlossary(glossaryCardId: number): Promise<{ success: boolean }> {
  return request.delete<{ success: boolean }>(`/glossary/${glossaryCardId}`)
}

export async function translateGlossaryTerms(
  terms: string[],
  targetLanguage: TargetLanguage,
  llmConfigId: number,
  glossaryCardId: number,
  projectId: number
): Promise<Array<{ source: string; translated: string }>> {
  const response = await request.post<TranslateTermsResponse>('/glossary/translate-terms', {
    terms,
    target_language: targetLanguage,
    llm_config_id: llmConfigId,
    glossary_card_id: glossaryCardId,
    project_id: projectId,
  })
  return response.translations
}
