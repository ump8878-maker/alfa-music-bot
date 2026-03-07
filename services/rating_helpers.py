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


def _taste_similarity(p1: MusicProfile, p2: MusicProfile) -> float:
    """Похожесть вкусов 0..1: жанры и артисты (Jaccard)."""
    g1 = set((g.get("name") or "").strip().lower() for g in (p1.genres or []))
    g2 = set((g.get("name") or "").strip().lower() for g in (p2.genres or []))
    a1 = set((a.get("name") or "").strip().lower() for a in (p1.artists or []))
    a2 = set((a.get("name") or "").strip().lower() for a in (p2.artists or []))
    g1.discard("")
    g2.discard("")
    a1.discard("")
    a2.discard("")
    jaccard_g = len(g1 & g2) / len(g1 | g2) if (g1 or g2) else 0
    jaccard_a = len(a1 & a2) / len(a1 | a2) if (a1 or a2) else 0
    if p1.mood and p2.mood and p1.mood == p2.mood:
        mood_bonus = 0.1
    else:
        mood_bonus = 0
    return min(1.0, (jaccard_g * 0.5 + jaccard_a * 0.5) + mood_bonus)


async def get_closest_in_chat(
    session: AsyncSession, chat_id: int, user_id: int
) -> Optional[Tuple[User, float]]:
    """Ближайший по вкусу участник чата (кроме user_id). Возвращает (User, similarity 0–100) или None."""
    ranking = await get_chat_member_ranking(session, chat_id)
    profiles_result = await session.execute(
        select(MusicProfile).where(
            MusicProfile.user_id.in_([r[0].id for r in ranking])
        )
    )
    profiles = {p.user_id: p for p in profiles_result.scalars().all()}
    my_profile = profiles.get(user_id)
    if not my_profile or len(ranking) < 2:
        return None
    best_user, best_score = None, -1.0
    for u, p, _ in ranking:
        if u.id == user_id:
            continue
        prof = profiles.get(u.id)
        if not prof:
            continue
        sim = _taste_similarity(my_profile, prof)
        if sim > best_score:
            best_score = sim
            best_user = u
    if best_user is None:
        return None
    return (best_user, round(best_score * 100, 0))


async def get_rarity_percentile_in_chat(
    session: AsyncSession, chat_id: int, user_id: int
) -> Optional[int]:
    """Топ-X% по редкости в чате (100 = самый редкий). None если нет профиля или один в чате."""
    members_result = await session.execute(
        select(ChatMember.user_id).where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True,
        )
    )
    user_ids = [r[0] for r in members_result.fetchall()]
    if len(user_ids) < 2 or user_id not in user_ids:
        return None
    all_profiles_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id.in_(user_ids))
    )
    all_profiles = list(all_profiles_result.scalars().all())
    my_p = next((p for p in all_profiles if p.user_id == user_id), None)
    if not my_p:
        return None
    rarities = [getattr(p, "rarity_score", 0.5) or 0.5 for p in all_profiles]
    if not rarities:
        return None
    my_r = getattr(my_p, "rarity_score", 0.5) or 0.5
    # Сколько людей с редкостью строго ниже (более мейнстрим) — мы реже их
    count_less = sum(1 for r in rarities if r < my_r)
    n = len(rarities)
    # Топ-X%: X = доля участников с редкостью не ниже нашей. Самый редкий → топ-100/n %, наименее редкий → топ-100%
    percentile = int(100 * (n - count_less) / n) if n else 0
    return min(100, max(1, percentile)) if n else None
