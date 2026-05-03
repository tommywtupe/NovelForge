from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Optional

from app.schemas.ai import ContinuationRequest


_SENTENCE_ENDINGS = "。！？!?…\n"


@dataclass(frozen=True)
class ContinuationRoundPlan:
    mode: str
    round_index: int
    max_rounds: int
    rounds_left: int
    current_word_count: int
    target_word_count: Optional[int]
    remaining_word_count: Optional[int]
    suggested_word_count: Optional[int]
    is_final_round: bool
    max_tokens: Optional[int]
    hard_word_limit: Optional[int]
    should_warn_wrap_up: bool


@dataclass(frozen=True)
class BeatInfo:
    beat_id: int
    beat_action: str
    beat_subtext_action: Optional[str] = None
    turning_point: bool = False


@dataclass(frozen=True)
class ContinuationTrimResult:
    text: str
    trimmed: bool


def count_text_units(text: str | None) -> int:
    return len("".join((text or "").split()))


def normalize_word_control_mode(request: ContinuationRequest) -> str:
    raw_mode = str(getattr(request, "word_control_mode", "") or "").strip().lower()
    target_word_count = getattr(request, "target_word_count", None)

    if raw_mode not in {"prompt_only", "balanced"}:
        raw_mode = "balanced" if target_word_count else "prompt_only"

    if not target_word_count and raw_mode != "prompt_only":
        return "prompt_only"
    return raw_mode


def estimate_required_call_count(request: ContinuationRequest) -> int:
    mode = normalize_word_control_mode(request)
    if mode == "prompt_only":
        return 1

    current_word_count = _resolve_current_word_count(request)
    remaining_word_count = _resolve_remaining_word_count(request, current_word_count)
    return _estimate_round_count_from_remaining(mode, remaining_word_count)


def build_round_plan(
    request: ContinuationRequest,
    current_word_count: int,
    round_index: int,
) -> ContinuationRoundPlan:
    print(f"[DEBUG build_round_plan] 入参: current_word_count={current_word_count}, round_index={round_index}, target={getattr(request, 'target_word_count', None)}, max_tokens={getattr(request, 'max_tokens', None)}")
    mode = normalize_word_control_mode(request)
    target_word_count = getattr(request, "target_word_count", None)
    remaining_word_count = _resolve_remaining_word_count(request, current_word_count)
    max_rounds = _estimate_round_cap(mode, target_word_count, current_word_count)
    print(f"[DEBUG build_round_plan] 基础参数: mode={mode}, target_word_count={target_word_count}, remaining_word_count={remaining_word_count}, max_rounds={max_rounds}")

    if mode == "prompt_only":
        print(f"[DEBUG build_round_plan] 模式=prompt_only，直接返回单轮计划")
        return ContinuationRoundPlan(
            mode=mode,
            round_index=1,
            max_rounds=1,
            rounds_left=1,
            current_word_count=current_word_count,
            target_word_count=target_word_count,
            remaining_word_count=remaining_word_count,
            suggested_word_count=remaining_word_count if remaining_word_count > 0 else None,
            is_final_round=True,
            max_tokens=request.max_tokens,
            hard_word_limit=None,
            should_warn_wrap_up=False,
        )

    rounds_left = max(1, max_rounds - round_index + 1)
    effective_remaining = remaining_word_count if remaining_word_count > 0 else 280
    close_mode = effective_remaining <= 0  # [MODIFIED] 只有剩余为0时才close，否则全部用advance均匀分配
    print(f"[DEBUG build_round_plan] 多轮模式: rounds_left={rounds_left}, effective_remaining={effective_remaining}, close_mode={close_mode}")

    if close_mode:
        suggested_word_count = _plan_close_suggestion(
            remaining_word_count=effective_remaining,
            rounds_left=rounds_left,
        )
        is_final_round = rounds_left == 1
        print(f"[DEBUG build_round_plan] close_mode策略: suggested_word_count={suggested_word_count}, is_final_round={is_final_round}")
    else:
        advance_rounds_left = rounds_left  # [MODIFIED] 均匀分配给所有轮次
        suggested_word_count = _plan_advance_suggestion(
            remaining_word_count=effective_remaining,
            advance_rounds_left=advance_rounds_left,
        )
        is_final_round = (rounds_left == 1)  # [MODIFIED] 只有rounds_left=1才是最终轮
        print(f"[DEBUG build_round_plan] advance_mode策略: advance_rounds_left={advance_rounds_left}, suggested_word_count={suggested_word_count}, is_final_round={is_final_round}")

    max_tokens = _resolve_round_max_tokens(request.max_tokens, suggested_word_count, mode)
    print(f"[DEBUG build_round_plan] max_tokens计算: request.max_tokens={request.max_tokens}, suggested_word_count={suggested_word_count}, 结果={max_tokens}")

    hard_word_limit = None if is_final_round else _resolve_round_hard_limit(
        suggested_word_count=suggested_word_count,
        remaining_word_count=effective_remaining,
        mode=mode,
    )
    print(f"[DEBUG build_round_plan] hard_word_limit: is_final_round={is_final_round}, 结果={hard_word_limit}")

    print(f"[DEBUG build_round_plan] 出参: round_index={round_index}, max_rounds={max_rounds}, rounds_left={rounds_left}, suggested_word_count={suggested_word_count}, hard_word_limit={hard_word_limit}")
    return ContinuationRoundPlan(
        mode=mode,
        round_index=round_index,
        max_rounds=max_rounds,
        rounds_left=rounds_left,
        current_word_count=current_word_count,
        target_word_count=target_word_count,
        remaining_word_count=remaining_word_count,
        suggested_word_count=suggested_word_count,
        is_final_round=is_final_round,
        max_tokens=max_tokens,
        hard_word_limit=hard_word_limit,
        should_warn_wrap_up=(not is_final_round and rounds_left <= 3),
    )


