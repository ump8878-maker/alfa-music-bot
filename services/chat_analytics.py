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
    mood_counts: Dict[str, int] = {}
    listening_counts: Dict[str, int] = {}
    total_score = 0.0

    for p in profiles:
        total_score += compute_user_taste_score(p)
        for g in p.genres or []:
            name = (g.get("name") or "").strip().lower() or "другое"
            if name in ("свой вариант", "other"):
                name = "хаос"
            genre_counts[name] = genre_counts.get(name, 0) + 1
        for a in p.artists or []:
            name = (a.get("name") or "").strip()
            if name:
                artist_counts[name] = artist_counts.get(name, 0) + 1
        if p.mood:
            mood_counts[p.mood] = mood_counts.get(p.mood, 0) + 1
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
    dominant_mood = max(mood_counts.items(), key=lambda x: x[1])[0] if mood_counts else None
    dominant_listening = (
        max(listening_counts.items(), key=lambda x: x[1])[0] if listening_counts else None
    )
    avg_score = total_score / len(profiles) if profiles else 0

    return {
        "participants_count": len(profiles),
        "genre_pcts": genre_pcts,
        "top_artists": top_artists,
        "dominant_mood": dominant_mood,
        "dominant_listening": dominant_listening,
        "avg_score": round(avg_score, 1),
        "genre_counts": genre_counts,
    }


def _derive_profile_name(stats: Dict[str, Any]) -> str:
    genre_pcts = stats.get("genre_pcts") or []
    top_genres = [g[0].lower() for g in genre_pcts[:3]]
    mood = stats.get("dominant_mood")
    listening = stats.get("dominant_listening")

    if any(
        g in ("electronic", "электроника", "techno", "техно") for g in top_genres
    ):
        return "Ночные меломаны" if listening == "night" else "Электронный клуб"
    if any(g in ("indie", "инди") for g in top_genres):
        return "Инди-меланхолики" if mood == "melancholic" else "Инди-семья"
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
    mood = stats.get("dominant_mood")
    listening = stats.get("dominant_listening")
    parts = []
    if listening == "night":
        parts.extend(["ночные прогулки", "поздние сеты"])
    elif listening == "evening":
        parts.append("вечерние плейлисты")
    elif listening == "morning":
        parts.append("утренний кофе под музыку")
    if mood == "energetic":
        parts.append("драйв и движение")
    elif mood == "melancholic":
        parts.append("грустные воскресные утра")
    elif mood == "calm":
        parts.append("чилл и фон")
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

    return ChatProfile(
        profile_name=profile_name,
        genre_stats=genre_stats,
        top_artists=top_artists,
        vibe_text=vibe_text,
        overall_score=overall_score,
    )


def generate_chat_comment(chat_profile: ChatProfile) -> str:
    """Короткий комментарий к профилю чата."""
    from utils.humor import get_chat_scan_comment
    return get_chat_scan_comment(chat_profile)
