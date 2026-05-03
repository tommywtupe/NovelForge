"""通用LLM服务

提供ChatModel构建、结构化生成和续写功能。
"""

from typing import Any, Dict, Type, Optional, AsyncGenerator
from pydantic import BaseModel
from sqlmodel import Session
from loguru import logger
import asyncio
import json

from langchain_core.messages import HumanMessage, SystemMessage
from app.services.ai.generation.continuation_budget_runtime import (
    build_budget_hint_text,
    build_dialogue_hint_text,
    build_round_plan,
    count_text_units,
    estimate_required_call_count,
    normalize_word_control_mode,
    trim_generated_text,
)
from app.services.ai.generation.structured_runtime import (
    generate_structured_via_instruction_flow_model,
)
from app.schemas.ai import ContinuationRequest
from .chat_model_factory import build_chat_model
from .token_utils import calc_input_tokens, estimate_tokens
from .quota_manager import precheck_quota, record_usage


async def generate_structured(
    session: Session,
    llm_config_id: int,
    user_prompt: str,
    output_type: Type[BaseModel],
    system_prompt: Optional[str] = None,
    deps: str = "",
    max_tokens: Optional[int] = None,
    max_retries: int = 3,
    temperature: Optional[float] = None,
    timeout: Optional[float] = None,
    track_stats: bool = True,
    use_instruction_flow: bool = False,
    return_logs: bool = False,
) -> BaseModel | Dict[str, Any]:
    """结构化输出生成
    
    使用LangChain ChatModel的structured output能力。
    
    Args:
        session: 数据库会话
        llm_config_id: LLM配置ID
        user_prompt: 用户提示词
        output_type: 输出Pydantic模型类型
        system_prompt: 系统提示词
        deps: 依赖项（预留）
        max_tokens: 最大token数
        max_retries: 最大重试次数
        temperature: 温度参数
        timeout: 超时时间
        track_stats: 是否记录统计
        
    Returns:
        结构化输出对象
    """
    if use_instruction_flow:
        return await generate_structured_via_instruction_flow_model(
            session=session,
            llm_config_id=llm_config_id,
            user_prompt=user_prompt,
            output_type=output_type,
            system_prompt=system_prompt,
            deps=deps,
            max_tokens=max_tokens,
            max_retries=max_retries,
            temperature=temperature,
            timeout=timeout,
            track_stats=track_stats,
            return_logs=return_logs,
        )

    native_result = await _generate_structured_native(
        session=session,
        llm_config_id=llm_config_id,
        user_prompt=user_prompt,
        output_type=output_type,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        max_retries=max_retries,
        temperature=temperature,
        timeout=timeout,
        track_stats=track_stats,
    )

    if return_logs:
        return {
            "result": native_result,
            "logs": [],
        }

    return native_result


async def generate_review(
    session: Session,
    llm_config_id: int,
    user_prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    timeout: Optional[float] = None,
    track_stats: bool = True,
) -> str:
    """审核文本生成。"""
    if track_stats:
        ok, reason = precheck_quota(
            session, llm_config_id,
            calc_input_tokens(system_prompt, user_prompt),
            need_calls=1
        )
        if not ok:
            raise ValueError(f"LLM配额不足: {reason}")

    try:
        model = build_chat_model(
            session=session,
            llm_config_id=llm_config_id,
            temperature=temperature or 0.7,
            max_tokens=16384 if max_tokens is None else max_tokens,
            timeout=timeout or 150,
        )

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=user_prompt))

        logger.info(f"开始审核，提示词: {system_prompt} \n\n {user_prompt}")
        response = await model.ainvoke(messages)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            text = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        else:
            text = "" if content is None else str(content)

        if not text.strip():
            raise ValueError("LLM返回了空响应")

        if track_stats:
            in_tokens = calc_input_tokens(system_prompt, user_prompt)
            out_tokens = estimate_tokens(text)
            record_usage(
                session, llm_config_id,
                in_tokens, out_tokens,
                calls=1, aborted=False
            )

        return text.strip()
    except asyncio.CancelledError:
        logger.info("[LangChain-Text] LLM调用被取消（CancelledError），立即中止。")
        if track_stats:
            in_tokens = calc_input_tokens(system_prompt, user_prompt)
            record_usage(
                session, llm_config_id,
                in_tokens, 0,
                calls=1, aborted=True
            )
        raise


