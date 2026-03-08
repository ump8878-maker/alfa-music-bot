"""Хелперы для рейтинга: полнота профиля, вкус пользователя, жанры и участники чата."""
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, ChatMember, MusicProfile

# Веса балла вкуса (итого 100): полнота 30, разнообразие 50, редкость 15, бонус 5
MAX_COMPLETENESS = 30
MAX_DIVERSITY = 50
MAX_RARITY = 15
MAX_CONSISTENCY = 5


@dataclass
class TasteScoreBreakdown:
    """Разбивка балла вкуса по компонентам."""
    completeness: int   # 0..30
    diversity: int     # 0..50
    rarity: int        # 0..15
    consistency: int   # 0..5
    total: int         # 0..100

    def to_short_str(self) -> str:
        return (
            f"Полнота {self.completeness}/{MAX_COMPLETENESS}, "
            f"Разнообразие {self.diversity}/{MAX_DIVERSITY}, "
            f"Редкость {self.rarity}/{MAX_RARITY}, "
            f"Бонус {self.consistency}/{MAX_CONSISTENCY}"
        )


def profile_completeness(profile: MusicProfile) -> float:
    """Полнота квиза: доля заполненных полей (0..1)."""
    filled = 0
    total = 4
    if profile.genres and len(profile.genres) > 0:
        filled += 1
    if profile.artists and len(profile.artists) > 0:
        filled += 1
    if getattr(profile, "guilty_genres", None):
        filled += 1
    if getattr(profile, "listening_time", None):
        filled += 1
    return filled / total


def get_taste_score_breakdown(profile: MusicProfile) -> TasteScoreBreakdown:
    """
    Разбивка балла вкуса 0–100:
    - Полнота (30): все 4 поля квиза заполнены.
    - Разнообразие (50): жанры (до 25) + артисты (до 25) — чем шире выбор, тем выше.
    - Редкость (15): вкус не только из чартов (Яндекс.Музыка, Beatport, DJ Mag) даёт до +15.
    - Бонус консистентности (5): время слушания + настроение совпадают по вайбу (ночь+меланхолия и т.п.).
    """
    filled = 0
    if profile.genres and len(profile.genres) > 0:
        filled += 1
    if profile.artists and len(profile.artists) > 0:
        filled += 1
    if getattr(profile, "guilty_genres", None):
        filled += 1
    if getattr(profile, "listening_time", None):
        filled += 1
    completeness = int(MAX_COMPLETENESS * (filled / 4))

    n_genres = len(profile.genres or [])
    n_artists = len(profile.artists or [])
    genre_pts = min(n_genres / 4, 1.0) * 25
    artist_pts = min(n_artists / 10, 1.0) * 25
    diversity = int(genre_pts + artist_pts)

    r = getattr(profile, "rarity_score", 0.5) or 0.5
    rarity = int(r * MAX_RARITY)

    # Бонус: guilty_genres не пересекаются с любимыми — осознанный вкус
    consistency = 0
    guilty = set(getattr(profile, "guilty_genres", None) or [])
    fav = set(g.get("name", "") for g in (profile.genres or []))
    if guilty:
        overlap = guilty & fav
        if not overlap:
            consistency = MAX_CONSISTENCY  # зашквар и любимое не пересекаются
        else:
            consistency = max(0, MAX_CONSISTENCY - len(overlap) * 2)

    total = min(100, completeness + diversity + rarity + consistency)
    return TasteScoreBreakdown(
        completeness=completeness,
        diversity=diversity,
        rarity=rarity,
        consistency=consistency,
        total=max(0, total),
    )


