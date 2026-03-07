"""Хелперы для рейтинга: полнота профиля, вкус пользователя, жанры и участники чата."""
from typing import List, Tuple, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, ChatMember, MusicProfile


def profile_completeness(profile: MusicProfile) -> float:
    """Полнота квиза: доля заполненных полей (0..1)."""
    filled = 0
    total = 4
    if profile.genres and len(profile.genres) > 0:
        filled += 1
    if profile.artists and len(profile.artists) > 0:
        filled += 1
    if profile.mood:
        filled += 1
    if getattr(profile, "listening_time", None):
        filled += 1
    return filled / total


def compute_user_taste_score(profile: MusicProfile) -> int:
    """
    Вкус 0–100: полнота квиза (45) + разнообразие выбора (45) + бонус редкости (10).
    Полнота: все 4 поля заполнены. Разнообразие: 2–4 жанра и несколько артистов дают макс.
    Редкость: вкус «не только из чартов» даёт до +10. Без предвзятости к жанрам.
    """
    completeness = profile_completeness(profile)
    n_genres = len(profile.genres or [])
    n_artists = len(profile.artists or [])
    # Разнообразие: сладкая точка 2–4 жанра, 3–10 артистов (не наказываем за 1, но макс за разнообразие)
    genre_part = min(n_genres / 4, 1.0) * 22.5
    artist_part = min(n_artists / 10, 1.0) * 22.5
    diversity = genre_part + artist_part
    completeness_bonus = completeness * 45
    # Небольшой бонус за редкий вкус (0–10), чтобы оценка была интереснее
    rarity = getattr(profile, "rarity_score", 0.5) or 0.5
    rarity_bonus = rarity * 10
    score = completeness_bonus + diversity + rarity_bonus
    return min(100, max(0, int(score)))


def compute_rarity_score(artist_names: list) -> float:
    """
    Редкость вкуса 0..1 по артистам. Опора на списки популярных (Яндекс.Музыка, Beatport, DJ Mag, чарты).
    0 = все артисты из популярных чартов, 1 = все реже/не из списка.
    """
    if not artist_names:
        return 0.5
    try:
        from keyboards.data import get_popular_artists_set
        popular = get_popular_artists_set()
        names = [a.strip() for a in artist_names if a and isinstance(a, str)]
        if not names:
            return 0.5
        in_popular = sum(1 for n in names if n in popular)
        share_popular = in_popular / len(names)
        return round(1.0 - share_popular, 2)
    except Exception:
        return 0.5


async def get_chat_member_ranking(
    session: AsyncSession, chat_id: int
) -> List[Tuple[User, MusicProfile, int]]:
    """Список (user, profile, taste_score) в чате, по убыванию score."""
    members_result = await session.execute(
        select(ChatMember).where(
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


async def get_chat_genre_stats(
    session: AsyncSession, chat_id: int
) -> List[Tuple[str, float]]:
    """Доля жанров в чате в процентах: [(genre_name, percent), ...]."""
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

    counts = {}
    total_mentions = 0
    for p in profiles:
        for g in p.genres or []:
            name = (g.get("name") or "").strip().lower() or "другое"
            if name in ("свой вариант", "other"):
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
    """Место пользователя в рейтинге чата (1-based) или None."""
    ranking = await get_chat_member_ranking(session, chat_id)
    for i, (u, _, _) in enumerate(ranking, 1):
        if u.id == user_id:
            return i
    return None