async def generate_line_by_line_streaming(
    session: Session,
    request,  # LineByLineMode request object
    system_prompt: str,
    track_stats: bool = True,
    max_retries: int = 2,
) -> AsyncGenerator[str, None]:
    """逐行润色/审核流式生成

    Args:
        session: 数据库会话
        request: 逐行请求对象（包含text, mode等）
        system_prompt: 系统提示词（由外部传入，已注入知识库）
        track_stats: 是否记录统计
        max_retries: 单行 LLM 调用最大重试次数

    Yields:
        处理后的文本片段（每行处理完成后yield）
    """
    from app.schemas.ai import LineByLineMode

    # 解析请求参数
    text = request.text
    mode = request.mode
    llm_config_id = request.llm_config_id
    temperature = request.temperature or 0.7
    max_tokens = request.max_tokens or 16384
    timeout = request.timeout or 150
    context_info = request.context_info

    # 按行分割
    lines = text.split('\n')

    # 批次大小（从配置读取，默认8）
    from app.core.config import settings
    batch_size = settings.ai.line_by_line_batch_size
    # 行间分隔符（必须唯一，不出现在内容中）
    SEPARATOR = "\n---LINE_SEPARATOR---\n"

    # 润色模式：记录已润色的前文，用于注入后续批次的 prompt 上下文
    polished_lines: list[str] = []

    total_lines = len(lines)

    # 按批次处理
    for batch_start in range(0, total_lines, batch_size):
        batch_end = min(batch_start + batch_size, total_lines)

        # 收集本批次结果：{line_index: (content, review_comment)}
        batch_results: dict[int, tuple[str, str]] = {}
        # 收集本批次非空行（需要 LLM 处理）
        non_empty_entries: list[tuple[int, str]] = []

        for idx in range(batch_start, batch_end):
            line = lines[idx]
            if not line.strip():
                # 空行直接记录，不消耗 LLM 调用
                batch_results[idx] = (line, "")
            else:
                non_empty_entries.append((idx, line))

        # 如果有非空行需要处理，调用 LLM（整个批次一次）
        if non_empty_entries:
            # 构建多行批次的用户提示词
            user_prompt_parts = []

            # 添加上下文
            if context_info:
                user_prompt_parts.append(f"【引用上下文】\n{context_info}")

            # 添加本批次所有待处理行（带行号标注）
            batch_lines_text = "\n".join(
                f"[{orig_idx + 1}] {line}" for orig_idx, line in non_empty_entries
            )
            batch_first = non_empty_entries[0][0] + 1
            batch_last = non_empty_entries[-1][0] + 1
            user_prompt_parts.append(f"【待处理行 {batch_first}-{batch_last}/{total_lines}】\n{batch_lines_text}")

            if mode == "polish":
                # 注入已润色的前文（之前所有批次的结果）
                if polished_lines:
                    polished_context = "\n".join(
                        f"{pi + 1} | {pl}" for pi, pl in enumerate(polished_lines)
                    )
                    user_prompt_parts.append(f"【已润色前文】\n{polished_context}")
                user_prompt_parts.append(
                    f"\n【指令】请按顺序润色以上{len(non_empty_entries)}行内容，并对每一行进行审核。"
                    f"每行输出格式：先输出润色后文本，换行后输出 <<<REVIEW>>>审核结果。"
                    f"审核结果说明：如该行无问题输出 'pass'，如存在问题输出 'revise: 修改建议 | 原文'。"
                    f"各行之间用 ---LINE_SEPARATOR--- 分隔。"
                    f"只输出上述格式内容，不要编号、不要额外解释。\n"
                    f"示例输出：\n"
                    f"润色后的第一行\n<<<REVIEW>>>pass\n"
                    f"---LINE_SEPARATOR---\n"
                    f"润色后的第二行\n<<<REVIEW>>>revise: 逻辑冲突，角色已死亡 | 修正后的第二行"
                )
            else:
                user_prompt_parts.append(
                    f"\n【指令】请按顺序审核以上{len(non_empty_entries)}行内容。"
                    f"每行审核结果之间用 ---LINE_SEPARATOR--- 分隔。"
                    f"只输出审核结果（'pass' 或 'revise: 修改建议 | 内容'），不要编号、不要解释。"
                )

            batch_prompt = "\n".join(user_prompt_parts)

            # 配额预检
            if track_stats:
                ok, reason = precheck_quota(
                    session, llm_config_id,
                    calc_input_tokens(system_prompt, batch_prompt),
                    need_calls=1
                )
                if not ok:
                    raise ValueError(f"LLM配额不足: {reason}")

            # 构建模型和消息
            model = build_chat_model(
                session=session,
                llm_config_id=llm_config_id,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=batch_prompt)
            ]

            # 调试日志
            logger.info(f"[逐行处理] 批次 行{batch_first}-{batch_last}/{total_lines} ========== User Prompt ==========")
            logger.info(f"{batch_prompt}")
            logger.info(f"[逐行处理] 批次 行{batch_first}-{batch_last}/{total_lines} ========== End User Prompt ==========")

            # 调用LLM（含重试）
            raw_response = ""
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    response = await model.ainvoke(messages)
                    content = getattr(response, "content", response)

                    logger.info(f"[逐行处理] 批次 行{batch_first}-{batch_last}/{total_lines} ========== Response Body ==========")
                    logger.info(f"{content}")
                    logger.info(f"[逐行处理] 批次 行{batch_first}-{batch_last}/{total_lines} ========== End Response Body ==========")

                    if isinstance(content, list):
                        raw_response = "".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in content
                        )
                    else:
                        raw_response = "" if content is None else str(content)

                    raw_response = raw_response.strip()
                    break  # 成功，退出重试循环
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        logger.warning(
                            f"[逐行处理] 批次 行{batch_first}-{batch_last} LLM 调用失败 "
                            f"(attempt {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        await asyncio.sleep(1.0 * (attempt + 1))
                    else:
                        logger.error(
                            f"[逐行处理] 批次 行{batch_first}-{batch_last} LLM 调用全部失败: {e}"
                        )
                        raise
            else:
                # 所有重试均失败
                raise last_error  # type: ignore[misc]

            # 按分隔符拆分批次响应为各行的处理结果
            processed_segments = [seg.strip() for seg in raw_response.split(SEPARATOR)]

            # 检查分段数是否匹配
            expected_count = len(non_empty_entries)
            if len(processed_segments) != expected_count:
                logger.warning(
                    f"[逐行处理] 批次 行{batch_first}-{batch_last} 解析异常: "
                    f"预期{expected_count}段，实际{len(processed_segments)}段，回退使用原文"
                )
                # 回退：使用原文
                for orig_idx, original_line in non_empty_entries:
                    batch_results[orig_idx] = (original_line, "")
            else:
                # 逐行解析处理结果
                processed_total_out_tokens = 0
                for (orig_idx, original_line), processed_segment in zip(non_empty_entries, processed_segments):
                    processed_line = processed_segment
                    review_comment = ""

                    # 审核模式：提取审核建议
                    if mode == "review":
                        if processed_line.lower() == "pass":
                            processed_line = original_line
                        elif processed_line.startswith("revise:"):
                            parts = processed_line.split("|", 1)
                            if len(parts) >= 2:
                                review_comment = parts[0].replace("revise:", "").strip()
                                processed_line = parts[1].strip()

                    # 润色模式：从响应中提取润色文本和审核子结果
                    if mode == "polish":
                        if "<<<REVIEW>>>" in processed_segment:
                            seg_parts = processed_segment.split("<<<REVIEW>>>", 1)
                            processed_line = seg_parts[0].strip()
                            review_raw = seg_parts[1].strip()
                            if review_raw.startswith("revise:"):
                                r_parts = review_raw.split("|", 1)
                                if len(r_parts) >= 2:
                                    review_comment = r_parts[0].replace("revise:", "").strip()
                            # "pass" or anything else -> review_comment stays ""
                        else:
                            processed_line = processed_segment

                        # 将处理后的行加入前文上下文
                        polished_lines.append(processed_line)

                    batch_results[orig_idx] = (processed_line, review_comment)
                    processed_total_out_tokens += estimate_tokens(processed_line)

                # 记录用量（整个批次一次）
                if track_stats:
                    in_tokens = calc_input_tokens(system_prompt, batch_prompt)
                    record_usage(
                        session, llm_config_id,
                        in_tokens, processed_total_out_tokens,
                        calls=1, aborted=False
                    )

        # 按索引顺序 yield 本批次所有行的结果
        for idx in range(batch_start, batch_end):
            content, review_comment = batch_results[idx]
            yield f"data: {json.dumps({'index': idx, 'content': content, 'original': lines[idx], 'review_comment': review_comment}, ensure_ascii=False)}\n\n"


async def _generate_structured_native(
    *,
    session: Session,
    llm_config_id: int,
    user_prompt: str,
    output_type: Type[BaseModel],
    system_prompt: Optional[str],
    max_tokens: Optional[int],
    max_retries: int,
    temperature: Optional[float],
    timeout: Optional[float],
    track_stats: bool,
) -> BaseModel:
    """原生结构化输出实现（LangChain with_structured_output）。"""

    # 配额预检
    if track_stats:
        ok, reason = precheck_quota(
            session, llm_config_id,
            calc_input_tokens(system_prompt, user_prompt),
            need_calls=1
        )
        if not ok:
            raise ValueError(f"LLM配额不足: {reason}")

    last_exception = None
    for attempt in range(max_retries):
        try:
            model = build_chat_model(
                session=session,
                llm_config_id=llm_config_id,
                temperature=temperature or 0.7,
                max_tokens=131072 if max_tokens is None else max_tokens,
                timeout=timeout or 150,
                thinking_enabled=False,  
                # reasoning_effort="max", 
            )

            structured_llm = model.with_structured_output(output_type)

            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=user_prompt))

            response = await structured_llm.ainvoke(messages)

            if response is None:
                raise ValueError("LLM返回了空响应")

            logger.info(f"[LangChain-Structured] response: {response}")

            if track_stats:
                in_tokens = calc_input_tokens(system_prompt, user_prompt)
                try:
                    out_text = (
                        response
                        if isinstance(response, str)
                        else json.dumps(response, ensure_ascii=False)
                    )
                except Exception:
                    out_text = str(response)
                out_tokens = estimate_tokens(out_text)
                record_usage(
                    session, llm_config_id,
                    in_tokens, out_tokens,
                    calls=1, aborted=False
                )

            return response

        except asyncio.CancelledError:
            logger.info("[LangChain-Structured] LLM调用被取消（CancelledError），立即中止，不再重试。")
            if track_stats:
                in_tokens = calc_input_tokens(system_prompt, user_prompt)
                record_usage(
                    session, llm_config_id,
                    in_tokens, 0,
                    calls=1, aborted=True
                )
            raise
        except Exception as e:
            last_exception = e
            logger.warning(
                f"[LangChain-Structured] 调用失败，重试 {attempt + 1}/{max_retries}，llm_config_id={llm_config_id}: {e}"
            )

            if attempt < max_retries - 1:
                retry_delay = min(2 ** attempt, 4)
                logger.info(f"[LangChain-Structured] 等待 {retry_delay} 秒后重试...")
                await asyncio.sleep(retry_delay)

    logger.error(
        f"[LangChain-Structured] 调用在重试 {max_retries} 次后仍失败，llm_config_id={llm_config_id}. Last error: {last_exception}"
    )
    raise ValueError(
        f"调用LLM服务失败，已重试 {max_retries} 次: {str(last_exception)}"
    )