def build_dialogue_hint_text(plan: ContinuationRoundPlan) -> str:
    """构建对白质量标准提示（仅在 balanced 模式下使用）

    根据轮次百分比调整对白提示的重点：
    - 前25%轮次：强调冲突张力、角色声音个体化
    - 25%-50%轮次：强调三功能、微限冲突
    - 50%-75%轮次：非直接冲突（收尾前铺垫）
    - 75%-100%轮次：自反性冲突（收尾/情感高潮）
    """
    lines = ["【对白质量标准】"]

    # 计算当前轮次在总轮次中的比例
    round_ratio = plan.round_index / max(plan.max_rounds, 1)

    # 对白三功能（所有轮次都适用）
    lines.append("■ 每句重要对白至少满足一个功能：")
    lines.append("  - 揭示人物：语言风格/话题选择/潜台词")
    lines.append("  - 推进行动：话语改变现状，向高潮移动")
    lines.append("  - 建立主题：承载主题但不直接说出")

    # 角色声音个体化（前25%轮次）
    if round_ratio <= 0.25:
        lines.append("■ 角色声音：不同角色词彙/句式/话题偏好须有明显差异")
        lines.append("  测试：删除说话者标签，能否分辨是谁说的？")

    # 微限冲突（25%-50%轮次）
    if 0.25 < round_ratio <= 0.50:
        lines.append("■ 微限冲突：每句对白之间须有微小张力变化")
        lines.append("  - 来回之间制造犹豫、停顿、打断")
        lines.append("  - 让对白像乒乓球来回，而非网球")

    # 非直接冲突（50%-75%轮次）
    if 0.50 < round_ratio <= 0.75:
        lines.append("■ 非直接冲突：适当使用沉默、绕弯子、替代话题")
        lines.append("  - 有时不说不比说更有力量")

    # 自反性冲突（75%-100%轮次，收尾/情感高潮）
    if round_ratio > 0.75:
        lines.append("■ 自反性冲突：角色内心挣扎须有体现")
        lines.append("  - 可用半句、沉默、内心独白表达")

    # 收尾轮特别注意
    if plan.is_final_round:
        lines.append("■ 收尾对白：自然结束，不过度解释，留余味")

    # 禁止清单（所有轮次）
    lines.append("■ 禁止：")
    lines.append("  - 角色解释自己行为（应让行动自明）")
    lines.append("  - 对白中介绍已知信息（历史倒叙）")
    lines.append("  - 每句都是完整陈述句（要有省略、打断）")
    lines.append("  - 直接说出主题（应让主题涌现）")

    return "\n".join(lines)


