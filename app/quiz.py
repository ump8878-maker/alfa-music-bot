# Логика квиза: 4 вопроса, подсчёт архетипа и сохранение
from typing import List, Dict, Any, Optional
from app.models import MusicProfile
from app.keyboards.data import GENRES, MOODS, WHEN_LISTEN


def normalize_genre_id(name_or_id: str) -> str:
    """Возвращает id жанра по имени или id."""
    name_lower = name_or_id.lower().strip()
    for g in GENRES:
        if g["id"] == name_or_id or g["name"].lower() == name_lower:
            return g["id"]
    return name_or_id


def build_profile_from_answers(
    selected_genres: List[str],
    selected_artists: List[str],
    listening_time: Optional[str],
    mood: Optional[str],
    rarity_score: float,
) -> Dict[str, Any]:
    """Формирует данные для сохранения в MusicProfile из ответов квиза."""
    genres = [{"name": normalize_genre_id(g), "weight": 1.0} for g in selected_genres]
    artists = [{"name": a} for a in selected_artists]
    return {
        "genres": genres,
        "artists": artists,
        "listening_time": listening_time or "anytime",
        "mood": mood or "calm",
        "rarity_score": rarity_score,
    }


def get_listening_time_label(listening_time_id: str) -> str:
    """Человекочитаемая подпись для «когда слушаешь»."""
    for w in WHEN_LISTEN:
        if w["id"] == listening_time_id:
            return w["name"]
    return listening_time_id or "в любое время"
