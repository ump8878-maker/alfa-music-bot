# Рейтинги: пользовательский «вкус», рейтинг чата, глобальный топ чатов
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models import (
    User,
    Chat,
    ChatMember,
    MusicProfile,
    Match,
)


def compute_user_taste_score(profile: MusicProfile) -> int:
    """
    Считает «вкус» пользователя 0–100 для отображения в рейтинге чата.
    Учитывает редкость, разнообразие жанров и артистов.
    """
    base = 50
    rarity_bonus = int(profile.rarity_score * 25)
    genre_bonus = min(len(profile.genres or []), 3) * 5
    artist_bonus = min(len(profile.artists or []), 5) * 2
    score = base + rarity_bonus + genre_bonus + artist_bonus
    return min(100, max(0, score))


async def get_chat_member_ranking(
    session: AsyncSession, chat_id: int
) -> List[Tuple[User, MusicProfile, int]]:
    """
    Возвращает список (user, profile, taste_score) в чате, отсортированный по score.
    """
    members_result = await session.execute(
        select(ChatMember)
        .where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True,
        )
    )
    members = members_result.scalars().all()
    if not members:
        return []

    user_ids = [m.user_id for m in members]
    users_result = await session.execute(select(User).where(User.id.in_(user_ids)))
    users = {u.id: u for u in users_result.scalars().all()}

    profiles_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id.in_(user_ids))
    )
    profiles = {p.user_id: p for p in profiles_result.scalars().all()}

    rows = []
    for m in members:
        u = users.get(m.user_id)
        p = profiles.get(m.user_id)
        if not u or not p:
            continue
        taste = compute_user_taste_score(p)
        rows.append((u, p, taste))

    rows.sort(key=lambda x: x[2], reverse=True)
    return rows


async def update_chat_rating(session: AsyncSession, chat_id: int) -> float:
    """
    Пересчитывает рейтинг чата (средний вкус участников) и сохраняет в Chat.rating.
    """
    ranking = await get_chat_member_ranking(session, chat_id)
    if not ranking:
        return 0.0
    avg = sum(r[2] for r in ranking) / len(ranking)
    chat = await session.get(Chat, chat_id)
    if chat:
        chat.rating = round(avg, 1)
        await session.commit()
    return round(avg, 1)


async def get_global_chat_ranking(
    session: AsyncSession, limit: int = 20
) -> List[Tuple[Chat, float]]:
    """Глобальный рейтинг чатов по полю rating (с подгрузкой владельца)."""
    result = await session.execute(
        select(Chat)
        .where(Chat.is_active == True, Chat.rating > 0)
        .options(selectinload(Chat.owner), selectinload(Chat.added_by))
        .order_by(Chat.rating.desc())
        .limit(limit)
    )
    chats = result.scalars().all()
    return [(c, c.rating) for c in chats]


async def get_chat_position(session: AsyncSession, chat_id: int) -> Optional[Tuple[int, int]]:
    """
    Возвращает (позиция, всего_чатов) для чата в глобальном рейтинге, или None.
    """
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


async def get_chat_genre_stats(
    session: AsyncSession, chat_id: int
) -> List[Tuple[str, float]]:
    """
    Доля жанров в чате в процентах. Возвращает список (genre_name, percent).
    """
    members_result = await session.execute(
        select(ChatMember.user_id).where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True,
        )
    )
    user_ids = [row[0] for row in members_result.fetchall()]
    if not user_ids:
        return []

    profiles_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id.in_(user_ids))
    )
    profiles = profiles_result.scalars().all()

    total_mentions = 0
    counts = {}
    for p in profiles:
        for g in p.genres or []:
            name = (g.get("name") or "").strip().lower() or "другое"
            if name == "свой вариант":
                name = "хаос"
            counts[name] = counts.get(name, 0) + 1
            total_mentions += 1

    if not total_mentions:
        return []

    return [
        (name, round(100 * count / total_mentions, 1))
        for name, count in sorted(counts.items(), key=lambda x: -x[1])
    ]


async def get_user_rank_in_chat(
    session: AsyncSession, user_id: int, chat_id: int
) -> Optional[int]:
    """Место пользователя в рейтинге чата (1-based), или None."""
    ranking = await get_chat_member_ranking(session, chat_id)
    for i, (u, _, _) in enumerate(ranking, 1):
        if u.id == user_id:
            return i
    return None
