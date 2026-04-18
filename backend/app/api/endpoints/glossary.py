"""翻译术语表 API"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db.session import get_session

logger = logging.getLogger(__name__)
from app.schemas.entity import (
    GlossaryTerm,
    GlossaryTermExtractionRequest,
    GlossaryTermExtractionResponse,
)
from app.services.glossary_service import (
    delete_glossary,
    get_project_glossaries,
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
def extract_and_update_glossary(
    request: GlossaryTermExtractionRequest,
    session: Session = Depends(get_session),
):
    """提取并更新术语表

    支持四种模式：
    - scan_new_concepts: 仅检测新概念
    - translate_new_concepts: 仅为新概念更新翻译（返回待翻译列表）
    - full_rebuild_translations: 全量重建翻译
    - scan_and_translate: 同时检测新概念和自动完成后续翻译
    """
    try:
        return update_glossary_from_extraction(session, request)
    except Exception as e:
        logger.error(f"术语表更新失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{glossary_card_id}/terms", response_model=dict)
def update_terms(
    glossary_card_id: int,
    terms: list[GlossaryTerm],
    session: Session = Depends(get_session),
):
    """更新术语表的术语（手动调整）"""
    try:
        card = update_glossary_terms(session, glossary_card_id, terms)
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
