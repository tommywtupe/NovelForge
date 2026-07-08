from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Iterable, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import Session, select

from app.db.models import Card, CardType
from app.schemas.entity import (
    GlossaryTerm,
    GlossaryTermExtractionRequest,
    GlossaryTermExtractionResponse,
    TranslationGlossary,
)


STORYAXIS_PREFIX = "StoryAxis·"
STORYAXIS_GLOSSARY_TYPE = f"{STORYAXIS_PREFIX}翻译术语表"
LEGACY_GLOSSARY_TYPE = "翻译术语表"

ENTITY_CARD_TYPE_TO_CATEGORY = {
    "角色卡": "character",
    "场景卡": "scene",
    "组织卡": "organization",
    "物品卡": "item",
    "概念卡": "concept",
    f"{STORYAXIS_PREFIX}角色卡": "character",
    f"{STORYAXIS_PREFIX}场景卡": "scene",
    f"{STORYAXIS_PREFIX}组织卡": "organization",
    f"{STORYAXIS_PREFIX}物品卡": "item",
    f"{STORYAXIS_PREFIX}概念卡": "concept",
}

PROJECT_TAG_CARD_TYPES = [f"{STORYAXIS_PREFIX}作品标签", "作品标签"]
PROJECT_OVERVIEW_CARD_TYPES = [f"{STORYAXIS_PREFIX}故事大纲", "故事大纲"]

GLOSSARY_PREFIX_MAP = {
    "繁體中文": "術語表",
    "日文": "用語集",
    "英文": "Glossary",
    "韓文": "용어집",
}


def _load_card_content(card: Card | None) -> dict[str, Any]:
    if card is None:
        return {}
    content = card.content or {}
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return content if isinstance(content, dict) else {}


def _is_storyaxis_card_type(name: str | None) -> bool:
    return bool(name and name.startswith(STORYAXIS_PREFIX))


def _project_prefers_storyaxis(session: Session, project_id: int) -> bool:
    statement = (
        select(Card.id)
        .join(CardType, Card.card_type_id == CardType.id)
        .where(Card.project_id == project_id)
        .where(CardType.name.startswith(STORYAXIS_PREFIX))
    )
    return session.exec(statement).first() is not None


def _sorted_glossary_cards(cards: Iterable[Card]) -> list[Card]:
    return sorted(
        cards,
        key=lambda card: (
            0 if _is_storyaxis_card_type(getattr(getattr(card, "card_type", None), "name", None)) else 1,
            card.id or 0,
        ),
    )


def _resolve_glossary_card_type(session: Session, project_id: int) -> CardType:
    prefer_storyaxis = _project_prefers_storyaxis(session, project_id)
    preferred_names = [STORYAXIS_GLOSSARY_TYPE, LEGACY_GLOSSARY_TYPE] if prefer_storyaxis else [LEGACY_GLOSSARY_TYPE, STORYAXIS_GLOSSARY_TYPE]

    for type_name in preferred_names:
        statement = select(CardType).where(CardType.name == type_name)
        card_type = session.exec(statement).first()
        if card_type:
            return card_type

    raise ValueError("未找到可用的术语表卡片类型")


def _select_first_card_by_types(session: Session, project_id: int, type_names: list[str]) -> Card | None:
    statement = (
        select(Card)
        .join(CardType, Card.card_type_id == CardType.id)
        .where(Card.project_id == project_id)
        .where(CardType.name.in_(type_names))
    )
    cards = session.exec(statement).all()
    if not cards:
        return None
    cards.sort(
        key=lambda card: (
            0 if _is_storyaxis_card_type(getattr(getattr(card, "card_type", None), "name", None)) else 1,
            card.id or 0,
        )
    )
    return cards[0]


def get_project_entity_cards(session: Session, project_id: int) -> list[Card]:
    statement = (
        select(Card)
        .join(CardType, Card.card_type_id == CardType.id)
        .where(Card.project_id == project_id)
        .where(CardType.name.in_(list(ENTITY_CARD_TYPE_TO_CATEGORY.keys())))
    )
    return session.exec(statement).all()


def extract_terms_from_card(card: Card) -> list[str]:
    terms: set[str] = set()
    content = _load_card_content(card)

    for value in (card.title, content.get("name"), content.get("title")):
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                terms.add(normalized)

    return list(terms)


