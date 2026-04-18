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


async def translate_pending_glossary_terms(
    session: Session,
    request: GlossaryTermExtractionRequest,
) -> GlossaryTermExtractionResponse:
    """仅为术语表中未翻译的项进行AI翻译（不扫描新概念）

    1. 获取现有术语表
    2. 找出 translated 为空的项
    3. 调用 AI 翻译
    4. 更新术语表并返回结果
    """
    from app.services import llm_config_service

    # 获取 LLM 配置
    llm_config_id = request.llm_config_id
    if not llm_config_id:
        configs = llm_config_service.get_llm_configs(session)
        if configs:
            llm_config_id = configs[0].id
        else:
            raise ValueError("未找到可用的 LLM 配置")

    # 获取术语表卡片
    glossary_card = get_or_create_glossary_card(
        session, request.project_id, request.target_language
    )

    if not glossary_card or not glossary_card.content:
        return GlossaryTermExtractionResponse(
            terms=[],
            new_terms_count=0,
            updated_terms_count=0,
            removed_terms_count=0,
            glossary_card_id=glossary_card.id if glossary_card else 0,
        )

    content = glossary_card.content
    if isinstance(content, str):
        import json
        content = json.loads(content)

    if not content.get("terms"):
        return GlossaryTermExtractionResponse(
            terms=[GlossaryTerm(**t) for t in content.get("terms", [])],
            new_terms_count=0,
            updated_terms_count=0,
            removed_terms_count=0,
            glossary_card_id=glossary_card.id,
        )

    # 找出未翻译的术语
    terms_to_translate = [t for t in content["terms"] if not t.get("translated")]
    if not terms_to_translate:
        # 没有需要翻译的项
        return GlossaryTermExtractionResponse(
            terms=[GlossaryTerm(**t) for t in content["terms"]],
            new_terms_count=0,
            updated_terms_count=0,
            removed_terms_count=0,
            glossary_card_id=glossary_card.id,
        )

    # 调用 AI 翻译
    source_terms = [t["source"] for t in terms_to_translate]
    translations = await translate_glossary_terms(
        session=session,
        terms=source_terms,
        target_language=request.target_language,
        llm_config_id=llm_config_id,
        glossary_card_id=glossary_card.id,
        project_id=request.project_id,
    )

    # 构建翻译映射并更新术语
    translated_map = {t["source"]: t["translated"] for t in translations}
    translated_count = 0
    for term in content["terms"]:
        source = term.get("source")
        if not term.get("translated") and source in translated_map:
            term["translated"] = translated_map[source]
            translated_count += 1

    # 保存更新后的术语表
    glossary_card.content = content
    session.add(glossary_card)
    session.commit()

    # 返回更新后的结果
    return GlossaryTermExtractionResponse(
        terms=[GlossaryTerm(**t) for t in content["terms"]],
        new_terms_count=0,
        updated_terms_count=translated_count,
        removed_terms_count=0,
        glossary_card_id=glossary_card.id,
    )