def build_budget_hint_text(
    plan: ContinuationRoundPlan,
    continuation_guidance: str | None = None,
    beat_list: Optional[list[dict]] = None,
) -> str:
    # 从完整 beat_list 中提取当前节拍和上一节拍
    current_beat: Optional[BeatInfo] = None
    previous_beat: Optional[BeatInfo] = None
    if beat_list:
        idx = plan.round_index - 1
        if 0 <= idx < len(beat_list):
            b = beat_list[idx]
            current_beat = BeatInfo(
                beat_id=b.get("beat_id", idx + 1),
                beat_action=b.get("beat_action", ""),
                beat_subtext_action=b.get("beat_subtext_action"),
                turning_point=b.get("turning_point", False),
            )
        # 非首个节拍时提取上一节拍
        if plan.round_index != 1:
            prev_idx = idx - 1
            if 0 <= prev_idx < len(beat_list):
                pb = beat_list[prev_idx]
                previous_beat = BeatInfo(
                    beat_id=pb.get("beat_id", prev_idx + 1),
                    beat_action=pb.get("beat_action", ""),
                    beat_subtext_action=pb.get("beat_subtext_action"),
                    turning_point=pb.get("turning_point", False),
                )

    lines: list[str] = ["【续写预算】", f"- 当前总字数：{plan.current_word_count} 字"]

    if plan.target_word_count is not None:
        lines.append(f"- 目标总字数：{plan.target_word_count} 字")
    # if plan.remaining_word_count is not None:
    #     lines.append(f"- 剩余字数：约 {max(plan.remaining_word_count, 0)} 字")
    if plan.mode != "prompt_only":
        if plan.is_final_round:
            lines.append(f"- 当前节拍：第 {plan.round_index} 节拍 / 共 {plan.max_rounds} 节拍（收尾节拍），本轮将处理本章最后一个节拍，请忽略字数限制，确保所有重点都被充分展开，并配以完美的结尾， 并参考该节拍的动作和潜文本动作，以及本节拍是否本章的转折点。承接上一节拍的正文结尾确保转场自然、情绪连贯")
        elif plan.round_index == 1:
            lines.append(f"- 当前节拍：第 {plan.round_index} 节拍 / 共 {plan.max_rounds} 节拍，这是本章第{plan.round_index} 节拍(beat_id:{plan.round_index} )，需要承接上一话最后一个节拍的正文结尾，并参考第 {plan.round_index} 节拍的动作和潜文本动作。确保转场自然、情绪连贯")
            lines.append("- 章节开头要求：请从以下五个叙述维度之一出发构建开篇：")
            lines.append("  1. 【私人记忆 | Private Anchor】挖掘角色过往与核心主题的矛盾锚点，通过带有主观色彩的回忆或执念带出世界观独特设定")
            lines.append("  2. 【异质现象 | Phenomenon】描写打破常规、具有跨领域冲击力的事实或视觉奇观，呈现让读者产生'为什么会这样'的违和画面")
            lines.append("  3. 【核心拷问 | Fatal Question】抛出叙述者或主角灵魂深处真正想要刺破的真相，带有命运感的终极困惑，定义故事基调")
            lines.append("  4. 【沉浸场景 | Immersive Scene】定格极具张力的瞬间（特定时间+地点+行动中的人物），利用五感细节快速建立现场感")
            lines.append("  5. 【第一句话 | The Hook】孤立的一行文字，具有极强文学爆发力或反直觉陈述，用一句话确立叙事风格并钩住读者")
        else:
            lines.append(f"- 当前节拍：第 {plan.round_index} 节拍 / 共 {plan.max_rounds} 节拍，本轮将处理本章第 {plan.round_index} 节拍(beat_id:{plan.round_index} )，并参考该节拍的动作和潜文本动作，以及本节拍是否本章的转折点。承接上一节拍的正文结尾确保转场自然、情绪连贯")
    if plan.suggested_word_count is not None and plan.mode != "prompt_only":
        lines.append(f"- 本轮建议规模：约 {plan.suggested_word_count} 字")
        # lines.append(f"- 本轮建议规模：约 800 字")
    if plan.hard_word_limit is not None:
        lines.append(f"- 本轮硬上限：约 {plan.hard_word_limit} 字（超出会提前停轮）")
        # lines.append(f"- 本轮硬上限：约 800 字（超出会提前停轮）")

    guidance = (continuation_guidance or "").strip()
    if guidance:
        lines.append(f"- 续写指导：{guidance}")

    if plan.mode == "prompt_only":
        lines.append("- 当前为提示词约束模式：目标字数仅作参考，以文风和连贯性优先。")
    else:
        lines.append("- 当前为智能字数控制模式：前两轮优先推进剧情，后续逐步收束字数并完成结尾。")

    # 注入当前节拍的具体内容
    if current_beat is not None:
        lines.append(f"- 节拍动作：{current_beat.beat_action}")
        if current_beat.beat_subtext_action:
            lines.append(f"- 潜文本动作：{current_beat.beat_subtext_action}")
        if current_beat.turning_point:
            lines.append("本章关键转折，需充分展开并自然收束")


    # 注入上一节拍的参考内容（非首个节拍时）
    if previous_beat is not None:
        lines.append("")
        lines.append("【上一节拍参考】")
        lines.append(f"- 上一节拍动作：{previous_beat.beat_action}")
        if previous_beat.beat_subtext_action:
            lines.append(f"- 上一节拍潜文本动作：{previous_beat.beat_subtext_action}")
        if previous_beat.turning_point:
            lines.append("- 上一节拍是关键转折")


    if plan.should_warn_wrap_up:
        if plan.rounds_left >= 3:
            lines.append("- 已进入最后一千字的收尾阶段：请开始压缩支线、回收信息，并为后续的收尾节奏预留空间。")
        elif plan.rounds_left == 2:
            lines.append("- 只剩最后两轮：请明显加快收束节奏，不要再开启新支线，并把最后一轮尽量压到约 100 字。")

    if plan.mode != "prompt_only" and plan.is_final_round:
        lines.append("- 这是最后一轮：请只做结尾收束，严控字数，不要开启新支线，不要明显超出预算；结尾要自然，并保留余味或轻微悬念。")

    # [NEW] 节拍写作协议
    if plan.mode != "prompt_only":
        lines.append("")
        lines.append("【节拍写作协议】")
        lines.append("1. 严格按本轮节拍范围写作，不得跨节拍提前写下一节拍内容")
        lines.append("2. 当本轮字数达到上限或节拍内容完成时，必须输出 <节拍完成> 标记")
        lines.append("3. 标记出现后立即停止输出，等待下一轮指令")
        lines.append("4. <节拍完成> 标记仅作为结束信号，不会出现在正文中")

    return "\n".join(lines).strip()