def detect_new_concepts(
    session: Session,
    project_id: int,
    existing_glossary: Optional[TranslationGlossary] = None,
    target_language: Optional[str] = None,
) -> tuple[list[GlossaryTerm], list[str]]:
    del target_language

    existing_sources: set[str] = set()
    if existing_glossary:
        existing_sources = {
            term.source.strip()
            for term in existing_glossary.terms
            if isinstance(term.source, str) and term.source.strip()
        }

    new_terms: list[GlossaryTerm] = []
    all_sources = list(existing_sources)

    for card in get_project_entity_cards(session, project_id):
        card_type_name = getattr(getattr(card, "card_type", None), "name", "")
        category = ENTITY_CARD_TYPE_TO_CATEGORY.get(card_type_name, "other")
        for term_text in extract_terms_from_card(card):
            if term_text in existing_sources:
                continue
            new_terms.append(
                GlossaryTerm(
                    source=term_text,
                    translated="",
                    category=category,
                    source_card_id=card.id,
                )
            )
            existing_sources.add(term_text)
            all_sources.append(term_text)

    return new_terms, all_sources


def get_glossary_prefix(ui_language: str) -> str:
    return GLOSSARY_PREFIX_MAP.get(ui_language, "Glossary")


def build_glossary_context(terms: list[GlossaryTerm], ui_language: str = "繁體中文") -> str:
    lines = [
        f"{get_glossary_prefix(ui_language)} {term.source} -> {term.translated}"
        for term in terms
        if term.translated
    ]
    return "\n".join(lines)


def build_glossary_context_dynamic(
    glossary: TranslationGlossary,
    source_text: str = "",
    ui_language: str = "繁體中文",
) -> str:
    if not glossary.terms:
        return ""

    normalized_source = source_text or ""
    lines: list[str] = []
    for term in sorted(glossary.terms, key=lambda item: len(item.source), reverse=True):
        if not term.translated:
            continue
        if normalized_source and term.source not in normalized_source:
            continue
        line = f"{get_glossary_prefix(ui_language)} {term.source} -> {term.translated}"
        if term.notes:
            line = f"{line} #{term.notes}"
        lines.append(line)

    return "\n".join(lines)


def get_project_glossaries(
    session: Session,
    project_id: int,
    target_language: Optional[str] = None,
) -> list[Card]:
    statement = (
        select(Card)
        .join(CardType, Card.card_type_id == CardType.id)
        .where(Card.project_id == project_id)
        .where(CardType.name.in_([STORYAXIS_GLOSSARY_TYPE, LEGACY_GLOSSARY_TYPE]))
    )
    cards = _sorted_glossary_cards(session.exec(statement).all())
    if not target_language:
        return cards

    filtered: list[Card] = []
    for card in cards:
        content = _load_card_content(card)
        if content.get("target_language") == target_language:
            filtered.append(card)
    return filtered


def get_or_create_glossary_card(
    session: Session,
    project_id: int,
    target_language: str,
    glossary_card_id: Optional[int] = None,
) -> Card:
    if glossary_card_id:
        glossary_card = session.get(Card, glossary_card_id)
        if glossary_card:
            return glossary_card

    existing = get_project_glossaries(session, project_id, target_language)
    if existing:
        return existing[0]

    card_type = _resolve_glossary_card_type(session, project_id)
    suffix = f"StoryAxis·术语表·{target_language}" if card_type.name == STORYAXIS_GLOSSARY_TYPE else f"{target_language}术语表"
    glossary = TranslationGlossary(
        name=suffix,
        target_language=target_language,
        terms=[],
        updated_at=datetime.now().isoformat(),
    )
    card = Card(
        title=suffix,
        project_id=project_id,
        card_type_id=card_type.id,
        content=glossary.model_dump(),
    )
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


def update_glossary_from_extraction(
    session: Session,
    request: GlossaryTermExtractionRequest,
) -> GlossaryTermExtractionResponse:
    glossary_card = get_or_create_glossary_card(
        session,
        request.project_id,
        request.target_language,
        glossary_card_id=request.glossary_card_id,
    )
    content = _load_card_content(glossary_card)

    try:
        existing_glossary = TranslationGlossary(**content) if content else TranslationGlossary(
            name=glossary_card.title,
            target_language=request.target_language,
            terms=[],
        )
    except Exception:
        existing_glossary = TranslationGlossary(
            name=glossary_card.title,
            target_language=request.target_language,
            terms=[],
        )

    if request.update_mode in {"scan_new_concepts", "scan_and_translate", "translate_new_concepts"}:
        new_terms, _ = detect_new_concepts(
            session,
            request.project_id,
            existing_glossary=existing_glossary,
            target_language=request.target_language,
        )
        if request.update_mode == "translate_new_concepts":
            return GlossaryTermExtractionResponse(
                terms=new_terms,
                new_terms_count=len(new_terms),
                updated_terms_count=0,
                removed_terms_count=0,
                glossary_card_id=glossary_card.id,
            )
        existing_glossary.terms.extend(new_terms)
        glossary_card.content = existing_glossary.model_dump()
        glossary_card.title = existing_glossary.name
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

    all_terms, _ = detect_new_concepts(
        session,
        request.project_id,
        existing_glossary=None,
        target_language=request.target_language,
    )
    rebuilt = TranslationGlossary(
        name=existing_glossary.name or glossary_card.title,
        target_language=request.target_language,
        terms=all_terms,
        updated_at=datetime.now().isoformat(),
    )
    glossary_card.content = rebuilt.model_dump()
    glossary_card.title = rebuilt.name
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