def get_taste_explanation(profile: MusicProfile) -> str:
    """Короткое объяснение, откуда взялся балл вкуса."""
    b = get_taste_score_breakdown(profile)
    parts = []
    if b.completeness >= MAX_COMPLETENESS:
        parts.append("квиз заполнен полностью")
    else:
        parts.append(f"заполни все шаги квиза (+{MAX_COMPLETENESS - b.completeness} за полноту)")
    if b.diversity >= 45:
        parts.append("широкий выбор жанров и артистов")
    elif b.diversity < 30:
        parts.append("добавь больше жанров и артистов — выше балл")
    if b.rarity >= 10:
        parts.append("редкий вкус даёт бонус")
    if b.consistency > 0:
        parts.append("зашквар не пересекается с любимым — бонус")
    if not parts:
        return "Пройди квиз до конца и выбери разнообразнее — балл вырастет."
    return " · ".join(parts).capitalize() + "."


def compute_user_taste_score(profile: MusicProfile) -> int:
    """Итоговый балл вкуса 0–100 (по разбивке: полнота + разнообразие + редкость + бонус)."""
    return get_taste_score_breakdown(profile).total


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


async def _get_completed_user_ids(
    session: AsyncSession, chat_id: int
) -> List[int]:
    """Список user_id участников чата, прошедших тест."""
    result = await session.execute(
        select(ChatMember.user_id).where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True,
        )
    )
    return [r[0] for r in result.fetchall()]


async def get_chat_member_ranking(
    session: AsyncSession, chat_id: int
) -> List[Tuple[User, MusicProfile, int]]:
    """Список (user, profile, taste_score) в чате, по убыванию score."""
    user_ids = await _get_completed_user_ids(session, chat_id)
    if not user_ids:
        return []

    users_result = await session.execute(select(User).where(User.id.in_(user_ids)))
    users = {u.id: u for u in users_result.scalars().all()}

    profiles_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id.in_(user_ids))
    )
    profiles = {p.user_id: p for p in profiles_result.scalars().all()}

    rows = []
    for uid in user_ids:
        u = users.get(uid)
        p = profiles.get(uid)
        if not u or not p:
            continue
        taste = compute_user_taste_score(p)
        rows.append((u, p, taste))

    rows.sort(key=lambda x: x[2], reverse=True)
    return rows


def find_rarest_user(
    ranking: List[Tuple[User, MusicProfile, int]],
) -> Optional[Tuple[User, MusicProfile, float]]:
    """Участник с самым редким вкусом из готового рейтинга. Чистая функция, без запросов."""
    if not ranking:
        return None
    best = None
    best_r = -1.0
    for u, p, _ in ranking:
        r = getattr(p, "rarity_score", 0.5) or 0.5
        if r > best_r:
            best_r = r
            best = (u, p, r)
    return best


async def get_chat_rarest_user(
    session: AsyncSession, chat_id: int
) -> Optional[Tuple[User, MusicProfile, float]]:
    """Участник чата с самым редким вкусом. Удобная обёртка с запросом."""
    ranking = await get_chat_member_ranking(session, chat_id)
    return find_rarest_user(ranking)


async def get_competitor_above(
    session: AsyncSession, chat_id: int, user_id: int
) -> Optional[Tuple[int, User, int]]:
    """Кто на месте выше в рейтинге чата и его балл. (rank_above, user_above, score_above) или None."""
    ranking = await get_chat_member_ranking(session, chat_id)
    for i, (u, _, score) in enumerate(ranking):
        if u.id == user_id:
            if i == 0:
                return None  # уже первый
            prev = ranking[i - 1]
            return (i, prev[0], prev[2])  # rank i+1 (1-based), user, score
    return None


async def get_chat_genre_stats(
    session: AsyncSession, chat_id: int
) -> List[Tuple[str, float]]:
    """Доля жанров в чате в процентах: [(genre_name, percent), ...]."""
    user_ids = await _get_completed_user_ids(session, chat_id)
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
    # Бонус за совпадение зашкварных жанров
    gg1 = set(getattr(p1, "guilty_genres", None) or [])
    gg2 = set(getattr(p2, "guilty_genres", None) or [])
    if gg1 and gg2 and (gg1 & gg2):
        guilty_bonus = 0.1
    else:
        guilty_bonus = 0
    return min(1.0, (jaccard_g * 0.5 + jaccard_a * 0.5) + guilty_bonus)