def trim_generated_text(text: str, plan: ContinuationRoundPlan) -> ContinuationTrimResult:
    if plan.mode == "prompt_only" or not text.strip():
        return ContinuationTrimResult(text=text, trimmed=False)

    remaining_word_count = plan.remaining_word_count
    if remaining_word_count is None:
        return ContinuationTrimResult(text=text, trimmed=False)

    preferred_limit = max(remaining_word_count, 160)
    soft_limit = max(preferred_limit, remaining_word_count + 120)
    actual_units = count_text_units(text)
    if actual_units <= soft_limit:
        return ContinuationTrimResult(text=text, trimmed=False)

    cut_index = _find_sentence_cut(text, preferred_limit)
    if cut_index is None:
        cut_index = _find_sentence_cut(text, soft_limit)
    if cut_index is None:
        cut_index = _find_hard_cut(text, soft_limit)

    if cut_index is None or cut_index <= 0:
        return ContinuationTrimResult(text=text, trimmed=False)

    trimmed_text = text[:cut_index].rstrip()
    return ContinuationTrimResult(
        text=trimmed_text or text[:cut_index],
        trimmed=trimmed_text != text,
    )


def _resolve_current_word_count(request: ContinuationRequest) -> int:
    existing_word_count = getattr(request, "existing_word_count", None)
    if existing_word_count is not None and existing_word_count >= 0:
        return existing_word_count
    return count_text_units(getattr(request, "previous_content", ""))


