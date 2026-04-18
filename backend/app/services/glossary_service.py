"""翻译术语表服务

提供术语表生成、更新和管理功能。
"""

from datetime import datetime
from typing import List, Optional, Tuple

from loguru import logger
from sqlmodel import Session, select

from app.db.models import Card, CardType
from app.schemas.entity import (
    GlossaryTerm,
    GlossaryTermExtractionRequest,
    GlossaryTermExtractionResponse,
    TranslationGlossary,
)


# 需要扫描的卡片类型
ENTITY_CARD_TYPES = ["角色卡", "场景卡", "组织卡", "物品卡", "概念卡"]

# 各类别的字段名映射（从卡片 content 中提取专有名词，仅使用卡片标题）
CATEGORY_FIELD_MAP = {
    "character": ["title"],  # 角色卡
    "scene": ["title"],  # 场景卡
    "organization": ["title"],  # 组织卡
    "item": ["title"],  # 物品卡
    "concept": ["title"],  # 概念卡
}

CARD_TYPE_TO_CATEGORY = {
    "角色卡": "character",
    "场景卡": "scene",
    "组织卡": "organization",
    "物品卡": "item",
    "概念卡": "concept",
}


def get_project_entity_cards(session: Session, project_id: int) -> List[Card]:
    """获取项目中所有实体卡片"""
    statement = (
        select(Card)
        .join(CardType, Card.card_type_id == CardType.id)
        .where(Card.project_id == project_id)
        .where(CardType.name.in_(ENTITY_CARD_TYPES))
    )
    return session.exec(statement).all()


def extract_terms_from_card(card: Card) -> List[str]:
    """从卡片中提取专有名词"""
    terms = set()
    content = card.content or {}
    category = CARD_TYPE_TO_CATEGORY.get(card.card_type.name if card.card_type else "")

    if not category:
        return list(terms)

    # 首先添加卡片的标题
    if card.title and card.title.strip():
        terms.add(card.title.strip())

    # 然后添加 content 中配置的字段
    fields = CATEGORY_FIELD_MAP.get(category, [])
    for field in fields:
        value = content.get(field, "")
        if isinstance(value, str) and value.strip():
            terms.add(value.strip())

    return list(terms)


def detect_new_concepts(
    session: Session,
    project_id: int,
    existing_glossary: Optional[TranslationGlossary] = None
) -> Tuple[List[GlossaryTerm], List[str]]:
    """检测新概念，返回 (新术语列表, 所有已存在术语的原文列表)"""
    entity_cards = get_project_entity_cards(session, project_id)

    existing_sources = set()
    if existing_glossary and existing_glossary.terms:
        existing_sources = {term.source for term in existing_glossary.terms}

    new_terms: List[GlossaryTerm] = []
    all_sources: List[str] = list(existing_sources)

    for card in entity_cards:
        extracted = extract_terms_from_card(card)
        category = CARD_TYPE_TO_CATEGORY.get(card.card_type.name if card.card_type else "", "other")

        for term_text in extracted:
            if term_text not in existing_sources:
                new_terms.append(GlossaryTerm(
                    source=term_text,
                    translated="",  # 待翻译
                    category=category,
                    source_card_id=card.id,
                ))
                existing_sources.add(term_text)
                all_sources.append(term_text)

    return new_terms, all_sources


def build_glossary_context(terms: List[GlossaryTerm]) -> str:
    """构建术语表上下文字符串，用于翻译 prompt"""
    if not terms:
        return ""

    lines = []
    for term in terms:
        if term.translated:  # 只包含已有翻译的术语
            lines.append(f"{term.source} → {term.translated}")

    if not lines:
        return ""

    return "【翻译术语表】\n" + "\n".join(lines) + "\n\n请在翻译时优先使用上述术语表的翻译。"


def get_or_create_glossary_card(
    session: Session,
    project_id: int,
    target_language: str,
) -> Card:
    """获取或创建术语表卡片"""
    # 查找已存在的术语表
    statement = (
        select(Card)
        .join(CardType, Card.card_type_id == CardType.id)
        .where(Card.project_id == project_id)
        .where(CardType.name == "翻译术语表")
    )
    existing = session.exec(statement).first()

    if existing:
        content = existing.content or {}
        if isinstance(content, dict):
            # 确保 content 是正确的格式
            if "terms" not in content:
                content["terms"] = []
            if "target_language" not in content:
                content["target_language"] = target_language
            if "name" not in content:
                content["name"] = f"{target_language}术语表"
        return existing

    # 创建新的术语表卡片
    new_card = Card(
        title=f"{target_language}术语表",
        project_id=project_id,
        content=TranslationGlossary(
            name=f"{target_language}术语表",
            target_language=target_language,
            terms=[],
            updated_at=datetime.now().isoformat(),
        ).model_dump(),
    )
    session.add(new_card)
    session.commit()
    session.refresh(new_card)
    return new_card


