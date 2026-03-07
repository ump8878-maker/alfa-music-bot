"""Одна фраза о вкусе — для био и шаринга. По профилю: жанры, время, настроение."""
from typing import Any, Optional

# Человекочитаемые короткие подписи
LISTEN_LABELS = {
    "morning": "утром",
    "day": "днём",
    "evening": "вечером",
    "night": "ночью",
    "anytime": "всегда",
}
MOOD_LABELS = {
    "melancholic": "меланхолия",
    "energetic": "драйв",
    "calm": "чилл",
    "aggressive": "агрессия",
    "other": "свой вайб",
}


def generate_taste_phrase(profile: Any) -> str:
    """
    Генерирует одну короткую фразу о вкусе по профилю.
    Примеры: «Инди ночью, хип-хоп днём», «Рок и драйв», «Джаз, чилл, вечером».
    """
    genres = []
    for g in (profile.genres or [])[:3]:
        name = (g.get("name") or "").strip()
        if name and name.lower() not in ("другое", "other", "свой вариант"):
            genres.append(name)
    listening = getattr(profile, "listening_time", None) or ""
    mood = (profile.mood or "").strip().lower()

    parts = []
    if genres:
        parts.append(", ".join(genres[:2]))
        if len(genres) > 2:
            parts[0] += " и ещё"
    listen_label = LISTEN_LABELS.get(listening)
    if listen_label:
        parts.append(listen_label)
    mood_label = MOOD_LABELS.get(mood)
    if mood_label:
        parts.append(mood_label)

    if not parts:
        return "Свой вайб"
    return " · ".join(parts)