def update_glossary_terms(
    session: Session,
    glossary_card_id: int,
    terms: list[GlossaryTerm],
    name: Optional[str] = None,
    target_language: Optional[str] = None,
) -> Card:
    glossary_card = session.get(Card, glossary_card_id)
    if not glossary_card:
        raise ValueError(f"术语表卡片不存在: {glossary_card_id}")

    content = _load_card_content(glossary_card)
    try:
        glossary = TranslationGlossary(**content)
    except Exception:
        glossary = TranslationGlossary(
            name=content.get("name") or glossary_card.title,
            target_language=content.get("target_language") or target_language or "繁體中文",
            terms=[],
        )

    glossary.terms = [
        term if isinstance(term, GlossaryTerm) else GlossaryTerm.model_validate(term)
        for term in terms
    ]
    if name is not None:
        glossary.name = name
    if target_language is not None:
        glossary.target_language = target_language
    glossary.updated_at = datetime.now().isoformat()

    glossary_card.title = glossary.name
    glossary_card.content = glossary.model_dump()
    session.add(glossary_card)
    session.commit()
    session.refresh(glossary_card)
    return glossary_card


def delete_glossary(session: Session, glossary_card_id: int) -> bool:
    glossary_card = session.get(Card, glossary_card_id)
    if not glossary_card:
        return False
    session.delete(glossary_card)
    session.commit()
    return True


def get_project_context_for_translation(session: Session, project_id: int) -> dict[str, str]:
    from app.schemas.wizard import ParagraphOverview, Tags

    tags_card = _select_first_card_by_types(session, project_id, PROJECT_TAG_CARD_TYPES)
    overview_card = _select_first_card_by_types(session, project_id, PROJECT_OVERVIEW_CARD_TYPES)

    tags_content = "未设置"
    audience = "通用"
    if tags_card:
        raw_tags = _load_card_content(tags_card)
        try:
            tags = Tags(**raw_tags)
            tag_parts: list[str] = []
            if tags.theme:
                tag_parts.append(f"主题类别: {tags.theme}")
            if tags.story_tags:
                tag_parts.append("故事标签: " + ", ".join(f"{name}({weight})" for name, weight in tags.story_tags))
            if tags.affection:
                tag_parts.append(f"情感标签: {tags.affection}")
            if tags.narrative_person:
                tag_parts.append(f"写作人称: {tags.narrative_person}")
            tags_content = "\n".join(tag_parts) if tag_parts else "未设置"
            audience = tags.audience or "通用"
        except Exception:
            tags_content = json.dumps(raw_tags, ensure_ascii=False)

    story_overview = "未设置"
    if overview_card:
        raw_overview = _load_card_content(overview_card)
        try:
            story_overview = ParagraphOverview(**raw_overview).overview or "未设置"
        except Exception:
            story_overview = json.dumps(raw_overview, ensure_ascii=False)

    return {
        "tags_content": tags_content,
        "audience": audience,
        "story_overview": story_overview,
    }


def _get_translation_prompt_template(session: Session) -> str:
    from app.services import prompt_service

    for prompt_name in ("StoryAxis·术语翻译", "术语翻译"):
        prompt = prompt_service.get_prompt_by_name(session, prompt_name)
        if prompt and prompt.template:
            return prompt_service.inject_knowledge(session, str(prompt.template))
    return (
        "你是专业文学翻译术语顾问。请结合题材、读者与故事概述，"
        "为专有名词给出自然、统一、可复用的目标语言译名。"
    )