def update_glossary_from_extraction(
    session: Session,
    request: GlossaryTermExtractionRequest,
) -> GlossaryTermExtractionResponse:
    """根据提取结果更新术语表"""
    glossary_card = get_or_create_glossary_card(
        session, request.project_id, request.target_language
    )

    content = glossary_card.content or {}
    if isinstance(content, str):
        import json
        content = json.loads(content)

    # 解析现有术语表
    existing_glossary = None
    if content.get("terms"):
        try:
            existing_glossary = TranslationGlossary(**content)
        except Exception:
            existing_glossary = None

    if request.update_mode in ["scan_new_concepts", "scan_and_translate"]:
        # 模式1和4：检测新概念
        new_terms, _ = detect_new_concepts(session, request.project_id, existing_glossary)

        if existing_glossary:
            existing_terms_map = {t.source: t for t in existing_glossary.terms}
            for nt in new_terms:
                if nt.source not in existing_terms_map:
                    existing_glossary.terms.append(nt)
        else:
            existing_glossary = TranslationGlossary(
                name=f"{request.target_language}术语表",
                target_language=request.target_language,
                terms=new_terms,
                updated_at=datetime.now().isoformat(),
            )

        # 更新卡片内容
        glossary_card.content = existing_glossary.model_dump()
        session.add(glossary_card)
        session.commit()
        session.refresh(glossary_card)

        return GlossaryTermExtractionResponse(
            terms=new_terms,
            new_terms_count=len(new_terms),
            updated_terms_count=0,
            removed_terms_count=0,
            glossary_card_id=glossary_card.id,
        )

    elif request.update_mode == "translate_new_concepts":
        # 模式2：仅为新概念更新翻译（需要外部调用 LLM 翻译后再次调用）
        new_terms, all_sources = detect_new_concepts(session, request.project_id, existing_glossary)

        # 返回待翻译的新术语，实际翻译由调用方处理
        return GlossaryTermExtractionResponse(
            terms=new_terms,
            new_terms_count=len(new_terms),
            updated_terms_count=0,
            removed_terms_count=0,
            glossary_card_id=glossary_card.id,
        )

    elif request.update_mode == "full_rebuild_translations":
        # 模式3：全量重建翻译
        all_terms, _ = detect_new_concepts(session, request.project_id, None)

        new_glossary = TranslationGlossary(
            name=f"{request.target_language}术语表",
            target_language=request.target_language,
            terms=all_terms,
            updated_at=datetime.now().isoformat(),
        )

        glossary_card.content = new_glossary.model_dump()
        session.add(glossary_card)
        session.commit()
        session.refresh(glossary_card)

        return GlossaryTermExtractionResponse(
            terms=all_terms,
            new_terms_count=len(all_terms),
            updated_terms_count=0,
            removed_terms_count=0,
            glossary_card_id=glossary_card.id,
        )

    return GlossaryTermExtractionResponse(
        terms=[],
        new_terms_count=0,
        updated_terms_count=0,
        removed_terms_count=0,
        glossary_card_id=glossary_card.id,
    )


def get_project_glossaries(
    session: Session,
    project_id: int,
    target_language: Optional[str] = None,
) -> List[Card]:
    """获取项目的所有术语表"""
    statement = (
        select(Card)
        .join(CardType, Card.card_type_id == CardType.id)
        .where(Card.project_id == project_id)
        .where(CardType.name == "翻译术语表")
    )

    if target_language:
        # 需要过滤特定语言的术语表
        cards = session.exec(statement).all()
        return [
            c for c in cards
            if (c.content or {}).get("target_language") == target_language
        ]

    return session.exec(statement).all()


def update_glossary_terms(
    session: Session,
    glossary_card_id: int,
    terms: List[GlossaryTerm],
) -> Card:
    """更新术语表的术语"""
    glossary_card = session.get(Card, glossary_card_id)
    if not glossary_card:
        raise ValueError(f"术语表卡片不存在: {glossary_card_id}")

    content = glossary_card.content or {}
    if isinstance(content, str):
        import json
        content = json.loads(content)

    # 解析现有术语表
    try:
        existing_glossary = TranslationGlossary(**content)
    except Exception:
        existing_glossary = TranslationGlossary(
            name=content.get("name", "术语表"),
            target_language=content.get("target_language", "繁體中文"),
            terms=[],
            updated_at=datetime.now().isoformat(),
        )

    # 更新术语
    existing_glossary.terms = terms
    existing_glossary.updated_at = datetime.now().isoformat()

    glossary_card.content = existing_glossary.model_dump()
    session.add(glossary_card)
    session.commit()
    session.refresh(glossary_card)

    return glossary_card


def delete_glossary(session: Session, glossary_card_id: int) -> bool:
    """删除术语表"""
    glossary_card = session.get(Card, glossary_card_id)
    if not glossary_card:
        return False

    session.delete(glossary_card)
    session.commit()
    return True
