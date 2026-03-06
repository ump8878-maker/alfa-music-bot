from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Set

from .data import GENRES, MOODS, ERAS, LANGUAGES, POPULAR_ARTISTS, POPULAR_ARTISTS_RU


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для стартового сообщения"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Погнали!", callback_data="start_test")
    builder.button(text="❓ Что это?", callback_data="about_bot")
    builder.adjust(1)
    return builder.as_markup()


def get_genres_keyboard(selected: Set[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора жанров"""
    selected = selected or set()
    builder = InlineKeyboardBuilder()
    
    for genre in GENRES:
        is_selected = genre["id"] in selected
        text = f"✅ {genre['emoji']} {genre['name']}" if is_selected else f"{genre['emoji']} {genre['name']}"
        builder.button(
            text=text,
            callback_data=f"genre:{genre['id']}"
        )
    
    builder.adjust(3)
    
    if selected:
        builder.row(
            InlineKeyboardButton(
                text=f"Далее → ({len(selected)} выбрано)",
                callback_data="genres_done"
            )
        )
    
    return builder.as_markup()


def get_artists_keyboard(
    genres: List[str],
    selected: Set[str] = None,
    current_genre_idx: int = 0,
    cached_artists_by_genre: dict = None
) -> InlineKeyboardMarkup:
    """Клавиатура выбора артистов по категориям жанров"""
    import random
    from .data import POPULAR_ARTISTS, POPULAR_ARTISTS_RU, GENRES
    
    selected = selected or set()
    builder = InlineKeyboardBuilder()
    
    if not genres:
        return builder.as_markup()
    
    # Получаем текущий жанр
    current_genre = genres[current_genre_idx] if current_genre_idx < len(genres) else genres[0]
    
    # Получаем название жанра для отображения
    genre_name = current_genre
    for g in GENRES:
        if g["id"] == current_genre:
            genre_name = g["name"]
            break
    
    # Используем кэшированных артистов или генерируем
    if cached_artists_by_genre and current_genre in cached_artists_by_genre:
        artists = cached_artists_by_genre[current_genre]
    else:
        artists = []
        if current_genre in POPULAR_ARTISTS:
            artists = POPULAR_ARTISTS[current_genre].copy()
        # Добавляем русских артистов для разнообразия
        ru_artists = [a for a in POPULAR_ARTISTS_RU if a not in artists]
        random.shuffle(ru_artists)
        artists.extend(ru_artists[:4])
        random.shuffle(artists)
        artists = artists[:12]  # Максимум 12 артистов на жанр
    
    # Показываем артистов текущего жанра
    for artist in artists:
        is_selected = artist in selected
        text = f"✅ {artist}" if is_selected else artist
        builder.button(
            text=text,
            callback_data=f"artist:{artist}"
        )
    
    builder.adjust(2)
    
    # Считаем выбранных артистов в текущем жанре
    current_genre_selected = sum(1 for a in artists if a in selected)
    total_genres = len(genres)
    
    # Навигация между жанрами
    nav_buttons = []
    if current_genre_idx > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️ Пред. жанр", 
                callback_data=f"artists_genre:{current_genre_idx - 1}"
            )
        )
    
    if current_genre_idx < total_genres - 1:
        # Есть ещё жанры
        next_text = f"След. жанр ▶️" if current_genre_selected > 0 else "Пропустить ▶️"
        nav_buttons.append(
            InlineKeyboardButton(
                text=next_text,
                callback_data=f"artists_genre:{current_genre_idx + 1}"
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопка завершения (только на последнем жанре или если что-то выбрано)
    if current_genre_idx == total_genres - 1 or len(selected) > 0:
        if selected:
            builder.row(
                InlineKeyboardButton(
                    text=f"✅ Готово ({len(selected)} артистов)",
                    callback_data="artists_done"
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text="Пропустить всё →",
                    callback_data="artists_skip"
                )
            )
    
    return builder.as_markup()


def get_mood_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора настроения"""
    builder = InlineKeyboardBuilder()
    
    for mood in MOODS:
        builder.button(
            text=f"{mood['emoji']} {mood['name']}",
            callback_data=f"mood:{mood['id']}"
        )
    
    builder.adjust(1)
    return builder.as_markup()


def get_era_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора эпохи"""
    builder = InlineKeyboardBuilder()
    
    for era in ERAS:
        builder.button(
            text=f"{era['emoji']} {era['name']}",
            callback_data=f"era:{era['id']}"
        )
    
    builder.adjust(1)
    return builder.as_markup()


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка музыки"""
    builder = InlineKeyboardBuilder()
    
    for lang in LANGUAGES:
        builder.button(
            text=f"{lang['emoji']} {lang['name']}",
            callback_data=f"language:{lang['id']}"
        )
    
    builder.adjust(1)
    return builder.as_markup()


def get_profile_keyboard(has_chats: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура после получения профиля"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="👥 Добавить в чат",
        callback_data="add_to_chat"
    )
    builder.button(
        text="🔄 Пройти заново",
        callback_data="restart_test"
    )
    builder.button(
        text="📊 Мои совпадения",
        callback_data="show_matches"
    )
    
    builder.adjust(1)
    return builder.as_markup()


def get_chat_invite_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Клавиатура для добавления бота в чат"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="➕ Добавить в чат",
        url=f"https://t.me/{bot_username}?startgroup=true"
    )
    builder.button(
        text="📤 Поделиться профилем",
        callback_data="share_profile"
    )
    
    builder.adjust(1)
    return builder.as_markup()


def get_match_keyboard(match_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для карточки матча"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="💬 Написать",
        url=f"tg://user?id={user_id}"
    )
    builder.button(
        text="📤 Поделиться",
        callback_data=f"share_match:{match_id}"
    )
    builder.button(
        text="Ещё совпадения →",
        callback_data="more_matches"
    )
    
    builder.adjust(2, 1)
    return builder.as_markup()


def get_battle_keyboard(battle_id: int, user1_id: int, user2_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для голосования в баттле"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="🅰️",
        callback_data=f"vote:{battle_id}:{user1_id}"
    )
    builder.button(
        text="🅱️",
        callback_data=f"vote:{battle_id}:{user2_id}"
    )
    
    builder.adjust(2)
    return builder.as_markup()


def get_prediction_keyboard(round_id: int, options: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура для prediction раунда"""
    builder = InlineKeyboardBuilder()
    
    for option in options:
        builder.button(
            text=option,
            callback_data=f"predict:{round_id}:{option}"
        )
    
    builder.adjust(2)
    return builder.as_markup()


def get_chat_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для первого сообщения в чате"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="🎵 Пройти тест",
        url="https://t.me/{bot_username}?start=from_chat"
    )
    
    return builder.as_markup()


def get_chat_map_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Клавиатура после открытия карты вкусов"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="📊 Все совпадения",
        callback_data=f"chat_matches:{chat_id}"
    )
    builder.button(
        text="⚔️ Запустить баттл",
        callback_data=f"start_battle:{chat_id}"
    )
    builder.button(
        text="🔮 Угадайка",
        callback_data=f"start_prediction:{chat_id}"
    )
    
    builder.adjust(1)
    return builder.as_markup()


def get_paywall_keyboard(product_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для paywall"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="🔓 Открыть",
        callback_data=f"buy:{product_id}"
    )
    builder.button(
        text="👥 Добавить в чат (бесплатно)",
        callback_data="add_to_chat"
    )
    
    builder.adjust(1)
    return builder.as_markup()