async def translate_glossary_terms(
    session: Session,
    terms: list[str],
    target_language: str,
    llm_config_id: int,
    glossary_card_id: int,
    project_id: int,
) -> list[dict[str, str]]:
    from app.services import prompt_service
    from app.services.ai.core.chat_model_factory import build_chat_model
    from app.services.ai.core.quota_manager import record_usage
    from app.services.ai.core.token_utils import calc_input_tokens, estimate_tokens

    if not terms:
        return []

    project_context = get_project_context_for_translation(session, project_id)
    system_prompt = prompt_service.render_prompt(
        _get_translation_prompt_template(session),
        project_context,
    )

    glossary_card = session.get(Card, glossary_card_id)
    glossary_context = ""
    if glossary_card:
        try:
            glossary = TranslationGlossary(**_load_card_content(glossary_card))
            glossary_context = build_glossary_context(glossary.terms, ui_language=target_language)
        except Exception:
            glossary_context = ""

    context_hint = f"\n\n现有术语表参考：\n{glossary_context}" if glossary_context else ""
    user_prompt = (
        f"请将以下术语翻译为{target_language}，保持文学专名统一、简洁、可复用：\n\n"
        f"{chr(10).join(terms)}"
        f"{context_hint}\n\n"
        "请逐行输出，格式固定为：原文 -> 译名"
    )

    model = build_chat_model(
        session=session,
        llm_config_id=llm_config_id,
        temperature=0.2,
        max_tokens=4096,
        timeout=120,
    )
    response = await model.ainvoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    content = getattr(response, "content", response)
    if isinstance(content, list):
        text = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    else:
        text = str(content or "")

    try:
        record_usage(
            session,
            llm_config_id,
            input_tokens=calc_input_tokens(system_prompt, user_prompt),
            output_tokens=estimate_tokens(text),
            calls=1,
            aborted=False,
        )
    except Exception:
        pass

    translations: list[dict[str, str]] = []
    seen_sources: set[str] = set()
    for line in text.splitlines():
        normalized = line.strip()
        if not normalized:
            continue
        if "->" in normalized:
            source, translated = normalized.split("->", 1)
        elif "→" in normalized:
            source, translated = normalized.split("→", 1)
        else:
            continue
        source = source.strip()
        translated = translated.strip()
        if not source or not translated or source in seen_sources:
            continue
        translations.append({"source": source, "translated": translated})
        seen_sources.add(source)

    return translations


async def translate_pending_glossary_terms(
    session: Session,
    request: GlossaryTermExtractionRequest,
) -> GlossaryTermExtractionResponse:
    glossary_card = get_or_create_glossary_card(
        session,
        request.project_id,
        request.target_language,
        glossary_card_id=request.glossary_card_id,
    )
    glossary = TranslationGlossary(**_load_card_content(glossary_card))
    terms_to_translate = [term for term in glossary.terms if not term.translated]
    if not terms_to_translate:
        return GlossaryTermExtractionResponse(
            terms=glossary.terms,
            new_terms_count=0,
            updated_terms_count=0,
            removed_terms_count=0,
            glossary_card_id=glossary_card.id,
        )

    if not request.llm_config_id:
        raise ValueError("术语翻译需要有效的 llm_config_id")

    translated_pairs = await translate_glossary_terms(
        session,
        [term.source for term in terms_to_translate],
        request.target_language,
        request.llm_config_id,
        glossary_card.id,
        request.project_id,
    )
    translation_map = {item["source"]: item["translated"] for item in translated_pairs}
    updated_count = 0
    for term in glossary.terms:
        translated = translation_map.get(term.source)
        if translated and not term.translated:
            term.translated = translated
            updated_count += 1
    glossary.updated_at = datetime.now().isoformat()
    glossary_card.content = glossary.model_dump()
    session.add(glossary_card)
    session.commit()
    session.refresh(glossary_card)
    return GlossaryTermExtractionResponse(
        terms=glossary.terms,
        new_terms_count=0,
        updated_terms_count=updated_count,
        removed_terms_count=0,
        glossary_card_id=glossary_card.id,
    )


async def extract_and_translate_glossary_terms(
    session: Session,
    request: GlossaryTermExtractionRequest,
) -> GlossaryTermExtractionResponse:
    extraction = update_glossary_from_extraction(session, request)
    if request.update_mode not in {"scan_and_translate", "full_rebuild_translations"}:
        return extraction
    pending_request = request.model_copy(update={"glossary_card_id": extraction.glossary_card_id})
    translated = await translate_pending_glossary_terms(session, pending_request)
    return GlossaryTermExtractionResponse(
        terms=translated.terms,
        new_terms_count=extraction.new_terms_count,
        updated_terms_count=translated.updated_terms_count,
        removed_terms_count=translated.removed_terms_count,
        glossary_card_id=translated.glossary_card_id,
    )