async def generate_continuation_streaming(
    session: Session,
    request: ContinuationRequest,
    system_prompt: str,
    track_stats: bool = True
) -> AsyncGenerator[str, None]:
    """续写流式生成
    
    Args:
        session: 数据库会话
        request: 续写请求对象
        system_prompt: 系统提示词（由外部传入）
        track_stats: 是否记录统计
        
    Yields:
        生成的文本片段
    """
    current_word_count = getattr(request, "existing_word_count", None)
    if current_word_count is None:
        current_word_count = count_text_units(getattr(request, "previous_content", ""))

    control_mode = normalize_word_control_mode(request)
    expected_rounds = estimate_required_call_count(request)
    if control_mode == "prompt_only" or expected_rounds <= 1:
        round_plan = build_round_plan(request, current_word_count, 1)
        async for chunk in _stream_continuation_single_round(
            session=session,
            request=request,
            system_prompt=system_prompt,
            round_plan=round_plan,
            track_stats=track_stats,
        ):
            yield chunk
        return

    current_content = request.previous_content or ""

    for round_index in range(1, expected_rounds + 1):
        round_plan = build_round_plan(request, current_word_count, round_index)
        round_request = request.model_copy(update={
            "previous_content": current_content,
            "existing_word_count": current_word_count,
            "word_control_mode": control_mode,
            "budget_round_hint": round_plan.round_index,
            "remaining_word_count_hint": round_plan.remaining_word_count,
            "is_final_round_hint": round_plan.is_final_round,
        })

        round_chunks: list[str] = []
        
        async for chunk in _stream_continuation_single_round(
            session=session,
            request=round_request,
            system_prompt=system_prompt,
            round_plan=round_plan,
            track_stats=track_stats,
        ):

            round_chunks.append(chunk)
            if getattr(request, "stream", False):
                yield chunk

        round_text = "".join(round_chunks)

        if not round_text.strip():
            logger.warning("续写预算运行时在第 {} 轮拿到空输出，提前结束。", round_index)
            break

        trim_result = trim_generated_text(round_text, round_plan)
        final_text = round_text if getattr(request, "stream", False) else trim_result.text
        if not final_text.strip():
            logger.warning("续写预算运行时在第 {} 轮裁剪后为空，提前结束。", round_index)
            break

        current_content = f"{current_content}{final_text}"
        current_word_count = count_text_units(current_content)

        if not getattr(request, "stream", False):
            for chunk in _chunk_text(final_text):
                yield chunk

        target_word_count = getattr(request, "target_word_count", None)
        if trim_result.trimmed and not getattr(request, "stream", False):
            logger.info("续写预算运行时在第 {} 轮触发句边界收束。", round_index)
            break
        if target_word_count is not None and current_word_count >= target_word_count:
            break
        if round_plan.is_final_round:
            break


