from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from app.bootstrap.card_types import (
    STORYAXIS_DEFAULT_MAX_TOKENS,
    STORYAXIS_DEFAULT_TIMEOUT,
)
from app.db.models import CardType
from app.db.session import engine


def repair_storyaxis_card_type_ai_params(session: Session) -> dict[str, int]:
    counts = {
        "updated": 0,
        "already_correct": 0,
        "missing_ai_params": 0,
    }

    storyaxis_types = session.exec(
        select(CardType).where(
            CardType.built_in == True,  # noqa: E712
            CardType.name.like("StoryAxis·%"),
        )
    ).all()

    for card_type in storyaxis_types:
        if getattr(card_type, "is_ai_enabled", True) is False:
            continue

        ai_params = dict(card_type.ai_params or {})
        if not ai_params:
            counts["missing_ai_params"] += 1
            continue

        if (
            ai_params.get("max_tokens") == STORYAXIS_DEFAULT_MAX_TOKENS
            and ai_params.get("timeout") == STORYAXIS_DEFAULT_TIMEOUT
        ):
            counts["already_correct"] += 1
            continue

        ai_params["max_tokens"] = STORYAXIS_DEFAULT_MAX_TOKENS
        ai_params["timeout"] = STORYAXIS_DEFAULT_TIMEOUT
        card_type.ai_params = ai_params
        session.add(card_type)
        counts["updated"] += 1

    session.commit()
    return counts


def _format_summary(counts: dict[str, Any]) -> str:
    details = ", ".join(
        f"{key}={counts.get(key, 0)}"
        for key in ("updated", "already_correct", "missing_ai_params")
    )
    return f"StoryAxis ai_params repair finished: {details}"


def main() -> int:
    with Session(engine) as session:
        counts = repair_storyaxis_card_type_ai_params(session)
    print(_format_summary(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