def _resolve_remaining_word_count(request: ContinuationRequest, current_word_count: int) -> int:
    target_word_count = getattr(request, "target_word_count", None)
    if target_word_count is None:
        return 0
    return max(target_word_count - current_word_count, 0)


def _resolve_round_max_tokens(
    request_max_tokens: Optional[int],
    suggested_word_count: Optional[int],
    mode: str,
) -> Optional[int]:
    if suggested_word_count is None:
        return request_max_tokens

    token_factor = 2.4
    computed_limit = max(256, int(suggested_word_count * token_factor))
    if request_max_tokens is None or request_max_tokens <= 0:
        return computed_limit
    return min(request_max_tokens, computed_limit)


def _resolve_round_hard_limit(
    *,
    suggested_word_count: Optional[int],
    remaining_word_count: int,
    mode: str,
) -> Optional[int]:
    if suggested_word_count is None:
        return None
    tolerance = 1.10
    return min(remaining_word_count, max(120, int(suggested_word_count * tolerance)))


def _find_sentence_cut(text: str, limit_units: int) -> Optional[int]:
    units = 0
    sentence_cut: Optional[int] = None
    for idx, char in enumerate(text):
        if not char.isspace():
            units += 1
        if char in _SENTENCE_ENDINGS and units <= limit_units:
            sentence_cut = idx + 1
        if units > limit_units:
            break
    return sentence_cut


def _find_hard_cut(text: str, limit_units: int) -> Optional[int]:
    units = 0
    for idx, char in enumerate(text):
        if not char.isspace():
            units += 1
        if units >= limit_units:
            return idx + 1
    return len(text) if text else None


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _estimate_round_count_from_remaining(mode: str, remaining_word_count: int) -> int:
    if remaining_word_count <= 0:
        return 1

    return 3 if remaining_word_count <= 1000 else 4


def _estimate_round_cap(
    mode: str,
    target_word_count: Optional[int],
    current_word_count: int,
) -> int:
    if mode == "prompt_only":
        return 1

    target = target_word_count or current_word_count or 4000

    return 3 if target <= 1000 else 4


def _plan_advance_suggestion(
    *,
    remaining_word_count: int,
    advance_rounds_left: int,
) -> int:
    # [MODIFIED] 均匀分配全部剩余字数，不再预留1000
    advance_budget = remaining_word_count
    suggestion = ceil(advance_budget / max(1, advance_rounds_left))
    upper = 2200
    lower = 220
    return _clamp(suggestion, lower, upper)


def _plan_close_suggestion(
    *,
    remaining_word_count: int,
    rounds_left: int,
) -> int:
    if rounds_left >= 3:
        return _clamp(min(600, max(remaining_word_count - 400, 0)), 180, 600)
    if rounds_left == 2:
        return _clamp(min(300, max(remaining_word_count - 100, 0)), 120, 300)
    return _clamp(min(remaining_word_count, 100), 60, 100)