def _parse_beat_list(request) -> Optional[list[dict]]:
    """解析 request.beat_list_json 为完整节拍列表"""
    raw = getattr(request, "beat_list_json", None)
    if not raw:
        return None
    try:
        beat_list = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(beat_list, list):
        return None
    return beat_list


def _build_continuation_user_prompt(
    request: ContinuationRequest,
    round_plan,
) -> str:
    # 组装用户消息
    user_prompt_parts = []
    
    # 1. 添加上下文信息（引用上下文 + 事实子图）
    context_info = (getattr(request, 'context_info', None) or '').strip()
    if context_info:
        # 检测context_info是否已包含结构化标记
        has_structured_marks = any(
            mark in context_info 
            for mark in ['【引用上下文】', '【上文】', '【需要润色', '【需要扩写']
        )
        
        if has_structured_marks:
            # 已经是结构化的上下文，直接使用
            user_prompt_parts.append(context_info)
        else:
            # 未结构化的上下文（老格式），添加标记
            user_prompt_parts.append(f"【参考上下文】\n{context_info}")
    
    # 2. 添加已有章节内容（仅当previous_content非空时）
    previous_content = (request.previous_content or '').strip()
    if previous_content:
        user_prompt_parts.append(f"【已有章节内容】\n{previous_content}")
        
        # 续写指令
        if getattr(request, 'append_continuous_novel_directive', True):
            user_prompt_parts.append("【指令】请接着上述内容继续写作，保持文风和剧情连贯。直接输出小说正文。")
    else:
        # 新写模式或润色/扩写模式（previous_content为空）
        if getattr(request, 'append_continuous_novel_directive', True):
            if context_info and '【已有章节内容】' in context_info:
                user_prompt_parts.append("【指令】请接着上述内容继续写作，保持文风和剧情连贯。直接输出小说正文。")
            else:
                user_prompt_parts.append("【指令】请开始创作新章节。直接输出小说正文。")

    beat_list = _parse_beat_list(request)
    budget_hint = build_budget_hint_text(round_plan, getattr(request, "continuation_guidance", None), beat_list)
    if budget_hint:
        user_prompt_parts.append(budget_hint)

    #追加对白质量提示
    dialogue_hint = build_dialogue_hint_text(round_plan)
    if dialogue_hint:
        user_prompt_parts.append(dialogue_hint)

    return "\n\n".join(user_prompt_parts)


