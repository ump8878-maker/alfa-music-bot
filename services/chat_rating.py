# Рейтинг чатов: простая стабильная формула без предвзятости к жанрам
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import Chat, ChatMember, MusicProfile, ChatStats
from services.rating_helpers import (
    get_chat_member_ranking,
    get_chat_genre_stats,
    profile_completeness,
)

WEIGHT_ACTIVITY = 25
WEIGHT_COMPLETENESS = 25
WEIGHT_CONSISTENCY = 25
WEIGHT_DIVERSITY = 15
WEIGHT_ENGAGEMENT = 10


@dataclass
class NeededForNextRank:
    current_position: int
    total_chats: int
    needed_count: int
    next_competitor_title: Optional[str] = None


async def calculate_chat_rating(session: AsyncSession, chat_id: int) -> float:
    """
    Рейтинг чата 0–100: активность, полнота, согласованность (упрощённо),
    разнообразие, вовлечённость.
    """
    members_result = await session.execute(
        select(ChatMember.user_id).where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True,
        )
    )
    user_ids = [r[0] for r in members_result.fetchall()]
    if not user_ids:
        return 0.0

    profiles_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id.in_(user_ids))
    )
    profiles = list(profiles_result.scalars().all())
    if not profiles:
        return 0.0

    participants_count = len(profiles)
    chat = await session.get(Chat, chat_id)

    activity = min(participants_count, 20) / 20.0 * WEIGHT_ACTIVITY

    avg_completeness = sum(profile_completeness(p) for p in profiles) / len(profiles)
    completeness = avg_completeness * WEIGHT_COMPLETENESS

    # Согласованность без matching: по разбросу полноты (чем равнее — тем выше)
    comps = [profile_completeness(p) for p in profiles]
    if len(comps) >= 2:
        mean_c = sum(comps) / len(comps)
        var = sum((c - mean_c) ** 2 for c in comps) / len(comps)
        consistency_norm = max(0, 1 - var * 2)
    else:
        consistency_norm = 1.0
    consistency = consistency_norm * WEIGHT_CONSISTENCY

    genre_stats = await get_chat_genre_stats(session, chat_id)
    unique_genres = len(genre_stats)
    diversity_norm = min(unique_genres / 8.0, 1.0)
    diversity = diversity_norm * WEIGHT_DIVERSITY

    engagement = 0.0
    if chat and getattr(chat, "member_count", None) and chat.member_count > 0:
        ratio = participants_count / chat.member_count
        engagement = min(ratio, 1.0) * WEIGHT_ENGAGEMENT
    else:
        engagement = WEIGHT_ENGAGEMENT / 2

    rating = activity + completeness + consistency + diversity + engagement
    rating = min(100.0, max(0.0, round(rating, 1)))

    if chat:
        chat.rating = round(rating, 1)

    stats = await session.get(ChatStats, chat_id)
    if not stats:
        stats = ChatStats(chat_id=chat_id)
        session.add(stats)
    stats.rating = round(rating, 1)
    stats.participants_count = participants_count
    stats.top_genres = [{"name": g[0], "pct": g[1]} for g in genre_stats[:10]]
    if not stats.top_artists and profiles:
        ranking = await get_chat_member_ranking(session, chat_id)
        if ranking:
            _, p, _ = ranking[0]
            stats.top_artists = [a.get("name", "") for a in (p.artists or [])[:5]]
    await session.commit()
    return round(rating, 1)


async def get_chat_rank(
    session: AsyncSession, chat_id: int
) -> Optional[Tuple[int, int]]:
    """(позиция, всего_чатов) в глобальном рейтинге."""
    chat = await session.get(Chat, chat_id)
    if not chat or chat.rating <= 0:
        return None
    higher = await session.scalar(
        select(func.count(Chat.id)).where(
            Chat.is_active == True,
            Chat.rating > chat.rating,
        )
    )
    total = await session.scalar(
        select(func.count(Chat.id)).where(
            Chat.is_active == True,
            Chat.rating > 0,
        )
    )
    return (int(higher or 0) + 1, int(total or 0))


async def get_global_chat_ranking(
    session: AsyncSession, limit: int = 20
) -> List[Tuple[Chat, float]]:
    """Глобальный топ чатов по рейтингу."""
    result = await session.execute(
        select(Chat)
        .where(Chat.is_active == True, Chat.rating > 0)
        .order_by(Chat.rating.desc())
        .limit(limit)
    )
    chats = result.scalars().all()
    return [(c, c.rating) for c in chats]


async def get_needed_participants_for_next_rank(
    session: AsyncSession, chat_id: int
) -> Optional[NeededForNextRank]:
    """Сколько участников добрать для подъёма в рейтинге."""
    rank = await get_chat_rank(session, chat_id)
    if not rank:
        return None
    current_position, total_chats = rank
    chat = await session.get(Chat, chat_id)
    if not chat or chat.rating <= 0:
        return None

    result_above = await session.execute(
        select(Chat)
        .where(Chat.is_active == True, Chat.rating > chat.rating)
        .order_by(Chat.rating.asc())
        .limit(1)
    )
    next_competitor = result_above.scalar_one_or_none()
    next_title = (
        (next_competitor.title or f"Чат #{current_position - 1}")
        if next_competitor
        else None
    )

    needed_count = 1 if current_position > 1 else 0
    if current_position > 1 and next_competitor:
        diff = next_competitor.rating - chat.rating
        if diff > 5:
            needed_count = 2
        elif diff > 10:
            needed_count = 3

    return NeededForNextRank(
        current_position=current_position,
        total_chats=total_chats,
        needed_count=needed_count,
        next_competitor_title=next_title,
    )


async def can_send_growth_message(
    session: AsyncSession, chat_id: int
) -> bool:
    """Можно ли отправить growth-сообщение (cooldown из config)."""
    from config import settings
    stats = await session.get(ChatStats, chat_id)
    if not stats or not stats.last_growth_message_at:
        return True
    since = stats.last_growth_message_at
    now = datetime.now(timezone.utc)
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    elapsed = (now - since).total_seconds() / 3600
    cooldown = getattr(settings, "growth_message_cooldown_hours", 3.0)
    return elapsed >= cooldown


async def mark_growth_message_sent(
    session: AsyncSession, chat_id: int
) -> None:
    """Обновить last_growth_message_at после отправки growth-сообщения."""
    stats = await session.get(ChatStats, chat_id)
    if not stats:
        stats = ChatStats(chat_id=chat_id)
        session.add(stats)
    stats.last_growth_message_at = datetime.now(timezone.utc)
    await session.commit()
