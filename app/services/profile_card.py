from typing import Optional
from app.models import MusicProfile
from app.keyboards.data import GENRES, MOODS, ERAS


def get_genre_emoji(genre_id: str) -> str:
    """Получает эмодзи для жанра"""
    for g in GENRES:
        if g["id"] == genre_id:
            return g["emoji"]
    return "🎵"


def get_mood_name(mood_id: str) -> str:
    """Получает название настроения"""
    mood_map = {
        "melancholic": "меланхоличная",
        "energetic": "энергичная", 
        "calm": "спокойная",
        "aggressive": "драйвовая",
    }
    return mood_map.get(mood_id, mood_id)


def get_era_name(era_id: str) -> str:
    """Получает название эпохи"""
    era_map = {
        "oldschool": "классика (до 2000)",
        "2000s": "нулевые",
        "2010s": "десятые",
        "2020s": "свежак (2020+)",
    }
    return era_map.get(era_id, era_id)


def get_listening_time_name(when_id: str) -> str:
    """Подпись для «когда слушаешь»."""
    from app.keyboards.data import WHEN_LISTEN
    for w in WHEN_LISTEN:
        if w["id"] == when_id:
            return w["name"]
    return when_id or "в любое время"


def generate_profile_text(profile: MusicProfile) -> str:
    """Генерирует текстовое описание профиля (индивидуальная аналитика)."""
    profile_type = profile.profile_type
    profile_desc = profile.profile_description

    genres_text = ""
    if profile.genres:
        genre_items = []
        for g in profile.genres[:3]:
            name = g.get("name", "")
            emoji = get_genre_emoji(name)
            genre_items.append(f"{emoji} {name.capitalize()}")
        genres_text = ", ".join(genre_items)

    artists_text = ""
    if profile.artists:
        artist_names = [a.get("name", "") for a in profile.artists[:5]]
        artists_text = ", ".join(artist_names)

    mood_text = get_mood_name(profile.mood) if profile.mood else ""
    when_text = get_listening_time_name(profile.listening_time or "") if getattr(profile, "listening_time", None) else ""
    era_text = get_era_name(profile.era) if profile.era else ""

    rarity_percent = int(profile.rarity_score * 100)
    if rarity_percent > 70:
        rarity_text = f"🦄 Редкость: {rarity_percent}% — ты слушаешь то, что слушает мало кто"
    elif rarity_percent < 30:
        rarity_text = f"📻 Редкость: {rarity_percent}% — ты в тренде"
    else:
        rarity_text = f"🎧 Редкость: {rarity_percent}%"

    lines = [
        f"<b>{profile_type}</b>",
        f"<i>{profile_desc}</i>",
        "",
    ]
    if genres_text:
        lines.append(f"🎸 <b>Вы любите:</b> {genres_text}")
    if artists_text:
        lines.append(f"🎤 <b>Артисты:</b> {artists_text}")
    if when_text:
        lines.append(f"🕐 <b>Чаще слушаете музыку:</b> {when_text.lower()}")
    if mood_text:
        lines.append(f"💜 <b>Настроение:</b> {mood_text}")
    if era_text:
        lines.append(f"📅 <b>Эпоха:</b> {era_text}")
    lines.append("")
    lines.append(rarity_text)
    return "\n".join(lines)


def generate_individual_analytics_block(profile: MusicProfile) -> str:
    """Блок «ваш музыкальный профиль» после квиза с подсказкой «вероятно»."""
    lines = [
        "🎧 <b>Ваш музыкальный профиль</b>",
        "",
        f"<b>Тип:</b> {profile.profile_type}",
        "",
    ]
    if profile.genres:
        names = [g.get("name", "").capitalize() for g in profile.genres[:5]]
        lines.append(f"<b>Вы любите:</b> " + ", ".join(names))
    if profile.artists:
        names = [a.get("name", "") for a in profile.artists[:5]]
        lines.append(f"<b>Артисты:</b> " + ", ".join(names))
    when = getattr(profile, "listening_time", None)
    if when:
        lines.append(f"<b>Вы чаще слушаете музыку:</b> {get_listening_time_name(when).lower()}")
    lines.append("")
    lines.append("<b>Вероятно:</b> " + profile.profile_description)
    return "\n".join(lines)


def generate_profile_card(profile: MusicProfile) -> Optional[bytes]:
    """
    Генерирует изображение карточки профиля.
    TODO: Реализовать генерацию изображения через Pillow
    """
    return None