async def _stream_continuation_single_round(
    session: Session,
    request: ContinuationRequest,
    system_prompt: str,
    round_plan,
    track_stats: bool = True,
) -> AsyncGenerator[str, None]:
    user_prompt = _build_continuation_user_prompt(request, round_plan)

    # 限额预检
    if track_stats:
        ok, reason = precheck_quota(
            session, request.llm_config_id,
            calc_input_tokens(system_prompt, user_prompt),
            need_calls=1
        )
        if not ok:
            raise ValueError(f"LLM配额不足: {reason}")

    # 使用LangChain ChatModel进行流式续写
    # balanced + 非终轮：使用 hard_word_limit 作为 max_tokens（*2.4 转为 token 数）
    _max_tokens = round_plan.max_tokens
    if round_plan.mode != "prompt_only" and round_plan.hard_word_limit is not None:
        _max_tokens = int(round_plan.hard_word_limit * 2.4)
    model = build_chat_model(
        session=session,
        llm_config_id=request.llm_config_id,
        temperature=request.temperature or 0.7,
        max_tokens=_max_tokens,
        timeout=request.timeout or 64,
        thinking_enabled=True,
        reasoning_effort="max",
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    
    logger.info(f"开始续写，提示词: {system_prompt} \n\n {user_prompt}")

    accumulated: str = ""
    pending_buffer: str = ""
    stream_with_hard_limit = bool(
        getattr(request, "stream", False)
        and round_plan.mode != "prompt_only"
        and not round_plan.is_final_round
        and round_plan.hard_word_limit
    )
    should_stop_current_round = False

    print(f"[DEBUG 硬截断模式] stream={getattr(request, 'stream', False)}, mode={round_plan.mode}, is_final={round_plan.is_final_round}, hard_limit={round_plan.hard_word_limit}, max_tokens={round_plan.max_tokens}")

    try:
        logger.debug("正在以LangChain ChatModel流式生成续写内容")
        async for chunk in model.astream(messages):
            content = getattr(chunk, "content", None)
            if not content:
                continue

            if isinstance(content, str):
                delta = content
            elif isinstance(content, list):
                texts = [
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                ]
                delta = "".join(texts)
            else:
                delta = str(content)

            if not delta:
                continue

            # [SIMPLE FIX] 只检测完整标记，用于提前终止
            BEAT_END_MARKER = "<节拍完成>"
            if BEAT_END_MARKER in delta:
                parts = delta.split(BEAT_END_MARKER, 1)
                text_before_marker = parts[0]
                print(f"[DEBUG <节拍完成>] 检测到完整标记, 标记前文本长度={len(text_before_marker)}")
                if text_before_marker:
                    accumulated += text_before_marker
                    yield text_before_marker
                print(f"[DEBUG <节拍完成>] 本轮结束, accumulated_len={len(accumulated)}")
                should_stop_current_round = True
                break

            if stream_with_hard_limit:
                pending_buffer += delta
                # emitted_text, pending_buffer, reached_limit = _flush_streaming_buffer_with_limit(
                #     already_emitted=accumulated,
                #     pending_text=pending_buffer,
                #     hard_limit=round_plan.hard_word_limit or 0,
                # )
                emitted_text, pending_buffer, _ = _flush_streaming_buffer_with_limit(
                    already_emitted=accumulated,
                    pending_text=pending_buffer,
                    hard_limit=round_plan.hard_word_limit or 0,
                )
                reached_limit = False
                print(f"[DEBUG yield硬截断] emitted_text={repr(emitted_text[:50]) if emitted_text else '空'}, accumulated_len={len(accumulated)}, hard_limit={round_plan.hard_word_limit}")
                if emitted_text:
                    accumulated += emitted_text
                    yield emitted_text
                # if reached_limit:
                #     should_stop_current_round = True
                #     break
                continue

            accumulated += delta
            print(f"[DEBUG yield] delta={repr(delta[:50]) if delta else '空'}, accumulated_len={len(accumulated)}")
            yield delta

        if stream_with_hard_limit and not should_stop_current_round and pending_buffer:
            # emitted_tail, pending_buffer, reached_limit = _flush_streaming_buffer_with_limit(
            #     already_emitted=accumulated,
            #     pending_text=pending_buffer,
            #     hard_limit=round_plan.hard_word_limit or 0,
            #     force_flush_tail=True,
            # )
            emitted_tail, pending_buffer, _ = _flush_streaming_buffer_with_limit(
                already_emitted=accumulated,
                pending_text=pending_buffer,
                hard_limit=round_plan.hard_word_limit or 0,
                force_flush_tail=True,
            )
            reached_limit = False
            print(f"[DEBUG yield尾部刷新] emitted_tail={repr(emitted_tail[:50]) if emitted_tail else '空'}, accumulated_len={len(accumulated)}")
            if emitted_tail:
                accumulated += emitted_tail
                yield emitted_tail

    except asyncio.CancelledError:
        logger.info("流式LLM调用被取消（CancelledError），停止推送。")
        if track_stats:
            in_tokens = calc_input_tokens(system_prompt, user_prompt)
            out_tokens = estimate_tokens(accumulated)
            record_usage(
                session, request.llm_config_id,
                in_tokens, out_tokens,
                calls=1, aborted=True
            )
        return
    except Exception as e:
        logger.error(f"流式LLM调用失败: {e}")
        raise

    # 正常结束后统计
    try:
        if track_stats:
            in_tokens = calc_input_tokens(system_prompt, user_prompt)
            out_tokens = estimate_tokens(accumulated)
            record_usage(
                session, request.llm_config_id,
                in_tokens, out_tokens,
                calls=1, aborted=False
            )
    except Exception as stat_e:
        logger.warning(f"记录LLM流式统计失败: {stat_e}")


async def _collect_continuation_single_round(
    session: Session,
    request: ContinuationRequest,
    system_prompt: str,
    round_plan,
    track_stats: bool = True,
) -> str:
    chunks: list[str] = []
    async for chunk in _stream_continuation_single_round(
        session=session,
        request=request,
        system_prompt=system_prompt,
        round_plan=round_plan,
        track_stats=track_stats,
    ):
        chunks.append(chunk)
    return "".join(chunks)


def _chunk_text(text: str, chunk_size: int = 240) -> list[str]:
    if not text:
        return []
    return [text[index:index + chunk_size] for index in range(0, len(text), chunk_size)]


def _flush_streaming_buffer_with_limit(
    *,
    already_emitted: str,
    pending_text: str,
    hard_limit: int,
    force_flush_tail: bool = False,
) -> tuple[str, str, bool]:
    print(f"[DEBUG _flush] 入参: 已发送长度={len(already_emitted)}, 待处理长度={len(pending_text)}, 硬限制={hard_limit}, 强制尾部={force_flush_tail}")
    if not pending_text:
        print("[DEBUG _flush] 出参: 待处理为空，直接返回空")
        return "", "", False

    emitted_parts: list[str] = []
    rest = pending_text

    while True:
        sentence_end = _find_first_sentence_boundary(rest)
        if sentence_end is None:
            print(f"[DEBUG _flush] 循环中断: 无更多句子边界，剩余长度={len(rest)}")
            break
        sentence = rest[:sentence_end]
        next_text = already_emitted + "".join(emitted_parts) + sentence
        next_units = count_text_units(next_text)
        print(f"[DEBUG _flush] 句子={repr(sentence[:50])}, 下一句字数={next_units}, 硬限制={hard_limit}")
        if next_units > hard_limit:
            print(f"[DEBUG _flush] 出参: 超过硬限制，返回 {len(emitted_parts)} 个句子，剩余长度={len(rest)}")
            return "".join(emitted_parts), rest, True
        emitted_parts.append(sentence)
        rest = rest[sentence_end:]

    if force_flush_tail and rest:
        next_text = already_emitted + "".join(emitted_parts) + rest
        next_units = count_text_units(next_text)
        print(f"[DEBUG _flush] 尾部刷新: 剩余长度={len(rest)}, 下一句字数={next_units}")
        if next_units <= hard_limit:
            emitted_parts.append(rest)
            rest = ""
            print(f"[DEBUG _flush] 出参: 尾部刷新成功，全部发出")
        elif not emitted_parts:
            available = hard_limit - count_text_units(already_emitted)
            print(f"[DEBUG _flush] 出参: 无已发送句子，可用字数={available}")
            truncated = _take_text_by_units(rest, available)
            return truncated, "", True
        else:
            print(f"[DEBUG _flush] 出参: 部分发送 {len(emitted_parts)} 个句子，剩余长度={len(rest)}")
            return "".join(emitted_parts), rest, True

    print(f"[DEBUG _flush] 出参: 正常返回，已发送句子={len(emitted_parts)}, 剩余长度={len(rest)}")
    return "".join(emitted_parts), rest, False


def _find_first_sentence_boundary(text: str) -> int | None:
    for idx, char in enumerate(text):
        if char in "。！？!?…\n":
            return idx + 1
    return None


def _take_text_by_units(text: str, limit_units: int) -> str:
    if limit_units <= 0:
        return ""
    units = 0
    out_chars: list[str] = []
    for char in text:
        if not char.isspace():
            units += 1
        if units > limit_units:
            break
        out_chars.append(char)
    return "".join(out_chars).rstrip()