def find_closest_in_ranking(
    ranking: List[Tuple[User, MusicProfile, int]], user_id: int
) -> Optional[Tuple[User, float]]:
    """Ближайший по вкусу участник из готового рейтинга. Чистая функция, без запросов."""
    if len(ranking) < 2:
        return None
    my_profile = None
    for u, p, _ in ranking:
        if u.id == user_id:
            my_profile = p
            break
    if not my_profile:
        return None
    best_user, best_score = None, -1.0
    for u, p, _ in ranking:
        if u.id == user_id:
            continue
        sim = _taste_similarity(my_profile, p)
        if sim > best_score:
            best_score = sim
            best_user = u
    if best_user is None:
        return None
    return (best_user, round(best_score * 100, 0))


async def get_closest_in_chat(
    session: AsyncSession, chat_id: int, user_id: int
) -> Optional[Tuple[User, float]]:
    """Ближайший по вкусу участник чата. Удобная обёртка с запросом."""
    ranking = await get_chat_member_ranking(session, chat_id)
    return find_closest_in_ranking(ranking, user_id)


def calc_rarity_percentile(
    ranking: List[Tuple[User, MusicProfile, int]], user_id: int
) -> Optional[int]:
    """Топ-X% по редкости из готового рейтинга. Чистая функция, без запросов."""
    if len(ranking) < 2:
        return None
    my_p = None
    for u, p, _ in ranking:
        if u.id == user_id:
            my_p = p
            break
    if not my_p:
        return None
    rarities = [getattr(p, "rarity_score", 0.5) or 0.5 for _, p, _ in ranking]
    my_r = getattr(my_p, "rarity_score", 0.5) or 0.5
    count_less = sum(1 for r in rarities if r < my_r)
    n = len(rarities)
    percentile = int(100 * (n - count_less) / n) if n else 0
    return min(100, max(1, percentile)) if n else None


async def get_rarity_percentile_in_chat(
    session: AsyncSession, chat_id: int, user_id: int
) -> Optional[int]:
    """Топ-X% по редкости в чате. Удобная обёртка с запросом."""
    ranking = await get_chat_member_ranking(session, chat_id)
    return calc_rarity_percentile(ranking, user_id)


@dataclass
class MatchResult:
    """Результат сравнения двух музыкальных профилей."""
    similarity_pct: int          # 0..100
    common_genres: List[str]     # общие жанры
    common_artists: List[str]    # общие артисты
    common_guilty: List[str]     # общий зашквар
    enemy_genres: List[str]      # один любит, другой считает зашкваром


def compute_match(p1: MusicProfile, p2: MusicProfile) -> MatchResult:
    """Детальное сравнение двух профилей для /match."""
    sim = _taste_similarity(p1, p2)
    similarity_pct = int(sim * 100)

    g1 = set((g.get("name") or "").strip().lower() for g in (p1.genres or []))
    g2 = set((g.get("name") or "").strip().lower() for g in (p2.genres or []))
    g1.discard("")
    g2.discard("")
    common_genres = sorted(g1 & g2)

    a1 = set((a.get("name") or "").strip() for a in (p1.artists or []))
    a2 = set((a.get("name") or "").strip() for a in (p2.artists or []))
    a1.discard("")
    a2.discard("")
    common_artists = sorted(a1 & a2, key=str.lower)

    gg1 = set(getattr(p1, "guilty_genres", None) or [])
    gg2 = set(getattr(p2, "guilty_genres", None) or [])
    common_guilty = sorted(gg1 & gg2)

    # «Конфликт»: один любит жанр, другой его ненавидит
    enemy = sorted((g1 & gg2) | (g2 & gg1))

    return MatchResult(
        similarity_pct=similarity_pct,
        common_genres=common_genres,
        common_artists=common_artists,
        common_guilty=common_guilty,
        enemy_genres=enemy,
    )
