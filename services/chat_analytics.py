# Музыкальный сканер чата: агрегация, профиль, комментарий
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import ChatMember, MusicProfile
from keyboards.data import GENRES
from services.rating_helpers import compute_user_taste_score

GENRE_DISPLAY = {g["id"]: g["name"].lower() for g in GENRES}
GENRE_DISPLAY["other"] = "хаос"
GENRE_DISPLAY["другое"] = "хаос"


@dataclass
class ChatProfile:
    """Музыкальный портрет чата для /chat_scan."""
    profile_name: str
    genre_stats: List[tuple]
    top_artists: List[str]
    vibe_text: str
    overall_score: float
    avg_rarity: float  # 0 = чарты, 1 = редкий
    rare_count: int
    mainstream_count: int
    top_guilty: Optional[str] = None  # самый зашкварный жанр в чате


async def collect_chat_music_stats(
    session: AsyncSession, chat_id: int
) -> Optional[Dict[str, Any]]:
    """
    Агрегированная статистика по музыке в чате.
    None, если участников с профилем меньше минимума (config).
    """
    from config import settings
    min_participants = getattr(
        settings, "min_participants_for_scan", 3
    )

    members_result = await session.execute(
        select(ChatMember.user_id).where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True,
        )
    )
    user_ids = [r[0] for r in members_result.fetchall()]
    if len(user_ids) < min_participants:
        return None

    profiles_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id.in_(user_ids))
    )
    profiles = profiles_result.scalars().all()
    if not profiles:
        return None

    genre_counts: Dict[str, int] = {}
    artist_counts: Dict[str, int] = {}
    guilty_counts: Dict[str, int] = {}
    listening_counts: Dict[str, int] = {}
    total_score = 0.0
    rarity_sum = 0.0
    rare_count = 0
    mainstream_count = 0

    for p in profiles:
        total_score += compute_user_taste_score(p)
        r = getattr(p, "rarity_score", 0.5) or 0.5
        rarity_sum += r
        if r > 0.5:
            rare_count += 1
        else:
            mainstream_count += 1
        for g in p.genres or []:
            name = (g.get("name") or "").strip().lower() or "другое"
            if name in ("свой вариант", "other"):
                name = "хаос"
            genre_counts[name] = genre_counts.get(name, 0) + 1
        for a in p.artists or []:
            name = (a.get("name") or "").strip()
            if name:
                artist_counts[name] = artist_counts.get(name, 0) + 1
        for gg in (getattr(p, "guilty_genres", None) or []):
            guilty_counts[gg] = guilty_counts.get(gg, 0) + 1
        if p.listening_time:
            listening_counts[p.listening_time] = listening_counts.get(
                p.listening_time, 0
            ) + 1

    total_genre_mentions = sum(genre_counts.values())
    genre_pcts = []
    if total_genre_mentions:
        for name, count in sorted(genre_counts.items(), key=lambda x: -x[1]):
            pct = round(100 * count / total_genre_mentions, 1)
            display_name = GENRE_DISPLAY.get(name, name)
            genre_pcts.append((display_name, pct))

    top_artists = [
        name for name, _ in sorted(artist_counts.items(), key=lambda x: -x[1])[:15]
    ]
    top_guilty = max(guilty_counts.items(), key=lambda x: x[1])[0] if guilty_counts else None
    dominant_listening = (
        max(listening_counts.items(), key=lambda x: x[1])[0] if listening_counts else None
    )
    avg_score = total_score / len(profiles) if profiles else 0
    avg_rarity = round(rarity_sum / len(profiles), 2) if profiles else 0.5

    return {
        "participants_count": len(profiles),
        "genre_pcts": genre_pcts,
        "top_artists": top_artists,
        "top_guilty": top_guilty,
        "dominant_listening": dominant_listening,
        "avg_score": round(avg_score, 1),
        "genre_counts": genre_counts,
        "avg_rarity": avg_rarity,
        "rare_count": rare_count,
        "mainstream_count": mainstream_count,
    }


def _derive_profile_name(stats: Dict[str, Any]) -> str:
    genre_pcts = stats.get("genre_pcts") or []
    top_genres = [g[0].lower() for g in genre_pcts[:3]]
    listening = stats.get("dominant_listening")

    if any(
        g in ("electronic", "электроника", "techno", "техно") for g in top_genres
    ):
        return "Ночные меломаны" if listening == "night" else "Электронный клуб"
    if any(g in ("indie", "инди") for g in top_genres):
        return "Инди-семья"
    if any(g in ("rock", "рок", "metal", "метал") for g in top_genres):
        return "Рок-тусовка"
    if any(g in ("hiphop", "хип-хоп") for g in top_genres):
        return "Хип-хоп компания"
    if any(g in ("pop", "поп") for g in top_genres):
        return "Поп-вечеринка"
    if "хаос" in top_genres or "другое" in top_genres:
        return "Музыкальный винегрет"
    if listening == "night":
        return "Ночные меломаны"
    if len(top_genres) >= 3:
        return "Разношёрстные меломаны"
    return "Музыкальный чат"


def _derive_vibe_text(stats: Dict[str, Any]) -> str:
    listening = stats.get("dominant_listening")
    top_guilty = stats.get("top_guilty")
    parts = []
    if listening == "night":
        parts.extend(["ночные прогулки", "поздние сеты"])
    elif listening == "evening":
        parts.append("вечерние плейлисты")
    elif listening == "morning":
        parts.append("утренний кофе под музыку")
    if top_guilty:
        guilty_display = GENRE_DISPLAY.get(top_guilty, top_guilty)
        parts.append(f"ненавидят {guilty_display}")
    if not parts:
        return "разный вайб, но в одном чате"
    return ", ".join(parts)


async def calculate_chat_profile(
    session: AsyncSession, chat_id: int
) -> Optional[ChatProfile]:
    """Музыкальный профиль чата. None при нехватке данных."""
    stats = await collect_chat_music_stats(session, chat_id)
    if not stats:
        return None

    profile_name = _derive_profile_name(stats)
    vibe_text = _derive_vibe_text(stats)
    genre_stats = stats.get("genre_pcts") or []
    top_artists = stats.get("top_artists") or []
    overall_score = stats.get("avg_score", 0)
    avg_rarity = stats.get("avg_rarity", 0.5)
    rare_count = stats.get("rare_count", 0)
    mainstream_count = stats.get("mainstream_count", 0)

    top_guilty = stats.get("top_guilty")

    return ChatProfile(
        profile_name=profile_name,
        genre_stats=genre_stats,
        top_artists=top_artists,
        vibe_text=vibe_text,
        overall_score=overall_score,
        avg_rarity=avg_rarity,
        rare_count=rare_count,
        mainstream_count=mainstream_count,
        top_guilty=top_guilty,
    )


def generate_chat_comment(chat_profile: ChatProfile) -> str:
    """Короткий комментарий к профилю чата."""
    from utils.humor import get_chat_scan_comment
    return get_chat_scan_comment(chat_profile)
