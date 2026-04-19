"""翻译术语表 API"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.db.session import get_session

logger = logging.getLogger(__name__)
from app.schemas.entity import (
    GlossaryTerm,
    GlossaryTermExtractionRequest,
    GlossaryTermExtractionResponse,
    TranslateTermsRequest,
    TranslateTermsResponse,
)
from app.services.glossary_service import (
    delete_glossary,
    extract_and_translate_glossary_terms,
    get_project_glossaries,
    translate_glossary_terms,
    translate_pending_glossary_terms,
    update_glossary_from_extraction,
    update_glossary_terms,
)

router = APIRouter(tags=["术语表"])


@router.get("/list", response_model=list)
def list_glossaries(
    project_id: int = Query(..., description="项目ID"),
    target_language: Optional[str] = Query(None, description="目标语言过滤"),
    session: Session = Depends(get_session),
):
    """获取项目的术语表列表"""
    return get_project_glossaries(session, project_id, target_language)


@router.post("/extract", response_model=GlossaryTermExtractionResponse)
async def extract_and_update_glossary(
    request: GlossaryTermExtractionRequest,
    session: Session = Depends(get_session),
):
    """提取并更新术语表

    支持四种模式：
    - scan_new_concepts: 仅检测新概念
    - translate_new_concepts: 仅为术语表中未翻译的项进行AI翻译
    - full_rebuild_translations: 全量重建翻译
    - scan_and_translate: 同时检测新概念和自动完成后续翻译
    """
    try:
        if request.update_mode == "translate_new_concepts":
            # 仅为未翻译的项进行AI翻译
            return await translate_pending_glossary_terms(session, request)
        elif request.update_mode in ["scan_and_translate", "full_rebuild_translations"]:
            # 扫描并翻译
            return await extract_and_translate_glossary_terms(session, request)
        else:
            # scan_new_concepts: 仅扫描
            return update_glossary_from_extraction(session, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"术语表更新失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateGlossaryRequest(BaseModel):
    """更新术语表的请求"""
    terms: list[GlossaryTerm]
    name: Optional[str] = None
    target_language: Optional[str] = None


@router.put("/{glossary_card_id}/terms", response_model=dict)
def update_terms(
    glossary_card_id: int,
    request: UpdateGlossaryRequest,
    session: Session = Depends(get_session),
):
    """更新术语表的术语和元数据（手动调整）"""
    try:
        card = update_glossary_terms(
            session,
            glossary_card_id,
            request.terms,
            name=request.name,
            target_language=request.target_language,
        )
        return card.content or {}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"术语表更新失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{glossary_card_id}")
def remove_glossary(
    glossary_card_id: int,
    session: Session = Depends(get_session),
):
    """删除术语表"""
    success = delete_glossary(session, glossary_card_id)
    if not success:
        raise HTTPException(status_code=404, detail="术语表不存在")
    return {"success": True}


@router.post("/translate-terms", response_model=TranslateTermsResponse)
async def translate_terms(
    request: TranslateTermsRequest,
    session: Session = Depends(get_session),
):
    """翻译术语表中的术语"""
    try:
        translations = await translate_glossary_terms(
            session=session,
            terms=request.terms,
            target_language=request.target_language,
            llm_config_id=request.llm_config_id,
            glossary_card_id=request.glossary_card_id,
            project_id=request.project_id,
        )
        return TranslateTermsResponse(translations=translations)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"术语翻译失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