async def extract_and_translate_glossary_terms(
    session: Session,
    request: GlossaryTermExtractionRequest,
) -> GlossaryTermExtractionResponse:
    """提取并翻译术语（异步版本）

    1. 先调用提取接口更新术语表
    2. 如果需要翻译（scan_and_translate 或 full_rebuild_translations），则调用 AI 翻译
    3. 更新术语表卡片中的翻译字段
    """
    from app.services import llm_config_service

    # 先执行提取（同步操作）
    extraction_result = update_glossary_from_extraction(session, request)

    # 检查是否需要翻译
    needs_translation = request.update_mode in [
        "scan_and_translate",
        "full_rebuild_translations",
        "translate_new_concepts",
    ]
    if not needs_translation:
        return extraction_result

    # 获取 LLM 配置
    llm_config_id = request.llm_config_id
    if not llm_config_id:
        # 尝试获取项目的默认 LLM 配置
        configs = llm_config_service.get_llm_configs(session)
        if configs:
            llm_config_id = configs[0].id
        else:
            raise ValueError("未找到可用的 LLM 配置")

    # 获取需要翻译的术语（translated 为空的术语）
    glossary_card = session.get(Card, extraction_result.glossary_card_id)
    if not glossary_card or not glossary_card.content:
        return extraction_result

    content = glossary_card.content
    if isinstance(content, str):
        import json
        content = json.loads(content)

    if not content.get("terms"):
        return extraction_result

    terms_to_translate = [t for t in content["terms"] if not t.get("translated")]
    if not terms_to_translate:
        return extraction_result

    # 调用 AI 翻译
    source_terms = [t["source"] for t in terms_to_translate]
    translations = await translate_glossary_terms(
        session=session,
        terms=source_terms,
        target_language=request.target_language,
        llm_config_id=llm_config_id,
        glossary_card_id=glossary_card.id,
        project_id=request.project_id,
    )

    # 构建翻译映射并更新术语
    translated_map = {t["source"]: t["translated"] for t in translations}
    translated_count = 0
    for term in content["terms"]:
        source = term.get("source")
        if not term.get("translated") and source in translated_map:
            term["translated"] = translated_map[source]
            translated_count += 1

    # 保存更新后的术语表
    glossary_card.content = content
    session.add(glossary_card)
    session.commit()

    # 返回更新后的结果
    return GlossaryTermExtractionResponse(
        terms=[GlossaryTerm(**t) for t in content["terms"]],
        new_terms_count=extraction_result.new_terms_count,
        updated_terms_count=translated_count,
        removed_terms_count=extraction_result.removed_terms_count,
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


def get_project_context_for_translation(
    session: Session,
    project_id: int,
) -> dict:
    """获取项目上下文信息用于术语翻译

    Args:
        session: 数据库会话
        project_id: 项目ID

    Returns:
        包含 tags_content, audience, story_overview 的字典
    """
    import json

    # 获取作品标签卡片
    tags_statement = (
        select(Card)
        .join(CardType, Card.card_type_id == CardType.id)
        .where(Card.project_id == project_id)
        .where(CardType.name == "作品标签")
    )
    tags_card = session.exec(tags_statement).first()

    tags_content = ""
    audience = "通用"
    if tags_card and tags_card.content:
        content = tags_card.content
        if isinstance(content, str):
            content = json.loads(content)
        # 解析 Tags schema
        try:
            from app.schemas.wizard import Tags
            tags_data = Tags(**content)
            # 构建标签内容字符串
            tag_parts = []
            if tags_data.theme:
                tag_parts.append(f"主题类别: {tags_data.theme}")
            if tags_data.story_tags:
                tag_strs = [f"{t[0]}({t[1]})" for t in tags_data.story_tags]
                tag_parts.append(f"故事标签: {', '.join(tag_strs)}")
            if tags_data.affection:
                tag_parts.append(f"情感标签: {tags_data.affection}")
            if tags_data.narrative_person:
                tag_parts.append(f"写作人称: {tags_data.narrative_person}")
            tags_content = "\n".join(tag_parts) if tag_parts else "未设置"
            audience = tags_data.audience or "通用"
        except Exception:
            tags_content = str(content)

    # 获取故事大纲卡片
    overview_statement = (
        select(Card)
        .join(CardType, Card.card_type_id == CardType.id)
        .where(Card.project_id == project_id)
        .where(CardType.name == "故事大纲")
    )
    overview_card = session.exec(overview_statement).first()

    story_overview = ""
    if overview_card and overview_card.content:
        content = overview_card.content
        if isinstance(content, str):
            content = json.loads(content)
        # 解析 ParagraphOverview schema
        try:
            from app.schemas.wizard import ParagraphOverview
            overview_data = ParagraphOverview(**content)
            story_overview = overview_data.overview or ""
        except Exception:
            story_overview = str(content)

    return {
        "tags_content": tags_content or "未设置",
        "audience": audience,
        "story_overview": story_overview or "未设置",
    }


async def translate_glossary_terms(
    session: Session,
    terms: List[str],
    target_language: str,
    llm_config_id: int,
    glossary_card_id: int,
    project_id: int,
) -> List[dict]:
    """翻译术语表中的术语

    Args:
        session: 数据库会话
        terms: 待翻译的术语列表
        target_language: 目标语言
        llm_config_id: LLM配置ID
        glossary_card_id: 术语表卡片ID
        project_id: 项目ID（用于获取作品背景上下文）

    Returns:
        翻译结果列表，每项包含 source 和 translated
    """
    from app.services import prompt_service
    from app.services.ai.core.chat_model_factory import build_chat_model
    from app.services.ai.core.token_utils import calc_input_tokens, estimate_tokens
    from app.services.ai.core.quota_manager import record_usage
    from langchain_core.messages import HumanMessage, SystemMessage
    import re

    if not terms:
        return []

    # 1. 加载术语翻译 prompt
    prompt = prompt_service.get_prompt_by_name(session, "术语翻译")
    if not prompt or not prompt.template:
        raise ValueError("未找到术语翻译提示词模板")

    raw_prompt = str(prompt.template)

    # 2. 获取项目上下文
    project_context = get_project_context_for_translation(session, project_id)

    # 3. 渲染 prompt 模板
    system_prompt = prompt_service.inject_knowledge(session, raw_prompt)
    # 使用 render_prompt 渲染上下文变量
    system_prompt = prompt_service.render_prompt(
        system_prompt,
        {
            "tags_content": project_context["tags_content"],
            "audience": project_context["audience"],
            "story_overview": project_context["story_overview"],
        }
    )

    # 4. 获取已有翻译用于保证一致性
    glossary_card = session.get(Card, glossary_card_id)
    existing_context = ""
    if glossary_card and glossary_card.content:
        content = glossary_card.content
        if isinstance(content, str):
            import json
            content = json.loads(content)
        if content.get("terms"):
            try:
                existing_glossary = TranslationGlossary(**content)
                existing_context = build_glossary_context(existing_glossary.terms)
            except Exception:
                existing_context = ""

    # 5. 构建用户提示词
    terms_list_text = "\n".join(terms)
    context_hint = f"（参考已有翻译：\n{existing_context}）" if existing_context else ""
    user_prompt = f"""请将以下术语翻译为{target_language}：

{terms_list_text}

{context_hint}

请直接输出翻译结果，每行一个，格式为：原文 → 译名"""

    # 6. 调用 LLM
    model = build_chat_model(
        session=session,
        llm_config_id=llm_config_id,
        temperature=0.3,
        max_tokens=4096,
        timeout=120,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = await model.ainvoke(messages)
    content = getattr(response, "content", response)
    if isinstance(content, list):
        text = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    else:
        text = "" if content is None else str(content)

    # 7. 记录 token 使用
    try:
        in_tokens = calc_input_tokens(system_prompt, user_prompt)
        out_tokens = estimate_tokens(text)
        record_usage(session, llm_config_id, in_tokens, out_tokens, calls=1, aborted=False)
    except Exception:
        pass  # 忽略统计错误

    # 8. 解析翻译结果
    translations = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or "→" not in line:
            continue
        parts = line.split("→", 1)
        if len(parts) == 2:
            source = parts[0].strip()
            translated = parts[1].strip()
            if source and translated:
                translations.append({"source": source, "translated": translated})

    return translations
