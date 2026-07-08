from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.db.session import get_session
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
    project_id: int = Query(..., description="项目 ID"),
    target_language: Optional[str] = Query(None, description="目标语言"),
    session: Session = Depends(get_session),
):
    return get_project_glossaries(session, project_id, target_language)


@router.post("/extract", response_model=GlossaryTermExtractionResponse)
async def extract_and_update_glossary(
    request: GlossaryTermExtractionRequest,
    session: Session = Depends(get_session),
):
    try:
        if request.update_mode == "translate_new_concepts":
            return await translate_pending_glossary_terms(session, request)
        if request.update_mode in {"scan_and_translate", "full_rebuild_translations"}:
            return await extract_and_translate_glossary_terms(session, request)
        return update_glossary_from_extraction(session, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class UpdateGlossaryRequest(BaseModel):
    terms: list[GlossaryTerm]
    name: Optional[str] = None
    target_language: Optional[str] = None


@router.put("/{glossary_card_id}/terms", response_model=dict)
def update_terms(
    glossary_card_id: int,
    request: UpdateGlossaryRequest,
    session: Session = Depends(get_session),
):
    try:
        card = update_glossary_terms(
            session,
            glossary_card_id,
            request.terms,
            name=request.name,
            target_language=request.target_language,
        )
        return card.content or {}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{glossary_card_id}")
def remove_glossary(
    glossary_card_id: int,
    session: Session = Depends(get_session),
):
    if not delete_glossary(session, glossary_card_id):
        raise HTTPException(status_code=404, detail="术语表不存在")
    return {"success": True}


@router.post("/translate-terms", response_model=TranslateTermsResponse)
async def translate_terms(
    request: TranslateTermsRequest,
    session: Session = Depends(get_session),
):
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
